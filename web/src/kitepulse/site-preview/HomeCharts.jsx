import { useEffect, useId, useRef, useState } from 'react'
import data from './data/home-dashboard.json'

/**
 * THE HOME PAGE'S CHARTS (2026-10-26).
 *
 * Every figure comes from `data/home-dashboard.json` and nowhere else, so the
 * real numbers go in by editing one file. While that file says `"sample":
 * true`, every chart wears a "Sample data" badge: the placeholders are there to
 * show the design and must never read as Kite Pulse measurements.
 *
 * Plain SVG and HTML, no chart library. Colours are the `--kpv-` tokens in
 * site.css: three categorical slots plus a grey for "other", validated for
 * colour-blind separation against the site's own light and dark surfaces.
 * Every chart has a table view, which is also what relieves the one slot
 * (aqua, light mode) that sits below 3:1 against white.
 */

export const dashboard = data

const SERIES = ['var(--kpv-1)', 'var(--kpv-2)', 'var(--kpv-3)']
const OTHER = 'var(--kpv-other)'

const num = (v) => v.toLocaleString('en-US', { maximumFractionDigits: 1 })
const usd = (v) => `$${Math.round(v).toLocaleString('en-US')}`
const tokens = (v) => (v >= 1e9 ? `${num(v / 1e9)}B` : v >= 1e6 ? `${num(v / 1e6)}M` : v >= 1e3 ? `${num(v / 1e3)}K` : num(v))
const FORMATS = { int: num, usd, tokens, hours: (v) => `${num(v)} h` }
function format(v, f) {
  const fn = FORMATS[f]
  if (!fn) throw new Error(`home-dashboard.json: unknown format "${f}"`)
  return fn(v)
}
const shortDate = (d) => new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })

/** The smallest 1, 2, 5 or 10 × 10ⁿ at or above `v`, so axis ticks land on round numbers. */
function niceMax(v) {
  if (!(v > 0)) return 1
  const p = 10 ** Math.floor(Math.log10(v))
  return [1, 2, 5, 10].map((m) => m * p).find((n) => n >= v)
}

/* ------------------------------------------------------------ motion */

// MOTION (2026-10-26). Sections rise in as they scroll into view, charts grow
// from their baseline, KPI figures count up, the collector demo types. All of
// it is CSS keyed off an `is-in` class, and none of it runs for a visitor who
// asked their system for reduced motion (site.css, and `stillness()` here).
const stillness = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** True once the element has scrolled into view; stays true. */
export function useInView(threshold = 0.15) {
  const ref = useRef(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || inView) return undefined
    if (!('IntersectionObserver' in window)) { setInView(true); return undefined }
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setInView(true); io.disconnect() }
    }, { threshold })
    io.observe(el)
    return () => io.disconnect()
  }, [inView, threshold])
  return [ref, inView]
}

/** A section that rises in the first time it scrolls into view. */
export function Reveal({ as: Tag = 'section', className = '', children, ...rest }) {
  const [ref, inView] = useInView(0.1)
  return <Tag ref={ref} className={`${className} kps-reveal${inView ? ' is-in' : ''}`} {...rest}>{children}</Tag>
}

const HEX_R = 24
const RIPPLE_MS = 1900

function hexPath(ctx, x, y, r) {
  ctx.beginPath()
  for (let i = 0; i < 6; i += 1) {
    const a = (Math.PI / 3) * i + Math.PI / 6
    if (i) ctx.lineTo(x + r * Math.cos(a), y + r * Math.sin(a))
    else ctx.moveTo(x + r * Math.cos(a), y + r * Math.sin(a))
  }
  ctx.closePath()
}

/**
 * HONEYCOMB RIPPLE: the blue bands' background (2026-10-26, option D of the
 * five tried). A faint honeycomb; moving the mouse sends rings of light out
 * through the cells, a click sends a bigger one, and now and then a slow one
 * starts on its own. One canvas, drawn only while its band is on screen. The
 * pointer is read from the band, so the canvas never blocks a click. Reduced
 * motion: no rings, no idle ripples, only the cells under the pointer light.
 */
