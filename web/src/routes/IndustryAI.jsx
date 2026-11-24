import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { industryAi } from '../api'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import { fmtDayUtc } from '../dates'
import { Bars, PLATFORM_LABEL, REASON_LABEL, STAGE_LABEL, TYPE_LABEL, n } from '../industry-ai/parts'
import '../styles/industry-ai.css'

/**
 * AI IN INDUSTRIES (2026-11-20): how much data the Industry AI agent and its
 * observer have collected for each active domain (industries and roles, from
 * contract/industry_ai.yaml). Signed in. Which domains are named is read from the
 * data, never written here: it said "five industries" while the active five were
 * mostly roles (2026-11-24).
 *
 * COUNTS ONLY. The API sends no post text, link or author (judge/industry_ai/
 * view.py), so nothing here can show one. Each card opens its domain's own page
 * (routes/IndustryAIDomain.jsx, signed in), which does list the posts. Every number is a count of stored
 * items, beside its denominator: what the domain's queries found, and what the
 * rules filtered out and why - so a small "kept" never reads as "nothing out
 * there" (rules 4 and 7). Items no domain's terms confirmed are counted apart,
 * never added to a domain (rule 6).
 */

function Months({ byMonth }) {
  const months = Object.keys(byMonth || {})
  if (months.length < 2) return null
  const max = Math.max(...months.map((m) => byMonth[m]))
  return (
    <div className="iai-trend" role="img" aria-label={`Kept items by month posted: ${months.map((m) => `${m} ${byMonth[m]}`).join(', ')}`}>
      {months.map((m) => (
        <span key={m} className="iai-trend-col" title={`${m}: ${byMonth[m]}`}>
          <span className="iai-trend-bar" style={{ height: `${Math.max(4, (100 * byMonth[m]) / max)}%` }} />
        </span>
      ))}
    </div>
  )
}

function DomainCard({ d, types }) {
  const stages = Object.entries(d.by_stage || {}).filter(([, v]) => v)
  return (
    <section className="card iai-card">
      <header className="iai-card-head">
        <h2><Link className="iai-open" to={`/ai-in-industries/${encodeURIComponent(d.key)}`}>{d.name}</Link>
          {d.kind === 'function' && <span className="dim iai-kind"> · function</span>}</h2>
        {d.definition && <p className="dim iai-def">{d.definition}</p>}
      </header>
      <div className="iai-figures">
        <div><b className="tnum">{n(d.kept)}</b><span>kept</span></div>
        <div><b className="tnum">{d.found == null ? '–' : n(d.found)}</b><span>found by its queries</span></div>
        {d.from_watch > 0 && (
          <div><b className="tnum">{n(d.from_watch)}</b><span>more from watch lists, counted apart</span></div>
        )}
        <div><b className="tnum">{n(d.authors)}</b><span>distinct authors</span></div>
        <div><b className="tnum">{n(d.reach)}</b><span>shares & copies</span></div>
      </div>
      {d.groups?.length > 0 && (
        <>
          <h3 className="iai-sub">By group</h3>
          <Bars counts={Object.fromEntries(d.groups.map((g) => [g.key, g.kept]))}
                labels={Object.fromEntries(d.groups.map((g) => [g.key, g.name]))} />
        </>
      )}
      <h3 className="iai-sub">By content type</h3>
      <Bars counts={d.by_type || {}} labels={TYPE_LABEL} order={types} />
      {stages.length > 0 && (
        <p className="dim iai-stages">
          Use cases by stage: {stages.map(([k, v]) => `${n(v)} ${STAGE_LABEL[k] || k}`).join(' · ')}
        </p>
      )}
      <h3 className="iai-sub">By platform</h3>
      <Bars counts={d.by_platform || {}} labels={PLATFORM_LABEL} />
      {Object.keys(d.by_month || {}).length > 1 && (
        <>
          <h3 className="iai-sub">By month posted</h3>
          <Months byMonth={d.by_month} />
        </>
      )}
      {d.undated > 0 && <p className="dim iai-note">{n(d.undated)} kept item(s) carry no posting date.</p>}
      <Link className="btn btn-ghost iai-open-btn" to={`/ai-in-industries/${encodeURIComponent(d.key)}`}>
        See the posts and every breakdown →
      </Link>
    </section>
  )
}

