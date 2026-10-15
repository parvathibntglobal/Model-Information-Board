import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { modelCatalog } from '../api'
import { fmtCtx, fmtUsd, modelPagePath } from '../catalog/format'
import { MODEL_TYPES, typeLabel } from '../catalog/types'
import { CONTEXT_STEPS } from './finder'

/**
 * FIND A MODEL BY WHAT IT READS AND WRITES (2026-10-15): "audio in, text out".
 *
 * Reads the whole catalogue (GET /model-catalog - every model OpenRouter lists,
 * every output type), not the registry the feature tab reads, because the
 * registry holds text models only. Inputs and outputs are OpenRouter's own
 * modalities, copied as published.
 *
 * A TICKED MODALITY IS A REQUIREMENT: a model must read every input ticked and
 * write every output ticked. A PRICE CEILING NEVER DROPS AN UNPRICED MODEL: a
 * model not priced per token cannot be compared with a per-token ceiling, so
 * it is listed apart and named, never treated as free or as too dear (rule 6).
 */

const INPUTS = ['text', 'image', 'audio', 'video', 'file']
const OUTPUTS = [...MODEL_TYPES.map((t) => t.key), 'embeddings', 'rerank']
const outLabel = (k) => (k === 'embeddings' ? 'Embeddings' : k === 'rerank' ? 'Rerank' : typeLabel(k))
const SORTS = [['name', 'A–Z'], ['price', 'Lowest input rate'], ['context', 'Largest context'], ['newest', 'Newest']]

function Chips({ label, all, on, setOn, name }) {
  const flip = (k) => setOn(on.includes(k) ? on.filter((x) => x !== k) : [...on, k])
  return (
    <div className="mf-group">
      <span className="label">{label}</span>
      <div className="mf-steps" role="group" aria-label={label}>
        {all.map((k) => (
          <button key={k} type="button" aria-pressed={on.includes(k)} onClick={() => flip(k)}
                  className={`chip${on.includes(k) ? ' chip-on' : ''}${name ? ` cat-chip t-${k}` : ''}`}>
            {name && <i aria-hidden="true" />}{name ? name(k) : k}
          </button>
        ))}
      </div>
    </div>
  )
}

function Row({ m, providerName }) {
  return (
    <div className="mf-row">
      <div className="mf-name">
        <Link to={modelPagePath(m.id)}>{m.name}</Link>
        <span className="dim">{providerName}</span>
      </div>
      <dl className="mf-specs">
        <div><dt>Context</dt><dd className="tnum">{m.context ? fmtCtx(m.context) : 'not stated'}</dd></div>
        <div><dt>In / 1M</dt><dd className="tnum">{m.price_state === 'free' ? 'Free' : m.price_in == null || m.price_state === 'not_published' ? 'not published' : fmtUsd(m.price_in)}</dd></div>
        <div><dt>Out / 1M</dt><dd className="tnum">{m.price_state === 'free' ? 'Free' : m.price_out == null || m.price_state === 'not_published' ? 'not published' : fmtUsd(m.price_out)}</dd></div>
        <div><dt>Voices</dt><dd className="tnum">{m.voices || '—'}</dd></div>
      </dl>
      <div className="mf-flags">
        <span className="mf-missing">Reads {m.inputs.join(', ')}</span>
        {m.outputs.map((o) => <span key={o} className={`cat-type t-${o}`}>{outLabel(o)}</span>)}
      </div>
      <Link className="mf-evidence" to={modelPagePath(m.id)}>Open →</Link>
    </div>
  )
}

