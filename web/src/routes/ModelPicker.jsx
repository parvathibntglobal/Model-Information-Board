import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { reportsPage, listRegistry, fetchAll, BoardUnreadable } from '../api'
import { Notice, Unreadable } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { useHead } from '../seo/head'
import { modelPicker, pickerAlternatives, pickerJob } from '../seo/pages'
import { comparePath, isReadable, resolveSlugs, slugOf } from '../compare/path'
import Freshness from '../components/Freshness'
import NotFound from '../components/NotFound'

/**
 * BEST AI MODEL PICKER (2026-10-14), from model-alternatives-demo.html: the
 * best model for a job and cheaper alternatives to a model, in one tool. The
 * top of the page follows the agreed layout (a sentence to fill in, the four
 * start-from chips, one search box, examples); the results keep every filter.
 *
 * TWO SOURCES, KEPT APART. The evidence is `/reviews` (judge/reports.py): the
 * board's counts over the PUBLIC view, never a quote, link or author. Prices
 * are the registry's (`/models`): what providers ADVERTISE, never evidence, and
 * a model with no published price shows "—", never $0.
 *
 * NOTHING IS A SCORE. Phrases are a fixed rule over the counts (`phrase`),
 * groups are by what the reports say, "saves $x" is arithmetic on two
 * advertised prices, and the short answer's picks are each one stated rule
 * over the counts ("most positive reports", "cheapest reported working",
 * "most people"), never a blend - and only among models reported working.
 *
 * NO METRICS. A metric is a figure - a price, a speed, a score - and polarity
 * is not enough to read one; its figures need their quotes, which this
 * counts-only tool never shows. Metrics stay on the AI models pages.
 *
 * THE ADDRESS HOLDS THE SEARCH (`?model=&job=&capability=&price=` and the
 * compare picks as `&cmp=`), so a result can be sent to somebody and opens as
 * they saw it.
 *
 * ONE JOB ALONE IS A PAGE OF ITS OWN (2026-10-21): `/best-ai-model/coding-agent`,
 * with its own title, heading and canonical - "best AI model for coding
 * agents" is what people search, and under `?job=` every job shared the
 * picker's one title and canonical, so none could be listed. Any other mix of
 * filters stays in the query. `?job=x` on its own moves to the path.
 *
 * SO IS ONE MODEL'S ALTERNATIVES (2026-10-21): `/alternatives/gpt-6-astra` -
 * "gpt-6 astra alternatives" is the search. The model is named by the part of
 * its id after the provider, as a comparison is (compare/path.js), or by
 * `provider--model` if two providers share that name. The model the picker puts
 * in the compare tray by itself is not repeated in the address (`cmp=`). Its
 * heading stays the picker's (her call, 2026-10-21): the title and the results'
 * own heading ("Alternatives to ...") name the model.
 *
 * A GROUP READS AS `?job-group=software-development` or
 * `?capability-group=instruction-and-reliability`. Its id is `parent:<group>`,
 * which came out as `?capability=parent%3A...` and, for a job group, as
 * `/best-ai-model/parent%3A...`; both still open. A group is a reading aid over
 * its jobs, never a page of its own, so it is never the job address.
 */
const GROUP = 'parent:'


const COMPARE_MAX = 3
const THIN = 3
const STALE_DAYS = 90
const KINDS = ['job', 'capability']
const KIND_LABEL = { job: 'job', capability: 'capability' }
const KIND_ORDER = { job: 0, capability: 1 }
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
const DEFAULTS = { sort: 'price', minV: 3, problems: true, kind: 'all', view: 'cards' }
const VIEWS = [['cards', 'Cards'], ['chart', 'Chart']]