export function HoneycombRipple() {
  const ref = useRef(null)
  useEffect(() => {
    const canvas = ref.current
    const host = canvas?.parentElement
    if (!canvas || !host) return undefined
    const ctx = canvas.getContext('2d')
    const still = stillness()
    const s = { w: 0, h: 0, t: 0, cells: [], rip: [], mouse: null, sm: null, hover: 0, idleAt: 1200, last: { t: -1e9, x: -999, y: -999 } }
    let raf = 0
    let visible = false
    let prev = 0

    const resize = () => {
      const r = host.getBoundingClientRect()
      const dpr = Math.min(2, window.devicePixelRatio || 1)
      s.w = r.width
      s.h = r.height
      canvas.width = Math.round(s.w * dpr)
      canvas.height = Math.round(s.h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      // The light's colour lives in site.css with the band's, so the two cannot drift apart.
      const css = getComputedStyle(host)
      s.glow = css.getPropertyValue('--kp-ripple').trim()
      s.line = css.getPropertyValue('--kp-ripple-line').trim()
      if (!s.glow || !s.line) console.error('HoneycombRipple: --kp-ripple / --kp-ripple-line are not set in site.css')
      const hw = Math.sqrt(3) * HEX_R
      const rh = 1.5 * HEX_R
      s.cells = []
      for (let row = -1; row * rh < s.h + HEX_R * 2; row += 1) {
        for (let x = (row & 1 ? hw / 2 : 0) - hw; x < s.w + hw; x += hw) s.cells.push([x, row * rh])
      }
      if (!raf) draw(performance.now())
    }

    const draw = (now) => {
      const dt = still ? 0 : Math.min(50, prev ? now - prev : 16)
      prev = now
      s.t += dt
      if (still) { s.sm = s.mouse; s.hover = s.mouse ? 1 : 0 } else {
        const f = Math.min(1, dt / 90)
        if (s.mouse) s.sm = s.sm ? { x: s.sm.x + (s.mouse.x - s.sm.x) * f, y: s.sm.y + (s.mouse.y - s.sm.y) * f } : { ...s.mouse }
        s.hover += ((s.mouse ? 1 : 0) - s.hover) * Math.min(1, dt / 220)
        if (s.t > s.idleAt) {
          s.rip.push({ x: s.w * (0.45 + Math.random() * 0.55), y: Math.random() * s.h, t: s.t, a: 0.5 })
          s.idleAt = s.t + 2200 + Math.random() * 1400
        }
      }
      s.rip = s.rip.filter((r) => s.t - r.t < RIPPLE_MS)

      ctx.clearRect(0, 0, s.w, s.h)
      if (!s.glow || !s.line) return
      ctx.lineWidth = 1
      for (const [x, y] of s.cells) {
        let I = s.sm ? s.hover * 0.55 * Math.exp(-((Math.hypot(x - s.sm.x, y - s.sm.y) / 70) ** 2)) : 0
        for (const r of s.rip) {
          const age = s.t - r.t
          const d = Math.hypot(x - r.x, y - r.y)
          I += r.a * Math.exp(-(((d - age * 0.32) / 26) ** 2)) * (1 - age / RIPPLE_MS)
        }
        I = Math.min(1, I)
        hexPath(ctx, x, y, HEX_R - 2)
        if (I > 0.03) { ctx.fillStyle = `rgba(${s.glow},${0.24 * I})`; ctx.fill() }
        ctx.strokeStyle = `rgba(${s.line},${0.08 + 0.7 * I})`
        ctx.shadowColor = `rgb(${s.glow})`
        ctx.shadowBlur = 10 * I
        ctx.stroke()
        ctx.shadowBlur = 0
      }
    }
    const loop = (now) => { draw(now); raf = visible ? requestAnimationFrame(loop) : 0 }
    const redrawIfStill = () => { if (still) draw(performance.now()) }

    const at = (e) => { const r = host.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top } }
    const onMove = (e) => {
      s.mouse = at(e)
      const l = s.last
      if (!still && s.t - l.t > 140 && Math.hypot(s.mouse.x - l.x, s.mouse.y - l.y) > 50) {
        s.rip.push({ x: s.mouse.x, y: s.mouse.y, t: s.t, a: 0.7 })
        s.last = { t: s.t, x: s.mouse.x, y: s.mouse.y }
      }
      redrawIfStill()
    }
    const onLeave = () => { s.mouse = null; redrawIfStill() }
    const onDown = (e) => { if (!still) { const p = at(e); s.rip.push({ x: p.x, y: p.y, t: s.t, a: 1.4 }) } }

    const ro = new ResizeObserver(resize)
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting && !still
      if (visible && !raf) { prev = 0; raf = requestAnimationFrame(loop) }
    })
    ro.observe(host)
    io.observe(host)
    host.addEventListener('pointermove', onMove)
    host.addEventListener('pointerleave', onLeave)
    host.addEventListener('pointerdown', onDown)
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      io.disconnect()
      host.removeEventListener('pointermove', onMove)
      host.removeEventListener('pointerleave', onLeave)
      host.removeEventListener('pointerdown', onDown)
    }
  }, [])
  return <canvas ref={ref} className="kps-honeycomb" aria-hidden="true" />
}

