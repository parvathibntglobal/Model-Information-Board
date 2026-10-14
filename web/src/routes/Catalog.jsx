import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { modelCatalog } from '../api'
import { MODEL_TYPES, typeLabel } from '../catalog/types'
import { useHead } from '../seo/head'
import { catalogIndex } from '../seo/pages'
import '../styles/catalog.css'

/**
 * MODELS (2026-10-14): every model OpenRouter lists, by provider and by type.
 *
 *   /catalog                    All models: type chips, then provider bubbles;
 *                               a bubble lists that provider's models below
 *   /catalog?type=image         ... one type (the menu's "Image models")
 *   /catalog?provider=openai    ... one provider
 *   /catalog/new                New releases: the newest listings
 *
 * Read from GET /model-catalog (judge/catalog.py), never from the evidence
 * pipeline. A model with reports links to its reports page (/reports/models/...);
 * one without says so, rather than linking to an empty page (rule 4).
 */

const fmtUsd = (n) => (n === 0 ? '$0' : n >= 100 ? `$${n.toFixed(0)}` : n >= 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(3)}`)
const fmtCtx = (n) => (n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}K` : String(n))
const fmtDate = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const reportsPath = (id) => `/reports/models/${id.split('/').map(encodeURIComponent).join('/')}`

/** NO PRICE IS INVENTED (rule 6): an unpublished price says so, a free model says free. */
function Price({ m, side }) {
  if (m.price_state === 'free') return <b>Free</b>
  const v = side === 'in' ? m.price_in : m.price_out
  if (m.price_state === 'not_published' || v == null) return <span className="cat-na">Not published</span>
  return <b>{fmtUsd(v)}</b>
}

function ModelCard({ m, providerName, showProvider = true }) {
  const reads = m.inputs.filter((i) => i !== 'text')
  return (
    <article className="cat-card">
      <div className="cat-card-top">
        {showProvider ? <span className="eyebrow">{providerName}</span> : <span />}
        {m.listed_at && <span className="cat-date">Listed {fmtDate(m.listed_at)}</span>}
      </div>
      <h3>{m.name}</h3>
      <div className="cat-facts">
        <div><span>Input / 1M</span><Price m={m} side="in" /></div>
        <div><span>Output / 1M</span><Price m={m} side="out" /></div>
        <div><span>Context</span>{m.context ? <b>{fmtCtx(m.context)}</b> : <span className="cat-na">Not stated</span>}</div>
        {m.type_price && (
          <div className="cat-fact-wide"><span>{m.type_price.label} / 1M</span><b>{fmtUsd(m.type_price.usd_per_million)}</b></div>
        )}
      </div>
      <div className="cat-badges">
        {m.types.map((t) => <span key={t} className={`cat-type t-${t}`}>{typeLabel(t)}</span>)}
        {reads.length > 0 && <span className="cat-reads">Reads {reads.join(', ')}</span>}
      </div>
      <div className="cat-foot">
        {m.reported
          ? <Link to={reportsPath(m.id)}>What engineers report →</Link>
          : <span className="cat-na">{m.in_registry ? 'No engineer reports yet' : 'Not yet tracked for reports'}</span>}
        <span className="cat-id">{m.id}</span>
      </div>
    </article>
  )
}

/** New releases, grouped by the week each was listed (weeks start Monday, UTC). */
function weekOf(iso) {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7))
  return d.toISOString().slice(0, 10)
}

function NewReleases({ view, byId, names }) {
  const groups = []
  for (const id of view.new_releases) {
    const m = byId[id]
    if (!m) continue
    const w = weekOf(m.listed_at)
    if (!groups.length || groups[groups.length - 1].week !== w) groups.push({ week: w, models: [] })
    groups[groups.length - 1].models.push(m)
  }
  return (
    <div className="stack stack-4">
      {groups.map((g) => (
        <section key={g.week} className="stack stack-2">
          <h2 className="cat-week">Week of {fmtDate(g.week)} <span>{g.models.length} {g.models.length === 1 ? 'model' : 'models'}</span></h2>
          <div className="cat-grid">{g.models.map((m) => <ModelCard key={m.id} m={m} providerName={names[m.provider]} />)}</div>
        </section>
      ))}
    </div>
  )
}

