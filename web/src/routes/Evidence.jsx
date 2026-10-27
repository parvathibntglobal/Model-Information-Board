import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { evidenceFeed, evidenceSummary, feedModels, modelCatalog } from '../api'
import { evidencePath, modelPagePath } from '../catalog/format'
import { PolarityChip, Posted, Report, SourceLine } from '../evidence/parts'
import { useHead } from '../seo/head'
import { evidenceHead } from '../seo/pages'
import '../styles/evidence.css'

/**
 * THE EVIDENCE FEED (2026-10-21, PROPOSED): every report behind a model's
 * counts, in our own words, newest first, each with its source below it.
 *
 *   /evidence                  pick a model (seated, with engineer voices)
 *   /evidence/<vendor>/<model> its feed; ?section=&slug= narrows it to one job,
 *                              capability or metric, ?polarity= to one side,
 *                              ?tab=summary opens the approved summary
 *
 * THE LIST IS THE COUNT'S OWN POPULATION (judge/feed/items.py). Every count on
 * the Models pages links here narrowed the way it was counted, so "3 negative"
 * opens three reports - and the header repeats the numbers in both units the
 * site uses (reports, and Compare's entries) so a reader finds the one they
 * clicked.
 *
 * LIVE: page 1 is asked for again every five minutes and when the tab regains
 * focus. New reports are announced above the list, never inserted under the
 * reader's eyes.
 */

const SECTION_LABEL = { best_for: 'Job', capability: 'Capability', metric: 'Metric' }
const POLARITIES = ['positive', 'negative', 'neutral']
const REFRESH_MS = 5 * 60 * 1000

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

