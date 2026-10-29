import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { publishedUpdates } from '../api'
import '../styles/updates-strip.css'

/**
 * THE HOME PAGE'S UPDATES STRIP (2026-10-29, Parvathi): the updates a person
 * approved and published on /updates, newest first, in their published words
 * (judge/updates.py published, a public read). Under the hero's chips.
 *
 * A NEWS CRAWL (Parvathi chose it over one headline at a time): the headlines
 * run right to left in an endless line, at a steady reading speed whatever
 * their length. Hovering or focusing it stops it; clicking a headline opens
 * its detail under the strip and holds it still until closed.
 *
 * ACCESSIBLE TWO WAYS. The second copy that makes the loop seamless is hidden
 * from screen readers and the keyboard, so each headline is announced and
 * reached once. A visitor who asked for less motion gets no crawl: one
 * headline at a time with arrows.
 *
 * "NEW" is a headline published since this browser's last visit (stored here
 * only; nothing is sent anywhere). Nothing published: nothing drawn.
 */

const PX_PER_SECOND = 60
const SEEN_KEY = 'mb-ustrip-seen'
const KIND_TONE = { launch: 'info', price_cut: 'pass', price_rise: 'fail', price_change: 'warn', retiring: 'warn', benchmark: 'mute', roundup: 'info' }

const fmtDay = (iso) => new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })

function lastSeen() {
  try {
    return localStorage.getItem(SEEN_KEY)
  } catch {
    return null
  }
}

function useReducedMotion() {
  const query = '(prefers-reduced-motion: reduce)'
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && !!window.matchMedia?.(query).matches)
  useEffect(() => {
    const m = window.matchMedia?.(query)
    if (!m) return undefined
    const on = (e) => setReduced(e.matches)
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [])
  return reduced
}

/** One headline in the line: kind, "New", the headline (a button), its date. */
function Item({ u, isNew, open, onOpen, hidden }) {
  return (
    <span className="ustrip-item" aria-hidden={hidden || undefined}>
      <span className={`badge badge-${KIND_TONE[u.kind] || 'mute'} ustrip-kind`}>{u.label}</span>
      {isNew && <span className="ustrip-new" title="Published since your last visit">New</span>}
      <button type="button" className="ustrip-head" aria-expanded={open} tabIndex={hidden ? -1 : 0}
              onClick={() => onOpen(u.key)} title={open ? 'Hide the detail' : 'Show the detail'}>
        {u.headline}
      </button>
      <time className="ustrip-when" dateTime={u.published_at}>{fmtDay(u.published_at)}</time>
      <span className="ustrip-dot" aria-hidden="true">●</span>
    </span>
  )
}

function Detail({ u }) {
  return (
    <p className="ustrip-detail" id="ustrip-detail">
      <strong>{u.headline}.</strong> {u.detail}
      {u.verify && <span className="ustrip-verify"> A listed price: check it on the provider&apos;s own page before relying on it.</span>}
    </p>
  )
}

export default function UpdatesStrip() {
  const [items, setItems] = useState(null)
  const [openKey, setOpenKey] = useState(null)
  const [at, setAt] = useState(0)
  const [seenBefore] = useState(lastSeen)
  const [duration, setDuration] = useState(30)
  const [reps, setReps] = useState(1)
  const reduced = useReducedMotion()
  const copy = useRef(null)
  const win = useRef(null)

  useEffect(() => {
    publishedUpdates()
      .then((d) => setItems(d.updates || []))
      .catch(() => setItems([])) // the home page never shows an error for this strip
  }, [])

  // This visit counts as seen once the strip has been on screen a moment.
  useEffect(() => {
    if (!items?.length) return undefined
    const t = setTimeout(() => {
      try { localStorage.setItem(SEEN_KEY, new Date().toISOString()) } catch { /* storage blocked */ }
    }, 3000)
    return () => clearTimeout(t)
  }, [items])

  // A copy is the headlines repeated until it is at least as wide as the
  // strip, so one short headline still makes a continuous line. The duration
  // keeps the same reading speed for a short line and a long one.
  // Measured again when the strip changes size (a window resized wider would
  // otherwise show a gap). Nothing to measure yet - hidden, or fonts still
  // loading - leaves it as it is rather than dividing by zero.
  const [width, setWidth] = useState(0)
  useEffect(() => {
    if (!win.current || typeof ResizeObserver === 'undefined') return undefined
    const watch = new ResizeObserver(([e]) => setWidth(Math.round(e.contentRect.width)))
    watch.observe(win.current)
    return () => watch.disconnect()
  }, [items, reduced])
  useLayoutEffect(() => {
    if (!copy.current || !win.current) return
    const one = copy.current.scrollWidth / reps
    if (!one || !win.current.clientWidth) return
    const need = Math.min(50, Math.max(1, Math.ceil(win.current.clientWidth / one)))
    if (need !== reps) setReps(need)
    else setDuration(Math.max(12, copy.current.scrollWidth / PX_PER_SECOND))
  }, [items, reduced, reps, width])

  if (items === null) return <div className="ustrip-strip ustrip-wait" aria-hidden="true" />
  if (!items.length) return null

  const toggle = (key) => setOpenKey((k) => (k === key ? null : key))
  const isNew = (u) => !!seenBefore && u.published_at > seenBefore
  const open = items.find((u) => u.key === openKey)

  if (reduced) {
    const u = items[at]
    const go = (step) => { setOpenKey(null); setAt((i) => (i + step + items.length) % items.length) }
    return (
      <section className="ustrip-strip ustrip-still" aria-label="Latest updates">
        <div className="ustrip-row">
          <span className="ustrip-lab">Latest</span>
          <div className="ustrip-one"><Item u={u} isNew={isNew(u)} open={openKey === u.key} onOpen={toggle} /></div>
          {items.length > 1 && (
            <div className="ustrip-nav">
              <button type="button" className="ustrip-arrow" onClick={() => go(-1)} aria-label="Previous headline">‹</button>
              <span className="ustrip-count" aria-live="polite">{at + 1} / {items.length}</span>
              <button type="button" className="ustrip-arrow" onClick={() => go(1)} aria-label="Next headline">›</button>
            </div>
          )}
        </div>
        {open && <Detail u={open} />}
      </section>
    )
  }

  return (
    <section className="ustrip-strip" aria-label="Latest updates">
      <div className="ustrip-row">
        <span className="ustrip-lab"><span className="ustrip-pulse" aria-hidden="true" />Latest</span>
        <div className={`ustrip-window${open ? ' held' : ''}`} ref={win}>
          <div className="ustrip-track" style={{ animationDuration: `${duration}s` }}>
            {[0, 1].map((half) => (
              // The second half makes the loop seamless; it, and every repeat
              // after the first, is hidden from screen readers and the keyboard.
              <div key={half} className="ustrip-copy" ref={half === 0 ? copy : undefined}
                   aria-hidden={half === 1 || undefined}>
                {Array.from({ length: reps }, (_, r) => items.map((u) => (
                  <Item key={`${r}-${u.key}`} u={u} isNew={isNew(u)} open={openKey === u.key} onOpen={toggle}
                        hidden={half === 1 || r > 0} />
                )))}
              </div>
            ))}
          </div>
        </div>
      </div>
      {open && <Detail u={open} />}
    </section>
  )
}
