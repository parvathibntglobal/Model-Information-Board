import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import PageLinks, { ADMIN } from '../components/PageLinks'
import IndustryAIInfo from '../components/IndustryAIInfo'
import { aiWatch, aiWatchPosts } from '../api'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import { fmtDayUtc } from '../dates'
import { Bars, KIND_LABEL, PLATFORM_LABEL, REASON_LABEL, TYPE_LABEL, countedAt, jumpTo, n } from '../industry-ai/parts'
import { FLAG_LABEL, Item, SORT_LABEL, shorten } from '../industry-ai/posts'
import '../styles/industry-ai.css'

/**
 * AI WATCH (2026-11-25, Parvathi; anooj's proposal on #667): what the OBSERVER
 * agent found - the newest posts of the watched communities, accounts and lists,
 * read with no keyword. Signed in. A post only the watch lists found is counted here;
 * one a keyword search found is the Industry AI agent's, never both
 * (judge/industry_ai/view.py KEYWORD_ARM / WATCH_ARM). Unrelated to AI in industries
 * for a reader, so the two pages do not link to each other (Parvathi, 2026-11-25).
 *
 * TABS: Feed (General AI posts, the observer's main yield; or every kept post),
 * Sources (each watched community, account and list: what it found, kept and lost),
 * People (one person across platforms, `watch.people`), Mentions (watched posts that
 * name an industry, linking to its page), Filtered (what the rules removed, and why).
 * The Info view explains the agent and lists its watch lists from the contract.
 *
 * Counts come from GET /ai-watch, posts from GET /ai-watch/posts; both say when they
 * were counted (rule 11). No number is written here: every figure is from the API.
 */

const TABS = ['feed', 'sources', 'people', 'mentions', 'filtered', 'unread']
const TAB_LABEL = {
  feed: 'Feed', sources: 'Sources', people: 'People', mentions: 'Mentions an industry', filtered: 'Filtered out',
  unread: 'Not readable',
}
/** What a not-readable post's media was (`media_kind`, collect/industry_ai/media.py). */
const MEDIA_LABEL = { image: 'A picture', gallery: 'Several pictures', video: 'A video' }
/** What reading a not-readable picture's text did (`ocr_status`, #679 step 3, shadow
 *  mode). `not_tried` is a picture nobody tried to read - not "no text" (rule 4). */
const PICTURE_READ_LABEL = {
  ok: 'Text read', no_text: 'No text found', failed: 'Could not be read', too_large: 'Too large',
  over_cap: 'Over the run’s limit', refused: 'Refused by robots.txt', not_tried: 'Not tried',
}
const FILTERS = ['type', 'platform', 'kind', 'reason', 'domain', 'source', 'account', 'person', 'q']
const FILTER_LABEL = {
  type: 'Content type', platform: 'Platform', kind: 'Kind', reason: 'Reason', domain: 'Industry',
  source: 'Source', account: 'X account', person: 'Person', q: 'Text contains',
}
const PAGE = 25
// The post list every click that changes it scrolls to (jumpTo).
const POSTS_ID = 'aiw-posts'
const PLATFORM_ORDER = ['x', 'reddit', 'bluesky', 'hackernews', 'instagram']
// `watch.people` keys are snake_case names (simon_willison -> Simon Willison).
const personName = (k) => k.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
const plat = (p) => PLATFORM_LABEL[p] || p
const sorted = (counts) => Object.fromEntries(
  Object.entries(counts || {}).filter(([, v]) => v).sort((x, y) => y[1] - x[1]))

/** A source key ("watch:reddit:r/ClaudeAI") or an X handle, as the reader names it. */
function sourceWords(name, v) {
  if (name === 'source') {
    const [, p, ...rest] = String(v).split(':')
    const s = rest.join(':').replace(/^from:/, '').replace(/^ig:/, '@').replace(/^hn:list:/, '')
      .replace(/^hn:author:/, 'by ')
    return `${plat(p)} ${s}`
  }
  if (name === 'account') return `@${v}`
  if (name === 'person') return personName(v)
  return v
}

