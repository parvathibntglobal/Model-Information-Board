import { useEffect, useState } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { modelPage, listModels, fetchAll, fmtPrice, fmtTokens, fmtInt, BoardUnreadable } from '../api'
import FetchPanel from '../components/FetchPanel'
import ModelEvidence from '../components/ModelEvidence'
import { Badge, Notice, Reveal, Stat, Unreadable } from '../components/ui'
import { IconAlert, IconArrow } from '../components/Icons'

export default function ModelDetail() {
  // `/models/*` rather than `/models/:id`, because an id can contain a
  // slash — google/gemini-2.5-flash is one path segment to us, two to the router.
  const id = useParams()['*']
  const { state } = useLocation()
  const [page, setPage] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  // GET /models/{id} still returns no display_name and no price, so the spec
  // comes from the roster. Router state covers an in-app click instantly; a
  // pasted or refreshed URL falls back to one call and finds itself in it.
  const [spec, setSpec] = useState(null)
  const name = spec?.display_name || state?.name || id

  useEffect(() => {
    setPage(null); setErr(null); setUnreadable(null)
    modelPage(id)
      .then(setPage)
      .catch((e) => (e instanceof BoardUnreadable ? setUnreadable(e.message) : setErr(e.message)))
  }, [id])

  useEffect(() => {
    let live = true
    setSpec(null)
    fetchAll((l, o) => listModels(l, o))
      .then((list) => {
        if (!live) return
        setSpec(list.models.find((m) => m.model_version_id === id) || null)
      })
      .catch(() => {})   // the spec panel is additive; its absence must not blank the page
    return () => { live = false }
  }, [id])

  // Back goes to the Models page, which is where the roster lives and where
  // this page is reached from. Arriving from the Board is the one exception,
  // because sending those visitors to /models would undo their navigation.
  const back = state?.from === '/board'
    ? { to: '/board', label: 'Back to the board' }
    : { to: '/models', label: 'Back to all models' }

  return (
    <div className="shell section-tight stack stack-4">
      <Link to={back.to} className="row" style={{ gap: 8, fontSize: 'var(--fs-xs)', color: 'var(--text-2)' }}>
        <IconArrow width={13} height={13} style={{ transform: 'rotate(180deg)' }} /> {back.label}
      </Link>

      <div className="stack stack-1">
        <span className="eyebrow">Model</span>
        <h1 style={{ fontSize: 'var(--fs-display)', wordBreak: 'break-word' }}>{name}</h1>
        {spec?.provider && <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>{spec.provider}</span>}
      </div>

      {/* NOT RENDERED FOR A MODEL THE REGISTRY DOES NOT HOLD. `in_registry`
          false means the OpenRouter poll has never seen it - Recraft,
          ElevenLabs, Qwen3.5 Omni Flash - so every figure in this panel would
          be a dash and the caveat underneath would be a sentence about
          routing, which is false about all three. An absent panel says "we
          have nothing here"; a panel of dashes says "we looked and it is
          nothing", and those are different claims. */}
      {spec && spec.in_registry !== false && <SpecPanel s={spec} />}

      <FetchPanel modelVersionId={id} onDone={() => modelPage(id).then(setPage).catch(() => {})} />

      {/* What was actually said about this model, grouped by the sections the
          classifier discovered. Placed directly under Fetch so the button and
          the evidence it produces are read together — clicking Fetch and then
          scrolling past six panels to find what changed is how a reader
          concludes nothing happened. */}
      <ModelEvidence modelVersionId={id} />

      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!page && !err && !unreadable && <div className="skel" style={{ height: 120 }} />}

      {/* NOT TRACKED stays in the open, outside the disclosure below.
          `tracked: false` is a fact about the MODEL — nobody has ever swept it —
          rather than a fact about capabilities, and it is the one silence on
          this page a reader can act on. Rule 4 is about not letting "we did not
          look" read like "nothing was found"; collapsing an actionable absence
          would be the same mistake with an extra click in front of it. */}
      {page?.tracked === false && (
        <div className="notice" style={{ borderColor: 'var(--warn)', background: 'var(--warn-dim, rgba(224,175,104,.1))' }}>
          <IconAlert style={{ flex: 'none', marginTop: 2, color: 'var(--warn)' }} />
          <div>
            <strong style={{ color: 'var(--text)' }}>Not tracked yet.</strong>{' '}
            This model has never been swept for evidence — nobody has looked at it.
            An empty evidence panel above means <em>we have not asked</em>, not that
            engineers reported no problems. That is different from a tracked model
            with no evidence, and you can change it by asking for this model to be
            tracked.
          </div>
        </div>
      )}

      {/* THE CAPABILITY CARDS ARE GONE FROM THIS PAGE.
          They showed the ratified twelve - a closed vocabulary feeding the
          legacy cell score - underneath an evidence panel keyed to nothing at
          all. Folding them into a disclosure said "secondary"; removing them
          says "not this page's job", which is truer: six of the eight
          capability sections on the reference board have no ratified key and
          could never have appeared here.

          UI ONLY, AND NOTHING IS DESTROYED. E7 still writes `cell` on every
          fetch, the Ask box still refuses to recommend a model without a
          published one, and the models list still counts them for its evidence
          badge. `GET /models/{id}` still returns `capabilities`; this page
          stops rendering them. */}
    </div>
  )
}



