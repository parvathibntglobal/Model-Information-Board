import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageLinks, { ADMIN } from '../components/PageLinks'
import { industryAi } from '../api'
import IndustryAIInfo from '../components/IndustryAIInfo'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import { fmtDayUtc } from '../dates'
import { Bars, PLATFORM_LABEL, REASON_LABEL, STAGE_LABEL, TYPE_LABEL, countedAt, n } from '../industry-ai/parts'
import '../styles/industry-ai.css'

/**
 * AI IN INDUSTRIES (2026-11-20): how much data the Industry AI agent and its
 * observer have collected for each domain (industries and roles, from
 * contract/industry_ai.yaml). Signed in. The intro gives the number of domains,
 * from the data, and names none of them (Parvathi, 2026-11-24): the Info view
 * lists them and says which are active.
 *
 * COUNTS ONLY ON THIS SUMMARY. Its API sends no post text, link or author
 * (judge/industry_ai/view.py industry_ai_view). Each card opens its domain's own
 * page (routes/IndustryAIDomain.jsx, signed in), which lists the posts, each with
 * its text up to its first `excerpt_chars` characters and a link (#665). Every number
 * is a count of stored items, beside its denominator: what the domain's queries
 * found, and what the rules filtered out and why - so a small "kept" never reads as
 * "nothing out there" (rules 4 and 7). Items no domain's terms confirmed are counted
 * apart, never added to a domain (rule 6).
 *
 * TABS (2026-11-24, Parvathi): one population per tab, never mixed - the domains
 * collecting posts of their own, the switched-off ones holding only watch-list
 * posts, posts kept but filed under no domain, what was filtered out, and the
 * domains with nothing yet. Each tab names its count; the tab is in the address.
 */

/** Counts as one sorted line: "X 300 · Bluesky 104 · Reddit 67". */
function line(counts, labels) {
  return Object.entries(counts || {}).filter(([, v]) => v).sort((x, y) => y[1] - x[1])
    .map(([k, v]) => `${labels[k] || k} ${n(v)}`).join(' · ')
}
const sorted = (counts) => Object.fromEntries(
  Object.entries(counts || {}).filter(([, v]) => v).sort((x, y) => y[1] - x[1]))
const hasData = (d) => d.kept > 0 || d.from_watch > 0
const to = (key) => `/ai-in-industries/${encodeURIComponent(key)}`

function Badges({ d, off = true }) {
  return (
    <>
      {d.kind === 'function' && <span className="iai-badge">role</span>}
      {off && d.active === false && <span className="iai-badge iai-badge-off">switched off</span>}
    </>
  )
}

/**
 * A domain with posts of its own, as one clickable card that opens its page. Only
 * what a reader needs at a glance: how many were kept of how many found, by how many
 * accounts, what kind of posts, and from where. No month chart: nearly every post is
 * from the harvest window, so it drew one spike and read as a trend it is not. The
 * domain's own page has the months, with their range.
 */
function DomainCard({ d, note }) {
  const stages = ['deployed', 'pilot', 'first_hand'].filter((k) => d.by_stage?.[k])
    .map((k) => [k, d.by_stage[k]])
  const types = Object.entries(sorted(d.by_type))
  const rest = types.slice(4)
  const groups = (d.groups || []).filter((g) => g.kept)
  return (
    <Link className="card iai-card iai-card-link" to={to(d.key)} aria-label={`Open ${d.name}`}>
      <header className="iai-card-head">
        <div className="iai-card-title">
          <h2>{d.name}</h2>
          <Badges d={d} />
          <span className="iai-go" aria-hidden="true">→</span>
        </div>
        {(note || d.definition) && <p className="dim iai-def iai-clamp">{note || d.definition}</p>}
      </header>
      <div className="iai-figures">
        <div><b className="tnum">{n(d.kept)}</b><span>posts kept</span></div>
        {d.found != null && <div><b className="tnum">{n(d.found)}</b><span>found by its searches</span></div>}
        <div><b className="tnum">{n(d.authors)}</b><span>accounts</span></div>
      </div>
      <h3 className="iai-sub">What was kept</h3>
      <Bars counts={Object.fromEntries(types.slice(0, 4))} labels={TYPE_LABEL} />
      {rest.length > 0 && (
        <p className="dim iai-note">Also: {rest.map(([k, v]) => `${TYPE_LABEL[k] || k} ${n(v)}`).join(' · ')}</p>
      )}
      {stages.length > 0 && (
        <p className="iai-stages">
          <b>Use reported</b> <span className="dim">(stage guessed from the wording)</span>:{' '}
          {stages.map(([k, v]) => `${n(v)} ${STAGE_LABEL[k] || k}`).join(' · ')}
        </p>
      )}
      {groups.length > 0 && (
        <p className="iai-stages"><b>By group:</b> {groups.map((g) => `${g.name} ${n(g.kept)}`).join(' · ')}</p>
      )}
      <p className="iai-stages"><b>From:</b> {line(d.by_platform, PLATFORM_LABEL) || '–'}</p>
      {(d.from_watch > 0 || d.reach > 0 || d.undated > 0) && (
        <p className="dim iai-note">
          {[d.from_watch > 0 && `${n(d.from_watch)} more from watch lists, counted apart`,
            d.reach > 0 && `${n(d.reach)} shares & copies`,
            d.undated > 0 && `${n(d.undated)} with no posting date`].filter(Boolean).join(' · ')}
        </p>
      )}
    </Link>
  )
}

