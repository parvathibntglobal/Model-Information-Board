import { useEffect, useMemo, useState } from 'react'
import { newsFeed } from '../api'
import { Badge } from '../components/ui'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import '../styles/news.css'

/**
 * THE NEWS PAGE (/news, signed in; 2026-10-28). Fresh AI headlines, laid out
 * like a news site: a lead story, the latest headlines beside it, then a grid.
 *
 * WRITTEN BY CODE, NOT A MODEL. Each summary is the source's own words cut to
 * whole sentences by collect/news/harvest.py; a source that gives no summary
 * shows none. Each picture is the feed's own; a story whose feed has none gets
 * a card drawn here naming its source - nothing is fetched from the article to
 * find one (anooj, 2026-10-28).
 *
 * NOTHING IS HIDDEN BY DEFAULT. The LLM badge marks stories that matched the
 * contract's keyword list; "LLM only" is the reader's choice (rule 8). An
 * undated story is listed after every dated one, never as fresh (rule 6), and
 * every source says what its last read did (rule 4).
 */

const GROUPS = [['all', 'All'], ['selected', 'News'], ['lab', 'AI labs'], ['writer', 'Writers'], ['release', 'Releases']]
const DAYS = [1, 3, 7, 14, 30]

function ago(iso) {
  if (!iso) return ''
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 60) return `${Math.max(mins, 1)} min ago`
  if (mins < 24 * 60) return `${Math.round(mins / 60)} h ago`
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}
const full = (iso) => (iso ? new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '')

/** A stable colour per source, so its drawn cards are recognisable at a glance. */
function hueOf(key) {
  let h = 0
  for (const ch of key) h = (h * 31 + ch.charCodeAt(0)) % 360
  return h
}

/** The picture: the feed's own, or a card drawn naming the source. */
function Picture({ it, source, lead = false }) {
  const [broken, setBroken] = useState(false)
  if (it.image_url && !broken) {
    return (
      <div className={`nw-pic${lead ? ' nw-pic-lead' : ''}`}>
        <img src={it.image_url} alt="" loading={lead ? 'eager' : 'lazy'} referrerPolicy="no-referrer"
             onError={() => setBroken(true)} />
      </div>
    )
  }
  // THE DRAWN CARD names the source, not the story: the headline is printed
  // right under it, and saying it twice reads as a mistake.
  const h = hueOf(it.source_key)
  const group = GROUPS.find(([k]) => k === source?.group)?.[1]
  return (
    <div className={`nw-pic nw-drawn${lead ? ' nw-pic-lead' : ''}`} aria-hidden="true"
         style={{ background: `radial-gradient(120% 90% at 85% 10%, hsl(${(h + 40) % 360} 60% 28%), transparent 60%),`
                  + ` linear-gradient(135deg, hsl(${h} 45% 20%), hsl(${(h + 20) % 360} 50% 10%))` }}>
      {group && <span className="nw-drawn-group">{group}</span>}
      <span className="nw-drawn-name" style={{ color: `hsl(${h} 85% 85%)` }}>{source?.label || it.source_key}</span>
    </div>
  )
}

function Meta({ it, source }) {
  return (
    <div className="nw-meta">
      <span className="nw-source">{source?.label || it.source_key}</span>
      {it.published_at
        ? <time dateTime={it.published_at} title={full(it.published_at)}>{ago(it.published_at)}</time>
        : <span title={`First seen ${full(it.first_seen_at)}`}>date not given</span>}
      {it.llm_keywords.length > 0 && <Badge tone="pass" title={`Matched: ${it.llm_keywords.join(', ')}`}>LLM</Badge>}
    </div>
  )
}

const Link = ({ it, children, className }) => (
  <a className={className} href={it.url} target="_blank" rel="noopener noreferrer nofollow">{children}</a>
)

function Lead({ it, source }) {
  return (
    <article className="nw-lead">
      <Link it={it}><Picture it={it} source={source} lead /></Link>
      <div>
        <Meta it={it} source={source} />
        <h2><Link it={it} className="nw-title">{it.title}</Link></h2>
        {it.summary && <p className="nw-summary nw-summary-lead">{it.summary}</p>}
        {it.author && <p className="nw-byline">By {it.author}</p>}
      </div>
    </article>
  )
}

function Card({ it, source }) {
  return (
    <article className="nw-card">
      <Link it={it}><Picture it={it} source={source} /></Link>
      <Meta it={it} source={source} />
      <h3><Link it={it} className="nw-title">{it.title}</Link></h3>
      {it.summary && <p className="nw-summary">{it.summary}</p>}
    </article>
  )
}

function Latest({ items, sources }) {
  return (
    <aside className="nw-latest" aria-label="Latest headlines">
      <h2 className="nw-latest-head">Latest</h2>
      <ol>
        {items.map((it) => (
          <li key={it.id}>
            <span className="nw-latest-time">{ago(it.published_at)}</span>
            <Link it={it} className="nw-title">{it.title}</Link>
            <span className="nw-latest-source">{sources[it.source_key]?.label || it.source_key}</span>
          </li>
        ))}
      </ol>
    </aside>
  )
}

