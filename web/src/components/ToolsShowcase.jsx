import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listRegistry, fetchAll, fmtPrice, fmtTokens } from '../api'
import { useInView } from './ui'

/**
 * THE TOOLS AS MICRO-APPS (2026-10-15), for the landing in place of "Browse AI
 * models by job, capability or metric" (that section opened the Board, which
 * is not published). Three tabs, one per tool on /tools; the active one plays
 * a short preview of the tool at work in a small window, and the window opens
 * the tool. The tabs turn every few seconds while on screen.
 *
 * WHAT IS REAL AND WHAT IS A SAMPLE:
 *   - Model specs finder and Token counter read the live registry (`/models`):
 *     the counts after each filter, the rows, and each model's input rate are
 *     what the tools themselves would show. Nothing is drawn until it is read.
 *   - Best AI model picker shows the top three for coding agents from
 *     `/reviews` as of 12 Oct (the team's 2026-10-15 database), fixed so the
 *     preview always plays the same; it says the date on its face.
 *   - The token figure in the counter preview is an estimate (about four
 *     characters a token) and says "≈"; the tool counts with o200k exactly.
 */

const TURN_MS = 6000
const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** 0, 1, 2, … one step every `ms`, up to `last`; at once with reduced motion. */
function useSteps(last, ms) {
  const [step, setStep] = useState(() => (reduced() ? last : 0))
  useEffect(() => {
    if (step >= last) return undefined
    const t = setTimeout(() => setStep((s) => s + 1), ms)
    return () => clearTimeout(t)
  }, [step, last, ms])
  return step
}

/** The text typed out a character at a time. */
function useTyped(text, ms = 38, startAfter = 300) {
  const [n, setN] = useState(() => (reduced() ? text.length : 0))
  useEffect(() => {
    if (n >= text.length) return undefined
    const t = setTimeout(() => setN((x) => x + 1), n === 0 ? startAfter : ms)
    return () => clearTimeout(t)
  }, [n, text, ms, startAfter])
  return [text.slice(0, n), n >= text.length]
}

/* ------------------------------------------------------------ the picker */

// The picker's own flow, played out: "Search by" Jobs, type, choose the
// suggestion, and the models engineers reported working arrive - the three
// with the most people on coding agents in `/reviews` as of 12 Oct.
const PICKS = [
  { name: 'DeepSeek V4 Flash', by: 'DeepSeek', people: 13, pos: 15, neg: 0 },
  { name: 'GPT-6 Astra', by: 'OpenAI', people: 10, pos: 8, neg: 1 },
  { name: 'Claude Fable 5.1', by: 'Anthropic', people: 9, pos: 8, neg: 2 },
]
const SEARCH_BY = ['Jobs', 'Capabilities', 'AI models']
// real job names on Reports that start with what is typed
const SUGGEST = ['Coding agents', 'Code review', 'Code refactoring']
const TYPED = 'cod'

/** The stage reached: each entry is how long to wait before the next. */
function useTimeline(waits, startAt = 0) {
  const [stage, setStage] = useState(() => (reduced() ? waits.length : startAt))
  useEffect(() => {
    if (stage >= waits.length || waits[stage] == null) return undefined
    const t = setTimeout(() => setStage((s) => s + 1), waits[stage])
    return () => clearTimeout(t)
  }, [stage, waits])
  return [stage, setStage]
}