export default function ModalityFinder() {
  const [view, setView] = useState(null)
  const [err, setErr] = useState(null)
  const [ins, setIns] = useState(['audio'])
  const [outs, setOuts] = useState(['text'])
  const [minContext, setMinContext] = useState(0)
  const [maxIn, setMaxIn] = useState('')
  const [maxOut, setMaxOut] = useState('')
  const [sort, setSort] = useState('price')

  useEffect(() => {
    let alive = true
    modelCatalog().then((v) => alive && setView(v)).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const names = useMemo(() => Object.fromEntries((view?.providers || []).flatMap((p) => p.ids.map((i) => [i, p.name]))), [view])
  const ceiling = (v) => (v === '' || Number.isNaN(Number(v)) ? null : Math.max(0, Number(v)))
  const result = useMemo(() => {
    if (!view) return null
    const cin = ceiling(maxIn)
    const cout = ceiling(maxOut)
    const fits = view.models.filter((m) => ins.every((i) => m.inputs.includes(i)) && outs.every((o) => m.outputs.includes(o))
      && (!minContext || (m.context || 0) >= minContext))
    const perToken = (m) => m.price_state !== 'not_published' && m.price_in != null && m.price_out != null
    const priced = []
    const unpriced = []
    let overPrice = 0
    for (const m of fits) {
      if (!perToken(m)) { if (cin != null || cout != null) unpriced.push(m); else priced.push(m); continue }
      const pin = m.price_state === 'free' ? 0 : m.price_in
      const pout = m.price_state === 'free' ? 0 : m.price_out
      if ((cin != null && pin > cin) || (cout != null && pout > cout)) { overPrice += 1; continue }
      priced.push(m)
    }
    const key = {
      name: (a, b) => a.name.localeCompare(b.name),
      price: (a, b) => (a.price_in ?? Infinity) - (b.price_in ?? Infinity) || a.name.localeCompare(b.name),
      context: (a, b) => (b.context || 0) - (a.context || 0) || a.name.localeCompare(b.name),
      newest: (a, b) => (b.listed_at || '').localeCompare(a.listed_at || ''),
    }[sort]
    return { match: priced.sort(key), unpriced: unpriced.sort(key), overPrice }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, ins, outs, minContext, maxIn, maxOut, sort])

  if (err) return <p className="dim tc-note">{err}</p>
  if (!view) return <div className="skel" style={{ height: 260 }} />
  if (view.reason) return <p className="dim tc-note">{view.reason}</p>

  return (
    <div className="mf-work">
      <aside className="card mf-rail" aria-label="Filters">
        <Chips label="Must read" all={INPUTS} on={ins} setOn={setIns} />
        <Chips label="Must write" all={OUTPUTS} on={outs} setOn={setOuts} name={outLabel} />
        <div className="mf-group">
          <span className="label">Context window at least</span>
          <div className="mf-steps" role="radiogroup" aria-label="Minimum context window">
            {CONTEXT_STEPS.map((n) => (
              <button key={n} type="button" role="radio" aria-checked={minContext === n}
                      className={`chip${minContext === n ? ' chip-on' : ''}`} onClick={() => setMinContext(n)}>
                {n === 0 ? 'Any' : `${fmtCtx(n)}+`}
              </button>
            ))}
          </div>
        </div>
        <div className="mf-group">
          <span className="label">Rate ceiling, USD per 1M tokens</span>
          <label className="mf-num"><span>Input at most</span>
            <input type="number" min="0" step="0.01" placeholder="no ceiling" value={maxIn} onChange={(e) => setMaxIn(e.target.value)} /></label>
          <label className="mf-num"><span>Output at most</span>
            <input type="number" min="0" step="0.01" placeholder="no ceiling" value={maxOut} onChange={(e) => setMaxOut(e.target.value)} /></label>
        </div>
        <button type="button" className="btn btn-quiet" style={{ alignSelf: 'flex-start' }}
                onClick={() => { setIns([]); setOuts([]); setMinContext(0); setMaxIn(''); setMaxOut('') }}>
          Clear filters
        </button>
      </aside>

      <section className="stack stack-2" aria-labelledby="mf-io-results">
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-label="Order">
          {SORTS.map(([k, l]) => (
            <button key={k} type="button" className={`chip${sort === k ? ' chip-on' : ''}`} aria-pressed={sort === k} onClick={() => setSort(k)}>{l}</button>
          ))}
        </div>
        <h2 id="mf-io-results" className="mf-count">
          {result.match.length} {result.match.length === 1 ? 'model' : 'models'}
          {ins.length || outs.length ? ` ${ins.length ? `reading ${ins.join(' + ')}` : ''}${ins.length && outs.length ? ' and ' : ''}${outs.length ? `writing ${outs.map(outLabel).join(' + ').toLowerCase()}` : ''}` : ''}
        </h2>
        {result.overPrice > 0 && <p className="dim tc-note">{result.overPrice} more read and write what you ticked but are above your price ceiling.</p>}
        <div className="stack stack-1">
          {result.match.map((m) => <Row key={m.id} m={m} providerName={names[m.provider] || m.provider} />)}
          {result.match.length === 0 && <p className="dim tc-note">No listed model reads and writes everything ticked{result.overPrice ? ' within your price ceiling' : ''}.</p>}
        </div>
        {result.unpriced.length > 0 && (
          <details className="tc-unpriced mf-unknown">
            <summary>{result.unpriced.length} also match but are not priced per token</summary>
            <p className="dim tc-note">
              A per-token ceiling cannot be checked against them - they are priced per second, per image
              or not at all on OpenRouter - so they are listed here rather than counted in or out.
            </p>
            <div className="stack stack-1">
              {result.unpriced.map((m) => <Row key={m.id} m={m} providerName={names[m.provider] || m.provider} />)}
            </div>
          </details>
        )}
        <p className="dim tc-note">
          {view.listed} models listed by OpenRouter; what each reads and writes is as OpenRouter publishes it.
        </p>
      </section>
    </div>
  )
}
