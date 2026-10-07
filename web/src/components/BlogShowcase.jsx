import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { blogPosts } from '../api'

/**
 * The landing page's blogs: a SLIDING STRIP of equal cards.
 *
 * WHY NOT A COVERFLOW: Browse above already is one, and two of the same on one
 * page repeat. Here every card is the same size and the strip glides sideways
 * on its own, looping; it pauses while hovered, touched or focused, can be
 * swiped or scrolled by hand, and has arrows. With reduced motion it does not
 * move at all - it is then an ordinary scrollable row.
 *
 * WHICH POSTS. The same rule as the Blogs page: a post a recorded generation
 * run wrote is shown once approved in Admin -> Blogs (`review`), and drafts that
 * predate the run history show as they always did. The featured post leads,
 * then the most recently written, one per format where possible.
 *
 * ⚠ EVERY COVER IS DRAWN FROM THE POST'S OWN DATA, never stock art and never a
 *   new number: its findings counted, the models it compares, its price table
 *   (registry list prices), or its scenario matrix. A post with none of those
 *   gets its format in type. See `coverFor`.
 */

const SHOW = 5

// ── REAL PICTURES FROM THE POSTS ────────────────────────────────────────────
// Any image dropped into src/assets/blog-art/ named after a post's slug
// (`capability-reasoning.svg`, `<slug>.png` ...) is that post's picture, picked
// up at build time with no code change. A post may also carry its own `image`
// URL if the generator ever writes one. Either way the picture is the post's -
// a post without one gets a cover drawn from its data instead.
const ART = Object.fromEntries(
  Object.entries(import.meta.glob('../assets/blog-art/*.{svg,png,jpg,jpeg,webp}',
    { eager: true, query: '?url', import: 'default' }))
    .map(([path, url]) => [path.split('/').pop().replace(/\.[^.]+$/, ''), url]),
)
const artFor = (p) => (typeof p.image === 'string' && p.image) || ART[p.slug] || null

function written(p) {
  const t = Date.parse(p?.provenance?.generated_at || '')
  return Number.isNaN(t) ? 0 : t
}

/** Posts with a real picture first, then featured, then newest - preferring a
 *  different format each time. */
function pick(posts) {
  const pool = [...posts].sort((a, b) => (artFor(b) ? 1 : 0) - (artFor(a) ? 1 : 0)
    || (b.feat ? 1 : 0) - (a.feat ? 1 : 0) || written(b) - written(a))
  const out = []
  const formats = new Set()
  for (const p of pool) {
    const f = p.kicker || p.tag
    if (out.length < SHOW && !formats.has(f)) { out.push(p); formats.add(f) }
  }
  for (const p of pool) if (out.length < SHOW && !out.includes(p)) out.push(p)
  return out
}

const blockOf = (p, kind) => (p.body || []).find((b) => b[0] === 'table' && b[1]?.kind === kind)?.[1]
const short = (name) => String(name).replace(/^Claude /, '')
const clip = (s, n) => (String(s).length > n ? `${String(s).slice(0, n - 1)}…` : String(s))

// ── the covers ──────────────────────────────────────────────────────────────

function Findings({ items }) {
  const ok = items.filter((x) => x.status === 'established').length
  const no = items.length - ok
  const tiles = items.slice(0, 6)
  return (
    <svg viewBox="0 0 400 210" role="img" aria-label={`${ok} findings established, ${no} not`}>
      <text x="16" y="22" className="cv-cap">FINDINGS IN THIS REPORT</text>
      {tiles.map((x, i) => {
        const good = x.status === 'established'
        return (
          <g key={i}>
            <rect x={28 + i * 60} y="58" width="48" height="64" rx="10" className={good ? 'cv-ok' : 'cv-no'} />
            <text x={52 + i * 60} y="100" textAnchor="middle" className="cv-mark">{good ? '✓' : '✗'}</text>
          </g>
        )
      })}
      <text x="28" y="160" className="cv-big">{ok} established</text>
      <text x="28" y="186" className="cv-lbl">{no} not established · counted from the post&rsquo;s findings</text>
    </svg>
  )
}

