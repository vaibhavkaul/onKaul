// localStorage can throw (private windows, blocked site data) — every access is
// best-effort and the UI works without it.

export function readLocal(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

export function writeLocal(key: string, value: string | null): void {
  try {
    if (value === null || value === '') localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* ignore */
  }
}

const DRAFT_PREFIX = 'onkaul_draft:'
const ENTER_TO_SEND_KEY = 'onkaul_enter_to_send'

export const draftKey = (sessionId: string | null) => `${DRAFT_PREFIX}${sessionId ?? 'new'}`

export function readEnterToSend(): boolean {
  return readLocal(ENTER_TO_SEND_KEY) !== 'false'
}

export function writeEnterToSend(value: boolean): void {
  writeLocal(ENTER_TO_SEND_KEY, value ? 'true' : 'false')
}
