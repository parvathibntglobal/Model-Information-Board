import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { reportsPage, BoardUnreadable } from '../api'
import { Notice, Unreadable } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { useHead } from '../seo/head'
import { reportsIndex } from '../seo/pages'

/**
 * REPORTS (2026-10-14): the demo's Reports page (model-information-board-home-
 * demo.html) on live data. What engineers report about each AI model, by job,
 * capability and metric - COUNTED, NEVER QUOTED, and a model is shown on an
 * axis only where at least N different people reported on it.
 *
 * THE DATA IS `/reports` (judge/reports.py): the board's own counts over the
 * PUBLIC view, so a withheld source adds nothing here. No quote, link, author
 * or platform name reaches this page; it is self-contained and links nowhere
 * outside Reports.
 *
 * THE ADDRESS HOLDS THE STATE: each section is its own page (see the routes
 * above `Reports`), with `?min=3|10` and `?multi=1` for the threshold. A view
 * can be sent to somebody, and the nav's Reports menu opens each page.
 *
 * NOTHING IS A SCORE. The phrases ("Mostly working") are a fixed rule over the
 * counts (`phrase`), and the order on an axis is the board's own.
 */

const KINDS = [
  { id: 'job', tab: 'jobs', label: 'Jobs', one: 'job', short: 'job', shortPl: 'jobs' },
  { id: 'capability', tab: 'capabilities', label: 'Capabilities', one: 'capability', short: 'cap', shortPl: 'cap' },
  { id: 'metric', tab: 'metrics', label: 'Metrics', one: 'metric', short: 'metric', shortPl: 'metrics' },
]
const KIND = Object.fromEntries(KINDS.map((k) => [k.id, k]))
const MINS = [3, 5, 10]
const GROUPS = [
  { id: 'working', label: 'Reported working', colour: 'var(--pass)' },
  { id: 'neutral', label: 'Neutral reports only', colour: 'var(--neutral)' },
  { id: 'problems', label: 'Problems reported, none working', colour: 'var(--fail)' },
]
const PLACEHOLDER = { models: 'Search models', job: 'Search jobs', capability: 'Search capabilities', metric: 'Search metrics' }

function Definition({ pill, min }) {
  if (pill === 'models') {
    return <p className="rp-definition"><b>Models</b>: the AI models on our registry that engineers have reported on in real use. A model is listed once at least <b>{min} different people</b> reported on it for one job, capability or metric. Open a model to see everything it has been discussed for.</p>
  }
  if (pill === 'job') return <p className="rp-definition"><b>Jobs</b> are what people used a model for, such as coding agents or summarising documents. They are named from the reports themselves, not picked from a fixed list.</p>
  if (pill === 'capability') return <p className="rp-definition"><b>Capabilities</b> are specific abilities people reported working or failing, such as reasoning, tool use, vision or long context.</p>
  return <p className="rp-definition"><b>Metrics</b> are figures people measured themselves, such as speed, cost or benchmark results. Here we count the reports; the figures themselves are not shown on this page.</p>
}

// ── names ──────────────────────────────────────────────────────────────────
const shortName = (m) => {
  const l = m.label || m.key || ''
  return l.includes(':') ? l.split(':').slice(1).join(':').trim() : l
}
const providerOf = (m) => {
  const l = m.label || ''
  if (l.includes(':')) return l.split(':')[0]
  return m.canonical && m.canonical.includes('/') ? m.canonical.split('/')[0] : ''
}
const modelId = (m) => m.canonical || m.key
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

// ── counts → words (a fixed rule, never a score) ─────────────────────────────
function phrase(s) {
  const p = s.positive, n = s.negative
  if (!p && !n) return { t: 'No side taken', c: 'neutral' }
  if (!n) return { t: 'Reported working, no problems reported', c: 'working' }
  if (!p) return { t: 'Problems reported, none working', c: 'problems' }
  if (p >= 3 * n) return { t: 'Mostly working', c: 'working' }
  if (n >= 3 * p) return { t: 'Mostly problems', c: 'problems' }
  return { t: 'Mixed reports', c: 'mixed' }
}
const squareClass = (m) => ({ working: 'rp-c-pos', problems: 'rp-c-neg', mixed: 'rp-c-mix', neutral: 'rp-c-neu' }[phrase(m.split).c])

