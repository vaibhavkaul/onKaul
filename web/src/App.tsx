import { useCallback, useEffect, useState } from 'react'
import { deleteSession, fetchSessions, renameSession } from './api'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'
import { readLocal, writeLocal } from './storage'
import type { SessionSummary } from './types'

const SESSION_KEY = 'onkaul_session_id'

export default function App() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() =>
    readLocal(SESSION_KEY),
  )
  // Remount the chat only when the user navigates — not when a new
  // conversation receives its id mid-stream, which would drop queued messages.
  const [viewKey, setViewKey] = useState(0)
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const loadSessions = useCallback(async () => {
    setSessions(await fetchSessions())
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const openSession = useCallback((sessionId: string | null) => {
    setCurrentSessionId(sessionId)
    writeLocal(SESSION_KEY, sessionId)
    setViewKey((k) => k + 1)
  }, [])

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      await deleteSession(sessionId)
      if (currentSessionId === sessionId) openSession(null)
      loadSessions()
    },
    [currentSessionId, loadSessions, openSession],
  )

  const handleRenameSession = useCallback(
    async (sessionId: string, title: string) => {
      const renamed = await renameSession(sessionId, title)
      if (renamed) loadSessions()
      return renamed !== null
    },
    [loadSessions],
  )

  // Called by the chat when the server assigns or updates its session.
  const handleSessionChange = useCallback(
    (sessionId: string) => {
      setCurrentSessionId(sessionId)
      writeLocal(SESSION_KEY, sessionId)
      loadSessions()
    },
    [loadSessions],
  )

  return (
    <div className="flex h-screen overflow-hidden bg-surface font-sans">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={openSession}
        onNewConversation={() => openSession(null)}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
      />
      <ChatWindow
        key={viewKey}
        initialSessionId={currentSessionId}
        onSessionChange={handleSessionChange}
      />
    </div>
  )
}
