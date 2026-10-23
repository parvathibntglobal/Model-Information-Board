import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Badge, Notice, Stat } from '../components/ui'
import { IconAlert, IconLayers } from '../components/Icons'
import { SECTIONS, isMissingMain, sitePath, useKitePulse, usePrototype, v } from './site'
import './admin.css'

/**
 * KITE PULSE - managing the SEO website for a second product, from this admin.
 * The site itself is previewed at /kite-pulse (KitePulseSite.jsx).
 *
 * Read only for now. Everything here comes from the keyword research sheet
 * (`docs/Kite Pulse - Keyword Research.xlsx` in this folder), converted to JSON by
 * `import_sheet.py` in this folder. The sheet stays the place people edit;
 * re-run the script after changing it. Nothing is written back.
 *
 * The sub-screen and the open page live in the URL (`kp`, `kpp`), like the
 * admin's own `s`, so a page brief is a link somebody can send.
 */

const TABS = [
  ['overview', 'Overview'],
  ['pages', 'Pages'],
  ['map', 'Keyword map'],
  ['keywords', 'Keywords'],
  ['aeo', 'AEO tracking'],
  ['competitors', 'Competitors'],
  ['settings', 'Settings'],
]

const SITE_SECTIONS = SECTIONS.map((s) => s.name)

// The workflow a page moves through. Statuses the sheet uses that are not in
// this list are still counted, after these, under their own name.
const STAGES = ['Not started', 'Brief', 'Draft', 'SEO check', 'Review', 'Published']

const ASSISTANTS = [['chatgpt', 'ChatGPT'], ['perplexity', 'Perplexity'], ['claude', 'Claude'],
  ['gemini', 'Gemini'], ['google_ai', 'Google AI']]

const KEYWORD_LIMIT = 200

export default function KitePulsePanel() {
  const { data, err, model } = useKitePulse()
  const [params, setParams] = useSearchParams()
  const tab = TABS.some(([id]) => id === params.get('kp')) ? params.get('kp') : 'overview'
  const openUrl = params.get('kpp')

  // Keeps the admin's own `s` (and anything else) in the URL.
  const go = (next) => setParams((prev) => {
    const p = new URLSearchParams(prev)
    for (const [k, val] of Object.entries(next)) {
      if (val == null) p.delete(k)
      else p.set(k, val)
    }
    return p
  }, { replace: true })

  const openPage = model && openUrl ? model.site.find((p) => p.url === openUrl) : null

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Kite Pulse — SEO website</span>
        </div>
        {model && <span className="label">{model.pages.length} pages planned</span>}
      </div>
      <div className="card-intro">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          The public pages for Kite Pulse: what each page targets, how far it has got, and whether AI
          assistants mention us. Read from the keyword research sheet
          {data && <> (<span className="mono">{data.source.file}</span>, imported {data.source.imported_on})</>}.
          Edit the sheet, then run <span className="mono">web/src/kitepulse/import_sheet.py</span> to update this.
        </p>
      </div>

      <div className="card-body stack stack-3">
        {err && <Notice icon={<IconAlert />}>The keyword sheet could not be loaded: {err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 160 }} />}

        {model && (
          <>
            <div className="row" style={{ gap: 6, flexWrap: 'wrap' }} role="tablist" aria-label="Kite Pulse screens">
              {TABS.map(([id, label]) => (
                <button key={id} type="button" role="tab" aria-selected={tab === id}
                        className={`chip${tab === id ? ' chip-on' : ''}`}
                        onClick={() => go({ kp: id === 'overview' ? null : id, kpp: null })}>
                  {label}
                  {id === 'pages' && <span className="x">{model.pages.length}</span>}
                  {id === 'keywords' && <span className="x">{model.keywords.length}</span>}
                  {id === 'aeo' && <span className="x">{model.aeo.length}</span>}
                  {id === 'competitors' && <span className="x">{model.competitors.length}</span>}
                </button>
              ))}
            </div>

            <div role="tabpanel">
              {tab === 'overview' && <Overview model={model} onOpen={(url) => go({ kp: 'pages', kpp: url })} />}
              {tab === 'pages' && (openPage
                ? <PageDetail page={openPage} model={model} onBack={() => go({ kpp: null })} />
                : <Pages model={model} onOpen={(url) => go({ kpp: url })} missing={openUrl} />)}
              {tab === 'map' && <KeywordMap model={model} onOpen={(url) => go({ kp: 'pages', kpp: url })} />}
              {tab === 'keywords' && <Keywords model={model} onOpen={(url) => go({ kp: 'pages', kpp: url })} />}
              {tab === 'aeo' && <Aeo model={model} />}
              {tab === 'competitors' && <Competitors model={model} />}
              {tab === 'settings' && <Settings data={data} />}
            </div>
          </>
        )}
      </div>
    </section>
  )
}

