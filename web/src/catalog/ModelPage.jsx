import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { modelCatalogEntry, reportsPage } from '../api'
import { useHead } from '../seo/head'
import { catalogModelHead } from '../seo/pages'
import { DAYS_PER_MONTH, fmtUsd as fmtCost, workloadCost } from '../tokens/cost'
import PersonaPicker from '../tokens/PersonaPicker'
import { PERSONAS } from '../tokens/personas'
import { SECTION_OF_KIND, evidencePath, fmtCtx, fmtDate, fmtUsd, modelPagePath, reportsPath } from './format'
import { typeLabel } from './types'

/**
 * ONE MODEL (2026-10-14), for every model the catalogue lists - not only the
 * ones engineers have reported on. Four parts, each from where it is recorded:
 *
 *   Price            OpenRouter's list prices (model_catalog)
 *   Your workload    the token counter's arithmetic (tokens/cost.js) on this
 *                    model's prices, started from a persona
 *   Specs            what the spec finder shows: context, output, inputs,
 *                    features - each feature true, false or NOT STATED (rule 6)
 *   Engineer voices  counted from the public view; the jobs and capabilities
 *                    with the most voices, and a link to every report
 */

const KIND_LABEL = { job: 'Job', capability: 'Capability', metric: 'Metric' }
const FEATURES = [
  ['tools', 'Tool calling'],
  ['structured_output', 'Structured output'],
  ['reasoning', 'Reasoning mode'],
  ['vision_input', 'Image input'],
  ['prompt_caching', 'Prompt caching'],
]

function Feature({ v }) {
  if (v == null) return <span className="mp2-na">Not stated</span>
  return v ? <span className="mp2-yes">Yes</span> : <span className="mp2-no">No</span>
}

function Workload({ m }) {
  const first = PERSONAS[0]
  const [w, setW] = useState({ inTok: first.inTok, outTok: first.outTok, perDay: first.perDay, cached: first.cached })
  const num = (k) => (e) => setW({ ...w, [k]: Math.max(0, Math.floor(Number(e.target.value) || 0)) })
  const tokenPriced = m.price_state === 'priced' && m.price_in != null && m.price_out != null
  const cost = tokenPriced
    ? workloadCost({ price_in: m.price_in, price_out: m.price_out, price_cached_read: m.price_cached_read },
      { inTok: w.inTok, outTok: w.outTok, callsPerDay: w.perDay, cachedShare: w.cached / 100 })
    : null
  return (
    <section className="card stack stack-3">
      <h2 className="mp2-h">What your workload would cost on {m.name}</h2>
      <PersonaPicker value={w} onPick={setW} />
      <div className="mp2-form">
        <label><span className="label">Input tokens / call</span><input type="number" min="0" value={w.inTok} onChange={num('inTok')} /></label>
        <label><span className="label">Output tokens / call</span><input type="number" min="0" value={w.outTok} onChange={num('outTok')} /></label>
        <label><span className="label">Calls / day</span><input type="number" min="0" value={w.perDay} onChange={num('perDay')} /></label>
        <label><span className="label">Input read from cache</span>
          <span className="mp2-pct"><input type="range" min="0" max="100" step="5" value={w.cached}
                 onChange={(e) => setW({ ...w, cached: Number(e.target.value) })} aria-label="Share of input read from cache" />
            <span className="tnum">{w.cached}%</span></span></label>
      </div>
      {cost ? (
        <div className="mp2-costs">
          <div><span>Per call</span><b>{fmtCost(cost.perCall)}</b></div>
          <div><span>Per day</span><b>{fmtCost(cost.perDay)}</b></div>
          <div className="big"><span>Per month ({DAYS_PER_MONTH} days)</span><b>{fmtCost(cost.perMonth)}</b></div>
        </div>
      ) : (
        <p className="mp2-na">
          {m.price_state === 'free' ? 'This is a free variant: OpenRouter lists no charge for it.'
            : 'This model is not priced per token on OpenRouter, so a token workload cannot be priced on it.'}
        </p>
      )}
      <p className="mp2-note">
        List prices times your token counts{cost && cost.cache === 'none' && w.cached > 0
          ? '. No cached-read price is published for this model, so the cached share is priced at the full input rate'
          : cost && cost.cache === 'applied' ? ', with the cached share at the published cached-read price' : ''}.
        Cache writes and batch discounts are not included. For your own text, use the{' '}
        <Link to="/token-counter">token counter</Link>.
      </p>
    </section>
  )
}