function AllModels({ view, names }) {
  const [sp, setSp] = useSearchParams()
  const type = sp.get('type') || ''
  const provider = sp.get('provider') || ''
  const set = (k, v) => {
    const next = new URLSearchParams(sp)
    if (v) next.set(k, v); else next.delete(k)
    setSp(next, { replace: true })
  }
  const ofType = useMemo(() => view.models.filter((m) => !type || m.types.includes(type)), [view, type])
  // A bubble may stand for several provider ids (Meta: `meta`, `meta-llama`).
  const providers = useMemo(() => {
    const n = {}
    for (const m of ofType) n[m.provider] = (n[m.provider] || 0) + 1
    return view.providers
      .map((p) => ({ ...p, shown: p.ids.reduce((t, i) => t + (n[i] || 0), 0) }))
      .filter((p) => p.shown)
  }, [view, ofType])
  const chosen = view.providers.find((p) => p.id === provider)
  const listed = chosen ? ofType.filter((m) => chosen.ids.includes(m.provider)) : type ? ofType : []
  // PICKING A BUBBLE SCROLLS TO ITS MODELS: with 80 bubbles above them, the
  // list would otherwise open below the fold and read as nothing happening.
  const results = useRef(null)
  const picked = useRef(false)
  useEffect(() => {
    if (picked.current && provider && results.current) results.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    picked.current = false
  }, [provider])
  const sorted = [...listed].sort((a, b) => (b.listed_at || '').localeCompare(a.listed_at || ''))

  return (
    <div className="stack stack-4">
      <div className="cat-types" role="group" aria-label="Model type">
        <button type="button" className={`chip${!type ? ' chip-on' : ''}`} aria-pressed={!type} onClick={() => set('type', '')}>
          All types <span className="x">{view.listed}</span>
        </button>
        {MODEL_TYPES.map((t) => (
          <button key={t.key} type="button" className={`chip cat-chip t-${t.key}${type === t.key ? ' chip-on' : ''}`}
                  aria-pressed={type === t.key} disabled={!view.types[t.key]} onClick={() => set('type', t.key)}>
            <i aria-hidden="true" />{t.label} <span className="x">{view.types[t.key] || 0}</span>
          </button>
        ))}
      </div>

      <div className="stack stack-2">
        <span className="eyebrow">{providers.length} providers{type ? ` with ${typeLabel(type).toLowerCase()} models` : ''}</span>
        <div className="cat-bubbles">
          {providers.map((p) => (
            <button key={p.id} type="button" className={`cat-bubble${provider === p.id ? ' on' : ''}`}
                    aria-pressed={provider === p.id} title={p.ids.length > 1 ? `OpenRouter ids: ${p.ids.join(', ')}` : undefined}
                    onClick={() => { picked.current = true; set('provider', provider === p.id ? '' : p.id) }}>
              <span className="cat-mono" aria-hidden="true">{p.name.slice(0, 1)}</span>{p.name}<span className="cat-n">{p.shown}</span>
            </button>
          ))}
        </div>
      </div>

      {listed.length ? (
        <section className="stack stack-2" ref={results} style={{ scrollMarginTop: 90 }}>
          <h2 className="cat-week">
            {chosen ? chosen.name : 'All providers'}{type ? ` · ${typeLabel(type)} models` : ''}
            <span>{listed.length} {listed.length === 1 ? 'model' : 'models'}, newest first</span>
          </h2>
          <div className="cat-grid">{sorted.map((m) => <ModelCard key={m.id} m={m} providerName={names[m.provider]} showProvider={!provider} />)}</div>
        </section>
      ) : (
        <p className="cat-hint">Pick a provider to see its models{type ? '' : ', or a type above to see every model of that type'}.</p>
      )}
    </div>
  )
}

export default function Catalog() {
  const rest = useParams()['*'] || ''
  const isNew = rest === 'new'
  const [sp] = useSearchParams()
  const [state, setState] = useState({ view: null, err: null })

  useEffect(() => {
    let alive = true
    modelCatalog()
      .then((view) => alive && setState({ view, err: null }))
      .catch((e) => alive && setState({ view: null, err: e.message || 'The models could not be read.' }))
    return () => { alive = false }
  }, [])

  const type = sp.get('type') || ''
  useHead(catalogIndex(isNew ? 'new' : type || null))
  const view = state.view
  const names = useMemo(() => Object.fromEntries((view?.providers || []).flatMap((p) => p.ids.map((i) => [i, p.name]))), [view])
  const byId = useMemo(() => Object.fromEntries((view?.models || []).map((m) => [m.id, m])), [view])

  const title = isNew ? 'New releases' : type ? `${typeLabel(type)} models` : 'All models'
  const lede = isNew
    ? `The ${view?.new_releases?.length || 40} models OpenRouter listed most recently, newest first.`
    : 'Every model OpenRouter lists, from every provider. Pick a type, then a provider, to see its models.'

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="go-badge go-models page-tag" style={{ alignSelf: 'flex-start' }}>Models</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>{title}</h1>
        <p className="muted" style={{ maxWidth: '72ch', margin: 0 }}>{lede}</p>
        <nav className="cat-tabs" aria-label="Models">
          <Link to="/catalog" className={!isNew ? 'on' : ''}>All models</Link>
          <Link to="/catalog/new" className={isNew ? 'on' : ''}>New releases</Link>
          <Link to="/compare">Compare models</Link>
          <Link to="/reports">Most reported</Link>
        </nav>
      </div>

      {!view && !state.err && <div className="skel" style={{ height: 220 }} />}
      {state.err && <p className="cat-hint">{state.err}</p>}
      {view && view.reason && <p className="cat-hint">{view.reason}</p>}
      {view && !view.reason && (isNew ? <NewReleases view={view} byId={byId} names={names} /> : <AllModels view={view} names={names} />)}

      {view && !view.reason && (
        <p className="cat-source">
          Listed by <a href="https://openrouter.ai/models" target="_blank" rel="noreferrer">OpenRouter</a>,
          read {fmtDate(view.polled_at.slice(0, 10))}: {view.listed} models from {view.providers.length} providers.
          A type is the output OpenRouter lists for a model; prices are its list prices.
          {view.aliases_left_out ? ` ${view.aliases_left_out} "latest" aliases are left out, each a pointer to a model listed under its own name.` : ''}
        </p>
      )}
    </div>
  )
}
