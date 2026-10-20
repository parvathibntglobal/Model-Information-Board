import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminSeoKeywords } from '../api'
import { Notice } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import '../styles/keywords.css'

/**
 * SEO KEYWORDS (2026-10-19, Parvathi): which SEO keywords sit on which public
 * page of the board, and where on it - title, meta description, headings,
 * links, body, navigation, footer, structured data. SIGNED-IN ONLY, like Admin.
 * At /seo-keywords; /keywords redirects here.
 *
 * ONE PILL PER PAGE. Clicking a pill opens that page's view: its title,
 * description and H1 as they are, and the table of keywords found on it. The
 * page lives in the address (`?page=/catalog`), so a view can be sent to
 * somebody. "All pages" shows every placement at once.
 *
 * EVERY COLUMN SORTS AND FILTERS, like the workbook: click a header to sort;
 * the row under the headers filters that column - text columns by "contains",
 * columns with a short list of values by a pick list, number columns by a
 * minimum. Filters combine.
 *
 * THE DATA IS A DATED SNAPSHOT (GET /admin/seo-keywords, judge/keywords_on_site.py):
 * every public tab rendered and each keyword of the SEO workbook matched
 * against the text actually on it. Search volumes are Keyword Planner bands
 * from that workbook only; a blank means none was measured. Two workbook
 * columns are left out on purpose - the sheet bookkeeping and the unmeasured
 * demand guess.
 */
// filter kinds: text = contains · pick = one of the values in the data · min = at least · place = has this placement
const COLS = [
  { k: 'keyword', h: 'Keyword', f: 'text' },
  { k: 'tab', h: 'Tab', f: 'pick' },
  { k: 'path', h: 'URL path', f: 'pick', mono: true },
  { k: 'placements', h: 'Placements', f: 'place' },
  { k: 'body_count', h: 'Times in body text', f: 'min', num: true },
  { k: 'combo', h: 'Combo code', f: 'text', mono: true },
  { k: 'categories', h: 'Categories (master matrix)', f: 'pick', split: true },
  { k: 'subcategories', h: 'Sub-categories (master matrix)', f: 'pick', split: true },
  { k: 'slots', h: 'Slot roles', f: 'pick', split: true },
  { k: 'legality', h: 'Legality', f: 'pick' },
  { k: 'target', h: 'Target page (SEO workbook)', f: 'pick' },
  { k: 'volume', h: 'Search volume / month (Keyword Planner band)', f: 'pick', sortKey: 'volume_floor', mono: true },
  { k: 'volume_floor', h: 'Volume band floor', f: 'min', num: true },
  { k: 'volume_source', h: 'Volume source', f: 'pick' },
]
const SHORT = { 'Meta description': 'Meta', 'Link text': 'Link', 'Image alt': 'Alt', 'Body text': 'Body', 'Navigation': 'Nav', 'Structured data': 'JSON-LD' }
const EMPTY = '(blank)'
const parts = (c, v) => (c.split ? String(v || '').split(' + ').filter(Boolean) : [v == null || v === '' ? EMPTY : String(v)])

