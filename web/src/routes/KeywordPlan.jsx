import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminSeoKeywordPlan } from '../api'
import { Notice } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'

/**
 * KEYWORD PLAN (2026-10-19, anooj): which keywords to use on which PUBLIC page.
 *
 * Every combination on the SEO workbook's Combinations sheet, expanded with the
 * board's own values (seo/keyword_plan.yaml), and kept when people search it
 * at least `min_monthly_searches` times a month - 10,000 by default. The
 * volume is a Google Keyword Planner band from the workbook, or an ESTIMATE
 * from one: the head term's measured band x the share of searches that add
 * that modifier, a share the build MEASURES from the workbook's own pairs.
 * A keyword with neither is not shown (scripts/build_keyword_plan.py).
 *
 * PAGES are the site's page layouts, not every post or comparison: a blog
 * post, a model page, a comparison are one page each, and a keyword names the
 * one it belongs on (its link). Pages that do not exist yet are suggested as
 * NEW PAGES or NEW TOOLS, with the keywords that would justify them. Nothing
 * behind the sign-in is a target: a search visitor cannot reach it.
 */
const GROUPS = [
  { kind: 'page', label: 'Pages on the site' },
  { kind: 'new-page', label: 'Suggested new pages' },
  { kind: 'new-tool', label: 'Suggested new tools' },
]
const STEP = 300
const fmt = (n) => (n == null ? '' : Number(n).toLocaleString('en-US'))

