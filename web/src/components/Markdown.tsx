import { useState, type ComponentPropsWithoutRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Clipboard API is unavailable on plain http or when permission is denied.
    const el = document.createElement('textarea')
    el.value = text
    el.style.position = 'fixed'
    el.style.opacity = '0'
    document.body.appendChild(el)
    el.select()
    const ok = document.execCommand('copy')
    el.remove()
    return ok
  }
}

function CodeBlock({
  children,
  node: _node,
  ...props
}: ComponentPropsWithoutRef<'pre'> & { node?: unknown }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')

  async function onCopy(e: React.MouseEvent<HTMLButtonElement>) {
    const code = e.currentTarget.parentElement?.querySelector('code')?.innerText ?? ''
    setState((await copyText(code)) ? 'copied' : 'failed')
    setTimeout(() => setState('idle'), 1500)
  }

  return (
    <div className="relative group">
      <pre {...props}>{children}</pre>
      <button
        type="button"
        onClick={onCopy}
        className="absolute top-2 right-2 text-[11px] px-2 py-0.5 rounded-md border border-border bg-panel text-muted hover:text-text opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
      >
        {state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : 'Copy'}
      </button>
    </div>
  )
}

export default function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        pre: CodeBlock,
        a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
        table: ({ node: _node, ...props }) => (
          <div className="overflow-x-auto">
            <table {...props} />
          </div>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  )
}
