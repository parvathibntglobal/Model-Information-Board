import { useEffect, useRef, useState } from 'react'

/* ---------------------------------------------------------------- primitives */

export function Badge({ tone = 'mute', children, ...rest }) {
  return <span className={`badge badge-${tone}`} {...rest}>{children}</span>
}

export function Chip({ on, children, ...rest }) {
  const Tag = rest.onClick ? 'button' : 'span'
  return <Tag className={`chip${on ? ' chip-on' : ''}`} {...rest}>{children}</Tag>
}

export function Label({ children }) {
  return <span className="label">{children}</span>
}

export function Stat({ n, l }) {
  return (
    <div className="stat">
      <span className="stat-n tnum">{n}</span>
      <span className="stat-l">{l}</span>
    </div>
  )
}

/**
 * Consensus meter. The bar is a reading aid for the counts beside it — the
 * board never publishes a score, so the number shown is always voices.
 */
export function Meter({ name, value, voices, platforms }) {
  const [w, setW] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setW(value), 60)
    return () => clearTimeout(t)
  }, [value])
  return (
    <div className="meter">
      <span className="meter-name">{name}</span>
      <span className="meter-val">
        {voices != null ? `${voices} ${voices === 1 ? 'voice' : 'voices'}` : ''}
        {platforms != null ? ` · ${platforms}pf` : ''}
      </span>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${Math.round(w * 100)}%` }} />
      </div>
    </div>
  )
}

export function BandHead({ tone = 'mute', title, count }) {
  return (
    <div className="band-head">
      <Badge tone={tone}>{title}</Badge>
      {count != null && <span className="label">{count}</span>}
      <span className="band-rule" />
    </div>
  )
}

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
          This is not a board with nothing on it. Start Postgres, point
          DATABASE_URL at it, and apply <code>contract/tables.sql</code>.
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
