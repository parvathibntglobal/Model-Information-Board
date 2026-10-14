import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { reportsPage, listRegistry, fetchAll, BoardUnreadable } from '../api'
import { Notice, Unreadable } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { useHead } from '../seo/head'
import { modelPicker } from '../seo/pages'

/**
 * BEST AI MODEL PICKER (2026-10-14), from model-alternatives-demo.html: the
 * best model for a job and cheaper alternatives to a model, in one tool.
 *
 * Start from a model you use, a job, a capability, a metric or a price range -
 * or several at once - and see which models engineers reported working and not
 * working, beside what each one costs.
 *
 * TWO SOURCES, KEPT APART. The evidence is `/reports` (judge/reports.py): the
 * board's counts over the PUBLIC view, never a quote, link or author. Prices
 * are the registry's (`/models`): what providers ADVERTISE, never evidence, and
 * a model with no published price shows "—", never $0.
 *
 * NOTHING IS A SCORE. Phrases are a fixed rule over the counts (`phrase`),
 * groups are by what the reports say, and "saves $x" is arithmetic on two
 * advertised prices, offered only beside a model reported working.
 *
 * THE ADDRESS HOLDS THE SEARCH (`?model=&job=&capability=&metric=&price=`), so
 * a result can be sent to somebody and opens as they saw it.
 */

const COMPARE_MAX = 3
const THIN = 3
const KINDS = ['job', 'capability', 'metric']
const KIND_LABEL = { job: 'job', capability: 'capability', metric: 'metric' }
const KIND_ORDER = { job: 0, capability: 1, metric: 2 }
const BANDS = [
  { id: 'b0', label: 'Under $0.10', lo: 0, hi: 0.1 },
  { id: 'b1', label: '$0.10 – $0.50', lo: 0.1, hi: 0.5 },
  { id: 'b2', label: '$0.50 – $2', lo: 0.5, hi: 2 },
  { id: 'b3', label: '$2 – $5', lo: 2, hi: 5 },
  { id: 'b4', label: '$5 – $10', lo: 5, hi: 10 },
  { id: 'b5', label: '$10 and over', lo: 10, hi: Infinity },
]
const inBand = (b, p) => p != null && p >= b.lo && p < b.hi
const TYPES = [
  { id: 'model', label: 'AI model', plural: 'AI models', ph: 'Type a model, such as Claude Opus 5 or DeepSeek V4' },
  { id: 'job', label: 'Job', plural: 'Jobs', ph: 'Type a job, such as coding agents' },
  { id: 'capability', label: 'Capability', plural: 'Capabilities', ph: 'Type a capability, such as reasoning or vision' },
  { id: 'metric', label: 'Metric', plural: 'Metrics', ph: 'Type a metric, such as cost per million tokens' },
  { id: 'price', label: 'Budget', plural: 'Budgets', ph: 'Choose a price range per 1M input tokens' },
]
const TYPE = Object.fromEntries(TYPES.map((t) => [t.id, t]))
const ORDER = TYPES.map((t) => t.id)
const GROUPS = [
  { id: 'working', label: 'Reported working', colour: 'var(--mp-good)' },
  { id: 'mixed', label: 'Mixed reports', colour: 'var(--mp-mixed)' },
  { id: 'problems', label: 'Reported not working', colour: 'var(--mp-bad)' },
  { id: 'neutral', label: 'No side taken', colour: 'var(--mp-neutral)' },
]
const METRIC_GROUP = { working: 'Positive reports', mixed: 'Mixed reports', problems: 'Negative reports', neutral: 'No side taken' }
const DEFAULTS = { sort: 'price', minV: 3, problems: true, kind: 'all', view: 'cards' }

// ── names, prices, words ─────────────────────────────────────────────────────
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
const rate = (r) => (r == null ? '—' : r === 0 ? '$0' : `$${r < 0.1 ? r.toPrecision(2) : r.toFixed(2)}`)
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

function phrase(s) {
  const p = s.positive, n = s.negative
  if (!p && !n) return { t: 'No side taken', c: 'neutral' }
  if (!n) return { t: 'Reported working', c: 'working' }
  if (!p) return { t: 'Reported not working', c: 'problems' }
  if (p >= 3 * n) return { t: 'Mostly working', c: 'working' }
  if (n >= 3 * p) return { t: 'Mostly not working', c: 'problems' }
  return { t: 'Mixed reports', c: 'mixed' }
}
/** Metrics are figures, not tasks: "working" reads wrong on a latency. */
function phraseFor(kind, s) {
  const ph = phrase(s)
  if (kind !== 'metric') return ph
  const t = { working: s.negative ? 'Mostly positive reports' : 'Positive reports', problems: s.positive ? 'Mostly negative reports' : 'Negative reports', mixed: 'Mixed reports', neutral: 'No side taken' }[ph.c]
  return { c: ph.c, t }
}
const voicesText = (m) => (m.voices ? plural(m.voices, 'voice') : `${plural(m.reports, 'report')} · author not identified`)

// ── pieces ───────────────────────────────────────────────────────────────────
/** One horizontal bar split positive / negative / neutral. One report gets no
 *  bar: a chart would make one person's experience look like a distribution. */
function SplitBar({ m }) {
  const s = m.split
  if (m.voices <= 1 && m.reports <= 1) return <span className="mp-single">single report</span>
  const total = Math.max(1, s.positive + s.negative + s.neutral)
  return (
    <span className="mp-bar" role="img" aria-label={`${s.positive} positive, ${s.negative} negative, ${s.neutral} neutral`}>
      {s.positive > 0 && <i className="mp-pos" style={{ width: `${(100 * s.positive) / total}%` }} />}
      {s.negative > 0 && <i className="mp-neg" style={{ width: `${(100 * s.negative) / total}%` }} />}
      {s.neutral > 0 && <i className="mp-neu" style={{ width: `${(100 * s.neutral) / total}%` }} />}
    </span>
  )
}
/** The three counts as a small legend: a coloured mark carries the meaning,
 *  the number and word stay in text colour so they read on any mark. */
