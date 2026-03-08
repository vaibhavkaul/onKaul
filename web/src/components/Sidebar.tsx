import type { SandboxRepo, SessionSummary } from '../types'

interface Props {
  sessions: SessionSummary[]
  currentSessionId: string | null
  onSelectSession: (id: string) => void
  onNewConversation: () => void
  onDeleteSession: (id: string) => void
  sandboxRepos: SandboxRepo[]
  activeSandboxKey: string | null
  onOpenSandbox: (key: string) => void
  collapsed: boolean
  onToggleCollapse: () => void
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

export default function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewConversation,
  onDeleteSession,
  sandboxRepos,
  activeSandboxKey,
  onOpenSandbox,
  collapsed,
  onToggleCollapse,
}: Props) {
  if (collapsed) {
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
    <aside className="w-64 bg-sidebar flex flex-col flex-shrink-0 border-r border-border">
      {/* Header */}
      <div className="px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center flex-shrink-0 shadow-sm">
            <span className="text-panel text-[10px] font-bold tracking-tight">oK</span>
          </div>
          <span className="font-semibold text-text text-sm tracking-tight">onKaul</span>
          <span className="text-[10px] text-sky bg-sky/10 px-1.5 py-0.5 rounded-full font-medium border border-sky/20">AI</span>
          <button
            onClick={onToggleCollapse}
            className="ml-auto p-1 rounded text-faint hover:text-muted hover:bg-border transition-colors"
            title="Collapse sidebar"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* New conversation */}
      <div className="px-3 pb-3">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2.5 text-sm text-muted hover:text-text hover:bg-border px-3 py-2 rounded-lg transition-colors font-medium"
        >
          <svg className="w-4 h-4 flex-shrink-0 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New conversation
        </button>
      </div>

      {/* Divider */}
      <div className="mx-4 border-t border-border mb-2" />

      {/* Sandboxes section */}
      {sandboxRepos.length > 0 && (
        <>
          <div className="px-4 pb-1">
            <p className="text-[10px] font-semibold text-faint uppercase tracking-widest">Sandboxes</p>
          </div>
          <div className="px-2 pb-2 space-y-0.5">
            {sandboxRepos.map((repo) => (
              <button
                key={repo.key}
                onClick={() => onOpenSandbox(repo.key)}
                className={`w-full flex items-center gap-2.5 text-left px-3 py-2 rounded-lg transition-colors ${
                  activeSandboxKey === repo.key
                    ? 'bg-border text-text'
                    : 'text-muted hover:text-text hover:bg-border-faint'
                }`}
              >
                <svg className="w-3.5 h-3.5 flex-shrink-0 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span className="text-xs font-medium truncate">{repo.name}</span>
              </button>
            ))}
          </div>
          <div className="mx-4 border-t border-border mb-2" />
        </>
      )}

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
        {sessions.length === 0 ? (
          <p className="text-xs text-faint px-3 py-6 text-center">No conversations yet</p>
        ) : (
          sessions.map((s) => (
            <div
              key={s.session_id}
              className={`group relative flex items-center rounded-lg transition-colors ${
                s.session_id === currentSessionId ? 'bg-border' : 'hover:bg-border-faint'
              }`}
            >
              <button
                onClick={() => onSelectSession(s.session_id)}
                className="flex-1 min-w-0 text-left px-3 py-2"
              >
                <p className={`text-xs font-medium truncate ${
                  s.session_id === currentSessionId ? 'text-text' : 'text-muted'
                }`}>
                  {s.title}
                </p>
                <p className="text-[11px] text-faint mt-0.5">{relativeTime(s.updated_at)}</p>
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onDeleteSession(s.session_id) }}
                title="Delete conversation"
                className="opacity-0 group-hover:opacity-100 flex-shrink-0 mr-1.5 p-1 rounded hover:bg-accent-faint hover:text-accent text-faint transition-all"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
