import { useEffect, useLayoutEffect, useRef } from 'react'

interface Props {
  value: string
  onChange: (value: string) => void
  onSend: (message: string) => void
  isStreaming: boolean
  onStop: () => void
  queued: string[]
  onRemoveQueued: (index: number) => void
  enterToSend: boolean
  onEnterToSendChange: (value: boolean) => void
}

const MAX_HEIGHT = 160

export default function MessageInput({
  value,
  onChange,
  onSend,
  isStreaming,
  onStop,
  queued,
  onRemoveQueued,
  enterToSend,
  onEnterToSendChange,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  // Grow with the content (also when a draft is restored programmatically).
  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, MAX_HEIGHT) + 'px'
  }, [value])

  function submit() {
    const message = value.trim()
    if (!message) return
    onChange('')
    onSend(message)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key !== 'Enter' || e.nativeEvent.isComposing) return
    const modifier = e.metaKey || e.ctrlKey
    if ((enterToSend && !e.shiftKey && !modifier) || (!enterToSend && modifier)) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <footer className="bg-surface border-t border-border px-6 py-4">
      <form
        className="max-w-3xl mx-auto"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        {queued.length > 0 && (
          <ul className="mb-2 space-y-1" aria-label="Queued messages">
            {queued.map((q, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-xs text-muted bg-panel border border-border-faint rounded-lg px-3 py-1.5"
              >
                <span className="text-faint flex-shrink-0">Queued</span>
                <span className="flex-1 min-w-0 truncate">{q}</span>
                <button
                  type="button"
                  onClick={() => onRemoveQueued(i)}
                  className="text-faint hover:text-text flex-shrink-0"
                  aria-label="Remove queued message"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-2 items-end bg-input border border-border-faint rounded-2xl px-4 py-3 shadow-sm focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10 transition-all">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            placeholder={isStreaming ? 'Queue a follow-up…' : 'Message onKaul…'}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            className="flex-1 resize-none overflow-y-auto outline-none text-sm text-text placeholder-faint bg-transparent leading-relaxed font-sans"
            style={{ maxHeight: MAX_HEIGHT }}
          />
          {isStreaming && (
            <button
              type="button"
              onClick={onStop}
              title="Stop (queued messages go back into the box)"
              className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-accent-faint hover:bg-accent/20 text-accent transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            </button>
          )}
          <button
            type="submit"
            disabled={!value.trim()}
            title={isStreaming ? 'Queue message' : 'Send'}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-accent hover:bg-accent-hover text-panel transition-colors shadow-sm disabled:opacity-40"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
        <div className="flex items-center justify-between mt-1.5 px-1 text-[11px] text-faint">
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={enterToSend}
              onChange={(e) => onEnterToSendChange(e.target.checked)}
              className="accent-accent"
            />
            Enter to send
          </label>
          <span>{enterToSend ? 'Shift+Enter for a new line' : '⌘/Ctrl+Enter to send'}</span>
        </div>
      </form>
    </footer>
  )
}
