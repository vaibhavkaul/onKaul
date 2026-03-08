import type { CreateProjectRequest, GitInfo, PushResult, SandboxAsset, SandboxRepo, SandboxStatus, SessionDetail, SessionSummary, ShareInfo, SharedSandboxInfo, UserProject } from './types'

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

export async function listAssets(repo: string): Promise<SandboxAsset[]> {
  try {
    const res = await fetch(`/sandbox/${repo}/assets`)
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

export async function uploadAsset(repo: string, file: File): Promise<SandboxAsset> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`/sandbox/${repo}/assets`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail ?? 'Upload failed')
  }
  return res.json()
}

export async function deleteAsset(repo: string, filename: string): Promise<void> {
  await fetch(`/sandbox/${repo}/assets/${encodeURIComponent(filename)}`, { method: 'DELETE' })
}

export async function linkSandboxRepo(repo: string, repoUrl: string): Promise<void> {
  const res = await fetch(`/sandbox/${repo}/link-repo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to link repo' }))
    throw new Error(err.detail ?? 'Failed to link repo')
  }
}

export async function shareSandbox(repo: string): Promise<ShareInfo> {
  const res = await fetch(`/sandbox/${repo}/share`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create share link' }))
    throw new Error(err.detail ?? 'Failed to create share link')
  }
  const { token } = await res.json()
  const url = `${window.location.origin}/shared/${token}`
  return { token, url }
}

export async function getSharedSandboxInfo(token: string): Promise<SharedSandboxInfo | null> {
  try {
    const res = await fetch(`/sandbox/shared/${token}/info`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
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