/** Who qualifies, and the per-model and per-axis views, at this threshold. */
function build(axes, min, multi) {
  const ok = (m) => m.voices >= min && (!multi || m.platforms >= 2)
  const models = new Map()
  const byKind = { job: [], capability: [], metric: [] }
  for (const a of axes) {
    const kept = []
    for (const m of a.models) {
      let r = models.get(m.key)
      if (!r) {
        r = { key: m.key, label: m.label, canonical: m.canonical, axes: { job: [], capability: [], metric: [] }, below: 0 }
        models.set(m.key, r)
      }
      if (ok(m)) { r.axes[a.kind].push({ axis: a, m }); kept.push(m) } else r.below += 1
    }
    if (kept.length && byKind[a.kind]) byKind[a.kind].push({ axis: a, models: kept })
  }
  const shown = [...models.values()].filter((r) => KINDS.some((k) => r.axes[k.id].length))
  for (const r of shown) {
    r.total = KINDS.reduce((n, k) => n + r.axes[k.id].length, 0)
    for (const k of KINDS) r.axes[k.id].sort((x, y) => y.m.voices - x.m.voices || y.m.reports - x.m.reports)
  }
  shown.sort((a, b) => b.total - a.total || shortName(a).localeCompare(shortName(b)))
  for (const k of KINDS) byKind[k.id].sort((a, b) => b.models.length - a.models.length || b.axis.voices - a.axis.voices)
  return { models: shown, all: models, byKind }
}

// ── pictures ────────────────────────────────────────────────────────────────
function VChart({ s }) {
  const vals = [['pos', 'positive', s.positive], ['neg', 'negative', s.negative], ['neu', 'neutral', s.neutral]]
  const nz = vals.filter((v) => v[2] > 0)
  if (nz.length === 1) {
    const [c, word, v] = nz[0]
    const col = c === 'pos' ? 'var(--pass)' : c === 'neg' ? 'var(--fail)' : 'var(--neutral)'
    return (
      <div className="rp-oneline" role="img" aria-label={`All ${v} reports ${word}`}>
        <div className="rp-line" style={{ background: col }} />
        <div className="rp-cap" style={{ color: c === 'neu' ? 'var(--text-1)' : col }}>All {plural(v, 'report')} {word}</div>
      </div>
    )
  }
  const max = Math.max(1, ...vals.map((v) => v[2]))
  return (
    <>
      <div className="rp-vchart" role="img" aria-label={`${s.positive} positive, ${s.negative} negative, ${s.neutral} neutral`}>
        {vals.map(([c, , v]) => (
          <div key={c} className={`rp-vcol rp-v-${v ? c : 'zero'}`}>
            <span className="rp-val">{v}</span>
            <span className="rp-vb" style={{ height: v ? Math.max(6, (72 * v) / max) : 2 }} />
          </div>
        ))}
      </div>
      <div className="rp-vlabels"><span>Positive</span><span>Negative</span><span>Neutral</span></div>
      {s.both > 0 && <div className="rp-both-note">{plural(s.both, 'report')} said both, counted in each bar</div>}
    </>
  )
}

function Legend() {
  return (
    <div className="rp-legend">
      <span><i className="rp-c-pos" />positive</span><span><i className="rp-c-neg" />negative</span>
      <span><i className="rp-c-neu" />neutral</span><span><i className="rp-c-both" />both</span>
    </div>
  )
}

/** The ten rules behind every number, worded as the demo words them. Shared by
 *  the "How the reports work" section and the "How we count" drawer. */
