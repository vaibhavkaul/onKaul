import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchSession, stopSessionReply } from '../api'
import { draftKey, readEnterToSend, readLocal, writeEnterToSend, writeLocal } from '../storage'
import type { Message, SessionStatus } from '../types'
import Markdown from './Markdown'
import MessageInput from './MessageInput'

const STATUS_NOTES: Partial<Record<SessionStatus, string>> = {
  streaming: 'Still answering in the background. Reopen this conversation in a moment to see the reply.',
  interrupted: 'This reply was cut off before it finished.',
  error: 'This reply failed before it finished.',
}

function errorMessage(status: number): string {
  if (status === 404) return 'This conversation is no longer available. Start a new one.'
  if (status === 409) return 'Still answering your previous message here. Wait for it, or press Stop.'
  return `Server error ${status}`
}

function formatTime(iso?: string): { label: string; full: string } | null {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const sameDay = date.toDateString() === new Date().toDateString()
  return {
    label: sameDay ? time : `${date.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${time}`,
    full: date.toLocaleString(),
  }
}

function askNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {})
  }
}

function notifyReplyFinished(reply: string) {
  if (!document.hidden || !('Notification' in window) || Notification.permission !== 'granted') {
    return
  }
  const body = reply.replace(/\s+/g, ' ').trim().slice(0, 140) || 'Your reply is ready.'
  const n = new Notification('onKaul replied', { body })
  n.onclick = () => {
    window.focus()
    n.close()
  }
}

interface Props {
  initialSessionId: string | null
  onSessionChange: (id: string) => void
}

