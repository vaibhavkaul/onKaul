import { useCallback, useEffect, useState } from 'react'
import { deleteSession, fetchSessions, listSandboxRepos, listUserProjects } from './api'
import ChatWindow from './components/ChatWindow'
import NewProjectModal from './components/NewProjectModal'
import SandboxView from './components/SandboxView'
import Sidebar from './components/Sidebar'
import type { SandboxRepo, SessionSummary, UserProject } from './types'

const SESSION_KEY = 'onkaul_session_id'

// Convert a UserProject into the SandboxRepo shape that SandboxView expects
function projectToSandboxRepo(p: UserProject): SandboxRepo {
  return {
    key: p.slug,
    name: p.name,
    org: '',
    sandbox: {
      appType: p.project_type,
      previewPort: p.preview_port,
      startCommand: p.start_command,
    },
  }
}

export default function App() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    () => localStorage.getItem(SESSION_KEY),
  )
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sandboxRepos, setSandboxRepos] = useState<SandboxRepo[]>([])
  const [userProjects, setUserProjects] = useState<UserProject[]>([])
  const [activeSandboxKey, setActiveSandboxKey] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showNewProject, setShowNewProject] = useState(false)

  const loadSessions = useCallback(async () => {
    setSessions(await fetchSessions())
  }, [])

  useEffect(() => {
    loadSessions()
    listSandboxRepos().then(setSandboxRepos)
    listUserProjects().then(setUserProjects)
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

  const handleProjectCreated = useCallback(
    (project: UserProject) => {
      setUserProjects((prev) => [project, ...prev])
      setShowNewProject(false)
      handleOpenSandbox(project.slug)
    },
    [handleOpenSandbox],
  )

  // Resolve active sandbox repo — could be a configured repo or a user project
  const activeSandboxRepo =
    sandboxRepos.find((r) => r.key === activeSandboxKey) ??
    (userProjects.find((p) => p.slug === activeSandboxKey)
      ? projectToSandboxRepo(userProjects.find((p) => p.slug === activeSandboxKey)!)
      : null)

  return (
    <div className="flex h-screen overflow-hidden bg-surface font-sans">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={selectSession}
        onNewConversation={newConversation}
        onDeleteSession={handleDeleteSession}
        sandboxRepos={sandboxRepos}
        userProjects={userProjects}
        activeSandboxKey={activeSandboxKey}
        onOpenSandbox={handleOpenSandbox}
        onNewProject={() => setShowNewProject(true)}
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
      {showNewProject && (
        <NewProjectModal
          onCreated={handleProjectCreated}
          onClose={() => setShowNewProject(false)}
        />
      )}
    </div>
  )
}
