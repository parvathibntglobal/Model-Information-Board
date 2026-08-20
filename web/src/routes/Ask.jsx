import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { askRequirements, askRevise, askUnderstand, capLabel, fmtInt, TIER, ERROR_COST } from '../api'
import { Badge, Notice, Reveal } from '../components/ui'
import AskLoading from '../components/AskLoading'
import { IconArrow, IconAlert, IconSearch } from '../components/Icons'

const EXAMPLES = [
  'Summarise incoming support tickets into weekly themes. 20k tickets a day, output must be valid JSON, internal tool.',
  'Classify support tickets into 12 categories, ~200k a month, machine-parsed.',
  'A customer-support agent with 12 tools and 30-turn sessions.',
  'Pull 30 fields out of scanned invoices, 5k a day. It feeds accounting.',
]

export default function Ask() {
  const [params, setParams] = useSearchParams()
  const [task, setTask] = useState(params.get('q') || '')
  const [toolCount, setToolCount] = useState('')

  // OFF BY DEFAULT, deliberately. Two reasons, and the second is not a taste
  // call: this endpoint is the only one that spends money and there is no
  // authentication, and the paragraph above the form promises the answer is
  // deterministic. Defaulting the model on would bill every visitor and make a
  // claim on the page false.
  const [useModel, setUseModel] = useState(false)
  const [downgraded, setDowngraded] = useState(null)
  const [state, setState] = useState('idle')     // idle | loading | done | error
  const [arrived, setArrived] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const pending = useRef(null)

  const run = useCallback(async (text, opts = {}) => {
    const q = text.trim()
    if (!q) return
    setState('loading'); setArrived(false); setError(null); setData(null); setDowngraded(null)
    try {
      let res = null

      if (opts.useModel) {
        // Q1: the model reads the free text and returns a profile plus every
        // field it had to GUESS. That profile is exactly what /ask/revise
        // consumes, so the model's reading flows into the same deterministic
        // half the button below already used — and `accepted_assumptions: []`
        // means every field it filled in comes back marked as a guess rather
        // than as something you said.
        try {
          const understood = await askUnderstand(q)
          const revised = await askRevise(understood.profile, [])
          res = { ...revised, llmCaveat: understood.caveat }
        } catch (err) {
          // A refusal here is NOT an outage: 503 means no spend cap is
          // configured, 429 means the cap is spent. The deterministic path
          // still works, so fall back to it — but SAY SO. Silently answering a
          // different question than the one asked is the failure this whole
          // product is about.
          if (err.status === 429 || err.status === 503 || err.name === 'BoardUnreadable') {
            setDowngraded(err.message)
          } else {
            throw err
          }
        }
      }

      if (res === null) res = await askRequirements({
        task: q,
        // '' means unset. Number('') is 0, and '0' is truthy — both traps.
        tool_count: opts.toolCount === '' ? null : Number(opts.toolCount),
      })
      // The loader always plays. It owns the timing from here — see MIN_FILL
      // in AskLoading — so a 20ms answer still fills the vessel instead of
      // flashing a bar nobody can read.
      pending.current = res
      setArrived(true)
    } catch (err) {
      setError(err.message)
      setState('error')
    }
  }, [])

  function submit(e) {
    e?.preventDefault()
    if (state === 'loading') return
    setParams(task.trim() ? { q: task.trim() } : {}, { replace: true })
    run(task, { toolCount, useModel })
  }

  function reveal() {
    setData(pending.current)
    setState('done')
  }

  const auto = useRef(false)
  useEffect(() => {
    const q = params.get('q')
    if (q && !auto.current) { auto.current = true; run(q) }
  }, [params, run])

  return (
    <div className="shell section-tight">
      <div className="stack stack-3" style={{ maxWidth: 880, margin: '0 auto' }}>
        <div className="stack stack-1">
          <span className="eyebrow">Ask the board</span>
          <h1 style={{ fontSize: 'var(--fs-display)' }}>What do you need a model to do?</h1>
        </div>

        {/* THE CLAIM HAS TO FOLLOW THE SWITCH. This paragraph promised a
            deterministic answer, and with the model reading the text that is no
            longer true of the first step — so the sentence changes rather than
            standing while being false. */}
        <p className="muted">
          {useModel
            ? <>Describe the work in your own words. A model reads it and proposes a
                profile; <strong style={{ color: 'var(--text)' }}>every field it
                fills in that you did not state comes back as an editable
                guess</strong>, and editing one re-runs the answer without the
                model, so a correction can never be overruled by it.</>
            : <>Describe the work in your own words. The answer is deterministic — the
                same task always produces the same requirements, so the reasoning is
                auditable rather than a model’s mood on the day.</>}
        </p>

        <form className="card" onSubmit={submit}>
          <textarea
            className="ask-input"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(e) }}
            placeholder="e.g. Summarise incoming support tickets into weekly themes. 20k a day, output must be valid JSON."
            aria-label="Describe your task"
          />

          <div className="ask-extra">
            <label className="field field-inline">
              <span className="field-label">Tool count</span>
              <input type="number" min="0" value={toolCount} placeholder="auto — inferred from the text"
                     onChange={(e) => setToolCount(e.target.value)} />
            </label>
            <span className="ask-hint">
              Setting this raises the tool-calling capabilities and picks the
              condition bucket to read cells at.
            </span>

            <label className="field field-inline">
              <input
                type="checkbox"
                checked={useModel}
                onChange={(e) => setUseModel(e.target.checked)}
              />
              <span className="field-label">Read my description with a model</span>
            </label>
            <span className="ask-hint">
              Off by default. This is the only part of the board that calls a
              language model, so it costs money and needs a spend cap configured
              on the server. Everything else here is ordinary code, and the
              rules-only reading is usually enough.
            </span>
          </div>

          <div className="ask-foot">
            <span className="label">⌘ + Enter to submit</span>
            <button className="btn btn-primary" type="submit" disabled={!task.trim() || state === 'loading'}>
              {state === 'loading'
                ? <><span className="spin" /> Reading…</>
                : <>Infer requirements <IconArrow width={15} height={15} /></>}
            </button>
          </div>
        </form>

        {state === 'idle' && (
          <div className="stack stack-2">
            <span className="label">Or start from one of these</span>
            <div className="grid g2">
              {EXAMPLES.map((ex) => (
                <button key={ex} type="button" className="example-btn" onClick={() => setTask(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {downgraded && (
          <Notice icon={<IconAlert />}>
            <strong style={{ color: 'var(--text)' }}>
              Answered without the model.
            </strong>{' '}
            You asked for a model reading and it was declined, so the rules-only
            path answered instead — a good answer to a slightly different
            question, which you should know about rather than infer. {downgraded}
          </Notice>
        )}

        {state === 'error' && (
          <Notice icon={<IconAlert />}>
            <strong style={{ color: 'var(--text)' }}>Could not reach the board.</strong> {error}
          </Notice>
        )}
      </div>

      {state === 'loading' && <AskLoading complete={arrived} onFinish={reveal} />}
      {state === 'done' && data && <Result data={data} task={task} />}
    </div>
  )
}

/* ------------------------------------------------------------------ result */

function Result({ data, task }) {
  const [live, setLive] = useState(data)
  const [accepted, setAccepted] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => { setLive(data); setAccepted([]) }, [data])

  const req = live.requirement
  const tier = TIER[req.complexity_tier] || {}
  const cost = ERROR_COST[req.error_cost] || {}

  /** Editing an assumption re-runs Q3 deterministically — no model involved. */
  async function edit(field, value) {
    setBusy(true)
    try {
      const profile = {
        raw_text: task,
        ...Object.fromEntries(req.assumptions.map((a) => [a.field, a.value])),
        tool_count: req.hard.tool_count,
        regions: req.hard.regions,
        [field]: value,
      }
      const next = await askRevise(profile, accepted)
      setLive({ requirement: next.requirement, guard: next.guard, note: next.note })
    } catch { /* leave the previous answer standing */ }
    setBusy(false)
  }

  return (
    <div style={{ marginTop: 'var(--s6)' }} className="stack stack-4">
      {/* Rendered rather than carried. Passing this through `run()` and never
          showing it would make it one more thing in this repo that is built,
          correct and unreachable - and it is the field that says which parts of
          the answer a model supplied rather than you. */}
      {live.llmCaveat && (
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>A model read your description.</strong>{' '}
          {live.llmCaveat}
        </Notice>
      )}

      {req.assumptions.length > 0 && (
        <div className="stack stack-2">
          <span className="label">
            What we assumed — every guess is editable, and editing re-runs the answer
          </span>
          <div className="wrapf">
            {req.assumptions.map((a) => (
              <AssumptionChip
                key={a.field}
                a={a}
                busy={busy}
                onCommit={(v) => edit(a.field, v)}
                onAccept={() => setAccepted((s) => [...new Set([...s, a.field])])}
                accepted={accepted.includes(a.field)}
              />
            ))}
          </div>
        </div>
      )}

      <Reveal>
        <div className="grid g3">
          <div className="card stack stack-1">
            <span className="label">Complexity</span>
            <span style={{ fontSize: '1.25rem', letterSpacing: '-.02em' }}>
              <span className="mono">{'●'.repeat(req.complexity_tier)}{'○'.repeat(5 - req.complexity_tier)}</span>
              {' '}{tier.label}
            </span>
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{tier.note}</span>
          </div>
          <div className="card stack stack-1">
            <span className="label">Error cost</span>
            <span><Badge tone={cost.tone || 'mute'}>{req.error_cost}</Badge></span>
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{cost.note}</span>
          </div>
          <div className="card stack stack-1">
            <span className="label">Cost dominates</span>
            <span style={{ fontSize: '1.25rem', letterSpacing: '-.02em' }}>
              {req.cost_dominates ? 'Yes' : 'No'}
            </span>
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
              {req.cost_dominates ? 'not interactive — price is the tiebreak' : 'latency is a real constraint'}
            </span>
          </div>
        </div>
      </Reveal>

      {req.capabilities.length > 0 && (
        <Notice icon={<IconSearch />}>{live.note}</Notice>
      )}

      <Reveal>
        <section className="card card-flush">
          <div className="card-head">
            <span className="label">What this role is gated on</span>
            <span className="label">{req.capabilities.length} capabilities</span>
          </div>
          <div className="card-body stack stack-3">
            {req.capabilities.length === 0 && <NothingRecognised />}
            {req.capabilities.map((c) => (
              <div key={c.key + c.condition_bucket} className="caprow">
                <div className="stack" style={{ gap: 4 }}>
                  <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: 'var(--fs-sm)' }}>{capLabel(c.key)}</strong>
                    <Badge tone={c.failure_mode === 'silent' ? 'warn' : 'info'}>
                      {c.failure_mode} failure
                    </Badge>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
                      {c.condition_bucket}
                    </span>
                  </div>
                  <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                    <span className="mono">{c.key}</span> · raised by “{c.triggered_by}”
                  </span>
                </div>
                {c.failure_mode === 'silent' && (
                  <span className="capnote">
                    Needs positive consensus — you would not find out you were wrong,
                    so an absence of complaints is not evidence.
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      </Reveal>

      <div className="grid g2">
        <Reveal>
          <div className="card stack stack-2" style={{ height: '100%' }}>
            <span className="label">Hard constraints — binary filters, no partial credit</span>
            <dl className="kv">
              <dt>Tools</dt>
              <dd>{req.hard.needs_tools ? `required · ${req.hard.tool_count ?? '?'} tools` : 'not required'}</dd>
              <dt>Structured</dt>
              <dd>{req.hard.needs_structured_output ? 'required' : 'not required'}</dd>
              <dt>Vision</dt>
              <dd>{req.hard.needs_vision ? 'required' : 'not required'}</dd>
              <dt>Min context</dt>
              <dd>
                {req.hard.min_context_tokens ? `${fmtInt(req.hard.min_context_tokens)} tokens` : 'no floor'}
                {req.hard.min_context_tokens
                  ? <span className="dim"> · matched against reported effective context, never advertised</span>
                  : null}
              </dd>
              <dt>Latency</dt>
              <dd>{req.hard.max_latency_ms ? `${fmtInt(req.hard.max_latency_ms)} ms` : 'unconstrained'}</dd>
              <dt>Regions</dt>
              <dd>{req.hard.regions.length ? req.hard.regions.join(', ') : 'any'}</dd>
            </dl>
          </div>
        </Reveal>

        <Reveal delay={90}>
          <div className="card stack stack-2" style={{ height: '100%' }}>
            <span className="label">Requirements you do not have</span>
            <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
              Every one of these widens the cheap end of the field. Carrying a
              constraint you do not need is the most common way to overpay.
            </p>
            <ul className="stack stack-1" style={{ marginTop: 4 }}>
              {req.dropped_constraints.length === 0 && (
                <li className="dim" style={{ fontSize: 'var(--fs-sm)' }}>None — every constraint applies.</li>
              )}
              {req.dropped_constraints.map((d) => (
                <li key={d} className="dropped">{d}</li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>

      {live.guard && (
        <Reveal>
          <div className="notice" style={{ borderColor: 'var(--warn)', background: 'var(--warn-dim)' }}>
            <IconAlert style={{ flex: 'none', marginTop: 2, color: 'var(--warn)' }} />
            <div>
              <strong style={{ color: 'var(--text)' }}>Guard</strong>
              <p style={{ marginTop: 4 }}>{live.guard}</p>
            </div>
          </div>
        </Reveal>
      )}

      <Notice icon={<IconSearch />}>
        <strong style={{ color: 'var(--text)' }}>This is the whole answer today, and it is not an error.</strong>{' '}
        The requirement profile above is what the board can say with certainty. Naming
        specific models needs published cells, and there are none yet — the registry
        carries 11 models but no claim has been extracted, so every capability on every
        model reads “nobody has discussed this”. Rather than invent candidates, the board
        stops here.
      </Notice>
    </div>
  )
}

/**
 * Zero capabilities is a real answer, and an empty box is not a way to give it.
 * Q3 matches verbs, not topics: "coding" and "programming" raise nothing, while
 * "write code" and "refactor" do. Say so, and say what would work.
 */
function NothingRecognised() {
  return (
    <div className="stack stack-2">
      <p style={{ fontSize: 'var(--fs-sm)' }}>
        <strong>Nothing in that description named a job.</strong> Requirements are
        matched from the <em>work</em> — the verb — not from the topic. “A good model
        for coding” names a subject; “write code from a spec” names a task, and only
        the second can be gated on anything.
      </p>
      <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Everything below still applies: the constraints, the tier and the dropped
        requirements come from the shape of the task, not from its capabilities.
      </p>
      <div className="wrapf" style={{ marginTop: 4 }}>
        {[
          'summarise / condense',
          'extract / parse',
          'classify / route / label',
          'write code · generate the code',
          'edit / refactor / patch',
          'plan / orchestrate / decide',
          '12 tools · calls the API',
          'must return JSON',
          'reads the whole document',
        ].map((t) => <span key={t} className="chip">{t}</span>)}
      </div>
      <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Backend gap, reported: the bare nouns <span className="mono">coding</span> and{' '}
        <span className="mono">programming</span> match no trigger, so the most natural
        phrasing of a coding task raises nothing.
      </p>
    </div>
  )
}

function AssumptionChip({ a, busy, onCommit, onAccept, accepted }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(a.value)

  useEffect(() => { setVal(a.value) }, [a.value])

  if (editing) {
    return (
      <span className="chip chip-edit">
        <span className="dim">{a.field}</span>
        <input
          autoFocus
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { setEditing(false); onCommit(isNaN(Number(val)) ? val : Number(val)) }
            if (e.key === 'Escape') { setEditing(false); setVal(a.value) }
          }}
          onBlur={() => { setEditing(false); setVal(a.value) }}
        />
      </span>
    )
  }

  return (
    <span className={`chip${accepted ? ' chip-ok' : ''}`} title={a.why}>
      <span className="dim">{a.field}:</span>
      <strong style={{ color: 'var(--text)' }}>{String(a.value)}</strong>
      <button className="x" disabled={busy} onClick={() => setEditing(true)}>edit</button>
      {!accepted && <button className="x" disabled={busy} onClick={onAccept}>ok</button>}
    </span>
  )
}
