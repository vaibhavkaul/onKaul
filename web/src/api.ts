import type { SessionDetail, SessionSummary } from './types'

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

export async function renameSession(sessionId: string, title: string): Promise<SessionSummary | null> {
  try {
    const res = await fetch(`/web/sessions/${sessionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function stopSessionReply(sessionId: string): Promise<void> {
  try {
    await fetch(`/web/sessions/${sessionId}/stop`, { method: 'POST' })
  } catch {
    /* best-effort: the reply may already have finished */
  }
}
