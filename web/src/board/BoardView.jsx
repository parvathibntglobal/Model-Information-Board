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
  // THE DRILL-DOWN, and the arg is two things: `slug:modelKey`. Split on the
  // FIRST colon only, because a model key can contain one - and it can contain
  // a slash too (`model_version.id` is canonical for 166 of 1,249 board rows),
  // which is why it goes last in the path and `Board.jsx` rejoins the tail.
  if (kind === 'jobmodel' || kind === 'capmodel' || kind === 'metmodel') {
    const j = arg.indexOf(':')
    const seg = kind === 'jobmodel' ? 'jobs' : kind === 'capmodel' ? 'capabilities' : 'metrics'
    return j === -1 ? `/board/${seg}` : `/board/${seg}/${arg.slice(0, j)}/${arg.slice(j + 1)}`
  }
  // Out to the model's own page, which holds every section rather than one.
  // `state.from` is what sends its back-link here instead of to /models.
  if (kind === 'model') return `/models/${arg}`
  if (kind === 'blogs') return '/blogs'
  if (kind === 'post') return `/blogs/${arg}`
  return '/board'
}

export default function BoardView({ html }) {
  const ref = useRef(null)
  const navigate = useNavigate()

  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }) }, [html])

  function onClick(e) {
    // THE LEAF FOLD. A heading shows the first few of its leaves and folds the
    // tail; this reveals it. The tail is in the DOM either way - hidden by an
    // attribute, not dropped - so find, screen readers and a JS-less render
    // all see every leaf. This only moves the eye.
    const expand = e.target.closest && e.target.closest('[data-expand]')
    if (expand && ref.current) {
      e.preventDefault()
      const key = expand.getAttribute('data-expand')
      const rest = ref.current.querySelector(`[data-rest="${key}"]`)
      if (rest) rest.hidden = false
      // THE BUTTON GOES, rather than becoming "show less". Re-folding a list
      // a reader deliberately opened is a state nobody asked for, and a
      // toggle that can hide evidence is worse than one that cannot.
      const row = expand.closest('.leaf-fold')
      if (row) row.remove()
      return
    }
    const go = e.target.closest && e.target.closest('[data-go]')
    if (go) {
      e.preventDefault()
      const path = goPath(go.getAttribute('data-go'))
      // `from` so the model page's back link returns to the board rather than
      // to /models - ModelDetail already reads it, and a visitor who arrived
      // from a drill-down should not be handed the roster on the way out.
      navigate(path, path.startsWith('/models/') ? { state: { from: '/board' } } : undefined)
      return
    }
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
