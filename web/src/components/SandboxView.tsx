import { useCallback, useEffect, useRef, useState } from 'react'
import { deleteAsset, getGitInfo, getSandboxStatus, linkSandboxRepo, listAssets, pushSandboxPR, resetSandbox, startSandbox, stopSandbox, uploadAsset } from '../api'
import type { GitInfo, PushResult, SandboxAsset, SandboxRepo, SandboxStatus } from '../types'
import Terminal from './Terminal'

const PREVIEW_NATURAL_WIDTH = 1280

interface Props {
  repo: SandboxRepo
  onClose: () => void
}

export default function SandboxView({ repo, onClose }: Props) {
  const [status, setStatus] = useState<SandboxStatus>({ status: 'stopped' })
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const previewWrapRef = useRef<HTMLDivElement>(null)
  const [previewScale, setPreviewScale] = useState(1)

  // Assets state
  const [showAssets, setShowAssets] = useState(false)
  const [assets, setAssets] = useState<SandboxAsset[]>([])
  const [uploading, setUploading] = useState(false)
  const [copiedPath, setCopiedPath] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Split / terminal visibility
  const [terminalVisible, setTerminalVisible] = useState(true)
  const [splitPercent, setSplitPercent] = useState(50)
  const [isDraggingDivider, setIsDraggingDivider] = useState(false)
  const splitContainerRef = useRef<HTMLDivElement>(null)
  const isDragging = useRef(false)

  // Git state
  const [gitInfo, setGitInfo] = useState<GitInfo | null>(null)
  const [resetConfirm, setResetConfirm] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [showPushForm, setShowPushForm] = useState(false)
  const [prTitle, setPrTitle] = useState('')
  const [pushing, setPushing] = useState(false)
  const [pushResult, setPushResult] = useState<PushResult | null>(null)
  const [showLinkForm, setShowLinkForm] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')
  const [linking, setLinking] = useState(false)

  const isRunning = status.status === 'running'

  useEffect(() => {
    getSandboxStatus(repo.key).then(setStatus)
  }, [repo.key])

  // Refresh git info whenever running
  const refreshGitInfo = useCallback(() => {
    if (isRunning) getGitInfo(repo.key).then(setGitInfo)
  }, [isRunning, repo.key])

  useEffect(() => {
    if (!isRunning) { setGitInfo(null); return }
    refreshGitInfo()
    const id = setInterval(refreshGitInfo, 5000)
    return () => clearInterval(id)
  }, [isRunning, refreshGitInfo])

  useEffect(() => {
    const el = previewWrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      setPreviewScale(el.clientWidth / PREVIEW_NATURAL_WIDTH)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [isRunning])

  // Hot reload: watch for file changes via SSE and reload the preview iframe
  useEffect(() => {
    if (!isRunning) return
    const es = new EventSource(`/sandbox/${repo.key}/watch`)
    let timer: ReturnType<typeof setTimeout> | null = null
    es.onmessage = (e) => {
      if (e.data !== 'reload') return
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        if (iframeRef.current) {
          // eslint-disable-next-line no-self-assign
          iframeRef.current.src = iframeRef.current.src
        }
        refreshGitInfo()
      }, 500)
    }
    return () => {
      es.close()
      if (timer) clearTimeout(timer)
    }
  }, [isRunning, repo.key, refreshGitInfo])

  const handleStart = useCallback(async () => {
    setStarting(true)
    setError(null)
    try {
      const s = await startSandbox(repo.key)
      setStatus(s)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setStarting(false)
    }
  }, [repo.key])

  const handleStop = useCallback(async () => {
    await stopSandbox(repo.key)
    setStatus({ status: 'stopped' })
    setGitInfo(null)
    setPushResult(null)
    setShowPushForm(false)
    setResetConfirm(false)
  }, [repo.key])

  const refreshAssets = useCallback(() => {
    if (isRunning) listAssets(repo.key).then(setAssets)
  }, [isRunning, repo.key])

  useEffect(() => {
    if (showAssets) refreshAssets()
  }, [showAssets, refreshAssets])

  const handleUploadFiles = useCallback(async (files: FileList | File[]) => {
    setUploading(true)
    try {
      for (const f of Array.from(files)) {
        await uploadAsset(repo.key, f)
      }
      refreshAssets()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setUploading(false)
    }
  }, [repo.key, refreshAssets])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    ;(e.currentTarget as HTMLElement).blur()
    if (e.dataTransfer.files.length) handleUploadFiles(e.dataTransfer.files)
  }, [handleUploadFiles])

  const handleDeleteAsset = useCallback(async (name: string) => {
    await deleteAsset(repo.key, name)
    refreshAssets()
  }, [repo.key, refreshAssets])

  const handleCopyPath = useCallback((path: string) => {
    navigator.clipboard.writeText(path)
    setCopiedPath(path)
    setTimeout(() => setCopiedPath(null), 1500)
  }, [])

  const handleDividerMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    setIsDraggingDivider(true)
    const container = splitContainerRef.current
    if (!container) return
    const onMove = (ev: MouseEvent) => {
      if (!isDragging.current) return
      const rect = container.getBoundingClientRect()
      const pct = ((ev.clientX - rect.left) / rect.width) * 100
      setSplitPercent(Math.min(80, Math.max(20, pct)))
    }
    const onUp = () => {
      isDragging.current = false
      setIsDraggingDivider(false)
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [])

  const reloadPreview = useCallback(() => {
    if (iframeRef.current) {
      // eslint-disable-next-line no-self-assign
      iframeRef.current.src = iframeRef.current.src
    }
  }, [])

  const handleReset = useCallback(async () => {
    setResetting(true)
    setError(null)
    try {
      await resetSandbox(repo.key)
      setResetConfirm(false)
      refreshGitInfo()
      reloadPreview()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setResetting(false)
    }
  }, [repo.key, refreshGitInfo, reloadPreview])

  const handlePush = useCallback(async () => {
    if (!prTitle.trim()) return
    setPushing(true)
    setError(null)
    try {
      const result = await pushSandboxPR(repo.key, prTitle.trim(), prTitle.trim())
      setPushResult(result)
      setShowPushForm(false)
      refreshGitInfo()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setPushing(false)
    }
  }, [repo.key, prTitle, refreshGitInfo])

  const handleLink = useCallback(async () => {
    if (!linkUrl.trim()) return
    setLinking(true)
    setError(null)
    try {
      await linkSandboxRepo(repo.key, linkUrl.trim())
      setShowLinkForm(false)
      setLinkUrl('')
      refreshGitInfo()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLinking(false)
    }
  }, [repo.key, linkUrl, refreshGitInfo])

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-surface">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border bg-sidebar flex-shrink-0">
        {/* Back */}
        <button
          onClick={onClose}
          className="p-1 rounded text-muted hover:text-text hover:bg-border transition-colors"
          title="Back to chat"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Repo name + branch + status */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-sm font-semibold text-text truncate">{repo.name}</span>
          <span className="text-[10px] text-muted font-mono">({repo.org})</span>

          {gitInfo && (
            <span className="flex items-center gap-1 text-[10px] text-sky font-mono bg-sky/10 px-1.5 py-0.5 rounded-full border border-sky/20 flex-shrink-0">
              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              {gitInfo.branch}
              {gitInfo.has_changes && (
                <span className="ml-0.5 text-amber-400">·{gitInfo.changed_count}</span>
              )}
            </span>
          )}

          <span
            className={`flex-shrink-0 flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium border ${
              isRunning
                ? 'bg-accent/10 text-accent border-accent/20'
                : 'bg-border/50 text-muted border-border'
            }`}
          >
            {isRunning && (
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse inline-block" />
            )}
            {isRunning ? 'Running' : 'Stopped'}
          </span>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isRunning ? (
            <>
<button
                onClick={() => setShowAssets((v) => !v)}
                className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors ${
                  showAssets
                    ? 'text-accent bg-accent/10 border-accent/30'
                    : 'text-muted hover:text-text hover:bg-border border-border'
                }`}
                title="Upload assets"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Assets
              </button>

              {/* Push PR / Link repo */}
              {gitInfo?.has_remote !== true ? (
                repo.org === '' && (
                  <button
                    onClick={() => { setShowLinkForm((v) => !v); setResetConfirm(false); setShowPushForm(false) }}
                    className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors ${
                      showLinkForm
                        ? 'text-accent bg-accent/10 border-accent/30'
                        : 'text-muted hover:text-text hover:bg-border border-border'
                    }`}
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    Link repo
                  </button>
                )
              ) : pushResult ? (
                <a
                  href={pushResult.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover px-2.5 py-1.5 rounded-lg hover:bg-accent/10 border border-accent/20 transition-colors"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  View PR
                </a>
              ) : (
                <button
                  onClick={() => { setShowPushForm((v) => !v); setResetConfirm(false) }}
                  className="flex items-center gap-1.5 text-xs text-sky hover:text-sky/80 px-2.5 py-1.5 rounded-lg hover:bg-sky/10 border border-sky/20 transition-colors"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                  </svg>
                  Push PR
                </button>
              )}

              {/* Reset button / confirm */}
              {resetConfirm ? (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={handleReset}
                    disabled={resetting}
                    className="text-xs text-red-400 hover:text-red-300 px-2.5 py-1.5 rounded-lg bg-red-500/10 border border-red-500/30 transition-colors disabled:opacity-60"
                  >
                    {resetting ? 'Resetting…' : 'Confirm reset'}
                  </button>
                  <button
                    onClick={() => setResetConfirm(false)}
                    className="text-xs text-muted hover:text-text px-2 py-1.5 rounded-lg hover:bg-border transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => { setResetConfirm(true); setShowPushForm(false) }}
                  className="flex items-center gap-1.5 text-xs text-muted hover:text-red-400 px-2.5 py-1.5 rounded-lg hover:bg-red-500/10 border border-border hover:border-red-500/20 transition-colors"
                  title="Reset to last commit"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Reset
                </button>
              )}

              <button
                onClick={reloadPreview}
                className="flex items-center gap-1.5 text-xs text-muted hover:text-text px-2.5 py-1.5 rounded-lg hover:bg-border border border-border transition-colors"
                title="Reload preview"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Reload
              </button>

              <button
                onClick={handleStop}
                className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 px-2.5 py-1.5 rounded-lg hover:bg-red-500/10 border border-red-500/20 transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Stop
              </button>
            </>
          ) : (
            <button
              onClick={handleStart}
              disabled={starting}
              className="flex items-center gap-1.5 text-xs text-panel bg-accent hover:bg-accent-hover disabled:opacity-60 px-3 py-1.5 rounded-lg font-semibold transition-colors"
            >
              {starting ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
                  </svg>
                  Starting…
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Start Sandbox
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Link repo form */}
      {showLinkForm && (
        <div className="px-4 py-2.5 border-b border-border bg-panel flex items-center gap-3 flex-shrink-0">
          <span className="text-xs text-muted flex-shrink-0">GitHub repo URL:</span>
          <input
            autoFocus
            type="url"
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleLink(); if (e.key === 'Escape') setShowLinkForm(false) }}
            placeholder="https://github.com/org/repo"
            className="flex-1 text-xs bg-surface border border-border rounded-lg px-3 py-1.5 text-text placeholder-faint focus:outline-none focus:border-accent"
          />
          <button
            onClick={handleLink}
            disabled={linking || !linkUrl.trim()}
            className="text-xs text-panel bg-accent hover:bg-accent-hover disabled:opacity-60 px-3 py-1.5 rounded-lg font-semibold transition-colors flex-shrink-0"
          >
            {linking ? 'Linking…' : 'Link'}
          </button>
          <button
            onClick={() => setShowLinkForm(false)}
            className="text-xs text-muted hover:text-text px-2 py-1.5 rounded-lg hover:bg-border transition-colors flex-shrink-0"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Push PR form */}
      {showPushForm && (
        <div className="px-4 py-2.5 border-b border-border bg-panel flex items-center gap-3 flex-shrink-0">
          <span className="text-xs text-muted flex-shrink-0">PR title:</span>
          <input
            autoFocus
            type="text"
            value={prTitle}
            onChange={(e) => setPrTitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handlePush(); if (e.key === 'Escape') setShowPushForm(false) }}
            placeholder="Describe your changes…"
            className="flex-1 text-xs bg-surface border border-border rounded-lg px-3 py-1.5 text-text placeholder-faint focus:outline-none focus:border-accent"
          />
          <button
            onClick={handlePush}
            disabled={pushing || !prTitle.trim()}
            className="text-xs text-panel bg-accent hover:bg-accent-hover disabled:opacity-60 px-3 py-1.5 rounded-lg font-semibold transition-colors flex-shrink-0"
          >
            {pushing ? 'Creating PR…' : 'Create PR'}
          </button>
          <button
            onClick={() => setShowPushForm(false)}
            className="text-xs text-muted hover:text-text px-2 py-1.5 rounded-lg hover:bg-border transition-colors flex-shrink-0"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Assets panel */}
      {showAssets && isRunning && (
        <div className="border-b border-border bg-panel flex-shrink-0 max-h-64 overflow-y-auto">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="px-4 pt-3 pb-2"
          >
            {/* Drop zone / upload trigger */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-border hover:border-accent rounded-lg px-4 py-3 text-center cursor-pointer transition-colors group"
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => {
                if (e.target.files) handleUploadFiles(e.target.files)
                e.target.value = ''
                e.target.blur()
              }}
              />
              {uploading ? (
                <p className="text-xs text-muted">Uploading…</p>
              ) : (
                <p className="text-xs text-faint group-hover:text-muted transition-colors">
                  <span className="text-accent font-medium">Click to upload</span> or drag files here
                  <span className="block text-[11px] mt-0.5">Images, SVGs, fonts, JSON — up to 20 MB each</span>
                </p>
              )}
            </div>

            {/* File list */}
            {assets.length > 0 && (
              <div className="mt-2 space-y-1">
                {assets.map((a) => (
                  <div key={a.name} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-border">
                    <svg className="w-3.5 h-3.5 text-faint flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-xs text-text truncate flex-1 font-mono">{a.name}</span>
                    <span className="text-[11px] text-faint flex-shrink-0">{(a.size / 1024).toFixed(1)} KB</span>
                    <button
                      onClick={() => handleCopyPath(a.container_path)}
                      title="Copy path for Claude"
                      className="flex-shrink-0 px-1.5 py-0.5 rounded text-[11px] font-mono border border-border hover:border-accent hover:text-accent text-faint transition-colors"
                    >
                      {copiedPath === a.container_path ? 'copied!' : 'copy path'}
                    </button>
                    <button
                      onClick={() => handleDeleteAsset(a.name)}
                      title="Delete asset"
                      className="flex-shrink-0 p-1 rounded hover:bg-red-500/10 hover:text-red-400 text-faint transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
            {assets.length === 0 && !uploading && (
              <p className="text-[11px] text-faint text-center mt-2 pb-1">
                Uploaded files appear here — reference them in Claude as <code className="text-sky font-mono">tmp-assets/filename</code>
              </p>
            )}
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs flex items-center gap-2">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {/* Main content */}
      {isRunning ? (
        <div ref={splitContainerRef} className="flex-1 flex overflow-hidden">
          {/* Left pane: Preview */}
          <div
            className="flex flex-col min-w-0"
            style={{ width: terminalVisible ? `${splitPercent}%` : '100%' }}
          >
            <div className="px-3 py-1.5 text-[11px] text-faint font-mono bg-panel border-b border-border flex items-center justify-between flex-shrink-0">
              <span>preview — {repo.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-faint/60">
                  {repo.sandbox.appType === 'fullstack-python-vite'
                    ? 'Vite + FastAPI'
                    : `port ${repo.sandbox.previewPort}`}
                </span>
                <button
                  onClick={() => setTerminalVisible((v) => !v)}
                  title={terminalVisible ? 'Hide terminal' : 'Show terminal'}
                  className="ml-1 p-0.5 rounded hover:bg-border text-faint hover:text-muted transition-colors"
                >
                  {terminalVisible ? (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                    </svg>
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            <div ref={previewWrapRef} className="flex-1 overflow-hidden relative bg-white">
              <iframe
                ref={iframeRef}
                src={`/sandbox/${repo.key}/preview/`}
                style={{
                  width: `${PREVIEW_NATURAL_WIDTH}px`,
                  height: previewScale > 0 ? `${100 / previewScale}%` : '100%',
                  transform: `scale(${previewScale})`,
                  transformOrigin: 'top left',
                  border: 'none',
                }}
                title={`${repo.name} preview`}
                sandbox="allow-scripts allow-same-origin allow-forms"
              />
              {/* Transparent cover prevents iframe from swallowing mouse events during divider drag */}
              {isDraggingDivider && (
                <div className="absolute inset-0 z-10 cursor-col-resize" />
              )}
            </div>
          </div>

          {/* Draggable divider — hidden when terminal is not visible */}
          <div
            onMouseDown={handleDividerMouseDown}
            className={`w-1.5 flex-shrink-0 bg-border hover:bg-accent/60 active:bg-accent cursor-col-resize transition-colors ${terminalVisible ? '' : 'hidden'}`}
            title="Drag to resize"
          />

          {/* Right pane: Terminal — always mounted to keep session alive, hidden via CSS */}
          <div
            className="flex flex-col flex-shrink-0 min-w-0"
            style={{ width: terminalVisible ? `${100 - splitPercent}%` : '0%', overflow: 'hidden' }}
          >
            <div className={`px-3 py-1.5 text-[11px] text-faint font-mono bg-panel border-b border-border flex items-center gap-2 flex-shrink-0 ${terminalVisible ? '' : 'hidden'}`}>
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              <span className="flex-1">terminal — type <span className="text-accent">claude</span> to start coding</span>
              <button
                onClick={() => setTerminalVisible(false)}
                className="text-[11px] text-faint hover:text-muted px-1.5 py-0.5 rounded hover:bg-border transition-colors"
              >
                hide
              </button>
            </div>
            <div className="flex-1 overflow-hidden p-1 bg-surface">
              <Terminal repo={repo.key} isRunning={isRunning} />
            </div>
          </div>
        </div>
      ) : (
        /* Not-started state */
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-8">
          <div className="w-16 h-16 rounded-2xl bg-panel border border-border flex items-center justify-center">
            <svg className="w-8 h-8 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-text mb-1">{repo.name}</p>
            <p className="text-xs text-muted max-w-xs leading-relaxed">
              Start the sandbox to get a live preview and terminal with Claude Code ready to edit.
            </p>
          </div>
          <button
            onClick={handleStart}
            disabled={starting}
            className="flex items-center gap-2 text-sm text-panel bg-accent hover:bg-accent-hover disabled:opacity-60 px-4 py-2 rounded-xl font-semibold transition-colors"
          >
            {starting ? 'Starting…' : 'Start Sandbox'}
          </button>
          <p className="text-[11px] text-faint">
            Spins up a Docker container with the repo cloned and Claude Code installed.
          </p>
        </div>
      )}
    </div>
  )
}
