import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { approvedUpdates, modelPath } from '../api'
import { useHead } from '../seo/head'
import { aiUpdates } from '../seo/pages'
import '../styles/ai-updates.css'

/**
 * AI UPDATES, /ai-news-headlines (2026-10-30, Parvathi): public. Short headlines on what changed in
 * AI models - launches, price changes, retirements, benchmark results, weekly
 * round-ups - each one approved on the signed-in Updates page
 * (routes/Updates.jsx, Manage). The home page's strip shows the few that were
 * also published; this page is the longer record, `window_days` back.
 *
 * The words are Manage's as they are now: the chosen style, or a person's edit.
 * Every price headline carries "Verify with the provider": a listed price can be
 * the provider's own change or only the router's.
 *
 * THE PAGE, top to bottom (Parvathi): a masthead whose bottom bar is the section
 * nav; the last 7 days in four counts, each one a way into its section; upcoming
 * retirements as countdown cards; then small cards by week, newest first - a
 * weekly round-up wider than the rest, as the week's review. Every update is a
 * headline and one line with no story behind it, so no card is a teaser. A
 * headline about one model links to that model's page (a benchmark result to
 * its AI benchmarks page). The section lives in the address
 * (`?section=pricing`) so a view can be sent to somebody.
 */

/** The page's sections; the three price kinds read as one, "Pricing". */
const SECTIONS = [
  { key: 'all', label: 'All', kinds: null },
  { key: 'launches', label: 'Launches', kinds: ['launch'] },
  { key: 'pricing', label: 'Pricing', kinds: ['price_cut', 'price_rise', 'price_change'] },
  { key: 'retiring', label: 'Retiring', kinds: ['retiring'] },
  { key: 'benchmarks', label: 'Benchmarks', kinds: ['benchmark'] },
  { key: 'roundups', label: 'Weekly round-ups', kinds: ['roundup'] },
]
/** The last 7 days, counted: one figure per section a reader acts on. Not
 *  "This week": the cards below group by calendar week, and a Saturday launch
 *  counted here on a Friday sits under "Last week" there. */
const GLANCE = [
  { section: 'launches', label: 'new models', one: 'new model', tone: 'info' },
  { section: 'pricing', label: 'price moves', one: 'price move', tone: 'pass' },
  { section: 'benchmarks', label: 'benchmark results', one: 'benchmark result', tone: 'mute' },
  { section: 'retiring', label: 'retirements', one: 'retirement', tone: 'warn' },
]
const KIND_TONE = {
  launch: 'info', price_cut: 'pass', price_rise: 'fail', price_change: 'warn', retiring: 'warn',
  benchmark: 'mute', roundup: 'info',
}
const PAGE = 24
const DAY = 86400000

/** One small line icon per kind, drawn in the kind's tone. */
const ICON = {
  launch: 'M5 19 19 5M9 5h10v10',
  price_cut: 'M4 7l6 6 4-4 6 6M20 10v5h-5',
  price_rise: 'M4 17l6-6 4 4 6-6M20 14V9h-5',
  price_change: 'M8 4v16M4 8l4-4 4 4M16 20V4M12 16l4 4 4-4',
  retiring: 'M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  benchmark: 'M5 20V12M12 20V5M19 20v-9M3 20h18',
  roundup: 'M4 5h16v15H4zM4 9h16M9 3v4M15 3v4',
}
function KindIcon({ kind }) {
  return (
    <svg className="au-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d={ICON[kind] || ICON.launch} />
    </svg>
  )
}

// A model name never breaks at its hyphen ("GPT-" / "6.1 Sol"): non-breaking
// hyphens look the same and keep the name on one line.
const keep = (text) => (text || '').replace(/(\w)-(?=\w)/g, '$1‑')