export default function Keywords() {
  useHead(PRIVATE.keywords)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [sp, setSp] = useSearchParams()
  const page = sp.get('page') || ''
  const [f, setF] = useState({})
  const [measured, setMeasured] = useState(false)
  const [sort, setSort] = useState({ k: 'volume_floor', dir: -1 })

  useEffect(() => { adminSeoKeywords().then(setData).catch((e) => setErr(e.message)) }, [])

  const tab = data?.tabs?.find((t) => t.path === page)
  const onPage = useMemo(() => (data?.rows || []).filter((r) => !page || r.path === page), [data, page])
  const unique = useMemo(() => new Set((data?.rows || []).map((r) => r.keyword)).size, [data])
  // the values each pick list offers, from the rows of the page being shown
  const options = useMemo(() => {
    const o = {}
    COLS.filter((c) => c.f === 'pick').forEach((c) => {
      const s = new Set()
      onPage.forEach((r) => parts(c, r[c.k]).forEach((v) => s.add(v)))
      o[c.k] = [...s].sort((a, b) => (a === EMPTY) - (b === EMPTY) || a.localeCompare(b, undefined, { numeric: true }))
    })
    return o
  }, [onPage])

  const rows = useMemo(() => {
    const keep = (r) => COLS.every((c) => {
      const v = f[c.k]
      if (v == null || v === '') return true
      if (c.f === 'text') return String(r[c.k] || '').toLowerCase().includes(String(v).trim().toLowerCase())
      if (c.f === 'pick') return parts(c, r[c.k]).includes(v)
      if (c.f === 'min') return Number(r[c.k] || 0) >= Number(v)
      if (c.f === 'place') return r.placements.includes(v)
      return true
    }) && (!measured || r.volume)
    const key = COLS.find((c) => c.k === sort.k)?.sortKey || sort.k
    const val = (r) => (key === 'placements' ? r.placements.length : r[key])
    return onPage.filter(keep).sort((a, b) => {
      const x = val(a), y = val(b)
      if (x == null || x === '') return 1
      if (y == null || y === '') return -1
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })) * sort.dir
    })
  }, [onPage, f, measured, sort])

  const active = Object.values(f).filter((v) => v !== '' && v != null).length + (measured ? 1 : 0)
  const set = (k, v) => setF((o) => ({ ...o, [k]: v }))
  const pick = (path) => { const n = new URLSearchParams(sp); if (path) n.set('page', path); else n.delete('page'); setSp(n) }

  const head = (c) => {
    const on = sort.k === c.k
    return (
      <th key={c.k} className={c.num ? 'num' : undefined} aria-sort={on ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none'}>
        <button type="button" className="kw-sort" title="Sort by this column"
                onClick={() => setSort({ k: c.k, dir: on ? -sort.dir : c.num || c.k === 'volume' ? -1 : 1 })}>
          {c.h}<span aria-hidden="true">{on ? (sort.dir > 0 ? ' ▲' : ' ▼') : ' ↕'}</span>
        </button>
      </th>
    )
  }
  const filterCell = (c) => {
    const v = f[c.k] ?? ''
    const label = `Filter ${c.h}`
    let input
    if (c.f === 'text') input = <input type="search" value={v} onChange={(e) => set(c.k, e.target.value)} placeholder="contains…" aria-label={label} />
    else if (c.f === 'min') input = <input type="number" min="0" value={v} onChange={(e) => set(c.k, e.target.value)} placeholder="at least…" aria-label={label} />
    else {
      const opts = c.f === 'place' ? data.placements : options[c.k] || []
      input = (
        <select value={v} onChange={(e) => set(c.k, e.target.value)} aria-label={label}>
          <option value="">All</option>
          {opts.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      )
    }
    return <th key={c.k} className={`kw-filter ${v !== '' ? 'kw-filter-on' : ''}`}>{input}</th>
  }

  if (err) return <div className="shell section-tight"><Notice icon={<IconAlert />}>The keyword snapshot could not be read: {err}</Notice></div>
  if (!data) return <div className="shell section-tight"><div className="skel" style={{ height: 320 }} /></div>
  if (!data.available) {
    return (
      <div className="shell section-tight">
        <Notice icon={<IconAlert />}>No keyword snapshot yet. Run <code>scripts/export_keywords_on_site.py</code> to make <code>seo/keywords_on_site.json</code>.</Notice>
      </div>
    )
  }

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="eyebrow">Signed in · Keyword dashboard</span>
        <h1 style={{ fontSize: 'var(--fs-h2)' }}>SEO keywords</h1>
        <p className="muted" style={{ maxWidth: '78ch' }}>
          Which keywords from our SEO workbook are on each public page, and where: title, description, headings,
          links, body, navigation and footer. Search volumes are Google Keyword Planner bands from the workbook;
          a blank means none was measured.
        </p>
        <p className="kw-meta mono">
          Snapshot {data.built} · {data.tabs.length} pages · {data.rows.length} placements · {unique} keywords · source {data.source}
        </p>
      </div>

      <nav className="kw-pills" aria-label="Pages">
        <button type="button" className={`chip ${!page ? 'chip-on' : ''}`} onClick={() => pick('')}>
          All pages <span className="x">{data.rows.length}</span>
        </button>
        {data.tabs.map((t) => (
          <button key={t.path} type="button" className={`chip ${page === t.path ? 'chip-on' : ''}`} onClick={() => pick(t.path)}>
            {t.tab} <span className="x">{t.keywords}</span>
          </button>
        ))}
      </nav>

      {tab && (
        <section className="card stack stack-2" aria-label={`${tab.tab} page`}>
          <div className="kw-tab-head">
            <div className="stack stack-1">
              <span className="label">{tab.tab}</span>
              <span className="mono kw-path">{tab.path}</span>
            </div>
            <Link to={tab.path} target="_blank" rel="noopener" className="btn btn-ghost">Open page ↗</Link>
          </div>
          <dl className="kw-facts">
            <dt>Title <small>{(tab.title || '').length} chars</small></dt><dd>{tab.title || '—'}</dd>
            <dt>Meta description <small>{(tab.description || '').length} chars</small></dt><dd>{tab.description || '—'}</dd>
            <dt>H1</dt><dd>{tab.h1 || '—'}</dd>
            <dt>Headings</dt><dd>{tab.h2_count} H2 · {tab.h3_count} H3</dd>
            <dt>Keywords</dt>
            <dd>{tab.keywords} on this page · {rowsOn(data.rows, tab.path, 'Title')} in the title · {rowsOn(data.rows, tab.path, 'H1')} in the H1 · {rowsOn(data.rows, tab.path, 'Meta description')} in the description</dd>
            {tab.note && (<><dt>Note</dt><dd className="kw-note">{tab.note}</dd></>)}
          </dl>
        </section>
      )}

      <div className="kw-filters">
        <label className="kw-check"><input type="checkbox" checked={measured} onChange={(e) => setMeasured(e.target.checked)} /> Measured volume only</label>
        <button type="button" className="btn btn-ghost kw-clear" onClick={() => { setF({}); setMeasured(false) }} disabled={!active}>
          Clear filters{active ? ` (${active})` : ''}
        </button>
        <span className="kw-hint muted">Click a header to sort · use the row under the headers to filter each column</span>
        <span className="kw-count mono">{rows.length} of {onPage.length} shown</span>
      </div>

      <div className="kw-scroll">
        <table className="kw-table">
          <thead>
            <tr>{COLS.map(head)}</tr>
            <tr className="kw-filter-row">{COLS.map(filterCell)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.path}|${r.keyword}|${i}`}>
                <th scope="row" className="kw-kw">{r.keyword}</th>
                <td>{r.tab}</td>
                <td className="mono">{r.path}</td>
                <td className="kw-places">{r.placements.map((p) => <span key={p} className={`kw-place ${p === 'Title' || p === 'H1' ? 'kw-strong' : ''}`}>{SHORT[p] || p}</span>)}</td>
                <td className="num mono">{r.body_count}</td>
                <td className="mono">{r.combo || ''}</td>
                <td>{r.categories || ''}</td>
                <td>{r.subcategories || ''}</td>
                <td>{r.slots || ''}</td>
                <td>{r.legality || ''}</td>
                <td>{r.target || ''}</td>
                <td className="mono">{r.volume || ''}</td>
                <td className="num mono">{r.volume_floor ?? ''}</td>
                <td>{r.volume_source || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <p className="muted kw-empty">No keyword matches these filters.</p>}
      </div>
    </div>
  )
}

function rowsOn(rows, path, place) {
  return rows.filter((r) => r.path === path && r.placements.includes(place)).length
}
