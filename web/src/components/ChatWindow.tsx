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
    let resolvedSessionId = sessionId

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
                resolvedSessionId = event.session_id
              } else if (event.type === 'text' && event.content) {
                accumulated += event.content
                const snapshot = accumulated
                setMessages((prev) => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: snapshot }
                  return updated
                })
              } else if (event.type === 'done') {
                if (resolvedSessionId) onSessionChange(resolvedSessionId)
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
    <div className="flex-1 flex flex-col overflow-hidden bg-surface">
      <main className="flex-1 overflow-y-auto px-6 py-8 flex flex-col gap-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center flex-1 text-center mt-20">
            <div className="w-14 h-14 rounded-2xl bg-accent flex items-center justify-center mb-5 shadow-md">
              <span className="text-panel text-xl font-bold tracking-tight">oK</span>
            </div>
            <p className="text-lg font-semibold text-text mb-1">How can I help?</p>
            <p className="text-sm text-muted max-w-sm leading-relaxed">
              Investigate errors, search code, query Datadog, look up Jira issues, and more.
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                <div className="max-w-xl bg-panel border border-border rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed text-accent">
                  {msg.content}
                </div>
              ) : (
                <div className="flex gap-3 max-w-2xl">
                  <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                    <span className="text-panel text-[10px] font-bold">oK</span>
                  </div>
                  <div className={`flex-1 bg-panel border border-border-faint rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-text shadow-sm prose${
                    isStreaming && i === messages.length - 1 ? ' streaming-cursor' : ''
                  }`}>
                    {msg.content ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      <span className="text-faint text-xs">Thinking…</span>
                    )}
                  </div>
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