const CountLegend = ({ s }) => (
  <span className="mp-clegend">
    <span><i className="mp-good-bg" /><b>{s.positive}</b> positive</span>
    <span><i className="mp-bad-bg" /><b>{s.negative}</b> negative</span>
    <span><i className="mp-neu-bg" /><b>{s.neutral}</b> neutral</span>
  </span>
)
const Badge = ({ ph }) => <span className={`mp-badge mp-b-${ph.c}`}><i />{ph.t}</span>

const Counts = ({ s }) => (
  <span className="mp-counts" title="positive · negative · neutral reports">
    <b className="mp-p">{s.positive}</b> · <b className="mp-ng">{s.negative}</b> · <b className="mp-u">{s.neutral}</b>
  </span>
)

/**
 * THE SPLIT AS A SMALL DONUT: positive, negative and neutral reports as parts
 * of one whole, with the report count in the middle. A 2px gap separates the
 * parts, so a thin slice still reads. One report gets no donut (see SplitBar).
 */
function Donut({ m, size = 46 }) {
  const s = m.split
  if (m.voices <= 1 && m.reports <= 1) return <span className="mp-single">single<br />report</span>
  const parts = [['var(--mp-good)', s.positive], ['var(--mp-bad)', s.negative], ['var(--mp-neutral)', s.neutral]].filter((x) => x[1] > 0)
  const total = parts.reduce((n, x) => n + x[1], 0) || 1
  const r = 16, C = 2 * Math.PI * r, gap = parts.length > 1 ? 1.6 : 0
  let at = 0
  return (
    <svg className="mp-donut" width={size} height={size} viewBox="0 0 44 44" role="img"
         aria-label={`${s.positive} positive, ${s.negative} negative, ${s.neutral} neutral of ${m.reports} reports`}>
      <title>{`${s.positive} positive · ${s.negative} negative · ${s.neutral} neutral${s.both ? ` · ${s.both} said both` : ''}`}</title>
      <circle cx="22" cy="22" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="7" />
      {parts.map(([colour, v]) => {
        const len = (C * v) / total
        const seg = <circle key={colour} cx="22" cy="22" r={r} fill="none" stroke={colour} strokeWidth="7"
                            strokeDasharray={`${Math.max(0.5, len - gap)} ${C}`} strokeDashoffset={-at} transform="rotate(-90 22 22)" />
        at += len
        return seg
      })}
      <text x="22" y="25.5" textAnchor="middle" className="mp-donut-n">{m.reports}</text>
    </svg>
  )
}

function ModelCard({ m, kind, refPrice, price, cmp }) {
  const ph = phraseFor(kind, m.split)
  const id = modelId(m)
  const on = cmp.has(id)
  const saves = ph.c === 'working' && refPrice != null && price != null && price < refPrice ? refPrice - price : null
  return (
    <div className={`mp-card mp-g-${ph.c}`}>
      <div className="mp-card-head">
        <Badge ph={ph} />
        <span className="mp-price" title="Advertised input price per 1M tokens">{rate(price)}<small> /1M in</small></span>
      </div>
      <div>
        <div className="mp-prov">{providerOf(m)}</div>
        <div className="mp-name">{shortName(m)}</div>
      </div>
      <div className="mp-card-mid">
        <Donut m={m} />
        <div className="mp-card-facts">
          <CountLegend s={m.split} />
          <div className="mp-meta">
            <span>{voicesText(m)}</span>
            {m.voices < THIN && <span className="mp-thin">thin evidence</span>}
          </div>
          {m.newest && <div className="mp-meta mp-dim">newest {m.newest}</div>}
        </div>
      </div>
      {saves != null && <div className="mp-save">↓ saves {rate(saves)} per 1M input</div>}
      <div className="mp-card-foot">
        <span className="mp-actions">
          <Link to={`/reports/models/${id}`} className="mp-link">Model page</Link>
          <label className="mp-cmp">
            <input type="checkbox" checked={on} disabled={!on && cmp.size >= COMPARE_MAX} onChange={() => cmp.toggle(id)} />
            Compare
          </label>
        </span>
      </div>
    </div>
  )
}

/**
 * THE CHART VIEW of one group: a row per model, negative reports to the left of
 * the line and positive to the right, every row on ONE scale so lengths compare
 * down the list. Neutral reports are a count beside it, not a bar: they take no
 * side, so they belong on neither.
 */
function GroupChart({ ms, kind, refPrice, priceOf, cmp }) {
  const scale = Math.max(1, ...ms.map((m) => Math.max(m.split.positive, m.split.negative)))
  return (
    <div className="mp-chart" role="table" aria-label="Positive and negative reports per model">
      <div className="mp-chart-h" role="row">
        <span>Model</span><span>Price /1M in</span>
        <span className="mp-chart-axis"><em className="mp-ng">← negative</em><em className="mp-p">positive →</em></span>
        <span>Neutral · voices</span><span />
      </div>
      {ms.map((m) => {
        const s = m.split, id = modelId(m), on = cmp.has(id), price = priceOf(m)
        // 40% each side leaves room for the count beside the longest bar
        const wn = (40 * s.negative) / scale, wp = (40 * s.positive) / scale
        const ph = phraseFor(kind, s)
        const saves = ph.c === 'working' && refPrice != null && price != null && price < refPrice
        return (
          <div className="mp-chart-row" role="row" key={m.key} title={`${ph.t} · ${s.positive} positive · ${s.negative} negative · ${s.neutral} neutral`}>
            <span className="mp-chart-name"><small>{providerOf(m)}</small>{shortName(m)}{m.voices < THIN && <span className="mp-thin">thin</span>}</span>
            <span className={`mp-chart-price${saves ? ' mp-save' : ''}`}>{rate(price)}</span>
            <span className="mp-div">
              <i className="mp-div-mid" />
              {s.negative > 0 && <i className="mp-div-neg" style={{ width: `${wn}%` }} />}
              {s.positive > 0 && <i className="mp-div-pos" style={{ width: `${wp}%` }} />}
              <b className="mp-div-l" style={{ right: `calc(50% + ${wn}% + 5px)` }}>{s.negative}</b>
              <b className="mp-div-r" style={{ left: `calc(50% + ${wp}% + 5px)` }}>{s.positive}</b>
            </span>
            <span className="mp-chart-side">{s.neutral} · {m.voices || '—'}</span>
            <label className="mp-cmp"><input type="checkbox" checked={on} disabled={!on && cmp.size >= COMPARE_MAX} onChange={() => cmp.toggle(id)} aria-label={`Compare ${shortName(m)}`} /></label>
          </div>
        )
      })}
    </div>
  )
}

