import { useEffect, useRef, useState } from 'react'
import { livePreview } from '../api'
import { fmtCtx, fmtUsd } from '../catalog/format'
import '../styles/blog-live.css'

/**
 * HOVER PREVIEWS (2026-10-15): rest the pointer on a link to a model, a job or
 * a capability, anywhere on the site, and a small card says what is behind it.
 *
 * Wikipedia's 2017-18 A/B tests of the same pattern found readers interacted
 * with 20-22% more distinct pages, and about 0.01% of sessions turned it off
 * (https://www.mediawiki.org/wiki/Page_Previews/2017-18_A/B_Tests).
 *
 * ONE LISTENER FOR THE WHOLE DOCUMENT, so the board's HTML-string views get
 * previews too. Pointer devices only: a touch has no hover, and a card that
 * opened on tap would swallow the tap that was meant to follow the link.
 *
 * Counts include every source, as on the blog's live pages; the sample
 * quotes come only from sources shown publicly.
 */

const ROUTES = [
  [/^\/ai-models\/([^/]+\/.+)$/, 'model'],
  [/^\/models\/([^/]+\/[^/]+)$/, 'model'],
  [/^\/board\/capabilities\/([^/]+)$/, 'cap'],
  [/^\/board\/jobs\/([^/]+)$/, 'job'],
]
const OPEN_MS = 350
const CLOSE_MS = 180
const misses = new Set()

function target(a) {
  let url
  try { url = new URL(a.href, window.location.origin) } catch { return null }
  if (url.origin !== window.location.origin) return null
  for (const [rx, kind] of ROUTES) {
    const m = url.pathname.match(rx)
    if (m) return { kind, id: m[1].split('/').map(decodeURIComponent).join('/') }
  }
  return null
}

function Body({ d }) {
  const none = d.working + d.problems + d.neutral === 0
  const counts = none
    ? <p className="hp-none">No public reports yet.</p>
    : (
      <p className="hp-counts">
        <span className="lv-pos">{d.working} working</span>
        <span className="lv-neg">{d.problems} {d.problems === 1 ? 'problem' : 'problems'}</span>
        {d.neutral > 0 && <span className="lv-neu">{d.neutral} neutral</span>}
        <span className="hp-unit">engineers</span>
      </p>
    )
  if (d.kind === 'model') {
    const price = d.price_in == null && d.price_out == null
      ? 'Price not per token'
      : `${d.price_in == null ? 'not published' : fmtUsd(d.price_in)} in · ${d.price_out == null ? 'not published' : fmtUsd(d.price_out)} out per 1M`
    return (
      <>
        <b className="hp-title">{d.name}</b>
        <p className="hp-meta">{price}{d.context ? ` · ${fmtCtx(d.context)} context` : ''}</p>
        {counts}
        {!none && <p className="hp-meta">across {d.topics} jobs and capabilities</p>}
      </>
    )
  }
  return (
    <>
      <b className="hp-title">{d.name}</b>
      {d.about && <p className="hp-about">{d.about.length > 180 ? `${d.about.slice(0, 180).trimEnd()}…` : d.about}</p>}
      {counts}
      {!none && <p className="hp-meta">across {d.models} {d.models === 1 ? 'model' : 'models'}</p>}
      {d.sample_working && <p className="hp-q hp-q-pos">“{d.sample_working.quote}” <span>{d.sample_working.model}</span></p>}
      {d.sample_problems
        ? <p className="hp-q hp-q-neg">“{d.sample_problems.quote}” <span>{d.sample_problems.model}</span></p>
        : !none && <p className="hp-none">Nobody has reported problems.</p>}
    </>
  )
}

export default function HoverPreview() {
  const [card, setCard] = useState(null) // { d, x, y }
  const timers = useRef({})
  const current = useRef(null)

  useEffect(() => {
    if (!window.matchMedia || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return undefined
    const clear = (k) => { clearTimeout(timers.current[k]); timers.current[k] = null }

    const over = (e) => {
      if (e.target.closest && e.target.closest('.hp-card')) { clear('close'); return }
      const a = e.target.closest && e.target.closest('a[href]')
      if (!a || a === current.current) return
      const t = target(a)
      if (!t || misses.has(`${t.kind}:${t.id}`)) return
      current.current = a
      clear('open'); clear('close')
      timers.current.open = setTimeout(() => {
        livePreview(t.kind, t.id)
          .then((d) => {
            if (current.current !== a) return
            const r = a.getBoundingClientRect()
            const w = 320
            const x = Math.max(12, Math.min(r.left, window.innerWidth - w - 12))
            const below = r.bottom + 8 + 220 < window.innerHeight
            setCard({ d, x, y: below ? r.bottom + 8 : null, bottom: below ? null : window.innerHeight - r.top + 8 })
          })
          .catch(() => misses.add(`${t.kind}:${t.id}`))
      }, OPEN_MS)
    }
    const out = (e) => {
      const a = e.target.closest && e.target.closest('a[href]')
      const card = e.target.closest && e.target.closest('.hp-card')
      if (!a && !card) return
      const to = e.relatedTarget
      if (to && to.closest && (to.closest('.hp-card') || (a && a.contains(to)))) return
      clear('open')
      timers.current.close = setTimeout(() => { current.current = null; setCard(null) }, CLOSE_MS)
    }
    const away = () => { clear('open'); current.current = null; setCard(null) }
    document.addEventListener('mouseover', over)
    document.addEventListener('mouseout', out)
    window.addEventListener('scroll', away, { passive: true })
    document.addEventListener('click', away)
    return () => {
      document.removeEventListener('mouseover', over)
      document.removeEventListener('mouseout', out)
      window.removeEventListener('scroll', away)
      document.removeEventListener('click', away)
      clear('open'); clear('close')
    }
  }, [])

  if (!card) return null
  const style = { left: card.x, ...(card.y != null ? { top: card.y } : { bottom: card.bottom }) }
  return (
    <div className="hp-card" style={style} role="tooltip">
      <Body d={card.d} />
    </div>
  )
}
