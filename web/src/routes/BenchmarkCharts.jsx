import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { aiBenchmarks, modelPath } from '../api'
import { useHead } from '../seo/head'
import { aiBenchmarks as aiBenchmarksHead } from '../seo/pages'
import '../styles/benchmark-charts.css'

/**
 * AI BENCHMARKS (/ai-benchmarks, 2026-10-30, Parvathi): a public page. Pick a model and see
 * all of its published benchmark scores in ONE column chart - every category
 * together, and each of its setting rows ("GPT 6 Astra (max)") as its own
 * column beside the model's own row.
 *
 * THE SAME VALUES AS THE SIGNED-IN BENCHMARKS TABLE (judge/benchmarks.py
 * charts, built from table()), so a run that changes the table changes these
 * charts. A value still waiting for a person's review is not sent at all.
 *
 * NOTHING IS COMPUTED HERE (rule 3). A column's height is the stored percent the
 * figure is shown from, on a fixed 0-100 axis; no average, no combined score, no
 * rank of our own. Which values are columns is the contract's call
 * (`score_unit: percent`, sent as `chart`): a leaderboard position, or a score in
 * another unit, goes in the table under the chart instead.
 *
 * COLOUR FOLLOWS THE SERIES (the dataviz rules): eight categorical slots,
 * checked with the palette validator on this site's surfaces. A series keeps
 * its slot while it is shown; turning one on takes the lowest free slot, so
 * nothing on screen is repainted. At most eight at once - a model can have
 * twelve rows - and four to start, so the chart opens readable.
 *
 * EVERY VALUE NAMES ITS SOURCE, LINK AND DATE (CLAUDE.md, the Benchmarks
 * exception, condition 4): in each column's tooltip, and as links under the chart.
 *
 * THE CHOICE IS THE ADDRESS: /ai-benchmarks/<model id>, so a shared link opens on
 * the same model and the back button returns to the last one. One page - no
 * page is built per model. An old ?model= link still opens.
 */

const TICKS = [0, 25, 50, 75, 100]
const MAX_SHOWN = 8
const FIRST_SHOWN = 4
// THE EIGHT SERIES COLOURS, written out (styles/benchmark-charts.css defines them):
// a name built at run time is one tests/test_a_figure_is_one_measurement.py cannot check.
const SERIES = ['var(--bc-s1)', 'var(--bc-s2)', 'var(--bc-s3)', 'var(--bc-s4)',
  'var(--bc-s5)', 'var(--bc-s6)', 'var(--bc-s7)', 'var(--bc-s8)']
const NEW_TAB = <span className="sr-only"> (opens in a new tab)</span>

const fmtDay = (iso) => {
  if (!iso) return null
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso)
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
}

/**
 * "SWE-bench leaderboard, 28 Oct 2026" when the board dates its value; otherwise
 * "…, read 28 Oct 2026" - when we read it, which is a different fact (rule 6).
 */
function sourceLine(v) {
  if (v.source_date) return `${v.source_label}, ${fmtDay(v.source_date)}`
  if (v.collected_at) return `${v.source_label}, read ${fmtDay(v.collected_at)}`
  return v.source_label
}

const rankText = (v) => `#${v.display}${v.rank_out_of ? ` of ${v.rank_out_of}` : ''}${v.tied ? ' (tied)' : ''}`

/** Benchmarks with a column in any series, in the table's own order, under their category. */
function layout(series) {
  const sections = []
  const seen = new Map()
  for (const s of series) {
    for (const v of s.values) {
      if (!v.chart) continue
      let sec = sections.find((x) => x.key === v.section)
      if (!sec) { sec = { key: v.section, label: v.section_label, benches: [] }; sections.push(sec) }
      if (!seen.has(v.key)) { seen.set(v.key, v); sec.benches.push(v) }
    }
  }
  // The table's own order, whichever row first had the benchmark.
  for (const sec of sections) sec.benches.sort((a, b) => a.order - b.order)
  return sections.sort((a, b) => a.benches[0].order - b.benches[0].order)
}

