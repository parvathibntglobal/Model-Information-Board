import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { modelCatalog, modelPath, watchModels } from '../api'
import '../styles/watch.css'

/**
 * MY MODELS: WHAT CHANGED (a prototype, feat/hooks-prototype, 2026-11-02, anooj).
 *
 * The team found no hook that brings a person back. This page is the one the
 * research pointed to: a visitor picks the models they run, and one page shows
 * what changed for those models - listed prices and price moves, retirement
 * dates, and what engineers report - counted, quoted, dated (judge/watch.py).
 *
 * NO ACCOUNT. The list lives in this browser (localStorage) and in the address
 * (?m=), so it can be bookmarked or sent to a colleague. "Since you last
 * looked" uses the time this browser last opened the page, stored here only.
 * Storage that is blocked just means no memory: the page still works.
 *
 * NOTHING HERE IS A SCORE (rule 3): prices as listed, counts of reports, dates,
 * quotes. A busy week of problem reports is shown, never flagged - the busiest
 * weeks are launch weeks, and counts follow how often we collect (rule 8).
 */

const LIST_KEY = 'mb-mymodels'
const SEEN_KEY = 'mb-mymodels-seen'

function load(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function save(key, value) {
  try { localStorage.setItem(key, value) } catch { /* storage blocked: no memory, still works */ }
}

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : '')
const fmtShort = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }) : '')
const daysUntil = (iso) => Math.round((new Date(iso).getTime() - Date.now()) / 86400000)
const clean = (name) => (name && name.includes(': ') ? name.split(': ').slice(1).join(': ') : name)
const PRICE_FIELD = { price_in: 'input', price_out: 'output', price_cached_read: 'cached input' }
const POL = { positive: ['Working', 'pass'], negative: ['Problem', 'fail'], neutral: ['Neutral', 'mute'] }

