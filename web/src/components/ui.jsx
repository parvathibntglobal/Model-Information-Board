import { useEffect, useRef, useState } from 'react'

/* ---------------------------------------------------------------- primitives */

export function Badge({ tone = 'mute', children, ...rest }) {
  return <span className={`badge badge-${tone}`} {...rest}>{children}</span>
}

export function Stat({ n, l, title }) {
  // `title` IS OPTIONAL AND CARRIES THE POPULATION. A figure's denominator has
  // to be reachable (rule 7), but printing it under every stat on every render
  // turns a caveat into wallpaper. On hover it stays available without being
  // recited - see UsagePanel's machine list, which used to be a sentence.
  return (
    <div className="stat" title={title || undefined}>
      <span className="stat-n tnum">{n}</span>
      <span className="stat-l">{l}</span>
    </div>
  )
}

// `Chip`, `Label`, `BandHead` and `Meter` lived here with no caller. Three were
// merely unused; `Meter` was worth deleting rather than keeping.
//
// It drew a 0-1 bar from a `value` prop with no counted quantity behind it —
// a filled bar IS a score, and rule 3 says no synthesised number reaches a
// page. It sat one import away from being wired up by someone reaching for
// "show consensus visually", and the comment above it called itself a reading
// aid, so nothing would have flagged it. The counts it was meant to illustrate
// already render as words.

export function Notice({ icon, children }) {
  return (
    <div className="notice">
      {icon && <span style={{ flex: 'none', marginTop: 2, color: 'var(--text-3)' }}>{icon}</span>}
      <div>{children}</div>
    </div>
  )
}

/**
 * 503 from a read surface. The backend is explicit that "cannot be read" is
 * not the same as "nothing on it", and collapsing the two would be the exact
 * mistake the whole board is built to avoid — so it gets its own treatment.
 */
export function Unreadable({ detail, compact }) {
  return (
    <div className={`unreadable${compact ? ' unreadable-compact' : ''}`}>
      <strong>The board cannot be read.</strong>
      <p>{detail}</p>
      {!compact && (
        <p className="dim">
          This is not a board with nothing on it. Start Postgres, point{' '}
          <code>DATABASE_URL</code> at it, then run <code>db init</code> and{' '}
          <code>db migrate</code>.
          {/* BOTH commands. `tables.sql` is the base schema and
              contract/migrations/ holds 7 files on top of it, so applying only
              the first leaves a database that connects, answers, and is missing
              thread_extraction and job_run — which fails later, further away,
              and looking like a different problem. */}
        </p>
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- reveal */

export function Reveal({ children, delay = 0, as: Tag = 'div', className = '', ...rest }) {
  const ref = useRef(null)
  const [seen, setSeen] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!('IntersectionObserver' in window)) { setSeen(true); return }

    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect() } },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.06 }
    )
    io.observe(el)

    // Fail open. Content must never stay hidden because an observer did not
    // fire — headless renderers, print, and bfcache restores can all skip it.
    const safety = setTimeout(() => setSeen(true), 900)

    return () => { io.disconnect(); clearTimeout(safety) }
  }, [])

  return (
    <Tag
      ref={ref}
      className={`rv${seen ? ' in' : ''}${className ? ' ' + className : ''}`}
      style={{ transitionDelay: `${delay}ms` }}
      {...rest}
    >
      {children}
    </Tag>
  )
}
