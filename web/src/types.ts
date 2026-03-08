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
  appType: 'static' | 'dev-server' | 'fullstack-python-vite'
  previewPort: number
  startCommand?: string
  backendStartCommand?: string
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
  branch: string | null
  has_changes: boolean
  changed_count: number
  has_remote: boolean
}

export interface PushResult {
  branch: string
  pr_url: string
}

export type ProjectType = 'static' | 'fullstack-python-vite'

export interface UserProject {
  slug: string
  name: string
  project_type: ProjectType
  preview_port: number
  start_command: string
  backend_start_command?: string
  local_path: string
  created_at: string
}

export interface CreateProjectRequest {
  name: string
  project_type: ProjectType
  repo_url?: string
  start_command?: string
  backend_start_command?: string
}

export interface SandboxAsset {
  name: string
  size: number
  container_path: string
}

export interface ShareInfo {
  token: string
  url: string
}

export interface SharedSandboxInfo {
  repo: string
  app_type: string
}
