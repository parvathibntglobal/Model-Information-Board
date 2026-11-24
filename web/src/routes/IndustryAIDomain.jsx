import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { industryAiDomain } from '../api'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import { fmtDayUtc } from '../dates'
import {
  Bars, KIND_LABEL, PLATFORM_LABEL, REASON_LABEL, STAGE_LABEL, TYPE_LABEL, n,
} from '../industry-ai/parts'
import '../styles/industry-ai.css'

/**
 * ONE DOMAIN OF "AI IN INDUSTRIES" (2026-11-24, Parvathi), opened from its card on
 * /ai-in-industries. Signed in. Everything the Industry AI agent stored for the
 * domain: the card's counts, every breakdown its labels allow (each one a filter),
 * and the posts - an EXCERPT of each, with its link, author id, date, engagement and
 * every label the code rules gave it (judge/industry_ai/view.py
 * `industry_ai_domain_view`).
 *
 * Three populations, never added together (rules 4 and 7): kept by the domain's own
 * queries; kept from the watch lists and filed here by their terms (counted apart on
 * the card too); and filtered out, with the reason. Every list says how many match.
 * The filters live in the address, so a view can be shared with the team.
 */

const SCOPE_LABEL = {
  kept: 'Kept',
  from_watch: 'From watch lists',
  dropped: 'Filtered out',
}
const SORT_LABEL = {
  newest: 'Newest posted', oldest: 'Oldest posted', engaged: 'Most engaged', first_seen: 'Newest found',
}
const ENGAGEMENT_LABEL = {
  views: 'views', score: 'score', bookmarks: 'bookmarks', comments: 'comments', reposts: 'reposts',
  likes: 'likes', quotes: 'quotes', points: 'points', reactions: 'reactions',
}
const FILTERS = ['type', 'kind', 'platform', 'stage', 'reason', 'flag', 'group', 'term',
  'ai_term', 'query', 'month', 'q']
const FILTER_LABEL = {
  type: 'Content type', kind: 'Kind', platform: 'Platform', stage: 'Stage', reason: 'Reason',
  flag: 'Flag', group: 'Group', term: 'Industry word', ai_term: 'AI term', query: 'Found by',
  month: 'Month posted', q: 'Text contains',
}
const PAGE = 25

/** "iai:retail:x:<query>" -> "X search: <query>"; "watch:reddit:r/x" -> "Reddit watch: r/x". */
function queryLabel(key) {
  const [lane, a, b, ...rest] = String(key).split(':')
  if (lane === 'iai') return `${PLATFORM_LABEL[b] || b} search: ${rest.join(':')}`
  if (lane === 'watch') return `${PLATFORM_LABEL[a] || a} watch: ${[b, ...rest].join(':')}`
  return key
}
function flagLabel(f) {
  if (f.startsWith('also_matches:')) return `also matches ${f.slice(13).replace(/_/g, ' ')}`
  if (f.startsWith('domain_from_terms:')) return `filed by its terms (${f.slice(18).replace(/_/g, ' ')})`
  return f.replace(/_/g, ' ')
}
/** X keeps the handle in the link; other platforms give an id only. */
function authorOf(it) {
  if (it.platform === 'x') {
    const m = /x\.com\/([^/]+)\/status/.exec(it.url || '')
    if (m && m[1] !== 'i') return `@${m[1]}`
  }
  if (it.platform === 'hackernews' && it.author_id) return it.author_id
  return it.author_id ? `id ${it.author_id}` : 'no author id'
}
/** A filter's value in words, for its chip. */
function chipValue(name, v, groupNames) {
  const labels = { type: TYPE_LABEL, kind: KIND_LABEL, platform: PLATFORM_LABEL, stage: STAGE_LABEL,
    reason: REASON_LABEL, group: groupNames }[name]
  if (labels) return labels[v] || v
  if (name === 'query') return queryLabel(v)
  if (name === 'flag') return flagLabel(v)
  return v
}
const toCounts = (rows) => Object.fromEntries((rows || []).map((r) => [r.value ?? '(none)', r.items]))

function Facet({ title, rows, labels, name, filters, setFilter, note, wide }) {
  if (!rows?.length) return null
  return (
    <section className={`card iai-card${wide ? ' iai-wide' : ''}`}>
      <h3 className="iai-sub">{title}</h3>
      {note && <p className="dim iai-note">{note}</p>}
      <Bars counts={toCounts(rows)} labels={labels} picked={filters[name]}
            onPick={(v) => v !== '(none)' && setFilter(name, filters[name] === v ? '' : v)} />
    </section>
  )
}

