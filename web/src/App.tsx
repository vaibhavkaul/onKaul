import { useCallback, useEffect, useState } from 'react'
import { deleteSession, fetchSessions, renameSession } from './api'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'
import { useIsMobile } from './hooks/useMediaQuery'
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
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    if (!isMobile) setDrawerOpen(false)
  }, [isMobile])

  useEffect(() => {
    if (!drawerOpen) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setDrawerOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen])

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
    setDrawerOpen(false)
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

  const currentTitle = sessions.find((s) => s.session_id === currentSessionId)?.title

  const sidebar = (
    <Sidebar
      sessions={sessions}
      currentSessionId={currentSessionId}
      onSelectSession={openSession}
      onNewConversation={() => openSession(null)}
      onDeleteSession={handleDeleteSession}
      onRenameSession={handleRenameSession}
      collapsed={sidebarCollapsed}
      onToggleCollapse={() =>
        isMobile ? setDrawerOpen(false) : setSidebarCollapsed((c) => !c)
      }
      drawer={isMobile}
    />
  )

  return (
    <div className="app-shell flex overflow-hidden bg-surface font-sans">
      {isMobile ? (
        drawerOpen && (
          <>
            <div
              className="fixed inset-0 z-30 bg-black/60"
              onClick={() => setDrawerOpen(false)}
              aria-hidden="true"
            />
            {sidebar}
          </>
        )
      ) : (
        sidebar
      )}
      <div className="flex-1 min-w-0 flex flex-col">
        {isMobile && (
          <header className="flex items-center gap-2 px-2 pt-[env(safe-area-inset-top)] border-b border-border bg-sidebar flex-shrink-0">
            <button
              onClick={() => setDrawerOpen(true)}
              className="p-2.5 text-muted hover:text-text"
              aria-label="Open conversations"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <span className="flex-1 min-w-0 truncate text-sm font-medium text-text">
              {currentTitle ?? 'onKaul'}
            </span>
            <button
              onClick={() => openSession(null)}
              className="p-2.5 text-accent"
              aria-label="New conversation"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </header>
        )}
        <ChatWindow
          key={viewKey}
          initialSessionId={currentSessionId}
          onSessionChange={handleSessionChange}
        />
      </div>
    </div>
  )
}
