import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { industryAiDomain } from '../api'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import { fmtDayUtc } from '../dates'
import {
  Bars, KIND_LABEL, PLATFORM_LABEL, REASON_LABEL, STAGE_LABEL, TYPE_LABEL, countedAt, n,
} from '../industry-ai/parts'
import '../styles/industry-ai.css'

/**
 * ONE DOMAIN OF "AI IN INDUSTRIES" (2026-11-24, Parvathi), opened from its card on
 * /ai-in-industries. Signed in. Everything the Industry AI agent stored for the
 * domain (judge/industry_ai/view.py `industry_ai_domain_view`), laid out so it
 * reads simply:
 *
 *   - three population tabs, never added together (rules 4 and 7): kept by the
 *     domain's own searches; kept from the watch lists and filed here by their
 *     words; and filtered out, with the reason;
 *   - two view tabs: POSTS (one row of dropdown filters, then compact posts whose
 *     extra labels fold away under "Details") and BREAKDOWNS (collapsible sections;
 *     clicking a bar filters the posts and opens them).
 *
 * Every list says how many match. Tabs and filters live in the address, so a view
 * can be shared with the team.
 */

const SCOPE_LABEL = { kept: 'Kept', from_watch: 'From watch lists', dropped: 'Filtered out' }
const SCOPE_NOTE = {
  kept: 'Kept: found by this domain’s own searches and confirmed by its words. The card’s "posts kept".',
  from_watch: 'Kept from the watched communities and accounts, and filed here by their words. Counted apart from "kept", as on the card.',
  dropped: 'Found by this domain’s searches and filtered out by the code rules, each with its reason.',
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
  if (f.startsWith('domain_from_terms:')) return `filed by its words (${f.slice(18).replace(/_/g, ' ')})`
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
/** The words for one filter's values. */
function labelsFor(name, groupNames) {
  return { type: TYPE_LABEL, kind: KIND_LABEL, platform: PLATFORM_LABEL, stage: STAGE_LABEL,
    reason: REASON_LABEL, group: groupNames }[name]
}
function valueLabel(name, v, groupNames) {
  const labels = labelsFor(name, groupNames)
  if (labels) return labels[v] || v
  if (name === 'query') return queryLabel(v)
  if (name === 'flag') return flagLabel(v)
  return v
}
const shorten = (s, max = 70) => (s.length > max ? `${s.slice(0, max - 1)}…` : s)
const toCounts = (rows) => Object.fromEntries((rows || []).filter((r) => r.value).map((r) => [r.value, r.items]))

/** One filter as a dropdown: every value with its count, plus "Any". */
function FilterSelect({ name, rows, value, onChange, groupNames }) {
  const options = (rows || []).filter((r) => r.value)
  if (!options.length && !value) return null
  return (
    <label className="iai-filter">
      <span>{FILTER_LABEL[name]}</span>
      <select value={value} onChange={(e) => onChange(name, e.target.value)}>
        <option value="">Any</option>
        {value && !options.some((o) => o.value === value) && (
          <option value={value}>{shorten(valueLabel(name, value, groupNames))}</option>
        )}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {shorten(valueLabel(name, o.value, groupNames))} ({n(o.items)})
          </option>
        ))}
      </select>
    </label>
  )
}

/** One collapsible breakdown. Clicking a bar filters the posts and opens them. */
function Section({ title, note, rows, name, open, onPick, groupNames, labels }) {
  const counts = toCounts(rows)
  if (!Object.keys(counts).length) return null
  const words = labels || Object.fromEntries(Object.keys(counts).map((k) => [k, valueLabel(name, k, groupNames)]))
  return (
    <details className="card iai-fold" open={open}>
      <summary>
        <span>{title}</span>
        <span className="dim iai-note">{n(Object.keys(counts).length)} value{Object.keys(counts).length === 1 ? '' : 's'}</span>
      </summary>
      {note && <p className="dim iai-note">{note}</p>}
      <Bars counts={counts} labels={words} onPick={(v) => onPick(name, v)} />
    </details>
  )
}

