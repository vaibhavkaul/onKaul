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
    <aside className="w-60 bg-white border-r border-slate-200 flex flex-col flex-shrink-0">
      <div className="px-4 py-4 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-800 text-base">onKaul</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">AI</span>
        </div>
      </div>

      <div className="px-3 pt-3 pb-2">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 px-3 py-2 rounded-lg transition-colors"
        >
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
        {sessions.length === 0 ? (
          <p className="text-xs text-slate-400 px-3 py-4 text-center">No conversations yet</p>
        ) : (
          sessions.map((s) => (
            <div
              key={s.session_id}
              className={`group relative flex items-center rounded-lg transition-colors ${
                s.session_id === currentSessionId ? 'bg-blue-50' : 'hover:bg-slate-50'
              }`}
            >
              <button
                onClick={() => onSelectSession(s.session_id)}
                className="flex-1 min-w-0 text-left px-3 py-2"
              >
                <p
                  className={`text-xs font-medium truncate ${
                    s.session_id === currentSessionId ? 'text-blue-700' : 'text-slate-700'
                  }`}
                >
                  {s.title}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">{relativeTime(s.updated_at)}</p>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteSession(s.session_id)
                }}
                title="Delete conversation"
                className="opacity-0 group-hover:opacity-100 flex-shrink-0 mr-1.5 p-1 rounded hover:bg-red-100 hover:text-red-500 text-slate-400 transition-all"
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