/**
 * What the provider advertises. Kept visually separate from everything below
 * it, and labelled, because this is the one block on the page nobody has
 * verified — the rest of the model page is gated evidence, and price sitting
 * unmarked beside it would borrow a credibility it has not earned.
 */
function SpecPanel({ s }) {
  const unpriced = s.price_in == null

  const features = [
    ['Tools', s.supports_tools],
    ['Vision', s.supports_vision],
    ['Structured output', s.supports_structured_output],
    ['Caching', s.supports_caching],
  ]

  return (
    <Reveal>
      <div className="card stack stack-3">
        <div className="row" style={{ justifyContent: 'space-between', gap: 'var(--s3)', flexWrap: 'wrap' }}>
          <span className="eyebrow">As advertised by the provider</span>
          <Badge tone="mute">not evidence</Badge>
        </div>

        <div className="grid g4">
          <Stat n={unpriced ? '—' : fmtPrice(s.price_in)} l="input · per Mtok" />
          <Stat n={unpriced ? '—' : fmtPrice(s.price_out)} l="output · per Mtok" />
          <Stat n={s.advertised_context ? fmtTokens(s.advertised_context) : '—'} l="context window" />
          <Stat n={s.max_output_tokens ? fmtTokens(s.max_output_tokens) : '—'} l="max output" />
        </div>

        {/* ⚠ THIS SAID "it routes requests to other models" FOR ANY NULL PRICE.
            A router is one REASON a registry row has no rate; it is not the
            only one, and a null cannot tell you which. The panel now only
            renders for models the registry holds, where a missing rate does
            mean a router - but the sentence no longer derives the reason from
            the absence, because the next null with a different cause would
            inherit the explanation. */}
        {unpriced && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            The registry holds this model but no rate for it. On this feed that
            is what a router looks like — it dispatches to other models and you
            are billed at whichever it picks. Either way it is not free.
          </p>
        )}

        {s.price_cached_read != null && !unpriced && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            Cached input reads at {fmtPrice(s.price_cached_read)} per Mtok
            {s.price_in > 0 && ` — ${Math.round((1 - s.price_cached_read / s.price_in) * 100)}% off the input rate.`}
          </p>
        )}

        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          {features.map(([label, v]) => (
            // Three states, not two. An unpublished flag is not a "no" —
            // reading absent capability data as false is exactly what took a
            // candidate list from 11 models to 1 once already.
            <Badge key={label} tone={v === true ? 'pass' : v === false ? 'mute' : 'warn'}>
              {v === true ? label : v === false ? `no ${label.toLowerCase()}` : `${label.toLowerCase()}: unstated`}
            </Badge>
          ))}
        </div>

        {s.advertised_context != null && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            {fmtInt(s.advertised_context)} tokens is the <em>advertised</em> window.
            The board ranks on the window engineers report actually working, which
            is a different number and is not yet measured for this model.
          </p>
        )}
      </div>
    </Reveal>
  )
}




