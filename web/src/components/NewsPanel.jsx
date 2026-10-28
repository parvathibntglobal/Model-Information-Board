import { useEffect, useMemo, useState } from 'react'
import { adminNews } from '../api'
import { Badge } from './ui'
import '../styles/blog-live.css'
import '../styles/news.css'

/**
 * ADMIN -> NEWS (2026-10-28): fresh AI headlines, each linking to its source.
 *
 * Read by collect/news/harvest.py from the feeds contract/news_sources.yaml
 * lists, every 6 hours once switched on. A news item is never evidence: no
 * claim, quote or board entry comes from it.
 *
 * NOTHING IS HIDDEN BY DEFAULT. The LLM badge marks items whose title or
 * summary matched the contract's keyword list; "LLM only" is the reader's
 * choice, because nobody has measured what that list misses (rule 8).
 *
 * A SOURCE THAT SAYS NOTHING SAYS WHY. Each source's last read is listed -
 * ok with its counts, refused by robots.txt, failed, or never read on this
 * database - so a quiet source never looks like a broken one (rule 4).
 *
 * AN UNDATED ITEM SAYS SO and is listed after every dated one, with when we
 * first saw it - never under a date it was not given (rule 6).
 */

const GROUPS = [['all', 'All'], ['selected', 'News'], ['lab', 'AI labs'], ['writer', 'Writers'], ['release', 'Releases']]
const DAYS = [1, 3, 7, 14, 30]
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '')

function Item({ it, source }) {
  return (
    <article className="nw-item">
      <div className="qb-meta">
        <span className="nw-source">{source?.label || it.source_key}</span>
        {it.published_at
          ? <time dateTime={it.published_at}>{fmt(it.published_at)}</time>
          : <span className="dim" title="The source gives no date for this item">date not given · first seen {fmt(it.first_seen_at)}</span>}
        {it.author && <span>{it.author}</span>}
        {it.daily_count != null && <Badge tone="info" title="One day's releases, folded into one entry">{it.daily_count} in one day</Badge>}
        {it.llm_keywords.length > 0 && (
          <Badge tone="pass" title={`Matched the LLM keyword list: ${it.llm_keywords.join(', ')}`}>LLM</Badge>
        )}
      </div>
      <a className="nw-title" href={it.url} target="_blank" rel="noopener noreferrer nofollow">{it.title}</a>
      {it.summary && <p className="qb-why nw-summary">{it.summary}</p>}
      {it.categories.length > 0 && (
        <div className="nw-tags">{it.categories.slice(0, 6).map((c) => <span key={c}>{c}</span>)}</div>
      )}
    </article>
  )
}

function readLine(s) {
  const r = s.last_read
  if (!r) return { text: 'never read on this database', tone: 'warn' }
  if (r.outcome === 'ok') return { text: `${r.items_seen} in the feed, ${r.items_new} new · ${fmt(r.at)}`, tone: 'mute' }
  if (r.outcome === 'robots_refused') return { text: `refused by robots.txt · ${fmt(r.at)}`, tone: 'warn', why: r.detail }
  return { text: `failed${r.http_status ? ` (HTTP ${r.http_status})` : ''} · ${fmt(r.at)}`, tone: 'fail', why: r.detail }
}

export default function NewsPanel() {
  const [days, setDays] = useState(7)
  const [group, setGroup] = useState('all')
  const [llmOnly, setLlmOnly] = useState(false)
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    setData(null)
    adminNews(days).then((d) => { if (alive) { setData(d); setErr(null) } }).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [days])

  const sources = useMemo(() => Object.fromEntries((data?.sources || []).map((s) => [s.key, s])), [data])
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (data?.items || []).filter((it) =>
      (group === 'all' || sources[it.source_key]?.group === group)
      && (!llmOnly || it.llm_keywords.length > 0)
      && (!q || `${it.title} ${it.summary || ''}`.toLowerCase().includes(q)))
  }, [data, group, llmOnly, query, sources])

  if (err && !data) return <p className="dim">The news could not be read: {err}</p>
  if (!data) return <div className="skel" style={{ height: 200 }} />
  const pop = data.population
  const undated = shown.filter((it) => !it.published_at).length

  return (
    <div className="stack stack-3">
      <p className="dim qb-intro">
        Fresh AI headlines from the feeds the publishers offer, each linking to the source. Read every
        6 hours; never used as evidence. The <b>LLM</b> badge marks items that matched a keyword list:
        a guide, not a filter, so nothing is hidden unless you choose <i>LLM only</i>.
      </p>

      <div className="nw-controls">
        <div className="lv-seg" role="group" aria-label="Which sources">
          {GROUPS.map(([k, label]) => (
            <button key={k} type="button" className={group === k ? 'on' : ''} onClick={() => setGroup(k)}>{label}</button>
          ))}
        </div>
        <div className="lv-seg" role="group" aria-label="How far back">
          {DAYS.filter((d) => d <= data.max_days).map((d) => (
            <button key={d} type="button" className={days === d ? 'on' : ''} onClick={() => setDays(d)}>{d === 1 ? '24 h' : `${d} days`}</button>
          ))}
        </div>
        <label className="nw-check">
          <input type="checkbox" checked={llmOnly} onChange={(e) => setLlmOnly(e.target.checked)} /> LLM only
        </label>
        <input className="lv-search" placeholder="Search headlines" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {/* Rule 7: what the count is counted over. */}
      <p className="dim nw-count">
        Showing <b>{shown.length}</b> of {pop.items_in_window} items from the last {data.days === 1 ? '24 hours' : `${data.days} days`}
        {' '}across {pop.sources_listed} sources ({pop.items_stored} stored in all)
        {pop.capped_at ? `; only the newest ${pop.capped_at} are listed` : ''}
        {undated ? `; ${undated} undated, listed last` : ''}.
      </p>

      {shown.length === 0
        ? <p className="lv-empty">No items match{llmOnly ? ' (LLM only is on)' : ''}.</p>
        : <div className="nw-list">{shown.map((it) => <Item key={it.id} it={it} source={sources[it.source_key]} />)}</div>}

      <details className="nw-sources">
        <summary>Sources and their last read</summary>
        <table className="nw-table">
          <thead><tr><th>Source</th><th>Group</th><th>In window</th><th>Last read</th></tr></thead>
          <tbody>
            {data.sources.map((s) => {
              const r = readLine(s)
              return (
                <tr key={s.key}>
                  <td title={s.terms}>{s.label}{s.one_entry_a_day ? <span className="dim"> · one entry a day</span> : null}</td>
                  <td>{GROUPS.find(([k]) => k === s.group)?.[1] || s.group}</td>
                  <td>{s.items_in_window}{s.undated_in_window ? <span className="dim"> ({s.undated_in_window} undated)</span> : null}</td>
                  <td><Badge tone={r.tone} title={r.why}>{r.text}</Badge></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </details>
    </div>
  )
}
