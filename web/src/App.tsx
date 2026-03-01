import { useCallback, useEffect, useState } from 'react'
import { fetchSessions } from './api'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'
import type { SessionSummary } from './types'

const SESSION_KEY = 'onkaul_session_id'

export default function App() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    () => localStorage.getItem(SESSION_KEY),
  )
  const [sessions, setSessions] = useState<SessionSummary[]>([])

  const loadSessions = useCallback(async () => {
    setSessions(await fetchSessions())
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const selectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    localStorage.setItem(SESSION_KEY, sessionId)
  }, [])

  const newConversation = useCallback(() => {
    setCurrentSessionId(null)
    localStorage.removeItem(SESSION_KEY)
  }, [])

  const handleSessionChange = useCallback(
    (sessionId: string) => {
      setCurrentSessionId(sessionId)
      localStorage.setItem(SESSION_KEY, sessionId)
      loadSessions()
    },
    [loadSessions],
  )

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={selectSession}
        onNewConversation={newConversation}
      />
      <ChatWindow
        key={currentSessionId ?? 'new'}
        sessionId={currentSessionId}
        onSessionChange={handleSessionChange}
      />
    </div>
  )
}