function Picker({ catalog, chosen, onAdd }) {
  const [q, setQ] = useState('')
  const matches = useMemo(() => {
    const term = q.trim().toLowerCase()
    if (!term || !catalog) return []
    return catalog
      .filter((m) => m.in_registry && !chosen.includes(m.id)
              && (m.name.toLowerCase().includes(term) || m.id.toLowerCase().includes(term)))
      .sort((a, b) => (b.reports || 0) - (a.reports || 0))
      .slice(0, 8)
  }, [q, catalog, chosen])
  return (
    <div className="mm-pick">
      <label htmlFor="mm-q" className="mm-pick-lab">Add a model you use</label>
      <input id="mm-q" className="mm-input" value={q} onChange={(e) => setQ(e.target.value)}
             placeholder="Type a model name: Claude, GPT, Gemini, DeepSeek…" autoComplete="off" />
      {matches.length > 0 && (
        <ul className="mm-matches" role="listbox" aria-label="Matching models">
          {matches.map((m) => (
            <li key={m.id}>
              <button type="button" onClick={() => { onAdd(m.id); setQ('') }}>
                <span>{m.name}</span>
                <span className="mm-match-n">{m.reports ? `${m.reports} reports` : 'no reports yet'}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Trend({ m }) {
  const max = Math.max(1, ...m.trend.map((w) => w.negative + w.positive + w.neutral))
  const released = m.release_date ? m.release_date.slice(0, 10) : null
  const last = m.trend.length - 1
  return (
    <figure className="mm-trend">
      <div className="mm-bars" role="img"
           aria-label={`Reports per week: ${m.trend.map((w) => `${fmtShort(w.week)} ${w.negative} problem of ${w.negative + w.positive + w.neutral}`).join('; ')}`}>
        {m.trend.map((w, i) => {
          const all = w.negative + w.positive + w.neutral
          const end = new Date(new Date(w.week).getTime() + 7 * 86400000).toISOString().slice(0, 10)
          const launch = released && released >= w.week && released < end
          return (
            <div key={w.week} className="mm-bar" title={`Week of ${fmtShort(w.week)}${i === last ? ' (so far)' : ''}: ${w.negative} problem, ${all} in all`}>
              <div className="mm-bar-col">
                <span className="mm-bar-rest" style={{ height: `${((all - w.negative) / max) * 100}%` }} />
                <span className="mm-bar-neg" style={{ height: `${(w.negative / max) * 100}%` }} />
              </div>
              <span className="mm-bar-lab">{launch ? 'launch' : i === last ? 'now' : fmtShort(w.week).split(' ')[0]}</span>
            </div>
          )
        })}
      </div>
      <figcaption>
        Reports per week, by the post&apos;s own date: <span className="mm-key-neg">problems</span> and <span className="mm-key-rest">everything else</span>.
        Counts follow how often we collect; a launch week is usually the busiest.
      </figcaption>
    </figure>
  )
}

function Card({ m, since, onRemove }) {
  const all = m.reports.positive + m.reports.negative + m.reports.neutral
  const prices = m.events.filter((e) => e.type === 'price-change' && e.changes?.length)
  const retire = m.retirement_date && daysUntil(m.retirement_date) >= -30 ? m.retirement_date : null
  const ns = m.new_since
  return (
    <article className="mm-card">
      <header className="mm-card-top">
        <div>
          <h2 className="mm-name"><Link to={`/ai-models/${modelPath(m.id)}`}>{clean(m.name)}</Link></h2>
          <div className="mm-sub">{m.provider} · listed {m.price_in ?? 'price not published'}
            {m.price_in && <> in / {m.price_out ?? 'not published'} out</>} per 1M tokens</div>
        </div>
        <button type="button" className="mm-x" onClick={() => onRemove(m.id)} aria-label={`Stop watching ${clean(m.name)}`}>×</button>
      </header>

      {(retire || m.deprecation_date || prices.length > 0) && (
        <ul className="mm-alerts">
          {retire && (
            <li className="mm-alert mm-alert-warn">
              {daysUntil(retire) >= 0
                ? <>Retires on <b>{fmtDate(retire)}</b> · in {daysUntil(retire)} days</>
                : <>Retired on <b>{fmtDate(retire)}</b></>}
            </li>
          )}
          {m.deprecation_date && !retire && (
            <li className="mm-alert mm-alert-warn">Deprecated on <b>{fmtDate(m.deprecation_date)}</b></li>
          )}
          {prices.map((e) => (
            <li key={e.date} className="mm-alert">
              Listed price moved on {fmtShort(e.date)}: {e.changes.map((c) => (
                <span key={c.field} className="mm-move">{PRICE_FIELD[c.field]} {c.from ?? 'not published'} → <b>{c.to ?? 'not published'}</b></span>
              ))}
              <span className="mm-verify"> · listed price, check it with the provider</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mm-since">
        {ns
          ? <>Since you last looked ({fmtShort(since)}): <b>{ns.negative}</b> new problem {ns.negative === 1 ? 'report' : 'reports'}, <b>{ns.positive}</b> working, <b>{ns.neutral}</b> neutral.</>
          : <>First look: below is the last {m.window_days} days.</>}
      </div>

      <div className="mm-counts" aria-label={`Reports in the last ${m.window_days} days`}>
        {['negative', 'positive', 'neutral'].map((p) => (
          <div key={p} className={`mm-count mm-c-${POL[p][1]}`}>
            <span className="mm-count-n">{m.reports[p]}</span>
            <span className="mm-count-l">{POL[p][0]} {m.reports[p] === 1 ? 'report' : 'reports'}</span>
          </div>
        ))}
        <div className="mm-count-note">{all ? `in the last ${m.window_days} days, counting each post once` : `No reports in the last ${m.window_days} days.`}</div>
      </div>

      <Trend m={m} />

      {m.quotes.length > 0 && (
        <ul className="mm-quotes">
          {m.quotes.map((q, i) => (
            <li key={i}>
              <span className={`badge badge-${POL[q.polarity]?.[1] || 'mute'}`}>{POL[q.polarity]?.[0] || q.polarity}</span>
              {q.about && <span className="mm-about">{q.about}</span>}
              <blockquote>“{q.quote}”</blockquote>
              <a className="mm-qsrc" href={q.url} target="_blank" rel="noopener noreferrer nofollow">{q.source} · {fmtShort(q.date)}</a>
            </li>
          ))}
        </ul>
      )}
      <Link className="mm-more" to={`/ai-models/${modelPath(m.id)}`}>Everything engineers report on {clean(m.name)} →</Link>
    </article>
  )
}

export default function Watch() {
  const [params, setParams] = useSearchParams()
  const fromUrl = params.get('m')
  const [ids, setIds] = useState(() => {
    const raw = fromUrl ?? load(LIST_KEY)
    return raw ? raw.split(',').filter(Boolean) : []
  })
  const [since] = useState(() => load(SEEN_KEY))
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [catalog, setCatalog] = useState(null)

  useEffect(() => { modelCatalog().then((d) => setCatalog(d.models || [])).catch(() => setCatalog([])) }, [])

  // The list in this browser and in the address, so it can be bookmarked or sent.
  useEffect(() => {
    save(LIST_KEY, ids.join(','))
    setParams(ids.length ? { m: ids.join(',') } : {}, { replace: true })
  }, [ids, setParams])

  useEffect(() => {
    let alive = true
    setError(null)
    watchModels(ids, ids.length ? since : null)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.message || 'The page could not load just now.'))
    return () => { alive = false }
  }, [ids, since])

  // This look counts once the page has been open a moment.
  useEffect(() => {
    if (!data?.models?.length) return undefined
    const t = setTimeout(() => save(SEEN_KEY, new Date().toISOString()), 4000)
    return () => clearTimeout(t)
  }, [data])

  const add = (id) => setIds((xs) => (xs.includes(id) ? xs : [...xs, id].slice(0, 12)))
  const remove = (id) => setIds((xs) => xs.filter((x) => x !== id))
  const nameOf = (id) => clean(catalog?.find((m) => m.id === id)?.name) || id

  return (
    <main className="mm shell">
      <header className="mm-head">
        <h1>My models: what changed</h1>
        <p>Pick the models you run. This page shows what changed for them: listed prices and price moves,
          retirement dates, and what engineers report, counted and quoted. No account: your list stays in
          this browser and in this page&apos;s address, so you can bookmark it or send it to your team.</p>
      </header>

      <section className="mm-bar-top">
        <Picker catalog={catalog} chosen={ids} onAdd={add} />
        {ids.length > 0 && (
          <ul className="mm-chips" aria-label="Models you watch">
            {ids.map((id) => (
              <li key={id}><span>{nameOf(id)}</span>
                <button type="button" onClick={() => remove(id)} aria-label={`Stop watching ${nameOf(id)}`}>×</button></li>
            ))}
          </ul>
        )}
      </section>

      {error && <p className="mm-quiet" role="alert">{error}</p>}
      {!data && !error && <div className="skel mm-skel" />}

      {data && !ids.length && (
        <section className="mm-empty">
          <h2>Start with the models engineers talk about most</h2>
          <p>Counted over the last {data.window_days} days, each post once.</p>
          <div className="mm-sugg">
            {data.suggestions.map((s) => (
              <button key={s.id} type="button" onClick={() => add(s.id)}>
                {clean(s.name)} <span>{s.reports} reports</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {data?.unknown?.length > 0 && (
        <p className="mm-quiet" role="status">Not in our model registry, so nothing to show: {data.unknown.join(', ')}.
          {' '}<button type="button" className="mm-link" onClick={() => setIds((xs) => xs.filter((x) => !data.unknown.includes(x)))}>Remove</button></p>
      )}

      {data?.models?.length > 0 && (
        <div className="mm-grid">
          {data.models.map((m) => (
            <Card key={m.id} m={{ ...m, window_days: data.window_days }} since={data.since} onRemove={remove} />
          ))}
        </div>
      )}
    </main>
  )
}