/** Cards grouped by what the reports say, eight shown per group until asked. */
function Grouped({ list, kind, refPrice, priceOf, cmp, settings, labelFor, openKey, open, toggleOpen }) {
  const blocks = GROUPS.filter((g) => g.id !== 'problems' || settings.problems).map((g) => {
    const ms = list.filter((m) => phrase(m.split).c === g.id && m.voices >= settings.minV)
    if (!ms.length) return null
    const key = openKey + g.id
    const shown = open.has(key) ? ms : ms.slice(0, 8)
    return (
      <div key={g.id} className="mp-group">
        <div className={`mp-group-h mp-gh-${g.id}`}><span className="mp-dot" style={{ background: g.colour }} />{labelFor ? labelFor(g) : g.label}<span className="mp-n">{ms.length}</span></div>
        {settings.view === 'chart'
          ? <GroupChart ms={shown} kind={kind} refPrice={refPrice} priceOf={priceOf} cmp={cmp} />
          : (
            <div className="mp-cards">
              {shown.map((m) => <ModelCard key={m.key} m={m} kind={kind} refPrice={refPrice} price={priceOf(m)} cmp={cmp} />)}
            </div>
          )}
        {ms.length > 8 && <button type="button" className="mp-more" onClick={() => toggleOpen(key)}>{open.has(key) ? 'Show fewer' : `Show all ${ms.length}`}</button>}
      </div>
    )
  }).filter(Boolean)
  return blocks.length ? blocks : null
}