function MethodBoxes({ min, multi, withheld }) {
  const box = (no, title, body) => (
    <div className="rp-mbox"><h4><span className="rp-no">{no}</span>{title}</h4>{body}</div>
  )
  return (
    <div className="rp-mgrid2">
      {box('01', 'Who is shown', <p>A model appears on a job, capability or metric only when <b>at least {min} different people</b> reported on that model for it{multi ? <>, <b>on at least two platforms</b></> : ''}. One voice or one report is never enough. An axis is listed when at least one model qualifies.</p>)}
      {box('02', 'Voices and reports', <p>A <b>voice</b> is one distinct author; a <b>report</b> is one distinct source document. Two comments by one person are one voice. An author we cannot identify adds a report but no voice. One person on two platforms is not yet linked, so voices are an upper bound.</p>)}
      {box('03', 'Not shown is not a judgement', <p>A model or axis below the threshold has too few voices <i>yet</i>. Every page says how many were left out, so &quot;not discussed enough&quot; never reads as &quot;bad&quot;.</p>)}
      {box('04', 'Positive, negative, neutral', <><p>Each report is labelled by our classifier, and every label is tied to text that code has checked exists in the source. A report can be both positive and negative; it is counted on both sides and the page says so.</p><div style={{ marginTop: 8 }}><Legend /></div></>)}
      {box('05', 'No scores', <p>Nothing here is a score or a rating. The short phrases are built from the counts by a fixed rule: <i>working</i> when no report took the other side, <i>mostly</i> when one side has at least three times the other, <i>mixed</i> otherwise.</p>)}
      {box('06', 'How models are ranked on an axis', <p>Three groups, in this order: models with at least one report of it working, models with only neutral reports, models with problems and none working. Inside the first group, models whose reports more consistently say it worked rank higher, with more reports giving more confidence. The other groups rank by number of reports. The bars share one scale, so lengths compare across rows.</p>)}
      {box('07', 'Sources', <p>Some sources are collected for research but not shown publicly; nothing from them is counted on this page{withheld ? <> (<b>{withheld.toLocaleString()}</b> entries left out)</> : ''}. No quote, link or author is ever shown.</p>)}
      {box('08', 'Counts are floors', <p>Axes are named in an open vocabulary, so one subject can be split across two names until a person merges them. When that happens, counts can only go up.</p>)}
      {box('09', 'Specs and costs are advertised', <p>Context windows, prices and features come from our registry: what providers publish about their own models. They are not evidence and never change what these pages count. A model with no published price shows &quot;—&quot;, never $0.</p>)}
      {box('10', 'Discussions are separate', <p>Comments are readers&apos; own experiences. They appear beside the counts but are never added to them.</p>)}
    </div>
  )
}

