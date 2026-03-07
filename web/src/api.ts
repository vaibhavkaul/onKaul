import type { CreateProjectRequest, GitInfo, PushResult, SandboxRepo, SandboxStatus, SessionDetail, SessionSummary, UserProject } from './types'

export async function fetchSessions(): Promise<SessionSummary[]> {
  try {
    const res = await fetch('/web/sessions')
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

export async function fetchSession(sessionId: string): Promise<SessionDetail | null> {
  try {
    const res = await fetch(`/web/sessions/${sessionId}`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function deleteSession(sessionId: string): Promise<boolean> {
  try {
    const res = await fetch(`/web/sessions/${sessionId}`, { method: 'DELETE' })
    return res.ok
  } catch {
    return false
  }
}

export async function listSandboxRepos(): Promise<SandboxRepo[]> {
  try {
    const res = await fetch('/sandbox/repos')
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

export async function startSandbox(repo: string): Promise<SandboxStatus> {
  const res = await fetch(`/sandbox/${repo}/start`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start sandbox' }))
    throw new Error(err.detail ?? 'Failed to start sandbox')
  }
  return res.json()
}

export async function stopSandbox(repo: string): Promise<void> {
  await fetch(`/sandbox/${repo}/stop`, { method: 'DELETE' })
}

export async function getSandboxStatus(repo: string): Promise<SandboxStatus> {
  try {
    const res = await fetch(`/sandbox/${repo}/status`)
    if (!res.ok) return { status: 'stopped' }
    return res.json()
  } catch {
    return { status: 'stopped' }
  }
}

export async function getGitInfo(repo: string): Promise<GitInfo | null> {
  try {
    const res = await fetch(`/sandbox/${repo}/git-info`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function resetSandbox(repo: string): Promise<void> {
  const res = await fetch(`/sandbox/${repo}/reset`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Reset failed' }))
    throw new Error(err.detail ?? 'Reset failed')
  }
}

export async function listUserProjects(): Promise<UserProject[]> {
  try {
    const res = await fetch('/sandbox/user-projects')
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

export async function deleteUserProject(slug: string): Promise<void> {
  await fetch(`/sandbox/user-projects/${slug}`, { method: 'DELETE' })
}

export async function createUserProject(req: CreateProjectRequest): Promise<UserProject> {
  const res = await fetch('/sandbox/user-projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create project' }))
    throw new Error(err.detail ?? 'Failed to create project')
  }
  return res.json()
}

export async function pushSandboxPR(repo: string, prTitle: string, commitMessage: string): Promise<PushResult> {
  const res = await fetch(`/sandbox/${repo}/push`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pr_title: prTitle, commit_message: commitMessage }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Push failed' }))
    throw new Error(err.detail ?? 'Push failed')
  }
  return res.json()
}
