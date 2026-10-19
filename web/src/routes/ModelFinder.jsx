import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { modelCatalog, fmtPrice, fmtTokens } from '../api'
import { Badge, Notice } from '../components/ui'
import { IconAlert, IconSearch } from '../components/Icons'
import { CONTEXT_STEPS, FLAGS, INPUTS, OUTPUTS, findModels, fromCatalog } from '../finder/finder'
import { modelPagePath } from '../catalog/format'
import { typeLabel } from '../catalog/types'
import { useHead } from '../seo/head'
import { modelFinder } from '../seo/pages'
import '../styles/catalog.css'

/**
 * THE SPEC FINDER (2026-10-12; one finder since 2026-10-15).
 *
 * ONE SET OF FILTERS OVER EVERY LISTED MODEL. It had two tabs - features over
 * the registry, inputs and outputs over the catalogue - that repeated the same
 * context steps, price ceilings, ordering and rows. Now what a model reads and
 * writes is one more requirement beside its features, and all of it runs over
 * the catalogue (GET /model-catalog: every model OpenRouter lists, every
 * output type), through the same engine (finder.js).
 *
 * ADVERTISED, NOT REPORTED. Every filter reads what a model is listed as doing.
 * The link to evidence is each row's engineer voices and its page.
 *
 * WHAT IS UNPUBLISHED IS SHOWN, NOT DROPPED (finder.js): a model whose value a
 * filter needs is not stated sits in its own group naming it, and models a
 * published value rules out are counted.
 */

const FIRST_ROWS = 40
const ctxLabel = (n) => (n === 0 ? 'Any' : `${fmtTokens(n)}+`)
const outLabel = (k) => (k === 'embeddings' ? 'Embeddings' : k === 'rerank' ? 'Rerank' : typeLabel(k))
const SORT_OPTIONS = [['name', 'A–Z'], ['price', 'Lowest input rate'], ['context', 'Largest context'],
  ['newest', 'Newest'], ['voices', 'Most engineer voices']]

