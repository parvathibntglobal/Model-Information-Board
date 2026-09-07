import { useEffect, useState } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { modelPage, listModels, fetchAll, capLabel, fmtPrice, fmtTokens, fmtInt, BoardUnreadable } from '../api'
import FetchPanel from '../components/FetchPanel'
import { Badge, Notice, Reveal, Stat, Unreadable } from '../components/ui'
import { IconAlert, IconArrow, IconExternal } from '../components/Icons'

const STATE = {
  published:    { tone: 'pass', label: 'published' },
  insufficient: { tone: 'warn', label: 'below the gate' },
  unreported:   { tone: 'mute', label: 'nobody has discussed this' },
}

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

      {spec && <SpecPanel s={spec} />}

      <FetchPanel modelVersionId={id} onDone={() => modelPage(id).then(setPage).catch(() => {})} />

      {page && <ReportedStrip page={page} focus={state?.focus} />}

      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!page && !err && !unreadable && <div className="skel" style={{ height: 280 }} />}

      {page && (
        <>
          {/* #33 Q2 — the THIRD silence, rendered distinctly. `tracked: false`
              means we have never swept this model, so the empty capabilities are
              "we have not looked", not "nobody reported problems". Rule 4 says
              those must not look the same, so this is a distinct warn banner
              rather than just a line in the summary. It is also the only silence
              a reader can act on — they can ask for the model to be tracked. */}
          {page.tracked === false && (
            <div className="notice" style={{ borderColor: 'var(--warn)', background: 'var(--warn-dim, rgba(224,175,104,.1))' }}>
              <IconAlert style={{ flex: 'none', marginTop: 2, color: 'var(--warn)' }} />
              <div>
                <strong style={{ color: 'var(--text)' }}>Not tracked yet.</strong>{' '}
                This model has never been swept for evidence — nobody has looked at
                it. The capabilities below are empty because <em>we have not asked</em>,
                not because engineers reported no problems. That is different from a
                tracked model with no evidence, and you can change it by asking for
                this model to be tracked.
              </div>
            </div>
          )}

          <Notice>{page.summary}</Notice>

          {page.unbound_phrases.length > 0 && (
            <div className="notice" style={{ borderColor: 'var(--fail)', background: 'var(--fail-dim)' }}>
              <IconAlert style={{ flex: 'none', marginTop: 2, color: 'var(--fail)' }} />
              <div>
                <strong style={{ color: 'var(--text)' }}>Phrases with no evidence behind them</strong>
                <p style={{ marginTop: 4 }}>
                  {page.unbound_phrases.join(', ')}
                </p>
                <p style={{ marginTop: 6 }}>
                  These are <strong>not rendered below</strong>. A published phrase with no
                  quote ids is an unfalsifiable claim, and showing it anyway would make a
                  backend defect permanent.
                </p>
              </div>
            </div>
          )}

          <Reveal>
            <CapabilitiesSection page={page} focus={state?.focus} />
          </Reveal>
        </>
      )}
    </div>
  )
}

/**
 * Capabilities, evidenced first. The undiscussed ones are COLLAPSED, not
 * dropped — hiding them would erase the board's core distinction, because a
 * capability engineers tested and found fine and one nobody ever mentioned
 * would then look identical (rule 4), and for a silent-failure capability that
 * blank reads as "safe" when it means "unknown".
 *
 * The count is framed as "tracked", never as a fixed universe: the capability
 * taxonomy grows as new ones are found in the evidence, so the twelve here are
 * what we track TODAY, not all there are. Presenting them as the denominator
 * would be the rule-7 mistake this framing exists to avoid.
 */
function CapabilitiesSection({ page, focus }) {
  const visible = page.capabilities.filter((c) => !page.unbound_phrases.includes(c.key))
  const evidenced = visible.filter((c) => c.state !== 'unreported')
  const undiscussed = visible.filter((c) => c.state === 'unreported')

  return (
    <section className="card card-flush">
      <div className="card-head">
        <span className="label">What engineers have reported</span>
        <span className="label">{evidenced.length} of {visible.length} tracked capabilities</span>
      </div>
      <div className="card-body stack stack-3">
        {evidenced.length === 0 && (
          <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
            No capability has evidence yet — nobody has reported on this model’s behaviour.
            That is an absence of reports, not a clean bill of health.
          </p>
        )}
        {evidenced.map((c) => (
          <CapRow key={c.key} c={c} page={page} focus={focus} />
        ))}

        {undiscussed.length > 0 && (
          <details>
            <summary className="label" style={{ cursor: 'pointer' }}>
              {undiscussed.length} tracked capabilit{undiscussed.length === 1 ? 'y has' : 'ies have'}{' '}
              no evidence yet — show {undiscussed.length === 1 ? 'it' : 'them'}
            </summary>
            <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: '8px 0 10px' }}>
              These are the capabilities we track <em>today</em>, not all there are — the
              taxonomy grows as new ones are found in the evidence. “Nobody has discussed
              this” is an absence of reports; for a silent-failure capability it is not
              reassurance, because a failure there produces no complaint to find.
            </p>
            <div className="stack stack-3">
              {undiscussed.map((c) => (
                <CapRow key={c.key} c={c} page={page} focus={focus} />
              ))}
            </div>
          </details>
        )}
      </div>
    </section>
  )
}

