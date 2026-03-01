import type { SessionSummary } from '../types'

interface Props {
  sessions: SessionSummary[]
  currentSessionId: string | null
  onSelectSession: (id: string) => void
  onNewConversation: () => void
  onDeleteSession: (id: string) => void
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

export default function Sidebar({ sessions, currentSessionId, onSelectSession, onNewConversation, onDeleteSession }: Props) {
  return (
    <aside className="w-64 bg-[#eeecea] flex flex-col flex-shrink-0 border-r border-[#dddbd6]">
      {/* Header */}
      <div className="px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#ff7a59] flex items-center justify-center flex-shrink-0 shadow-sm">
            <span className="text-white text-[10px] font-bold tracking-tight">oK</span>
          </div>
          <span className="font-semibold text-[#0d1117] text-sm tracking-tight">onKaul</span>
          <span className="text-[10px] text-[#7c9eff] bg-[#7c9eff]/10 px-1.5 py-0.5 rounded-full font-medium border border-[#7c9eff]/20">AI</span>
        </div>
      </div>

      {/* New conversation */}
      <div className="px-3 pb-3">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2.5 text-sm text-[#4b5563] hover:text-[#0d1117] hover:bg-[#e2e0dc] px-3 py-2 rounded-lg transition-colors font-medium"
        >
          <svg className="w-4 h-4 flex-shrink-0 text-[#ff7a59]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New conversation
        </button>
      </div>

      {/* Divider */}
      <div className="mx-4 border-t border-[#d5d3ce] mb-2" />

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
        {sessions.length === 0 ? (
          <p className="text-xs text-[#9ca3af] px-3 py-6 text-center">No conversations yet</p>
        ) : (
          sessions.map((s) => (
            <div
              key={s.session_id}
              className={`group relative flex items-center rounded-lg transition-colors ${
                s.session_id === currentSessionId
                  ? 'bg-[#e2e0dc]'
                  : 'hover:bg-[#e5e3df]'
              }`}
            >
              <button
                onClick={() => onSelectSession(s.session_id)}
                className="flex-1 min-w-0 text-left px-3 py-2"
              >
                <p
                  className={`text-xs font-medium truncate ${
                    s.session_id === currentSessionId ? 'text-[#0d1117]' : 'text-[#374151]'
                  }`}
                >
                  {s.title}
                </p>
                <p className="text-[11px] text-[#9ca3af] mt-0.5">{relativeTime(s.updated_at)}</p>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteSession(s.session_id)
                }}
                title="Delete conversation"
                className="opacity-0 group-hover:opacity-100 flex-shrink-0 mr-1.5 p-1 rounded hover:bg-[#ff7a59]/15 hover:text-[#ff7a59] text-[#9ca3af] transition-all"
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
