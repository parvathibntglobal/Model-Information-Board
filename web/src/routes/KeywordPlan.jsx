import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminSeoKeywordPlan } from '../api'
import { Notice } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'

/**
 * KEYWORD PLAN, BY QUERY TYPE (2026-10-19, anooj).
 *
 * A search query is an INTENT plus an ENTITY: "what is system 1 model" is a
 * definition ("what is") of a concept ("system 1 model"). The intent decides
 * what shape of answer wins it - a glossary entry, a comparison table, a model
 * page, a tutorial, first-hand experiences - so each section here is one
 * intent, the page and FORMAT that answers it on this board, how to place the
 * keyword there (title, H1, H2s, links, structured data), and every keyword
 * the intent makes with the entities it fits (seo/keyword_plan.yaml,
 * scripts/build_keyword_plan.py).
 *
 * Two views: BY QUERY TYPE (an intent and its keywords) and BY PAGE (every
 * query type one page should answer). A keyword's link is the exact page that
 * answers it where one exists - a model's page, a pair's comparison, the post
 * already written on a concept; "to write" marks a page that does not yet.
 *
 * A volume is shown only where Google Keyword Planner measured it or a
 * measured share estimates it; everything else says "not measured".
 */
const STEP = 200
const KIND = { page: 'Page on the site', 'new-page': 'Suggested new page', 'new-tool': 'Suggested new tool' }

