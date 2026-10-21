import { isTouchDevice } from './hooks/useMediaQuery'

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
  const stored = readLocal(ENTER_TO_SEND_KEY)
  if (stored !== null) return stored !== 'false'
  // On touch keyboards Enter is the only way to add a new line; send with the button.
  return !isTouchDevice()
}

export function writeEnterToSend(value: boolean): void {
  writeLocal(ENTER_TO_SEND_KEY, value ? 'true' : 'false')
}