// THE SEATED MODELS ONLY (2026-10-23): every model with reports has its
// paraphrases stored, and the feed shows the ones the models page lists
// (judge/feed/items.py `seated_keys`). Not-yet-loaded or unreadable seated list
// shows the error, never every model (rule 6).
function Picker() {
  const [state, setState] = useState({ models: null, err: null })
  const [q, setQ] = useState('')
  useEffect(() => {
    let alive = true
    Promise.all([modelCatalog(), feedModels()])
      .then(([v, s]) => {
        const seated = new Set(s.ids || [])
        alive && setState({ models: (v.models || []).filter((m) => m.voices > 0 && seated.has(m.id)), err: null })
      })
      .catch((e) => alive && setState({ models: null, err: e.message || 'The models could not be read.' }))
    return () => { alive = false }
  }, [])
  const ql = q.trim().toLowerCase()
  const shown = useMemo(() => (state.models || [])
    .filter((m) => !ql || `${m.name} ${m.id}`.toLowerCase().includes(ql))
    .sort((a, b) => b.voices - a.voices || b.reports - a.reports || a.name.localeCompare(b.name)), [state.models, ql])
  return (
    <section className="stack stack-2">
      <input className="ev-search" type="search" value={q} onChange={(e) => setQ(e.target.value)}
             placeholder="Search models" aria-label="Search models" />
      {!state.models && !state.err && <div className="skel" style={{ height: 220 }} />}
      {state.err && <p className="ev-dim">{state.err}</p>}
      {state.models && (
        shown.length ? (
          <ul className="ev-pick">
            {shown.map((m) => (
              <li key={m.id}>
                <Link to={evidencePath(m.id)}>
                  <span className="ev-pick-name">{m.name}</span>
                  <span className="ev-dim">{plural(m.voices, 'voice')} · {plural(m.reports, 'report')}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : <p className="ev-dim">No model with engineer reports matches &quot;{q}&quot;.</p>
      )}
    </section>
  )
}

/** "12 reports from 9 voices", the split in reports, and the entries. */
function CountsLine({ counts }) {
  const s = counts.reports_by_polarity
  const e = counts.entries_by_polarity
  return (
    <p className="ev-counts">
      <b>{plural(counts.reports, 'report')}</b> from <b>{plural(counts.voices, 'voice')}</b>
      {' · '}{s.positive} positive, {s.negative} negative, {s.neutral} neutral
      {s.both > 0 && ` (${s.both} said both, counted in each)`}
      {' · '}<span title="An entry is one statement filed from a report; one report can hold several. Compare counts entries.">
        {plural(counts.entries, 'entry', 'entries')}: {e.positive} positive, {e.negative} negative, {e.neutral} neutral
      </span>
    </p>
  )
}

function Feed({ id, section, slug, category, polarity, setParam }) {
  const [state, setState] = useState({ head: null, items: [], page: 1, err: null, loading: true })
  const [fresh, setFresh] = useState(null)
  const filter = useMemo(() => ({ section, slug, category, polarity }), [section, slug, category, polarity])
  const known = useRef(new Set())

  const load = useCallback(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true, err: null }))
    setFresh(null)
    evidenceFeed(id, filter)
      .then((d) => {
        if (!alive) return
        known.current = new Set(d.items.map((x) => x.id))
        setState({ head: d, items: d.items, page: 1, err: null, loading: false })
      })
      .catch((e) => alive && setState({ head: null, items: [], page: 1, err: e.message || 'The feed could not be read.', loading: false }))
    return () => { alive = false }
  }, [id, filter])
  useEffect(load, [load])

  // LIVE, WITHOUT MOVING THE LIST: ask page 1 again, and announce what is new.
  useEffect(() => {
    const check = () => {
      evidenceFeed(id, filter)
        .then((d) => {
          const added = d.items.filter((x) => !known.current.has(x.id))
          if (added.length) setFresh(d)
        })
        .catch(() => { /* a failed refresh leaves the list as it is; the next one tries again */ })
    }
    const timer = setInterval(check, REFRESH_MS)
    const onFocus = () => check()
    window.addEventListener('focus', onFocus)
    return () => { clearInterval(timer); window.removeEventListener('focus', onFocus) }
  }, [id, filter])

  const more = () => {
    const next = state.page + 1
    setState((s) => ({ ...s, loading: true }))
    evidenceFeed(id, { ...filter, page: next })
      .then((d) => setState((s) => {
        const add = d.items.filter((x) => !known.current.has(x.id))
        add.forEach((x) => known.current.add(x.id))
        return { ...s, items: [...s.items, ...add], page: next, loading: false }
      }))
      .catch((e) => setState((s) => ({ ...s, loading: false, err: e.message || 'The next page could not be read.' })))
  }

  const head = state.head
  if (state.err && !head) return <p className="ev-dim">{state.err}</p>
  if (!head) return <div className="skel" style={{ height: 320 }} />
  const c = head.counts
  const newCount = fresh ? fresh.items.filter((x) => !known.current.has(x.id)).length : 0

  return (
    <section className="stack stack-2">
      <div className="ev-polbar" role="group" aria-label="Show reports by reaction">
        <button type="button" className={`chip${!polarity ? ' chip-on' : ''}`} onClick={() => setParam({ polarity: null })}>
          All <span className="x">{c.reports}</span>
        </button>
        {POLARITIES.map((p) => (
          <button key={p} type="button" className={`chip${polarity === p ? ' chip-on' : ''}`}
                  aria-pressed={polarity === p} onClick={() => setParam({ polarity: polarity === p ? null : p })}>
            {p[0].toUpperCase() + p.slice(1)} <span className="x">{c.reports_by_polarity[p]}</span>
          </button>
        ))}
      </div>

      {newCount > 0 && (
        <button type="button" className="ev-new" onClick={() => {
          known.current = new Set(fresh.items.map((x) => x.id))
          setState({ head: fresh, items: fresh.items, page: 1, err: null, loading: false })
          setFresh(null)
        }}>
          {plural(newCount, 'new report')} - show
        </button>
      )}

      {head.paraphrased < c.reports && (
        <p className="ev-note">{head.paraphrased} of {plural(c.reports, 'report')} paraphrased so far. The rest are listed with their source.</p>
      )}

      {state.items.length ? (
        <div className="ev-list">
          {state.items.map((it) => <Report key={it.id} item={it} id={`r-${it.id}`} />)}
        </div>
      ) : <p className="ev-dim">No report matches this filter.</p>}

      {state.err && <p className="ev-dim">{state.err}</p>}
      {state.page < head.page.pages && (
        <button type="button" className="btn btn-ghost" style={{ alignSelf: 'center' }} disabled={state.loading} onClick={more}>
          {state.loading ? 'Loading…' : 'Load more'}
        </button>
      )}
      <p className="ev-note">
        Showing {state.items.length} of {plural(head.matching, 'report')}{polarity ? ` that took the ${polarity} side` : ''}, newest first.
      </p>
    </section>
  )
}

