import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

// The ported views emit demo-style links: data-go="kind:slug", data-tab="best",
// and .bm evidence bookmarks. This maps them onto the app's real routes and
// keeps the in-page evidence scroll working.
function goPath(go) {
  const i = go.indexOf(':')
  const kind = i === -1 ? go : go.slice(0, i)
  const arg = i === -1 ? '' : go.slice(i + 1)
  if (kind === 'board') return arg ? `/board?tab=${arg}` : '/board'
  if (kind === 'job') return `/board/jobs/${arg}`
  if (kind === 'cap') return `/board/capabilities/${arg}`
  if (kind === 'metric') return `/board/metrics/${arg}`
  if (kind === 'blogs') return '/blogs'
  if (kind === 'post') return `/blogs/${arg}`
  return '/board'
}

export default function BoardView({ html }) {
  const ref = useRef(null)
  const navigate = useNavigate()

  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }) }, [html])

  function onClick(e) {
    const go = e.target.closest && e.target.closest('[data-go]')
    if (go) { e.preventDefault(); navigate(goPath(go.getAttribute('data-go'))); return }
    const tab = e.target.closest && e.target.closest('[data-tab]')
    if (tab) { e.preventDefault(); navigate(`/board?tab=${tab.getAttribute('data-tab')}`); return }
    const bm = e.target.closest && e.target.closest('.bm')
    if (bm && ref.current) {
      const row = ref.current.querySelector('#ev' + bm.getAttribute('data-ev'))
      if (row) {
        ref.current.querySelectorAll('.evrow').forEach((r) => r.classList.remove('hl'))
        row.classList.add('hl')
        row.scrollIntoView({ block: 'center', behavior: 'smooth' })
      }
    }
  }

  return (
    <div className="bv" ref={ref} onClick={onClick} dangerouslySetInnerHTML={{ __html: html }} />
  )
}
