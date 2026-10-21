import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { modelCatalog } from '../api'
import ModelPage from '../catalog/ModelPage'
import { fmtCtx, fmtDate, fmtUsd, modelPagePath } from '../catalog/format'
import { MODEL_TYPES, typeLabel } from '../catalog/types'
import { useHead } from '../seo/head'
import { catalogIndex } from '../seo/pages'
import '../styles/catalog.css'

/**
 * MODELS (2026-10-14): every model OpenRouter lists, by provider and by type.
 *
 *   /ai-models                  All models: the models engineers have reported
 *                               on, most voices first; type chips above
 *                               provider bubbles; a bubble lists its models
 *   /ai-models/image            ... one type (the menu's "Image models"); was
 *                               ?type=image, which still opens and moves here
 *   /ai-models?provider=openai  ... one provider
 *   /ai-models/latest           Latest releases: the newest listings, voiced or not
 *                               (was /ai-models/new until 2026-10-21; it moves here)
 *   /ai-models/<provider>/<model>  ONE model: price, workload cost, specs, voices
 *
 * THE ADDRESS (2026-10-21) was /catalog, /catalog/new and /catalog/model/<id>:
 * "catalog" is a word nobody searches, and "ai models" is what people type.
 * An old /catalog address still opens and moves here (App.jsx, CatalogMoved).
 *
 * Read from GET /model-catalog (judge/catalog.py), never from the evidence
 * pipeline. Every card opens its model's page.
 */

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
    <Link to={modelPagePath(m.id)} className="cat-card">
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
        {m.voices
          ? <span className="cat-voices"><b>{m.voices}</b> {m.voices === 1 ? 'voice' : 'voices'} · {m.reports} {m.reports === 1 ? 'report' : 'reports'}</span>
          : <span className="cat-na">No engineer voices yet</span>}
        <span className="cat-open">Open →</span>
      </div>
    </Link>
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

/**
 * ALL MODELS LISTS THE MODELS ENGINEERS HAVE REPORTED ON (2026-10-14), most
 * distinct voices first - a COUNT, shown on every card beside the order it
 * makes (rule 3). A type with no voiced model stays empty until one arrives.
 * Every other listed model is still one click away, in New releases and on its
 * own page; the page says how many, so the shorter list is not read as all.
 */
function AllModels({ view, names, type }) {
  const [sp, setSp] = useSearchParams()
  const navigate = useNavigate()
  const provider = sp.get('provider') || ''
  // A TYPE IS AN ADDRESS (/ai-models/image, 2026-10-21), so Google can list
  // "image models" as a page; a provider stays a filter on it.
  const set = (k, v) => {
    if (k === 'type') {
      navigate(`/ai-models${v ? `/${v}` : ''}${sp.toString() ? `?${sp}` : ''}`, { replace: true })
      return
    }
    const next = new URLSearchParams(sp)
    if (v) next.set(k, v); else next.delete(k)
    setSp(next, { replace: true })
  }
  const voiced = useMemo(() => view.models.filter((m) => m.voices > 0), [view])
  const ofType = useMemo(() => voiced.filter((m) => !type || m.types.includes(type)), [voiced, type])
  // A bubble may stand for several provider ids (Meta: `meta`, `meta-llama`).
  const providers = useMemo(() => {
    const n = {}
    const v = {}
    for (const m of ofType) { n[m.provider] = (n[m.provider] || 0) + 1; v[m.provider] = (v[m.provider] || 0) + m.voices }
    return view.providers
      .map((p) => ({ ...p, shown: p.ids.reduce((t, i) => t + (n[i] || 0), 0) }))
      .filter((p) => p.shown)
      .sort((a, b) => b.shown - a.shown || a.name.localeCompare(b.name))
  }, [view, ofType])
  const chosen = view.providers.find((p) => p.id === provider)
  const listed = (chosen ? ofType.filter((m) => chosen.ids.includes(m.provider)) : ofType)
    .slice().sort((a, b) => b.voices - a.voices || b.reports - a.reports || a.name.localeCompare(b.name))
  // PICKING A BUBBLE SCROLLS TO ITS MODELS, which sit below every bubble.
  const results = useRef(null)
  const picked = useRef(false)
  useEffect(() => {
    if (picked.current && provider && results.current) results.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    picked.current = false
  }, [provider])
  const unvoiced = view.listed - voiced.length

  return (
    <div className="stack stack-4">
      <div className="cat-types" role="group" aria-label="Model type">
        <button type="button" className={`chip${!type ? ' chip-on' : ''}`} aria-pressed={!type} onClick={() => set('type', '')}>
          All types <span className="x">{voiced.length}</span>
        </button>
        {MODEL_TYPES.map((t) => (
          <button key={t.key} type="button" className={`chip cat-chip t-${t.key}${type === t.key ? ' chip-on' : ''}`}
                  aria-pressed={type === t.key} disabled={!view.types_voiced[t.key]} onClick={() => set('type', t.key)}
                  title={view.types_voiced[t.key] ? undefined : `No ${t.label.toLowerCase()} model has an engineer voice yet`}>
            <i aria-hidden="true" />{t.label} <span className="x">{view.types_voiced[t.key] || 0}</span>
          </button>
        ))}
      </div>

      <div className="stack stack-2">
        <span className="eyebrow">{providers.length} providers{type ? ` with voiced ${typeLabel(type).toLowerCase()} models` : ' with voiced models'}</span>
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

      <section className="stack stack-2" ref={results} style={{ scrollMarginTop: 90 }}>
        <h2 className="cat-week">
          {chosen ? chosen.name : 'All providers'}{type ? ` · ${typeLabel(type)} models` : ''}
          <span>{listed.length} {listed.length === 1 ? 'model' : 'models'}, most engineer voices first</span>
        </h2>
        {listed.length
          ? <div className="cat-grid">{listed.map((m) => <ModelCard key={m.id} m={m} providerName={names[m.provider]} showProvider={!chosen} />)}</div>
          : <p className="cat-hint">No model here has an engineer voice yet.</p>}
      </section>

      <p className="cat-hint">
        These are the {voiced.length} models engineers have reported on. OpenRouter lists {unvoiced} more
        with no engineer voice yet; they are in <Link to="/ai-models/latest">Latest AI model releases</Link> and each has its own page.
        A voice is one person: someone who posted about a model several times counts once.
      </p>
    </div>
  )
}