function Months({ rows, filters, setFilter }) {
  const months = (rows || []).filter((r) => r.value)
  if (months.length < 2) return null
  const max = Math.max(...months.map((m) => m.items))
  return (
    <section className="card iai-card iai-wide">
      <h3 className="iai-sub">By month posted</h3>
      <div className="iai-trend iai-trend-tall" role="img"
           aria-label={`Posts by month posted: ${months.map((m) => `${m.value} ${m.items}`).join(', ')}`}>
        {months.map((m) => (
          <button type="button" key={m.value} title={`${m.value}: ${n(m.items)}`}
                  className={`iai-trend-col iai-pick${filters.month === m.value ? ' iai-picked' : ''}`}
                  onClick={() => setFilter('month', filters.month === m.value ? '' : m.value)}>
            <span className="iai-trend-bar" style={{ height: `${Math.max(4, (100 * m.items) / max)}%` }} />
          </button>
        ))}
      </div>
      <p className="dim iai-note">{months[0].value} to {months[months.length - 1].value}. Click a month to filter.</p>
    </section>
  )
}

function Item({ it, terms, groupNames, domainKey }) {
  const eng = Object.entries(it.engagement || {}).filter(([k, v]) => k !== 'upvote_ratio' && v)
  return (
    <li className="card iai-item">
      <div className="iai-item-meta">
        <span className="chip">{KIND_LABEL[it.kind] || it.kind}</span>
        <span>{PLATFORM_LABEL[it.platform] || it.platform}</span>
        <span>{it.created_at ? fmtDayUtc(it.created_at) : 'no posting date'}</span>
        <span className="dim">{authorOf(it)}</span>
        {it.lang && <span className="dim">lang {it.lang}</span>}
      </div>
      {it.title && <h3 className="iai-item-title">{it.title}</h3>}
      {it.text_cleared_at
        ? <p className="dim iai-item-text">Text cleared by retention on {fmtDayUtc(it.text_cleared_at)}; its labels are kept.</p>
        : it.excerpt && <p className="iai-item-text">{it.excerpt}{it.excerpt_cut && '…'}</p>}
      {eng.length > 0 && (
        <p className="dim iai-note tnum">{eng.map(([k, v]) => `${n(v)} ${ENGAGEMENT_LABEL[k] || k}`).join(' · ')}
          {it.share_count > 0 && ` · ${n(it.share_count)} shares & copies`}</p>
      )}
      <div className="iai-tags">
        {it.verdict === 'dropped' && (
          <span className="iai-tag iai-tag-drop">Filtered out: {REASON_LABEL[it.drop_reason] || it.drop_reason} ({it.drop_stage})</span>
        )}
        {it.content_type && <span className="iai-tag">{TYPE_LABEL[it.content_type] || it.content_type}</span>}
        {it.stage && <span className="iai-tag">stage: {STAGE_LABEL[it.stage] || it.stage}</span>}
        {it.groups.map((g) => <span className="iai-tag" key={g}>group: {groupNames[g] || g}</span>)}
        {(terms || []).map((t) => <span className="iai-tag iai-tag-term" key={t}>{t}</span>)}
        {it.ai_terms.map((t) => <span className="iai-tag iai-tag-ai" key={t}>{t}</span>)}
        {it.flags.filter((f) => !f.startsWith('person:')).map((f) => <span className="iai-tag iai-tag-flag" key={f}>{flagLabel(f)}</span>)}
      </div>
      {it.matched_pattern && <p className="dim iai-note">Content type decided by the pattern <code>{it.matched_pattern}</code></p>}
      <p className="dim iai-note">Found by: {it.queries.map(queryLabel).join(' · ') || '–'}
        {it.domain_hints.length > 1 && ` · searched for under ${it.domain_hints.length} domains`}
        {it.first_seen_at && ` · first seen ${fmtDayUtc(it.first_seen_at)}`}</p>
      {it.domains.length > 1 && (
        <p className="dim iai-note">Also filed under: {it.domains.filter((x) => x !== domainKey).map((x) => x.replace(/_/g, ' ')).join(', ')}</p>
      )}
      {it.duplicate_of && <p className="dim iai-note">A copy of {it.duplicate_of}</p>}
      {it.canonical_url && it.canonical_url !== it.link && (
        <p className="dim iai-note">Article, as deduplicated: {it.canonical_url}</p>
      )}
      <div className="iai-item-links">
        {it.url && <a href={it.url} target="_blank" rel="noopener noreferrer nofollow">Open the original →</a>}
        {it.link && <a href={it.link} target="_blank" rel="noopener noreferrer nofollow" className="dim">Linked article</a>}
      </div>
    </li>
  )
}

