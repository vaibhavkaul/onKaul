import { useCallback, useEffect, useState } from 'react'
import { deleteSession, fetchSessions, listSandboxRepos } from './api'
import ChatWindow from './components/ChatWindow'
import SandboxView from './components/SandboxView'
import Sidebar from './components/Sidebar'
import type { SandboxRepo, SessionSummary } from './types'

const SESSION_KEY = 'onkaul_session_id'

export default function App() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    () => localStorage.getItem(SESSION_KEY),
  )
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sandboxRepos, setSandboxRepos] = useState<SandboxRepo[]>([])
  const [activeSandboxKey, setActiveSandboxKey] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const loadSessions = useCallback(async () => {
    setSessions(await fetchSessions())
  }, [])

  useEffect(() => {
    loadSessions()
    listSandboxRepos().then(setSandboxRepos)
  }, [loadSessions])

  const selectSession = useCallback((sessionId: string) => {
    setActiveSandboxKey(null)
    setCurrentSessionId(sessionId)
    localStorage.setItem(SESSION_KEY, sessionId)
  }, [])

  const newConversation = useCallback(() => {
    setActiveSandboxKey(null)
    setCurrentSessionId(null)
    localStorage.removeItem(SESSION_KEY)
  }, [])

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      await deleteSession(sessionId)
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null)
        localStorage.removeItem(SESSION_KEY)
      }
      loadSessions()
    },
    [currentSessionId, loadSessions],
  )

  const handleSessionChange = useCallback(
    (sessionId: string) => {
      setCurrentSessionId(sessionId)
      localStorage.setItem(SESSION_KEY, sessionId)
      loadSessions()
    },
    [loadSessions],
  )

  const handleOpenSandbox = useCallback((key: string) => {
    setActiveSandboxKey(key)
    setCurrentSessionId(null)
    localStorage.removeItem(SESSION_KEY)
  }, [])

  const handleCloseSandbox = useCallback(() => {
    setActiveSandboxKey(null)
  }, [])

  const activeSandboxRepo = sandboxRepos.find((r) => r.key === activeSandboxKey) ?? null

  return (
    <div className="flex h-screen overflow-hidden bg-surface font-sans">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={selectSession}
        onNewConversation={newConversation}
        onDeleteSession={handleDeleteSession}
        sandboxRepos={sandboxRepos}
        activeSandboxKey={activeSandboxKey}
        onOpenSandbox={handleOpenSandbox}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
      />
      {activeSandboxRepo ? (
        <SandboxView
          key={activeSandboxRepo.key}
          repo={activeSandboxRepo}
          onClose={handleCloseSandbox}
        />
      ) : (
        <ChatWindow
          key={currentSessionId ?? 'new'}
          sessionId={currentSessionId}
          onSessionChange={handleSessionChange}
        />
      )}
    </div>
  )
}
