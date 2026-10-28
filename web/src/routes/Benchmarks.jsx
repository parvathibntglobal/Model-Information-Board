import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  BoardUnreadable,
  benchmarksChanges,
  benchmarksReview,
  benchmarksRunLog,
  benchmarksRuns,
  benchmarksTable,
  benchmarksUnmatched,
  decideBenchmarkName,
  startBenchmarksRun,
  undoBenchmarkName,
} from '../api'
import { Unreadable } from '../components/ui'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import '../styles/benchmarks.css'

/**
 * BENCHMARKS (2026-10-22, Parvathi): signed in. Published benchmark results for
 * the tracked text models, as each source publishes them - public leaderboard
 * pages, scraped by collect/benchmarks/ into the bench_ tables
 * (BENCHMARK_PIPELINE_WORKFLOW.md). No data-file downloads, no key, no paid
 * service, no language model anywhere in it.
 *
 * THE SOURCES' OWN VALUES (2026-10-22). Every cell is a source's published
 * value, with the source, link and date behind it. A score shows in one style -
 * a percentage to two decimals, no "%" (2026-10-27) - and the hover keeps the
 * source's own text; ranks show as printed. The page computes nothing - no local
 * rank, no percentile, no score.
 *
 * ROWS ARE MODELS AND THEIR SETTINGS. A source that publishes "GPT 6 Astra (max)"
 * fills the (max) row under GPT 6 Astra, never the model's own row: results at
 * different reasoning efforts are different results.
 *
 * THE RUN BUTTON starts a background run (judge/benchmarks.py start_run) and the
 * terminal below shows its log live. Admin edits of single cells come in phase 2.
 */

const TABS = [
  ['table', 'Table'],
  ['changes', 'Changelog'],
  ['runs', 'Runs'],
  ['unmatched', 'Unmatched names'],
  ['review', 'Review'],
  ['sources', 'Sources'],
]

const fmtWhen = (iso) => (iso
  ? new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  : '')

function cellTitle(cell, column) {
  if (!cell) return 'No source publishes this yet.'
  const lines = [
    cell.rounded_from
      ? `${column.label}: ${cell.display}  (the source printed ${cell.rounded_from})`
      : `${column.label}: ${cell.display}  (as the source printed it)`,
    `Source: ${cell.source_label}${cell.tier ? ` · tier ${cell.tier}, ${cell.tier_label}` : ''}`,
    `Name on the source: "${cell.raw_name}"`,
  ]
  if (cell.variant) lines.push(`Test setup: ${cell.variant}`)
  if (cell.benchmark_version) lines.push(`Benchmark version: ${cell.benchmark_version}`)
  if (cell.rank_board) lines.push(`Board: ${cell.rank_board}${cell.rank_out_of ? `, ${cell.rank_out_of} entries when read` : ''}`)
  if (cell.tied) lines.push(cell.tied_with?.length ? `Tied with ${cell.tied_with.join(', ')}` : 'Tied with another entry')
  if (cell.source_date) lines.push(`Source's date: ${cell.source_date}`)
  if (cell.collected_at) lines.push(`Collected: ${fmtWhen(cell.collected_at)}`)
  if (cell.setting_not_stated) lines.push('The source does not state the setting.')
  if (cell.needs_review) lines.push('Flagged for review: sources disagree.')
  if (cell.badges?.includes('source')) lines.push('Recently taken over by this source (a higher tier, or the only one left) - the model did not move.')
  if (cell.others?.length) {
    lines.push('', 'Other sources for this cell (not shown: a higher tier, or the same tier ranked first):')
    for (const o of cell.others) {
      lines.push(`  ${o.source_label}${o.tier ? ` (tier ${o.tier})` : ''}: ${o.display}${o.variant ? ` [${o.variant}]` : ''}`)
    }
  }
  return lines.join('\n')
}

function Cell({ cell, column }) {
  if (!cell) return <td className="bm-c bm-empty" title={cellTitle(null, column)}>—</td>
  const recent = ['new', 'source', 'changed'].find((b) => cell.badges?.includes(b)) || null
  return (
    <td className={`bm-c${cell.needs_review ? ' bm-flag' : ''}`} title={cellTitle(cell, column)}>
      <a href={cell.url} target="_blank" rel="noreferrer noopener nofollow" className="bm-v">{cell.display}</a>
      {recent && (
        <span className={`bm-badge bm-${recent}${cell.direction ? ` bm-${cell.direction}` : ''}`}>
          {recent === 'new' ? 'new' : recent === 'source' ? 'source' : cell.direction === 'better' ? '▲' : cell.direction === 'worse' ? '▼' : '•'}
        </span>
      )}
    </td>
  )
}

function useBenchData(tab, refreshKey) {
  const [table, setTable] = useState(null)
  const [error, setError] = useState(null)
  const [extra, setExtra] = useState({})
  useEffect(() => {
    let alive = true
    benchmarksTable()
      .then((d) => { if (alive) { setTable(d); setError(null) } })
      .catch((e) => { if (alive) setError(e) })
    return () => { alive = false }
  }, [refreshKey])
  useEffect(() => {
    let alive = true
    const load = { changes: benchmarksChanges, runs: benchmarksRuns, unmatched: benchmarksUnmatched, review: benchmarksReview }[tab]
    if (!load) return undefined
    load()
      .then((d) => { if (alive) setExtra((x) => ({ ...x, [tab]: d })) })
      .catch((e) => { if (alive) setExtra((x) => ({ ...x, [tab]: { error: e.message } })) })
    return () => { alive = false }
  }, [tab, refreshKey])
  return { table, error, extra }
}

