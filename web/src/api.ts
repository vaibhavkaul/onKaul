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
