import { useEffect, useRef } from 'react'

interface Props {
  onSend: (message: string) => void
  isStreaming: boolean
  onStop: () => void
}

export default function MessageInput({ onSend, isStreaming, onStop }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!isStreaming) textareaRef.current?.focus()
  }, [isStreaming])

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  function submit() {
    const el = textareaRef.current
    if (!el || isStreaming) return
    const message = el.value.trim()
    if (!message) return
    el.value = ''
    autoResize()
    onSend(message)
  }

  return (
    <footer className="bg-[#f5f4f0] border-t border-[#dddbd6] px-6 py-4">
      <form
        className="max-w-3xl mx-auto"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <div className="flex gap-2 items-end bg-white border border-[#e5e7eb] rounded-2xl px-4 py-3 shadow-sm focus-within:border-[#ff7a59] focus-within:ring-2 focus-within:ring-[#ff7a59]/10 transition-all">
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder="Message onKaul…"
            disabled={isStreaming}
            onInput={autoResize}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                submit()
              }
            }}
            className="flex-1 resize-none overflow-hidden outline-none text-sm text-[#0d1117] placeholder-[#9ca3af] bg-transparent leading-relaxed disabled:opacity-60"
            style={{ maxHeight: 160 }}
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-[#fff0ed] hover:bg-[#ff7a59]/20 text-[#ff7a59] transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            </button>
          ) : (
            <button
              type="submit"
              className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-[#ff7a59] hover:bg-[#f56a47] text-white transition-colors shadow-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>
      </form>
    </footer>
  )
}
