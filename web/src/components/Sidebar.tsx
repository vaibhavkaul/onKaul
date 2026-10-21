import { useState } from 'react'
import type { SessionSummary } from '../types'

interface Props {
  sessions: SessionSummary[]
  currentSessionId: string | null
  onSelectSession: (id: string) => void
  onNewConversation: () => void
  onDeleteSession: (id: string) => void
  onRenameSession: (id: string, title: string) => Promise<boolean>
  collapsed: boolean
  onToggleCollapse: () => void
  /** Render as a slide-over drawer (phones); the toggle button closes it. */
  drawer?: boolean
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function RenameInput({
  initial,
  onDone,
}: {
  initial: string
  onDone: (title: string | null) => void
}) {
  const [value, setValue] = useState(initial)
  const finish = (save: boolean) => {
    const title = value.trim()
    onDone(save && title && title !== initial ? title : null)
  }
  return (
    <input
      autoFocus
      value={value}
      maxLength={200}
      aria-label="Conversation title"
      onChange={(e) => setValue(e.target.value)}
      onFocus={(e) => e.currentTarget.select()}
      onKeyDown={(e) => {
        if (e.key === 'Enter') finish(true)
        if (e.key === 'Escape') finish(false)
      }}
      onBlur={() => finish(false)}
      className="flex-1 min-w-0 mx-2 my-1.5 px-2 py-1 text-xs bg-surface text-text border border-accent rounded-md outline-none"
    />
  )
}

export default function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewConversation,
  onDeleteSession,
  onRenameSession,
  collapsed,
  onToggleCollapse,
  drawer = false,
}: Props) {
  const [renamingId, setRenamingId] = useState<string | null>(null)

  async function finishRename(sessionId: string, title: string | null) {
    setRenamingId(null)
    if (title) await onRenameSession(sessionId, title)
  }

  if (collapsed && !drawer) {
    return (
      <aside className="w-10 bg-sidebar flex flex-col flex-shrink-0 border-r border-border items-center py-3 gap-3">
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-border transition-colors"
          title="Expand sidebar"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </aside>
    )
  }

  return (
    <aside
      className={`bg-sidebar flex flex-col flex-shrink-0 border-r border-border ${
        drawer
          ? 'fixed inset-y-0 left-0 z-40 w-72 max-w-[85vw] shadow-2xl pt-[env(safe-area-inset-top)]'
          : 'w-64'
      }`}
    >
      {/* Header */}
      <div className="px-5 py-5 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center flex-shrink-0 shadow-sm">
            <span className="text-panel text-[10px] font-bold tracking-tight">oK</span>
          </div>
          <span className="font-semibold text-text text-sm tracking-tight">onKaul</span>
          <span className="text-[10px] text-sky bg-sky/10 px-1.5 py-0.5 rounded-full font-medium border border-sky/20">AI</span>
          <button
            onClick={onToggleCollapse}
            className="ml-auto p-1 rounded text-faint hover:text-muted hover:bg-border transition-colors"
            title={drawer ? 'Close menu' : 'Collapse sidebar'}
            aria-label={drawer ? 'Close menu' : 'Collapse sidebar'}
          >
            <svg className={drawer ? 'w-5 h-5' : 'w-3.5 h-3.5'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={drawer ? 'M6 18L18 6M6 6l12 12' : 'M15 19l-7-7 7-7'}
              />
            </svg>
          </button>
        </div>
      </div>

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto">
        {/* Conversations */}
        <div className="pt-3 pb-2">
          <div className="px-4 pb-2">
            <p className="text-[10px] font-semibold text-faint uppercase tracking-widest">Conversations</p>
          </div>
          <div className="px-3 pb-2">
            <button
              onClick={onNewConversation}
              className="w-full flex items-center gap-2 text-xs font-semibold text-accent bg-accent/10 hover:bg-accent/20 border border-accent/25 hover:border-accent/40 px-3 py-2 rounded-lg transition-colors"
            >
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
              New conversation
            </button>
          </div>
          <div className="px-2 space-y-0.5">
            {sessions.length === 0 ? (
              <p className="text-xs text-faint px-3 py-4 text-center">No conversations yet</p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.session_id}
                  className={`group relative flex items-center rounded-lg transition-colors ${
                    s.session_id === currentSessionId ? 'bg-border' : 'hover:bg-border-faint'
                  }`}
                >
                  {renamingId === s.session_id ? (
                    <RenameInput
                      initial={s.title}
                      onDone={(title) => finishRename(s.session_id, title)}
                    />
                  ) : (
                    <button
                      onClick={() => onSelectSession(s.session_id)}
                      onDoubleClick={() => setRenamingId(s.session_id)}
                      className="flex-1 min-w-0 text-left px-3 py-2"
                    >
                      <p className={`text-xs font-medium truncate ${
                        s.session_id === currentSessionId ? 'text-text' : 'text-muted'
                      }`}>
                        {s.title}
                      </p>
                      <p className="text-[11px] text-faint mt-0.5">{relativeTime(s.updated_at)}</p>
                    </button>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); setRenamingId(s.session_id) }}
                    title="Rename conversation"
                    aria-label="Rename conversation"
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 [@media(hover:none)]:opacity-100 flex-shrink-0 p-1 rounded hover:bg-accent-faint hover:text-accent text-faint transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536M4 20h4l10.5-10.5a2.5 2.5 0 00-3.536-3.536L4 16.5V20z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDeleteSession(s.session_id) }}
                    title="Delete conversation"
                    aria-label="Delete conversation"
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 [@media(hover:none)]:opacity-100 flex-shrink-0 mr-1.5 p-1 rounded hover:bg-accent-faint hover:text-accent text-faint transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </aside>
  )
}
