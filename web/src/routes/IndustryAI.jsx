import { useEffect, useState } from 'react'
import { industryAi } from '../api'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import { fmtDayUtc } from '../dates'
import '../styles/industry-ai.css'

/**
 * AI IN INDUSTRIES (2026-11-20): how much data the Industry AI agent has
 * collected in each of five industries. Signed in.
 *
 * COUNTS ONLY. The API sends no post text, link or author (judge/industry_ai/
 * view.py), so nothing here can show one. Every number is a count of stored
 * items, beside its denominator: what the domain's queries found, and what the
 * rules filtered out and why - so a small "kept" never reads as "nothing out
 * there" (rules 4 and 7). Items no domain's terms confirmed are counted apart,
 * never added to a domain (rule 6).
 */

const TYPE_LABEL = {
  use_case: 'Use cases', how_to: 'How-to & tips', tool_or_product: 'Tools & products',
  research: 'Research', news: 'News', discussion: 'Discussion',
}
const STAGE_LABEL = { deployed: 'deployed', pilot: 'pilot', first_hand: 'first-hand' }
const PLATFORM_LABEL = {
  reddit: 'Reddit', x: 'X', github: 'GitHub', hackernews: 'Hacker News', devto: 'dev.to',
  bluesky: 'Bluesky', feeds: 'Blogs & feeds',
}
const REASON_LABEL = {
  no_ai_term: 'No AI term', no_domain_term: 'No industry term',
  outside_window: 'Older than the window', shared_link: 'Same article shared elsewhere',
  repeat_post: 'Same author, same post again', near_duplicate: 'Near-duplicate text',
  too_short: 'Too short', bot: 'Bot account', non_english: 'Not English', spam: 'Spam or scam',
  promo: 'Sponsored or affiliate', hiring: 'Hiring or job ad', signup_ad: 'Sign-up ad',
}

const n = (v) => (v ?? 0).toLocaleString('en-GB')

function Bars({ counts, labels, order }) {
  const keys = (order || Object.keys(counts)).filter((k) => counts[k])
  if (!keys.length) return <p className="dim iai-none">None yet.</p>
  const max = Math.max(...keys.map((k) => counts[k]))
  return (
    <ul className="iai-bars">
      {keys.map((k) => (
        <li key={k}>
          <span className="iai-bar-label">{labels?.[k] || k}</span>
          <span className="iai-bar-track"><span className="iai-bar" style={{ width: `${(100 * counts[k]) / max}%` }} /></span>
          <span className="iai-bar-n tnum">{n(counts[k])}</span>
        </li>
      ))}
    </ul>
  )
}

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
        <h2>{d.name}{d.kind === 'function' && <span className="dim iai-kind"> · function</span>}</h2>
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

  return (
    <div className="shell section-tight stack stack-4">
      <header className="stack stack-1">
        <span className="eyebrow">Industry AI</span>
        <h1 className="iai-h1">AI in industries</h1>
        <p className="dim iai-lede">
          How much data we have collected about AI in finance, healthcare, hospitality, engineering and
          governance, from Reddit, X, GitHub, Hacker News, dev.to, Bluesky and blogs. Counts only: what the
          searches found, what the rules kept, and what they filtered out and why.
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
              <h2>Domain unconfirmed</h2>
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
              <h2>General AI</h2>
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
