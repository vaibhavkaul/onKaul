import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import SharedSandboxView from './components/SharedSandboxView'

const sharedMatch = window.location.pathname.match(/^\/shared\/([^/]+)$/)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {sharedMatch ? <SharedSandboxView token={sharedMatch[1]} /> : <App />}
  </StrictMode>,
)
