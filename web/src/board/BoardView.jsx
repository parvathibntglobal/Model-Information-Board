import { useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { goPath } from './links'

// The ported views emit `data-go="kind:arg"` links, `data-tab` tabs and `.bm`
// evidence bookmarks. The route a link means lives in ./links.js, shared with
// the views that write its `href` (SEO item 3), and this keeps the in-page
// evidence scroll working.

export default function BoardView({ html }) {
  const ref = useRef(null)
  const navigate = useNavigate()

  // A new view starts at the top - unless the URL names a heading on it
  // (`#parent-<slug>`), which is how a link opens the board at one group.
  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1))
    const target = id && ref.current?.querySelector(`[id="${CSS.escape(id)}"]`)
    if (target) target.scrollIntoView({ behavior: 'instant', block: 'start' })
    else window.scrollTo({ top: 0, behavior: 'instant' })
  }, [html])

  // FIND-IN-PAGE REVEALS THE TAIL WITHOUT THE BUTTON, so the button has to go
  // then too. `hidden="until-found"` fires `beforematch` when the browser is
  // about to reveal the element; without this the reader is left looking at
  // expanded leaves under a control still offering to expand them.
  useEffect(() => {
    const root = ref.current
    if (!root) return undefined
    const offs = []
    root.querySelectorAll('[data-rest]').forEach((rest) => {
      const onMatch = () => {
        const btn = root.querySelector(`[data-expand="${rest.getAttribute('data-rest')}"]`)
        if (btn) {
          btn.setAttribute('aria-expanded', 'true')
          const row = btn.closest('.leaf-fold')
          if (row) row.remove()
        }
      }
      rest.addEventListener('beforematch', onMatch)
      offs.push(() => rest.removeEventListener('beforematch', onMatch))
    })
    return () => offs.forEach((off) => off())
  }, [html])

  function onClick(e) {
    // THE LEAF FOLD. A heading shows the first few of its leaves and folds the
    // tail; this reveals it. The tail is `hidden="until-found"`, so Ctrl+F can
    // already match inside it and the browser reveals it on its own - this
    // button is for the reader who is looking rather than searching.
    const expand = e.target.closest && e.target.closest('[data-expand]')
    if (expand && ref.current) {
      e.preventDefault()
      const key = expand.getAttribute('data-expand')
      const rest = ref.current.querySelector(`[data-rest="${key}"]`)
      // SET BEFORE REMOVING THE BUTTON. It is true for the instant the button
      // still exists, and a screen reader reading the two in either order gets
      // a consistent answer.
      expand.setAttribute('aria-expanded', 'true')
      if (rest) rest.hidden = false
      // THE BUTTON GOES, rather than becoming "show less". Re-folding a list
      // a reader deliberately opened is a state nobody asked for, and a
      // toggle that can hide evidence is worse than one that cannot.
      const row = expand.closest('.leaf-fold')
      if (row) row.remove()
      return
    }
    const go = e.target.closest && e.target.closest('[data-go]')
    // A MODIFIED CLICK IS THE BROWSER'S (SEO item 3). Every link now has a real
    // href, so Ctrl/Cmd/Shift/Alt-click opens it in a new tab or window the
    // way any link does; only a plain click becomes in-app navigation.
    // (Middle-click never reaches here - it fires `auxclick`, not `click`.)
    if (go && (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button !== 0)) return
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
    // AN ESSAY'S CONTENTS LIST. Scrolls in place rather than using `#hash`
    // links, which would rewrite the app's URL and fight the router.
    const toc = e.target.closest && e.target.closest('[data-toc]')
    if (toc && ref.current) {
      e.preventDefault()
      const target = ref.current.querySelector('#' + CSS.escape(toc.getAttribute('data-toc')))
      if (target) target.scrollIntoView({ block: 'start', behavior: 'smooth' })
      return
    }
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

  // ONE OBJECT PER STRING. Measured 2026-10-14 on React 19.2: a re-render with
  // the SAME html and a fresh `{ __html }` object rewrote the DOM anyway, which
  // wiped the Reddit and X embeds their scripts had already drawn - and nothing
  // redrew them, because nothing had changed. A post opened directly lost every
  // embed ~8 s in, when a slow /seo/indexable answer re-rendered the page.
  const inner = useMemo(() => ({ __html: html }), [html])

  return (
    <div className="bv" ref={ref} onClick={onClick} dangerouslySetInnerHTML={inner} />
  )
}