function Versus({ a, b }) {
  const [a1, ...a2] = a.split(' ')
  const [b1, ...b2] = b.split(' ')
  return (
    <svg viewBox="0 0 400 210" role="img" aria-label={`${a} versus ${b}`}>
      <text x="16" y="22" className="cv-cap">HEAD-TO-HEAD</text>
      <circle cx="110" cy="112" r="62" className="cv-a" />
      <circle cx="290" cy="112" r="62" className="cv-b" />
      <text x="110" y="108" textAnchor="middle" className="cv-name">{clip(a1, 10)}</text>
      <text x="110" y="128" textAnchor="middle" className="cv-sub">{clip(a2.join(' '), 16)}</text>
      <text x="290" y="108" textAnchor="middle" className="cv-name">{clip(b1, 10)}</text>
      <text x="290" y="128" textAnchor="middle" className="cv-sub">{clip(b2.join(' '), 16)}</text>
      <rect x="178" y="98" width="44" height="28" rx="14" className="cv-vs" />
      <text x="200" y="117" textAnchor="middle" className="cv-vst">VS</text>
    </svg>
  )
}

function Prices({ rows }) {
  // Output $/M, the third column; a row with no published price is skipped,
  // never drawn as zero. The first row is the post's own subject.
  const vals = rows
    .map((r, i) => ({ name: short(r[0]), v: Number(String(r[2]).replace(/[$,]/g, '')), first: i === 0 }))
    .filter((r) => Number.isFinite(r.v))
    .slice(0, 5)
  const top = Math.max(...vals.map((r) => r.v), 1)
  return (
    <svg viewBox="0 0 400 210" role="img" aria-label="Output price per million tokens, from the post's price table">
      <text x="16" y="22" className="cv-cap">OUTPUT $ / 1M TOKENS · FROM THE POST</text>
      {vals.map((r, i) => {
        const y = 40 + i * 32
        const w = (r.v / top) * 210
        return (
          <g key={r.name + i}>
            <text x="124" y={y + 14} textAnchor="end" className={`cv-lbl${r.first ? ' hl' : ''}`}>{clip(r.name, 16)}</text>
            <rect x="134" y={y + 2} width={w} height="16" rx="4" className={r.first ? 'cv-bar-hl' : 'cv-bar'} />
            <text x={138 + w} y={y + 15} className="cv-val">${r.v.toFixed(2)}</text>
          </g>
        )
      })}
    </svg>
  )
}

function Routes({ rows }) {
  return (
    <svg viewBox="0 0 400 210" role="img" aria-label="Scenario to route, from the post's scenario matrix">
      <text x="16" y="22" className="cv-cap">SCENARIO → ROUTE · FROM THE POST</text>
      {rows.slice(0, 7).map((r, i) => {
        const y = 40 + i * 24
        return (
          <g key={i}>
            <text x="16" y={y + 12} className="cv-lbl">{clip(r[0], 20)}</text>
            <line x1="150" y1={y + 8} x2="196" y2={y + 8} className="cv-link" />
            <rect x="200" y={y - 3} width="184" height="20" rx="10" className="cv-route" />
            <text x="210" y={y + 11} className="cv-rt">{clip(r[r.length - 1], 28)}</text>
          </g>
        )
      })}
    </svg>
  )
}

function TypeCover({ kicker, title }) {
  const word = clip(String(title).split(':')[0], 22)
  return (
    <svg viewBox="0 0 400 210" role="img" aria-label={kicker}>
      <text x="24" y="40" className="cv-cap">{String(kicker).toUpperCase()}</text>
      <text x="24" y="118" className="cv-type">{word}</text>
      <rect x="24" y="140" width="64" height="4" rx="2" className="cv-vs" />
    </svg>
  )
}

/** The post's own data, in this order of preference. */
function coverFor(p) {
  const sp = p.special
  if (sp?.type === 'findings' && sp.items?.length) return <Findings items={sp.items} />
  if (sp?.type === 'picks' && sp.items?.length) {
    const names = [...new Set(sp.items.map((x) => x.pick))]
    if (names.length >= 2) return <Versus a={names[0]} b={names[1]} />
  }
  const vs = String(p.title).split(':')[0].split(/\s+vs\.?\s+/i)
  if (vs.length === 2) return <Versus a={short(vs[0].trim())} b={short(vs[1].trim())} />
  const prices = blockOf(p, 'prices')
  if (prices?.rows?.length) return <Prices rows={prices.rows} />
  const matrix = blockOf(p, 'matrix')
  if (matrix?.rows?.length) return <Routes rows={matrix.rows} />
  return <TypeCover kicker={p.kicker || p.tag} title={p.title} />
}