/** A domain with no posts of its own: one line. Clickable when it holds any posts. */
function DomainTile({ d, children }) {
  const body = (
    <>
      <div className="iai-card-title">
        <span>{d.name}</span>
        <Badges d={d} off={false} />
        {hasData(d) && <span className="iai-go" aria-hidden="true">→</span>}
      </div>
      <p className="dim iai-note">{children}</p>
    </>
  )
  return hasData(d)
    ? <Link className="card iai-tile iai-card-link" to={to(d.key)} aria-label={`Open ${d.name}`}>{body}</Link>
    : <div className="card iai-tile">{body}</div>
}

export default function IndustryAI() {
  useHead(PRIVATE.industryAi)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  // THE INFO VIEW (2026-11-24): `?view=info`, so it can be linked and the back
  // button returns to the counts. The counts are still loaded once, either way.
  const [params, setParams] = useSearchParams()
  const showInfo = params.get('view') === 'info'
  const toggleInfo = () => setParams(showInfo ? {} : { view: 'info' })

  useEffect(() => {
    let alive = true
    industryAi().then((d) => alive && setData(d)).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const last = data?.last_run
  // THE INTRO COUNTS THE DOMAINS FROM THE PAYLOAD (2026-11-24, Parvathi): every
  // domain in contract/industry_ai.yaml, active or not, so the number follows
  // the contract (rule 11). INDUSTRIES AND ROLES APART (#668 review, point 5):
  // each domain's `kind` is `industry` or `function` (a role in every industry),
  // and calling roles industries misnamed them. The Info view lists them.
  const kinds = (data?.domains || []).reduce((acc, d) => {
    acc[d.kind] = (acc[d.kind] || 0) + 1
    return acc
  }, {})
  const kindText = [
    kinds.industry && `${kinds.industry} ${kinds.industry === 1 ? 'industry' : 'industries'}`,
    kinds.function && `${kinds.function} ${kinds.function === 1 ? 'role' : 'roles'}`,
  ].filter(Boolean).join(' and ')
  const filtered = (data?.dropped || []).reduce((s, r) => s + r.items, 0)
  const domains = data?.domains || []
  const own = domains.filter((d) => d.kept > 0).sort((a, b) => b.kept - a.kept)
  const watchOnly = domains.filter((d) => !d.kept && d.from_watch > 0)
    .sort((a, b) => b.from_watch - a.from_watch)
  const empty = domains.filter((d) => !hasData(d))
  const unfiled = [data?.general, data?.unconfirmed].filter((b) => b?.kept > 0)

  const tabs = [
    { key: 'collecting', label: 'Collecting', count: own.length },
    { key: 'watch', label: 'Watch lists only', count: watchOnly.length },
    { key: 'unfiled', label: 'Not filed under a domain', count: unfiled.reduce((s, b) => s + b.kept, 0) },
    { key: 'filtered', label: 'Filtered out', count: filtered },
    { key: 'empty', label: 'Nothing collected', count: empty.length },
  ].filter((t) => t.count > 0 || t.key === 'collecting')
  const tab = tabs.some((t) => t.key === params.get('tab')) ? params.get('tab') : 'collecting'
  const pick = (k) => {
    const next = new URLSearchParams(params)
    if (k === 'collecting') next.delete('tab')
    else next.set('tab', k)
    setParams(next, { replace: true })
  }

  return (
    <div className="shell section-tight stack stack-4">
      <header className="stack stack-1">
        <div className="iai-head-row">
          <div className="stack stack-1">
            <span className="eyebrow">Industry AI</span>
            <h1 className="iai-h1">AI in industries{showInfo && <span className="dim"> · Info</span>}</h1>
          </div>
          <div className="page-links">
            {/* No public page: AI in industries is signed in. */}
            <PageLinks links={[
              { to: ADMIN.section('ai-in-industries'), label: 'Admin', title: 'Admin → Board & content → AI in industries' },
              { to: ADMIN.scheduler('industry-ai'), label: 'Schedule', title: 'Admin → Scheduler → Industry AI' },
            ]} />
            <button type="button" className="btn btn-ghost iai-info-btn" onClick={toggleInfo}
                    aria-pressed={showInfo}>
              {showInfo ? '← Counts' : 'ⓘ Info'}
            </button>
          </div>
        </div>
        <p className="dim iai-lede">
          How much data we have collected about AI in {kindText || 'industries and roles'}, from Reddit, X, GitHub,
          Hacker News, dev.to, Bluesky and blogs, by keyword searches and by watched communities and
          accounts. Click an industry to see its posts and every breakdown.
        </p>
        {last && (
          <p className="dim iai-note">
            Last run {fmtDayUtc(last.finished_at || last.started_at) || '–'} ({last.mode}, {last.status}).
            {countedAt(data?.counted_at) && <> Counted at {countedAt(data.counted_at)}; recounted on a visit after 10 minutes, and recounted when over an hour old.</>}
          </p>
        )}
      </header>

      {showInfo && <IndustryAIInfo />}

      {!showInfo && err && <p className="iai-error">Could not load: {err}</p>}
      {!showInfo && !data && !err && <p className="dim">Loading…</p>}
      {!showInfo && data?.reason && <p className="iai-error">{data.reason}</p>}

      {!showInfo && data && !data.reason && (
        <>
          <div className="iai-totals">
            <div><b className="tnum">{n(data.collected)}</b><span>items collected</span></div>
            <div><b className="tnum">{n(data.kept)}</b><span>kept</span></div>
            <div><b className="tnum">{n(filtered)}</b><span>filtered out</span></div>
            {data.pending > 0 && (
              <div><b className="tnum">{n(data.pending)}</b><span>waiting to be labelled</span></div>
            )}
          </div>
          {data.pending > 0 && (
            <p className="dim iai-note">
              {n(data.pending)} saved, waiting to be labelled: a run&apos;s labelling failed after its posts
              were saved. The next run or a relabel labels them. They are counted in no domain and not as
              filtered out.
            </p>
          )}
          {data.collected === 0 && (
            <p className="dim">Nothing collected yet: no run has stored any item.</p>
          )}

          <div className="iai-tabbar" role="tablist" aria-label="What to show">
            {tabs.map((t) => (
              <button type="button" role="tab" key={t.key} aria-selected={tab === t.key}
                      className={`iai-tabbtn${tab === t.key ? ' iai-tabbtn-on' : ''}`} onClick={() => pick(t.key)}>
                {t.label} <span className="iai-tabn tnum">{n(t.count)}</span>
              </button>
            ))}
          </div>

          {tab === 'collecting' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">Domains whose own searches are running, most posts kept first.</p>
              <div className="iai-grid">{own.map((d) => <DomainCard key={d.key} d={d} />)}</div>
            </section>
          )}

          {tab === 'watch' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">
                These domains&apos; own searches are switched off, but posts from the watched communities and
                accounts were filed under them by their words. Counted apart, never as the domain&apos;s own.
              </p>
              <div className="iai-tiles">
                {watchOnly.map((d) => (
                  <DomainTile key={d.key} d={d}>
                    {n(d.from_watch)} post{d.from_watch === 1 ? '' : 's'} from watch lists
                  </DomainTile>
                ))}
              </div>
            </section>
          )}

          {tab === 'unfiled' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">Kept, but counted in no domain.</p>
              <div className="iai-grid">
                {data.general?.kept > 0 && (
                  <DomainCard d={data.general}
                              note="From the watched communities and accounts, naming no industry or role: general AI news and opinion." />
                )}
                {data.unconfirmed?.kept > 0 && (
                  <DomainCard d={data.unconfirmed}
                              note="Found by a domain's searches, but that domain's own words did not confirm it." />
                )}
              </div>
            </section>
          )}

          {tab === 'filtered' && (
            <section className="card iai-card" role="tabpanel">
              <h2>Filtered out, by reason</h2>
              <p className="dim iai-note">
                Every post the rules removed, across all domains. Each domain&apos;s page lists its own, with the posts.
              </p>
              <Bars counts={sorted(Object.fromEntries(data.dropped.map((r) => [r.reason, r.items])))}
                    labels={REASON_LABEL} />
            </section>
          )}

          {tab === 'empty' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">Domains in the contract that hold no posts yet.</p>
              <div className="iai-tiles">
                {empty.map((d) => (
                  <DomainTile key={d.key} d={d}>
                    {d.active === false ? 'Its searches are switched off.' : 'Its searches have not kept anything yet.'}
                  </DomainTile>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
