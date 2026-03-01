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
    <footer className="bg-white border-t border-slate-200 px-4 py-3">
      <form
        className="max-w-3xl mx-auto flex gap-2 items-end"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder="Ask onKaul something…"
          disabled={isStreaming}
          onInput={autoResize}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          className="flex-1 resize-none overflow-hidden rounded-xl border border-slate-300 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 transition-all disabled:opacity-60"
          style={{ maxHeight: 160 }}
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="bg-slate-200 hover:bg-red-100 hover:text-red-600 border border-slate-200 text-slate-600 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors flex-shrink-0"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            className="bg-blue-500 hover:bg-blue-600 text-white rounded-xl px-4 py-2.5 text-sm font-medium transition-colors flex-shrink-0"
          >
            Send
          </button>
        )}
      </form>
    </footer>
  )
}