function Toggles({ label, all, on, setOn, show = (x) => x, typed }) {
  const flip = (k) => setOn(on.includes(k) ? on.filter((x) => x !== k) : [...on, k])
  return (
    <div className="mf-group">
      <span className="label">{label}</span>
      <div className="mf-steps" role="group" aria-label={label}>
        {all.map((k) => (
          <button key={k} type="button" aria-pressed={on.includes(k)} onClick={() => flip(k)}
                  className={`chip${on.includes(k) ? ' chip-on' : ''}${typed ? ` cat-chip t-${k}` : ''}`}>
            {typed && <i aria-hidden="true" />}{show(k)}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function ModelFinder() {
  useHead(modelFinder())
  const [view, setView] = useState(null)
  const [err, setErr] = useState(null)

  const [ins, setIns] = useState([])
  const [outs, setOuts] = useState([])
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
    modelCatalog().then((v) => alive && setView(v)).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const models = useMemo(() => {
    if (!view || view.reason) return null
    const names = Object.fromEntries((view.providers || []).flatMap((p) => p.ids.map((i) => [i, p.name])))
    return view.models.map((m) => fromCatalog(m, names[m.provider]))
  }, [view])

  // An empty box is "no ceiling", never 0 - a 0 ceiling would rule out every
  // paid model for a field the reader did not fill in.
  const ceiling = (v) => (v === '' || Number.isNaN(Number(v)) ? null : Math.max(0, Number(v)))
  const result = useMemo(
    () => findModels(models, { need, ins, outs, minContext, maxIn: ceiling(maxIn), maxOut: ceiling(maxOut), query, sort, reportedOnly }),
    [models, need, ins, outs, minContext, maxIn, maxOut, query, sort, reportedOnly],
  )
  const shown = showAll ? result.match : result.match.slice(0, FIRST_ROWS)
  const anyFilter = ins.length || outs.length || need.length || minContext || maxIn !== '' || maxOut !== '' || reportedOnly
  const reset = () => { setIns([]); setOuts([]); setNeed([]); setMinContext(0); setMaxIn(''); setMaxOut(''); setReportedOnly(false) }

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <nav className="tc-trail label" aria-label="Breadcrumb">
          <Link to="/tools">Tools</Link> <span aria-hidden="true">/</span> Spec finder
        </nav>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Find a model by spec</h1>
        <p className="tc-lead">
          Tick what your feature needs - what the model must read and write, and what it must support.
          These are what each model is listed as doing, not what engineers found; each model's page has the reports.
        </p>
      </div>

      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {view && view.reason && <Notice icon={<IconAlert />}>{view.reason}</Notice>}
      {!view && !err && <div className="skel" style={{ height: 260 }} />}

      {models && (
        <div className="mf-work">
          <aside className="card mf-rail" aria-label="Filters">
            <Toggles label="Must read" all={INPUTS} on={ins} setOn={setIns} />
            <Toggles label="Must write" all={OUTPUTS} on={outs} setOn={setOuts} show={outLabel} typed />
            <div className="mf-group">
              <span className="label">Must support</span>
              {FLAGS.map((f) => (
                <label key={f.key} className="mf-check">
                  <input type="checkbox" checked={need.includes(f.key)}
                         onChange={() => setNeed((cur) => (cur.includes(f.key) ? cur.filter((k) => k !== f.key) : [...cur, f.key]))} />
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
              <div className="row" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-label="Order">
                {SORT_OPTIONS.map(([k, l]) => (
                  <button key={k} type="button" className={`chip${sort === k ? ' chip-on' : ''}`}
                          aria-pressed={sort === k} onClick={() => setSort(k)}>{l}</button>
                ))}
              </div>
            </div>

            <h2 id="mf-results" className="mf-count">
              {result.match.length} {result.match.length === 1 ? 'model matches' : 'models match'}
              <span className="dim" style={{ fontSize: 'var(--fs-sm)', fontWeight: 400 }}> of {models.length} listed</span>
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
                  {result.unknown.length} might match: something you filtered on is not published for them
                </summary>
                <p className="dim tc-note">
                  Not ruled out and not confirmed. An unpublished feature or a price that is not per token
                  is not a "no", so these stay here with what is missing named, rather than being dropped.
                </p>
                <div className="stack stack-1">
                  {result.unknown.map(({ m, unknown }) => (
                    <Row key={m.model_version_id} m={m} need={need} missing={unknown} />
                  ))}
                </div>
              </details>
            )}
            <p className="dim tc-note">
              {models.length} models, as OpenRouter lists them: what each reads and writes, its features and its prices.
            </p>
          </section>
        </div>
      )}
    </div>
  )
}

function Row({ m, need, missing }) {
  const page = modelPagePath(m.canonical_id)
  return (
    <div className="mf-row">
      <div className="mf-name">
        <Link to={page}>{m.display_name || m.canonical_id}</Link>
        <span className="dim">{m.provider || 'provider not recorded'}</span>
      </div>
      <dl className="mf-specs">
        <div><dt>Context</dt><dd className="tnum">{m.advertised_context ? fmtTokens(m.advertised_context) : 'not published'}</dd></div>
        <div><dt>Max output</dt><dd className="tnum">{m.max_output_tokens ? fmtTokens(m.max_output_tokens) : 'not published'}</dd></div>
        <div><dt>In / 1M</dt><dd className="tnum">{fmtPrice(m.price_in)}</dd></div>
        <div><dt>Out / 1M</dt><dd className="tnum">{fmtPrice(m.price_out)}</dd></div>
      </dl>
      <div className="mf-flags">
        <span className="mf-missing">Reads {(m.inputs || []).join(', ') || 'not stated'}</span>
        {(m.outputs || []).map((o) => <span key={o} className={`cat-type t-${o}`}>{outLabel(o)}</span>)}
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
      <Link className="mf-evidence" to={page}>
        {m.voices > 0 ? `${m.voices} engineer ${m.voices === 1 ? 'voice' : 'voices'} →` : 'No engineer voices yet →'}
      </Link>
    </div>
  )
}