function Select({ name, rows, value, onChange, labels }) {
  const options = (rows || []).filter((r) => r.value)
  if (!options.length && !value) return null
  return (
    <label className="iai-filter">
      <span>{FILTER_LABEL[name]}</span>
      <select value={value} onChange={(e) => onChange({ [name]: e.target.value })}>
        <option value="">Any</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{shorten(labels?.[o.value] || o.value)} ({n(o.items)})</option>
        ))}
      </select>
    </label>
  )
}

/** One list of the observer's posts, with its filters, in `scope`. */
function Posts({ scope, params, update, note }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [text, setText] = useState(params.get('q') || '')
  const sort = params.get('sort') || 'newest'
  const offset = Math.max(0, Number(params.get('offset')) || 0)
  const filters = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f, params.get(f) || ''])), [params])

  useEffect(() => {
    let alive = true
    setLoading(true)
    aiWatchPosts({ scope, sort, offset, limit: PAGE, ...filters })
      .then((d) => { if (alive) { setData(d); setErr(null) } })
      .catch((e) => alive && setErr(e.message))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [scope, sort, offset, filters])

  if (err) return <p id={POSTS_ID} className="iai-error iai-anchor">Could not load the posts: {err}</p>
  if (!data) return <p id={POSTS_ID} className="dim iai-anchor">Loading posts…</p>
  const f = data.facets || {}
  const names = data.domain_names || {}
  const active = FILTERS.filter((x) => filters[x])
  const last = Math.min(offset + PAGE, data.matching)
  const word = (name, v) => ({ type: TYPE_LABEL, platform: PLATFORM_LABEL, kind: KIND_LABEL, reason: REASON_LABEL,
    domain: names }[name]?.[v] || sourceWords(name, v))

  return (
    <section id={POSTS_ID} className="stack stack-2 iai-anchor">
      <div className="iai-filterbar">
        <form className="iai-search" onSubmit={(e) => { e.preventDefault(); update({ q: text.trim() }) }}>
          <input type="search" value={text} onChange={(e) => setText(e.target.value)}
                 placeholder="Search the text" aria-label="Search the post text" />
        </form>
        <Select name="type" rows={f.type} value={filters.type} onChange={update} labels={TYPE_LABEL} />
        <Select name="platform" rows={f.platform} value={filters.platform} onChange={update} labels={PLATFORM_LABEL} />
        <Select name="kind" rows={f.kind} value={filters.kind} onChange={update} labels={KIND_LABEL} />
        {scope === 'dropped' && <Select name="reason" rows={f.reason} value={filters.reason} onChange={update} labels={REASON_LABEL} />}
        {scope !== 'general' && <Select name="domain" rows={f.domain} value={filters.domain} onChange={update} labels={names} />}
        <label className="iai-filter">
          <span>Order</span>
          <select value={sort} onChange={(e) => update({ sort: e.target.value === 'newest' ? '' : e.target.value })}>
            {Object.entries(SORT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
      {active.length > 0 && (
        <div className="iai-active">
          <span className="dim iai-note">Filtered by</span>
          {active.map((name) => (
            <button type="button" key={name} className="chip" onClick={() => update({ [name]: '' })} title="Remove this filter">
              {FILTER_LABEL[name]}: {shorten(word(name, filters[name]), 50)} ×
            </button>
          ))}
          <button type="button" className="btn btn-ghost"
                  onClick={() => { setText(''); update(Object.fromEntries(FILTERS.map((x) => [x, '']))) }}>
            Clear all
          </button>
        </div>
      )}
      {note && <p className="dim iai-note">{note}</p>}
      {sort === 'engaged' && (
        <p className="dim iai-note">Most engaged: ordered by the platform&apos;s own counts (views, likes, comments and so on) added together, so X posts with view counts tend to come first.</p>
      )}
      {data.matching === 0
        ? <p className="dim">No posts match{active.length ? ' these filters' : ''}.</p>
        : <p className="dim iai-note">Showing {n(offset + 1)}–{n(last)} of {n(data.matching)}{loading ? ' · loading…' : ''}</p>}
      <ul className="iai-items">
        {data.items.map((it) => <Item key={it.id} it={it} domainNames={names} />)}
      </ul>
      {data.matching > PAGE && (
        <div className="iai-pager">
          <button type="button" className="btn btn-ghost" disabled={offset === 0}
                  onClick={() => { update({ offset: String(Math.max(0, offset - PAGE)) }); jumpTo(POSTS_ID) }}>← Previous</button>
          <button type="button" className="btn btn-ghost" disabled={last >= data.matching}
                  onClick={() => { update({ offset: String(offset + PAGE) }); jumpTo(POSTS_ID) }}>Next →</button>
        </div>
      )}
      <p className="dim iai-note">
        Each post shows its text up to its first {n(data.excerpt_chars)} characters (most are shorter, so are shown
        whole), with a link to the original. Labels are set by code rules ({data.rules_version}); no language model
        read these posts.{countedAt(data.counted_at) && ` Counted at ${countedAt(data.counted_at)}.`}
      </p>
    </section>
  )
}

/** A source's flagged posts, flag by flag, as words (`flags` from GET /ai-watch). */
const flagWords = (flags) => Object.entries(flags || {}).sort((a, b) => b[1] - a[1])
  .map(([f, c]) => `${FLAG_LABEL[f] || f}: ${n(c)}`).join(' · ') || undefined

/** Every watched source on one platform, as a table folded under its heading. */
function SourceTable({ platform, rows, onOpen }) {
  // Saved, not yet labelled (#663): shown only when some are, so Found = Kept +
  // Filtered out + Waiting always reads true (#673 review, point 5).
  const waits = rows.some((r) => r.waiting > 0)
  // Not readable (iai-5): a picture or video with too few words to judge. Shown only
  // when some are, so Found = Kept + Filtered out + Waiting + Not readable.
  const unreads = rows.some((r) => r.unread > 0)
  const quiet = rows.filter((r) => r.listed && !r.found).length
  const gone = rows.filter((r) => !r.listed).length
  const kept = rows.reduce((s, r) => s + r.kept, 0)
  const byYield = [...rows].sort((a, b) => b.kept - a.kept || b.found - a.found
    || a.source.localeCompare(b.source))
  return (
    <details className="card iai-fold">
      <summary>
        <span>{plat(platform)}</span>
        <span className="dim iai-note">
          {n(rows.length - gone)} watched · {n(kept)} kept
          {quiet > 0 && ` · ${n(quiet)} nothing found yet`}
          {gone > 0 && ` · ${n(gone)} no longer listed`}
        </span>
      </summary>
      <div className="iai-table-wrap">
        <table className="iai-table">
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col" className="tnum">Found</th>
              <th scope="col" className="tnum">Kept</th>
              <th scope="col" className="tnum">Filtered out</th>
              {waits && <th scope="col" className="tnum" title="Saved, not yet labelled: the next run or a relabel labels them">Waiting</th>}
              {unreads && <th scope="col" className="tnum" title="A picture or video with too few words to judge: not read, so not filtered out">Not readable</th>}
              <th scope="col" className="tnum" title="Kept posts carrying a flag for review (product support, short reply, heavy poster...): a busy source that is mostly flagged is the one to read first">Flagged</th>
              <th scope="col" className="tnum" title="Also found by an industry's keyword search, so counted by the Industry AI agent, not here">Also by keyword</th>
              <th scope="col">Newest post</th>
            </tr>
          </thead>
          <tbody>
            {byYield.map((r) => (
              <tr key={`${r.key || r.account}-${r.source}`} className={r.found ? undefined : 'dim'}>
                <th scope="row">
                  {r.found > 0
                    ? <button type="button" className="iai-pick" onClick={() => onOpen(r)}>{r.source}</button>
                    : r.source}
                  {!r.listed && <span className="iai-tag">no longer listed</span>}
                </th>
                <td className="tnum">{n(r.found)}</td>
                <td className="tnum">{n(r.kept)}</td>
                <td className="tnum">{n(r.filtered)}</td>
                {waits && <td className="tnum">{n(r.waiting)}</td>}
                {unreads && <td className="tnum">{n(r.unread)}</td>}
                <td className="tnum" title={flagWords(r.flags)}>
                  {r.kept > 0 ? `${n(r.flagged)} (${Math.round((100 * r.flagged) / r.kept)}%)` : n(r.flagged)}
                </td>
                <td className="tnum">{n(r.also_keyword)}</td>
                <td>{r.newest ? fmtDayUtc(r.newest) : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

export default function AIWatch() {
  useHead(PRIVATE.aiWatch)
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const showInfo = params.get('view') === 'info'
  const tab = TABS.includes(params.get('tab')) ? params.get('tab') : 'feed'
  const feedScope = params.get('scope') === 'kept' ? 'kept' : 'general'

  useEffect(() => {
    let alive = true
    aiWatch().then((d) => alive && setData(d)).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const update = (changes) => {
    const next = new URLSearchParams(params)
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    if (!('offset' in changes)) next.delete('offset')
    setParams(next)
  }
  /** A bar or a row picks a filter: apply it, then show the posts it picked. */
  const show = (changes) => { update(changes); jumpTo(POSTS_ID) }
  /** A new tab starts with no filters: each tab is its own list. */
  const pick = (t, extra = {}) => {
    const next = new URLSearchParams()
    if (t !== 'feed') next.set('tab', t)
    Object.entries(extra).forEach(([k, v]) => v && next.set(k, v))
    setParams(next)
  }
  const openSource = (r) => {
    pick('feed', { scope: 'kept', ...(r.account ? { account: r.account } : { source: r.key }) })
    jumpTo(POSTS_ID)
  }

  const byPlatform = useMemo(() => {
    const out = {}
    for (const s of data?.sources || []) (out[s.platform] = out[s.platform] || []).push(s)
    return out
  }, [data])
  const platforms = [...PLATFORM_ORDER.filter((p) => byPlatform[p]),
    ...Object.keys(byPlatform).filter((p) => !PLATFORM_ORDER.includes(p))]
  const counts = {
    feed: data?.general, sources: data?.sources?.filter((s) => s.listed).length,
    people: data?.people?.length, mentions: data?.mentions, filtered: data?.filtered,
    unread: data?.unread,
  }
  const last = data?.last_run
  // A SOURCE'S KEPT IS NOT ALWAYS WHAT ITS LIST SHOWS (#673 review, point 4, rule 7):
  // a kept post a keyword search also found belongs to the Industry AI agent, so the
  // Feed leaves it out. Say how many, beside the list a source row opened.
  const opened = (data?.sources || []).find((s) => (params.get('source') && s.key === params.get('source'))
    || (params.get('account') && s.account === params.get('account')?.toLowerCase()))
  const sourceNote = opened?.kept_keyword > 0
    ? `${n(opened.kept_keyword)} more of ${opened.source}'s ${n(opened.kept)} kept posts are not listed here: a keyword search found them too, so the Industry AI agent counts them.`
    : null

  return (
    <div className="shell section-tight stack stack-4">
      <header className="stack stack-1">
        <div className="iai-head-row">
          <div className="stack stack-1">
            <span className="eyebrow">Observer agent</span>
            <h1 className="iai-h1">AI Watch{showInfo && <span className="dim"> · Info</span>}</h1>
          </div>
          <div className="page-links">
            {/* No public page: AI Watch is signed in. */}
            <PageLinks links={[
              { to: ADMIN.section('ai-in-industries'), label: 'Admin', title: 'Admin → Board & content → AI in industries' },
              { to: ADMIN.scheduler('industry-ai'), label: 'Schedule', title: 'Admin → Scheduler → Industry AI' },
            ]} />
            <button type="button" className="btn btn-ghost iai-info-btn" aria-pressed={showInfo}
                    onClick={() => update({ view: showInfo ? '' : 'info' })}>
              {showInfo ? '← Counts' : 'ⓘ Info'}
            </button>
          </div>
        </div>
        <p className="dim iai-lede">
          What the people, communities and lists we watch are saying about AI: the newest posts of chosen X,
          Reddit, Bluesky, Hacker News and Instagram sources, read with no keyword. Most name no industry.
        </p>
        {data && !data.reason && (
          <p className="dim iai-note">
            The observer agent is {data.enabled === true ? 'on' : data.enabled === false ? 'off in the contract (runs started by hand only)' : 'not set'}.
            {last && <> Last run {fmtDayUtc(last.finished_at || last.started_at) || '–'} ({last.mode}, {last.status}).</>}
            {countedAt(data.counted_at) && <> Counted at {countedAt(data.counted_at)}; recounted on a visit after 10 minutes, and recounted when over an hour old.</>}
          </p>
        )}
      </header>

      {showInfo && <IndustryAIInfo agent="watch" />}

      {!showInfo && err && <p className="iai-error">Could not load: {err}</p>}
      {!showInfo && !data && !err && <p className="dim">Loading…</p>}
      {!showInfo && data?.reason && <p className="iai-error">{data.reason}</p>}

      {!showInfo && data && !data.reason && (
        <>
          <div className="iai-totals">
            <div><b className="tnum">{n(data.collected)}</b><span>posts collected</span></div>
            <div><b className="tnum">{n(data.kept)}</b><span>kept</span></div>
            <div><b className="tnum">{n(data.general)}</b><span>General AI</span></div>
            <div><b className="tnum">{n(data.mentions)}</b><span>mention an industry</span></div>
            <div><b className="tnum">{n(data.filtered)}</b><span>filtered out</span></div>
            <div><b className="tnum">{n(data.authors)}</b><span>authors</span></div>
            {data.pending > 0 && <div><b className="tnum">{n(data.pending)}</b><span>waiting to be labelled</span></div>}
            {data.unread > 0 && <div><b className="tnum">{n(data.unread)}</b><span>not readable (picture or video)</span></div>}
          </div>
          {data.collected === 0 && <p className="dim">Nothing collected yet: no run has read the watch lists.</p>}

          <div className="iai-tabbar" role="tablist" aria-label="What to show">
            {TABS.map((t) => (
              <button type="button" role="tab" key={t} aria-selected={tab === t}
                      className={`iai-tabbtn${tab === t ? ' iai-tabbtn-on' : ''}`} onClick={() => pick(t)}>
                {TAB_LABEL[t]} {counts[t] != null && <span className="iai-tabn tnum">{n(counts[t])}</span>}
              </button>
            ))}
          </div>

          {tab === 'feed' && (
            <section className="stack stack-2" role="tabpanel">
              <div className="iai-tabbar iai-tabbar-sub" role="tablist" aria-label="Which posts">
                <button type="button" role="tab" aria-selected={feedScope === 'general'}
                        className={`iai-tabbtn${feedScope === 'general' ? ' iai-tabbtn-on' : ''}`}
                        onClick={() => update({ scope: '' })}>
                  General AI <span className="iai-tabn tnum">{n(data.general)}</span>
                </button>
                <button type="button" role="tab" aria-selected={feedScope === 'kept'}
                        className={`iai-tabbtn${feedScope === 'kept' ? ' iai-tabbtn-on' : ''}`}
                        onClick={() => update({ scope: 'kept' })}>
                  Every kept post <span className="iai-tabn tnum">{n(data.kept)}</span>
                </button>
              </div>
              <p className="dim iai-note">
                {feedScope === 'general'
                  ? 'Watched posts that name an AI term but no industry: AI news, launches, tools, how-tos and opinion.'
                  : 'Every post the watch lists kept: General AI and the posts that mention an industry.'}
              </p>
              <details className="iai-more">
                <summary>What kind of posts</summary>
                <Bars counts={sorted(feedScope === 'general' ? data.general_by_type : data.by_type)} labels={TYPE_LABEL}
                      onPick={(v) => show({ type: v })} />
                {feedScope === 'kept' && (
                  <>
                    <h3 className="iai-sub">From</h3>
                    <Bars counts={sorted(data.by_platform)} labels={PLATFORM_LABEL} onPick={(v) => show({ platform: v })} />
                  </>
                )}
              </details>
              <Posts scope={feedScope} params={params} update={update} note={sourceNote} />
            </section>
          )}

          {tab === 'sources' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">
                Every community, account and list the observer watches, from the contract, with what it found. Open a
                platform; click a source to read its posts. &quot;Found&quot; counts every post the source brought in,
                kept or not, including posts an industry&apos;s keyword search also found (&quot;Also by
                keyword&quot;, counted by the Industry AI agent, not here). &quot;Flagged&quot; is how many of its kept posts
                carry a flag for review, and their share of its kept posts; point at it to see which flags. A source that found
                nothing is greyed: quiet, or worth checking.
              </p>
              <div className="stack stack-2">
                {platforms.map((p) => <SourceTable key={p} platform={p} rows={byPlatform[p]} onOpen={openSource} />)}
              </div>
            </section>
          )}

          {tab === 'people' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">
                People watched on more than one platform, each counted as one author. Kept posts by platform; click a
                name to read them.
              </p>
              {data.people.length === 0
                ? <p className="dim">No one is mapped across platforms in the contract.</p>
                : (
                  <div className="iai-table-wrap card">
                    <table className="iai-table">
                      <thead>
                        <tr><th scope="col">Person</th><th scope="col">Handles</th><th scope="col" className="tnum">Kept</th><th scope="col">By platform</th></tr>
                      </thead>
                      <tbody>
                        {[...data.people].sort((a, b) => b.kept - a.kept || a.key.localeCompare(b.key)).map((p) => (
                          <tr key={p.key} className={p.kept ? undefined : 'dim'}>
                            <th scope="row">
                              {p.kept > 0
                                ? <button type="button" className="iai-pick" onClick={() => { pick('feed', { scope: 'kept', person: p.key }); jumpTo(POSTS_ID) }}>{personName(p.key)}</button>
                                : personName(p.key)}
                            </th>
                            <td>{Object.entries(p.handles).map(([pl, h]) => `${plat(pl)} ${pl === 'x' ? `@${h}` : h}`).join(' · ')}</td>
                            <td className="tnum">{n(p.kept)}</td>
                            <td>{Object.entries(p.by_platform).map(([pl, v]) => `${plat(pl)} ${n(v)}`).join(' · ') || '–'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
            </section>
          )}

          {tab === 'mentions' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">
                Watched posts that name an industry&apos;s keywords, filed under every industry they name, so a post can
                count under two. Click an industry to read its posts.
              </p>
              <section className="card iai-card">
                <Bars counts={Object.fromEntries(data.mentioned.map((m) => [m.key, m.items]))}
                      labels={Object.fromEntries(data.mentioned.map((m) => [m.key, m.name]))}
                      picked={params.get('domain') || undefined}
                      onPick={(v) => show({ domain: v })} />
              </section>
              <Posts scope="mentions" params={params} update={update} />
            </section>
          )}

          {tab === 'filtered' && (
            <section className="stack stack-2" role="tabpanel">
              <section className="card iai-card">
                <h2>Filtered out, by reason</h2>
                <p className="dim iai-note">What the rules removed from the watch lists&apos; posts. Click a reason to see its posts.</p>
                <Bars counts={sorted(Object.fromEntries(data.dropped.map((r) => [r.reason, r.items])))}
                      labels={REASON_LABEL} picked={params.get('reason') || undefined}
                      onPick={(v) => show({ reason: v })} />
              </section>
              <Posts scope="dropped" params={params} update={update} />
            </section>
          )}

          {tab === 'unread' && (
            <section className="stack stack-2" role="tabpanel">
              <section className="card iai-card">
                <h2>Not readable: a picture or a video with too few words</h2>
                <p className="dim iai-note">
                  This page reads words only. These posts&apos; content is in a picture or a video, and their few words
                  cannot say whether they are about AI, so they are not counted as filtered out: nobody read them. Open
                  one to see it on its platform.
                </p>
                {Object.keys(data.unread_by_media || {}).length > 0 && (
                  <Bars counts={sorted(data.unread_by_media)} labels={MEDIA_LABEL} />
                )}
                {Object.keys(data.unread_pictures_by_read || {}).some((k) => k !== 'not_tried') && (
                  <>
                    <h3>The text in their pictures (shadow mode)</h3>
                    <p className="dim iai-note">
                      The first picture of a not-readable picture post is read for its text, where the picture&apos;s host
                      allows it. That text decides nothing yet: it is counted, and checked by hand, before it can.{' '}
                      With their picture&apos;s text,{' '}
                      <span className="tnum">{data.unread_pictures_would_pass}</span> would have passed the AI and
                      industry word check.
                    </p>
                    <Bars counts={sorted(data.unread_pictures_by_read)} labels={PICTURE_READ_LABEL} />
                  </>
                )}
              </section>
              <Posts scope="unread" params={params} update={update} />
            </section>
          )}
        </>
      )}
    </div>
  )
}