export default function KeywordPlan() {
  useHead(PRIVATE.keywords)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [sp, setSp] = useSearchParams()
  const pageKey = sp.get('p') || ''
  const [below, setBelow] = useState(false)
  const [q, setQ] = useState('')
  const [sort, setSort] = useState({ k: 'searches', dir: -1 })
  const [shown, setShown] = useState(STEP)

  useEffect(() => { adminSeoKeywordPlan().then(setData).catch((e) => setErr(e.message)) }, [])

  const floor = data?.min_monthly_searches || 0
  const pages = useMemo(() => new Map((data?.pages || []).map((p) => [p.key, p])), [data])
  const inScope = useMemo(
    () => (data?.keywords || []).filter((k) => below || k.searches >= floor),
    [data, below, floor],
  )
  const perPage = useMemo(() => {
    const c = {}
    inScope.forEach((k) => { c[k.page] = (c[k.page] || 0) + 1 })
    return c
  }, [inScope])
  const page = pageKey ? pages.get(pageKey) : null

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const keep = (k) => (!pageKey || k.page === pageKey)
      && (!needle || k.keyword.toLowerCase().includes(needle) || (k.pattern || '').toLowerCase().includes(needle))
    const val = (k) => (sort.k === 'page' ? pages.get(k.page)?.name : k[sort.k])
    return inScope.filter(keep).sort((a, b) => {
      const x = val(a), y = val(b)
      if (x == null || x === '') return 1
      if (y == null || y === '') return -1
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })) * sort.dir
    })
  }, [inScope, pageKey, q, sort, pages])

  useEffect(() => { setShown(STEP) }, [pageKey, below, q, sort])

  const choose = (key) => setSp(key ? { tab: 'plan', p: key } : { tab: 'plan' })
  const th = (k, label, num) => {
    const on = sort.k === k
    return (
      <th className={num ? 'num' : undefined} aria-sort={on ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none'}>
        <button type="button" className="kw-sort" onClick={() => setSort({ k, dir: on ? -sort.dir : num ? -1 : 1 })}>
          {label}<span aria-hidden="true">{on ? (sort.dir > 0 ? ' ▲' : ' ▼') : ' ↕'}</span>
        </button>
      </th>
    )
  }

  if (err) return <div className="shell section-tight"><Notice icon={<IconAlert />}>The keyword plan could not be read: {err}</Notice></div>
  if (!data) return <div className="shell section-tight"><div className="skel" style={{ height: 320 }} /></div>
  if (!data.available) {
    return (
      <div className="shell section-tight">
        <Notice icon={<IconAlert />}>No keyword plan yet. Run <code>scripts/build_keyword_plan.py</code> to make <code>seo/keyword_plan.json</code>.</Notice>
      </div>
    )
  }
  const m = data.method || {}
  const c = m.counts || {}
  const total = data.keywords.length
  const atFloor = data.keywords.filter((k) => k.searches >= floor).length

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="eyebrow">Signed in · Keyword plan</span>
        <h1 style={{ fontSize: 'var(--fs-h2)' }}>Keyword plan</h1>
        <p className="muted" style={{ maxWidth: '80ch' }}>
          Keywords people search at least {fmt(floor)} times a month, worldwide, and the public page each one should be
          used on. Built from every combination on the SEO workbook. A volume is a Google Keyword Planner band from the
          workbook, or an estimate made from one; the table says which.
        </p>
        <p className="kw-meta mono">
          Plan {data.built} · {atFloor} keywords at {fmt(floor)}+ a month · {total - atFloor} with a volume below it ·
          {' '}{fmt(c.no_volume)} generated with no volume · {fmt(c.generated)} generated in all
        </p>
        <details className="kw-method">
          <summary>How the volumes are worked out</summary>
          <div className="stack stack-2" style={{ marginTop: 8 }}>
            <p className="muted">
              <b>Measured</b>: the keyword itself was measured by Keyword Planner ({m.volume_source}). The band is shown;
              its geometric midpoint is used to sort. <b>Estimated</b>: only its head term was measured, so the estimate
              is that head's midpoint times the share of a head's searches that add the modifier. Each share is measured
              from the workbook's own pairs, where a head and its modified form were both measured. A modifier with no
              such pair has no share, and its keywords no estimate.
            </p>
            <table className="kw-table kw-shares">
              <thead><tr><th>Modifier</th><th className="num">Share</th><th>Measured from</th></tr></thead>
              <tbody>
                {Object.entries(m.shares || {}).map(([cls, s]) => (
                  <tr key={cls}>
                    <td className="mono">{cls}</td>
                    <td className="num mono">{s.share == null ? 'none' : `${(100 * s.share).toFixed(1)}%`}</td>
                    <td>{s.pairs.length
                      ? s.pairs.map((p) => `${p.keyword} (${p.band}) / ${p.head} (${p.head_band})`).join(' · ')
                      : 'no measured pair'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted">
              {Object.keys(m.skipped_combinations || {}).length} combinations make no keyword, each with its reason:
              {' '}{Object.entries(m.skipped_combinations || {}).map(([k, why]) => `${k} (${why})`).join(' · ')}.
              {' '}{fmt(c.one_word_dropped)} one-word keywords were dropped: one word is kept only when it names a model.
            </p>
          </div>
        </details>
      </div>

      <div className="stack stack-2">
        <button type="button" className={`chip ${!pageKey ? 'chip-on' : ''}`} style={{ alignSelf: 'flex-start' }} onClick={() => choose('')}>
          All pages <span className="x">{inScope.length}</span>
        </button>
        {GROUPS.map((g) => (
          <div key={g.kind} className="stack stack-1">
            <span className="label">{g.label}</span>
            <nav className="kw-pills" aria-label={g.label}>
              {data.pages.filter((p) => p.kind === g.kind).map((p) => (
                <button key={p.key} type="button" onClick={() => choose(p.key)}
                        className={`chip ${pageKey === p.key ? 'chip-on' : ''} ${perPage[p.key] ? '' : 'kw-chip-none'}`}>
                  {p.name} <span className="x">{perPage[p.key] || 0}</span>
                </button>
              ))}
            </nav>
          </div>
        ))}
      </div>

      {page && (
        <section className="card stack stack-2" aria-label={page.name}>
          <div className="kw-tab-head">
            <div className="stack stack-1">
              <span className="label">{page.kind === 'page' ? 'Page on the site' : page.kind === 'new-page' ? 'Suggested new page' : 'Suggested new tool'}</span>
              <b>{page.name}</b>
              <span className="mono kw-path">{page.url}</span>
            </div>
            {page.kind === 'page' && !page.url.includes('<') && (
              <Link to={page.url} target="_blank" rel="noopener" className="btn btn-ghost">Open page ↗</Link>
            )}
          </div>
          <p className="muted">{page.about}</p>
          <p className="muted">
            {perPage[page.key]
              ? `${perPage[page.key]} keyword${perPage[page.key] === 1 ? '' : 's'} to use on this page${below ? '' : `, each searched ${fmt(floor)}+ times a month`}.`
              : `No keyword reaches ${fmt(floor)} searches a month here${below ? '' : ' - tick "Include keywords below" to see the rest'}.`}
          </p>
        </section>
      )}

      <div className="kw-filters">
        <span className="kw-filters-search">
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find a keyword or pattern…" aria-label="Find a keyword" />
        </span>
        <label className="kw-check">
          <input type="checkbox" checked={below} onChange={(e) => setBelow(e.target.checked)} />
          Include keywords below {fmt(floor)} a month ({total - atFloor})
        </label>
        <span className="kw-count mono">{rows.length} shown</span>
      </div>

      <div className="kw-scroll">
        <table className="kw-table">
          <thead>
            <tr>
              {th('keyword', 'Keyword')}
              {th('searches', 'Searches a month', true)}
              {th('volume_kind', 'Volume')}
              {!pageKey && th('page', 'Use on')}
              {th('link', 'Page link')}
              {th('pattern', 'Pattern')}
              {th('combo', 'Combo code')}
              <th>How it was estimated</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, shown).map((k) => {
              const p = pages.get(k.page)
              return (
                <tr key={k.keyword}>
                  <th scope="row" className="kw-kw">{k.keyword}</th>
                  <td className="num mono">{k.volume}</td>
                  <td className={k.volume_kind === 'estimated' ? 'kw-variant' : undefined}>{k.volume_kind === 'measured' ? 'Measured' : 'Estimated'}</td>
                  {!pageKey && (
                    <td>
                      <button type="button" className="kw-linkbtn" onClick={() => choose(k.page)}>{p?.name || k.page}</button>
                      {p && p.kind !== 'page' && <span className="kw-new"> {p.kind === 'new-tool' ? 'new tool' : 'new page'}</span>}
                    </td>
                  )}
                  <td className="mono">
                    {p?.kind === 'page' && !k.link.includes('<')
                      ? <Link to={k.link} target="_blank" rel="noopener">{k.link}</Link>
                      : k.link}
                  </td>
                  <td className="mono">{k.pattern}</td>
                  <td className="mono">{k.combo}</td>
                  <td className="muted">{k.basis || ''}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!rows.length && <p className="muted kw-empty">No keyword here{below ? '' : ` at ${fmt(floor)}+ a month`}.</p>}
      </div>
      {rows.length > shown && (
        <button type="button" className="btn btn-ghost" style={{ alignSelf: 'flex-start' }} onClick={() => setShown((n) => n + STEP)}>
          Show {Math.min(STEP, rows.length - shown)} more of {rows.length - shown}
        </button>
      )}
    </div>
  )
}