const utcDay = (iso) => new Date(`${iso}T00:00:00Z`)
const todayIso = () => new Date().toISOString().slice(0, 10)
const daysFrom = (iso) => Math.round((utcDay(iso) - utcDay(todayIso())) / DAY)
const fmtShort = (iso) => utcDay(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
/** A card's date as a reader says it: Today, Yesterday, or "Wed 28 Oct". */
function friendly(iso) {
  const d = daysFrom(iso)
  if (d === 0) return 'Today'
  if (d === -1) return 'Yesterday'
  return utcDay(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
}
/** How far off a retirement is. */
function countdown(iso) {
  const d = daysFrom(iso)
  if (d <= 0) return 'Today'
  if (d === 1) return 'Tomorrow'
  return `In ${d} days`
}
const today = () => new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
const inSection = (u, s) => !s.kinds || s.kinds.includes(u.kind)

/** The Monday that starts a date's week (UTC), as an ISO date. */
function weekOf(iso) {
  const d = utcDay(iso)
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7))
  return d.toISOString().slice(0, 10)
}
function weekLabel(week) {
  const now = weekOf(todayIso())
  const prev = utcDay(now)
  prev.setUTCDate(prev.getUTCDate() - 7)
  if (week === now) return 'This week'
  if (week === prev.toISOString().slice(0, 10)) return 'Last week'
  return `Week of ${utcDay(week).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', timeZone: 'UTC' })}`
}
/** Updates by week, newest first. */
function byWeek(items) {
  const groups = []
  for (const u of items) {
    const week = weekOf(u.date)
    const last = groups[groups.length - 1]
    if (last && last.week === week) last.items.push(u)
    else groups.push({ week, items: [u] })
  }
  return groups
}

/** Where a headline leads: the one model's page, its benchmarks for a benchmark
 *  result, the latest releases for a group of launches; a round-up and a group
 *  of price moves have no single page and stay plain text. */
function linkOf(u) {
  const ids = u.models || []
  if (ids.length === 1) {
    return u.kind === 'benchmark' ? `/ai-benchmarks/${modelPath(ids[0])}` : `/ai-models/${modelPath(ids[0])}`
  }
  if (u.kind === 'launch') return '/ai-models/latest'
  return null
}

/** A headline, linked when it has somewhere to go. */
function Head({ u, as: Tag, className }) {
  const to = linkOf(u)
  return (
    <Tag className={className}>
      {to ? <Link to={to} className="au-link">{keep(u.headline)}</Link> : keep(u.headline)}
    </Tag>
  )
}

/** One update: a small card; a round-up is wider, the week's review. */
function Card({ u }) {
  const tone = KIND_TONE[u.kind] || 'mute'
  const review = u.kind === 'roundup'
  return (
    <article className={`au-card au-tone-${tone}${review ? ' au-card-review' : ''}`}>
      <div className="au-card-top">
        <span className="au-badge"><KindIcon kind={u.kind} />{review ? 'Week in review' : u.label}</span>
        <time className="au-date" dateTime={u.date}>{friendly(u.date)}</time>
      </div>
      <Head u={u} as="h3" className="au-head" />
      <p className="au-dek">{u.detail}</p>
      {u.verify && (
        <p className="au-verify" tabIndex={0}
           title="Seen in OpenRouter's listed price. Confirm on the provider's own pricing page before relying on it.">
          Listed price - verify with the provider
        </p>
      )}
    </article>
  )
}

/** "Last 7 days": four counts, each one a way into its section. */
function Glance({ items, onPick }) {
  const since = new Date(Date.now() - 6 * DAY).toISOString().slice(0, 10)
  const counts = GLANCE.map((g) => {
    const s = SECTIONS.find((x) => x.key === g.section)
    const n = items.filter((u) => inSection(u, s) && (u.upcoming || u.date >= since)).length
    return { ...g, n }
  })
  if (!counts.some((c) => c.n)) return null
  return (
    <section className="au-glance" aria-label="The last 7 days at a glance">
      <h2 className="au-label">Last 7 days</h2>
      <div className="au-glance-row">
        {counts.map((c) => (
          <button key={c.section} type="button" className={`au-stat au-tone-${c.tone}`} disabled={!c.n}
                  onClick={() => onPick(c.section)}>
            <span className="au-stat-n">{c.n}</span>
            <span className="au-stat-l">{c.n === 1 ? c.one : c.label}</span>
          </button>
        ))}
      </div>
    </section>
  )
}