function firstSentences(text, n = 2) {
  return String(text || '').split(/(?<=[.!?])\s+/).slice(0, n).join(' ')
}

function Card({ p, hidden }) {
  return (
    <Link to={`/blogs/${encodeURIComponent(p.slug)}`} className="bs-card"
          aria-hidden={hidden || undefined} tabIndex={hidden ? -1 : undefined}>
      <div className="bs-img">
        {artFor(p)
          ? <><img src={artFor(p)} alt={`Picture from the post: ${p.title}`} loading="lazy" /><span className="bs-badge">From the post</span></>
          : coverFor(p)}
      </div>
      <div className="bs-body">
        <span className="bs-kick">{p.kicker || p.tag}</span>
        <h3>{p.title}</h3>
        {p.lead && <p>{firstSentences(p.lead)}</p>}
        <div className="bs-meta">
          {(p.meta || [])[0] && <span>{p.meta[0]}</span>}
          {(p.meta || [])[0] && p.read ? <span className="dot">·</span> : null}
          {p.read ? <span>{p.read} min read</span> : null}
        </div>
        {(p.tags || []).length > 0 && (
          <div className="bs-tags">{p.tags.slice(0, 2).map((t) => <span key={t}>{t}</span>)}</div>
        )}
      </div>
    </Link>
  )
}

export default function BlogShowcase() {
  const [posts, setPosts] = useState(null)

  useEffect(() => {
    let alive = true
    blogPosts()
      .then((d) => {
        if (!alive) return
        // APPROVED POSTS ONLY, filtered on the server (judge/blog_store.py).
        setPosts(pick(d.posts || []))
      })
      .catch(() => alive && setPosts([]))
    return () => { alive = false }
  }, [])

  if (posts === null) return <div className="skel" style={{ height: 420, marginTop: 24 }} />
  if (posts.length === 0) {
    return (
      <p className="dim" style={{ marginTop: 18, fontSize: 'var(--fs-sm)' }}>
        The first posts are being reviewed. They appear here once approved.
      </p>
    )
  }

  return <Strip posts={posts} />
}

/** The moving row. The cards are rendered twice so the loop has no seam; the
 *  second copy is hidden from screen readers and from the tab order. */
function Strip({ posts }) {
  const box = useRef(null)
  const paused = useRef(false)

  useEffect(() => {
    const el = box.current
    if (!el) return undefined
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    let raf = 0
    let last = performance.now()
    const SPEED = 0.025 // px per ms: a slow glide, roughly one card every fifteen seconds
    const tick = (now) => {
      const dt = Math.min(now - last, 64)
      last = now
      if (!paused.current) {
        el.scrollLeft += SPEED * dt
        const half = el.scrollWidth / 2
        if (el.scrollLeft >= half) el.scrollLeft -= half
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [posts])

  const hold = (v) => () => { paused.current = v }
  const step = (dir) => {
    const el = box.current
    const card = el?.querySelector('.bs-card')
    if (!el || !card) return
    el.scrollBy({ left: dir * (card.offsetWidth + 20), behavior: 'smooth' })
  }

  return (
    <div className="bs">
      {/* THE ARROWS SIT ON THE STRIP'S EDGES, at the cards' middle. */}
      <button type="button" className="bs-btn bs-prev" aria-label="Previous posts" onClick={() => step(-1)}>‹</button>
      <button type="button" className="bs-btn bs-next" aria-label="Next posts" onClick={() => step(1)}>›</button>
      <div className="bs-track" ref={box}
           onMouseEnter={hold(true)} onMouseLeave={hold(false)}
           onTouchStart={hold(true)} onTouchEnd={hold(false)}
           onFocus={hold(true)} onBlur={hold(false)}>
        {posts.map((p) => <Card key={p.slug} p={p} />)}
        {posts.map((p) => <Card key={`${p.slug}~2`} p={p} hidden />)}
      </div>
    </div>
  )
}
