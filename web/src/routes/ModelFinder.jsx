import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import ModalityFinder from '../finder/ModalityFinder'
import '../styles/catalog.css'
import { listRegistry, fetchAll, fmtPrice, fmtTokens, BoardUnreadable } from '../api'
import { Badge, Notice, Unreadable } from '../components/ui'
import { IconAlert, IconSearch } from '../components/Icons'
import { CONTEXT_STEPS, FLAGS, findModels } from '../finder/finder'
import { modelHref } from '../tokens/links'
import { useHead } from '../seo/head'
import { modelFinder } from '../seo/pages'

/**
 * THE SPEC FINDER (2026-10-12): which models advertise what you need.
 *
 * ADVERTISED, NOT REPORTED. Every filter here reads a provider's claim about
 * its own model. The one link to evidence is the entry count on each row,
 * which goes to the model page where the reports are.
 *
 * WHAT IS UNPUBLISHED IS SHOWN, NOT DROPPED. See finder.js: a model whose
 * provider has not published a value a filter needs sits in its own group
 * naming that value, and models a published value rules out are counted.
 */

const FIRST_ROWS = 40
const ctxLabel = (n) => (n === 0 ? 'Any' : `${fmtTokens(n)}+`)

export default function ModelFinder() {
  useHead(modelFinder())
  // TWO WAYS IN (2026-10-15): by advertised feature (the registry, below) or by
  // what a model reads and writes (the whole catalogue, ModalityFinder).
  const [sp, setSp] = useSearchParams()
  const io = sp.get('view') === 'io'
  const [models, setModels] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  const [need, setNeed] = useState([])
  const [minContext, setMinContext] = useState(0)
  const [maxIn, setMaxIn] = useState('')
  const [maxOut, setMaxOut] = useState('')
  const [reportedOnly, setReportedOnly] = useState(false)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('name')
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const list = await fetchAll((l, o) => listRegistry(l, o))
        if (alive) setModels(list.models)
      } catch (e) {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message)
      }
    })()
    return () => { alive = false }
  }, [])

  // An empty box is "no ceiling", never 0 - a 0 ceiling would rule out every
  // paid model for a field the reader did not fill in.
  const ceiling = (v) => (v === '' || Number.isNaN(Number(v)) ? null : Math.max(0, Number(v)))
  const result = useMemo(
    () => findModels(models, { need, minContext, maxIn: ceiling(maxIn), maxOut: ceiling(maxOut), query, sort, reportedOnly }),
    [models, need, minContext, maxIn, maxOut, query, sort, reportedOnly],
  )
  const shown = showAll ? result.match : result.match.slice(0, FIRST_ROWS)
  const toggle = (key) => setNeed((cur) => (cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key]))
  const anyFilter = need.length || minContext || maxIn !== '' || maxOut !== '' || reportedOnly
  const reset = () => { setNeed([]); setMinContext(0); setMaxIn(''); setMaxOut(''); setReportedOnly(false) }

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <nav className="tc-trail label" aria-label="Breadcrumb">
          <Link to="/models">Models</Link> <span aria-hidden="true">/</span> Spec finder
        </nav>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Find a model by spec</h1>
        <p className="tc-lead">
          Tick what your feature needs. These are what each provider advertises about its own model,
          not what engineers found; each model's page has the reports.
        </p>
        <nav className="cat-tabs" aria-label="Find by">
          <button type="button" className={!io ? 'on' : ''} onClick={() => setSp({}, { replace: true })}>By feature</button>
          <button type="button" className={io ? 'on' : ''} onClick={() => setSp({ view: 'io' }, { replace: true })}>By input and output</button>
        </nav>
      </div>

      {io && <ModalityFinder />}

      {!io && unreadable && <Unreadable detail={unreadable} />}
      {!io && err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!io && !models && !err && !unreadable && <div className="skel" style={{ height: 260 }} />}

      {!io && models && (
        <div className="mf-work">
          <aside className="card mf-rail" aria-label="Filters">
            <div className="mf-group">
              <span className="label">Must support</span>
              {FLAGS.map((f) => (
                <label key={f.key} className="mf-check">
                  <input type="checkbox" checked={need.includes(f.key)} onChange={() => toggle(f.key)} />
                  {f.label}
                </label>
              ))}
            </div>

            <div className="mf-group">
              <span className="label">Context window at least</span>
              <div className="mf-steps" role="radiogroup" aria-label="Minimum context window">
                {CONTEXT_STEPS.map((n) => (
                  <button key={n} type="button" role="radio" aria-checked={minContext === n}
                          className={`chip${minContext === n ? ' chip-on' : ''}`} onClick={() => setMinContext(n)}>
                    {ctxLabel(n)}
                  </button>
                ))}
              </div>
            </div>

            <div className="mf-group">
              <span className="label">Rate ceiling, USD per 1M tokens</span>
              <label className="mf-num">
                <span>Input at most</span>
                <input type="number" min="0" step="0.01" placeholder="no ceiling" value={maxIn}
                       onChange={(e) => setMaxIn(e.target.value)} />
              </label>
              <label className="mf-num">
                <span>Output at most</span>
                <input type="number" min="0" step="0.01" placeholder="no ceiling" value={maxOut}
                       onChange={(e) => setMaxOut(e.target.value)} />
              </label>
            </div>

            <div className="mf-group">
              <label className="mf-check">
                <input type="checkbox" checked={reportedOnly} onChange={() => setReportedOnly((v) => !v)} />
                Only models engineers have reported on
              </label>
            </div>

            {anyFilter ? (
              <button type="button" className="btn btn-quiet" style={{ alignSelf: 'flex-start' }} onClick={reset}>
                Clear filters
              </button>
            ) : null}
          </aside>

          <section className="stack stack-2" aria-labelledby="mf-results">
            <div className="tc-tablebar">
              <label className="searchbar" style={{ flex: 1 }}>
                <IconSearch width={15} height={15} />
                <input type="search" value={query} onChange={(e) => setQuery(e.target.value)}
                       placeholder="Narrow by name or provider" aria-label="Narrow by name or provider"
                       autoComplete="off" spellCheck="false" />
                {query && <button className="x" onClick={() => setQuery('')}>clear</button>}
              </label>
              <div className="row" style={{ gap: 6 }} role="group" aria-label="Order">
                {[['name', 'A–Z'], ['price', 'Lowest input rate'], ['context', 'Largest context']].map(([k, l]) => (
                  <button key={k} type="button" className={`chip${sort === k ? ' chip-on' : ''}`}
                          aria-pressed={sort === k} onClick={() => setSort(k)}>{l}</button>
                ))}
              </div>
            </div>

            <h2 id="mf-results" className="mf-count">
              {result.match.length} {result.match.length === 1 ? 'model matches' : 'models match'}
            </h2>
            {result.out > 0 && (
              <p className="dim tc-note">
                {result.out} ruled out by a published value: {Object.entries(result.outBy)
                  .sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k.toLowerCase()} (${n})`).join(', ')}.
              </p>
            )}

            <div className="stack stack-1">
              {shown.map(({ m }) => <Row key={m.model_version_id} m={m} need={need} />)}
              {result.match.length === 0 && (
                <p className="dim tc-note">No model matches every filter on a published value.</p>
              )}
            </div>
            {result.match.length > FIRST_ROWS && (
              <button type="button" className="btn btn-quiet" style={{ alignSelf: 'flex-start' }}
                      onClick={() => setShowAll((v) => !v)}>
                {showAll ? `Show the first ${FIRST_ROWS}` : `Show all ${result.match.length}`}
              </button>
            )}

            {result.unknown.length > 0 && (
              <details className="tc-unpriced mf-unknown">
                <summary>
                  {result.unknown.length} might match: the provider has not published something you filtered on
                </summary>
                <p className="dim tc-note">
                  Not ruled out and not confirmed. An unpublished feature flag is not a "no", so these
                  stay here with what is missing named, rather than being dropped.
                </p>
                <div className="stack stack-1">
                  {result.unknown.map(({ m, unknown }) => (
                    <Row key={m.model_version_id} m={m} need={need} missing={unknown} />
                  ))}
                </div>
              </details>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

function Row({ m, need, missing }) {
  const entries = m.board ? m.board.entries : null
  const id = m.canonical_id || m.model_version_id
  return (
    <div className="mf-row">
      <div className="mf-name">
        <Link to={modelHref(m.model_version_id)}>{m.display_name || id}</Link>
        <span className="dim">{m.provider || 'provider not recorded'}</span>
      </div>
      <dl className="mf-specs">
        <div><dt>Context</dt><dd className="tnum">{m.advertised_context ? fmtTokens(m.advertised_context) : 'not published'}</dd></div>
        <div><dt>Max output</dt><dd className="tnum">{m.max_output_tokens ? fmtTokens(m.max_output_tokens) : 'not published'}</dd></div>
        <div><dt>In / 1M</dt><dd className="tnum">{fmtPrice(m.price_in)}</dd></div>
        <div><dt>Out / 1M</dt><dd className="tnum">{fmtPrice(m.price_out)}</dd></div>
      </dl>
      <div className="mf-flags">
        {FLAGS.map((f) => {
          const v = m[f.key]
          const tone = v == null ? 'mute' : v ? 'pass' : 'fail'
          const word = v == null ? 'not published' : v ? 'yes' : 'no'
          return (
            <Badge key={f.key} tone={tone} title={`${f.label}: ${word}`}
                   className={`badge badge-${tone}${need.includes(f.key) ? ' mf-asked' : ''}`}>
              {f.label}{v == null ? ' ?' : v ? '' : ' ✕'}
            </Badge>
          )
        })}
        {missing && missing.length > 0 && (
          <span className="mf-missing">Not published: {missing.join(', ')}</span>
        )}
      </div>
      <Link className="mf-evidence" to={modelHref(m.model_version_id)}>
        {entries > 0 ? `${entries.toLocaleString('en-US')} board ${entries === 1 ? 'entry' : 'entries'} →`
          : entries === 0 ? 'Nobody has reported on it yet' : 'Reports →'}
      </Link>
    </div>
  )
}
