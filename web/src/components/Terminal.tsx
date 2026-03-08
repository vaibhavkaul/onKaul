import { FitAddon } from '@xterm/addon-fit'
import { Terminal as XTerm } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'
import { useEffect, useRef } from 'react'

interface Props {
  repo: string
  isRunning: boolean
  wsPath?: string
}

export default function Terminal({ repo, isRunning, wsPath }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isRunning || !containerRef.current) return

    const term = new XTerm({
      theme: {
        background: '#0b0d12',
        foreground: '#e6edf7',
        cursor: '#63e6be',
        cursorAccent: '#0b0d12',
        selectionBackground: 'rgba(99,230,190,0.25)',
        black: '#0b0d12',
        brightBlack: '#5a6a7a',
        white: '#e6edf7',
        brightWhite: '#ffffff',
        cyan: '#63e6be',
        brightCyan: '#4dd4a8',
        blue: '#7c9eff',
        brightBlue: '#93abff',
      },
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: 13,
      lineHeight: 1.4,
      cursorBlink: true,
      scrollback: 5000,
    })

    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(containerRef.current)
    fitAddon.fit()

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const path = wsPath ?? `/sandbox/${repo}/terminal`
    const ws = new WebSocket(`${protocol}//${location.host}${path}`)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      // Send initial terminal dimensions
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
    }

    ws.onmessage = (e) => {
      if (e.data instanceof ArrayBuffer) {
        term.write(new Uint8Array(e.data))
      } else {
        term.write(e.data as string)
      }
    }

    ws.onerror = () => {
      term.write('\r\n\x1b[31m[Connection error]\x1b[0m\r\n')
    }

    ws.onclose = () => {
      term.write('\r\n\x1b[33m[Terminal disconnected]\x1b[0m\r\n')
    }

    const inputDisposable = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(data)
    })

    const resizeDisposable = term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }))
      }
    })

    const ro = new ResizeObserver(() => fitAddon.fit())
    ro.observe(containerRef.current!)

    return () => {
      ro.disconnect()
      inputDisposable.dispose()
      resizeDisposable.dispose()
      ws.close()
      term.dispose()
    }
  }, [repo, isRunning, wsPath])

  return <div ref={containerRef} className="w-full h-full" />
}