function Tooltip({ tip }) {
  if (!tip) return null
  const { v, s, x, y, below } = tip
  return (
    <div className={`bc-tip${below ? ' below' : ''}`} style={{ left: x, top: y }} role="status">
      <strong>{v.label}</strong>
      <span><i className="bc-swatch" style={{ background: SERIES[s.slot] }} />{s.label}</span>
      <span className="bc-tip-value tnum">{v.display} <span className="dim">out of 100</span></span>
      <span className="dim">{sourceLine(v)}</span>
      {v.variant && <span className="dim">Setup: {v.variant}</span>}
      {v.setting_not_stated && <span className="dim">The board does not say which setting was used.</span>}
    </div>
  )
}

function ColumnChart({ sections, shown }) {
  const [tip, setTip] = useState(null)
  // The tooltip is placed against the window, so a page scroll would leave it behind.
  useEffect(() => {
    if (!tip) return undefined
    const hide = () => setTip(null)
    window.addEventListener('scroll', hide, { passive: true })
    return () => window.removeEventListener('scroll', hide)
  }, [tip])
  const benches = sections.reduce((n, s) => n + s.benches.length, 0)
  const single = shown.length === 1
  // PLACED AGAINST THE WINDOW (position: fixed), so the chart's sideways scroll
  // never clips it; under the column when there is no room above it.
  const show = (e, v, s) => {
    const box = e.currentTarget.getBoundingClientRect()
    const below = box.top < 170
    setTip({ v, s, below, x: box.left + box.width / 2, y: below ? box.top + 12 : box.top })
  }
  return (
    <div className="bc-scroll" onScroll={() => setTip(null)}>
      <div className="bc-plot" style={{ minWidth: `${Math.max(640, benches * (single ? 48 : 64))}px` }}
        onMouseLeave={() => setTip(null)}>
        <div className="bc-yaxis" aria-hidden="true">
          {TICKS.map((t) => <span key={t} style={{ bottom: `${t}%` }}>{t}</span>)}
        </div>
        <div className="bc-area">
          <div className="bc-gridlines" aria-hidden="true">
            {TICKS.map((t) => <i key={t} style={{ bottom: `${t}%` }} className={t === 0 ? 'base' : ''} />)}
          </div>
          <div className="bc-sections">
            {sections.map((sec) => (
              <div key={sec.key} className="bc-section" style={{ flexGrow: sec.benches.length }}>
                <div className="bc-clusters">
                  {sec.benches.map((b) => (
                    <div key={b.key} className="bc-cluster">
                      <div className="bc-cols">
                        {shown.map((s) => {
                          const v = s.byKey.get(b.key)
                          if (!v) return <span key={s.id} className="bc-col-gap" />
                          return (
                            <button key={s.id} type="button" className="bc-col"
                              style={{ height: `${v.percent}%`, background: SERIES[s.slot] }}
                              aria-label={`${b.label}, ${s.label}: ${v.display} out of 100, from ${sourceLine(v)}`}
                              onMouseEnter={(e) => show(e, v, s)} onFocus={(e) => show(e, v, s)}
                              onBlur={() => setTip(null)}>
                              {single && <span className="bc-col-value tnum">{v.display}</span>}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="bc-xlabels" aria-hidden="true">
                  {sec.benches.map((b) => <span key={b.key}>{b.label}</span>)}
                </div>
                <div className="bc-section-label">{sec.label}</div>
              </div>
            ))}
          </div>
          <Tooltip tip={tip} />
        </div>
      </div>
    </div>
  )
}

function Legend({ series, onToggle }) {
  const count = series.filter((s) => s.slot != null).length
  return (
    <div className="bc-legend" role="group" aria-label="Rows shown in the chart">
      {series.map((s) => {
        const on = s.slot != null
        const full = !on && count >= MAX_SHOWN
        return (
          <button key={s.id} type="button" className={`bc-chip${on ? ' on' : ''}`} aria-pressed={on}
            disabled={full || (on && count === 1)} onClick={() => onToggle(s.id)}
            title={full ? `At most ${MAX_SHOWN} at once: turn one off to add this.` : s.label}>
            <i className="bc-swatch" style={on ? { background: SERIES[s.slot] } : undefined} />
            {s.short}
          </button>
        )
      })}
    </div>
  )
}

/**
 * THE LEADERBOARD (2026-10-30, Parvathi): every value the model's rows have, one
 * line per benchmark and variant - the board's position for it and its score -
 * in one table a reader can filter and sort. It replaces the position cards and
 * the chart-as-a-table: both laid the same values out a second time.
 *
 * NOTHING IS RANKED BY US. A position is the board's own ("#3 of 35"); its track
 * draws those two printed numbers. Sorting only orders the lines, and "Best
 * placing per benchmark" only keeps, of a model's variants on one board, the
 * one that board places highest - no value is changed or combined (rule 3).
 */
const FIRST_LINES = 12
const SORTS = [
  ['position', 'Best position'],
  ['score', 'Highest score'],
  ['name', 'Benchmark, A to Z'],
  ['category', 'Category'],
]

function leaderboardRows(series) {
  const rows = new Map()
  for (const s of series) {
    for (const v of s.values) {
      const id = `${s.id}|${v.benchmark}`
      if (!rows.has(id)) {
        rows.set(id, {
          id, s, benchmark: v.benchmark, order: v.order, section: v.section,
          section_label: v.section_label, label: v.label.replace(/ rank$/, ''), score: null, rank: null,
        })
      }
      const row = rows.get(id)
      row.order = Math.min(row.order, v.order)
      if (v.metric === 'rank') row.rank = v
      else { row.score = v; row.label = v.label }
    }
  }
  return [...rows.values()]
}

const rankOf = (r) => (r.rank && Number.isFinite(Number(r.rank.display)) ? Number(r.rank.display) : null)
const COMPARE = {
  // Lines the board does not place go last, whatever the order.
  position: (a, b) => (rankOf(a) ?? Infinity) - (rankOf(b) ?? Infinity) || a.order - b.order,
  score: (a, b) => (b.score?.percent ?? -Infinity) - (a.score?.percent ?? -Infinity) || a.order - b.order,
  name: (a, b) => a.label.localeCompare(b.label) || a.order - b.order,
  category: (a, b) => a.order - b.order,
}

function Position({ v, colour }) {
  if (!v) return <span className="dim bc-small" title="This board gives a score but no position.">No position</span>
  const n = Number(v.display)
  const at = v.rank_out_of > 1 && Number.isFinite(n)
    ? Math.min(100, Math.max(0, ((n - 1) / (v.rank_out_of - 1)) * 100)) : null
  const podium = Number.isFinite(n) && n <= 3 ? ` podium p${n}` : ''
  return (
    <span className="bc-lb-pos" title={`${rankText(v)} on the board\n${sourceLine(v)}`}>
      <span className={`bc-lb-badge tnum${podium}`}>#{v.display}</span>
      <span className="bc-lb-pos-meta">
        <span className="dim bc-small tnum">
          {v.rank_out_of ? `of ${v.rank_out_of}` : 'board size not given'}{v.tied ? ' · tied' : ''}
          {/* A MOVE: where the board placed it before, as printed - not a
              difference of ours (judge/benchmarks.py _moved). */}
          {v.moved && (
            <span className={`bc-lb-move ${v.moved.direction}`}
              title={`Was #${v.moved.was}${v.moved.was_out_of ? ` of ${v.moved.was_out_of}` : ''} before the read on ${fmtDay(v.moved.on)}`}>
              <span aria-hidden="true">{v.moved.direction === 'up' ? '▲' : '▼'}</span>
              <span className="sr-only">{v.moved.direction === 'up' ? 'Moved up' : 'Moved down'}, </span>
              was #{v.moved.was}
            </span>
          )}
        </span>
        {at != null && (
          <span className="bc-lb-track" aria-hidden="true"><i style={{ left: `${at}%`, background: colour }} /></span>
        )}
      </span>
    </span>
  )
}

function Score({ v, colour }) {
  if (!v) return <span className="dim">—</span>
  return (
    <span className="bc-lb-score" title={sourceLine(v)}>
      <span className="bc-lb-score-n tnum">{v.display}</span>
      {v.chart && <span className="bc-lb-meter" aria-hidden="true"><i style={{ width: `${v.percent}%`, background: colour }} /></span>}
    </span>
  )
}

function Leaderboard({ series }) {
  const [sort, setSort] = useState('position')
  const [category, setCategory] = useState('all')
  const [variant, setVariant] = useState('all')
  const [bestOnly, setBestOnly] = useState(false)
  const [everything, setEverything] = useState(false)

  const all = useMemo(() => leaderboardRows(series), [series])
  // THE PODIUM: on how many boards the model places first, second, third - each
  // board once, at the model's best-placed variant there - out of the boards
  // that place it at all (rule 7). Counts of the boards' own positions.
  const podium = useMemo(() => {
    const best = new Map()
    for (const r of all) {
      const n = rankOf(r)
      if (n != null && (!best.has(r.benchmark) || n < best.get(r.benchmark))) best.set(r.benchmark, n)
    }
    const places = [...best.values()]
    return { boards: places.length, counts: [1, 2, 3].map((p) => places.filter((n) => n === p).length) }
  }, [all])
  const categories = useMemo(() => {
    const seen = new Map()
    for (const r of [...all].sort(COMPARE.category)) if (!seen.has(r.section)) seen.set(r.section, r.section_label)
    return [...seen]
  }, [all])

  let rows = all.filter((r) => (category === 'all' || r.section === category)
    && (variant === 'all' || r.s.id === variant))
  if (bestOnly) {
    const best = new Map()
    for (const r of [...rows].sort(COMPARE.position)) if (!best.has(r.benchmark)) best.set(r.benchmark, r)
    rows = [...best.values()]
  }
  rows = [...rows].sort(COMPARE[sort])
  // The first lines, then the rest on asking: a model with many variants has dozens.
  const visible = everything ? rows : rows.slice(0, FIRST_LINES)

  const colour = (s) => (s.slot != null ? SERIES[s.slot] : 'var(--text-3)')
  const header = (key, label, cls = '') => (
    <th scope="col" className={cls} aria-sort={sort === key ? (key === 'name' || key === 'position' ? 'ascending' : 'descending') : undefined}>
      <button type="button" className={`bc-lb-sort${sort === key ? ' on' : ''}`} onClick={() => setSort(key)}>
        {label}{sort === key ? <span aria-hidden="true"> ↓</span> : null}
      </button>
    </th>
  )

  return (
    <section className="bc-lb card" aria-labelledby="bc-lb-h">
      <div className="bc-lb-head">
        <div className="stack stack-1">
          <h2 id="bc-lb-h" className="bc-h2">Leaderboard</h2>
          <p className="dim bc-small">
            Each board&apos;s own position and score for every variant. A position depends on which models a board
            lists, so it is not a score; the line beside it runs from first place to last.
          </p>
        </div>
        <div className="bc-lb-tools">
          {series.length > 1 && (
            <label className="bc-lb-field">
              <span>Variant</span>
              <select value={variant} onChange={(e) => setVariant(e.target.value)}>
                <option value="all">All variants</option>
                {series.map((s) => <option key={s.id} value={s.id}>{s.short}</option>)}
              </select>
            </label>
          )}
          <label className="bc-lb-field">
            <span>Sort</span>
            <select value={sort} onChange={(e) => setSort(e.target.value)}>
              {SORTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
          {series.length > 1 && (
            <label className="bc-lb-switch">
              <input type="checkbox" checked={bestOnly} onChange={(e) => setBestOnly(e.target.checked)} />
              <span>Best placing per benchmark</span>
            </label>
          )}
        </div>
      </div>

      {podium.boards > 0 && (
        <ul className="bc-podium" aria-label="Podium">
          {['1st', '2nd', '3rd'].map((label, i) => (
            <li key={label} className={`bc-podium-place p${i + 1}`}>
              <span className="bc-podium-n tnum">{podium.counts[i]}</span>
              <span className="bc-podium-l">{label} place</span>
            </li>
          ))}
          <li className="bc-podium-of dim bc-small">
            of the {podium.boards} {podium.boards === 1 ? 'board' : 'boards'} that place this model,
            counting each board once at its best-placed variant
          </li>
        </ul>
      )}

      <div className="bc-lb-cats" role="group" aria-label="Category">
        {[['all', 'All'], ...categories].map(([k, l]) => (
          <button key={k} type="button" className={`bc-cat${category === k ? ' on' : ''}`} aria-pressed={category === k}
            onClick={() => setCategory(k)}>{l}</button>
        ))}
        <span className="dim bc-small bc-lb-count tnum">{rows.length} {rows.length === 1 ? 'line' : 'lines'}</span>
      </div>

      <div className="bc-table-wrap">
        <table className="bc-lb-table">
          <thead>
            <tr>
              {header('position', 'Position', 'w-pos')}
              {header('name', 'Benchmark')}
              <th scope="col">Variant</th>
              {header('score', 'Score', 'w-score')}
              <th scope="col">Source</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => {
              const src = r.score || r.rank
              const when = sourceLine(src).slice(src.source_label.length + 2)
              return (
                <tr key={r.id}>
                  <td><Position v={r.rank} colour={colour(r.s)} /></td>
                  <td>
                    <span className="bc-lb-bench">{r.label}</span>
                    <span className="bc-lb-cat">{r.section_label}</span>
                  </td>
                  <td>
                    <span className="bc-lb-variant" title={r.s.label}>
                      <i className="bc-swatch" style={{ background: colour(r.s) }} />{r.s.short}
                    </span>
                  </td>
                  <td><Score v={r.score} colour={colour(r.s)} /></td>
                  <td className="bc-lb-src">
                    <a href={src.url} target="_blank" rel="noopener noreferrer nofollow">{src.source_label}{NEW_TAB}</a>
                    {when && <span className="dim">{when}</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {rows.length === 0 && <p className="dim bc-small bc-lb-empty">Nothing matches these filters.</p>}
      </div>
      {rows.length > FIRST_LINES && (
        <button type="button" className="bc-lb-more" onClick={() => setEverything((x) => !x)}>
          {everything ? 'Show fewer' : `Show all ${rows.length} lines`}
        </button>
      )}
    </section>
  )
}

/** The distinct sources behind the values shown, each once, with its link. */
function Sources({ values }) {
  const seen = new Map()
  for (const v of values) if (!seen.has(v.url)) seen.set(v.url, v)
  if (!seen.size) return null
  // FOLDED: a model with many rows draws on a dozen boards. Each column's tooltip
  // names its own source and date; this list carries the links.
  return (
    <details className="bc-sources">
      <summary>Sources ({seen.size} leaderboards)</summary>
      <ul>
        {[...seen.values()].map((v) => (
          <li key={v.url}>
            <a href={v.url} target="_blank" rel="noopener noreferrer nofollow">{sourceLine(v)}{NEW_TAB}</a>
          </li>
        ))}
      </ul>
    </details>
  )
}

export default function BenchmarkCharts() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const wanted = useParams()['*'] || params.get('model') || null
  const goTo = useCallback((id, replace) => navigate(`/ai-benchmarks/${modelPath(id)}`, { replace }), [navigate])
  // seriesId -> colour slot for the series shown, kept per model: a model the
  // reader has not touched opens with its first rows shown.
  const [picked, setPicked] = useState({ model: null, slots: {} })

  // THE LIST, THEN ONE MODEL (judge/benchmarks.py charts): each answer carries
  // the list; with no model in the address, the first one is opened.
  useEffect(() => {
    let live = true
    aiBenchmarks(wanted).then((d) => {
      if (!live) return
      setErr(null)
      setData(d)
      // No model, an unknown one, or an old ?model= link: settle on a model's address.
      if (d.model && params.has('model')) goTo(d.model.id, true)
      else if (!d.model && d.models.length) goTo(d.models[0].id, true)
    }).catch((e) => live && setErr(e))
    return () => { live = false }
    // `params` is read once per answer, to move an old ?model= link; it never re-asks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, goTo])

  const models = data?.models || []
  const model = data?.model || null
  useHead(aiBenchmarksHead(model))

  const slots = useMemo(() => {
    if (picked.model === model?.id) return picked.slots
    const first = {}
    ;(model?.series || []).slice(0, FIRST_SHOWN).forEach((s, i) => { first[s.id] = i })
    return first
  }, [picked, model])

  const series = useMemo(() => (model?.series || []).map((s) => ({
    ...s, slot: slots[s.id], byKey: new Map(s.values.map((v) => [v.key, v])),
  })), [model, slots])
  const shown = series.filter((s) => s.slot != null)
  const sections = useMemo(() => layout(shown), [shown])

  // FROM THE PREVIOUS STATE, not this render's copy: two clicks in quick
  // succession must both count (the second used to undo the first).
  const toggle = (id) => setPicked((prev) => {
    const cur = prev.model === model.id ? prev.slots : slots
    let next
    if (cur[id] != null) {
      next = { ...cur }
      delete next[id]
    } else {
      const used = new Set(Object.values(cur))
      const free = [...Array(MAX_SHOWN).keys()].find((i) => !used.has(i))
      next = free == null ? cur : { ...cur, [id]: free }
    }
    return { model: model.id, slots: next }
  })

  const pick = (id) => goTo(id, false)

  const charted = useMemo(() => sections.flatMap((s) => s.benches), [sections])

  const tracked = models.filter((m) => m.tracked)
  const others = models.filter((m) => !m.tracked)

  return (
    <div className="shell section-tight stack stack-3 bc-page">
      <header className="stack stack-2">
        <h1>AI model benchmarks</h1>
        <p className="dim">
          Pick a model to see its published benchmark scores in one chart, with each of its settings
          (such as max or high effort) as its own column. Every value comes from a public leaderboard,
          exactly as that board prints it, with the board&apos;s name and date. Scores are percentages,
          out of 100. Each benchmark tests something different, so a taller column on one benchmark is
          not &ldquo;better&rdquo; than a shorter one on another.
        </p>
      </header>

      {err && <p className="bc-error" role="alert">The charts can&apos;t be loaded right now. Please try again later.</p>}
      {!err && !data && <p className="dim" aria-live="polite">Loading the charts…</p>}
      {data && models.length === 0 && <p className="dim">No published benchmark scores yet.</p>}

      {model && (
        <>
          <div className="bc-controls">
            <label className="bc-select">
              <span>Model</span>
              <select value={model.id} onChange={(e) => pick(e.target.value)}>
                {tracked.length > 0 && (
                  <optgroup label="Tracked models">
                    {tracked.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                  </optgroup>
                )}
                {others.length > 0 && (
                  <optgroup label="Other models on the leaderboards">
                    {others.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                  </optgroup>
                )}
              </select>
            </label>
            <ul className="bc-stats">
              <li><strong className="tnum">{model.benchmarks_scored}</strong> {model.benchmarks_scored === 1 ? 'benchmark' : 'benchmarks'}</li>
              {model.series.length > 1 && <li><strong className="tnum">{model.series.length}</strong> variants</li>}
              {data.last_run?.finished_at && <li>Updated <strong>{fmtDay(data.last_run.finished_at)}</strong></li>}
            </ul>
          </div>

          <figure className="bc-chart card">
            <figcaption className="bc-chart-head">
              <span className="bc-chart-title">{model.label}</span>
              {series.length > 1 && (
                <span className="dim bc-small">
                  Turn rows on or off below{series.length > MAX_SHOWN ? ` (up to ${MAX_SHOWN} at once)` : ''}. Hover a column for its value and source.
                </span>
              )}
            </figcaption>
            {series.length > 1 && <Legend series={series} onToggle={toggle} />}
            {charted.length
              ? <ColumnChart sections={sections} shown={shown} />
              : <p className="dim">No percentage scores for the rows shown; their leaderboard positions are below.</p>}
          </figure>

          <Leaderboard series={series} />

          <Sources values={series.flatMap((s) => s.values)} />

          {data.withheld_for_review > 0 && (
            <p className="dim bc-small">
              {data.withheld_for_review} value{data.withheld_for_review === 1 ? ' is' : 's are'} not shown here
              yet, across all models, while a person checks {data.withheld_for_review === 1 ? 'it' : 'them'}.
            </p>
          )}
        </>
      )}
    </div>
  )
}
