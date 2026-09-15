import { useEffect, useState } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { modelPage, listModels, fetchAll, BoardUnreadable } from '../api'
import FetchPanel from '../components/FetchPanel'
import ModelEvidence from '../components/ModelEvidence'
import { Notice, Unreadable } from '../components/ui'
import { IconAlert, IconArrow } from '../components/Icons'

export default function ModelDetail() {
  // `/models/*` rather than `/models/:id`, because an id can contain a
  // slash — google/gemini-2.5-flash is one path segment to us, two to the router.
  const id = useParams()['*']
  const { state } = useLocation()
  const [page, setPage] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  // THE ROSTER ROW, NOW FOR ONE FIELD. This comment used to say "GET
  // /models/{id} still returns no display_name and no price" - half of that is
  // no longer true: it returns `display_name` fine, and `name` below prefers
  // the roster's only by accident of ordering. What it does NOT return is
  // `provider`, and with the advertised panel gone that single string is the
  // whole reason this second call exists.
  //
  // Left in rather than traded for a blank byline, and written down rather than
  // left as a call whose purpose has quietly shrunk to one field. If `provider`
  // ever joins the model payload, this effect and `fetchAll` go with it.
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
      .catch(() => {})   // additive: a missing provider must not blank the page
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
      {/* The "As advertised by the provider" panel was here: price, context
          window, max output and four capability badges, read from the roster
          row. Removed at Parvathi's request along with the price column on
          the registry list, so the two surfaces agree: this board shows what
          engineers reported, and a vendor's own spec sheet is not that.
      
          `spec` is still fetched - the heading above reads its display_name
          and provider, which are the model's identity rather than its
          advertised numbers. */}

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

      {/* THE "NOT TRACKED YET" BANNER WAS HERE, AND IT WAS SAYING SOMETHING FALSE.

          It rendered on `page.tracked === false`, which is
          `model_version.last_swept_at IS NULL` (judge/pages/model.py:175). The
          reasoning was sound — "we never asked" and "nobody answered" are
          opposite claims and rule 4 says render them differently. The INPUT was
          not: `last_swept_at` has exactly two writers, `collect/ops/sweep.py`
          and `collect/registry/openrouter.py:648`, and the Fetch button on this
          very page is neither. `/fetch/start` runs the pipeline end to end and
          never calls `mark_swept`.

          So a model could be fetched, harvested, extracted and vetted, and this
          banner would still tell the reader nobody had looked at it — directly
          above a ModelEvidence panel listing what was found. Measured on the
          shared database on 2026-09-15, of the 15 in contract/tracked_models.yaml:

              13 of 15  carried the banner
               9 of 13  had board evidence anyway
                        Claude Fable 5.1 34, MiniMax M3 29, DeepSeek V4 Pro 23,
                        GLM 5.3 10, GPT 6 Astra 9, Nano Banana 2 5, GPT-5.6 Sol 4,
                        Kimi K3 3, Grok 4.6 1

          Removed rather than re-predicated. Stamping `last_swept_at` from the
          Fetch path would make the banner true, but that is a change to what the
          column MEANS — `assert_no_sweep_without_harvest`
          (collect/registry/assertions.py:69) exists precisely to refuse a
          `last_swept_at` no sweep accounts for — and it belongs in the collect
          lane with its own review, not smuggled in behind a UI fix.

          WHAT IS LOST, STATED. A model genuinely never looked at now renders an
          empty evidence panel with no caveat. That is a real rule-4 cost. It is
          the smaller one: the banner was not silent about those models, it was
          WRONG about nine others, and a caveat that fires on the wrong rows
          teaches a reader to skip it on the right ones. `tracked` and `swept_at`
          are still on the payload (judge/app.py:1331) for whoever fixes the
          predicate. */}

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