// ── icons for the start-from chips and the feature row ───────────────────────
const svg = (d) => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{d}</svg>
)
const ICON = {
  model: svg(<><path d="M12 2 3 7v10l9 5 9-5V7z" /><path d="M3 7l9 5 9-5M12 12v10" /></>),
  job: svg(<><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18" /></>),
  capability: svg(<><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" /></>),
  price: svg(<><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" /></>),
  info: svg(<><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8v.5" /></>),
  filter: svg(<path d="M3 5h18l-7 8.5V19l-4 2v-7.5z" />),
  shield: svg(<><path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z" /><path d="m9 12 2 2 4-4" /></>),
  bars: svg(<><path d="M5 20V12M12 20V6M19 20v-9" /></>),
  tag: svg(<><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z" /><circle cx="7.5" cy="7.5" r="1.5" /></>),
}

/** One part of the example query, in the colour and icon of its chip. */
const Token = ({ t, children }) => (
  <span className={`mp-tok mp-tok-${t}`}><span className="mp-tok-ic">{ICON[t]}</span><em>{TYPE[t].label}</em>{children}</span>
)

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
/** "5 people · 2 platforms": how much evidence, in words a reader weighs. */
const peopleText = (m) => {
  const who = m.voices ? plural(m.voices, 'person', 'people') : `${plural(m.reports, 'report')}, author not identified`
  return m.platforms ? `${who} · ${plural(m.platforms, 'platform')}` : who
}
const splitTitle = (s, newest) => `${s.positive} positive · ${s.negative} negative · ${s.neutral} neutral${s.both ? ` · ${s.both} said both` : ''}${newest ? ` · newest report ${newest}` : ''}`
/** A muted note when the newest report is old, so old evidence never reads as current. */
function staleText(newest) {
  if (!newest) return null
  const days = (Date.now() - Date.parse(`${newest}T00:00:00Z`)) / 864e5
  if (!(days > STALE_DAYS)) return null
  const months = Math.round(days / 30)
  return `newest report ${months < 12 ? plural(months, 'month') : plural(Math.round(months / 12), 'year')} ago`
}

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
const Badge = ({ ph }) => <span className={`mp-badge mp-b-${ph.c}`}><i />{ph.t}</span>
const Counts = ({ s }) => (
  <span className="mp-counts" title="positive · negative · neutral reports">
    <b className="mp-p">{s.positive}</b> · <b className="mp-ng">{s.negative}</b> · <b className="mp-u">{s.neutral}</b>
  </span>
)

/** The split as a small donut, the report count in the middle; a 2px gap
 *  separates the parts so a thin slice still reads. One report gets none. */
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
      <title>{splitTitle(s)}</title>
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

const CompareBox = ({ id, cmp, label }) => {
  const on = cmp.has(id)
  return (
    <label className="mp-cmp">
      <input type="checkbox" checked={on} disabled={!on && cmp.size >= COMPARE_MAX} onChange={() => cmp.toggle(id)} aria-label={label} />
      {label ? null : 'Compare'}
    </label>
  )
}

/** One model on one job or capability: the verdict, the price, the donut and
 *  how many people. Exact counts and dates are in the hover; "Also reported
 *  working on" says why it is worth a look beyond this one item. */
function ModelCard({ m, refPrice, price, cmp, why }) {
  const ph = phrase(m.split)
  const id = modelId(m)
  const saves = ph.c === 'working' && refPrice != null && price != null && price < refPrice ? refPrice - price : null
  const stale = staleText(m.newest)
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
      <div className="mp-card-mid" title={splitTitle(m.split, m.newest)}>
        <Donut m={m} />
        <div className="mp-card-facts">
          <div className="mp-people">{peopleText(m)}</div>
          {m.voices < THIN && <span className="mp-thin">thin evidence</span>}
          {stale && <div className="mp-stale">{stale}</div>}
        </div>
      </div>
      {why && why.length > 0 && (
        <div className="mp-why">Also reported working on {why.map((w, i) => <span key={w}>{i ? ', ' : ''}<b>{w}</b></span>)}</div>
      )}
      {saves != null && <div className="mp-save">↓ saves {rate(saves)} per 1M input</div>}
      <div className="mp-card-foot">
        <span className="mp-actions">
          <Link to={`/reviews/models/${id}`} className="mp-link">Model page</Link>
          <CompareBox id={id} cmp={cmp} />
        </span>
      </div>
    </div>
  )
}

/** THE CHART VIEW of one group: negative reports left of the line, positive
 *  right, every row on ONE scale. Neutral is a count beside it, not a bar. */
function GroupChart({ ms, refPrice, priceOf, cmp }) {
  const scale = Math.max(1, ...ms.map((m) => Math.max(m.split.positive, m.split.negative)))
  return (
    <div className="mp-chart" role="table" aria-label="Positive and negative reports per model">
      <div className="mp-chart-h" role="row">
        <span>Model</span><span>Price /1M in</span>
        <span className="mp-chart-axis"><em className="mp-ng">← negative</em><em className="mp-p">positive →</em></span>
        <span>Neutral · people</span><span />
      </div>
      {ms.map((m) => {
        const s = m.split, id = modelId(m), price = priceOf(m)
        // 40% each side leaves room for the count beside the longest bar
        const wn = (40 * s.negative) / scale, wp = (40 * s.positive) / scale
        const ph = phrase(s)
        const saves = ph.c === 'working' && refPrice != null && price != null && price < refPrice
        return (
          <div className="mp-chart-row" role="row" key={m.key} title={`${ph.t} · ${splitTitle(s, m.newest)}`}>
            <span className="mp-chart-name"><small>{providerOf(m)}</small>{shortName(m)}{m.voices < THIN && <span className="mp-thin">thin</span>}</span>
            <span className={`mp-chart-price${saves ? ' mp-save' : ''}`}>{rate(price)}</span>
            <span className="mp-div">
              <i className="mp-div-mid" />
              {s.negative > 0 && <i className="mp-div-neg" style={{ width: `${wn}%` }} />}
              {s.positive > 0 && <i className="mp-div-pos" style={{ width: `${wp}%` }} />}
              <b style={{ right: `calc(50% + ${wn}% + 5px)` }}>{s.negative}</b>
              <b style={{ left: `calc(50% + ${wp}% + 5px)` }}>{s.positive}</b>
            </span>
            <span className="mp-chart-side">{s.neutral} · {m.voices || '—'}</span>
            <CompareBox id={id} cmp={cmp} label={`Compare ${shortName(m)}`} />
          </div>
        )
      })}
    </div>
  )
}

/** Cards grouped by what the reports say. The first group is open; the weaker
 *  ones are one-line headers until opened. Three cards per group until asked. */
function Grouped({ list, refPrice, priceOf, cmp, settings, labelFor, openKey, open, toggleOpen, whyFor, empty }) {
  const visible = list.filter((m) => m.voices >= settings.minV && (settings.problems || phrase(m.split).c !== 'problems'))
  const present = GROUPS.filter((g) => g.id !== 'problems' || settings.problems)
    .map((g) => ({ g, ms: visible.filter((m) => phrase(m.split).c === g.id) }))
    .filter((x) => x.ms.length)
  if (!present.length) return empty || null
  const [lead, ...rest] = present
  const keyOf = (g) => openKey + g.id
  const label = (g) => (labelFor ? labelFor(g) : g.label)
  const body = (g, ms) => {
    const shown = open.has(keyOf(g)) ? ms : ms.slice(0, 3)
    return settings.view === 'chart'
      ? <GroupChart ms={shown} refPrice={refPrice} priceOf={priceOf} cmp={cmp} />
      : (
        <div className="mp-cards">
          {shown.map((m) => <ModelCard key={m.key} m={m} refPrice={refPrice} price={priceOf(m)} cmp={cmp} why={whyFor ? whyFor(m) : null} />)}
        </div>
      )
  }
  const showAll = (g, ms) => ms.length > 3 && (
    <button type="button" className="mp-more" onClick={() => toggleOpen(keyOf(g))}>{open.has(keyOf(g)) ? 'Show fewer' : `Show all ${ms.length}`}</button>
  )
  const leadOpen = !open.has(`${keyOf(lead.g)}:closed`)
  const restOpen = (g) => open.has(`${keyOf(g)}:open`)
  // THE OTHER GROUPS SIT ON THE SAME LINE AS "Show all", as one-line pills; an
  // opened one shows its cards below that line.
  return (
    <div className="mp-group">
      <button type="button" className={`mp-group-h mp-gh-${lead.g.id}`} aria-expanded={leadOpen} onClick={() => toggleOpen(`${keyOf(lead.g)}:closed`)}>
        <span className="mp-dot" style={{ background: lead.g.colour }} />{label(lead.g)}<span className="mp-n">{lead.ms.length}</span>
        <span className="mp-caret-s" aria-hidden="true">{leadOpen ? '▾' : '▸'}</span>
      </button>
      {leadOpen && body(lead.g, lead.ms)}
      <div className="mp-group-row">
        {leadOpen && showAll(lead.g, lead.ms)}
        {rest.map(({ g, ms }) => (
          <button type="button" key={g.id} className={`mp-group-h mp-gh-${g.id}${restOpen(g) ? ' mp-gh-on' : ''}`} aria-expanded={restOpen(g)} onClick={() => toggleOpen(`${keyOf(g)}:open`)}>
            <span className="mp-dot" style={{ background: g.colour }} />{label(g)}<span className="mp-n">{ms.length}</span>
            <span className="mp-caret-s" aria-hidden="true">{restOpen(g) ? '▾' : '▸'}</span>
          </button>
        ))}
      </div>
      {rest.filter(({ g }) => restOpen(g)).map(({ g, ms }) => (
        <div key={g.id} className="mp-group-more">
          <div className={`mp-group-sub mp-gh-${g.id}`}><span className="mp-dot" style={{ background: g.colour }} />{label(g)}</div>
          {body(g, ms)}
          {showAll(g, ms)}
        </div>
      ))}
    </div>
  )
}

/** THE SHORT ANSWER: up to three picks among models reported working, each
 *  from ONE rule over the counts. A model that wins twice shows once. */
function TopPicks({ cands, priceOf, cmp, minV }) {
  const working = cands.filter((c) => c.m.voices >= minV && phrase(c.m.split).c === 'working')
  const picks = []
  const add = (c, label, why) => {
    if (!c) return
    const hit = picks.find((x) => x.c.m.key === c.m.key)
    if (hit) hit.labels.push(label)
    else picks.push({ c, labels: [label], why })
  }
  add([...working].sort((a, b) => b.m.split.positive - a.m.split.positive || b.m.voices - a.m.voices)[0], 'Most reported working',
    (c) => `${plural(c.m.split.positive, 'positive report')}${c.on ? ` on ${c.on}` : ''}`)
  add([...working].filter((c) => priceOf(c.m) != null).sort((a, b) => priceOf(a.m) - priceOf(b.m) || b.m.voices - a.m.voices)[0], 'Cheapest reported working',
    (c) => `${rate(priceOf(c.m))} per 1M input`)
  add([...working].sort((a, b) => b.m.voices - a.m.voices || b.m.reports - a.m.reports)[0], 'Most people reporting', () => null)
  if (!picks.length) return null
  return (
    <section className="mp-picks" aria-label="The short answer">
      <div className="mp-picks-h"><b>The short answer</b><span className="mp-dim">Each pick is one rule over the counts, not a score.</span></div>
      <div className="mp-picks-row">
        {picks.map(({ c, labels, why }) => {
          const id = modelId(c.m)
          return (
            <div key={c.m.key} className="mp-pick">
              <div className="mp-pick-labels">{labels.map((l) => <span key={l} className="mp-pick-label">{l}</span>)}</div>
              <div className="mp-pick-name"><small>{providerOf(c.m)}</small>{shortName(c.m)}</div>
              <div className="mp-pick-line"><Badge ph={phrase(c.m.split)} /><span className="mp-pick-price">{rate(priceOf(c.m))}<small> /1M in</small></span></div>
              <div className="mp-pick-why">{[why(c), peopleText(c.m)].filter(Boolean).join(' · ')}</div>
              <div className="mp-pick-foot">
                <Link to={`/reviews/models/${id}`} className="mp-link">Model page</Link>
                <CompareBox id={id} cmp={cmp} />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

// ── the page ─────────────────────────────────────────────────────────────────
export default function ModelPicker() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const { job: jobPath, model: altPath } = useParams()
  const [sp] = useSearchParams()
  const [data, setData] = useState(null)
  const [registry, setRegistry] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  const [type, setType] = useState('job')
  const [filters, setFilters] = useState({})
  const [ran, setRan] = useState(null)
  const [settings, setSettings] = useState({ ...DEFAULTS, cheaper: true })
  const [axesShown, setAxesShown] = useState(6)
  const [open, setOpen] = useState(new Set())
  const [cmpIds, setCmpIds] = useState([])
  const [q, setQ] = useState('')
  const [listOpen, setListOpen] = useState(false)
  const [act, setAct] = useState(0)
  const [sideOpen, setSideOpen] = useState(false)
  const comboRef = useRef(null)
  const resultsRef = useRef(null)
  const restored = useRef(false)
  // A job or model address that names nothing: 'job' or 'model' (shown as not found, noindex).
  const [missing, setMissing] = useState(null)

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

  // ── index: jobs and capabilities only ──────────────────────────────────────
  const idx = useMemo(() => {
    if (!data) return null
    const axes = data.axes.filter((a) => KINDS.includes(a.kind))
    const models = new Map()
    for (const a of axes) {
      for (const m of a.models) {
        let r = models.get(m.key)
        if (!r) { r = { key: m.key, label: m.label, canonical: m.canonical, axes: [], voices: 0 }; models.set(m.key, r) }
        r.axes.push({ a, m })
        r.voices += m.voices
      }
    }
    const list = [...models.values()].sort((x, y) => y.axes.length - x.axes.length || shortName(x).localeCompare(shortName(y)))
    const byId = new Map(list.map((r) => [modelId(r), r]))
    const members = (kind, pid) => axes.filter((a) => a.kind === kind && a.parent === pid).sort((x, y) => y.models.length - x.models.length)
    const jobs = axes.filter((a) => a.kind === 'job').sort((x, y) => y.voices - x.voices || x.name.localeCompare(y.name))
    return { axes, models, list, byId, members, jobs, parents: data.parents || {} }
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
      return idx.list.map((r) => ({ id: modelId(r), label: shortName(r), pre: providerOf(r), sub: `${plural(r.axes.length, 'job or capability', 'jobs and capabilities')} · ${rate(priceOf(r))} per 1M in` }))
    }
    if (t === 'price') {
      return BANDS.map((b) => ({ id: b.id, label: `${b.label} per 1M input`, pre: 'budget', sub: plural(idx.list.filter((r) => inBand(b, priceOf(r))).length, 'model') }))
    }
    const axes = idx.axes.filter((a) => a.kind === t)
      .sort((x, y) => y.models.length - x.models.length || x.name.localeCompare(y.name))
      .map((a) => ({ id: a.slug, label: a.name, pre: t, sub: `${plural(a.models.length, 'model')} · ${a.voices} voices${a.parent ? ` · ${idx.parents[a.parent] || a.parent}` : ''}` }))
    // GROUPS FIRST, for capabilities: a reading aid, never a merge.
    const groups = Object.entries(idx.parents)
      .map(([pid, name]) => ({ pid, name, n: idx.members(t, pid).length }))
      .filter((g) => g.n > 1)
      .map((g) => ({ id: `parent:${g.pid}`, label: g.name, pre: 'group', sub: `${g.n} ${t === 'job' ? 'jobs' : 'capabilities'}, shown separately` }))
    return groups.concat(axes)
  }
  const shownOpts = useMemo(() => {
    const ql = q.trim().toLowerCase()
    return optionsFor(type).filter((o) => !ql || `${o.label} ${o.pre}`.toLowerCase().includes(ql)).slice(0, 60)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, q, idx, prices])

  // ── the search (and the compare picks) in the address ──────────────────────
  const labelFor = (t, id) => (optionsFor(t).find((o) => o.id === id) || {}).label
  useEffect(() => {
    if (!idx || restored.current) return
    restored.current = true
    const f = {}
    const altId = altPath ? resolveSlugs([altPath], idx.list.map((r) => ({ id: modelId(r) }))).ids[0] : null
    const groupOf = (t) => (sp.get(`${t}-group`) ? `${GROUP}${sp.get(`${t}-group`)}` : null)
    for (const t of ORDER) {
      const id = sp.get(t) || { job: jobPath || groupOf('job'), model: altId, capability: groupOf('capability') }[t] || null
      if (id) { const label = labelFor(t, id); if (label) f[t] = { id, label } }
    }
    if (jobPath && !f.job) { setMissing('job'); return }
    if (altPath && !f.model) { setMissing('model'); return }
    const picks = (sp.get('cmp') || '').split(',').filter((id) => idx.byId.has(id)).slice(0, COMPARE_MAX)
    if (picks.length) setCmpIds(picks)
    if (Object.keys(f).length) { setFilters(f); run(f, false, picks) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, registry])
  // ONE WRITER FOR THE ADDRESS: the search and the tray are rebuilt into it
  //   together whenever either changes. Two writes in one moment do not build
  //   on each other in this router, and that dropped `?model=` (2026-10-14).
  //   The tray is in it so opening a model page and coming back keeps it.
  useEffect(() => {
    if (!restored.current) return
    const next = new URLSearchParams()
    const own = jobOnly ? `/best-ai-model/${encodeURIComponent(ran.job.id)}`
      : altOnly ? `/alternatives/${encodeURIComponent(altSlug(ran.model.id))}` : null
    if (own) {
      if (pathname !== own || sp.toString()) navigate(own, { replace: true })
      return
    }
    for (const t of ORDER) {
      if (!ran || !ran[t]) continue
      const id = String(ran[t].id)
      if ((t === 'job' || t === 'capability') && id.startsWith(GROUP)) next.set(`${t}-group`, id.slice(GROUP.length))
      else next.set(t, id)
    }
    // The searched model sits in the tray by itself; the address does not repeat it.
    const onlyTheModel = ran?.model && cmpIds.length === 1 && cmpIds[0] === ran.model.id
    if (cmpIds.length && !onlyTheModel) next.set('cmp', cmpIds.join(','))
    if (pathname !== '/best-ai-model' || next.toString() !== sp.toString()) {
      navigate(`/best-ai-model${next.toString() ? `?${next}` : ''}`, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ran, cmpIds])

  const has = (f) => ORDER.some((k) => f && f[k])
  // One job and nothing else: the page /best-ai-model/<job> (see the note at the top).
  const jobOnly = !!(ran && ran.job && !String(ran.job.id).startsWith(GROUP)
    && !ORDER.some((k) => k !== 'job' && ran[k]) && !cmpIds.length)
  // One model and nothing else (the tray holding only it): /alternatives/<model>.
  const altOnly = !!(ran && ran.model && isReadable(ran.model.id) && !ORDER.some((k) => k !== 'model' && ran[k])
    && cmpIds.every((c) => c === ran.model.id))
  // The model's name in its address; `provider--model` if another provider uses the same name.
  const altSlug = (id) => {
    const name = slugOf(id)
    const twins = (idx?.list || []).filter((r) => isReadable(modelId(r)) && slugOf(modelId(r)) === name).length
    return twins > 1 ? id.replace('/', '--') : name
  }
  // A job or model address waits for its item to be known before it names itself.
  useHead(jobOnly ? pickerJob(ran.job)
    : altOnly ? pickerAlternatives({ ...ran.model, slug: altSlug(ran.model.id) })
    : (jobPath || altPath) && !ran ? null : modelPicker())
  function run(f = filters, scroll = true, keepCmp = cmpIds) {
    if (!has(f)) { setRan(null); return }
    const firstOfKind = !ran || !!ran.model !== !!f.model
    setRan(JSON.parse(JSON.stringify(f)))
    setAxesShown(6)
    setOpen(new Set())
    if (firstOfKind) setSettings((s) => ({ ...s, kind: 'all', cheaper: !!f.model }))
    if (f.model && !keepCmp.includes(f.model.id)) setCmpIds((c) => [f.model.id, ...c.filter((x) => x !== f.model.id)].slice(0, COMPARE_MAX))
    if (scroll) setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }
  /** RESULTS FOLLOW THE FILTERS: picking or dropping one updates at once
   *  (Find stays, for a keyboard reader who types and presses Enter). */
  const applyFilters = (f) => { setFilters(f); run(f, !ran) }
  const setFilter = (t, opt) => {
    const f = { ...filters }
    if (opt) f[t] = { id: opt.id, label: opt.label }
    else delete f[t]
    applyFilters(f)
  }
  const choose = (o) => {
    setQ('')
    setListOpen(false)
    setFilter(type, o)
  }
  const removeFilter = (t) => setFilter(t, null)
  const clearAll = () => { setFilters({}); setRan(null) }
  const tryExample = (f) => { setType(Object.keys(f)[0]); applyFilters(f) }

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
      else { const a = idx.axes.find((x) => x.kind === k && x.slug === f.id); if (a) out.push({ a, group: null }) }
    }
    return out
  }
  const openAxis = (a) => { setType(a.kind); applyFilters({ ...filters, [a.kind]: { id: a.slug, label: a.name } }) }
  const openGroup = (kind, pid) => { setType(kind); applyFilters({ ...filters, [kind]: { id: `parent:${pid}`, label: idx.parents[pid] || pid } }) }
  /** "Also reported working on": the model's other jobs and capabilities with
   *  enough people reporting it working - the reason to look beyond this one. */
  const whyFor = (skipKind, skipSlug) => (m) => {
    const r = idx.models.get(m.key)
    if (!r) return []
    return r.axes
      .filter(({ a, m: x }) => !(a.kind === skipKind && a.slug === skipSlug) && x.voices >= Math.max(1, settings.minV) && phrase(x.split).c === 'working')
      .sort((p, q2) => q2.m.voices - p.m.voices)
      .slice(0, 2)
      .map(({ a }) => a.name)
  }

  /** WHEN NOTHING SHOWS, OFFER THE STEP THAT WOULD SHOW SOMETHING. */
  function Relax({ children }) {
    const steps = []
    if (settings.minV > 0) steps.push(['Show any number of voices', () => set({ minV: 0 })])
    if (ran?.model && settings.cheaper) steps.push(['Include pricier models', () => set({ cheaper: false })])
    if (!settings.problems) steps.push(['Show reported not working', () => set({ problems: true })])
    if (ran?.price) steps.push(['Remove the budget', () => removeFilter('price')])
    return (
      <div className="mp-none">
        {children}
        {steps.length > 0 && <div className="mp-relax">{steps.map(([label, go]) => <button type="button" key={label} className="mp-chip mp-chip-go" onClick={go}>{label}</button>)}</div>}
      </div>
    )
  }

  /** THE ACTIVE FILTERS, above the results, each removable in one click. */
  function ActiveChips() {
    const chips = []
    for (const t of ORDER) if (ran[t]) chips.push({ key: t, label: `${TYPE[t].label}: ${ran[t].label}`, drop: () => removeFilter(t) })
    if (settings.minV > 0) chips.push({ key: 'minV', label: `${settings.minV}+ voices`, drop: () => set({ minV: 0 }) })
    if (ran.model && settings.cheaper) chips.push({ key: 'cheaper', label: 'Cheaper only', drop: () => set({ cheaper: false }) })
    if (!settings.problems) chips.push({ key: 'problems', label: 'Hiding not working', drop: () => set({ problems: true }) })
    if (settings.kind !== 'all') chips.push({ key: 'kind', label: `${{ job: 'Jobs', capability: 'Capabilities' }[settings.kind]} only`, drop: () => set({ kind: 'all' }) })
    return (
      <div className="mp-active" aria-label="Active filters">
        {chips.map((c) => (
          <span key={c.key} className="mp-tag">{c.label}<button type="button" aria-label={`Remove ${c.label}`} onClick={c.drop}>✕</button></span>
        ))}
      </div>
    )
  }

  /** ONE JOB OR CAPABILITY AS A COLLAPSIBLE PANEL: its icon, name and what
   *  counts as a report, with how many models show and a toggle. Open by
   *  default; the state lives with the page so it survives a re-render. */
  const panel = ({ a, group, count, children, sub }) => {
    const key = `panel:${a.kind}${a.slug}:closed`
    const isOpen = !open.has(key)
    return (
      <section key={a.kind + a.slug} className={`mp-panel${isOpen ? '' : ' mp-panel-closed'}`}>
        <button type="button" className="mp-panel-h" aria-expanded={isOpen} onClick={() => toggleOpen(key)}>
          <span className="mp-panel-ic">{ICON[a.kind]}</span>
          <span className="mp-panel-t">
            <b>{a.name}</b>
            <small>{KIND_LABEL[a.kind]}{group ? ` · in ${group}` : ''}{sub ? ` · ${sub}` : a.definition ? ` · ${a.definition}` : ''}</small>
          </span>
          <span className="mp-panel-n">{plural(count, 'model')}</span>
          <span className="mp-panel-caret" aria-hidden="true">{isOpen ? '▴' : '▾'}</span>
        </button>
        {isOpen && <div className="mp-panel-body">{children}</div>}
      </section>
    )
  }
  const visibleCount = (list) => list.filter((m) => m.voices >= settings.minV && (settings.problems || phrase(m.split).c !== 'problems')).length

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
    const mine = priceOf(r), priceBand = bandOf(F), sel = selectedAxes(F)
    let rows = sel.length
      ? sel.map(({ a, group }) => ({ a, group, m: a.models.find((x) => x.key === r.key) || null }))
      : r.axes.filter(({ a }) => settings.kind === 'all' || a.kind === settings.kind).map(({ a, m }) => ({ a, m, group: null }))
    rows = rows.filter(({ m }) => sel.length || (m && m.voices >= settings.minV))
      .sort((x, y) => (KIND_ORDER[x.a.kind] - KIND_ORDER[y.a.kind]) || ((y.m ? y.m.voices : 0) - (x.m ? x.m.voices : 0)) || y.a.models.length - x.a.models.length)
    const othersOf = (a) => {
      let others = a.models.filter((x) => x.key !== r.key && (!priceBand || inBand(priceBand, priceOf(x))))
      if (settings.cheaper && mine != null) others = others.filter((x) => priceOf(x) != null && priceOf(x) < mine)
      return [...others].sort(sorter)
    }
    // the short answer looks across EVERY row, not just the ones on screen
    const cands = rows.flatMap(({ a }) => othersOf(a).map((m) => ({ m, on: a.name })))
    const total = rows.length
    rows = rows.slice(0, axesShown)
    return (
      <>
        <div className="mp-res-head">
          <h2>Alternatives to {shortName(r)}</h2>
          <p>{providerOf(r)} · {rate(mine)} per 1M input · reported on {plural(r.axes.length, 'job or capability', 'jobs and capabilities')}{priceBand ? ` · showing models priced ${priceBand.label} per 1M input` : ''}</p>
        </div>
        <ActiveChips />
        <TopPicks cands={cands} priceOf={priceOf} cmp={cmp} minV={settings.minV} />
        {!rows.length && <Relax>Nothing of this kind is reported for this model from {settings.minV}+ people yet.</Relax>}
        {rows.map(({ a, m, group }) => {
          const others = othersOf(a)
          const cheap = settings.cheaper ? ', and cheaper' : ''
          const ph = m ? phrase(m.split) : null
          const empty = <Relax>No {settings.cheaper ? 'cheaper ' : ''}model{priceBand ? ' in this price range' : ''} has reports on this{settings.minV > 0 ? ` from ${settings.minV}+ people` : ''} yet.</Relax>
          return panel({ a, group, count: visibleCount(others), children: (
            <>
              {!group && <ParentNav a={a} />}
              <div className="mp-self">
                {m ? (
                  <>
                    <b>{shortName(r)}</b>
                    <span className={`mp-phrase mp-ph-${ph.c}`} style={{ margin: 0 }}>{ph.t}</span>
                    <span style={{ minWidth: 120, flex: '0 1 160px' }}><SplitBar m={m} /></span>
                    <span>{peopleText(m)}</span><Counts s={m.split} />
                    {m.voices < THIN && <span className="mp-thin">thin evidence</span>}
                  </>
                ) : <><b>{shortName(r)}</b><span className="mp-dim">no reports on this yet</span></>}
              </div>
              {others.length ? (
                <Grouped list={others} refPrice={mine} priceOf={priceOf} cmp={cmp} settings={settings}
                         openKey={a.kind + a.slug} open={open} toggleOpen={toggleOpen} whyFor={whyFor(a.kind, a.slug)} empty={empty}
                         labelFor={(g) => (g.id === 'working' ? `Also reported working on this${cheap}`
                           : g.id === 'problems' ? `Reported not working on this${cheap}` : g.label)} />
              ) : empty}
            </>
          ) })
        })}
        {total > axesShown && <div className="mp-center"><button type="button" className="mp-more" onClick={() => setAxesShown((n) => n + 6)}>Show more ({total - axesShown} of {total} left)</button></div>}
      </>
    )
  }

  function AxisResults({ F }) {
    const priceBand = bandOf(F), sel = selectedAxes(F)
    const inB = (m) => !priceBand || inBand(priceBand, priceOf(m))
    const plain = sel.filter((x) => !x.group)
    const groups = [...new Set(sel.map((x) => x.group).filter(Boolean))]
    // A model qualifies for "all of them" when its reports say it works on EVERY
    // selected item, each from enough people. Counts stay per item.
    const all = plain.length >= 2
      ? idx.list.filter((r) => inB(r) && plain.every(({ a }) => { const m = a.models.find((x) => x.key === r.key); return m && m.voices >= settings.minV && phrase(m.split).c === 'working' }))
        .sort(settings.sort === 'price' ? (x, y) => (priceOf(x) ?? 1e9) - (priceOf(y) ?? 1e9) : (x, y) => y.voices - x.voices)
      : null
    const names = ORDER.filter((k) => F[k] && k !== 'model').map((k) => F[k].label)
    // the short answer: from "all of them" when there is such a list, else the first item
    const lead = sel[0]?.a
    const cands = all && all.length
      ? all.map((r) => ({ m: plain[0].a.models.find((x) => x.key === r.key), on: plain[0].a.name }))
      : lead ? lead.models.filter(inB).map((m) => ({ m, on: lead.name })) : []
    return (
      <>
        <div className="mp-res-head">
          <h2>Models for {names.join(' · ')}</h2>
          <p>{sel.length === 1 ? `One ${sel[0].a.kind}` : `${sel.length} jobs or capabilities`} selected{priceBand ? ` · models priced ${priceBand.label} per 1M input` : ''}</p>
        </div>
        <ActiveChips />
        <TopPicks cands={cands} priceOf={priceOf} cmp={cmp} minV={settings.minV} />
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
                    <div className="mp-card-head">
                      <Badge ph={{ c: 'working', t: 'Working on all of them' }} />
                      <span className="mp-price">{rate(priceOf(r))}<small> /1M in</small></span>
                    </div>
                    <div><div className="mp-prov">{providerOf(r)}</div><div className="mp-name">{shortName(r)}</div></div>
                    <div className="mp-meta" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
                      {plain.map(({ a }) => { const m = a.models.find((x) => x.key === r.key); return <span key={a.slug}>{a.name}: {peopleText(m)} · <Counts s={m.split} /></span> })}
                    </div>
                    <div className="mp-card-foot">
                      <span className="mp-actions">
                        <Link to={`/reviews/models/${modelId(r)}`} className="mp-link">Model page</Link>
                        <CompareBox id={modelId(r)} cmp={cmp} />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : <Relax>No model{priceBand ? ' in this price range' : ''} is reported working on all of them by {settings.minV || 1}+ people yet.</Relax>}
          </section>
        )}
        {sel.slice(0, axesShown).map(({ a, group }) => {
          const list = a.models.filter(inB).sort(sorter)
          const empty = <Relax>No model{priceBand ? ' in this price range' : ''} has reports from {settings.minV}+ people here yet.</Relax>
          return panel({ a, group, count: visibleCount(list), children: (
            <>
              {!group && <ParentNav a={a} />}
              <Grouped list={list} priceOf={priceOf} cmp={cmp} settings={settings} openKey={a.kind + a.slug} open={open} toggleOpen={toggleOpen}
                       whyFor={whyFor(a.kind, a.slug)} empty={empty} />
            </>
          ) })
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
    // each model's best-supported working item, for the short answer
    const cands = ms.map((r) => {
      const best = [...r.axes].sort((x, y) => y.m.split.positive - x.m.split.positive || y.m.voices - x.m.voices)[0]
      return best ? { m: best.m, on: best.a.name } : null
    }).filter(Boolean)
    const chip = ({ a, m }) => {
      const ph = phrase(m.split)
      return (
        <button type="button" key={a.kind + a.slug} className={`mp-chip mp-axc mp-g-${ph.c}`} onClick={() => openAxis(a)}
                title={`${ph.t} · ${peopleText(m)} · ${splitTitle(m.split)}`}>
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
        <ActiveChips />
        <TopPicks cands={cands} priceOf={priceOf} cmp={cmp} minV={settings.minV} />
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
                  <div className="mp-card-head">
                    <div><div className="mp-prov">{providerOf(r)}</div><div className="mp-name">{shortName(r)}</div></div>
                    <span className="mp-price">{rate(priceOf(r))}<small> /1M in</small></span>
                  </div>
                  <div className="mp-group-h mp-gh-working" style={{ marginTop: 6 }}><span className="mp-dot" style={{ background: 'var(--mp-good)' }} />Reported working on<span className="mp-n">{work.length}</span></div>
                  <div className="mp-chips">{work.length ? work.map(chip) : <span className="mp-dim">Nothing yet</span>}</div>
                  {settings.problems && bad.length > 0 && (
                    <>
                      <div className="mp-group-h mp-gh-problems"><span className="mp-dot" style={{ background: 'var(--mp-bad)' }} />Reported not working on<span className="mp-n">{bad.length}</span></div>
                      <div className="mp-chips">{bad.map(chip)}</div>
                    </>
                  )}
                  {other.length > 0 && (
                    <>
                      <div className="mp-group-h mp-gh-mixed"><span className="mp-dot" style={{ background: 'var(--mp-mixed)' }} />Mixed or no side taken<span className="mp-n">{other.length}</span></div>
                      <div className="mp-chips">{other.map(chip)}</div>
                    </>
                  )}
                  <div className="mp-card-foot">
                    <span className="mp-actions">
                      <Link to={`/reviews/models/${id}`} className="mp-link">Model page</Link>
                      <CompareBox id={id} cmp={cmp} />
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : <Relax>No model in this range has reports from {settings.minV}+ people yet.</Relax>}
        <p className="mp-def" style={{ marginTop: 12 }}>
          Numbers on the chips are people reporting; hover one for its positive / negative / neutral counts, click it to see every model for it.
          {hidden > 0 && ` ${plural(hidden, 'more model is', 'more models are')} in this range with fewer than ${settings.minV} voices on everything.`}
        </p>
      </>
    )
  }

  // ── examples, from what the board holds ────────────────────────────────────
  const examples = useMemo(() => {
    if (!idx) return []
    const top = idx.list[0]
    const job = idx.jobs[0]
    const cap = idx.axes.filter((a) => a.kind === 'capability').sort((x, y) => y.voices - x.voices)[0]
    const out = []
    if (top) out.push({ label: `Alternatives to ${shortName(top)}`, f: { model: { id: modelId(top), label: shortName(top) } } })
    if (job) out.push({ label: `Models for ${job.name.toLowerCase()}`, f: { job: { id: job.slug, label: job.name } } })
    out.push({ label: 'Models at $0.10 – $0.50', f: { price: { id: 'b1', label: '$0.10 – $0.50 per 1M input' } } })
    if (job && cap) out.push({ label: `${job.name} + ${cap.name.toLowerCase()}`, f: { job: { id: job.slug, label: job.name }, capability: { id: cap.slug, label: cap.name } } })
    return out
  }, [idx])

  const exampleQuery = useMemo(() => {
    if (!idx || !idx.jobs[0]) return null
    const job = idx.jobs[0]
    const cap = idx.axes.filter((a) => a.kind === 'capability' && a.models.some((m) => job.models.some((x) => x.key === m.key)))
      .sort((x, y) => y.voices - x.voices)[0]
    const top = idx.list.find((r) => (priceOf(r) ?? 0) > 0.5) || idx.list[0]
    const priceBand = BANDS[1]
    const f = { job: { id: job.slug, label: job.name }, price: { id: priceBand.id, label: `${priceBand.label} per 1M input` } }
    if (cap) f.capability = { id: cap.slug, label: cap.name }
    if (top) f.model = { id: modelId(top), label: shortName(top) }
    return { f, job: job.name, cap: cap?.name, priceBand: priceBand.label, model: top ? shortName(top) : null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, prices])
  const cmpModels = cmpIds.map((id) => idx?.byId.get(id)).filter(Boolean)

  // NOT A SOFT 404 (2026-10-21): an unknown /best-ai-model/<job> or
  // /alternatives/<model> said nothing and kept the site's default head.
  if (missing) return <NotFound what={missing} back={{ to: '/best-ai-model', label: 'Open the best AI model picker' }} />

  return (
    <div className={`shell section-tight stack stack-4 mp mp-layout${cmpIds.length ? ' mp-with-tray' : ''}`}>
      <div className="stack stack-1">
        <span className="go-badge go-models page-tag" style={{ alignSelf: 'flex-start' }}>Tools</span>
        {/* ONE HEADING FOR EVERY VIEW (her call, 2026-10-21): a job's or a
            model's page names itself in its title and its results' heading. */}
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Best <span className="mp-accent-text">AI model</span> picker</h1>
        <p className="mp-sub">Find the best AI model for the job, or a cheaper alternative to the one you use.</p>
        <p className="muted" style={{ maxWidth: '78ch', margin: 0 }}>
          Start from the job you need done to find the models engineers reported working for it, or from a model
          you already use to find alternatives that worked as well and cost less. Narrow it by capability or
          budget, and see what each one costs beside the evidence. <Link to="/methodology">How we count reports</Link>.
        </p>
        {!jobOnly && !altOnly && <Freshness style={{ margin: 0 }} />}
      </div>

      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!data && !err && !unreadable && <div className="skel" style={{ height: 220 }} />}

      {idx && (
        <section className="mp-finder">
          <div className="mp-finder-body">
            <div className="mp-types" role="tablist" aria-label="Search by">
              <span className="mp-types-lab">Search by:</span>
              {TYPES.map((t) => (
                <button type="button" key={t.id} role="tab" aria-selected={type === t.id}
                        className={`mp-type${type === t.id ? ' mp-on' : ''}${filters[t.id] ? ' mp-has' : ''}`}
                        onClick={() => { setType(t.id); setQ(''); setListOpen(true); setAct(0) }}>
                  {ICON[t.id]}{t.plural}{filters[t.id] && <span className="mp-tick">✓</span>}
                </button>
              ))}
            </div>
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
              <button type="button" className="mp-find mp-find-accent" disabled={!has(filters)} onClick={() => run()}>
                {filters.model ? 'Find alternatives' : 'Find models'} <span aria-hidden="true">→</span>
              </button>
            </div>

            {has(filters) ? (
              <div className="mp-tags">
                <span className="mp-dim">Filters:</span>
                {ORDER.filter((k) => filters[k]).map((k) => (
                  <span key={k} className="mp-tag"><em>{TYPE[k].label}</em>{filters[k].label}
                    <button type="button" aria-label={`Remove ${TYPE[k].label} filter`} onClick={() => removeFilter(k)}>✕</button>
                  </span>
                ))}
                <button type="button" className="mp-textbtn" onClick={clearAll}>Clear all</button>
              </div>
            ) : (
              <p className="mp-info">{ICON.info}You can combine a task, model, capability and budget in your search.</p>
            )}
            {/* A WORKED EXAMPLE, built from what the board holds: one query with
                each part highlighted in the colour and icon of the chip it comes
                from, so a reader sees how the chips combine. Clicking it runs it. */}
            {exampleQuery && (
              <button type="button" className="mp-example" onClick={() => tryExample(exampleQuery.f)}
                      title="Run this example">
                <span className="mp-sentence-lab">Example: how the chips combine</span>
                <span className="mp-example-text">
                  I need a model for <Token t="job">{exampleQuery.job}</Token>
                  {exampleQuery.cap && <>{' '}good at <Token t="capability">{exampleQuery.cap}</Token></>}
                  {' '}under <Token t="price">{exampleQuery.priceBand}</Token>
                  {exampleQuery.model && <>,{' '}cheaper than <Token t="model">{exampleQuery.model}</Token></>}
                </span>
              </button>
            )}
            <div className="mp-try">
              <span className="mp-dim">Try:</span>
              {examples.map((x) => <button type="button" key={x.label} className="mp-chip" onClick={() => tryExample(x.f)}>{x.label}</button>)}
            </div>
          </div>
        </section>
      )}

      {idx && ran && (
        <div className="mp-results" ref={resultsRef}>
          {/* ON A NARROW SCREEN THE SETTINGS FOLD INTO ONE BUTTON */}
          <button type="button" className="mp-side-toggle" aria-expanded={sideOpen} onClick={() => setSideOpen((o) => !o)}>
            {sideOpen ? 'Hide view and filters ▴' : 'View and filters ▾'}
          </button>
          <aside className={`mp-side mp-side2${sideOpen ? ' mp-side-open' : ''}`} aria-label="Filters">
            <div className="mp-side-top">
              <span>{ICON.filter}Filters</span>
              <button type="button" className="mp-textbtn" disabled={!settingsChanged}
                      onClick={() => { setSettings({ ...DEFAULTS, cheaper: !!ran.model }); setAxesShown(6); setOpen(new Set()) }}>Reset</button>
            </div>
            <fieldset className="mp-fs">
              <legend>View</legend>
              {VIEWS.map(([v, label]) => (
                <label key={v} className="mp-radio"><input type="radio" name="mp-view" checked={settings.view === v} onChange={() => set({ view: v })} />{label}</label>
              ))}
            </fieldset>
            <label className="mp-fs mp-fs-select">
              <span className="mp-fs-l">Sort by</span>
              <select value={settings.sort} onChange={(e) => set({ sort: e.target.value })}>
                <option value="price">Cheapest</option>
                <option value="voices">Most voices</option>
              </select>
            </label>
            <div className="mp-fs">
              <div className="mp-fs-row">
                <span className="mp-fs-l">Minimum voices</span>
                <select value={settings.minV} aria-label="Minimum voices" onChange={(e) => { set({ minV: Number(e.target.value) }); setAxesShown(6) }}>
                  {[0, 2, 3, 5, 10].map((v) => <option key={v} value={v}>{v ? `${v}+` : 'Any'}</option>)}
                </select>
              </div>
              <input type="range" className="mp-range" min="0" max="4" step="1" aria-label="Minimum voices"
                     value={[0, 2, 3, 5, 10].indexOf(settings.minV)}
                     style={{ '--pct': `${([0, 2, 3, 5, 10].indexOf(settings.minV) / 4) * 100}%` }}
                     onChange={(e) => { set({ minV: [0, 2, 3, 5, 10][Number(e.target.value)] }); setAxesShown(6) }} />
            </div>
            <div className="mp-fs">
              <label className="mp-check"><input type="checkbox" checked={settings.problems} onChange={(e) => set({ problems: e.target.checked })} /> Show reported not working</label>
              {ran.model && <label className="mp-check"><input type="checkbox" checked={settings.cheaper} onChange={(e) => set({ cheaper: e.target.checked })} /> Cheaper only</label>}
            </div>
            {ran.model && !KINDS.some((k) => ran[k]) && (
              <fieldset className="mp-fs">
                <legend>Report type</legend>
                {['all', ...KINDS].map((k) => (
                  <label key={k} className="mp-radio"><input type="radio" name="mp-kind" checked={settings.kind === k} onChange={() => { set({ kind: k }); setAxesShown(6) }} />
                    {{ all: 'All', job: 'Jobs', capability: 'Capabilities' }[k]}</label>
                ))}
              </fieldset>
            )}
            <div className="mp-fs">
              <span className="mp-fs-l">Evidence legend</span>
              <ul className="mp-ev-legend">
                <li><i style={{ background: 'var(--mp-good)' }} />Reported working</li>
                <li><i style={{ background: 'var(--mp-mixed)' }} />Mixed reports</li>
                <li><i style={{ background: 'var(--mp-bad)' }} />Reported not working</li>
                <li><i style={{ background: 'var(--mp-neutral)' }} />No side taken</li>
              </ul>
              <span className="mp-dim mp-fs-note">The number in a donut is its reports; prices are advertised input per 1M tokens.</span>
            </div>
            <div className="mp-side-links">
              <a href="#mp-points">{ICON.info} How we collect evidence?</a>
            </div>
          </aside>
          <div className="mp-main">
            {ran.model
              ? (idx.byId.get(ran.model.id) ? <ModelResults r={idx.byId.get(ran.model.id)} F={ran} /> : <div className="mp-none">That model is not on the board.</div>)
              : (ran.job || ran.capability) ? <AxisResults F={ran} />
                : <BudgetResults b={bandOf(ran)} />}
            <details className="mp-why-box">
              <summary>{ICON.info}<b>Why these results?</b></summary>
              <p>We show models from what engineers publicly reported, narrowed by your job, capability, budget and model. Each model is grouped by what its reports say, counted once per person, and shown only with at least {settings.minV || 1} {settings.minV > 1 ? 'people' : 'person'} reporting. Prices are what providers advertise.</p>
            </details>
          </div>
        </div>
      )}

      {idx && !ran && (
        <div className="mp-start">
          <svg className="mp-start-art" width="120" height="76" viewBox="0 0 120 76" fill="none" aria-hidden="true">
            <g stroke="var(--mp-good)" strokeWidth="2" strokeLinecap="round">
              <path d="M14 22h8M10 38h10M14 54h8M98 22h8M100 38h10M98 54h8" opacity=".7" />
              <rect x="34" y="12" width="20" height="20" rx="4" /><rect x="58" y="12" width="20" height="20" rx="4" /><rect x="34" y="36" width="20" height="20" rx="4" />
              <path d="M40 24l4-4 4 4M64 22c3-3 7-3 9 0" />
            </g>
            <g stroke="var(--mp-accent)" strokeWidth="3" strokeLinecap="round"><circle cx="70" cy="48" r="11" /><path d="m78 56 9 9" /></g>
          </svg>
          <b>Start with a <span className="mp-accent-text">task</span>, <span className="mp-accent-text">model</span>, <span className="mp-accent-text">capability</span> or <span className="mp-accent-text">budget</span></b>
          <span>Your matches will appear here as you refine your search.</span>
        </div>
      )}

      <section className="mp-features" id="mp-points">
        <div><span className="mp-feat-ic mp-feat-green">{ICON.shield}</span><div><b>Counts, not quotes</b><p>We count different engineers (voices) and source posts (reports). No quotes, links or authors are shown, and research-only sources aren&apos;t counted.</p></div></div>
        <div><span className="mp-feat-ic mp-feat-violet">{ICON.info}</span><div><b>You choose how much evidence</b><p>Starts at 3+ people. Choose &quot;Any&quot; to see all: 1–2 people are marked <span className="mp-thin">thin evidence</span>, and a single report gets no chart.</p></div></div>
        <div><span className="mp-feat-ic mp-feat-green">{ICON.bars}</span><div><b>Working and problems, both shown</b><p>Grouped as working, mixed, not working or no side taken. A cheaper model with problems is never offered as an alternative.</p></div></div>
        <div><span className="mp-feat-ic mp-feat-violet">{ICON.tag}</span><div><b>Prices are advertised</b><p>Input prices per 1M tokens, as providers publish them. No published price shows &quot;—&quot;, never $0.</p></div></div>
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
                  onClick={() => navigate(comparePath(cmpModels.map(modelId), { from: 'reports' }))}>
            {cmpModels.length < 2 ? 'Tick one more to compare' : 'Compare →'}
          </button>
        </div>
      )}
    </div>
  )
}
