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

export interface SandboxConfig {
  appType: 'static' | 'dev-server'
  previewPort: number
  startCommand?: string
}

export interface SandboxRepo {
  key: string
  name: string
  org: string
  sandbox: SandboxConfig
}

export interface SandboxStatus {
  status: 'running' | 'stopped'
  container_name?: string
  preview_port?: number
}

export interface GitInfo {
  branch: string
  has_changes: boolean
  changed_count: number
}

export interface PushResult {
  branch: string
  pr_url: string
}