/** One capability row — the same card whether it is evidenced or undiscussed. */
function CapRow({ c, page, focus }) {
  const st = STATE[c.state] || STATE.unreported
  return (
    <div id={`cap-${c.key}`} className={`caprow${c.key === focus ? ' caprow-focus' : ''}`}>
      <div className="stack" style={{ gap: 5 }}>
        <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
          <strong style={{ fontSize: 'var(--fs-sm)' }}>{capLabel(c.key)}</strong>
          <Badge tone={st.tone}>{st.label}</Badge>
          {c.needs_positive_consensus && <Badge tone="warn">needs positive consensus</Badge>}
        </div>
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{c.headline}</span>

        {c.conditions.map((s) => (
          <div key={s.bucket} className="slice">
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{s.bucket}</span>
            <span style={{ fontSize: 'var(--fs-xs)' }}>{s.phrase || s.status}</span>
            <span className="label">
              {s.voices} {s.voices === 1 ? 'voice' : 'voices'} · {s.platforms}pf
            </span>
            {s.note && <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{s.note}</span>}
            {s.quote_ids.length > 0 && (
              <div className="wrapf" style={{ marginTop: 4 }}>
                {s.quote_ids.map((qid) => (
                  <Quote key={qid} q={page.quotes[qid]} id={qid} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
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

        {unpriced && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            This model publishes no rate of its own — it routes requests to other
            models, and you are billed at whichever one it picks. That is not the
            same as free.
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

function Quote({ q, id }) {
  if (!q) return <span className="badge badge-fail">missing quote {id}</span>
  // Published content is quote + attribution + link. Some documents have no
  // URL yet, and an unattributed quote is worse than no quote.
  if (!q.permalink) {
    return <span className="badge badge-warn">quote withheld — no source link</span>
  }
  return (
    <blockquote className="mcard-quote" style={{ width: '100%' }}>
      {/* PRAISE vs CRITICISM, read straight from the claim — never inferred in
          the browser. A disputed sign (marked positive while naming a problem)
          is flagged rather than shown as a green "praise", because for this
          board a criticism read as praise is the dangerous direction. */}
      <PolarityTag polarity={q.polarity} disputed={q.sign_disputed} />
      “{q.text}”
      <cite className="mcard-cite">
        {q.platform} · {q.claimed_at} ·{' '}
        <a href={q.permalink} target="_blank" rel="noreferrer" style={{ color: 'var(--text-2)' }}>
          open <IconExternal width={10} height={10} />
        </a>
      </cite>
    </blockquote>
  )
}

function PolarityTag({ polarity, disputed }) {
  if (disputed) {
    return (
      <span
        className="badge badge-fail"
        title="Marked as praise by the extractor, but it also names a problem — the sign contradicts itself and is flagged for review rather than trusted."
        style={{ marginRight: 8 }}
      >
        sign disputed
      </span>
    )
  }
  if (polarity === 'positive') {
    return <span className="badge badge-pass" style={{ marginRight: 8 }}>praise</span>
  }
  if (polarity === 'negative') {
    return <span className="badge badge-warn" style={{ marginRight: 8 }}>criticism</span>
  }
  if (polarity === 'neutral') {
    return (
      <span
        className="badge badge-mute"
        title="A factual observation with no praise or criticism. Counts as a voice discussing this capability, but toward neither positive nor negative."
        style={{ marginRight: 8 }}
      >
        neutral
      </span>
    )
  }
  return null
}


/**
 * The capabilities somebody has actually reported on, above the full list.
 *
 * THE UNDISCUSSED CAPABILITIES STAY, COLLAPSED. FR-24 and rule 4 are why they
 * are not dropped — a page showing only what it has evidence for renders
 * "nobody has looked" and "no problems found" identically, as nothing. So the
 * evidenced ones show, and the rest sit one click away behind a disclosure in
 * CapabilitiesSection, still present and still distinct.
 *
 * This strip is a jump list over the evidenced rows, which are always rendered
 * (never inside the collapse), so every chip resolves. It earns its place
 * because even an evidenced-first list can bury the one capability the reader
 * arrived from the Evidence filter to see.
 */
function ReportedStrip({ page, focus }) {
  const reported = page.capabilities.filter(
    (c) => c.state !== 'unreported' && !page.unbound_phrases.includes(c.key)
  )

  useEffect(() => {
    if (!focus) return
    const el = document.getElementById(`cap-${focus}`)
    if (!el) return
    // rAF so the scroll happens after this render has painted, not against
    // the previous layout.
    const id = requestAnimationFrame(() =>
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    )
    return () => cancelAnimationFrame(id)
  }, [focus, page])

  if (!reported.length) {
    return (
      <Notice icon={<IconAlert />}>
        <strong style={{ color: 'var(--text)' }}>Nobody has reported on this model.</strong>{' '}
        Every capability below reads “nobody has discussed this”. That is an absence of
        evidence and not a finding about the model — it may be excellent and simply
        unwritten-about.
      </Notice>
    )
  }

  return (
    <div className="card stack stack-2">
      <span className="eyebrow">
        Reported on {reported.length} of {page.capabilities.length} capabilities
      </span>
      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
        {reported.map((c) => (
          <a
            key={c.key}
            href={`#cap-${c.key}`}
            className={`chip${c.key === focus ? ' chip-on' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              document.getElementById(`cap-${c.key}`)
                ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
            }}
          >
            {capLabel(c.key)}
            <Badge tone={c.state === 'published' ? 'pass' : 'warn'}>
              {c.state === 'published' ? 'published' : 'below the gate'}
            </Badge>
          </a>
        ))}
      </div>
      <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        These are the ones with something behind them. The{' '}
        {page.capabilities.length - reported.length} nobody has discussed are collapsed
        below, one click away — kept, not hidden, because an absence is a finding too.
      </p>
    </div>
  )
}
