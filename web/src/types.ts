export interface Message {
  role: 'user' | 'assistant'
  content: string
  ts?: string // ISO 8601, set by the server
}

export interface SessionSummary {
  session_id: string
  title: string
  updated_at: string
}

export type SessionStatus = 'streaming' | 'done' | 'error' | 'interrupted'

export interface SessionDetail extends SessionSummary {
  messages: Message[]
  status?: SessionStatus
}