/** Counts from zero to `value` once `run` turns true. Ends on the exact figure. */
function CountUp({ value, fmt, run }) {
  const [shown, setShown] = useState(() => (stillness() ? value : 0))
  useEffect(() => {
    if (!run || stillness()) { if (run) setShown(value); return undefined }
    let raf = 0
    const t0 = performance.now()
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / 1300)
      setShown(p < 1 ? value * (1 - (1 - p) ** 3) : value)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [run, value])
  return fmt(shown === value ? value : Math.round(shown))
}

/** The element's width in pixels, so an SVG draws at its real size and its text never scales. */
function useWidth() {
  const ref = useRef(null)
  const [w, setW] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    const ro = new ResizeObserver(([e]) => setW(Math.floor(e.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

/* ------------------------------------------------------------ frame */

/** A chart's card: title, the sample badge, and a switch to the same figures as a table. */
export function ChartCard({ title, sub, table, children, className = '' }) {
  const [asTable, setAsTable] = useState(false)
  const [ref, inView] = useInView()
  return (
    <figure ref={ref} className={`kpv-card ${className}${inView ? ' is-in' : ''}`}>
      <figcaption className="kpv-head">
        <span className="kpv-titles">
          <span className="kpv-title">{title}</span>
          {sub && <span className="kpv-sub">{sub}</span>}
        </span>
        <span className="kpv-tools">
          {data.sample && <SampleBadge />}
          {table && (
            <button type="button" className="kpv-toggle" aria-pressed={asTable} onClick={() => setAsTable(!asTable)}>
              {asTable ? 'Chart' : 'Table'}
            </button>
          )}
        </span>
      </figcaption>
      {asTable && table ? <DataTable {...table} /> : children}
    </figure>
  )
}

export function SampleBadge() {
  return <span className="kpv-sample" title="Placeholder figures that show the design. Not Kite Pulse measurements.">Sample data</span>
}

function DataTable({ columns, rows }) {
  return (
    <div className="kpv-tablewrap">
      <table className="kpv-table">
        <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{rows.map((r) => <tr key={r[0]}>{r.map((c, i) => <td key={columns[i]}>{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
  )
}

function Legend({ series }) {
  return (
    <ul className="kpv-legend">
      {series.map((s) => <li key={s.name}><i style={{ background: s.color }} />{s.name}</li>)}
    </ul>
  )
}

/* ------------------------------------------------------------ columns */

/**
 * Vertical columns, stacked when there is more than one series. Rounded at the
 * top only, a 2px gap between stacked segments, hover or focus for the values.
 */
function Columns({ labels, series, rows, height = 210, unit, label }) {
  const [ref, w] = useWidth()
  const [hover, setHover] = useState(null)
  const id = useId().replace(/[^a-zA-Z0-9]/g, '')
  const m = { l: 40, r: 4, t: 10, b: 26 }
  const totals = rows.map((r) => r.reduce((a, b) => a + b, 0))
  const max = niceMax(Math.max(...totals))
  const pw = Math.max(0, w - m.l - m.r)
  const ph = height - m.t - m.b
  const band = rows.length ? pw / rows.length : 0
  const bw = Math.max(4, Math.min(30, band * 0.62))
  const y = (v) => m.t + ph - (v / max) * ph
  const base = m.t + ph
  const every = Math.max(1, Math.ceil(52 / Math.max(band, 1)))
  const cx = (i) => m.l + band * (i + 0.5)
  const fmt = (v) => (unit ? `${num(v)} ${unit}` : num(v))

  return (
    <div>
      {series.length > 1 && <Legend series={series} />}
      <div className="kpv-plot" ref={ref} onMouseLeave={() => setHover(null)}>
        {w > 0 && (
          <svg width={w} height={height} role="img" aria-label={label}>
            {[0, 0.25, 0.5, 0.75, 1].map((t) => (
              <g key={t}>
                <line x1={m.l} x2={w - m.r} y1={y(max * t)} y2={y(max * t)} className={t ? 'kpv-grid' : 'kpv-base'} />
                <text x={m.l - 8} y={y(max * t)} dy="0.32em" textAnchor="end" className="kpv-tick">{num(max * t)}</text>
              </g>
            ))}
            {rows.map((r, i) => {
              let acc = 0
              const top = y(totals[i])
              return (
                <g key={labels[i]} opacity={hover === null || hover === i ? 1 : 0.45}>
                  <clipPath id={`${id}c${i}`}>
                    <rect x={cx(i) - bw / 2} y={top} width={bw} height={base - top + 6} rx={4} />
                  </clipPath>
                  <g clipPath={`url(#${id}c${i})`} className="kpv-grow" style={{ '--d': `${i * 40}ms` }}>
                    {r.map((v, j) => {
                      const y0 = y(acc) - (j > 0 ? 2 : 0)
                      acc += v
                      const h = y0 - y(acc)
                      return h > 0 && <rect key={series[j].name} x={cx(i) - bw / 2} y={y(acc)} width={bw} height={h} fill={series[j].color} />
                    })}
                  </g>
                  {i % every === 0 && (
                    <text x={cx(i)} y={height - 8} textAnchor="middle" className="kpv-tick">{labels[i]}</text>
                  )}
                </g>
              )
            })}
            {labels.map((l, i) => (
              <rect key={l} x={m.l + band * i} y={m.t} width={band} height={ph} fill="transparent"
                    tabIndex={0} aria-label={`${labels[i]}: ${fmt(totals[i])}`}
                    onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
            ))}
          </svg>
        )}
        {hover !== null && w > 0 && (
          <div className="kpv-tip" style={{ left: Math.min(Math.max(cx(hover), 80), w - 80), top: Math.max(0, y(totals[hover]) - 12) }}>
            <b>{labels[hover]}</b>
            {series.length > 1 && series.map((s, j) => (
              <span key={s.name}><i style={{ background: s.color }} />{s.name}<em>{fmt(rows[hover][j])}</em></span>
            ))}
            <span className="kpv-tip-total">{series.length > 1 ? 'Total' : series[0].name}<em>{fmt(totals[hover])}</em></span>
          </div>
        )}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------ charts */

export function KpiTiles({ run = true }) {
  return (
    <div className="kpv-kpis">
      {data.kpis.map((k) => (
        <div key={k.label} className="kpv-kpi">
          <span className="kpv-kpi-l">{k.label}</span>
          <span className="kpv-kpi-v"><CountUp value={k.value} fmt={(v) => format(v, k.format)} run={run} /></span>
          {k.note && <span className="kpv-kpi-n">{k.note}</span>}
        </div>
      ))}
    </div>
  )
}

/**
 * Estimated cost per tool, as a list and never a total: Team AI Usage does not
 * add cost across tools (Master Source of Truth, 1.2). A tool with no price is
 * a dash, never $0.
 */
export function CostPerTool() {
  return (
    <div className="kps-console-chart">
      <span className="kps-console-h">Estimated cost per tool <span className="kpv-muted">· this week</span></span>
      <ul className="kpv-costs">
        {data.costPerTool.map((c) => (
          <li key={c.tool}>
            <span>{c.tool}</span>
            <b>{c.usd == null ? '—' : usd(c.usd)}</b>
            <small>{c.usd == null ? 'no price' : c.basis}</small>
          </li>
        ))}
      </ul>
      <small className="kpv-note">Not billed spend. Each tool stands alone; costs are never added up across tools.</small>
    </div>
  )
}

export function SessionsByTool({ bare }) {
  const s = data.sessionsByTool
  const series = [...s.tools.map((name, i) => ({ name, color: SERIES[i] })), { name: s.other, color: OTHER }]
  const labels = s.days.map((d) => shortDate(d.date))
  const chart = (
    <Columns labels={labels} series={series} rows={s.days.map((d) => d.values)}
             label={`AI sessions per day by tool, ${labels[0]} to ${labels.at(-1)}`} />
  )
  if (bare) return chart
  return (
    <ChartCard title="AI sessions per day, by tool" sub={`${labels[0]} – ${labels.at(-1)}`}
               table={{ columns: ['Day', ...series.map((x) => x.name)], rows: s.days.map((d, i) => [labels[i], ...d.values.map(num)]) }}>
      {chart}
    </ChartCard>
  )
}

/** A status is always an icon and a word as well as a colour. */
function budgetStatus(pct) {
  if (pct >= 100) return { key: 'crit', icon: '●', word: '100% alert' }
  if (pct >= 80) return { key: 'warn', icon: '▲', word: '80% alert' }
  return { key: 'good', icon: '✓', word: 'Within budget' }
}
const budgetFmt = (r, v) => {
  if (r.unit === 'usd') return usd(v)
  if (r.unit === 'tokens') return tokens(v)
  throw new Error(`home-dashboard.json: aiBudgets "${r.name}" has unknown unit "${r.unit}"`)
}

/**
 * AI Budgets: a monthly budget per team or project, in tokens or estimated US
 * dollars, alerts at 80% and 100% (Master Source of Truth, 1.2). The only place
 * the console shows cost per team or project, so the home page shows it here.
 */
export function AiBudgets() {
  const rows = data.aiBudgets.map((r) => ({ ...r, pct: Math.round((r.used / r.budget) * 100) }))
  return (
    <ChartCard title="AI Budgets" sub="Month to date · alerts at 80% and 100%"
               table={{ columns: ['Budget', 'Per', 'Used', 'Budget', 'Share', 'Unpriced tokens', 'Status'],
                 rows: rows.map((r) => [r.name, r.scope, budgetFmt(r, r.used), budgetFmt(r, r.budget), `${r.pct}%`,
                   r.unpricedTokens == null ? '—' : tokens(r.unpricedTokens), budgetStatus(r.pct).word]) }}>
      <ul className="kpv-meters">
        {rows.map((r, i) => {
          const s = budgetStatus(r.pct)
          return (
            <li key={r.name}>
              <span className="kpv-m-who">
                <b>{r.name}</b>
                <small>{r.scope} · {budgetFmt(r, r.used)} of {budgetFmt(r, r.budget)}</small>
                {r.unpricedTokens != null && <small>+ {tokens(r.unpricedTokens)} unpriced tokens</small>}
              </span>
              <span className="kpv-m-track" role="meter" aria-valuenow={r.pct} aria-valuemin={0} aria-valuemax={100}
                    aria-label={`${r.name} budget used`}>
                <span className={`kpv-m-fill kpv-${s.key}`} style={{ width: `${Math.min(100, r.pct)}%`, '--d': `${i * 90}ms` }} />
              </span>
              <span className="kpv-m-pct">{r.pct}%</span>
              <span className={`kpv-status kpv-status-${s.key}`}><span aria-hidden="true">{s.icon}</span>{s.word}</span>
            </li>
          )
        })}
      </ul>
      <small className="kpv-note">A dollar budget adds up the priced tools only and reports unpriced tokens separately.</small>
    </ChartCard>
  )
}

/** "Near" is 80% or more, "at limit" is 100% (Master Source of Truth, 1.2). */
function headroomStatus(pct) {
  const { near, limit } = data.headroomBands
  if (pct >= limit) return { key: 'crit', icon: '●', word: 'At limit' }
  if (pct >= near) return { key: 'warn', icon: '▲', word: 'Near' }
  return { key: 'good', icon: '✓', word: 'Room left' }
}

export function PlanHeadroom() {
  const rows = [...data.planHeadroom].sort((a, b) => b.usedPct - a.usedPct)
  return (
    <ChartCard title="Plan headroom (Claude Code)" sub="5-hour, weekly and per-model weekly windows, worst first"
               table={{ columns: ['Person', 'Plan', 'Window', 'Used', 'Status', 'Reading'],
                 rows: rows.map((r) => [r.person, r.plan, r.window, `${r.usedPct}%`, headroomStatus(r.usedPct).word, r.stale ? 'Stale' : 'Current']) }}>
      <ul className="kpv-meters">
        {rows.map((r, i) => {
          const s = headroomStatus(r.usedPct)
          return (
            <li key={r.person}>
              <span className="kpv-m-who">
                <b>{r.person}</b>
                <small>{r.plan} · {r.window}{r.stale && <> · <span className="kpv-stale">stale reading</span></>}</small>
              </span>
              <span className="kpv-m-track" role="meter" aria-valuenow={r.usedPct} aria-valuemin={0} aria-valuemax={100}
                    aria-label={`${r.person}, ${r.window.toLowerCase()} window`}>
                <span className={`kpv-m-fill kpv-${s.key}`} style={{ width: `${Math.min(100, r.usedPct)}%`, '--d': `${i * 90}ms` }} />
              </span>
              <span className="kpv-m-pct">{r.usedPct}%</span>
              <span className={`kpv-status kpv-status-${s.key}`}><span aria-hidden="true">{s.icon}</span>{s.word}</span>
            </li>
          )
        })}
      </ul>
    </ChartCard>
  )
}

const PRESENCE = { coding: 'Coding', online: 'Online', offline: 'Offline' }

/**
 * Team Overview: who is online and who is coding right now, active time and
 * sessions today against a typical day, who needs attention, and each person's
 * current project (Master Source of Truth, 1.4).
 */
export function TeamToday() {
  const t = data.teamToday
  const word = (s) => {
    if (!PRESENCE[s]) throw new Error(`home-dashboard.json: teamToday status "${s}" is not one of ${Object.keys(PRESENCE).join(', ')}`)
    return PRESENCE[s]
  }
  return (
    <ChartCard title="Team Overview" sub={`Today, as of ${t.now} · refreshes every 30 seconds`}
               table={{ columns: ['Person', 'Status', 'Current project', 'Needs attention'],
                 rows: t.people.map((p) => [p.person, word(p.status), p.project, p.attention || '—']) }}>
      <div className="kpv-facts">
        <div className="kpv-fact"><span>Active time today</span><b>{num(t.activeHours.today)} h</b><small>typical day {num(t.activeHours.typical)} h</small></div>
        <div className="kpv-fact"><span>Sessions today</span><b>{num(t.sessions.today)}</b><small>typical day {num(t.sessions.typical)}</small></div>
        <div className="kpv-fact"><span>Coding now</span><b>{t.people.filter((p) => p.status === 'coding').length}</b><small>of {t.people.length} people</small></div>
      </div>
      <div className="kpv-tablewrap">
        <table className="kpv-table kpv-projects">
          <thead><tr><th>Person</th><th>Status</th><th>Current project</th><th>Needs attention</th></tr></thead>
          <tbody>
            {t.people.map((p) => (
              <tr key={p.person}>
                <td>{p.person}</td>
                <td><span className={`kpv-health kpv-presence-${p.status}`}>{word(p.status)}</span></td>
                <td><b>{p.project}</b></td>
                <td>{p.attention
                  ? <span className="kpv-status kpv-status-warn"><span aria-hidden="true">▲</span>{p.attention}</span>
                  : <span className="kpv-muted">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartCard>
  )
}

function Sparkline({ values, label }) {
  const w = 96
  const h = 28
  const max = Math.max(1, ...values)
  const pts = values.map((v, i) => [3 + (i / (values.length - 1)) * (w - 6), h - 4 - (v / max) * (h - 8)])
  const [ex, ey] = pts.at(-1)
  return (
    <svg width={w} height={h} role="img" aria-label={label} className="kpv-spark">
      <path d={`M${pts.map((p) => p.join(',')).join('L')}`} pathLength="1" />
      <circle cx={ex} cy={ey} r={3} />
    </svg>
  )
}

const HEALTH = { active: 'Active', stable: 'Stable', dormant: 'Dormant' }

export function ProjectHealth() {
  const rows = data.projects
  return (
    <ChartCard title="All Projects" sub="Sessions over the last 8 weeks"
               table={{ columns: ['Project', 'Health', 'Sessions', 'Contributors', 'Last activity', 'Weekly sessions'],
                 rows: rows.map((p) => [p.project, HEALTH[p.health], num(p.sessions), p.contributors, p.lastActivity, p.weekly.join(', ')]) }}>
      <div className="kpv-tablewrap">
        <table className="kpv-table kpv-projects">
          <thead><tr><th>Project</th><th>Health</th><th>Trend</th><th className="kpv-r">Sessions</th><th className="kpv-r">People</th><th>Last activity</th></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.project}>
                <td><b>{p.project}</b></td>
                <td><span className={`kpv-health kpv-health-${p.health}`}>{HEALTH[p.health]}</span></td>
                <td><Sparkline values={p.weekly} label={`${p.project} weekly sessions: ${p.weekly.join(', ')}`} /></td>
                <td className="kpv-r">{num(p.sessions)}</td>
                <td className="kpv-r">{p.contributors}</td>
                <td className="kpv-muted">{p.lastActivity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartCard>
  )
}

export function PersonalView() {
  const p = data.personal
  const days = p.activeHoursByDay
  return (
    <ChartCard title="My Scorecard & Insights" sub={`Working style: ${p.workingStyle}`}
               table={{ columns: ['Day', 'Active hours'], rows: days.map((d) => [d.day, num(d.hours)]) }}>
      <div className="kpv-facts">
        {p.facts.map((f) => (
          <div key={f.label} className="kpv-fact"><span>{f.label}</span><b>{f.value}</b></div>
        ))}
      </div>
      <Columns labels={days.map((d) => d.day)} series={[{ name: 'Active hours', color: SERIES[0] }]}
               rows={days.map((d) => [d.hours])} height={170} unit="h" label="Active hours by weekday" />
    </ChartCard>
  )
}

/* ------------------------------------------------------------ picker */

/**
 * "WHAT WOULD YOU SEE?" (2026-10-28, the Page Map's plan for the home page).
 * The visitor picks their tools and a team size; the table shows a sample week
 * of what Team AI Usage would hold for them.
 *
 * `tools` are product facts (KitePulseSite.jsx, from the Master Source of
 * Truth's "What each tool provides"); the figures are sample data from
 * home-dashboard.json. The two must agree on which tools have a price, and a
 * disagreement throws rather than showing a priced tool as "—" or an unpriced
 * one with a dollar figure.
 */
export function TeamPicker({ tools }) {
  const p = data.picker
  const [picked, setPicked] = useState(() => new Set(p.defaultTools))
  const [size, setSize] = useState(p.defaultSize)
  const toggle = (name) => setPicked((s) => {
    const n = new Set(s)
    if (n.has(name)) n.delete(name)
    else n.add(name)
    return n
  })

  const rows = tools.filter((t) => picked.has(t.name)).map((t) => {
    const d = p.perDeveloperWeek[t.name]
    if (!d) throw new Error(`home-dashboard.json: picker.perDeveloperWeek has no entry for "${t.name}"`)
    if (t.priced !== (d.usd != null)) {
      throw new Error(`"${t.name}": the tool facts say priced=${t.priced}, but its sample usd is ${d.usd}`)
    }
    const devs = Math.max(1, Math.round(size * d.share))
    return { ...t, devs, sessions: devs * d.sessions, tokens: devs * d.tokens, usd: d.usd == null ? null : devs * d.usd,
      near: t.planLimits ? Math.round(devs * p.claudeNearLimitShare) : null }
  })
  const partialTokens = rows.some((r) => r.tokensNote)

  return (
    <div className="kpv-picker">
      <div className="kpv-ctl">
        <span className="kpv-ctl-l" id="kpv-pick-tools">AI tools your team uses</span>
        <div className="kpv-chips" role="group" aria-labelledby="kpv-pick-tools">
          {tools.map((t) => (
            <button key={t.name} type="button" aria-pressed={picked.has(t.name)} onClick={() => toggle(t.name)}>{t.name}</button>
          ))}
        </div>
      </div>
      <div className="kpv-ctl">
        <span className="kpv-ctl-l" id="kpv-pick-size">Team size</span>
        <div className="kpv-chips" role="group" aria-labelledby="kpv-pick-size">
          {p.teamSizes.map((n) => (
            <button key={n} type="button" aria-pressed={size === n} onClick={() => setSize(n)}>{n} developers</button>
          ))}
        </div>
      </div>

      <ChartCard title="Team AI Usage" sub={`A sample week for ${size} developers`}>
        {rows.length === 0 ? <p className="kpv-muted">Pick at least one tool.</p> : (
          <div className="kpv-tablewrap">
            <table className="kpv-table kpv-pick">
              <thead>
                <tr><th>Tool</th><th className="kpv-r">Developers</th><th className="kpv-r">Sessions</th>
                  <th className="kpv-r">Tokens</th><th className="kpv-r">Estimated cost</th><th>Plan limits</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name}>
                    <td><b>{r.name}</b></td>
                    <td className="kpv-r">{num(r.devs)}</td>
                    <td className="kpv-r">{num(r.sessions)}</td>
                    <td className="kpv-r">{tokens(r.tokens)}{r.tokensNote && <small>{r.tokensNote}</small>}</td>
                    <td className="kpv-r">{r.usd == null ? '—' : usd(r.usd)}<small>{r.costNote}</small></td>
                    <td>{r.planLimits
                      ? <>{r.near} near a limit<small>5-hour and weekly windows</small></>
                      : <span className="kpv-muted">Not reported by this tool</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <small className="kpv-note">
          Cost is never added up across tools and is not billed spend.
          {partialTokens && ' Cursor and Copilot report input and output tokens only.'}
        </small>
      </ChartCard>
    </div>
  )
}

/* ------------------------------------------------------------ how it works */

// What the collector does, as log lines, each tied to the part of "How it
// works" it belongs to. Every line restates the Master Source of Truth (1.1):
// only new activity, secrets masked on the computer, picks up where it stopped
// when the network drops, session uploads encrypted, sent only to the team's
// own server. An illustration, badged so.
const DEMO = [
  { step: 0, tone: 'ok', text: 'Claude Code  ·  2 new sessions  ·  payments-api' },
  { step: 0, tone: 'ok', text: 'Cursor  ·  1 new session  ·  web-app' },
  { step: 0, tone: 'ok', text: 'Secrets masked on this computer: 3' },
  { step: 1, tone: 'warn', text: 'Network dropped  ·  will resume where it stopped' },
  { step: 1, tone: 'ok', text: 'Back online  ·  caught up, uploads encrypted' },
  { step: 1, tone: 'ok', text: 'Sent to your Kite Pulse server  ·  no vendor cloud' },
  { step: 2, tone: 'ok', text: 'Console updated  ·  Team Overview, Team AI Usage' },
]

/** The three parts beside a terminal that plays through them, lighting each part as its lines run. */
export function HowItWorks({ steps }) {
  const [ref, inView] = useInView(0.3)
  const [still] = useState(stillness)
  const [n, setN] = useState(() => (stillness() ? DEMO.length : 0))
  useEffect(() => {
    if (!inView || still) return undefined
    const done = n >= DEMO.length
    const t = setTimeout(() => setN(done ? 0 : n + 1), done ? 3400 : n === 0 ? 500 : 950)
    return () => clearTimeout(t)
  }, [inView, n, still])
  const active = n === 0 ? 0 : DEMO[Math.min(n, DEMO.length) - 1].step

  return (
    <div className="kps-how" ref={ref}>
      <ol className="kps-steps">
        {steps.map(([title, body], i) => (
          <li key={title} className={i === active ? 'on' : undefined}>
            <span className="kps-step-n">{i + 1}</span>
            <h3>{title}</h3>
            <p className="kps-muted">{body}</p>
          </li>
        ))}
      </ol>
      <div className="kps-term" aria-label="Illustration of the desktop program at work">
        <div className="kps-term-bar">
          <span aria-hidden="true"><i /><i /><i /></span>
          <b>Kite Pulse desktop program</b>
          <span className="kps-term-badge">Illustration</span>
        </div>
        <ol className="kps-term-body" aria-live="off">
          {DEMO.slice(0, n).map((l) => (
            <li key={l.text} className={`kps-term-line kps-term-${l.tone}`}>
              <span aria-hidden="true">{l.tone === 'warn' ? '!' : '✓'}</span>{l.text}
            </li>
          ))}
          {n < DEMO.length && <li className="kps-term-cursor" aria-hidden="true">▍</li>}
        </ol>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------ screenshots */

// Screenshot files sit in ./screens/ and are named in home-dashboard.json.
const SHOTS = import.meta.glob('./screens/*.{png,jpg,jpeg,webp}', { eager: true, query: '?url', import: 'default' })

/** A named file that is not there says so, rather than quietly showing the empty slot. */
export function Screenshot({ shot }) {
  const src = shot.file && SHOTS[`./screens/${shot.file}`]
  return (
    <figure className="kpv-shot">
      <div className="kpv-shot-frame">
        <span className="kpv-shot-bar" aria-hidden="true"><i /><i /><i /><em>{shot.title}</em></span>
        {src ? <img src={src} alt={`${shot.title}: ${shot.caption}`} loading="lazy" />
          : (
            <div className="kpv-shot-empty">
              {shot.file
                ? <><b>File not found</b><small><code>screens/{shot.file}</code> is named in home-dashboard.json but is not in the folder.</small></>
                : <><b>Screenshot to come</b><small>Save it in <code>web/src/kitepulse/site-preview/screens/</code> and name it in home-dashboard.json.</small></>}
            </div>
          )}
      </div>
      <figcaption><b>{shot.title}</b> {shot.caption}</figcaption>
    </figure>
  )
}