// ── the page ─────────────────────────────────────────────────────────────────
export default function ModelPicker() {
  useHead(modelPicker())
  const navigate = useNavigate()
  const [sp, setSp] = useSearchParams()
  const [data, setData] = useState(null)
  const [registry, setRegistry] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  const [type, setType] = useState('model')
  const [filters, setFilters] = useState({})
  const [ran, setRan] = useState(null)
  const [settings, setSettings] = useState({ ...DEFAULTS, cheaper: true })
  const [axesShown, setAxesShown] = useState(6)
  const [open, setOpen] = useState(new Set())
  const [cmpIds, setCmpIds] = useState([])
  const [q, setQ] = useState('')
  const [listOpen, setListOpen] = useState(false)
  const [act, setAct] = useState(0)
  const comboRef = useRef(null)
  const resultsRef = useRef(null)

  useEffect(() => {
    let alive = true
    reportsPage()
      .then((d) => { if (alive) setData(d) })
      .catch((e) => {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message || 'The board could not be read.')
      })
    // Prices are optional: without them every price reads "—", never a failure.
    fetchAll((l, o) => listRegistry(l, o)).then((r) => { if (alive) setRegistry(r.models || []) }).catch(() => { if (alive) setRegistry([]) })
    return () => { alive = false }
  }, [])

  // ── index ──────────────────────────────────────────────────────────────────
  const idx = useMemo(() => {
    if (!data) return null
    const models = new Map()
    for (const a of data.axes) {
      for (const m of a.models) {
        let r = models.get(m.key)
        if (!r) { r = { key: m.key, label: m.label, canonical: m.canonical, axes: [], voices: 0 }; models.set(m.key, r) }
        r.axes.push({ a, m })
        r.voices += m.voices
      }
    }
    const list = [...models.values()].sort((x, y) => y.axes.length - x.axes.length || shortName(x).localeCompare(shortName(y)))
    const byId = new Map(list.map((r) => [modelId(r), r]))
    const members = (kind, pid) => data.axes.filter((a) => a.kind === kind && a.parent === pid).sort((x, y) => y.models.length - x.models.length)
    return { models, list, byId, members, parents: data.parents || {} }
  }, [data])

  const prices = useMemo(() => {
    const byCanon = new Map(), byMv = new Map()
    for (const r of registry || []) {
      if (r.canonical_id) byCanon.set(r.canonical_id, r.price_in)
      if (r.model_version_id) byMv.set(r.model_version_id, r.price_in)
    }
    return { byCanon, byMv }
  }, [registry])
  const priceOf = (m) => {
    const p = (m.canonical && prices.byCanon.get(m.canonical)) ?? prices.byMv.get(m.key)
    return p == null ? null : p
  }

  // ── options for each "start from" type ─────────────────────────────────────
  const optionsFor = (t) => {
    if (!idx) return []
    if (t === 'model') {
      return idx.list.map((r) => ({ id: modelId(r), label: shortName(r), pre: providerOf(r), sub: `${plural(r.axes.length, 'job, capability or metric', 'jobs, capabilities and metrics')} · ${rate(priceOf(r))} per 1M in` }))
    }
    if (t === 'price') {
      return BANDS.map((b) => ({ id: b.id, label: `${b.label} per 1M input`, pre: 'budget', sub: plural(idx.list.filter((r) => inBand(b, priceOf(r))).length, 'model') }))
    }
    const axes = data.axes.filter((a) => a.kind === t)
      .sort((x, y) => y.models.length - x.models.length || x.name.localeCompare(y.name))
      .map((a) => ({ id: a.slug, label: a.name, pre: t, sub: `${plural(a.models.length, 'model')} · ${a.voices} voices${a.parent ? ` · ${idx.parents[a.parent] || a.parent}` : ''}` }))
    // GROUPS FIRST, for capabilities and metrics: a reading aid, never a merge.
    const groups = Object.entries(idx.parents)
      .map(([pid, name]) => ({ pid, name, n: idx.members(t, pid).length }))
      .filter((g) => g.n > 1)
      .map((g) => ({ id: `parent:${g.pid}`, label: g.name, pre: 'group', sub: `${g.n} ${t === 'metric' ? 'metrics' : 'capabilities'}, shown separately` }))
    return groups.concat(axes)
  }
  const shownOpts = useMemo(() => {
    const ql = q.trim().toLowerCase()
    return optionsFor(type).filter((o) => !ql || `${o.label} ${o.pre}`.toLowerCase().includes(ql)).slice(0, 60)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, q, idx, prices])

  // ── the search in the address ──────────────────────────────────────────────
  const labelFor = (t, id) => (optionsFor(t).find((o) => o.id === id) || {}).label
  useEffect(() => {
    if (!idx || ran) return
    const f = {}
    for (const t of ORDER) {
      const id = sp.get(t)
      if (id) { const label = labelFor(t, id); if (label) f[t] = { id, label } }
    }
    if (Object.keys(f).length) { setFilters(f); run(f, false) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, registry])

  const has = (f) => ORDER.some((k) => f && f[k])
  function run(f = filters, scroll = true) {
    if (!has(f)) return
    const firstOfKind = !ran || !!ran.model !== !!f.model
    setRan(JSON.parse(JSON.stringify(f)))
    setAxesShown(6)
    setOpen(new Set())
    if (firstOfKind) setSettings((s) => ({ ...s, kind: 'all', cheaper: !!f.model }))
    if (f.model && !cmpIds.includes(f.model.id)) setCmpIds((c) => [f.model.id, ...c].slice(0, COMPARE_MAX))
    const next = new URLSearchParams()
    for (const t of ORDER) if (f[t]) next.set(t, f[t].id)
    setSp(next, { replace: true })
    if (scroll) setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }
  const choose = (o) => {
    setFilters((f) => ({ ...f, [type]: { id: o.id, label: o.label } }))
    setQ('')
    setListOpen(false)
  }
  const removeFilter = (t) => {
    const f = { ...filters }
    delete f[t]
    setFilters(f)
    if (ran) { if (has(f)) run(f, false); else { setRan(null); setSp(new URLSearchParams(), { replace: true }) } }
  }
  const clearAll = () => { setFilters({}); setRan(null); setSp(new URLSearchParams(), { replace: true }) }
  const tryExample = (f) => { setFilters(f); setType(Object.keys(f)[0]); run(f) }

  useEffect(() => {
    const close = (e) => { if (comboRef.current && !comboRef.current.contains(e.target)) setListOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const cmp = {
    has: (id) => cmpIds.includes(id),
    size: cmpIds.length,
    toggle: (id) => setCmpIds((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= COMPARE_MAX ? c : [...c, id])),
  }
  const toggleOpen = (k) => setOpen((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n })
  const set = (patch) => setSettings((s) => ({ ...s, ...patch }))
  const settingsChanged = Object.keys(DEFAULTS).some((k) => settings[k] !== DEFAULTS[k]) || (ran && settings.cheaper !== !!ran.model)

  // ── results ────────────────────────────────────────────────────────────────
  const sorter = settings.sort === 'price'
    ? (x, y) => ((priceOf(x) ?? 1e9) - (priceOf(y) ?? 1e9)) || y.voices - x.voices
    : (x, y) => y.voices - x.voices || ((priceOf(x) ?? 1e9) - (priceOf(y) ?? 1e9))
  const bandOf = (F) => (F.price ? BANDS.find((b) => b.id === F.price.id) : null)
  const selectedAxes = (F) => {
    const out = []
    for (const k of KINDS) {
      const f = F[k]
      if (!f) continue
      if (String(f.id).startsWith('parent:')) for (const a of idx.members(k, f.id.slice(7))) out.push({ a, group: f.label })
      else { const a = data.axes.find((x) => x.kind === k && x.slug === f.id); if (a) out.push({ a, group: null }) }
    }
    return out
  }
  const openAxis = (a) => { const f = { ...filters, [a.kind]: { id: a.slug, label: a.name } }; setFilters(f); setType(a.kind); run(f) }
  const openGroup = (kind, pid) => { const f = { ...filters, [kind]: { id: `parent:${pid}`, label: idx.parents[pid] || pid } }; setFilters(f); setType(kind); run(f) }

  function ParentNav({ a }) {
    if (!a.parent) return null
    const members = idx.members(a.kind, a.parent)
    const sibs = members.filter((x) => x.slug !== a.slug)
    const name = idx.parents[a.parent] || a.parent
    return (
      <div className="mp-pnav">
        <span className="mp-pl">Part of</span>
        <button type="button" className="mp-chip mp-chip-go" onClick={() => openGroup(a.kind, a.parent)}>{name} · {plural(members.length, a.kind)} →</button>
        {sibs.length > 0 && <span className="mp-pl" style={{ marginLeft: 8 }}>Related</span>}
        {sibs.slice(0, 6).map((x) => <button type="button" key={x.slug} className="mp-chip" onClick={() => openAxis(x)}>{x.name}</button>)}
        {sibs.length > 6 && <button type="button" className="mp-chip" onClick={() => openGroup(a.kind, a.parent)}>+{sibs.length - 6} more</button>}
      </div>
    )
  }

  function ModelResults({ r, F }) {
    const mine = priceOf(r), band = bandOf(F), sel = selectedAxes(F)
    let rows = sel.length
      ? sel.map(({ a, group }) => ({ a, group, m: a.models.find((x) => x.key === r.key) || null }))
      : r.axes.filter(({ a }) => settings.kind === 'all' || a.kind === settings.kind).map(({ a, m }) => ({ a, m, group: null }))
    rows = rows.filter(({ m }) => sel.length || (m && m.voices >= settings.minV))
      .sort((x, y) => (KIND_ORDER[x.a.kind] - KIND_ORDER[y.a.kind]) || ((y.m ? y.m.voices : 0) - (x.m ? x.m.voices : 0)) || y.a.models.length - x.a.models.length)
    const total = rows.length
    rows = rows.slice(0, axesShown)
    return (
      <>
        <div className="mp-res-head">
          <h2>Alternatives to {shortName(r)}</h2>
          <p>{providerOf(r)} · {rate(mine)} per 1M input · reported on {plural(r.axes.length, 'job, capability or metric', 'jobs, capabilities and metrics')}{band ? ` · showing models priced ${band.label} per 1M input` : ''}</p>
        </div>
        {!rows.length && <div className="mp-none">Nothing of this kind is reported for this model from {settings.minV}+ people yet. Lower the minimum voices to see more.</div>}
        {rows.map(({ a, m, group }) => {
          let others = a.models.filter((x) => x.key !== r.key && (!band || inBand(band, priceOf(x))))
          if (settings.cheaper && mine != null) others = others.filter((x) => priceOf(x) != null && priceOf(x) < mine)
          others = [...others].sort(sorter)
          const metric = a.kind === 'metric', cheap = settings.cheaper ? ', and cheaper' : ''
          const ph = m ? phraseFor(a.kind, m.split) : null
          const body = others.length ? (
            <Grouped list={others} kind={a.kind} refPrice={mine} priceOf={priceOf} cmp={cmp} settings={settings}
                     openKey={a.kind + a.slug} open={open} toggleOpen={toggleOpen}
                     labelFor={(g) => (g.id === 'working' ? (metric ? `Positive reports on this${cheap}` : `Also reported working on this${cheap}`)
                       : g.id === 'problems' ? (metric ? `Negative reports on this${cheap}` : `Reported not working on this${cheap}`) : g.label)} />
          ) : null
          return (
            <section key={a.kind + a.slug} className="mp-block">
              <h3>{a.name}<span className="mp-k">{KIND_LABEL[a.kind]}{group ? ` · in ${group}` : ''}</span></h3>
              {!group && <ParentNav a={a} />}
              <div className="mp-self">
                {m ? (
                  <>
                    <b>{shortName(r)}</b>
                    <span className={`mp-phrase mp-ph-${ph.c}`} style={{ margin: 0 }}>{ph.t}</span>
                    <span style={{ minWidth: 120, flex: '0 1 160px' }}><SplitBar m={m} /></span>
                    <span>{voicesText(m)}</span><Counts s={m.split} />
                    {m.voices < THIN && <span className="mp-thin">thin evidence</span>}
                  </>
                ) : <><b>{shortName(r)}</b><span className="mp-dim">no reports on this yet</span></>}
              </div>
              {body || <div className="mp-none">No {settings.cheaper ? 'cheaper ' : ''}model{band ? ' in this price range' : ''} has reports on this{settings.minV > 0 ? ` from ${settings.minV}+ people` : ''} yet.</div>}
            </section>
          )
        })}
        {total > axesShown && <div className="mp-center"><button type="button" className="mp-more" onClick={() => setAxesShown((n) => n + 6)}>Show more ({total - axesShown} of {total} left)</button></div>}
      </>
    )
  }

  function AxisResults({ F }) {
    const band = bandOf(F), sel = selectedAxes(F)
    const inB = (m) => !band || inBand(band, priceOf(m))
    const plain = sel.filter((x) => !x.group)
    const groups = [...new Set(sel.map((x) => x.group).filter(Boolean))]
    // A model qualifies for "all of them" when its reports say it works on EVERY
    // selected item, each from enough people. Counts stay per item.
    const all = plain.length >= 2
      ? idx.list.filter((r) => inB(r) && plain.every(({ a }) => { const m = a.models.find((x) => x.key === r.key); return m && m.voices >= settings.minV && phrase(m.split).c === 'working' }))
        .sort(settings.sort === 'price' ? (x, y) => (priceOf(x) ?? 1e9) - (priceOf(y) ?? 1e9) : (x, y) => y.voices - x.voices)
      : null
    const names = ORDER.filter((k) => F[k] && k !== 'model').map((k) => F[k].label)
    return (
      <>
        <div className="mp-res-head">
          <h2>Models for {names.join(' · ')}</h2>
          <p>{sel.length === 1 ? `One ${sel[0].a.kind}` : `${sel.length} jobs, capabilities or metrics`} selected{band ? ` · models priced ${band.label} per 1M input` : ''}</p>
        </div>
        {groups.length > 0 && (
          <div className="mp-note">
            {groups.join(', ')} {groups.length === 1 ? 'is a group' : 'are groups'}: a heading for reading, not a merge. Each member keeps its own counts, never added together, because one post can be filed under two names.
          </div>
        )}
        {all && (
          <section className="mp-block mp-inter">
            <h3>Reported working on all of them<span className="mp-k">{plain.map(({ a }) => a.name).join(' + ')}</span></h3>
            <p className="mp-def">Each model here is reported working on every selected item, each by at least {settings.minV || 1} {settings.minV > 1 ? 'people' : 'person'}. Counts stay per item.</p>
            {all.length ? (
              <div className="mp-cards">
                {all.map((r) => (
                  <div key={r.key} className="mp-card mp-g-working">
                    <div className="mp-card-top">
                      <div><div className="mp-prov">{providerOf(r)}</div><div className="mp-name">{shortName(r)}</div></div>
                      <div className="mp-price">{rate(priceOf(r))}<small>/1M in</small></div>
                    </div>
                    <div className="mp-meta" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
                      {plain.map(({ a }) => { const m = a.models.find((x) => x.key === r.key); return <span key={a.slug}>{a.name}: {voicesText(m)} · <Counts s={m.split} /></span> })}
                    </div>
                    <div className="mp-card-foot">
                      <span />
                      <span className="mp-actions">
                        <Link to={`/reports/models/${modelId(r)}`} className="mp-link">Model page</Link>
                        <label className="mp-cmp"><input type="checkbox" checked={cmp.has(modelId(r))} disabled={!cmp.has(modelId(r)) && cmp.size >= COMPARE_MAX} onChange={() => cmp.toggle(modelId(r))} />Compare</label>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : <div className="mp-none">No model{band ? ' in this price range' : ''} is reported working on all of them by {settings.minV || 1}+ people yet.</div>}
          </section>
        )}
        {sel.slice(0, axesShown).map(({ a, group }) => {
          const list = a.models.filter(inB).sort(sorter)
          const body = <Grouped list={list} kind={a.kind} priceOf={priceOf} cmp={cmp} settings={settings} openKey={a.kind + a.slug} open={open} toggleOpen={toggleOpen}
                                labelFor={(g) => (a.kind === 'metric' ? METRIC_GROUP[g.id] : g.label)} />
          return (
            <section key={a.kind + a.slug} className="mp-block">
              <h3>{a.name}<span className="mp-k">{KIND_LABEL[a.kind]} · {plural(a.models.length, 'model')}{group ? ` · in ${group}` : ''}</span></h3>
              {!group && <ParentNav a={a} />}
              {a.definition && sel.length === 1 && <p className="mp-def">What counts as a report here: {a.definition}</p>}
              {body || <div className="mp-none">No model{band ? ' in this price range' : ''} has reports from {settings.minV}+ people here yet.</div>}
            </section>
          )
        })}
        {sel.length > axesShown && <div className="mp-center"><button type="button" className="mp-more" onClick={() => setAxesShown((n) => n + 6)}>Show more ({sel.length - axesShown} of {sel.length} left)</button></div>}
      </>
    )
  }

  function BudgetResults({ b }) {
    const inRange = idx.list.filter((r) => inBand(b, priceOf(r)))
    const ms = inRange.filter((r) => r.axes.some(({ m }) => m.voices >= settings.minV))
      .sort(settings.sort === 'price' ? (x, y) => priceOf(x) - priceOf(y) || y.voices - x.voices : (x, y) => y.voices - x.voices)
    const hidden = inRange.length - ms.length
    const chip = ({ a, m }) => {
      const ph = phrase(m.split)
      return (
        <button type="button" key={a.kind + a.slug} className={`mp-chip mp-axc mp-g-${ph.c}`} onClick={() => openAxis(a)}
                title={`${ph.t} · ${voicesText(m)} · ${m.split.positive} positive / ${m.split.negative} negative / ${m.split.neutral} neutral`}>
          {a.name} · {m.voices || `${m.reports} rep.`}
        </button>
      )
    }
    return (
      <>
        <div className="mp-res-head">
          <h2>Models at {b.label} per 1M input</h2>
          <p>{plural(ms.length, 'model')} on the board in this range, with what engineers reported them working and not working on</p>
        </div>
        {ms.length ? (
          <div className="mp-cards mp-cards-wide">
            {ms.map((r) => {
              const enough = r.axes.filter(({ m }) => m.voices >= settings.minV).sort((x, y) => y.m.voices - x.m.voices)
              const work = enough.filter(({ m }) => phrase(m.split).c === 'working').slice(0, 8)
              const bad = enough.filter(({ m }) => phrase(m.split).c === 'problems').slice(0, 6)
              const other = enough.filter(({ m }) => ['mixed', 'neutral'].includes(phrase(m.split).c)).slice(0, 6)
              const id = modelId(r)
              return (
                <div key={r.key} className="mp-card">
                  <div className="mp-card-top">
                    <div><div className="mp-prov">{providerOf(r)}</div><div className="mp-name">{shortName(r)}</div></div>
                    <div className="mp-price">{rate(priceOf(r))}<small>/1M in</small></div>
                  </div>
                  <div className="mp-group-h" style={{ marginTop: 6 }}><span className="mp-dot" style={{ background: 'var(--mp-good)' }} />Reported working on<span className="mp-n">{work.length}</span></div>
                  <div className="mp-chips">{work.length ? work.map(chip) : <span className="mp-dim">Nothing yet</span>}</div>
                  {settings.problems && (
                    <>
                      <div className="mp-group-h"><span className="mp-dot" style={{ background: 'var(--mp-bad)' }} />Reported not working on<span className="mp-n">{bad.length}</span></div>
                      <div className="mp-chips">{bad.length ? bad.map(chip) : <span className="mp-dim">Nothing reported</span>}</div>
                    </>
                  )}
                  {other.length > 0 && (
                    <>
                      <div className="mp-group-h"><span className="mp-dot" style={{ background: 'var(--mp-mixed)' }} />Mixed or no side taken<span className="mp-n">{other.length}</span></div>
                      <div className="mp-chips">{other.map(chip)}</div>
                    </>
                  )}
                  <div className="mp-card-foot">
                    <span />
                    <span className="mp-actions">
                      <Link to={`/reports/models/${id}`} className="mp-link">Model page</Link>
                      <label className="mp-cmp"><input type="checkbox" checked={cmp.has(id)} disabled={!cmp.has(id) && cmp.size >= COMPARE_MAX} onChange={() => cmp.toggle(id)} />Compare</label>
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : <div className="mp-none">No model in this range has reports from {settings.minV}+ people yet.</div>}
        <p className="mp-def" style={{ marginTop: 12 }}>
          Numbers on the chips are voices; hover one for its positive / negative / neutral counts, click it to see every model for it.
          {hidden > 0 && ` ${plural(hidden, 'more model is', 'more models are')} in this range with fewer than ${settings.minV} voices on everything; lower the minimum voices to see ${hidden === 1 ? 'it' : 'them'}.`}
        </p>
      </>
    )
  }

  // ── examples, from what the board holds ────────────────────────────────────
  const examples = useMemo(() => {
    if (!idx) return []
    const top = idx.list[0]
    const job = data.axes.filter((a) => a.kind === 'job').sort((x, y) => y.voices - x.voices)[0]
    const cap = data.axes.filter((a) => a.kind === 'capability').sort((x, y) => y.voices - x.voices)[0]
    const out = []
    if (top) out.push({ label: `Alternatives to ${shortName(top)}`, f: { model: { id: modelId(top), label: shortName(top) } } })
    if (job) out.push({ label: `Models for ${job.name}`, f: { job: { id: job.slug, label: job.name } } })
    out.push({ label: 'Models at $0.10 – $0.50', f: { price: { id: 'b1', label: '$0.10 – $0.50 per 1M input' } } })
    if (job && cap) out.push({ label: `${job.name} + ${cap.name}`, f: { job: { id: job.slug, label: job.name }, capability: { id: cap.slug, label: cap.name } } })
    return out
  }, [idx, data])

  const counts = idx ? Object.fromEntries(TYPES.map((t) => [t.id, t.id === 'model' ? idx.list.length : t.id === 'price' ? BANDS.length : data.axes.filter((a) => a.kind === t.id).length])) : {}
  const cmpModels = cmpIds.map((id) => idx?.byId.get(id)).filter(Boolean)

  return (
    <div className={`shell section-tight stack stack-4 mp${cmpIds.length ? ' mp-with-tray' : ''}`}>
      <div className="stack stack-1">
        <span className="go-badge go-models page-tag" style={{ alignSelf: 'flex-start' }}>Tools</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Best AI model picker</h1>
        <p className="mp-sub">Find the best AI model for the job, or a cheaper alternative to the one you use.</p>
        <p className="muted" style={{ maxWidth: '78ch', margin: 0 }}>
          Start from the job you need done to find the models engineers reported working for it, or from a model
          you already use to find alternatives that worked as well and cost less. Narrow it by capability, metric
          or budget, and see what each one costs beside the evidence.
        </p>
      </div>

      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!data && !err && !unreadable && <div className="skel" style={{ height: 220 }} />}

      {idx && (
        <section className="mp-finder">
          <div className="mp-step"><span>1</span>Start from</div>
          <div className="mp-types" role="tablist">
            {TYPES.map((t) => (
              <button type="button" key={t.id} role="tab" aria-selected={type === t.id}
                      className={`mp-type${type === t.id ? ' mp-on' : ''}${filters[t.id] ? ' mp-has' : ''}`}
                      onClick={() => { setType(t.id); setQ(''); setListOpen(true); setAct(0) }}>
                {t.plural}<span className="mp-n">{counts[t.id]}</span>{filters[t.id] && <span className="mp-tick">✓</span>}
              </button>
            ))}
          </div>

          <div className="mp-step"><span>2</span>Choose one, then add more if you like</div>
          <div className="mp-searchrow">
            <div className="mp-combo" ref={comboRef}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
              <input value={q} placeholder={TYPE[type].ph} role="combobox" aria-expanded={listOpen} aria-controls="mp-opts" autoComplete="off"
                     onChange={(e) => { setQ(e.target.value); setListOpen(true); setAct(0) }}
                     onFocus={() => setListOpen(true)}
                     onKeyDown={(e) => {
                       if (e.key === 'ArrowDown') { e.preventDefault(); setListOpen(true); setAct((a) => Math.min(shownOpts.length - 1, a + 1)) }
                       else if (e.key === 'ArrowUp') { e.preventDefault(); setAct((a) => Math.max(0, a - 1)) }
                       else if (e.key === 'Enter') { e.preventDefault(); if (listOpen && q.trim() && shownOpts[act]) choose(shownOpts[act]); else run() }
                       else if (e.key === 'Escape') setListOpen(false)
                     }} />
              {q && <button type="button" className="mp-x" aria-label="Clear the search" onClick={() => setQ('')}>✕</button>}
              <button type="button" className="mp-caret" aria-label="Show all options" onClick={() => setListOpen((o) => !o)}>▾</button>
              {listOpen && (
                <div className="mp-opts" id="mp-opts" role="listbox">
                  {shownOpts.length ? shownOpts.map((o, i) => (
                    <button type="button" key={o.id} role="option" aria-selected={i === act}
                            className={`mp-opt${i === act ? ' mp-act' : ''}`}
                            onMouseEnter={() => setAct(i)} onClick={() => choose(o)}>
                      <span className="mp-opt-pre">{o.pre}</span>
                      <span className="mp-opt-label">{o.label}{filters[type]?.id === o.id && <em> ✓ chosen</em>}</span>
                      <span className="mp-opt-sub">{o.sub}</span>
                    </button>
                  )) : <div className="mp-opt mp-dim">Nothing on the board matches &quot;{q}&quot;</div>}
                </div>
              )}
            </div>
            <button type="button" className="mp-find" disabled={!has(filters)} onClick={() => run()}>
              {filters.model ? 'Find alternatives →' : 'Find models →'}
            </button>
          </div>

          <div className="mp-tags">
            {has(filters) ? (
              <>
                <span className="mp-dim">Filters:</span>
                {ORDER.filter((k) => filters[k]).map((k) => (
                  <span key={k} className="mp-tag"><em>{TYPE[k].label}</em>{filters[k].label}
                    <button type="button" aria-label={`Remove ${TYPE[k].label} filter`} onClick={() => removeFilter(k)}>✕</button>
                  </span>
                ))}
                <button type="button" className="mp-textbtn" onClick={clearAll}>Clear all</button>
              </>
            ) : <span className="mp-dim">No filters yet. A model, a job, a capability, a metric and a budget can all be combined.</span>}
          </div>
          <div className="mp-try">
            <span className="mp-dim">Try:</span>
            {examples.map((x) => <button type="button" key={x.label} className="mp-chip" onClick={() => tryExample(x.f)}>{x.label}</button>)}
          </div>
        </section>
      )}

      {idx && ran && (
        <div className="mp-results" ref={resultsRef}>
          <aside className="mp-side">
            <div className="mp-side-h">View</div>
            <div className="mp-seg">
              <button type="button" className={settings.view === 'cards' ? 'mp-on' : ''} onClick={() => set({ view: 'cards' })}>Cards</button>
              <button type="button" className={settings.view === 'chart' ? 'mp-on' : ''} onClick={() => set({ view: 'chart' })}>Chart</button>
            </div>
            <div className="mp-side-h">Sort</div>
            <div className="mp-seg">
              <button type="button" className={settings.sort === 'price' ? 'mp-on' : ''} onClick={() => set({ sort: 'price' })}>Cheapest</button>
              <button type="button" className={settings.sort === 'voices' ? 'mp-on' : ''} onClick={() => set({ sort: 'voices' })}>Most voices</button>
            </div>
            <label className="mp-field">Minimum voices
              <select value={settings.minV} onChange={(e) => { set({ minV: Number(e.target.value) }); setAxesShown(6) }}>
                {[0, 2, 3, 5, 10].map((v) => <option key={v} value={v}>{v ? `${v}+` : 'Any'}</option>)}
              </select>
            </label>
            <label className="mp-check"><input type="checkbox" checked={settings.problems} onChange={(e) => set({ problems: e.target.checked })} /> Show reported not working</label>
            {ran.model && <label className="mp-check"><input type="checkbox" checked={settings.cheaper} onChange={(e) => set({ cheaper: e.target.checked })} /> Cheaper only</label>}
            {ran.model && !KINDS.some((k) => ran[k]) && (
              <>
                <div className="mp-side-h" style={{ marginTop: 14 }}>Reported on</div>
                <div className="mp-seg mp-seg-col">
                  {['all', ...KINDS].map((k) => (
                    <button type="button" key={k} className={settings.kind === k ? 'mp-on' : ''} onClick={() => { set({ kind: k }); setAxesShown(6) }}>
                      {{ all: 'Everything', job: 'Jobs', capability: 'Capabilities', metric: 'Metrics' }[k]}
                    </button>
                  ))}
                </div>
              </>
            )}
            <div className="mp-legend">
              <span><i className="mp-pos" />positive</span><span><i className="mp-neg" />negative</span><span><i className="mp-neu" />neutral</span>
              <span className="mp-dim">The number in a donut is its reports</span>
              <span className="mp-dim">Prices are advertised input per 1M tokens</span>
            </div>
            <button type="button" className="mp-textbtn" disabled={!settingsChanged}
                    onClick={() => { setSettings({ ...DEFAULTS, cheaper: !!ran.model }); setAxesShown(6); setOpen(new Set()) }}>↺ Reset settings</button>
            <div className="mp-side-links">
              <Link to="/token-counter">Price your own prompt →</Link>
              <Link to="/model-finder">Filter by specs →</Link>
            </div>
          </aside>
          <div className="mp-main">
            {ran.model
              ? (idx.byId.get(ran.model.id) ? <ModelResults r={idx.byId.get(ran.model.id)} F={ran} /> : <div className="mp-none">That model is not on the board.</div>)
              : (ran.job || ran.capability || ran.metric) ? <AxisResults F={ran} />
                : <BudgetResults b={bandOf(ran)} />}
          </div>
        </div>
      )}

      {idx && !ran && (
        <div className="mp-empty">
          <b>Pick what to start from, choose an option, then press Find.</b>
          <span>Add more filters to narrow it down, or try one of the examples above.</span>
        </div>
      )}

      <section className="mp-how">
        <div><h4>Counts, not quotes</h4><p>Every card is a count of distinct engineers (voices) and source documents (reports) from public posts, with no quote, link or author shown. Some sources are collected for research but not counted here.</p></div>
        <div><h4>You choose how much evidence</h4><p>Minimum voices starts at 3 different people. Set it to &quot;Any&quot; to see everything: results from one or two people are tagged <span className="mp-thin">thin evidence</span>, and a single report gets no chart, because one experience is an anecdote, not a consensus.</p></div>
        <div><h4>Working and problems, both shown</h4><p>Models are grouped by what their reports say: working, mixed, not working, or no side taken. A cheaper model with problem reports is shown as such, never as an alternative.</p></div>
        <div><h4>Prices are advertised</h4><p>Input prices per million tokens are what providers publish, from our registry. A model with no published price shows &quot;—&quot;, never $0.</p></div>
      </section>

      {cmpModels.length > 0 && (
        <div className="mp-tray" role="region" aria-label="Compare tray">
          <span className="mp-tray-lab">Compare ({cmpModels.length}/{COMPARE_MAX})</span>
          {cmpModels.map((r) => (
            <span key={r.key} className="mp-tray-chip">{shortName(r)}
              <button type="button" aria-label={`Remove ${shortName(r)}`} onClick={() => cmp.toggle(modelId(r))}>✕</button>
            </span>
          ))}
          <button type="button" className="mp-textbtn" onClick={() => setCmpIds([])}>Clear</button>
          <button type="button" className="mp-find" disabled={cmpModels.length < 2}
                  onClick={() => navigate(`/compare?ids=${encodeURIComponent(cmpModels.map(modelId).join(','))}&from=reports`)}>
            {cmpModels.length < 2 ? 'Tick one more to compare' : 'Compare →'}
          </button>
        </div>
      )}
    </div>
  )
}