function Voices({ m }) {
  const [axes, setAxes] = useState(null)
  useEffect(() => {
    if (!m.voices) return undefined
    let alive = true
    reportsPage().then((r) => alive && setAxes(r.axes || [])).catch(() => alive && setAxes([]))
    return () => { alive = false }
  }, [m.voices])
  const top = useMemo(() => (axes || [])
    .map((a) => ({ a, row: a.models.find((x) => x.canonical === m.id) }))
    .filter((x) => x.row && x.row.voices > 0)
    .sort((x, y) => y.row.voices - x.row.voices || y.row.reports - x.row.reports)
    .slice(0, 8), [axes, m.id])

  if (!m.voices) {
    return (
      <section className="card stack stack-2">
        <h2 className="mp2-h">What engineers report</h2>
        <p className="mp2-na">
          No engineer voices yet. {m.in_registry
            ? 'We track this model and nobody we read has reported on it publicly.'
            : 'This model is not yet one we collect reports for.'} That is an absence of reports, not a verdict.
        </p>
      </section>
    )
  }
  return (
    <section className="card stack stack-2">
      <div className="mp2-row">
        <h2 className="mp2-h">What engineers report</h2>
        {/* EVERY COUNT HERE OPENS ITS REPORTS (2026-10-21): the evidence feed,
            narrowed the way the number was counted. */}
        <Link to={evidencePath(m.id)} className="mp2-count ev-open"
              title={`Read the ${m.reports} reports behind this count`}>
          <b>{m.voices}</b> {m.voices === 1 ? 'voice' : 'voices'} · {m.reports} reports
        </Link>
      </div>
      {axes == null ? <div className="skel" style={{ height: 120 }} /> : (
        <ul className="mp2-axes">
          {top.map(({ a, row }) => {
            const s = row.split || {}
            const at = { section: SECTION_OF_KIND[a.kind], slug: a.slug }
            // A zero opens nothing: an empty list says less than the 0 does.
            const side = (k, cls) => (s[k] ? (
              <Link to={evidencePath(m.id, { ...at, polarity: k })} className={`${cls} ev-open`}
                    title={`Read the ${s[k]} ${k} reports on ${a.name}`}>{s[k]}</Link>
            ) : <span className={cls}>0</span>)
            return (
              <li key={`${a.kind}:${a.slug}`}>
                <span className="mp2-kind">{KIND_LABEL[a.kind] || a.kind}</span>
                <Link to={evidencePath(m.id, at)} className="mp2-axis ev-open"
                      title={`Read the ${row.reports} reports on ${a.name}`}>{a.name}</Link>
                {/* A METRIC CARRIES NO POLARITY (2026-10-15): a stated figure is
                    not praised or criticised, so its row shows no split. */}
                {a.kind === 'metric' ? <span /> : (
                  <span className="mp2-split" title="Positive / negative / neutral reports">
                    {side('positive', 'p')}{side('negative', 'n')}{side('neutral', 'z')}
                  </span>
                )}
                <Link to={evidencePath(m.id, at)} className="mp2-v ev-open"
                      title={`Read the reports these ${row.voices} voices wrote on ${a.name}`}>
                  {row.voices} {row.voices === 1 ? 'voice' : 'voices'}
                </Link>
              </li>
            )
          })}
        </ul>
      )}
      <Link to={reportsPath(m.id)} className="btn btn-ghost" style={{ alignSelf: 'flex-start' }}>Every job, capability and metric →</Link>
      <p className="mp2-note">Counted, never scored. A voice is one person; a report is one post.</p>
    </section>
  )
}

/** Days from today (UTC) to an ISO date: negative once it has passed. */
function daysUntil(iso) {
  const today = new Date(new Date().toISOString().slice(0, 10) + 'T00:00:00Z')
  return Math.round((new Date(`${iso}T00:00:00Z`) - today) / 86400000)
}

/**
 * LIFECYCLE (2026-10-15): the dates a reader needs before building on a model,
 * each with where it came from. Retirement first, because it is the one that
 * breaks a build. "No retirement announced" is said in those words: an absent
 * date is not a promise the model stays (rule 6).
 */
function Lifecycle({ m }) {
  const lc = m.lifecycle || {}
  const soonest = (lc.retirements || []).slice().sort((a, b) => a.date.localeCompare(b.date))[0]
  const d = soonest ? daysUntil(soonest.date) : null
  const rows = [
    ['Released', lc.released, 'registry'],
    ['Listed on OpenRouter', lc.listed, null],
    ['Knowledge cutoff', lc.knowledge_cutoff, lc.knowledge_cutoff_source],
    ['Deprecated', lc.deprecated, 'registry'],
  ].filter(([, v]) => v)
  return (
    <section className="card stack stack-2">
      <h2 className="mp2-h">Lifecycle</h2>
      <div className={`mp2-retire${soonest ? (d < 0 ? ' gone' : d <= 30 ? ' soon' : '') : ''}`}>
        {soonest ? (
          <>
            <b>{d < 0 ? `Retired ${fmtDate(soonest.date)}` : `Retires ${fmtDate(soonest.date)}`}</b>
            <span>{d < 0 ? `${-d} days ago` : d === 0 ? 'today' : `in ${d} ${d === 1 ? 'day' : 'days'}`}</span>
            <small>
              {lc.retirements.map((r) => `${fmtDate(r.date)} (${r.source})`).join(' · ')}: the date OpenRouter stops serving it
            </small>
          </>
        ) : (
          <><b>No retirement announced</b><small>Neither OpenRouter nor our registry lists a date. That is not a promise it stays.</small></>
        )}
      </div>
      {rows.length > 0 && (
        <dl className="mp2-dl">
          {rows.map(([label, v, src]) => (
            <div key={label}><dt>{label}{src && <span className="mp2-src"> · {src === 'registry' ? 'registry' : src}</span>}</dt><dd>{fmtDate(v)}</dd></div>
          ))}
        </dl>
      )}
      {(lc.newer_from_provider || []).length > 0 && (
        <div className="stack stack-1">
          <span className="label">Listed more recently by {m.provider_name}</span>
          <div className="mp2-newer">
            {lc.newer_from_provider.map((n) => (
              <Link key={n.id} to={modelPagePath(n.id)}>{n.name} <span>{fmtDate(n.listed_at)}</span></Link>
            ))}
          </div>
          <p className="mp2-note">Newer listings of the same kind from the same provider - not a statement that any of them replaces this one.</p>
        </div>
      )}
    </section>
  )
}

