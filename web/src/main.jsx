import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import './styles/fonts.css'
import './styles/app.css'
import './styles/board.css'
import './styles/token-counter.css'
import './styles/vram.css'
import './styles/reports.css'
import './styles/picker.css'
import App from './App'

/**
 * A PRE-RENDERED PAGE STARTS WITH ITS OWN HEAD (web/prerender.js). head.js
 * reads the document's head at start as the defaults it restores on leaving a
 * page, so the shell's head is put back first, from the JSON prerender.js
 * left, and the saved JSON-LD is removed: the page writes its own again. The
 * saved body is replaced by createRoot's first render.
 */
function restoreShellHead() {
  const el = document.getElementById('shell-head')
  if (!el) return
  let h
  try { h = JSON.parse(el.textContent) } catch { return }
  el.remove()
  document.head.querySelectorAll('script[data-prerendered]').forEach((s) => s.remove())
  document.title = h.title || ''
  const put = (sel, attr, name, value) => {
    let m = document.head.querySelector(sel)
    if (value == null) { m?.remove(); return }
    if (!m) { m = document.createElement('meta'); m.setAttribute(attr, name); document.head.appendChild(m) }
    m.setAttribute('content', value)
  }
  put('meta[name="description"]', 'name', 'description', h.description)
  put('meta[name="robots"]', 'name', 'robots', h.robots)
  put('meta[property="og:title"]', 'property', 'og:title', h.ogTitle)
  put('meta[property="og:description"]', 'property', 'og:description', h.ogDescription)
  put('meta[property="og:url"]', 'property', 'og:url', h.ogUrl)
  const link = document.head.querySelector('link[rel="canonical"]')
  if (h.canonical == null) link?.remove()
  else if (link) link.setAttribute('href', h.canonical)
}
restoreShellHead()

// The single-file build has no server to rewrite paths, so it routes on the hash.
const Router = import.meta.env.VITE_HASH_ROUTER ? HashRouter : BrowserRouter

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Router>
      <App />
    </Router>
  </StrictMode>
)
