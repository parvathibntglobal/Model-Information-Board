import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * The landing page's search: a model, a job, a capability or a metric, by name.
 *
 * THE INDEX IS THE BOARD ITSELF, read from the same `/board` payload the
 * landing already holds - every section with its report count, and every model
 * named in any section. Nothing is typed in here, so the box can only suggest
 * pages that exist and models the board has evidence about.
 *
 * Matching is plain: every word typed must appear in the name. Names that start
 * with the query come first, then by report count - a count, not a score; it
 * only orders the suggestions.
 *
 * The placeholder is the same before and after the board loads: a query typed
 * early simply waits, and its suggestions appear once the board is read.
 *
 * Keyboard: arrows move, Enter opens the highlighted (or first) suggestion,
 * Escape closes. Built as an ARIA combobox so a screen reader hears the list.
 */

const KINDS = [
  ['jobs', 'Job', 'jobs'],
  ['caps', 'Capability', 'capabilities'],
  ['mets', 'Metric', 'metrics'],
]
const LIMIT = 8

const shortLabel = (label) => (label && label.includes(': ') ? label.split(': ').slice(1).join(': ') : label || '')

function buildIndex(board) {
  if (!board) return []
  const out = []
  const models = new Map()
  for (const [key, kind, route] of KINDS) {
    for (const s of board[key] || []) {
      out.push({ kind, name: s.name || s.slug, to: `/board/${route}/${s.slug}`, n: s.reports || 0, unit: 'report' })
      for (const m of s.models || []) {
        const name = shortLabel(m.model_label)
        if (!name || !m.model_key) continue
        const prev = models.get(name)
        if (prev) prev.n += 1
        else models.set(name, { kind: 'Model', name, to: `/models/${m.model_key}`, n: 1, unit: 'section' })
      }
    }
  }
  return [...models.values(), ...out]
}

function match(index, q) {
  const words = q.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return []
  const hits = index.filter((it) => {
    const name = it.name.toLowerCase()
    return words.every((w) => name.includes(w))
  })
  const head = q.trim().toLowerCase()
  hits.sort((a, b) => {
    const as = a.name.toLowerCase().startsWith(head) ? 0 : 1
    const bs = b.name.toLowerCase().startsWith(head) ? 0 : 1
    return as - bs || b.n - a.n || a.name.localeCompare(b.name)
  })
  return hits.slice(0, LIMIT)
}

export default function SiteSearch({ board }) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const navigate = useNavigate()
  const box = useRef(null)
  const index = useMemo(() => buildIndex(board), [board])
  const results = useMemo(() => match(index, q), [index, q])
  const listId = 'site-search-list'

  const go = (it) => {
    if (!it) return
    setOpen(false)
    navigate(it.to)
  }

  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); go(results[active] || results[0]) }
    else if (e.key === 'Escape') { setOpen(false) }
  }

  const showList = open && q.trim() && board
  return (
    <div className="site-search" ref={box}
         onBlur={(e) => { if (!box.current?.contains(e.relatedTarget)) setOpen(false) }}>
      <label htmlFor="site-search-input" className="sr-only">Search the board</label>
      <svg className="site-search-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <input
        id="site-search-input"
        type="search"
        role="combobox"
        aria-expanded={Boolean(showList)}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && results[active] ? `site-search-opt-${active}` : undefined}
        autoComplete="off"
        placeholder="Search a model, job, capability or metric — e.g. Claude, coding agents, context window"
        value={q}
        onChange={(e) => { setQ(e.target.value); setActive(0); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKey}
      />
      {showList && (
        <ul className="site-search-list" id={listId} role="listbox">
          {results.length ? results.map((it, i) => (
            <li
              key={it.kind + it.to}
              id={`site-search-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'on' : ''}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => { e.preventDefault(); go(it) }}
            >
              <span className="site-search-kind">{it.kind}</span>
              <span className="site-search-name">{it.name}</span>
              <span className="site-search-n tnum">{it.n} {it.unit}{it.n === 1 ? '' : 's'}</span>
            </li>
          )) : (
            <li className="site-search-none" role="option" aria-selected="false">
              Nothing on the board by that name yet.
            </li>
          )}
        </ul>
      )}
    </div>
  )
}