/** A number counting up to `to` once `on`. */
function useCount(to, on, ms = 900) {
  const [n, setN] = useState(() => (reduced() ? to : 0))
  useEffect(() => {
    if (!on || reduced()) return undefined
    let raf = 0
    const t0 = performance.now()
    const tick = (t) => {
      const k = Math.min(1, (t - t0) / ms)
      setN(Math.round(to * (1 - (1 - k) ** 3)))
      if (k < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to, on, ms])
  return n
}

// 0 idle · 1 "Jobs" pressed · 2 typing · 3 suggestions open · 4 choice moves
// to "Coding agent" pressed · 5 chosen · 6 results · 7 top pick
const PICK_WAITS = [700, 500, null, 700, 450, 450, 1500]

function PickRing({ p, on, i }) {
  const people = useCount(p.people, on, 900 + i * 150)
  const C = 2 * Math.PI * 17
  const total = p.pos + p.neg
  const pos = on ? (C * p.pos) / total : 0
  const neg = on ? (C * p.neg) / total : 0
  return (
    <span className="ts-ring">
      <svg viewBox="0 0 44 44" aria-hidden="true">
        <circle cx="22" cy="22" r="17" className="ts-ring-bg" />
        <circle cx="22" cy="22" r="17" className="ts-ring-pos" strokeDasharray={`${Math.max(0, pos - 2)} ${C}`}
                style={{ transitionDelay: `${i * 150}ms` }} />
        <circle cx="22" cy="22" r="17" className="ts-ring-neg" strokeDasharray={`${Math.max(0, neg - 2)} ${C}`}
                strokeDashoffset={-pos} style={{ transitionDelay: `${i * 150}ms` }} />
      </svg>
      <b className="tnum">{people}<small>people</small></b>
    </span>
  )
}

function PickerPreview() {
  const [stage, setStage] = useTimeline(PICK_WAITS)
  const [typed, done] = useTyped(stage >= 2 ? TYPED : '', 110, 120)
  useEffect(() => { if (stage === 2 && done && typed) setStage(3) }, [stage, done, typed, setStage])
  const chosen = stage >= 5
  const results = stage >= 6
  return (
    <div className="ts-app ts-pk">
      <div className="ts-pk-by">
        <span className="ts-pk-lab">Search by:</span>
        {SEARCH_BY.map((t, i) => (
          <span key={t} className={`ts-pk-type${i === 0 && stage >= 1 ? ' ts-on' : ''}${i === 0 && stage === 1 ? ' ts-press' : ''}`}>
            {t}{i === 0 && chosen && <span className="ts-pk-tick">✓</span>}
          </span>
        ))}
      </div>
      <div className="ts-pk-combo">
        <div className={`ts-search${stage >= 1 && !chosen ? ' ts-focus' : ''}`}>
          <span className="ts-ico" aria-hidden="true">⌕</span>
          {chosen
            ? <span className="ts-pk-token">Job: Coding agents <span aria-hidden="true">×</span></span>
            : <>
                {typed ? <span>{typed}</span> : <span className="ts-ph">{stage >= 1 ? 'Type a job…' : 'Pick a job, capability or model'}</span>}
                {stage >= 1 && <span className="ts-caret" aria-hidden="true" />}
              </>}
          {chosen && <span className="ts-pk-go">Find models</span>}
        </div>
        {stage >= 3 && !chosen && (
          <ul className="ts-pk-menu">
            {SUGGEST.map((s, i) => (
              <li key={s} className={`${i === 0 && stage >= 3 ? 'ts-act' : ''}${i === 0 && stage === 4 ? ' ts-press' : ''}`}>
                <span><mark>{s.slice(0, 3)}</mark>{s.slice(3)}</span><span className="ts-pk-kind">job</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className={`ts-pk-head${results ? ' ts-in' : ''}`}>
        <span><b>Most people</b> reported working for coding agents</span>
        <span className="ts-note">as of 12 Oct</span>
      </div>
      <div className="ts-pk-cards">
        {PICKS.map((p, i) => (
          <div key={p.name} className={`ts-pk-card${results ? ' ts-in' : ''}${i === 0 && stage >= 7 ? ' ts-top' : ''}`} style={{ '--i': i }}>
            {i === 0 && <span className="ts-pk-badge">Top pick</span>}
            <PickRing p={p} on={results} i={i} />
            <span className="ts-pk-name">{p.name}</span>
            <span className="ts-pk-by2">{p.by}</span>
            <span className="ts-pk-split tnum"><b>{p.pos}</b> working · <i>{p.neg}</i> not</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------- the specs finder */

const FILTERS = [
  { label: 'Context ≥ 1M', test: (m) => (m.advertised_context || 0) >= 1_000_000 },
  { label: 'Input ≤ $1 / M', test: (m) => m.price_in != null && m.price_in <= 1 },
  { label: 'Tool calling', test: (m) => m.supports_tools === true },
]

function SpecsPreview({ models }) {
  const step = useSteps(FILTERS.length, 1100)
  const match = useMemo(() => models.filter((m) => FILTERS.slice(0, step).every((f) => f.test(m))), [models, step])
  // one row per provider, so the four shown are not four versions of one model
  const rows = useMemo(() => {
    const seen = new Set()
    return [...match].sort((a, b) => (b.advertised_context || 0) - (a.advertised_context || 0))
      .filter((m) => !seen.has(m.provider) && seen.add(m.provider)).slice(0, 4)
  }, [match])
  return (
    <div className="ts-app">
      <div className="ts-chips">
        {FILTERS.map((f, i) => <span key={f.label} className={`ts-chip ts-chip-spec${step > i ? ' ts-in' : ''}`}>✓ {f.label}</span>)}
      </div>
      <div className="ts-tally"><b className="tnum" key={match.length}>{match.length}</b> of {models.length} models match</div>
      <table className="ts-table">
        <thead><tr><th>Model</th><th>Context</th><th>Input / M</th></tr></thead>
        <tbody key={step}>
          {rows.map((m, i) => (
            <tr key={m.model_version_id} style={{ '--i': i }}>
              <td>{m.display_name.split(': ').slice(1).join(': ') || m.display_name}</td>
              <td className="tnum">{fmtTokens(m.advertised_context)}</td>
              <td className="tnum">{fmtPrice(m.price_in)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ------------------------------------------------------- the token counter */

const PROMPT = 'Summarise this support ticket in three bullet points and suggest a reply.'
const CALLS = 1000
const PRICED = ['openai/gpt-6-astra', 'anthropic/claude-opus-5', 'google/gemini-3.8-flash', 'deepseek/deepseek-v4-flash']
// a pasted ticket under the instruction, so the count is a realistic prompt's
const TICKET_TOKENS = 1180

function TokenPreview({ models }) {
  const [typed, done] = useTyped(PROMPT, 26, 200)
  const tokens = Math.ceil(typed.length / 4) + (typed.length ? TICKET_TOKENS : 0)
  const step = useSteps(done ? 1 : 0, 300)
  const priced = PRICED.map((id) => models.find((m) => m.canonical_id === id)).filter((m) => m && m.price_in != null)
  const fullTokens = Math.ceil(PROMPT.length / 4) + TICKET_TOKENS
  const cost = (m) => (m.price_in * fullTokens * CALLS) / 1_000_000
  const max = Math.max(...priced.map(cost), 0.0001)
  return (
    <div className="ts-app">
      <div className="ts-text">
        <span className="ts-attach">📎 ticket-4182.txt</span>
        {typed}<span className={`ts-caret${done ? ' ts-caret-off' : ''}`} aria-hidden="true" />
      </div>
      <div className="ts-tally"><b className="tnum">≈ {tokens.toLocaleString()}</b> tokens · input cost for {CALLS.toLocaleString()} calls</div>
      <ul className="ts-bars">
        {priced.map((m, i) => (
          <li key={m.canonical_id} className={step ? 'ts-in' : ''} style={{ '--i': i }}>
            <span className="ts-name">{m.display_name.split(': ').slice(1).join(': ')}</span>
            <span className="ts-bar"><span style={{ '--w': `${Math.max(1.5, (100 * cost(m)) / max)}%` }} /></span>
            <span className="ts-count tnum">${cost(m) < 0.1 ? cost(m).toFixed(3) : cost(m).toFixed(2)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ------------------------------------------------------------- the frame */

const TOOLS = [
  { key: 'picker', to: '/best-ai-model/coding-agent', path: '/best-ai-model', icon: '◎', name: 'Best AI model picker',
    line: 'Type a job, see which models engineers reported working.', cta: 'Open the picker', App: PickerPreview, live: false, ms: 9000 },
  { key: 'specs', to: '/ai-model-pricing', path: '/ai-model-pricing', icon: '▤', name: 'AI model pricing & specs table',
    line: 'Tick what you need: context, price, tools. Watch the list narrow.', cta: 'Open the pricing & specs table', App: SpecsPreview, live: true },
  { key: 'tokens', to: '/token-counter', path: '/token-counter', icon: '#', name: 'LLM cost calculator',
    line: 'Paste a prompt, see what it costs on each model.', cta: 'Open token counter', App: TokenPreview, live: true },
]

export default function ToolsShowcase() {
  const [at, setAt] = useState(0)
  const [models, setModels] = useState(null)
  useEffect(() => {
    let alive = true
    fetchAll((l, o) => listRegistry(l, o)).then((d) => alive && setModels(d.models || [])).catch(() => alive && setModels([]))
    return () => { alive = false }
  }, [])
  // it turns only while on screen, and a preview starts when it comes into
  // view rather than playing out unseen (components/ui.jsx: useInView)
  const [el, setEl] = useState(null)
  const inView = useInView(el)
  useEffect(() => {
    if (!inView || reduced()) return undefined
    const t = setTimeout(() => setAt((i) => (i + 1) % TOOLS.length), TOOLS[at].ms || TURN_MS)
    return () => clearTimeout(t)
  }, [at, inView])

  const tool = TOOLS[at]
  const ready = !tool.live || (models && models.length > 0)
  return (
    <div className="ts" ref={setEl}>
      <div className="ts-tabs" role="tablist" aria-label="Tools">
        {TOOLS.map((t, i) => (
          <button key={t.key} type="button" role="tab" aria-selected={i === at}
                  className={`ts-tab${i === at ? ' ts-tab-on' : ''}`} onClick={() => setAt(i)}>
            <span className="ts-tab-ico" aria-hidden="true">{t.icon}</span>
            <span className="ts-tab-text">
              <b>{t.name}</b>
              <span>{t.line}</span>
            </span>
            {i === at && <span className="ts-progress" key={`p${at}`} style={{ '--ms': `${t.ms || TURN_MS}ms` }} aria-hidden="true" />}
          </button>
        ))}
      </div>
      <Link to={tool.to} className="ts-window" aria-label={`${tool.cta}: ${tool.name}`}>
        <div className="ts-bar-top" aria-hidden="true">
          <i /><i /><i />
          <span className="ts-url">{tool.path}</span>
        </div>
        <div className="ts-body" key={`${tool.key}${inView ? '' : '-off'}`}>
          {ready && inView ? <tool.App models={models || []} /> : <div className="ts-wait" aria-hidden="true" />}
        </div>
        <div className="ts-cta">{tool.cta} <span aria-hidden="true">→</span></div>
      </Link>
    </div>
  )
}
