import { useCallback, useState } from 'react'
import { createUserProject } from '../api'
import type { ProjectType, UserProject } from '../types'

interface Props {
  onCreated: (project: UserProject) => void
  onClose: () => void
}

const PROJECT_TYPES: { value: ProjectType; label: string; description: string }[] = [
  {
    value: 'static',
    label: 'Static site',
    description: 'HTML, CSS, JS — served instantly with live reload',
  },
  {
    value: 'fullstack-python-vite',
    label: 'Fullstack app',
    description: 'Vite frontend + FastAPI backend — /api/* proxied automatically',
  },
]

const DEFAULT_FRONTEND_CMD = 'npm install && npm run dev -- --host 0.0.0.0 --port ${PREVIEW_PORT:-5173}'
const DEFAULT_BACKEND_CMD = 'python3 -m venv .venv && .venv/bin/pip install --quiet -r requirements.txt && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'

export default function NewProjectModal({ onCreated, onClose }: Props) {
  const [name, setName] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [projectType, setProjectType] = useState<ProjectType>('static')
  const [frontendCmd, setFrontendCmd] = useState(DEFAULT_FRONTEND_CMD)
  const [backendCmd, setBackendCmd] = useState(DEFAULT_BACKEND_CMD)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = useCallback(async () => {
    const trimmedName = name.trim()
    if (!trimmedName) return
    setLoading(true)
    setError(null)
    try {
      const project = await createUserProject({
        name: trimmedName,
        project_type: projectType,
        repo_url: repoUrl.trim() || undefined,
        ...(projectType === 'fullstack-python-vite' && {
          start_command: frontendCmd,
          backend_start_command: backendCmd,
        }),
      })
      onCreated(project)
    } catch (e) {
      setError((e as Error).message)
      setLoading(false)
    }
  }, [name, repoUrl, projectType, frontendCmd, backendCmd, onCreated])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-sidebar border border-border rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-text">New Project</h2>
          <button
            onClick={onClose}
            className="p-1 rounded text-muted hover:text-text hover:bg-border transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">Name</label>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit() }}
              placeholder="My Awesome App"
              className="w-full text-sm bg-surface border border-border rounded-xl px-3.5 py-2.5 text-text placeholder-faint focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Repo URL */}
          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">
              Repository URL
              <span className="ml-1.5 text-faint font-normal">optional</span>
            </label>
            <input
              type="url"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/you/repo"
              className="w-full text-sm bg-surface border border-border rounded-xl px-3.5 py-2.5 text-text placeholder-faint focus:outline-none focus:border-accent transition-colors"
            />
            <p className="mt-1.5 text-[11px] text-faint">
              Leave empty to start from a fresh starter template.
            </p>
          </div>

          {/* Project type */}
          <div>
            <label className="block text-xs font-medium text-muted mb-2">Project type</label>
            <div className="space-y-2">
              {PROJECT_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setProjectType(t.value)}
                  className={`w-full text-left px-4 py-3 rounded-xl border transition-colors ${
                    projectType === t.value
                      ? 'border-accent bg-accent/10 text-text'
                      : 'border-border bg-surface text-muted hover:border-accent/40 hover:text-text'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 transition-colors ${
                        projectType === t.value ? 'border-accent bg-accent' : 'border-muted'
                      }`}
                    />
                    <div>
                      <div className="text-xs font-semibold">{t.label}</div>
                      <div className="text-[11px] text-faint mt-0.5">{t.description}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Fullstack command fields */}
          {projectType === 'fullstack-python-vite' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1.5">Frontend start command</label>
                <input
                  type="text"
                  value={frontendCmd}
                  onChange={(e) => setFrontendCmd(e.target.value)}
                  className="w-full text-xs bg-surface border border-border rounded-xl px-3.5 py-2.5 text-text placeholder-faint focus:outline-none focus:border-accent transition-colors font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1.5">Backend start command</label>
                <input
                  type="text"
                  value={backendCmd}
                  onChange={(e) => setBackendCmd(e.target.value)}
                  className="w-full text-xs bg-surface border border-border rounded-xl px-3.5 py-2.5 text-text placeholder-faint focus:outline-none focus:border-accent transition-colors font-mono"
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-panel">
          <button
            onClick={onClose}
            className="text-sm text-muted hover:text-text px-4 py-2 rounded-xl hover:bg-border transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !name.trim()}
            className="text-sm text-panel bg-accent hover:bg-accent-hover disabled:opacity-60 px-4 py-2 rounded-xl font-semibold transition-colors"
          >
            {loading ? 'Creating…' : 'Create project'}
          </button>
        </div>
      </div>
    </div>
  )
}