export default function IndustryAI() {
  useHead(PRIVATE.industryAi)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    industryAi().then((d) => alive && setData(d)).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const last = data?.last_run
  const filtered = (data?.dropped || []).reduce((s, r) => s + r.items, 0)
  // The active domains' names, from the contract the API reads: the lede names them
  // so it cannot go stale when the active set changes.
  const active = (data?.domains || []).filter((d) => d.active).map((d) => d.name)
  const activeText = active.length > 1
    ? `${active.slice(0, -1).join(', ')} and ${active[active.length - 1]}`
    : active[0]

  return (
    <div className="shell section-tight stack stack-4">
      <header className="stack stack-1">
        <span className="eyebrow">Industry AI</span>
        <h1 className="iai-h1">AI in industries</h1>
        <p className="dim iai-lede">
          How much data we have collected about how AI is used across industries and roles
          {activeText ? <> (now: {activeText})</> : null}, from Reddit, X, GitHub, Hacker News, dev.to,
          Bluesky and blogs, by keyword searches and by watched communities and accounts. Counts only:
          what was found, what the rules kept, and what they filtered out and why.
        </p>
        {last && (
          <p className="dim iai-note">
            Last run {fmtDayUtc(last.finished_at || last.started_at) || '–'} ({last.mode}, {last.status}).
          </p>
        )}
      </header>

      {err && <p className="iai-error">Could not load: {err}</p>}
      {!data && !err && <p className="dim">Loading…</p>}
      {data?.reason && <p className="iai-error">{data.reason}</p>}

      {data && !data.reason && (
        <>
          <div className="iai-totals">
            <div><b className="tnum">{n(data.collected)}</b><span>items collected</span></div>
            <div><b className="tnum">{n(data.kept)}</b><span>kept</span></div>
            <div><b className="tnum">{n(filtered)}</b><span>filtered out</span></div>
          </div>
          {data.collected === 0 && (
            <p className="dim">Nothing collected yet: no run has stored any item.</p>
          )}

          <div className="iai-grid">
            {/* Active domains, and any switched-off one that still holds data: a
                file of 20 umbrellas with five active shows five cards, not twenty. */}
            {data.domains.filter((d) => d.active !== false || d.kept > 0 || d.from_watch > 0)
              .map((d) => <DomainCard key={d.key} d={d} types={data.types} />)}
          </div>

          {data.unconfirmed?.kept > 0 && (
            <section className="card iai-card">
              <h2><Link className="iai-open" to="/ai-in-industries/unconfirmed">Domain unconfirmed</Link></h2>
              <p className="dim iai-def">
                Kept items whose finding domain&apos;s own terms did not confirm it. Counted here and in no
                domain above.
              </p>
              <div className="iai-figures"><div><b className="tnum">{n(data.unconfirmed.kept)}</b><span>kept</span></div></div>
              <Bars counts={data.unconfirmed.by_type || {}} labels={TYPE_LABEL} order={data.types} />
            </section>
          )}

          {data.general?.kept > 0 && (
            <section className="card iai-card">
              <h2><Link className="iai-open" to="/ai-in-industries/general">General AI</Link></h2>
              <p className="dim iai-def">
                Kept items from the watched communities, accounts and lists that name no industry or role:
                general AI news and opinion. Counted here and in no domain above, and apart from
                &quot;Domain unconfirmed&quot;.
              </p>
              <div className="iai-figures"><div><b className="tnum">{n(data.general.kept)}</b><span>kept</span></div></div>
              <Bars counts={data.general.by_type || {}} labels={TYPE_LABEL} order={data.types} />
            </section>
          )}

          {data.dropped?.length > 0 && (
            <section className="card iai-card">
              <h2>Filtered out, by reason</h2>
              <Bars
                counts={Object.fromEntries(data.dropped.map((r) => [r.reason, r.items]))}
                labels={REASON_LABEL}
              />
            </section>
          )}
        </>
      )}
    </div>
  )
}