export default function Catalog() {
  const rest = useParams()['*'] || ''
  // A model id is `provider/model`, so a path with a slash in it is one model.
  const modelId = rest.includes('/') ? decodeURIComponent(rest) : null
  const isNew = rest === 'latest'
  const [sp] = useSearchParams()
  const [state, setState] = useState({ view: null, err: null })

  useEffect(() => {
    if (modelId) return undefined
    let alive = true
    modelCatalog()
      .then((view) => alive && setState({ view, err: null }))
      .catch((e) => alive && setState({ view: null, err: e.message || 'The models could not be read.' }))
    return () => { alive = false }
  }, [modelId])

  const type = MODEL_TYPES.some((t) => t.key === rest) ? rest : ''
  const oldType = !rest && MODEL_TYPES.some((t) => t.key === sp.get('type')) ? sp.get('type') : ''
  const view = state.view
  // THE LIST FOR STRUCTURED DATA (2026-10-21): the models this page shows, in
  // its order - newest first on New releases; most voices first otherwise, as
  // AllModels sorts them before a provider is picked. The first 50.
  const listed = useMemo(() => {
    if (!view || view.reason || modelId) return []
    const by = Object.fromEntries((view.models || []).map((m) => [m.id, m]))
    const models = isNew
      ? (view.new_releases || []).map((id) => by[id]).filter(Boolean)
      : view.models.filter((m) => m.voices > 0 && (!type || m.types.includes(type)))
        .slice().sort((a, b) => b.voices - a.voices || b.reports - a.reports || a.name.localeCompare(b.name))
    return models.slice(0, 50).map((m) => ({ name: m.name, path: modelPagePath(m.id) }))
  }, [view, isNew, type, modelId])
  useHead(modelId || oldType ? null : catalogIndex(isNew ? 'new' : type || null, listed))
  const names = useMemo(() => Object.fromEntries((view?.providers || []).flatMap((p) => p.ids.map((i) => [i, p.name]))), [view])
  const byId = useMemo(() => Object.fromEntries((view?.models || []).map((m) => [m.id, m])), [view])

  if (modelId) return <ModelPage id={modelId} />
  if (rest === 'new') return <Navigate to={`/ai-models/latest${sp.toString() ? `?${sp}` : ''}`} replace />
  if (oldType) {
    const keep = new URLSearchParams(sp)
    keep.delete('type')
    return <Navigate to={`/ai-models/${oldType}${keep.toString() ? `?${keep}` : ''}`} replace />
  }

  const title = isNew ? 'Latest AI model releases' : type ? `${typeLabel(type)} models` : 'All models'
  // THE SHORT ANSWERS (2026-10-22, approved draft): keyword-led.
  const lede = isNew
    ? `The latest AI models: the ${view?.new_releases?.length || 40} most recently listed, newest first, with price, context window and type.`
    : type
      ? `${typeLabel(type)} AI models engineers have reported on, by provider, with price and context window.`
      : 'A list of AI models engineers have reported on, by provider and type (text, image, video, speech and more), most-reported first. Pick a type, then a provider.'

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="go-badge go-models page-tag" style={{ alignSelf: 'flex-start' }}>Models</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>{title}</h1>
        <p className="muted" style={{ maxWidth: '72ch', margin: 0 }}>{lede}</p>
        <nav className="cat-tabs" aria-label="Models">
          <Link to="/ai-models" className={!isNew ? 'on' : ''}>All models</Link>
          <Link to="/ai-models/latest" className={isNew ? 'on' : ''}>Latest AI model releases</Link>
          <Link to="/compare">AI model comparison</Link>
          <Link to="/reviews">AI model reviews</Link>
        </nav>
      </div>

      {!view && !state.err && <div className="skel" style={{ height: 220 }} />}
      {state.err && <p className="cat-hint">{state.err}</p>}
      {view && view.reason && <p className="cat-hint">{view.reason}</p>}
      {view && !view.reason && (isNew ? <NewReleases view={view} byId={byId} names={names} /> : <AllModels view={view} names={names} type={type} />)}

      {view && !view.reason && (
        <p className="cat-source">
          Listed by <a href="https://openrouter.ai/models" target="_blank" rel="noreferrer">OpenRouter</a>,
          read {fmtDate(view.polled_at.slice(0, 10))}: {view.listed} models from {view.providers.length} providers.
          A type is the output OpenRouter lists for a model; prices are its list prices. Voices and reports
          count what engineers posted publicly, from every source this site reads.
          {view.aliases_left_out ? ` ${view.aliases_left_out} "latest" aliases are left out, each a pointer to a model listed under its own name.` : ''}
        </p>
      )}
    </div>
  )
}