/* ------------------------------------------------------------ overview */

function Overview({ model, onOpen }) {
  const { pages, keywords } = model
  const published = pages.filter((p) => p.status === 'Published')
  const p1 = pages.filter((p) => p.priority === 'P1')
  const seo = keywords.filter((k) => k.type === 'SEO').length
  const aeo = keywords.filter((k) => k.type === 'AEO').length
  const withVolume = keywords.filter((k) => k.volume != null).length

  const stageCounts = new Map(STAGES.map((s) => [s, 0]))
  for (const p of pages) {
    const s = p.status || 'No status in sheet'
    stageCounts.set(s, (stageCounts.get(s) || 0) + 1)
  }

  return (
    <div className="stack stack-4">
      <div className="grid g4">
        <Stat n={`${published.length} of ${pages.length}`} l="pages published"
              title={`Pages in the sheet's Page Map tab with status "Published"`} />
        <Stat n={`${p1.filter((p) => p.status === 'Published').length} of ${p1.length}`} l="P1 pages published" />
        <Stat n={keywords.length} l={`keyword rows · ${seo} SEO, ${aeo} AEO`} />
        <Stat n={`${withVolume} of ${keywords.length}`} l="rows with search volume"
              title="Monthly Volume entered in the Keywords tab" />
      </div>

      <div className="stack stack-2">
        <span className="label">Workflow</span>
        <div className="tablewrap"><table>
          <thead><tr>{[...stageCounts.keys()].map((s) => <th key={s}>{s}</th>)}</tr></thead>
          <tbody><tr>{[...stageCounts.values()].map((n, i) => <td key={i} className="tnum">{n}</td>)}</tr></tbody>
        </table></div>
      </div>

      {model.pages.some((p) => p.prototype) && (
        <div className="stack stack-2">
          <span className="label">Prototypes <span className="dim">{model.pages.filter((p) => p.prototype).length}</span></span>
          <div className="tablewrap"><table>
            <thead><tr><th>Page</th><th>Main keyword</th><th>Type</th><th>Priority</th><th /></tr></thead>
            <tbody>
              {model.pages.filter((p) => p.prototype).map((p) => (
                <tr key={p.url}>
                  <td><button type="button" className="mono kp-link" onClick={() => onOpen(p.url)}>{p.url}</button></td>
                  <td>{v(p.main)}</td>
                  <td className="dim">{v(p.type)}</td>
                  <td>{p.priority ? <Badge tone={priorityTone(p.priority)}>{p.priority}</Badge> : '—'}</td>
                  <td><button type="button" className="btn btn-ghost prompt-btn" onClick={() => onOpen(p.url)}>Preview</button></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      )}

      <div className="stack stack-2">
        <span className="label">Pages by website section</span>
        <div className="tablewrap"><table>
          <thead><tr><th>Section</th><th>Pages</th><th>P1</th><th>Published</th></tr></thead>
          <tbody>
            {sectionsInOrder(pages).map(([name, list]) => (
              <tr key={name}>
                <td>{name}</td>
                <td className="tnum">{list.length}</td>
                <td className="tnum">{list.filter((p) => p.priority === 'P1').length}</td>
                <td className="tnum">{list.filter((p) => p.status === 'Published').length}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>
    </div>
  )
}

function sectionsInOrder(pages) {
  const by = new Map()
  for (const p of pages) {
    if (!by.has(p.section)) by.set(p.section, [])
    by.get(p.section).push(p)
  }
  const names = [...SITE_SECTIONS.filter((s) => by.has(s)), ...[...by.keys()].filter((s) => !SITE_SECTIONS.includes(s))]
  return names.map((n) => [n, by.get(n)])
}

const priorityTone = (p) => (p === 'P1' ? 'pass' : p === 'P2' ? 'warn' : 'mute')
const statusTone = (s) => (s === 'Published' ? 'pass' : s && s !== 'Not started' ? 'info' : 'mute')

/* ------------------------------------------------------------ pages */

function Pages({ model, onOpen, missing }) {
  const [prio, setPrio] = useState('all')
  const shown = model.pages.filter((p) => prio === 'all' || p.priority === prio)
  return (
    <div className="stack stack-3">
      {missing && <Notice icon={<IconAlert />}>No page <span className="mono">{missing}</span> in the Page Map.</Notice>}
      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-label="Priority">
        {['all', 'P1', 'P2', 'P3'].map((p) => (
          <button key={p} type="button" aria-pressed={prio === p}
                  className={`chip${prio === p ? ' chip-on' : ''}`} onClick={() => setPrio(p)}>
            {p === 'all' ? 'All priorities' : p}
            <span className="x">{p === 'all' ? model.pages.length : model.pages.filter((x) => x.priority === p).length}</span>
          </button>
        ))}
      </div>
      {sectionsInOrder(shown).map(([name, list]) => (
        <div key={name} className="stack stack-2">
          <span className="label">{name} <span className="dim">{list.length}</span></span>
          <div className="tablewrap"><table>
            <thead>
              <tr><th>Page</th><th>Main keyword</th><th>Type</th><th>Priority</th><th>Status</th>
                <th title="Main / Secondary / FAQ rows in the Keywords tab for this URL">Keywords</th></tr>
            </thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.url}>
                  <td>
                    <button type="button" className="mono kp-link" onClick={() => onOpen(p.url)}>{p.url}</button>
                    {p.prototype && <> <Badge tone="info">prototype</Badge></>}
                  </td>
                  <td>{isMissingMain(p) ? <Badge tone="warn">{p.main || 'none'}</Badge> : p.main}</td>
                  <td className="dim">{v(p.type)}</td>
                  <td>{p.priority ? <Badge tone={priorityTone(p.priority)}>{p.priority}</Badge> : '—'}</td>
                  <td>{p.status ? <Badge tone={statusTone(p.status)}>{p.status}</Badge> : '—'}</td>
                  <td className="tnum dim" style={{ whiteSpace: 'nowrap' }}>
                    {p.main_kws.length} / {p.secondary.length} / {p.faq.length}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      ))}

      {/* PAGES THE SITE STRUCTURE NEEDS AND THE SHEET DOES NOT LIST (site.js,
          PROPOSED). Shown apart, under every priority, so they are never
          mistaken for the sheet's own pages or counted with them. */}
      {model.proposed.length > 0 && (
        <div className="stack stack-2">
          <span className="label">Proposed — not in the keyword sheet yet <span className="dim">{model.proposed.length}</span></span>
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, maxWidth: '78ch' }}>
            The site structure needs these pages. Add them to the sheet&apos;s Page Map to make them part of the plan.
          </p>
          <div className="tablewrap"><table>
            <thead><tr><th>Page</th><th>Type</th><th>Why</th></tr></thead>
            <tbody>
              {model.proposed.map((p) => (
                <tr key={p.url}>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button type="button" className="mono kp-link" onClick={() => onOpen(p.url)}>{p.url}</button>
                    {' '}<Badge tone="warn">proposed</Badge>
                  </td>
                  <td className="dim">{v(p.type)}</td>
                  <td className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{p.notes}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      )}
    </div>
  )
}

const PAGE_TABS = [
  ['brief', 'Brief'],
  ['content', 'Content'],
  ['seo', 'SEO check'],
  ['preview', 'Preview'],
  ['history', 'History'],
]

// What each unbuilt tab will do, said rather than left blank.
const NOT_BUILT = {
  content: 'The page copy, section by section in the layout for its page type, drafted by the writer agent or written by hand. Every product claim is checked against the Product Guide.',
  seo: 'A pass/fail list: title and meta length, main keyword in the H1 and URL, canonical, JSON-LD, internal links from the Page Map notes, no avoided keywords. A page publishes only when it passes.',
  preview: 'The page as a visitor will see it on the Kite Pulse website.',
  history: 'Every version of the page, who changed it, and when it was published.',
}

function PageDetail({ page, model, onBack }) {
  // A page with a prototype opens on it: that is the thing to look at.
  const [tab, setTab] = useState(page.prototype ? 'preview' : 'brief')
  const built = (id) => id === 'brief' || (id === 'preview' && page.prototype)
  return (
    <div className="stack stack-3">
      <div className="row" style={{ gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <button type="button" className="btn btn-ghost prompt-btn" onClick={onBack}>← All pages</button>
        <strong className="mono">{page.url}</strong>
        <Badge tone="mute">{page.type || 'no type'}</Badge>
        {page.priority && <Badge tone={priorityTone(page.priority)}>{page.priority}</Badge>}
        <Badge tone={statusTone(page.status)}>{page.status || 'no status'}</Badge>
        <Link to={sitePath(page.url)} className="btn btn-ghost prompt-btn" style={{ marginLeft: 'auto' }}>
          View in Kite Pulse site →
        </Link>
      </div>

      <div className="tabstrip" role="tablist" aria-label="Page">
        {PAGE_TABS.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>
            {label}{!built(id) && <span className="x">not built</span>}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {tab === 'brief' && <Brief page={page} model={model} />}
        {tab === 'preview' && page.prototype && <Preview page={page} />}
        {!built(tab) && <Notice icon={<IconAlert />}>Not built yet. {NOT_BUILT[tab]}</Notice>}
      </div>
    </div>
  )
}

const VIEWPORTS = [['desktop', 'Desktop', '100%'], ['mobile', 'Phone', '390px']]

/**
 * THE PROTOTYPE, RUNNING, in a sandboxed frame. `allow-scripts` without
 * `allow-same-origin` gives it a unique origin: its calculators run, but it
 * cannot read this admin's storage or session token. `allow-popups` lets its
 * vendor links open in a new tab.
 */
function Preview({ page }) {
  const { html, err } = usePrototype(page.prototype.file)
  const [vp, setVp] = useState('desktop')

  const width = VIEWPORTS.find(([id]) => id === vp)[2]
  return (
    <div className="stack stack-3">
      <div className="row-between" style={{ gap: 'var(--s2)', flexWrap: 'wrap' }}>
        <div className="row" style={{ gap: 6 }} role="group" aria-label="Screen size">
          {VIEWPORTS.map(([id, label]) => (
            <button key={id} type="button" aria-pressed={vp === id}
                    className={`chip${vp === id ? ' chip-on' : ''}`} onClick={() => setVp(id)}>{label}</button>
          ))}
        </div>
        <span className="row" style={{ gap: 10, alignItems: 'center' }}>
          <Badge tone="warn">prototype</Badge>
          <a href={page.prototype.artifact} target="_blank" rel="noopener noreferrer"
             className="btn btn-ghost prompt-btn">Edit in Claude ↗</a>
        </span>
      </div>
      {err && <Notice icon={<IconAlert />}>The prototype could not be loaded: {err}</Notice>}
      {!html && !err && <div className="skel" style={{ height: 480 }} />}
      {html && (
        <div className="kp-frame-wrap">
          <iframe className="kp-frame" title={`Prototype of ${page.url}`} srcDoc={html}
                  sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
                  style={{ width }} />
        </div>
      )}
    </div>
  )
}

function Brief({ page, model }) {
  const mainRow = page.main_kws[0]
  const research = page.kws.filter((k) => k.ranking || k.gap)
  const avoidHits = model.avoid.filter((a) =>
    page.kws.some((k) => (k.keyword || '').toLowerCase().includes((a.keyword || '').toLowerCase())))
  return (
    <div className="stack stack-4">
      <div className="grid g3">
        <Stat n={page.main_kws.length} l="main keyword rows" />
        <Stat n={page.secondary.length} l="secondary keywords" />
        <Stat n={page.faq.length} l="FAQ questions" />
      </div>

      <div className="stack stack-1">
        <span className="label">Main keyword — title, H1 and URL</span>
        <p style={{ margin: 0, fontSize: 'var(--fs-body)' }}>
          {isMissingMain(page)
            ? <Badge tone="warn">Not chosen yet ({page.main || 'empty'})</Badge>
            : <strong>{page.main}</strong>}
          {mainRow?.intent && <span className="dim"> · {mainRow.intent}</span>}
        </p>
      </div>

      {page.notes && (
        <div className="stack stack-1">
          <span className="label">Page plan (Page Map notes)</span>
          <p className="muted" style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 'var(--fs-sm)', lineHeight: 1.6, maxWidth: '90ch' }}>
            {page.notes}
          </p>
        </div>
      )}

      {research.map((k) => (
        <div key={k.id} className="stack stack-1">
          <span className="label">Research for “{k.keyword}”</span>
          {k.ranking && (
            <p className="muted" style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 'var(--fs-sm)', lineHeight: 1.6, maxWidth: '90ch' }}>
              <strong style={{ color: 'var(--text)' }}>Currently ranking: </strong>{k.ranking}
            </p>
          )}
          {k.gap && (
            <p className="muted" style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 'var(--fs-sm)', lineHeight: 1.6, maxWidth: '90ch' }}>
              <strong style={{ color: 'var(--text)' }}>Gap and angle: </strong>{k.gap}
            </p>
          )}
        </div>
      ))}

      <KeywordList title="Secondary keywords — subheadings and body" rows={page.secondary} />
      <KeywordList title="FAQ questions — the FAQ section and its JSON-LD" rows={page.faq} />

      {avoidHits.length > 0 && (
        <Notice icon={<IconAlert />}>
          Keywords on this page contain a term from the avoid list: {avoidHits.map((a) => a.keyword).join(', ')}.
        </Notice>
      )}
    </div>
  )
}

function KeywordList({ title, rows }) {
  if (rows.length === 0) return null
  return (
    <div className="stack stack-2">
      <span className="label">{title} <span className="dim">{rows.length}</span></span>
      <div className="tablewrap"><table>
        <thead><tr><th>Keyword</th><th>Intent</th><th>Group</th><th>Volume</th><th>KD</th></tr></thead>
        <tbody>
          {rows.map((k) => (
            <tr key={k.id}>
              <td>{k.keyword}</td>
              <td className="dim">{v(k.intent)}</td>
              <td className="dim">{v(k.group)}</td>
              <td className="tnum dim">{v(k.volume)}</td>
              <td className="tnum dim">{v(k.kd)}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  )
}

/* ------------------------------------------------------------ keywords */

/* ------------------------------------------------------------ keyword map */

const words = (s) => (s || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(Boolean)
/** Every word of `needle` appears in `hay`: "copilot metrics viewer" contains "copilot metrics". */
const containsWords = (hay, needle) => { const h = new Set(words(hay)); return words(needle).every((w) => h.has(w)) }

/** The page's main keyword: its Main row, else the Page Map's, else none. */
const mainOf = (p) => p.main_kws[0]?.keyword || (!isMissingMain(p) ? p.main : null)

/**
 * WHAT IS WRONG WITH ONE PAGE'S KEYWORDS, in words a sheet editor can act on.
 * Computed from the sheet every time, so fixing the sheet and re-importing
 * clears it; nothing here is stored.
 *
 * The overlap check reads Main and Secondary rows only. FAQ rows are questions
 * ("Does an AI coding analytics tool read our code?") and naming the category
 * in a question is how people ask it, not two pages competing for one search.
 */
function keywordIssues(p, pages) {
  const out = []
  const mains = p.main_kws
  if (mains.length === 0) {
    if (isMissingMain(p)) out.push(p.kws.length ? 'No main keyword chosen' : null)
    else {
      const row = p.kws.find((k) => k.keyword.toLowerCase() === p.main.toLowerCase())
      out.push(row
        ? `Page Map's main keyword "${p.main}" is row ${row.id}, marked ${row.role}: mark it Main`
        : `Page Map's main keyword "${p.main}" has no keyword row`)
    }
  }
  if (mains.length > 1) {
    out.push(`${mains.length} Main rows (${mains.map((k) => `${k.id} "${k.keyword}"`).join(', ')}): keep one, make the others Secondary or move them`)
  }
  if (mains.length === 1 && !isMissingMain(p) && mains[0].keyword.toLowerCase() !== p.main.toLowerCase()) {
    out.push(`Page Map says "${p.main}", the Main row says "${mains[0].keyword}"`)
  }
  for (const k of [...mains, ...p.secondary]) {
    for (const q of pages) {
      const qm = q.url !== p.url && mainOf(q)
      if (qm && words(qm).length >= 2 && containsWords(k.keyword, qm)) {
        out.push(`Row ${k.id} "${k.keyword}" contains ${q.url}'s main keyword "${qm}": the two pages may compete`)
      }
    }
  }
  return out.filter(Boolean)
}

const SUB_SHOWN = 10

function KeywordMap({ model, onOpen }) {
  const [only, setOnly] = useState('issues')
  const rows = useMemo(() => model.pages.map((p) => ({ p, issues: keywordIssues(p, model.pages) })), [model])
  const withIssues = rows.filter((r) => r.issues.length > 0)
  const noRows = rows.filter((r) => r.p.kws.length === 0)
  const shown = only === 'issues' ? withIssues : rows

  // Rows that point at a page the Page Map does not list.
  const planned = new Set(model.site.map((p) => p.url))
  const stray = model.keywords.filter((k) => k.url && !planned.has(k.url))
  const typeMismatch = model.keywords.filter((k) => {
    const p = model.pages.find((x) => x.url === k.url)
    return p && k.page_type && p.type && k.page_type !== p.type
  })

  return (
    <div className="stack stack-3">
      <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
        Each page&apos;s main keyword (title, H1, URL) and its sub keywords (subheadings and body), from the
        Keywords tab&apos;s Main / Secondary / FAQ column. {withIssues.length} of {model.pages.length} pages in the
        Page Map have something to fix; {noRows.length} have no keyword rows at all.
      </p>

      {(stray.length > 0 || typeMismatch.length > 0) && (
        <Notice icon={<IconAlert />}>
          {stray.map((k) => (
            <span key={k.id} style={{ display: 'block' }}>
              Row {k.id} &quot;{k.keyword}&quot; targets <span className="mono">{k.url}</span>, which is not in the Page Map.
            </span>
          ))}
          {typeMismatch.map((k) => (
            <span key={k.id} style={{ display: 'block' }}>
              Row {k.id} says page type &quot;{k.page_type}&quot;; the Page Map says{' '}
              &quot;{model.pages.find((x) => x.url === k.url).type}&quot; for <span className="mono">{k.url}</span>.
            </span>
          ))}
        </Notice>
      )}

      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-label="Which pages">
        {[['issues', 'Pages to fix', withIssues.length], ['all', 'All pages', rows.length]].map(([id, label, n]) => (
          <button key={id} type="button" aria-pressed={only === id}
                  className={`chip${only === id ? ' chip-on' : ''}`} onClick={() => setOnly(id)}>
            {label} <span className="x">{n}</span>
          </button>
        ))}
      </div>

      <div className="tablewrap"><table>
        <thead>
          <tr><th>Page</th><th>Main keyword</th><th>Sub keywords</th>
            <th title="FAQ rows: questions for the page's FAQ section">FAQ</th><th>To fix</th></tr>
        </thead>
        <tbody>
          {shown.length === 0 && <tr><td colSpan={5} className="dim">Nothing to fix.</td></tr>}
          {shown.map(({ p, issues }) => {
            const main = mainOf(p)
            return (
              <tr key={p.url}>
                <td style={{ whiteSpace: 'nowrap' }}>
                  <button type="button" className="mono kp-link" onClick={() => onOpen(p.url)}>{p.url}</button>
                  {p.priority && <> <Badge tone={priorityTone(p.priority)}>{p.priority}</Badge></>}
                </td>
                <td>
                  {main ? <strong>{main}</strong> : <Badge tone="warn">none</Badge>}
                  {p.main_kws.length === 0 && main && <span className="dim" style={{ display: 'block', fontSize: 11 }}>from the Page Map only</span>}
                </td>
                <td style={{ minWidth: 260 }}>
                  {p.secondary.length === 0 ? <span className="dim">—</span> : (
                    <div className="kp-subs">
                      {p.secondary.slice(0, SUB_SHOWN).map((k) => <span key={k.id} className="kp-sub">{k.keyword}</span>)}
                      {p.secondary.length > SUB_SHOWN && (
                        <details className="kp-more">
                          <summary>and {p.secondary.length - SUB_SHOWN} more</summary>
                          <div className="kp-subs">
                            {p.secondary.slice(SUB_SHOWN).map((k) => <span key={k.id} className="kp-sub">{k.keyword}</span>)}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                </td>
                <td className="tnum dim">{p.faq.length}</td>
                <td style={{ fontSize: 'var(--fs-xs)', minWidth: 240 }}>
                  {issues.length === 0
                    ? (p.kws.length === 0 ? <span className="dim">No keyword rows</span> : <Badge tone="pass">ok</Badge>)
                    : <ul style={{ margin: 0, paddingLeft: 16, display: 'grid', gap: 4 }}>{issues.map((t) => <li key={t}>{t}</li>)}</ul>}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table></div>
    </div>
  )
}

function Keywords({ model, onOpen }) {
  const [q, setQ] = useState('')
  const [type, setType] = useState('all')
  const [group, setGroup] = useState('all')
  const groups = useMemo(() => [...new Set(model.keywords.map((k) => k.group).filter(Boolean))].sort(), [model])
  const needle = q.trim().toLowerCase()
  const rows = model.keywords.filter((k) =>
    (type === 'all' || k.type === type)
    && (group === 'all' || k.group === group)
    && (!needle || (k.keyword || '').toLowerCase().includes(needle) || (k.url || '').toLowerCase().includes(needle)))

  return (
    <div className="stack stack-3">
      <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input id="kp-kw-search" type="search" className="input kp-search" placeholder="Search keyword or page URL"
               value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search keywords" />
        <select id="kp-kw-type" className="input kp-select" value={type} onChange={(e) => setType(e.target.value)} aria-label="Type">
          <option value="all">SEO and AEO</option>
          <option value="SEO">SEO</option>
          <option value="AEO">AEO</option>
        </select>
        <select id="kp-kw-group" className="input kp-select" value={group} onChange={(e) => setGroup(e.target.value)} aria-label="Keyword group">
          <option value="all">All groups</option>
          {groups.map((g) => <option key={g} value={g}>{g}</option>)}
        </select>
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          {rows.length > KEYWORD_LIMIT ? `Showing ${KEYWORD_LIMIT} of ${rows.length}` : `${rows.length} rows`}
        </span>
      </div>
      <div className="tablewrap"><table>
        <thead>
          <tr><th>Keyword / question</th><th>Type</th><th>Group</th><th>Intent</th><th>Role</th>
            <th>Page</th><th>Volume</th><th>KD</th><th>Status</th></tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={9} className="dim">No keywords match.</td></tr>}
          {rows.slice(0, KEYWORD_LIMIT).map((k) => (
            <tr key={k.id}>
              <td>{k.keyword}</td>
              <td><Badge tone={k.type === 'AEO' ? 'info' : 'mute'}>{v(k.type)}</Badge></td>
              <td className="dim">{v(k.group)}</td>
              <td className="dim">{v(k.intent)}</td>
              <td className="dim">{v(k.role)}</td>
              <td>{k.url
                ? <button type="button" className="mono kp-link" onClick={() => onOpen(k.url)}>{k.url}</button>
                : '—'}</td>
              <td className="tnum dim">{v(k.volume)}</td>
              <td className="tnum dim">{v(k.kd)}</td>
              <td className="dim">{v(k.status)}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  )
}

/* ------------------------------------------------------------ AEO */

function Aeo({ model }) {
  const tested = model.aeo.filter((a) => a.tested).length
  return (
    <div className="stack stack-3">
      <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
        Each month, ask these questions to each AI assistant and record whether it mentions Kite Pulse.
        {' '}{tested} of {model.aeo.length} questions have a test date in the sheet. An empty cell means not
        tested, not &quot;not mentioned&quot;.
      </p>
      <div className="tablewrap"><table>
        <thead>
          <tr><th>Question</th><th>Target page</th>{ASSISTANTS.map(([, l]) => <th key={l}>{l}</th>)}<th>Tested</th></tr>
        </thead>
        <tbody>
          {model.aeo.map((a) => (
            <tr key={a.question}>
              <td>{a.question}</td>
              <td className="mono dim">{v(a.page)}</td>
              {ASSISTANTS.map(([k]) => <td key={k} className="dim">{v(a[k])}</td>)}
              <td className="dim">{v(a.tested)}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  )
}

/* ------------------------------------------------------------ competitors */

function Competitors({ model }) {
  return (
    <div className="tablewrap"><table>
      <thead>
        <tr><th>Competitor</th><th>Ranks for</th><th>Does well</th><th>Misses</th><th>Our compare page</th></tr>
      </thead>
      <tbody>
        {model.competitors.map((c) => (
          <tr key={c.name}>
            <td><strong>{c.name}</strong><span className="mono dim" style={{ display: 'block', fontSize: 11 }}>{c.site}</span></td>
            <td className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{v(c.ranks_for)}</td>
            <td className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{v(c.strengths)}</td>
            <td className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{v(c.gaps)}</td>
            <td className="mono dim">{v(c.compare_page)}</td>
          </tr>
        ))}
      </tbody>
    </table></div>
  )
}

/* ------------------------------------------------------------ settings */

function Settings({ data }) {
  return (
    <div className="stack stack-4">
      <div className="stack stack-2">
        <span className="label">Keywords to avoid <span className="dim">{data.avoid.length}</span></span>
        <div className="tablewrap"><table>
          <thead><tr><th>Keyword</th><th>Why</th></tr></thead>
          <tbody>
            {data.avoid.map((a) => (
              <tr key={a.keyword}><td>{a.keyword}</td><td className="dim">{v(a.why)}</td></tr>
            ))}
          </tbody>
        </table></div>
      </div>

      <Notice icon={<IconAlert />}>
        Not built yet: the website domain, the fact source for page copy (the Product Guide), the writer
        model, and the sitemap and robots settings.
      </Notice>
    </div>
  )
}