export default function ChatWindow({ initialSessionId, onSessionChange }: Props) {
  // The conversation this view was opened on. App remounts the view (new key)
  // when the user navigates; later prop changes are just this chat's own id.
  const [openedId] = useState(initialSessionId)
  const [sessionId, setSessionId] = useState<string | null>(openedId)
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionStatus, setSessionStatus] = useState<SessionStatus | undefined>()
  const [queue, setQueue] = useState<string[]>([])
  const [draft, setDraftState] = useState(() => readLocal(draftKey(openedId)) ?? '')
  const [enterToSend, setEnterToSendState] = useState(readEnterToSend)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!openedId) return
    fetchSession(openedId).then((session) => {
      if (session) {
        setMessages(session.messages)
        setSessionStatus(session.status)
      }
    })
  }, [openedId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, queue.length])

  // When a new conversation receives its id, move the unsent draft to the new key.
  const draftRef = useRef(draft)
  draftRef.current = draft
  useEffect(() => {
    if (!sessionId || sessionId === openedId) return
    writeLocal(draftKey(null), null)
    writeLocal(draftKey(sessionId), draftRef.current)
  }, [sessionId, openedId])

  const setDraft = useCallback(
    (value: string) => {
      setDraftState(value)
      writeLocal(draftKey(sessionId), value)
    },
    [sessionId],
  )

  const sendMessage = useCallback(
    async (message: string) => {
      setIsStreaming(true)
      setSessionStatus(undefined)
      askNotificationPermission()
      const now = new Date().toISOString()
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: message, ts: now },
        { role: 'assistant', content: '' },
      ])

      const setReply = (content: string) =>
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: 'assistant', content, ts: new Date().toISOString() },
        ])

      const controller = new AbortController()
      abortRef.current = controller
      let buffer = ''
      let accumulated = ''
      let finished = false
      let resolvedId = sessionId

      try {
        const res = await fetch('/web/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, session_id: sessionId }),
          signal: controller.signal,
        })
        if (!res.ok) throw new Error(errorMessage(res.status))

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
              let event: { type: string; content?: string; session_id?: string }
              try {
                event = JSON.parse(line.slice(6))
              } catch {
                continue // skip malformed events
              }
              if (event.type === 'session' && event.session_id) {
                resolvedId = event.session_id
                if (resolvedId !== sessionId) setSessionId(resolvedId)
                onSessionChange(resolvedId)
              } else if (event.type === 'text' && event.content) {
                accumulated += event.content
                setReply(accumulated)
              } else if (event.type === 'done' || event.type === 'error') {
                if (event.type === 'error') {
                  const note = `⚠️ ${event.content || 'Something went wrong.'}`
                  setReply(accumulated ? `${accumulated}\n\n${note}` : note)
                }
                finished = true
                // The server has saved the turn; refresh the sidebar entry.
                if (resolvedId) onSessionChange(resolvedId)
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          if (!accumulated) setMessages((prev) => prev.slice(0, -1))
        } else {
          setReply(`⚠️ ${(err as Error).message}`)
        }
      } finally {
        abortRef.current = null
        setIsStreaming(false)
        if (finished) notifyReplyFinished(accumulated)
      }
    },
    [sessionId, onSessionChange],
  )

  // Send the next queued message once the current reply ends.
  useEffect(() => {
    if (isStreaming || queue.length === 0) return
    const [next, ...rest] = queue
    setQueue(rest)
    sendMessage(next)
  }, [isStreaming, queue, sendMessage])

  function handleSend(message: string) {
    if (isStreaming) setQueue((q) => [...q, message])
    else sendMessage(message)
  }

  function handleStop() {
    // Stopping also cancels queued follow-ups; put them back in the box so
    // nothing typed is lost.
    if (queue.length) {
      setDraft([...queue, draft].filter((s) => s.trim()).join('\n\n'))
      setQueue([])
    }
    // The reply runs on the server independently of this connection, so ask
    // it to stop (it saves the partial reply), then stop listening.
    if (sessionId) stopSessionReply(sessionId)
    abortRef.current?.abort()
  }

  function handleEnterToSend(value: boolean) {
    setEnterToSendState(value)
    writeEnterToSend(value)
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-surface">
      <main className="flex-1 overflow-y-auto px-3 py-4 md:px-6 md:py-8 flex flex-col gap-5 md:gap-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center flex-1 text-center mt-10 md:mt-20 px-4">
            <div className="w-14 h-14 rounded-2xl bg-accent flex items-center justify-center mb-5 shadow-md">
              <span className="text-panel text-xl font-bold tracking-tight">oK</span>
            </div>
            <p className="text-lg font-semibold text-text mb-1">How can I help?</p>
            <p className="text-sm text-muted max-w-sm leading-relaxed">
              Investigate errors, search code, query Datadog, look up Jira issues, and more.
            </p>
          </div>
        ) : (
          messages.map((msg, i) => {
            const time = formatTime(msg.ts)
            const isLastStreaming = isStreaming && i === messages.length - 1
            return (
              <div
                key={i}
                className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                {msg.role === 'user' ? (
                  <div className="max-w-[85%] md:max-w-xl bg-panel border border-border rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed text-accent whitespace-pre-wrap break-words">
                    {msg.content}
                  </div>
                ) : (
                  <div className="flex gap-2 md:gap-3 max-w-full md:max-w-2xl min-w-0">
                    <div className="hidden md:flex w-7 h-7 rounded-lg bg-accent items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                      <span className="text-panel text-[10px] font-bold">oK</span>
                    </div>
                    <div
                      className={`flex-1 min-w-0 break-words bg-panel border border-border-faint rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-text shadow-sm prose${
                        isLastStreaming ? ' streaming-cursor' : ''
                      }`}
                    >
                      {msg.content ? (
                        <Markdown>{msg.content}</Markdown>
                      ) : (
                        <span className="text-faint text-xs">Thinking…</span>
                      )}
                    </div>
                  </div>
                )}
                {time && !isLastStreaming && (
                  <time
                    dateTime={msg.ts}
                    title={time.full}
                    className={`text-[11px] text-faint ${msg.role === 'assistant' ? 'md:ml-10' : ''}`}
                  >
                    {time.label}
                  </time>
                )}
              </div>
            )
          })
        )}
        {!isStreaming && sessionStatus && STATUS_NOTES[sessionStatus] && (
          <p className="text-xs text-faint text-center">{STATUS_NOTES[sessionStatus]}</p>
        )}
        <div ref={bottomRef} />
      </main>
      <MessageInput
        value={draft}
        onChange={setDraft}
        onSend={handleSend}
        isStreaming={isStreaming}
        onStop={handleStop}
        queued={queue}
        onRemoveQueued={(i) => setQueue((q) => q.filter((_, j) => j !== i))}
        enterToSend={enterToSend}
        onEnterToSendChange={handleEnterToSend}
      />
    </div>
  )
}