export default function IndustryAIDomain() {
  const { key } = useParams()
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [text, setText] = useState(params.get('q') || '')

  const scope = params.get('scope') || 'kept'
  const sort = params.get('sort') || 'newest'
  const offset = Math.max(0, Number(params.get('offset')) || 0)
  const filters = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f, params.get(f) || ''])), [params])
  useHead({ ...PRIVATE.industryAiDomain, title: `${data?.name || 'Domain'} · ${PRIVATE.industryAiDomain.title}` })

  useEffect(() => {
    let alive = true
    setLoading(true)
    industryAiDomain(key, { scope, sort, offset, limit: PAGE, ...filters })
      .then((d) => { if (alive) { setData(d); setErr(null) } })
      .catch((e) => alive && setErr(e.message))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [key, scope, sort, offset, filters])

  const update = (changes) => {
    const next = new URLSearchParams(params)
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    if (!('offset' in changes)) next.delete('offset')
    setParams(next)
  }
  const setFilter = (name, value) => update({ [name]: value })
  const active = FILTERS.filter((f) => filters[f])
  const f = data?.facets || {}
  const termLabels = {}
  const groupNames = data?.group_names || {}
  const isBucket = key === 'general' || key === 'unconfirmed'
  const first = offset + 1
  const last = Math.min(offset + PAGE, data?.matching || 0)

  return (
    <div className="shell section-tight stack stack-4">
      <header className="stack stack-1">
        <Link to="/ai-in-industries" className="dim iai-back">← AI in industries</Link>
        <span className="eyebrow">Industry AI{data?.kind === 'function' ? ' · function' : ''}{data?.active === false ? ' · switched off' : ''}</span>
        <h1 className="iai-h1">{data?.name || key}</h1>
        {data?.definition && <p className="dim iai-lede">{data.definition}</p>}
        <p className="dim iai-note">
          Everything collected for this {isBucket ? 'bucket' : 'domain'}: the counts, every breakdown, and the posts.
          Each post shows an excerpt (the first {data?.excerpt_chars ?? '…'} characters) and a link to the original.
          Labels are set by code rules ({data?.rules_version || '…'}); no language model read these posts.
        </p>
      </header>

      {err && <p className="iai-error">Could not load: {err}</p>}
      {!data && !err && <p className="dim">Loading…</p>}

      {data && (
        <>
          <nav className="iai-tabs" aria-label="Which posts">
            {Object.entries(data.scopes).map(([s, count]) => (
              <button type="button" key={s} className={`chip${scope === s ? ' iai-tab-on' : ''}`}
                      aria-pressed={scope === s} onClick={() => update({ scope: s === 'kept' ? '' : s, reason: '' })}>
                {SCOPE_LABEL[s]} <b className="tnum">{n(count)}</b>
              </button>
            ))}
            {data.found != null && <span className="dim iai-note">of {n(data.found)} found by this domain&apos;s queries</span>}
          </nav>
          <p className="dim iai-note">
            {scope === 'kept' && 'Kept, found by this domain’s own queries and confirmed by its terms: the card’s "kept".'}
            {scope === 'from_watch' && 'Kept from the watched communities and accounts and filed here by their terms: counted apart from "kept", as on the card.'}
            {scope === 'dropped' && 'Found by this domain’s queries and filtered out by the code rules, each with its reason. Shown so a small "kept" never reads as "nothing out there".'}
          </p>

          <div className="iai-figures">
            <div><b className="tnum">{n(data.matching)}</b><span>{active.length ? 'match the filters' : 'posts'}</span></div>
            <div><b className="tnum">{n(data.authors)}</b><span>distinct accounts</span></div>
            <div><b className="tnum">{n(data.with_link)}</b><span>link an outside article</span></div>
            {data.undated > 0 && <div><b className="tnum">{n(data.undated)}</b><span>no posting date</span></div>}
            {data.text_cleared > 0 && <div><b className="tnum">{n(data.text_cleared)}</b><span>text cleared by retention</span></div>}
            {data.mapped_people_items > 0 && <div><b className="tnum">{n(data.mapped_people_items)}</b><span>by a mapped person</span></div>}
          </div>
          {data.first_posted && (
            <p className="dim iai-note">Posted {fmtDayUtc(data.first_posted)} to {fmtDayUtc(data.last_posted)}.</p>
          )}
          {Object.keys(data.engagement || {}).length > 0 && (
            <p className="dim iai-note tnum">
              Engagement, added up over these posts, as each platform reports it: {Object.entries(data.engagement)
                .filter(([, v]) => v).map(([k, v]) => `${n(v)} ${ENGAGEMENT_LABEL[k] || k}`).join(' · ')}.
              Platforms count differently, so these are not comparable across platforms.
            </p>
          )}

          {active.length > 0 && (
            <div className="iai-active">
              {active.map((name) => (
                <button type="button" key={name} className="chip" onClick={() => setFilter(name, '')}>
                  {FILTER_LABEL[name]}: {chipValue(name, filters[name], groupNames)} ×
                </button>
              ))}
              <button type="button" className="btn btn-ghost"
                      onClick={() => { setText(''); update(Object.fromEntries(FILTERS.map((x) => [x, '']))) }}>
                Clear all
              </button>
            </div>
          )}

          <div className="iai-grid">
            <Facet title="By content type" rows={(f.type || []).filter((r) => r.value)} labels={TYPE_LABEL} name="type" filters={filters} setFilter={setFilter} />
            <Facet title="What each row is" rows={f.kind} labels={KIND_LABEL} name="kind" filters={filters} setFilter={setFilter}
                   note="Read from each platform's own id and link. X and Bluesky replies are counted as posts: nothing stored tells them apart." />
            <Facet title="By platform" rows={f.platform} labels={PLATFORM_LABEL} name="platform" filters={filters} setFilter={setFilter} />
            <Facet title="Use-case stage" rows={(f.stage || []).filter((r) => r.value)} labels={STAGE_LABEL} name="stage"
                   filters={filters} setFilter={setFilter}
                   note={`Guessed by code from the wording. ${n((f.stage || []).find((r) => !r.value)?.items)} posts have no stage.`} />
            <Facet title="Filtered out, by reason" rows={f.reason} labels={REASON_LABEL} name="reason" filters={filters} setFilter={setFilter} />
            <Facet title="By group" rows={f.group} labels={groupNames} name="group" filters={filters} setFilter={setFilter} />
            <Facet title="Industry words that matched" rows={f.term} labels={termLabels} name="term" filters={filters} setFilter={setFilter}
                   note="The domain's own words that filed each post here. Top 30." />
            <Facet title="AI terms that matched" rows={f.ai_term} labels={termLabels} name="ai_term" filters={filters} setFilter={setFilter}
                   note="Top 30." />
            <Facet title="Flags" rows={f.flag} labels={Object.fromEntries((f.flag || []).map((r) => [r.value, flagLabel(r.value)]))}
                   name="flag" filters={filters} setFilter={setFilter} note="Flags never filter a post out." />
            <Months rows={f.month} filters={filters} setFilter={setFilter} />
            <Facet title="Found by (searches and watch lists)" rows={f.query}
                   labels={Object.fromEntries((f.query || []).map((r) => [r.value, queryLabel(r.value)]))}
                   name="query" filters={filters} setFilter={setFilter} wide note="Top 25. A post found by two searches counts under both." />
          </div>

          {!isBucket && data.domain_terms?.length > 0 && (
            <details className="card iai-card">
              <summary>This domain&apos;s words ({n(data.domain_terms.length)}), from the contract</summary>
              <p className="dim iai-note">{data.domain_terms.join(' · ')}</p>
            </details>
          )}

          <section className="stack stack-2">
            <div className="iai-listbar">
              <h2 className="iai-sub">Posts</h2>
              <form className="iai-search" onSubmit={(e) => { e.preventDefault(); setFilter('q', text.trim()) }}>
                <input type="search" value={text} onChange={(e) => setText(e.target.value)}
                       placeholder="Search the text" aria-label="Search the post text" />
              </form>
              <label className="dim iai-note">Order{' '}
                <select value={sort} onChange={(e) => update({ sort: e.target.value === 'newest' ? '' : e.target.value })}>
                  {Object.entries(SORT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
            </div>
            {sort === 'engaged' && (
              <p className="dim iai-note">Most engaged: ordered by the platform&apos;s own counts (views, likes, comments and so on) added together, so X posts with view counts tend to come first.</p>
            )}
            {data.matching === 0
              ? <p className="dim">No posts match{active.length ? ' these filters' : ''}.</p>
              : <p className="dim iai-note">Showing {n(first)}–{n(last)} of {n(data.matching)}{loading ? ' · loading…' : ''}</p>}
            <ul className="iai-items">
              {data.items.map((it) => <Item key={it.id} it={it} terms={it.terms} groupNames={groupNames} domainKey={key} />)}
            </ul>
            {data.matching > PAGE && (
              <div className="iai-pager">
                <button type="button" className="btn btn-ghost" disabled={offset === 0}
                        onClick={() => update({ offset: String(Math.max(0, offset - PAGE)) })}>← Previous</button>
                <button type="button" className="btn btn-ghost" disabled={last >= data.matching}
                        onClick={() => update({ offset: String(offset + PAGE) })}>Next →</button>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