export default function ModelPage({ id }) {
  const [state, setState] = useState({ m: null, err: null })
  useEffect(() => {
    let alive = true
    setState({ m: null, err: null })
    modelCatalogEntry(id)
      .then((m) => alive && setState({ m, err: null }))
      .catch((e) => alive && setState({ m: null, err: e.message || 'This model could not be read.' }))
    return () => { alive = false }
  }, [id])
  const m = state.m
  useHead(m ? catalogModelHead(m) : null)

  if (state.err) {
    return (
      <div className="shell section-tight stack stack-2">
        <p className="cat-hint">{state.err}</p>
        <Link to="/catalog">← All models</Link>
      </div>
    )
  }
  if (!m) return <div className="shell section-tight"><div className="skel" style={{ height: 320 }} /></div>

  return (
    <div className="shell section-tight stack stack-4 mp2">
      <div className="stack stack-1">
        <p className="crumb"><Link to="/catalog">Models</Link><i>/</i><Link to={`/catalog?provider=${encodeURIComponent(m.provider)}`}>{m.provider_name}</Link></p>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>{m.name}</h1>
        <div className="cat-badges">
          {m.types.map((t) => <span key={t} className={`cat-type t-${t}`}>{typeLabel(t)}</span>)}
          {m.listed_at && <span className="cat-reads">Listed {fmtDate(m.listed_at)}</span>}
          <span className="cat-id">{m.id}</span>
        </div>
        {m.description && <p className="muted" style={{ maxWidth: '78ch', margin: 0 }}>{m.description}</p>}
        <div className="mp2-actions">
          {m.in_registry
            ? <Link to={`/compare?ids=${encodeURIComponent(m.id)}`} className="btn btn-ghost">Compare with…</Link>
            : <span className="mp2-na" title="Comparisons are of what engineers report, so they cover the models we collect reports for">Not comparable yet</span>}
          <a href={m.source} target="_blank" rel="noreferrer" className="btn btn-quiet">On OpenRouter ↗</a>
        </div>
      </div>

      <div className="mp2-grid">
        <section className="card stack stack-2">
          <h2 className="mp2-h">Price</h2>
          {m.price_state === 'not_published' ? (
            <p className="mp2-na">OpenRouter publishes no per-token price for this model{m.type_price ? '' : ', and none we can show'}.</p>
          ) : (
            <dl className="mp2-dl">
              <div><dt>Input / 1M tokens</dt><dd>{m.price_state === 'free' ? 'Free' : m.price_in == null ? '—' : fmtUsd(m.price_in)}</dd></div>
              <div><dt>Output / 1M tokens</dt><dd>{m.price_state === 'free' ? 'Free' : m.price_out == null ? '—' : fmtUsd(m.price_out)}</dd></div>
              <div><dt>Cached input / 1M</dt><dd>{m.price_cached_read == null ? <span className="mp2-na">Not published</span> : fmtUsd(m.price_cached_read)}</dd></div>
            </dl>
          )}
          {m.type_price && <dl className="mp2-dl"><div><dt>{m.type_price.label} / 1M</dt><dd>{fmtUsd(m.type_price.usd_per_million)}</dd></div></dl>}
          <p className="mp2-note">OpenRouter's list prices; a provider's own price can differ.</p>
        </section>

        <section className="card stack stack-2">
          <h2 className="mp2-h">Specs</h2>
          <dl className="mp2-dl">
            <div><dt>Context window</dt><dd>{m.context ? fmtCtx(m.context) : <span className="mp2-na">Not stated</span>}</dd></div>
            <div><dt>Longest answer</dt><dd>{m.max_output_tokens ? `${fmtCtx(m.max_output_tokens)} tokens` : <span className="mp2-na">Not stated</span>}</dd></div>
            <div><dt>Reads</dt><dd>{m.inputs.join(', ') || '—'}</dd></div>
            <div><dt>Writes</dt><dd>{m.outputs.join(', ') || '—'}</dd></div>
            {FEATURES.map(([k, label]) => <div key={k}><dt>{label}</dt><dd><Feature v={m.features[k]} /></dd></div>)}
          </dl>
          <p className="mp2-note">"Not stated" means OpenRouter does not say - not that the model lacks it.</p>
        </section>
      </div>

      <Lifecycle m={m} />

      <Workload m={m} />
      <Voices m={m} />
    </div>
  )
}
