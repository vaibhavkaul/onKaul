import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { fetchSession } from '../api'
import type { Message } from '../types'
import MessageInput from './MessageInput'

interface Props {
  sessionId: string | null
  onSessionChange: (id: string) => void
}

export default function ChatWindow({ sessionId, onSessionChange }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sessionId) return
    fetchSession(sessionId).then((session) => {
      if (session) setMessages(session.messages)
    })
  }, [sessionId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(message: string) {
    setIsStreaming(true)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message },
      { role: 'assistant', content: '' },
    ])

    const controller = new AbortController()
    abortRef.current = controller
    let buffer = ''
    let accumulated = ''

    try {
      const res = await fetch('/web/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId }),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const parts = buffer.split('\n\n')
        buffer = parts.pop()!

        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue
            try {
              const event = JSON.parse(line.slice(6)) as {
                type: string
                content?: string
                session_id?: string
              }
              if (event.type === 'session' && event.session_id) {
                onSessionChange(event.session_id)
              } else if (event.type === 'text' && event.content) {
                accumulated += event.content
                const snapshot = accumulated
                setMessages((prev) => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: snapshot }
                  return updated
                })
              }
            } catch {
              /* skip malformed events */
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        if (!accumulated) setMessages((prev) => prev.slice(0, -1))
      } else {
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: 'assistant', content: `⚠️ ${(err as Error).message}` },
        ])
      }
    } finally {
      abortRef.current = null
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <main className="flex-1 overflow-y-auto px-4 py-6 flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="flex justify-center">
            <div className="max-w-xl text-center text-slate-400 mt-16">
              <div className="text-4xl mb-4">🤖</div>
              <p className="text-lg font-medium text-slate-600">Ask onKaul anything</p>
              <p className="text-sm mt-1">
                Investigate errors, search code, query Datadog, look up Jira issues, and more.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                <div className="max-w-xl bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm whitespace-pre-wrap">
                  {msg.content}
                </div>
              ) : (
                <div
                  className={`max-w-2xl bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 shadow-sm prose${
                    isStreaming && i === messages.length - 1 ? ' streaming-cursor' : ''
                  }`}
                >
                  {msg.content ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    <span className="text-slate-400 text-xs">Thinking…</span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </main>
      <MessageInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        onStop={() => abortRef.current?.abort()}
      />
    </div>
  )
}
