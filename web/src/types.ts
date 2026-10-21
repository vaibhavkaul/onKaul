export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface SessionSummary {
  session_id: string
  title: string
  updated_at: string
}

export interface SessionDetail extends SessionSummary {
  messages: Message[]
}
