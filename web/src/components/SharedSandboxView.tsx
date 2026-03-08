import { useEffect, useRef, useState } from 'react'
import { getSharedSandboxInfo } from '../api'
import Terminal from './Terminal'

const PREVIEW_NATURAL_WIDTH = 1280

interface Props {
  token: string
}

export default function SharedSandboxView({ token }: Props) {
  const [repoName, setRepoName] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const previewWrapRef = useRef<HTMLDivElement>(null)
  const [previewScale, setPreviewScale] = useState(1)
  const [terminalVisible, setTerminalVisible] = useState(true)
  const [splitPercent, setSplitPercent] = useState(50)
  const isDragging = useRef(false)
  const splitContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getSharedSandboxInfo(token).then((info) => {
      if (!info) {
        setError('Share link not found or the sandbox is not running.')
      } else {
        setRepoName(info.repo)
      }
    })
  }, [token])

  useEffect(() => {
    if (!repoName) return
    const es = new EventSource(`/sandbox/shared/${token}/watch`)
    let timer: ReturnType<typeof setTimeout> | null = null
    es.onmessage = (e) => {
      if (e.data !== 'reload') return
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        if (iframeRef.current) {
          // eslint-disable-next-line no-self-assign
          iframeRef.current.src = iframeRef.current.src
        }
      }, 500)
    }
    return () => {
      es.close()
      if (timer) clearTimeout(timer)
    }
  }, [repoName, token])

  useEffect(() => {
    const el = previewWrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      setPreviewScale(el.clientWidth / PREVIEW_NATURAL_WIDTH)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [repoName])

  const onDividerMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    const onMove = (ev: MouseEvent) => {
      if (!isDragging.current || !splitContainerRef.current) return
      const rect = splitContainerRef.current.getBoundingClientRect()
      const pct = Math.min(90, Math.max(10, ((ev.clientX - rect.left) / rect.width) * 100))
      setSplitPercent(pct)
    }
    const onUp = () => { isDragging.current = false; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface text-text">
        <div className="text-center space-y-3">
          <p className="text-lg font-semibold">Sandbox unavailable</p>
          <p className="text-sm text-muted">{error}</p>
        </div>
      </div>
    )
  }

  if (!repoName) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface text-muted text-sm">
        Loading shared sandbox…
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-surface overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border bg-panel flex-shrink-0">
        <span className="text-xs font-semibold text-text">{repoName}</span>
        <span className="text-xs text-muted bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">shared</span>
        <div className="flex-1" />
        <button
          onClick={() => setTerminalVisible((v) => !v)}
          className="text-xs text-muted hover:text-text px-2.5 py-1.5 rounded-lg hover:bg-border border border-border transition-colors"
        >
          {terminalVisible ? 'Hide terminal' : 'Show terminal'}
        </button>
      </div>

      {/* Split panes */}
      <div ref={splitContainerRef} className="flex flex-1 overflow-hidden">
        {/* Preview */}
        <div ref={previewWrapRef} className="relative overflow-hidden flex-shrink-0 h-full bg-white" style={{ width: terminalVisible ? `${splitPercent}%` : '100%' }}>
          <iframe
            ref={iframeRef}
            src={`/sandbox/shared/${token}/preview/`}
            title="Preview"
            style={{
              width: PREVIEW_NATURAL_WIDTH,
              height: previewScale > 0 ? `${100 / previewScale}%` : '100%',
              border: 'none',
              transformOrigin: 'top left',
              transform: `scale(${previewScale})`,
            }}
          />
        </div>

        {/* Divider */}
        {terminalVisible && (
          <div
            onMouseDown={onDividerMouseDown}
            className="w-1 bg-border hover:bg-accent cursor-col-resize flex-shrink-0 transition-colors"
          />
        )}

        {/* Terminal */}
        {terminalVisible && (
          <div className="flex flex-col flex-1 overflow-hidden bg-[#0b0d12]">
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-border flex-shrink-0">
              <span className="text-xs text-muted font-mono">terminal (shared)</span>
              <button onClick={() => setTerminalVisible(false)} className="text-xs text-muted hover:text-text transition-colors">✕</button>
            </div>
            <div className="flex-1 overflow-hidden">
              <Terminal repo={repoName} isRunning={true} wsPath={`/sandbox/shared/${token}/terminal`} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