function readLine(s) {
  const r = s.last_read
  if (!r) return { text: 'never read on this database', tone: 'warn' }
  if (r.outcome === 'ok') return { text: `${r.items_seen} in the feed, ${r.items_new} new · ${full(r.at)}`, tone: 'mute' }
  if (r.outcome === 'robots_refused') return { text: `refused by robots.txt · ${full(r.at)}`, tone: 'warn', why: r.detail }
  return { text: `failed${r.http_status ? ` (HTTP ${r.http_status})` : ''} · ${full(r.at)}`, tone: 'fail', why: r.detail }
}

export default function News() {
  useHead(PRIVATE.news)
  const [days, setDays] = useState(7)
  const [group, setGroup] = useState('all')
  const [llmOnly, setLlmOnly] = useState(false)
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    setData(null)
    newsFeed(days).then((d) => { if (alive) { setData(d); setErr(null) } }).catch((e) => alive && setErr(e.message))
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

  const dated = shown.filter((it) => it.published_at)
  const undated = shown.filter((it) => !it.published_at)
  // THE LEAD is a story, not a build: the newest non-release story with a
  // picture of its own among the ten newest, else the newest non-release one,
  // else (a Releases-only view) simply the newest.
  const isStory = (it) => sources[it.source_key]?.group !== 'release'
  const pictured = dated.slice(0, 10).findIndex((it) => isStory(it) && it.image_url)
  const firstStory = dated.findIndex(isStory)
  const leadIdx = pictured >= 0 ? pictured : Math.max(0, firstStory)
  const lead = dated[leadIdx]
  const rest = dated.filter((_, i) => i !== leadIdx)
  const latest = rest.slice(0, 6)
  const grid = rest.slice(6)

  return (
    <div className="shell section-tight stack stack-4">
      <header className="stack stack-1">
        <span className="eyebrow">News</span>
        <h1 className="nw-h1">AI news</h1>
        <p className="muted nw-intro">
          Fresh headlines from AI labs, news sites, writers and release notes, each linking to its source.
          Summaries are the sources&apos; own words, cut to a few sentences by code; pictures are the
          feeds&apos; own, or a card naming the source when a feed has none.
        </p>
      </header>

      <div className="nw-controls">
        <div className="lv-seg" role="group" aria-label="Which sources">
          {GROUPS.map(([k, label]) => (
            <button key={k} type="button" className={group === k ? 'on' : ''} onClick={() => setGroup(k)}>{label}</button>
          ))}
        </div>
        <div className="lv-seg" role="group" aria-label="How far back">
          {DAYS.filter((d) => !data || d <= data.max_days).map((d) => (
            <button key={d} type="button" className={days === d ? 'on' : ''} onClick={() => setDays(d)}>{d === 1 ? '24 h' : `${d} days`}</button>
          ))}
        </div>
        <label className="nw-check">
          <input type="checkbox" checked={llmOnly} onChange={(e) => setLlmOnly(e.target.checked)} /> LLM only
        </label>
        <input className="lv-search" placeholder="Search headlines" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {err && !data && <p className="dim">The news could not be read: {err}</p>}
      {!data && !err && <div className="skel" style={{ height: 420 }} />}

      {data && (
        <>
          {/* Rule 7: what the count is counted over. */}
          <p className="dim nw-count">
            {shown.length} of {data.population.items_in_window} stories from the last
            {data.days === 1 ? ' 24 hours' : ` ${data.days} days`}, across {data.population.sources_listed} sources
            ({data.population.items_stored} stored in all)
            {data.population.capped_at ? `; only the newest ${data.population.capped_at} are listed` : ''}
            {undated.length ? `; ${undated.length} undated, listed last` : ''}.
          </p>

          {shown.length === 0 && <p className="lv-empty">No stories match{llmOnly ? ' (LLM only is on)' : ''}.</p>}

          {lead && (
            <section className="nw-top">
              <Lead it={lead} source={sources[lead.source_key]} />
              {latest.length > 0 && <Latest items={latest} sources={sources} />}
            </section>
          )}

          {grid.length > 0 && (
            <section className="stack stack-2">
              <h2 className="nw-section-head">More stories</h2>
              <div className="nw-grid">{grid.map((it) => <Card key={it.id} it={it} source={sources[it.source_key]} />)}</div>
            </section>
          )}

          {undated.length > 0 && (
            <section className="stack stack-2">
              <h2 className="nw-section-head">Date not given by the source</h2>
              <p className="dim nw-count">These feeds publish no date, so these are listed by when we first saw them.</p>
              <div className="nw-grid">{undated.map((it) => <Card key={it.id} it={it} source={sources[it.source_key]} />)}</div>
            </section>
          )}

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
        </>
      )}
    </div>
  )
}