export default function KeywordPlan() {
  useHead(PRIVATE.keywords)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [sp, setSp] = useSearchParams()
  const view = sp.get('view') === 'page' ? 'page' : 'intent'
  const pick = sp.get('s') || ''
  const [q, setQ] = useState('')
  const [shown, setShown] = useState(STEP)

  useEffect(() => { adminSeoKeywordPlan().then(setData).catch((e) => setErr(e.message)) }, [])

  const pages = useMemo(() => new Map((data?.pages || []).map((p) => [p.key, p])), [data])
  const sections = useMemo(() => data?.sections || [], [data])
  const byKey = useMemo(() => new Map(sections.map((s) => [s.key, s])), [sections])
  const perPage = useMemo(() => {
    const c = {}
    ;(data?.keywords || []).forEach((k) => { c[k.page] = (c[k.page] || 0) + 1 })
    return c
  }, [data])
  const pagesInUse = useMemo(
    () => (data?.pages || []).filter((p) => perPage[p.key]),
    [data, perPage],
  )
  const first = view === 'page' ? pagesInUse[0]?.key : sections[0]?.key
  const sel = pick || first || ''

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (data?.keywords || [])
      .filter((k) => (view === 'page' ? k.page === sel : k.section === sel))
      .filter((k) => !needle || k.keyword.toLowerCase().includes(needle) || k.entity.toLowerCase().includes(needle))
      .sort((a, b) => (b.searches ?? -1) - (a.searches ?? -1))
  }, [data, view, sel, q])

  useEffect(() => { setShown(STEP) }, [view, sel, q])

  const go = (v, s) => setSp({ tab: 'plan', ...(v === 'page' ? { view: 'page' } : {}), ...(s ? { s } : {}) })

  if (err) return <div className="shell section-tight"><Notice icon={<IconAlert />}>The keyword plan could not be read: {err}</Notice></div>
  if (!data) return <div className="shell section-tight"><div className="skel" style={{ height: 320 }} /></div>
  if (!data.available) {
    return (
      <div className="shell section-tight">
        <Notice icon={<IconAlert />}>No keyword plan yet. Run <code>scripts/build_keyword_plan.py</code> to make <code>seo/keyword_plan.json</code>.</Notice>
      </div>
    )
  }
  const c = data.method?.counts || {}
  const section = view === 'intent' ? byKey.get(sel) : null
  const page = view === 'page' ? pages.get(sel) : null
  const pageSections = page ? sections.filter((s) => s.page === page.key) : []

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="eyebrow">Signed in · Keyword plan</span>
        <h1 style={{ fontSize: 'var(--fs-h2)' }}>Keyword plan</h1>
        <p className="muted" style={{ maxWidth: '82ch' }}>
          A search is an intent plus a subject: <i>what is</i> + <i>system 1 model</i>. The intent decides which kind of
          answer wins it, so each query type below says which page answers it here, in what format, and how to place
          the keyword: title, heading, links and structured data. Then every keyword it makes.
        </p>
        <p className="kw-meta mono">
          Plan {data.built} · {c.keywords?.toLocaleString('en-US')} keywords in {sections.length} query types ·
          {' '}{c.concepts} concepts · {c.models} models · {c.measured} measured · {c.estimated} estimated ·
          {' '}{c.posts_to_write?.toLocaleString('en-US')} concept keywords with no post yet
        </p>
      </div>

      <div className="kw-tabs" role="tablist" aria-label="Plan views">
        <button type="button" role="tab" aria-selected={view === 'intent'} className={`kw-tab ${view === 'intent' ? 'kw-tab-on' : ''}`} onClick={() => go('intent')}>By query type</button>
        <button type="button" role="tab" aria-selected={view === 'page'} className={`kw-tab ${view === 'page' ? 'kw-tab-on' : ''}`} onClick={() => go('page')}>By page</button>
      </div>

      <nav className="kw-pills" aria-label={view === 'page' ? 'Pages' : 'Query types'}>
        {view === 'intent'
          ? sections.map((s) => (
            <button key={s.key} type="button" className={`chip ${sel === s.key ? 'chip-on' : ''}`} onClick={() => go('intent', s.key)}>
              {s.name} <span className="x">{s.keywords}</span>
            </button>
          ))
          : pagesInUse.map((p) => (
            <button key={p.key} type="button" className={`chip ${sel === p.key ? 'chip-on' : ''}`} onClick={() => go('page', p.key)}>
              {p.name}{p.kind !== 'page' && <span className="kw-new"> {p.kind === 'new-tool' ? 'new tool' : 'new page'}</span>} <span className="x">{perPage[p.key]}</span>
            </button>
          ))}
      </nav>

      {section && <IntentCard s={section} page={pages.get(section.page)} />}
      {page && (
        <div className="stack stack-2">
          <section className="card stack stack-1">
            <span className="label">{KIND[page.kind]}</span>
            <b>{page.name}</b>
            <span className="mono kw-path">{page.url}</span>
            <p className="muted">Answers {pageSections.length} query type{pageSections.length === 1 ? '' : 's'}: {pageSections.map((s) => s.name).join(' · ')}.</p>
          </section>
          {pageSections.map((s) => <IntentCard key={s.key} s={s} page={page} compact />)}
        </div>
      )}

      <div className="kw-filters">
        <span className="kw-filters-search">
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find a keyword or subject…" aria-label="Find a keyword" />
        </span>
        <span className="kw-count mono">{rows.length.toLocaleString('en-US')} keywords</span>
      </div>

      <div className="kw-scroll">
        <table className="kw-table">
          <thead>
            <tr>
              <th><span className="kw-sort">Keyword</span></th>
              <th><span className="kw-sort">Subject</span></th>
              {view === 'page' && <th><span className="kw-sort">Query type</span></th>}
              <th><span className="kw-sort">Answered at</span></th>
              <th className="num"><span className="kw-sort">Searches a month</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, shown).map((k) => {
              const p = pages.get(k.page)
              return (
                <tr key={k.keyword}>
                  <th scope="row" className="kw-kw">{k.keyword}</th>
                  <td className="muted">{k.entity}</td>
                  {view === 'page' && <td>{byKey.get(k.section)?.name}</td>}
                  <td className="mono">
                    {k.page_exists && p?.kind === 'page'
                      ? <Link to={k.link} target="_blank" rel="noopener">{k.link}</Link>
                      : <>{k.link} <span className="kw-new">{p?.kind === 'page' ? 'to write' : p?.kind === 'new-tool' ? 'new tool' : 'new page'}</span></>}
                  </td>
                  <td className="num mono">
                    {k.volume_kind ? <>{k.volume}{k.volume_kind === 'estimated' && <span className="kw-variant"> est.</span>}</> : <span className="kw-variant">not measured</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!rows.length && <p className="muted kw-empty">No keyword matches.</p>}
      </div>
      {rows.length > shown && (
        <button type="button" className="btn btn-ghost" style={{ alignSelf: 'flex-start' }} onClick={() => setShown((n) => n + STEP)}>
          Show {Math.min(STEP, rows.length - shown)} more of {(rows.length - shown).toLocaleString('en-US')}
        </button>
      )}
    </div>
  )
}

/** One query type: its intent, the page and format that answer it, and how to place it. */
function IntentCard({ s, page, compact }) {
  const pl = s.place || {}
  return (
    <section className="card stack stack-2" aria-label={s.name}>
      <div className="kw-tab-head">
        <div className="stack stack-1">
          <span className="label">{compact ? 'Query type' : 'Query type · combo ' + s.combo}</span>
          <b>{s.name}</b>
        </div>
        {page && (
          <span className="kw-target">
            Answered on <b>{page.name}</b>{page.kind !== 'page' && <span className="kw-new"> {page.kind === 'new-tool' ? 'new tool' : 'new page'}</span>}
            <span className="mono kw-path"> {page.url}</span>
          </span>
        )}
      </div>
      <dl className="kw-facts">
        <dt>Intent words</dt><dd>{s.intent}</dd>
        <dt>Combined with</dt><dd>{s.entity}</dd>
        <dt>Answer format</dt><dd>{s.format}</dd>
        {pl.title && (<><dt>Title</dt><dd className="mono">{pl.title}</dd></>)}
        {pl.h1 && (<><dt>H1</dt><dd className="mono">{pl.h1}</dd></>)}
        {pl.h2 && (<><dt>H2 sections</dt><dd>{pl.h2.join(' · ')}</dd></>)}
        {pl.links && (<><dt>Link to</dt><dd>{pl.links.join(' · ')}</dd></>)}
        {pl.schema && (<><dt>Structured data</dt><dd className="mono">{pl.schema}</dd></>)}
        {!compact && (<><dt>Patterns</dt><dd className="mono">{(s.patterns || []).join(' · ')}</dd></>)}
      </dl>
    </section>
  )
}