/* ── the run panel and its terminal ──────────────────────────────────────── */

// A run the page started that has not shown up after this long never will
// (its process failed to start); the page stops waiting (PR #573 review).
const NEVER_STARTED_MS = 60_000

function Terminal({ log, running, title, onClose }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [log])
  return (
    <div className="bm-term-wrap">
      <div className="bm-term-bar">
        <span className={`bm-dot${running ? ' bm-dot-live' : ''}`} aria-hidden="true" />
        <span>{title}</span>
        {onClose && (
          <button type="button" className="bm-term-close" onClick={onClose} aria-label="Close the log">
            Close ✕
          </button>
        )}
      </div>
      <pre className="bm-term" ref={ref} aria-live="polite">{log || (running ? 'Starting…' : '')}</pre>
    </div>
  )
}

function RunPanel({ onFinished, viewRun, clearView, savedPages }) {
  const [watch, setWatch] = useState(null)        // { requestId } | { runId }
  const [log, setLog] = useState('')
  const [run, setRun] = useState(null)
  const [done, setDone] = useState(true)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const finished = useRef(onFinished)
  finished.current = onFinished

  useEffect(() => {
    if (viewRun) { setWatch({ runId: viewRun }); setDone(false); setLog(''); setError(null) }
  }, [viewRun])

  useEffect(() => {
    if (!watch) return undefined
    let alive = true
    let timer
    const startedAt = Date.now()
    const poll = async () => {
      try {
        const d = await benchmarksRunLog(watch)
        if (!alive) return
        if (!d.found && Date.now() - startedAt > NEVER_STARTED_MS) {
          setError('The run did not start within a minute - see the backend log. Nothing was published.')
          setDone(true)
          return
        }
        if (d.found) {
          setLog(d.log)
          setRun(d.run)
          if (d.done) {
            setDone(true)
            if (watch.requestId) finished.current?.()
            return
          }
        }
        timer = setTimeout(poll, 1500)
      } catch (e) {
        if (alive) { setError(e.message); setDone(true) }
      }
    }
    poll()
    return () => { alive = false; clearTimeout(timer) }
  }, [watch])

  const start = async (opts) => {
    setBusy(true); setError(null); clearView?.()
    try {
      const r = await startBenchmarksRun(opts)
      setLog(''); setRun(null); setDone(false)
      setWatch({ requestId: r.request_id })
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const running = watch && !done
  // A finished run's log (one opened from the Runs tab, or a run that has just
  // ended) can be closed; a run still going stays on screen until it ends.
  const close = () => {
    clearView?.()
    setWatch(null); setLog(''); setRun(null); setError(null); setDone(true)
  }
  const title = run
    ? `Run #${run.id}${run.dry_run ? ' (dry run)' : ''} · ${run.status}${run.finished_at ? ` · finished ${fmtWhen(run.finished_at)}` : ''}`
    : running ? 'Waiting for the run to start…' : 'Terminal'
  return (
    <section className="bm-run card" aria-label="Run">
      <div className="bm-run-head">
        <div className="stack stack-1">
          <h2 className="bm-h2">Run</h2>
          <p className="muted bm-small">
            Fetches every enabled source once, politely (robots.txt, an identifying User-Agent), and publishes what
            changed. The terminal shows the run&apos;s log as it happens.
          </p>
        </div>
        <div className="bm-actions">
          <button type="button" className="btn btn-primary" disabled={busy || running} onClick={() => start({})}>
            {running ? 'Running…' : 'Run now'}
          </button>
          <button type="button" className="btn btn-ghost" disabled={busy || running} onClick={() => start({ dryRun: true })}
                  title="Everything except publish: shows what would change">
            Preview (dry run)
          </button>
          <button type="button" className="btn btn-ghost" disabled={busy || running || !savedPages}
                  onClick={() => start({ useSnapshot: true })}
                  title={savedPages
                    ? "Re-parse each source's last saved copy; no site is asked"
                    : 'No page has been saved yet - make a real run first'}>
            Re-parse saved pages
          </button>
        </div>
      </div>
      {error && <p className="bm-error" role="alert">{error}</p>}
      {(watch || log) && <Terminal log={log} running={running} title={title} onClose={running ? null : close} />}
    </section>
  )
}

/* ── the table ───────────────────────────────────────────────────────────── */

// A model's place in a sorted column: the best value on its own row or any of
// its setting rows (the column's own direction decides which is best).
function bestValue(row, column) {
  const values = [row.cells[column.key], ...row.children.map((c) => c.cells[column.key])]
    .filter((cell) => cell && cell.sort != null)
    .map((cell) => cell.sort)
  if (!values.length) return null
  return column.better === 'lower' ? Math.min(...values) : Math.max(...values)
}

function sortRows(rows, columns, sort) {
  if (!sort) return rows
  const column = columns.find((c) => c.key === sort.key)
  const name = sort.key === 'model'
  if (!name && !column) return rows
  const sign = sort.dir === 'best' ? 1 : -1
  const groupOf = (r) => (r.group === 'tracked' ? 0 : 1)
  return [...rows].sort((a, b) => {
    if (groupOf(a) !== groupOf(b)) return groupOf(a) - groupOf(b) // tracked stay first
    if (name) return sign * a.label.localeCompare(b.label)
    const va = bestValue(a, column)
    const vb = bestValue(b, column)
    if (va == null || vb == null) return va == null ? (vb == null ? 0 : 1) : -1 // no value: last
    const better = column.better === 'lower' ? va - vb : vb - va
    return sign * better || a.label.localeCompare(b.label)
  })
}

// Every heading shows an arrow, so it reads as sortable: ↕ not sorted, ↓ best
// first (A-Z for the model name), ↑ worst first (Z-A). A third click resets.
function SortHeader({ id, label, sort, setSort, className, title, rowSpan }) {
  const on = sort?.key === id
  const next = () => setSort(!on ? { key: id, dir: 'best' } : sort.dir === 'best' ? { key: id, dir: 'worst' } : null)
  const arrow = !on ? '↕' : sort.dir === 'best' ? '↓' : '↑'
  return (
    <th className={className} title={title} rowSpan={rowSpan} scope="col"
        aria-sort={on ? (sort.dir === 'best' ? 'descending' : 'ascending') : 'none'}>
      <button type="button" className={`bm-sort${on ? ' on' : ''}`} onClick={next}>
        <span className="bm-sort-label">{label}</span>
        <span className="bm-arrow" aria-hidden="true">{arrow}</span>
      </button>
    </th>
  )
}

const MODEL_WIDTH = 260
const CHAR_PX = 7.4      // the 12px monospace digits the cells use
const BADGE_PX = 40      // a "new" / ▲ badge after the value
const PAD_PX = 26

// Each column as wide as its longest value (as printed), so nothing is cut off;
// the heading wraps to fit. Both halves of the table use these widths.
function columnWidths(rows, columns) {
  const widths = {}
  for (const c of columns) {
    // At least the longest word of the heading (it wraps between words) plus its arrow.
    const word = Math.max(...c.label.split(/\s+/).map((w) => w.length))
    let px = Math.max(96, PAD_PX + 20 + word * 8)
    for (const row of rows) {
      for (const cells of [row.cells, ...row.children.map((ch) => ch.cells)]) {
        const cell = cells[c.key]
        if (!cell) continue
        const need = PAD_PX + String(cell.display).length * CHAR_PX + (cell.badges?.length ? BADGE_PX : 0)
        if (need > px) px = need
      }
    }
    widths[c.key] = Math.min(Math.ceil(px), 280)
  }
  return widths
}

function Cols({ columns, widths }) {
  return (
    <colgroup>
      <col style={{ width: MODEL_WIDTH }} />
      {columns.map((c) => <col key={c.key} style={{ width: widths[c.key] }} />)}
    </colgroup>
  )
}

// Which columns the table shows (2026-10-28): with a rank beside most scores
// the table doubled in width, so scores, ranks or both. Remembered per browser.
const VIEWS = [
  { key: 'score', label: 'Scores' },
  { key: 'rank', label: 'Ranks' },
  { key: 'both', label: 'Both' },
]
const VIEW_KEY = 'bm-view'
const readView = () => {
  try {
    const v = localStorage.getItem(VIEW_KEY)
    return VIEWS.some((x) => x.key === v) ? v : 'score'
  } catch {
    return 'score'
  }
}
const inView = (column, view) => view === 'both' || (view === 'rank') === (column.metric === 'rank')

function BenchTable({ data }) {
  const [section, setSection] = useState('all')
  const [view, setViewState] = useState(readView)
  const setView = (v) => {
    setViewState(v)
    try { localStorage.setItem(VIEW_KEY, v) } catch { /* storage blocked: this visit only */ }
  }
  const [sort, setSort] = useState(null) // { key, dir: 'best' | 'worst' } - best first, then worst first, then off
  const [showSettings, setShowSettings] = useState(true)
  const [hideEmpty, setHideEmpty] = useState(true)
  const [collapsed, setCollapsed] = useState({})

  const filled = useMemo(() => {
    const has = new Set()
    for (const row of data.rows) {
      for (const k of Object.keys(row.cells)) has.add(k)
      for (const child of row.children) for (const k of Object.keys(child.cells)) has.add(k)
    }
    return has
  }, [data])

  const sections = data.sections
    .filter((s) => section === 'all' || s.key === section)
    .map((s) => ({
      ...s,
      columns: s.columns.filter((c) => inView(c, view) && (!hideEmpty || filled.has(c.key))),
    }))
    .filter((s) => s.columns.length)
  const emptyColumns = data.sections
    .flatMap((s) => s.columns)
    .filter((c) => inView(c, view) && !filled.has(c.key))
  const columns = sections.flatMap((s) => s.columns)
  const rows = sortRows(data.rows, columns, sort)
  const widths = useMemo(() => columnWidths(data.rows, data.sections.flatMap((s) => s.columns)), [data])
  const width = MODEL_WIDTH + columns.reduce((sum, c) => sum + widths[c.key], 0)

  // The heading sits in its own strip that stays under the app bar while the
  // page scrolls, and carries the sideways scrollbar; the rows scroll sideways
  // with it. Fixed column widths keep the two lined up exactly.
  const headRef = useRef(null)
  const bodyRef = useRef(null)
  const follow = (from, to) => () => {
    if (from.current && to.current && to.current.scrollLeft !== from.current.scrollLeft) {
      to.current.scrollLeft = from.current.scrollLeft
    }
  }

  const n = data.counts
  return (
    <div className="stack stack-2">
      <p className="bm-totals">
        <b>{n.models + n.registry_models}</b> models <span className="muted">({n.models} tracked · {n.registry_models} registry)</span>
        {' · '}<b>{n.columns}</b> benchmark columns <span className="muted">({n.benchmarks} benchmarks)</span>
        {' · '}<b>{n.filled_cells}</b> values
      </p>
      <div className="bm-filters">
        <div className="bm-chips" role="group" aria-label="Sections">
          {[{ key: 'all', label: 'All sections' }, ...data.sections].map((s) => (
            <button key={s.key} type="button" className={`bm-chip${section === s.key ? ' on' : ''}`}
                    aria-pressed={section === s.key} onClick={() => setSection(s.key)}>
              {s.label}
            </button>
          ))}
        </div>
        <div className="bm-chips" role="group" aria-label="Show scores, ranks or both">
          {VIEWS.map((v) => (
            <button key={v.key} type="button" className={`bm-chip${view === v.key ? ' on' : ''}`}
                    aria-pressed={view === v.key} onClick={() => setView(v.key)}
                    title={v.key === 'rank' ? 'Each board’s own printed rank, where the board gives one' : undefined}>
              {v.label}
            </button>
          ))}
        </div>
        <div className="bm-toggles">
          <label><input type="checkbox" checked={showSettings} onChange={(e) => setShowSettings(e.target.checked)} /> Setting rows</label>
          <label><input type="checkbox" checked={hideEmpty} onChange={(e) => setHideEmpty(e.target.checked)} /> Hide empty columns</label>
        </div>
      </div>

      {columns.length === 0 ? (
        <p className="muted">No source has published a value for these columns yet.</p>
      ) : (
        <div className="bm-grid">
          <div className="bm-head" ref={headRef} onScroll={follow(headRef, bodyRef)}>
            <table className="bm-table" style={{ width }}>
              <Cols columns={columns} widths={widths} />
              <thead>
                <tr>
                  <SortHeader id="model" label="Model" sort={sort} setSort={setSort} className="bm-model-h" rowSpan={2}
                              title="Sort by name: A-Z, then Z-A, then the usual order (tracked models stay first)" />
                  {sections.map((s) => <th key={s.key} colSpan={s.columns.length} className="bm-sec" scope="colgroup">{s.label}</th>)}
                </tr>
                <tr>
                  {columns.map((c) => (
                    <SortHeader key={c.key} id={c.key} label={c.label} sort={sort} setSort={setSort} className="bm-col"
                                title={`${c.label}${c.benchmark_version ? ` (${c.benchmark_version})` : ''} · ${c.better} is better · updates: ${c.volatility}. `
                                  + (c.setup_note ? `${c.setup_note} ` : '')
                                  + 'Click to sort by value: best first, then worst first, then the usual order. A model sorts '
                                  + 'by its best value on any of its rows; tracked models stay above the others.'} />
                  ))}
                </tr>
              </thead>
            </table>
          </div>
          <div className="bm-body" ref={bodyRef} onScroll={follow(bodyRef, headRef)}>
          <table className="bm-table" style={{ width }}>
            <Cols columns={columns} widths={widths} />
            <tbody>
              {rows.map((row, i) => {
                const open = showSettings && !collapsed[row.row_id]
                const firstRegistry = row.group === 'registry' && rows[i - 1]?.group !== 'registry'
                return (
                  <Fragment key={row.row_id}>
                    {firstRegistry && (
                      <tr className="bm-group">
                        <th scope="rowgroup" colSpan={columns.length + 1}>
                          <span className="bm-group-label">
                            Other models (not tracked)
                            <span className="muted"> · registry models, listed here because a source published them</span>
                          </span>
                        </th>
                      </tr>
                    )}
                    <tr className="bm-row">
                      <th scope="row" className="bm-model">
                        {showSettings && row.children.length > 0 && (
                          <button type="button" className="bm-twisty" aria-expanded={open}
                                  aria-label={`${open ? 'Hide' : 'Show'} ${row.label} settings`}
                                  onClick={() => setCollapsed((c) => ({ ...c, [row.row_id]: open }))}>
                            {open ? '▾' : '▸'}
                          </button>
                        )}
                        <span>{row.label}</span>
                        {row.children.length > 0 && <span className="bm-n">{row.children.length}</span>}
                      </th>
                      {columns.map((c) => <Cell key={c.key} cell={row.cells[c.key]} column={c} />)}
                    </tr>
                    {open && row.children.map((child) => (
                      <tr key={child.row_id} className="bm-row bm-child">
                        <th scope="row" className="bm-model bm-setting">{child.dated ? child.label : `(${child.setting})`}</th>
                        {columns.map((c) => <Cell key={c.key} cell={child.cells[c.key]} column={c} />)}
                      </tr>
                    ))}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
          </div>
        </div>
      )}
      {hideEmpty && emptyColumns.length > 0 && (
        <p className="muted bm-small">
          {emptyColumns.length} column{emptyColumns.length === 1 ? ' has' : 's have'} no value from any source yet,
          for any tracked model: {emptyColumns.map((c) => c.label).join(', ')}. An empty column means no source we read
          lists these models there - not a low result.
        </p>
      )}
    </div>
  )
}

/* ── changelog, runs, unmatched, review ──────────────────────────────────── */

// The changelog's filter pills. The server filters the WHOLE changelog (judge
// CHANGE_KINDS) and counts each kind. "Score/Rank changes" are a value that
// moved on the same source; "Moved up/down" is any change with a direction,
// including another source taking the cell over.
const CHANGE_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'score', label: 'Score changes' },
  { key: 'rank', label: 'Rank changes' },
  { key: 'up', label: 'Moved up ▲' },
  { key: 'down', label: 'Moved down ▼' },
  { key: 'added', label: 'New values' },
  { key: 'removed', label: 'Removed' },
  { key: 'source_changed', label: 'Source switched' },
  { key: 'variant_added', label: 'New rows' },
]

// NEWS-WORTHY (judge NEWS_KINDS): what happened, not just what the board read.
// The numbers in the hints are the server's (contract news rules), never a copy here.
const NEWS_FILTERS = [
  { key: 'news', label: 'All news-worthy', hint: () => 'Debuts, fresh results, movers and drops together' },
  { key: 'debut', label: 'Debuts', hint: (r) => `A model released in the last ${r.debut_days} days showing up on a benchmark` },
  { key: 'fresh', label: 'Fresh results', hint: (r) => `A new value the source itself dates within the last ${r.fresh_days} days` },
  { key: 'mover', label: 'Movers', hint: (r) => `A rank move, or a score moving ${r.mover_points} point or more, on the same release` },
  { key: 'dropped', label: 'Dropped', hint: () => 'A model the benchmark’s own board no longer lists - often retired or withdrawn' },
]
const NEWS_LABEL = { debut: 'debut', fresh: 'fresh', mover: 'mover', dropped: 'dropped' }

function NewsMenu({ filter, counts, rules, onPick }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const away = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    const esc = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
  }, [open])
  const current = NEWS_FILTERS.find((f) => f.key === filter)
  return (
    <div className="bm-news" ref={ref}>
      <button type="button" className={`bm-chip bm-news-btn${current ? ' on' : ''}`} aria-haspopup="menu"
              aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {current ? current.label : 'News-worthy'} <span className="bm-chip-n">{counts[current?.key || 'news'] ?? 0}</span> ▾
      </button>
      {open && (
        <div className="bm-news-menu" role="menu">
          {NEWS_FILTERS.map((f) => (
            <button key={f.key} type="button" role="menuitemradio" aria-checked={filter === f.key}
                    className={`bm-news-item${filter === f.key ? ' on' : ''}`} disabled={!counts[f.key]}
                    onClick={() => { onPick(f.key); setOpen(false) }}>
              <span className="bm-news-label">{f.label} <span className="bm-chip-n">{counts[f.key] ?? 0}</span></span>
              {rules && <span className="muted bm-small">{f.hint(rules)}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// "16 of 30" for a rank, as the board stood when it was read.
const withOutOf = (value, outOf) => (value == null ? '—' : outOf ? `${value} of ${outOf}` : value)

// The Old / New hover in the Changelog: the same facts a table cell's hover
// gives - the value, the source's own text, the source and its tier (2026-10-27).
function sideTitle(e, side) {
  if (!e.old_detail && !e.new_detail) return undefined // e.g. a setting row added: no values
  const value = side === 'old' ? e.old : e.new
  const detail = side === 'old' ? e.old_detail : e.new_detail
  if (value == null || !detail) return side === 'old' ? 'No value before this run.' : 'No value after this run.'
  const lines = [
    detail.printed
      ? `${e.column || ''}: ${value}  (the source printed ${detail.printed})`
      : `${e.column || ''}: ${value}  (as the source printed it)`,
    `Source: ${detail.source_label}${detail.tier ? ` · tier ${detail.tier}, ${detail.tier_label}` : ''}`,
  ]
  if (side === 'new' && e.source_date) lines.push(`Source's date: ${e.source_date}`)
  if (side === 'new') lines.push(`Read: ${fmtWhen(e.changed_at)} (run #${e.run_id})`)
  if (e.type === 'source_changed' && side === 'new') lines.push('Another source took this cell over - the model did not move.')
  return lines.join('\n')
}

function Changelog({ data: all }) {
  const [openRuns, setOpenRuns] = useState({})
  const [filter, setFilter] = useState('all')
  const [filtered, setFiltered] = useState(null)
  // Older runs' changes, loaded a batch at a time ("Load older runs").
  const [older, setOlder] = useState([])
  const [loadingOlder, setLoadingOlder] = useState(false)
  useEffect(() => { setOlder([]) }, [filter, all])
  useEffect(() => {
    if (filter === 'all') return undefined
    let alive = true
    setFiltered(null)
    benchmarksChanges(null, filter)
      .then((d) => { if (alive) setFiltered(d) })
      .catch((e) => { if (alive) setFiltered({ error: e.message }) })
    return () => { alive = false }
  }, [filter, all])
  const data = filter === 'all' ? all : filtered
  if (!all) return <p className="muted">Loading…</p>
  if (all.error) return <p className="bm-error">{all.error}</p>
  if (!all.entries.length) return <p className="muted">No changes yet. The first run will add every value it finds.</p>
  const counts = { ...all.counts, all: all.total }
  const pills = (
    <div className="bm-filters">
      <div className="bm-chips" role="group" aria-label="Show changes of one kind">
        {CHANGE_FILTERS.map((f) => (
          <button key={f.key} type="button" className={`bm-chip${filter === f.key ? ' on' : ''}`}
                  aria-pressed={filter === f.key} onClick={() => setFilter(f.key)} disabled={!counts[f.key]}>
            {f.label} <span className="bm-chip-n">{counts[f.key]}</span>
          </button>
        ))}
      </div>
      <NewsMenu filter={filter} counts={counts} rules={all.news_rules} onPick={setFilter} />
    </div>
  )
  if (!data) return <div className="stack stack-3">{pills}<p className="muted">Loading…</p></div>
  if (data.error) return <div className="stack stack-3">{pills}<p className="bm-error">{data.error}</p></div>
  const last = older.length ? older[older.length - 1] : data
  const loadOlder = () => {
    setLoadingOlder(true)
    benchmarksChanges(null, filter, last.older_than)
      .then((d) => setOlder((o) => [...o, d]))
      .catch((e) => setOlder((o) => [...o, { entries: [], more: false, error: e.message }]))
      .finally(() => setLoadingOlder(false))
  }
  const byRun = []
  for (const e of [...data.entries, ...older.flatMap((d) => d.entries)]) {
    if (!byRun.length || byRun[byRun.length - 1].run !== e.run_id) byRun.push({ run: e.run_id, items: [] })
    byRun[byRun.length - 1].items.push(e)
  }
  return (
    <div className="stack stack-3">
      {pills}
      {byRun.length === 0 && <p className="muted">No changes of this kind yet.</p>}
      {byRun.map(({ run, items }) => {
        const initial = (all.baseline_runs || []).includes(run)
        const open = openRuns[run] ?? (filter !== 'all' || !initial)
        return (
          <div key={run} className="bm-log card">
            <div className="bm-log-head">
              <strong>Run #{run}</strong>
              <span className="muted bm-small">{items[0].reason?.replace('_', ' ')}{items[0].actor ? ` · by ${items[0].actor}` : ''}</span>
              <span className="muted">{fmtWhen(items[0].changed_at)} · {items.length} entr{items.length === 1 ? 'y' : 'ies'}
                {initial ? ' · first import' : ''}</span>
              <button type="button" className="btn btn-ghost bm-small" onClick={() => setOpenRuns((o) => ({ ...o, [run]: !open }))}>
                {open ? 'Hide' : 'Show'}
              </button>
            </div>
            {open && (
              <table className="bm-list">
                <thead><tr><th>Change</th><th>Row</th><th>Column</th><th>Old</th><th>New</th><th>Source</th></tr></thead>
                <tbody>
                  {items.map((e) => (
                    <tr key={e.id} className={e.needs_review ? 'bm-flag' : ''}>
                      <td><span className={`bm-type bm-t-${e.type}`}>{e.type.replace('_', ' ')}</span>
                        {e.direction === 'better' && <span className="bm-better"> ▲</span>}
                        {e.direction === 'worse' && <span className="bm-worse"> ▼</span>}
                        {e.news && <span className={`bm-newstag bm-news-${e.news}`}>{NEWS_LABEL[e.news]}</span>}</td>
                      <td>{e.row}</td>
                      <td>{e.column || <span className="muted">{e.note}</span>}
                        {e.column && e.note && <div className="muted bm-small">{e.note}</div>}</td>
                      <td className="bm-num" title={sideTitle(e, 'old')}>{withOutOf(e.old, e.old_out_of)}</td>
                      <td className="bm-num" title={sideTitle(e, 'new')}>{withOutOf(e.new, e.new_out_of)}</td>
                      <td className="muted">{e.new_detail?.source_label || e.old_detail?.source_label || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )
      })}
      {last.error && <p className="bm-error">{last.error}</p>}
      {last.more && (
        <button type="button" className="btn btn-ghost bm-small" style={{ alignSelf: 'flex-start' }} onClick={loadOlder} disabled={loadingOlder}>
          {loadingOlder ? 'Loading…' : 'Load older runs'}
        </button>
      )}
    </div>
  )
}

function Runs({ data, onView }) {
  // Older runs, loaded a batch at a time ("Show older runs").
  const [older, setOlder] = useState([])
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [olderError, setOlderError] = useState(null)
  useEffect(() => { setOlder([]); setOlderError(null) }, [data])
  if (!data) return <p className="muted">Loading…</p>
  if (data.error) return <p className="bm-error">{data.error}</p>
  if (!data.runs.length) return <p className="muted">No runs yet.</p>
  const all = [...data.runs, ...older.flatMap((d) => d.runs)]
  const more = older.length ? older[older.length - 1].more : data.more
  const loadOlder = () => {
    setLoadingOlder(true); setOlderError(null)
    benchmarksRuns(all[all.length - 1].id)
      .then((d) => setOlder((o) => [...o, d]))
      .catch((e) => setOlderError(e.message))
      .finally(() => setLoadingOlder(false))
  }
  return (
    <div className="stack stack-3">
      <table className="bm-list">
        <thead><tr><th>Run</th><th>Started</th><th>Trigger</th><th>Status</th><th>Sources</th><th>Cells</th><th>Changes</th><th /></tr></thead>
        <tbody>
          {all.map((r) => {
            const sources = Object.entries(r.sources || {})
            const ok = sources.filter(([, s]) => s.status === 'OK').length
            return (
              <tr key={r.id}>
                <td>#{r.id}{r.dry_run && <span className="bm-pill">dry run</span>}</td>
                <td>{fmtWhen(r.started_at)}</td>
                <td className="muted">{r.trigger.replace('_', ' ')}{r.scope !== 'all' && ` · ${r.scope}`}</td>
                <td><span className={`bm-status bm-s-${r.status}`}>{r.status.replace('_', ' ')}</span></td>
                <td title={sources.map(([k, s]) => `${k}: ${s.status}${s.errors?.length ? ` - ${s.errors[0]}` : ''}`).join('\n')}>
                  {sources.length ? `${ok} of ${sources.length} read` : '—'}
                </td>
                <td className="bm-num">{r.totals?.cells ?? '—'}</td>
                <td className="bm-num">{r.totals?.changes ?? '—'}</td>
                <td><button type="button" className="btn btn-ghost bm-small" onClick={() => onView(r.id)}>Log</button></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {olderError && <p className="bm-error">{olderError}</p>}
      {more && (
        <button type="button" className="btn btn-ghost bm-small" style={{ alignSelf: 'flex-start' }} onClick={loadOlder} disabled={loadingOlder}>
          {loadingOlder ? 'Loading…' : 'Show older runs'}
        </button>
      )}
    </div>
  )
}

const ACTION_LABEL = { alias: 'Same model as', new_row: 'Added as new row', ignore: 'Ignored' }

function UnmatchedRow({ group, onDone }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const act = async (action, target = null) => {
    setBusy(true); setError(null)
    try {
      await decideBenchmarkName({ key: group.key, name: group.name, action, target })
      onDone()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <tr>
      <td>
        <strong>{group.name}</strong>
        {group.similar_to.length > 0 && (
          <div className="bm-small">looks like: {group.similar_to.map((t) => t.name).join(' · ')}</div>
        )}
        {group.raw_names.some((n) => n !== group.name) && (
          <div className="muted bm-small">as written: {group.raw_names.join(' · ')}</div>
        )}
      </td>
      <td className="bm-small">{group.sources.length} · <span className="muted">{group.sources.join(', ')}</span></td>
      <td className="muted bm-small">{group.reasons.map((r) => r.replaceAll('_', ' ')).join(', ')}</td>
      <td>
        {group.decidable ? (
          <div className="bm-decide">
            {group.similar_to.map((t) => (
              <button key={t.id} type="button" className="btn btn-ghost bm-small" disabled={busy}
                      title={t.id} onClick={() => act('alias', t.id)}>
                Same model as {t.name}
              </button>
            ))}
            <button type="button" className="btn btn-quiet bm-small" disabled={busy} onClick={() => act('ignore')}>Ignore</button>
          </div>
        ) : <span className="muted bm-small">a setting word for a known model - see Review</span>}
        {error && <div className="bm-error">{error}</div>}
      </td>
    </tr>
  )
}

function Unmatched({ data, onChanged }) {
  if (!data) return <p className="muted">Loading…</p>
  if (data.error) return <p className="bm-error">{data.error}</p>
  const names = Object.fromEntries((data.targets || []).map((t) => [t.id, t.name]))
  const undo = async (key) => { await undoBenchmarkName(key); onChanged() }
  return (
    <div className="stack stack-3">
      <p className="muted bm-small">
        Only models in the registry are considered. Registry and tracked models are matched exactly; listed here
        are names that look almost the same as a registry name (same numbers, only words like &quot;Claude&quot; or
        &quot;Instruct&quot; differ) - confirm with <b>Same model as</b> or Ignore - and known models whose setting or
        date the run could not read (add the word to <code>contract/benchmarks/settings_vocabulary.yaml</code>).
        Names of models that are not in the registry are not listed (each run&apos;s log counts them). Earlier
        decisions stay below and can be undone.
      </p>
      {data.groups.length === 0 ? <p className="muted">Nothing unmatched.</p> : (
        <table className="bm-list">
          <thead><tr><th>Name</th><th>Sources</th><th>Why</th><th>Decide</th></tr></thead>
          <tbody>
            {data.groups.map((g) => <UnmatchedRow key={g.key} group={g} onDone={onChanged} />)}
          </tbody>
        </table>
      )}
      {data.decisions.length > 0 && (
        <div className="stack stack-1">
          <h3 className="bm-h3">Decisions ({data.decisions.length})</h3>
          <table className="bm-list">
            <thead><tr><th>Name</th><th>Decision</th><th>When</th><th /></tr></thead>
            <tbody>
              {data.decisions.map((d) => (
                <tr key={d.key}>
                  <td>{d.name}</td>
                  <td>{ACTION_LABEL[d.action]}{d.action === 'alias' && <> <b>{names[d.target] || d.target}</b></>}</td>
                  <td className="muted bm-small">{fmtWhen(d.at)}</td>
                  <td><button type="button" className="btn btn-quiet bm-small" onClick={() => undo(d.key)}>Undo</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Review({ data }) {
  if (!data) return <p className="muted">Loading…</p>
  if (data.error) return <p className="bm-error">{data.error}</p>
  if (!data.items.length) return <p className="muted">No open review items.</p>
  return (
    <div className="stack stack-2">
      <p className="muted bm-small">Flags from the checks. Each value stays published; resolving them (accept, override,
        suppress) comes with the admin edits in phase 2.</p>
      <table className="bm-list">
        <thead><tr><th>Check</th><th>Source</th><th>Row</th><th>Message</th><th>Run</th></tr></thead>
        <tbody>
          {data.items.map((i) => (
            <tr key={i.id}>
              <td><span className="bm-type">{i.check.replaceAll('_', ' ')}</span></td>
              <td className="muted">{i.source || '—'}</td>
              <td>{i.row || '—'}{i.column ? <span className="muted"> · {i.column}</span> : null}</td>
              <td>{i.message}</td>
              <td className="muted">#{i.run_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// sources.yaml records "Not stated on the page." when a page gives no licence:
// a note for us, not for the reader, so only a real licence is shown (2026-10-27).
const hasLicense = (license) => Boolean(license) && !/^not stated/i.test(license)

// The tiers, in the words sources.yaml and the server use (2026-10-27).
function TierBadge({ tier }) {
  return tier ? <span className={`bm-tier bm-tier-${tier}`}>Tier {tier}</span> : null
}

function Sources({ sources }) {
  const order = { enabled: 0, disabled: 1 }
  const list = [...sources].sort(
    (a, b) => order[a.state] - order[b.state] || (a.tier ?? 9) - (b.tier ?? 9)
      || b.priority - a.priority || a.label.localeCompare(b.label),
  )
  const tiers = [...new Map(list.filter((s) => s.tier).map((s) => [s.tier, s.tier_label])).entries()].sort()
  const count = (tier) => list.filter((s) => s.tier === tier).length
  return (
    <div className="stack stack-2">
      <p className="muted bm-small">
        Every page a run reads, hardcoded in <code>contract/benchmarks/sources.yaml</code>. A run asks only these
        pages (and each site&apos;s robots.txt); no other site is searched or visited. Each source is fetched once per run.
      </p>
      <div className="bm-tiers">
        {tiers.map(([tier, label]) => (
          <div key={tier} className="bm-small"><TierBadge tier={tier} /> {label} · {count(tier)} source{count(tier) === 1 ? '' : 's'}</div>
        ))}
        {!tiers.some(([t]) => t === 3) && (
          <div className="bm-small"><TierBadge tier={3} /> another third party · none used now</div>
        )}
        <p className="muted bm-small">
          A cell shows the highest tier that has a value for it. A lower tier fills a cell only when no higher tier
          has one, and its value is still listed in the cell&apos;s hover when a higher tier is shown.
        </p>
      </div>
      <table className="bm-list">
        <thead><tr><th>Source</th><th>Tier</th><th>Fills</th><th>Fetched by</th><th>Read as</th><th>Last run</th></tr></thead>
        <tbody>
          {list.map((s) => (
            <tr key={s.key}>
              <td>
                <a href={s.url} target="_blank" rel="noreferrer noopener nofollow">{s.label}</a>
                <div className="muted bm-small">{s.url}</div>
                <span className={`bm-status bm-s-${s.state === 'enabled' ? 'ok' : 'error'}`}>
                  {s.state}
                </span>
                {s.in_table && <span className="bm-status bm-s-ok">in the table</span>}
                {s.why && <div className="muted bm-small">{s.why}</div>}
                {s.attribution && (
                  <div className="muted bm-small">{s.attribution}{hasLicense(s.license) ? ` · ${s.license}` : ''}</div>
                )}
              </td>
              <td className="bm-small">
                <TierBadge tier={s.tier} />
                <div>{s.tier_label}</div>
                {s.tier_note && <div className="muted">{s.tier_note}</div>}
                <div className="muted">priority {s.priority} within the tier</div>
              </td>
              <td>{s.fills.length ? s.fills.join(', ') : <span className="muted">—</span>}</td>
              <td className="bm-small">{s.fetcher}
                <div className="muted">{s.kind}</div></td>
              <td className="bm-small">{s.readers.join(', ') || '—'}</td>
              <td className="bm-small">
                {s.last ? (
                  <>
                    <div>run #{s.last.run_id} · {s.last.status}{s.last.http_status ? ` · HTTP ${s.last.http_status}` : ''}</div>
                    <div className="muted">{s.last.rows ?? 0} rows read · {s.last.matched ?? 0} models matched · {s.last.values ?? 0} values</div>
                    {s.last.error && <div className="bm-error">{s.last.error}</div>}
                  </>
                ) : <span className="muted">not read yet</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── the page ────────────────────────────────────────────────────────────── */

export default function Benchmarks() {
  useHead(PRIVATE.benchmarks)
  const [tab, setTab] = useState('table')
  const [refreshKey, setRefreshKey] = useState(0)
  const [viewRun, setViewRun] = useState(null)
  const { table, error, extra } = useBenchData(tab, refreshKey)
  const refresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  if (error) {
    return (
      <div className="shell section-tight stack stack-3">
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Benchmarks</h1>
        {error instanceof BoardUnreadable
          ? <Unreadable detail={error.message} compact />
          : <p className="bm-error">{error.message}</p>}
      </div>
    )
  }

  const last = table?.last_run
  return (
    <div className="shell section-tight stack stack-4 bm-page">
      <div className="stack stack-1">
        <span className="eyebrow">Signed in</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Benchmarks</h1>
        <p className="muted">
          Published results for the {table?.counts.models ?? 'tracked'} tracked text models, from public leaderboards.
          Each cell shows the most trusted source&apos;s value (the benchmark&apos;s own leaderboard first); scores are
          percentages to two decimals and ranks are the board&apos;s own. Hover a value for its source, the
          source&apos;s own text and the date.
        </p>
        {last && (
          <p className="muted bm-small">
            Last published run #{last.id}, {last.status}, {fmtWhen(last.finished_at || last.started_at)}
            {table && <> · {table.counts.setting_rows} setting rows · sources and their attribution are on the Sources tab</>}
          </p>
        )}
      </div>

      <RunPanel onFinished={refresh} viewRun={viewRun} clearView={() => setViewRun(null)}
                savedPages={table?.counts.saved_pages ?? 0} />

      <nav className="bm-tabs" aria-label="Benchmarks views">
        {TABS.map(([id, label]) => (
          <button key={id} type="button" className={`bm-tab${tab === id ? ' on' : ''}`}
                  aria-current={tab === id ? 'page' : undefined} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      {tab === 'table' && (table ? <BenchTable data={table} /> : <p className="muted">Loading…</p>)}
      {tab === 'changes' && <Changelog data={extra.changes} />}
      {tab === 'runs' && <Runs data={extra.runs} onView={(id) => { setViewRun(id); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />}
      {tab === 'unmatched' && <Unmatched data={extra.unmatched} onChanged={refresh} />}
      {tab === 'review' && <Review data={extra.review} />}
      {tab === 'sources' && (table ? <Sources sources={table.sources} /> : <p className="muted">Loading…</p>)}

    </div>
  )
}