/** Upcoming retirements, soonest first, as countdown cards. */
function ComingUp({ items }) {
  if (!items.length) return null
  return (
    <section className="au-coming" aria-labelledby="au-coming-h">
      <h2 id="au-coming-h" className="au-label">Coming up</h2>
      <ul className="au-coming-list">
        {items.map((u) => (
          <li key={u.key} className="au-coming-item">
            <div className="au-count">
              <span className="au-count-when">{countdown(u.date)}</span>
              <time className="au-count-date" dateTime={u.date}>{fmtShort(u.date)}</time>
            </div>
            <div className="au-coming-body">
              <Head u={u} as="p" className="au-coming-head" />
              <p className="au-coming-dek">{u.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function AiUpdates() {
  useHead(aiUpdates())
  const [params, setParams] = useSearchParams()
  const section = SECTIONS.find((s) => s.key === params.get('section')) || SECTIONS[0]
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [shown, setShown] = useState(PAGE)

  useEffect(() => {
    let live = true
    approvedUpdates().then((d) => { if (live) setData(d) }).catch((e) => { if (live) setError(e) })
    return () => { live = false }
  }, [])
  useEffect(() => { setShown(PAGE) }, [section.key])

  const all = useMemo(() => data?.updates || [], [data])
  const upcoming = useMemo(() => all.filter((u) => u.upcoming).sort((a, b) => a.date.localeCompare(b.date)), [all])
  // On "All" the upcoming retirements are the countdown cards, not grid cards too.
  const cards = useMemo(() => (section.key === 'all'
    ? all.filter((u) => !u.upcoming)
    : all.filter((u) => inSection(u, section))), [all, section])
  const counts = useMemo(() => Object.fromEntries(SECTIONS.map((s) => [s.key, all.filter((u) => inSection(u, s)).length])), [all])

  const pick = (key) => {
    const next = new URLSearchParams(params)
    if (key === 'all') next.delete('section'); else next.set('section', key)
    setParams(next, { replace: true })
  }

  return (
    <div className="shell section-tight au-page">
      <header className="au-masthead">
        <div className="au-mast-top">
          <div>
            <p className="au-label">Insights</p>
            <h1 className="au-title">AI updates</h1>
          </div>
          <p className="au-standfirst">
            What changed in AI models: new launches, price moves, retirements and benchmark results.
          </p>
        </div>
        <div className="au-bar">
          {data && all.length > 0 ? (
            <nav className="au-sections" aria-label="Sections">
              {SECTIONS.filter((s) => s.key === 'all' || counts[s.key]).map((s) => (
                <button key={s.key} type="button" className={`au-section${section.key === s.key ? ' on' : ''}`}
                        aria-pressed={section.key === s.key} onClick={() => pick(s.key)}>
                  {s.label}<span className="au-section-n">{counts[s.key]}</span>
                </button>
              ))}
            </nav>
          ) : <span />}
          <p className="au-dateline">{today()}</p>
        </div>
      </header>

      {error && <p className="au-quiet" role="alert">The updates could not be loaded just now. Please try again in a minute.</p>}
      {!data && !error && <div className="skel au-skel" />}
      {data && !all.length && <p className="au-quiet">No updates from the last {data.window_days} days yet. Check back soon.</p>}

      {data && all.length > 0 && (
        <>
          {section.key === 'all' && (
            <div className="au-top">
              <Glance items={all} onPick={pick} />
              <ComingUp items={upcoming} />
            </div>
          )}

          {cards.length ? byWeek(cards.slice(0, shown)).map((g) => (
            <section key={g.week} className="au-week" aria-label={weekLabel(g.week)}>
              <h2 className="au-week-h">{weekLabel(g.week)}<span className="au-week-n">{g.items.length}</span></h2>
              <div className="au-grid">
                {g.items.map((u) => <Card key={u.key} u={u} />)}
              </div>
            </section>
          )) : (
            <p className="au-quiet">Nothing in this section in the last {data.window_days} days.</p>
          )}
          {cards.length > shown && (
            <button type="button" className="btn btn-ghost au-more" onClick={() => setShown((n) => n + PAGE)}>
              Show older ({cards.length - shown} more)
            </button>
          )}

          <footer className="au-note">
            <p>
              <strong>About these updates.</strong> Each headline comes from data we track: new and retiring models
              and listed prices from OpenRouter, and results from the public benchmark leaderboards we follow. A price
              headline compares the new price with the price that had held before it, so a brief blip is not news.
              A listed price can be the provider&apos;s own change or only the router&apos;s, so confirm it on the
              provider&apos;s pricing page before relying on it.
            </p>
            <p>
              More: <Link to="/ai-models/latest">latest AI model releases</Link> ·{' '}
              <Link to="/ai-model-pricing">AI model pricing</Link> ·{' '}
              <Link to="/ai-benchmarks">AI benchmarks</Link>
            </p>
          </footer>
        </>
      )}
    </div>
  )
}