function HowWeCount({ min, multi, withheld, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  // ON THE BODY, NOT INSIDE THE PAGE: a parent of the page creates its own
  // stacking and containing box, which put the drawer under the sticky nav and
  // let its header scroll away. A portal keeps it a true full-screen layer.
  return createPortal(
    <div className="rp rp-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="rp-drawer" role="dialog" aria-modal="true" aria-label="How we count">
        <div className="rp-dhead">
          <div><h2>How we count</h2><p>The rules behind every number on these pages.</p></div>
          <button type="button" className="rp-btn rp-close" onClick={onClose} aria-label="Close How we count">✕ Close</button>
        </div>
        <MethodBoxes min={min} multi={multi} withheld={withheld} />
      </div>
    </div>,
    document.body,
  )
}

/** A breadcrumb step: reachable by keyboard as well as by mouse. */
function Crumb({ onGo, children }) {
  return <a role="button" tabIndex={0} onClick={onGo} onKeyDown={(e) => { if (e.key === 'Enter') onGo() }}>{children}</a>
}

// ── views ───────────────────────────────────────────────────────────────────
const COMPARE_MAX = 3

/**
 * THE AI MODELS LIST, with Compare top right (2026-10-14). Compare turns the
 * cards into tick boxes; up to three can be picked, and "Compare" opens the
 * same `/compare?ids=` page the Models list opens - with the same ids
 * (`canonical`, else the internal key), so the two routes agree.
 */
function ModelsList({ v, q, open, onCompare }) {
  const [all, setAll] = useState(false)
  const [picking, setPicking] = useState(false)
  const [picked, setPicked] = useState([])
  const ql = q.toLowerCase()
  const matches = v.models.filter((r) => !ql || `${r.label} ${r.canonical || ''}`.toLowerCase().includes(ql))
  const LIMIT = 8
  const list = ql || all ? matches : matches.slice(0, LIMIT)
  const toggle = (id) => setPicked((cur) => (cur.includes(id) ? cur.filter((x) => x !== id)
    : cur.length >= COMPARE_MAX ? cur : [...cur, id]))
  const stop = () => { setPicking(false); setPicked([]) }
  return (
    <>
      <div className="rp-sec-head">
        <h2>Models</h2>
        <span className="rp-count">{matches.length === v.models.length ? v.models.length : `${matches.length} of ${v.models.length}`}</span>
        <div className="rp-tools rp-cmpbar">
          {picking ? (
            <>
              <span className="rp-hint">
                {picked.length === 0 ? `Tick 2–${COMPARE_MAX} models` : picked.length === 1 ? 'Tick one more' : `${picked.length} of ${COMPARE_MAX} picked`}
              </span>
              <button type="button" className="rp-btn" onClick={stop}>Cancel</button>
              <button type="button" className="rp-btn rp-primary" disabled={picked.length < 2}
                      onClick={() => onCompare(picked)}>
                Compare{picked.length ? ` (${picked.length})` : ''} →
              </button>
            </>
          ) : (
            <button type="button" className="rp-btn" onClick={() => setPicking(true)}
                    title={`Pick up to ${COMPARE_MAX} models to compare side by side`}>
              Compare
            </button>
          )}
        </div>
      </div>
      {list.length ? (
        <div className="rp-mgrid">
          {list.map((r) => {
            const id = modelId(r)
            const on = picked.includes(id)
            return (
              <button type="button" key={r.key}
                      className={`rp-mcard${on ? ' rp-picked' : ''}`}
                      aria-pressed={picking ? on : undefined}
                      disabled={picking && !on && picked.length >= COMPARE_MAX}
                      onClick={() => (picking ? toggle(id) : open('models', id))}>
                {picking && <span className="rp-tick" aria-hidden="true">{on ? '✓' : ''}</span>}
                <div className="rp-prov">{providerOf(r)}</div>
                <div className="rp-nm">{shortName(r)}</div>
                <div className="rp-cnt">
                  {KINDS.map((k) => { const n = r.axes[k.id].length; return n ? <span key={k.id}>{n} {n === 1 ? k.short : k.shortPl}</span> : null })}
                </div>
              </button>
            )
          })}
        </div>
      ) : <div className="rp-empty">No model matches &quot;{q}&quot;.</div>}
      {!ql && matches.length > LIMIT && (
        <div className="rp-seemore"><button type="button" className="rp-btn" onClick={() => setAll(!all)}>{all ? 'Show fewer' : `See all ${matches.length} models`}</button></div>
      )}
    </>
  )
}

function ModelView({ v, id, min, multi, open, back }) {
  const r = v.models.find((x) => modelId(x) === id || x.key === id)
  const base = r || [...v.all.values()].find((x) => modelId(x) === id || x.key === id)
  const crumbs = (
    <div className="rp-crumbs"><Crumb onGo={() => back(null)}>Models</Crumb> / <span>{base ? shortName(base) : 'Model'}</span></div>
  )
  if (!r) {
    return <>{crumbs}<div className="rp-empty">{base ? `${shortName(base)} has no job, capability or metric with ${min}+ voices${multi ? ' from 2+ platforms' : ''}. Lower the threshold to see it.` : 'There is no model at this address.'}</div></>
  }
  return (
    <>
      {crumbs}
      <div className="rp-mhead">
        <div>
          <div className="rp-prov">{providerOf(r)}</div>
          <h2>{shortName(r)}</h2>
          {r.canonical && <div className="rp-mid">{r.canonical}</div>}
        </div>
      </div>
      <div className="rp-chips">
        {KINDS.map((k) => { const n = r.axes[k.id].length; return <span key={k.id} className="rp-chip">{n} {n === 1 ? k.one : k.label.toLowerCase()}</span> })}
      </div>
      {r.below > 0 && (
        <p className="rp-below">Also discussed on {r.below} more {r.below === 1 ? 'job, capability or metric' : 'jobs, capabilities or metrics'} with fewer than {min} voices{multi ? ' or from one platform' : ''}. Not shown, and not a judgement.</p>
      )}
      {KINDS.map((k) => (
        <section key={k.id} className="rp-kind">
          <h3>{k.label} <span className="rp-n">{r.axes[k.id].length}</span></h3>
          {r.axes[k.id].length ? (
            <div className="rp-grid">
              {r.axes[k.id].map(({ axis, m }) => {
                const ph = phrase(m.split)
                return (
                  <div key={axis.slug} className="rp-tile" tabIndex={0} role="button"
                       onClick={() => open(k.tab, axis.slug)}
                       onKeyDown={(e) => { if (e.key === 'Enter') open(k.tab, axis.slug) }}>
                    <div className="rp-t-name">{axis.name}</div>
                    <div className={`rp-phrase rp-ph-${ph.c}`}>{ph.t}</div>
                    <VChart s={m.split} />
                    <div className="rp-nums">
                      <span><b>{m.voices}</b> voices</span><span><b>{m.reports}</b> reports</span>
                      <span><b>{m.platforms}</b> platform{m.platforms === 1 ? '' : 's'}</span>
                      {k.id === 'metric' && m.figures > 0 && <span><b>{m.figures}</b> figures</span>}
                    </div>
                    {m.newest && <div className="rp-date">Newest report {m.newest}</div>}
                  </div>
                )
              })}
            </div>
          ) : <div className="rp-empty">No {k.one} has {min}+ voices for this model yet.</div>}
        </section>
      ))}
    </>
  )
}

function AxisList({ v, kind, q, open }) {
  const k = KIND[kind]
  const ql = q.toLowerCase()
  const all = v.byKind[k.id]
  const items = all.filter((x) => !ql || `${x.axis.name} ${x.axis.slug}`.toLowerCase().includes(ql))
  return (
    <>
      <div className="rp-sec-head">
        <h2>{k.label}</h2>
        <span className="rp-count">{items.length === all.length ? items.length : `${items.length} of ${all.length}`}</span>
        <div className="rp-tools rp-legend">One square per model:
          <span><i className="rp-c-pos" />working</span><span><i className="rp-c-mix" />mixed</span>
          <span><i className="rp-c-neg" />problems</span><span><i className="rp-c-neu" />neutral</span>
        </div>
      </div>
      {items.length ? (
        <div className="rp-axis-grid">
          {items.map((x) => (
            <button type="button" key={x.axis.slug} className="rp-acard" onClick={() => open(k.tab, x.axis.slug)}>
              <div className="rp-kind-label">{k.one}</div>
              <div className="rp-t-name">{x.axis.name}</div>
              <div className="rp-cnt">{plural(x.models.length, 'model')} <span className="rp-dim">· {x.axis.voices} voices · {x.axis.reports} reports</span></div>
              <div className="rp-mini">{x.models.map((m) => <i key={m.key} className={squareClass(m)} title={shortName(m)} />)}</div>
            </button>
          ))}
        </div>
      ) : <div className="rp-empty">No {k.one} matches &quot;{q}&quot;.</div>}
    </>
  )
}

function AxisView({ v, axes, kind, slug, min, multi, open, back }) {
  const k = KIND[kind]
  const hit = v.byKind[k.id].find((x) => x.axis.slug === slug)
  const a = hit ? hit.axis : axes.find((x) => x.kind === k.id && x.slug === slug)
  const crumbs = (
    <div className="rp-crumbs"><Crumb onGo={() => back(null)}>Models</Crumb> / <Crumb onGo={() => back(k.tab)}>{k.label}</Crumb> / <span>{a ? a.name : slug}</span></div>
  )
  if (!a) return <>{crumbs}<div className="rp-empty">There is no {k.one} at this address.</div></>
  const models = hit ? hit.models : []
  const hidden = a.models.length - models.length
  const scale = Math.max(1, ...models.map((m) => Math.max(m.split.positive, m.split.negative)))
  let rank = 0
  const row = (m) => {
    rank += 1
    const ph = phrase(m.split), s = m.split
    const wp = (40 * s.positive) / scale, wn = (40 * s.negative) / scale
    return (
      <div key={m.key} className="rp-rrow" role="button" tabIndex={0}
           onClick={() => open('models', modelId(m))}
           onKeyDown={(e) => { if (e.key === 'Enter') open('models', modelId(m)) }}>
        <span className="rp-rk">{String(rank).padStart(2, '0')}</span>
        <span className="rp-nm"><span className="rp-prov">{providerOf(m)}</span>{shortName(m)}</span>
        <span className="rp-div" role="img" aria-label={`${s.positive} positive, ${s.negative} negative`}>
          <span className="rp-mid" />
          {s.negative > 0 && <span className="rp-neg" style={{ width: `${wn}%` }} />}
          {s.positive > 0 && <span className="rp-pos" style={{ width: `${wp}%` }} />}
          <span className="rp-lab rp-l" style={{ right: `calc(50% + ${wn}% + 6px)` }}>{s.negative}</span>
          <span className="rp-lab rp-r" style={{ left: `calc(50% + ${wp}% + 6px)` }}>{s.positive}</span>
        </span>
        <span className="rp-side">
          <span className="rp-neu">{s.neutral} neutral</span>{s.both > 0 && ` · ${s.both} said both`}<br />
          {m.voices} voices · {m.reports} reports{k.id === 'metric' && m.figures > 0 && <><br />{m.figures} figures</>}
        </span>
        <span className={`rp-ph rp-ph-${ph.c}`}>{ph.t}</span>
      </div>
    )
  }
  let body
  if (!models.length) body = <div className="rp-empty" style={{ margin: 16 }}>No model has {min}+ voices on this {k.one} yet.</div>
  else if (k.id === 'metric') body = [...models].sort((x, y) => y.reports - x.reports).map(row)
  else {
    body = GROUPS.map((g) => {
      const ms = models.filter((m) => (m.group || 'neutral') === g.id)
      return ms.length ? (
        <div key={g.id}>
          <div className="rp-group-h"><span className="rp-dot" style={{ background: g.colour }} />{g.label}<span className="rp-n">{ms.length}</span></div>
          {ms.map(row)}
        </div>
      ) : null
    })
  }
  return (
    <>
      {crumbs}
      <div className="rp-adetail">
        <div className="rp-kind-label">{k.one}</div>
        <h2>{a.name}</h2>
        <div className="rp-chips">
          <span className="rp-chip">{plural(models.length, 'model')} ranked</span>
          <span className="rp-chip">{a.voices} voices in all</span>
          <span className="rp-chip">{a.reports} reports in all</span>
        </div>
        {a.definition && <div className="rp-rule"><span className="rp-k">What counts as a report here</span>{a.definition}</div>}
        <div className="rp-rankwrap">
          <div className="rp-rankhead">
            <span>#</span><span>Model</span>
            <span className="rp-axis-scale"><span style={{ color: 'var(--fail)' }}>← negative reports</span><span style={{ color: 'var(--pass)' }}>positive reports →</span></span>
            <span>Also</span><span>Summary</span>
          </div>
          {body}
        </div>
        <p className="rp-order-note">
          {k.id === 'metric'
            ? 'Ranked by number of reports. The figures themselves are not shown on this page.'
            : 'Ranked in three groups: reported working, then neutral only, then problems and none working. Within the first group, models whose reports more consistently say it worked rank higher; more reports give more confidence. Bars share one scale across all rows.'}
          {' '}Click a model to see everything it has been reported for.
        </p>
        {hidden > 0 && (
          <p className="rp-below">{hidden} more model{hidden === 1 ? ' is' : 's are'} discussed here with fewer than {min} voices{multi ? ' or from one platform' : ''}. Not shown, and not a judgement.</p>
        )}
      </div>
    </>
  )
}

/**
 * EACH SECTION IS ITS OWN PAGE (2026-10-14), as Model specs is under Tools:
 *
 *   /reports, /reports/models         Models (the first is the nav's Models link)
 *   /reports/models/<vendor>/<model>  one model, everything it was reported for
 *   /reports/jobs | capabilities | metrics           the list
 *   /reports/jobs/<slug> (etc.)                      one job, capability, metric
 *
 * The threshold travels as `?min=3|10` and `?multi=1` on every one of them, so
 * moving between pages keeps the reader's setting. The old `?tab=` addresses
 * the nav first used are redirected to their page.
 */
const SECTIONS = {
  models: { pill: 'models', title: 'Models', lede: 'Every AI model on our registry that engineers have reported on in real use, with what it has been discussed for.' },
  jobs: { pill: 'job', title: 'Jobs', lede: 'What people used AI models for, such as coding agents or summarising documents, and which models they reported on for each.' },
  capabilities: { pill: 'capability', title: 'Capabilities', lede: 'Specific abilities people reported working or failing, such as reasoning, tool use, vision or long context.' },
  metrics: { pill: 'metric', title: 'Metrics', lede: 'Figures people measured themselves, such as speed, cost or benchmark results, counted by the reports that gave them.' },
}

export default function Reports() {
  const { pathname, search } = useLocation()
  const navigate = useNavigate()
  const [sp] = useSearchParams()
  const rest = pathname.replace(/^\/reports\/?/, '')
  const [sectionKey, ...itemParts] = rest ? rest.split('/') : []
  // `/reports` ITSELF IS THE AI MODELS LIST (2026-10-14); there is no hub page.
  const section = sectionKey ? (SECTIONS[sectionKey] || null) : SECTIONS.models
  const pill = section ? section.pill : null
  const item = itemParts.length ? decodeURIComponent(itemParts.join('/')) : null
  const min = MINS.includes(Number(sp.get('min'))) ? Number(sp.get('min')) : 5
  const multi = sp.get('multi') === '1'

  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)
  const [how, setHow] = useState(false)
  const [q, setQ] = useState({ models: '', job: '', capability: '', metric: '' })

  // THE FIRST NAV LINKS were `/reports?tab=jobs`; send them to their page.
  useEffect(() => {
    const tab = sp.get('tab')
    if (!sectionKey && tab && SECTIONS[tab]) {
      const next = new URLSearchParams(sp)
      next.delete('tab')
      const it = next.get('item')
      next.delete('item')
      const qs = next.toString()
      navigate(`/reports/${tab}${it ? `/${it}` : ''}${qs ? `?${qs}` : ''}`, { replace: true })
    }
  }, [sectionKey, sp, navigate])

  useEffect(() => {
    let alive = true
    reportsPage()
      .then((d) => { if (alive) setData(d) })
      .catch((e) => {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message || 'The models could not be read.')
      })
    return () => { alive = false }
  }, [])

  const v = useMemo(() => (data ? build(data.axes, min, multi) : null), [data, min, multi])

  // The page's own name, for its title once the item is known.
  const itemName = (() => {
    if (!item || !data) return null
    if (pill === 'models') {
      const m = data.axes.flatMap((a) => a.models).find((x) => modelId(x) === item || x.key === item)
      return m ? shortName(m) : null
    }
    const a = data.axes.find((x) => x.kind === pill && x.slug === item)
    return a ? a.name : null
  })()
  useHead(reportsIndex(section ? { key: sectionKey || 'models', title: section.title, lede: section.lede } : null,
                       item ? { path: itemParts.join('/'), name: itemName } : null))

  const keep = () => {
    const next = new URLSearchParams()
    if (min !== 5) next.set('min', String(min))
    if (multi) next.set('multi', '1')
    const qs = next.toString()
    return qs ? `?${qs}` : ''
  }
  const TAB_TO_KEY = { models: 'models', jobs: 'jobs', capabilities: 'capabilities', metrics: 'metrics' }
  const go = (key, id) => {
    const path = key ? `/reports/${TAB_TO_KEY[key] || key}${id ? `/${id.split('/').map(encodeURIComponent).join('/')}` : ''}` : '/reports'
    navigate(path + keep())
    window.scrollTo({ top: 0 })
  }
  const open = (tab, id) => go(tab, id)
  const back = (tab) => go(tab)
  const setCriteria = (patch) => {
    const next = new URLSearchParams(search)
    for (const [key, val] of Object.entries(patch)) {
      if (val === null || val === undefined || val === '') next.delete(key)
      else next.set(key, String(val))
    }
    const qs = next.toString()
    navigate(pathname + (qs ? `?${qs}` : ''), { replace: true })
  }

  const heading = section ? section.title : 'Models'
  const lede = section
    ? section.lede
    : 'The jobs they used them for, the capabilities they tested and the figures they measured. Everything is counted from our evidence collection and never quoted.'

  return (
    <div className="shell section-tight stack stack-4 rp">
      <div className="stack stack-1">
        <span className="go-badge go-board page-tag" style={{ alignSelf: 'flex-start' }}>Models</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>{heading}</h1>
        <p className="muted" style={{ maxWidth: '78ch', margin: 0 }}>
          {lede} A model appears only where at least {min} different people reported on it.
        </p>
      </div>

      <section className="rp-part">
        <div className="rp-part-head">
          <span className="eyebrow">{section && section.title !== 'Models' ? `Models · ${section.title}` : 'Models'}</span>
          <span className="rp-part-sub">
            Counted from public reports, at least <b>{min}</b> voices each
            {data?.newest_report && <> · newest report {data.newest_report}</>}
          </span>
        </div>
        <div className="rp-controls">
          {section && !item && (
            <div className="rp-searchbar" style={{ marginTop: 0, flex: '1 1 360px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
              <input autoComplete="off" aria-label="Search" placeholder={PLACEHOLDER[pill]}
                     value={q[pill]} onChange={(e) => setQ({ ...q, [pill]: e.target.value })} />
            </div>
          )}
          <div className="rp-criteria">
            <span>At least</span>
            <select aria-label="Minimum voices" value={min} onChange={(e) => setCriteria({ min: Number(e.target.value) === 5 ? null : e.target.value })}>
              {MINS.map((n) => <option key={n} value={n}>{n} voices</option>)}
            </select>
            <label title="Require the voices to come from at least two different platforms">
              <input type="checkbox" checked={multi} onChange={(e) => setCriteria({ multi: e.target.checked ? 1 : null })} /> from 2+ platforms
            </label>
            <button type="button" className="rp-btn" onClick={() => setHow(true)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></svg>
              How we count
            </button>
          </div>
        </div>
        {section && !item && <Definition pill={pill} min={min} />}

        <div style={{ marginTop: 22 }}>
          {unreadable && <Unreadable detail={unreadable} />}
          {err && <Notice icon={<IconAlert />}>{err}</Notice>}
          {!data && !err && !unreadable && <div className="skel" style={{ height: 260 }} />}
          {v && sectionKey && !section && <div className="rp-empty">There is no page at this address.</div>}
          {v && section && (
            item
              ? pill === 'models'
                ? <ModelView v={v} id={item} min={min} multi={multi} open={open} back={back} />
                : <AxisView v={v} axes={data.axes} kind={pill} slug={item} min={min} multi={multi} open={open} back={back} />
              : pill === 'models'
                ? <ModelsList v={v} q={q.models} open={open}
                              onCompare={(ids) => navigate(`/compare?ids=${encodeURIComponent(ids.join(','))}&from=reports`)} />
                : <AxisList v={v} kind={pill} q={q[pill]} open={open} />
          )}
        </div>
      </section>

      {/* AT THE FOOT OF THE HUB AND THE LISTS, as in the demo: the method behind
          every number, open on the page rather than only behind a button. */}
      {data && !item && (
        <section className="rp-method">
          <h2>How the reports work</h2>
          <p className="rp-intro">Everything on these pages is an output of our research method: collect public reports, check every classified statement against its source text in code, then count. These rules decide what is shown and how.</p>
          <MethodBoxes min={min} multi={multi} withheld={data.withheld_entries} />
        </section>
      )}

      {how && <HowWeCount min={min} multi={multi} withheld={data?.withheld_entries} onClose={() => setHow(false)} />}
    </div>
  )
}