function Summary({ id }) {
  const [state, setState] = useState({ d: null, err: null })
  useEffect(() => {
    let alive = true
    setState({ d: null, err: null })
    evidenceSummary(id)
      .then((d) => alive && setState({ d, err: null }))
      .catch((e) => alive && setState({ d: null, err: e.message || 'The summary could not be read.' }))
    return () => { alive = false }
  }, [id])
  if (state.err) return <p className="ev-dim">{state.err}</p>
  if (!state.d) return <div className="skel" style={{ height: 240 }} />
  const { d } = state
  if (d.state === 'awaiting_review') return <p className="ev-dim">A summary has been drafted and is waiting for a person to review it.</p>
  if (d.state !== 'approved' || !d.summary) return <p className="ev-dim">No summary yet.</p>

  const s = d.summary
  // Footnote numbers in the order the reports are first cited.
  const order = []
  for (const p of s.paragraphs) for (const c of p.cites) if (!order.includes(c)) order.push(c)
  const num = Object.fromEntries(order.map((c, i) => [c, i + 1]))
  const day = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : 'an unrecorded date')

  return (
    <section className="stack stack-2 ev-summary">
      {s.paragraphs.map((p, i) => (
        <p key={i}>
          {p.text}
          {p.cites.map((c) => <sup key={c}><a href={`#cite-${num[c]}`} aria-label={`Report ${num[c]}`}>{num[c]}</a></sup>)}
        </p>
      ))}
      <p className="ev-note">
        {/* PARAPHRASED reports, Admin's word (#558 second review): reports_available
            counts only reports with a current paraphrase, so it is not the Feed tab's
            report count, and must not read as if it were (rule 7). */}
        Written from the newest {s.reports_used} of {plural(s.reports_available, 'paraphrased report')}, up to {day(s.newest_report_at)}.
        {' '}{d.reports_since} {d.reports_since === 1 ? 'report' : 'reports'} posted since {d.reports_since === 1 ? 'is' : 'are'} not in it.
        {/* A WEEKLY REVISION SAYS SO (2026-10-27): its newest points were added by a
            model from newer reports and approved by a person, like the draft. */}
        {' '}{s.revised
          ? `Drafted by a language model, last revised from newer reports, and approved by a person on ${day(s.reviewed_at)}.`
          : `Drafted by a language model and approved by a person on ${day(s.reviewed_at)}.`}
      </p>
      <h3 className="ev-h3">The reports it cites</h3>
      <ol className="ev-cites">
        {order.map((c) => {
          const r = s.cited[c]
          return (
            <li key={c} id={`cite-${num[c]}`}>
              {!r || r.gone ? <span className="ev-dim">This report has since been removed from the board.</span> : (
                <>
                  <div className="ev-meta"><Posted at={r.posted_at} /><PolarityChip polarity={r.polarity} /></div>
                  {r.paraphrase ? <p className="ev-text">{r.paraphrase}</p> : <p className="ev-text ev-dim">Not paraphrased yet. The source is below.</p>}
                  <SourceLine source={r.source} />
                </>
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}

export default function Evidence() {
  const rest = useParams()['*'] || ''
  const id = rest ? rest.split('/').map(decodeURIComponent).join('/') : ''
  const [sp, setSp] = useSearchParams()
  const section = sp.get('section') || null
  const slug = sp.get('slug') || null
  // ONE OF COMPARE'S CATEGORY SCORES (coding, agents...), from a score row. Its
  // own filter: the API refuses it with a section, so a section wins nothing here.
  const category = sp.get('category') || null
  const polarity = POLARITIES.includes(sp.get('polarity')) ? sp.get('polarity') : null
  const tab = sp.get('tab') === 'summary' ? 'summary' : 'feed'

  // THE HEADING AND ITS COUNTS: the narrowed population WITHOUT the polarity
  // filter, so the header keeps every side's number while the list shows one.
  const [base, setBase] = useState(null)
  useEffect(() => {
    if (!id) return undefined
    let alive = true
    setBase(null)
    evidenceFeed(id, { section, slug, category })
      .then((d) => alive && setBase(d))
      .catch((e) => alive && setBase({ notFound: e.status === 404 && !(e.body && e.body.seated === false), err: e.message, model: { label: id, canonical: id } }))
    return () => { alive = false }
  }, [id, section, slug, category])
  const model = base && !base.err ? base.model : null
  const filterName = base && !base.err ? base.filter.name : null

  useHead(evidenceHead(model ? model.label : null, id || null))

  const setParam = (patch) => {
    const next = new URLSearchParams(sp)
    for (const [k, v] of Object.entries(patch)) {
      if (v == null || v === '') next.delete(k)
      else next.set(k, v)
    }
    setSp(next, { replace: false })
  }

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="go-badge go-models page-tag" style={{ alignSelf: 'flex-start' }}>Evidence feed</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>
          {id ? (model ? model.label : base ? id : '…') : 'The reports behind every count'}
        </h1>
        <p className="muted" style={{ maxWidth: '72ch', margin: 0 }}>
          {id
            ? 'Every report behind this model’s counts, in our own words, newest first, with its source below it.'
            : 'Pick a model to read every report behind its counts: each one in our own words, newest first, with its source.'}
        </p>
        {id && model && (
          <Link to={modelPagePath(model.canonical || id)} className="ev-modellink">Price, specs and counts for this model →</Link>
        )}
      </div>

      {!id ? <Picker /> : (
        <>
          {base && base.err ? <p className="ev-dim">{base.notFound ? 'There is no model at this address.' : base.err}</p> : (
            <>
              {base ? <CountsLine counts={base.counts} /> : <div className="skel" style={{ height: 22, maxWidth: 520 }} />}
              {(section || category || polarity) && (
                <div className="ev-filters" aria-label="Active filters">
                  {section && (
                    <button type="button" className="chip chip-on" onClick={() => setParam({ section: null, slug: null })}
                            aria-label={`Remove the filter ${SECTION_LABEL[section] || section}: ${filterName || slug || ''}`}>
                      {SECTION_LABEL[section] || section}{slug ? `: ${filterName || slug}` : ''} <span className="x">×</span>
                    </button>
                  )}
                  {category && (
                    <button type="button" className="chip chip-on" onClick={() => setParam({ category: null })}
                            aria-label={`Remove the filter category: ${filterName || category}`}>
                      Category: {filterName || category} <span className="x">×</span>
                    </button>
                  )}
                  {polarity && (
                    <button type="button" className="chip chip-on" onClick={() => setParam({ polarity: null })}
                            aria-label={`Remove the filter ${polarity}`}>
                      {polarity[0].toUpperCase() + polarity.slice(1)} <span className="x">×</span>
                    </button>
                  )}
                </div>
              )}
              <nav className="ev-tabs" aria-label="Evidence">
                <button type="button" className={tab === 'feed' ? 'on' : ''} onClick={() => setParam({ tab: null })}>Live feed</button>
                <button type="button" className={tab === 'summary' ? 'on' : ''} onClick={() => setParam({ tab: 'summary' })}>Summary</button>
              </nav>
              {tab === 'feed'
                ? <Feed id={id} section={section} slug={slug} category={category} polarity={polarity} setParam={setParam} />
                : <Summary id={id} />}
              <p className="ev-note">
                Each report is paraphrased by a language model from the excerpts we verified, and checked in code for
                copied wording and added numbers. Open the source to read it in full. Positive, negative and neutral
                say how each report was phrased, not whether it was right.
              </p>
            </>
          )}
        </>
      )}
    </div>
  )
}