function Months({ rows, onPick }) {
  const months = (rows || []).filter((r) => r.value)
  if (months.length < 2) return null
  const max = Math.max(...months.map((m) => m.items))
  return (
    <details className="card iai-fold">
      <summary>
        <span>By month posted</span>
        <span className="dim iai-note">{months[0].value} to {months[months.length - 1].value}</span>
      </summary>
      <div className="iai-trend iai-trend-tall" role="img"
           aria-label={`Posts by month posted: ${months.map((m) => `${m.value} ${m.items}`).join(', ')}`}>
        {months.map((m) => (
          <button type="button" key={m.value} title={`${m.value}: ${n(m.items)}`}
                  className="iai-trend-col iai-pick" onClick={() => onPick('month', m.value)}>
            <span className="iai-trend-bar" style={{ height: `${Math.max(4, (100 * m.items) / max)}%` }} />
          </button>
        ))}
      </div>
      <p className="dim iai-note">Click a month to see its posts.</p>
    </details>
  )
}

function Item({ it, groupNames, domainKey }) {
  const eng = Object.entries(it.engagement || {}).filter(([k, v]) => k !== 'upvote_ratio' && v)
  const flags = it.flags.filter((f) => !f.startsWith('person:'))
  const others = it.domains.filter((x) => x !== domainKey)
  return (
    <li className="card iai-item">
      <div className="iai-item-meta">
        <span className="chip">{KIND_LABEL[it.kind] || it.kind}</span>
        <span>{PLATFORM_LABEL[it.platform] || it.platform}</span>
        <span>{it.created_at ? fmtDayUtc(it.created_at) : 'no posting date'}</span>
        <span className="dim">{authorOf(it)}</span>
        {it.content_type && <span className="iai-tag">{TYPE_LABEL[it.content_type] || it.content_type}</span>}
        {it.stage && <span className="iai-tag">{STAGE_LABEL[it.stage] || it.stage}</span>}
        {it.verdict === 'dropped' && (
          <span className="iai-tag iai-tag-drop">{REASON_LABEL[it.drop_reason] || it.drop_reason}</span>
        )}
      </div>
      {it.title && <h3 className="iai-item-title">{it.title}</h3>}
      {it.text_cleared_at
        ? <p className="dim iai-item-text">Text cleared by retention on {fmtDayUtc(it.text_cleared_at)}; its labels are kept.</p>
        : it.excerpt && <p className="iai-item-text iai-clamp3">{it.excerpt}{it.excerpt_cut && '…'}</p>}
      <div className="iai-item-foot">
        {it.url && <a href={it.url} target="_blank" rel="noopener noreferrer nofollow">Open the original →</a>}
        {eng.length > 0 && (
          <span className="dim iai-note tnum">{eng.slice(0, 3).map(([k, v]) => `${n(v)} ${ENGAGEMENT_LABEL[k] || k}`).join(' · ')}</span>
        )}
      </div>
      <details className="iai-details">
        <summary>Details</summary>
        <dl className="iai-dl">
          {(it.terms || []).length > 0 && <><dt>Industry words</dt><dd>{it.terms.join(' · ')}</dd></>}
          {it.ai_terms.length > 0 && <><dt>AI terms</dt><dd>{it.ai_terms.join(' · ')}</dd></>}
          {it.groups.length > 0 && <><dt>Group</dt><dd>{it.groups.map((g) => groupNames[g] || g).join(' · ')}</dd></>}
          {it.matched_pattern && <><dt>Type decided by</dt><dd><code>{it.matched_pattern}</code></dd></>}
          {it.verdict === 'dropped' && <><dt>Filtered at</dt><dd>{it.drop_stage}</dd></>}
          {flags.length > 0 && <><dt>Flags</dt><dd>{flags.map(flagLabel).join(' · ')}</dd></>}
          <dt>Found by</dt>
          <dd>{it.queries.map(queryLabel).join(' · ') || '–'}
            {it.domain_hints.length > 1 && ` (searched for under ${it.domain_hints.length} domains)`}</dd>
          {others.length > 0 && <><dt>Also filed under</dt><dd>{others.map((x) => x.replace(/_/g, ' ')).join(', ')}</dd></>}
          {eng.length > 3 && <><dt>Engagement</dt><dd className="tnum">{eng.map(([k, v]) => `${n(v)} ${ENGAGEMENT_LABEL[k] || k}`).join(' · ')}</dd></>}
          {it.share_count > 0 && <><dt>Shares & copies</dt><dd>{n(it.share_count)}</dd></>}
          {it.duplicate_of && <><dt>A copy of</dt><dd>{it.duplicate_of}</dd></>}
          {it.link && <><dt>Linked article</dt><dd><a href={it.link} target="_blank" rel="noopener noreferrer nofollow">{shorten(it.link, 80)}</a></dd></>}
          {it.canonical_url && it.canonical_url !== it.link && <><dt>Article, deduplicated</dt><dd>{shorten(it.canonical_url, 80)}</dd></>}
          {it.lang && <><dt>Language</dt><dd>{it.lang}</dd></>}
          {it.first_seen_at && <><dt>First seen</dt><dd>{fmtDayUtc(it.first_seen_at)}</dd></>}
        </dl>
      </details>
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
  const view = params.get('view') === 'breakdowns' ? 'breakdowns' : 'posts'
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
  const pickFromBreakdown = (name, value) => update({ [name]: value, view: '' })
  const active = FILTERS.filter((f) => filters[f])
  const f = data?.facets || {}
  const groupNames = data?.group_names || {}
  const isBucket = key === 'general' || key === 'unconfirmed'
  const last = Math.min(offset + PAGE, data?.matching || 0)
  const flagWords = Object.fromEntries((f.flag || []).map((r) => [r.value, flagLabel(r.value)]))
  const noStage = (f.stage || []).find((r) => !r.value)?.items

  return (
    <div className="shell section-tight stack stack-3">
      <header className="stack stack-1">
        <Link to="/ai-in-industries" className="dim iai-back">← AI in industries</Link>
        <div className="iai-card-title">
          <h1 className="iai-h1">{data?.name || key}</h1>
          {data?.kind === 'function' && <span className="iai-badge">role</span>}
          {data?.active === false && <span className="iai-badge iai-badge-off">switched off</span>}
        </div>
        {data?.definition && <p className="dim iai-lede">{data.definition}</p>}
      </header>

      {err && <p className="iai-error">Could not load: {err}</p>}
      {!data && !err && <p className="dim">Loading…</p>}

      {data && (
        <>
          <div className="iai-tabbar" role="tablist" aria-label="Which posts">
            {Object.entries(data.scopes).filter(([s, count]) => count > 0 || s === 'kept' || s === scope).map(([s, count]) => (
              <button type="button" role="tab" key={s} aria-selected={scope === s}
                      className={`iai-tabbtn${scope === s ? ' iai-tabbtn-on' : ''}`}
                      onClick={() => update({ scope: s === 'kept' ? '' : s, reason: '' })}>
                {SCOPE_LABEL[s]} <span className="iai-tabn tnum">{n(count)}</span>
              </button>
            ))}
          </div>
          <p className="dim iai-note">
            {SCOPE_NOTE[scope]}
            {data.found != null && ` This domain's searches found ${n(data.found)} posts in all.`}
          </p>

          <div className="iai-figures">
            <div><b className="tnum">{n(data.matching)}</b><span>{active.length ? 'match the filters' : 'posts'}</span></div>
            <div><b className="tnum">{n(data.authors)}</b><span>accounts</span></div>
            <div><b className="tnum">{n(data.with_link)}</b><span>link an outside article</span></div>
            {data.first_posted && (
              <div><b className="iai-range">{fmtDayUtc(data.first_posted)} – {fmtDayUtc(data.last_posted)}</b><span>posted</span></div>
            )}
          </div>

          <details className="iai-more">
            <summary>More figures</summary>
            <ul className="iai-more-list">
              {Object.keys(data.engagement || {}).length > 0 && (
                <li className="tnum">Engagement added up, as each platform reports it: {Object.entries(data.engagement)
                  .filter(([, v]) => v).map(([k, v]) => `${n(v)} ${ENGAGEMENT_LABEL[k] || k}`).join(' · ')}.
                  Platforms count differently, so these do not compare across platforms.</li>
              )}
              {data.undated > 0 && <li>{n(data.undated)} posts carry no posting date.</li>}
              {data.text_cleared > 0 && <li>{n(data.text_cleared)} posts had their text cleared by retention (their labels stay).</li>}
              {data.mapped_people_items > 0 && <li>{n(data.mapped_people_items)} posts are by a person mapped across platforms.</li>}
              {countedAt(data.counted_at) && (
                <li>Counted at {countedAt(data.counted_at)} on {fmtDayUtc(data.counted_at)}. Each view is recounted on a visit after 10 minutes, and never shown more than an hour old.</li>
              )}
              <li>Each post shows its text up to its first {n(data.excerpt_chars)} characters (most posts are
                shorter, so are shown whole), with a link to the original. Labels are
                set by code rules ({data.rules_version}); no language model read these posts.</li>
              {!isBucket && data.domain_terms?.length > 0 && (
                <li>This domain&apos;s words ({n(data.domain_terms.length)}): {data.domain_terms.join(' · ')}</li>
              )}
            </ul>
          </details>

          <div className="iai-tabbar iai-tabbar-sub" role="tablist" aria-label="View">
            <button type="button" role="tab" aria-selected={view === 'posts'}
                    className={`iai-tabbtn${view === 'posts' ? ' iai-tabbtn-on' : ''}`} onClick={() => update({ view: '' })}>
              Posts <span className="iai-tabn tnum">{n(data.matching)}</span>
            </button>
            <button type="button" role="tab" aria-selected={view === 'breakdowns'}
                    className={`iai-tabbtn${view === 'breakdowns' ? ' iai-tabbtn-on' : ''}`}
                    onClick={() => update({ view: 'breakdowns' })}>
              Breakdowns
            </button>
          </div>

          {active.length > 0 && (
            <div className="iai-active">
              <span className="dim iai-note">Filtered by</span>
              {active.map((name) => (
                <button type="button" key={name} className="chip" onClick={() => setFilter(name, '')}
                        title="Remove this filter">
                  {FILTER_LABEL[name]}: {shorten(valueLabel(name, filters[name], groupNames), 50)} ×
                </button>
              ))}
              <button type="button" className="btn btn-ghost"
                      onClick={() => { setText(''); update(Object.fromEntries(FILTERS.map((x) => [x, '']))) }}>
                Clear all
              </button>
            </div>
          )}

          {view === 'posts' && (
            <section className="stack stack-2" role="tabpanel">
              <div className="iai-filterbar">
                <form className="iai-search" onSubmit={(e) => { e.preventDefault(); setFilter('q', text.trim()) }}>
                  <input type="search" value={text} onChange={(e) => setText(e.target.value)}
                         placeholder="Search the text" aria-label="Search the post text" />
                </form>
                <FilterSelect name="type" rows={f.type} value={filters.type} onChange={setFilter} />
                <FilterSelect name="platform" rows={f.platform} value={filters.platform} onChange={setFilter} />
                <FilterSelect name="kind" rows={f.kind} value={filters.kind} onChange={setFilter} />
                {scope === 'dropped' && <FilterSelect name="reason" rows={f.reason} value={filters.reason} onChange={setFilter} />}
                <FilterSelect name="term" rows={f.term} value={filters.term} onChange={setFilter} />
                <label className="iai-filter">
                  <span>Order</span>
                  <select value={sort} onChange={(e) => update({ sort: e.target.value === 'newest' ? '' : e.target.value })}>
                    {Object.entries(SORT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </label>
              </div>
              <details className="iai-more">
                <summary>More filters</summary>
                <div className="iai-filterbar">
                  <FilterSelect name="stage" rows={f.stage} value={filters.stage} onChange={setFilter} />
                  <FilterSelect name="ai_term" rows={f.ai_term} value={filters.ai_term} onChange={setFilter} />
                  <FilterSelect name="group" rows={f.group} value={filters.group} onChange={setFilter} groupNames={groupNames} />
                  <FilterSelect name="flag" rows={f.flag} value={filters.flag} onChange={setFilter} />
                  <FilterSelect name="month" rows={f.month} value={filters.month} onChange={setFilter} />
                  <FilterSelect name="query" rows={f.query} value={filters.query} onChange={setFilter} />
                </div>
              </details>
              {sort === 'engaged' && (
                <p className="dim iai-note">Most engaged: ordered by the platform&apos;s own counts (views, likes, comments and so on) added together, so X posts with view counts tend to come first.</p>
              )}
              {data.matching === 0
                ? <p className="dim">No posts match{active.length ? ' these filters' : ''}.</p>
                : <p className="dim iai-note">Showing {n(offset + 1)}–{n(last)} of {n(data.matching)}{loading ? ' · loading…' : ''}</p>}
              <ul className="iai-items">
                {data.items.map((it) => <Item key={it.id} it={it} groupNames={groupNames} domainKey={key} />)}
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
          )}

          {view === 'breakdowns' && (
            <section className="stack stack-2" role="tabpanel">
              <p className="dim iai-note">
                Counts over the {active.length ? 'filtered ' : ''}posts above. Open a section; click a bar to see those posts.
              </p>
              <div className="iai-folds">
                <Section title="Content type" rows={f.type} name="type" labels={TYPE_LABEL} open onPick={pickFromBreakdown} />
                <Section title="Platform" rows={f.platform} name="platform" labels={PLATFORM_LABEL} open onPick={pickFromBreakdown} />
                {scope === 'dropped' && (
                  <Section title="Filtered out, by reason" rows={f.reason} name="reason" labels={REASON_LABEL} open onPick={pickFromBreakdown} />
                )}
                <Section title="Industry words that matched" rows={f.term} name="term" note="The domain's own words that filed each post here. Top 30." onPick={pickFromBreakdown} />
                <Section title="What each row is" rows={f.kind} name="kind" labels={KIND_LABEL} onPick={pickFromBreakdown}
                         note="Read from each platform's own id and link. X and Bluesky replies count as posts: nothing stored tells them apart." />
                <Section title="Use-case stage" rows={f.stage} name="stage" labels={STAGE_LABEL} onPick={pickFromBreakdown}
                         note={`Guessed by code from the wording.${noStage ? ` ${n(noStage)} posts have no stage.` : ''}`} />
                <Section title="AI terms that matched" rows={f.ai_term} name="ai_term" note="Top 30." onPick={pickFromBreakdown} />
                <Section title="Group" rows={f.group} name="group" labels={groupNames} onPick={pickFromBreakdown} />
                <Section title="Flags" rows={f.flag} name="flag" labels={flagWords} note="Flags never filter a post out." onPick={pickFromBreakdown} />
                <Months rows={f.month} onPick={pickFromBreakdown} />
                <Section title="Found by (searches and watch lists)" rows={f.query} name="query"
                         note="Top 25. A post found by two searches counts under both." onPick={pickFromBreakdown} />
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
