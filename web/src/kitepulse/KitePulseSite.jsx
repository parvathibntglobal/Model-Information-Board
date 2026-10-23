import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useParams } from 'react-router-dom'
import { useHead } from '../seo/head'
import { FOOTER, MENU, SECTIONS, isMissingMain, sitePath, useKitePulse, usePrototype } from './site'
import { KITE_PULSE_OPEN } from './status'
import './site.css'

/**
 * KITE PULSE, AS A WEBSITE, INSIDE THIS APP (2026-10-22).
 *
 * A second product's site, browsed the way a visitor would - home, menus,
 * pages - without a separate deployment. Every page has an address at
 * /kite-pulse + its own URL, so `/ai-cost-tracking` is
 * `/kite-pulse/ai-cost-tracking`.
 *
 * The structure (menus, footer, the home page's order) follows mentlio.com, a
 * direct competitor, reviewed 2026-10-22; the addresses are the keyword sheet's.
 *
 * ⚠ AN INTERNAL PREVIEW, NOT THE PUBLIC SITE. It is behind sign-in and asks for
 * `noindex`: these pages must rank on Kite Pulse's own domain, and the same
 * pages indexed here first would compete with them.
 *
 * ⚠ THE HOME PAGE'S WORDS ARE THE PRODUCT GUIDE'S, VERBATIM. The headline is
 * the one the keyword sheet plans (row 1, Content Gap / Angle). Nothing here
 * describes the product in words the guide does not use; what is not built yet
 * (the sample dashboard, demo booking) says so where it would be.
 *
 * What a page shows depends on how far it has got:
 *   prototype          the prototype itself, running, in a sandboxed frame
 *   section hub        (/integrations, /blog, /glossary) that section's pages
 *   anything else      its plan, marked "not written yet" or "proposed"
 */

const FONTS = 'https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap'

function useFonts() {
  useEffect(() => {
    if (document.querySelector('link[data-kp-fonts]')) return
    const link = Object.assign(document.createElement('link'), { rel: 'stylesheet', href: FONTS })
    link.dataset.kpFonts = ''
    document.head.appendChild(link)
  }, [])
}

/** `/kite-pulse#privacy` scrolls to the section, which the router does not do. */
function useHashScroll(ready) {
  const { hash, pathname } = useLocation()
  useEffect(() => {
    if (!ready || !hash) return
    document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView({ block: 'start' })
  }, [hash, pathname, ready])
}

// One line under each section heading. Says what the section is for; claims
// nothing about the product the Product Guide does not.
const SECTION_BLURBS = {
  Product: 'What Kite Pulse does, and what it costs.',
  Trust: 'Privacy, security, and running Kite Pulse on your own server.',
  Solutions: 'Problems Kite Pulse helps engineering teams with.',
  'Guides & tools': 'Interactive guides and tools to work through with your own numbers.',
  Glossary: 'Short definitions of the terms used in AI-assisted development.',
  Integrations: 'The AI coding tools Kite Pulse collects sessions from.',
  Blog: 'Articles on AI-assisted development.',
  Compare: 'How Kite Pulse compares with other tools.',
  Help: 'Documentation, changes and common questions.',
  Legal: 'Terms and policies.',
}

// SHORT NAMES FOR LINKS, from the address, because a main keyword is a search
// phrase ("privacy-first developer analytics") and reads badly in a menu.
const LABELS = {
  '/': 'Home', '/faq': 'FAQ', '/legal/privacy-policy': 'Privacy policy', '/legal/terms': 'Terms',
  '/integrations': 'All integrations',
  '/integrations/claude-code': 'Claude Code', '/integrations/codex': 'Codex', '/integrations/gemini-cli': 'Gemini CLI',
  '/integrations/cursor': 'Cursor', '/integrations/github-copilot': 'GitHub Copilot', '/integrations/cline': 'Cline',
  '/integrations/roo-code': 'Roo Code', '/integrations/kilo-code': 'Kilo Code', '/integrations/opencode': 'OpenCode',
  '/integrations/aider': 'Aider',
  '/compare/linearb': 'vs LinearB', '/compare/jellyfish': 'vs Jellyfish', '/compare/dx': 'vs DX',
  '/compare/swarmia': 'vs Swarmia', '/compare/github-copilot-metrics': 'vs GitHub Copilot metrics',
  '/compare/anthropic-console': 'vs Anthropic Console',
}
const WORDS = { ai: 'AI', roi: 'ROI', faq: 'FAQ', cli: 'CLI', mcp: 'MCP', vs: 'vs' }
function linkName(p) {
  if (LABELS[p.url]) return LABELS[p.url]
  const words = (p.url.split('/').filter(Boolean).pop() || 'home').split('-').map((w) => WORDS[w] || w)
  const s = words.join(' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}
/** The page's main keyword, as a heading. */
function headline(p) {
  if (isMissingMain(p)) return linkName(p)
  return p.main.charAt(0).toUpperCase() + p.main.slice(1)
}

const sectionHref = (s) => (s.hub ? sitePath(s.hub) : s.slug ? `/kite-pulse/${s.slug}` : '/kite-pulse')
const sectionByName = (name) => SECTIONS.find((s) => s.name === name)
const manageHref = (url) => `/admin?p=kite-pulse&s=kite-pulse&kp=pages&kpp=${encodeURIComponent(url)}`
const pagesOf = (model, names, except = []) =>
  model.site.filter((p) => names.includes(p.section) && !except.includes(p.url)
    && !SECTIONS.some((s) => s.hub === p.url))

/** Closed while its team works inside it (status.js): every page goes to the admin. */
export default function KitePulse() {
  return KITE_PULSE_OPEN ? <KitePulseSite /> : <Navigate to="/admin" replace />
}

function KitePulseSite() {
  useHead({ title: 'Kite Pulse — site preview', noindex: true })
  useFonts()
  const { model, err } = useKitePulse()
  useHashScroll(!!model)
  const path = `/${(useParams()['*'] || '').replace(/\/+$/, '')}`

  const page = model?.site.find((p) => p.url === path)
  const hubOf = page && SECTIONS.find((s) => s.hub === page.url)
  const section = !page && SECTIONS.find((s) => s.slug && !s.hub && `/${s.slug}` === path)

  return (
    <div className="kps">
      <div className="kps-preview">
        <div className="kps-wrap kps-preview-in">
          <span><b>Kite Pulse</b> · internal site preview, not public</span>
          <span className="kps-preview-links">
            {page && <Link to={manageHref(page.url)}>Page brief</Link>}
            <Link to="/admin?p=kite-pulse&s=kite-pulse">Manage pages &amp; keywords</Link>
            <Link to="/admin">← Admin</Link>
          </span>
        </div>
      </div>

      {model && <Announcement model={model} />}
      {model && <Header model={model} page={page} path={path} />}

      <main>
        {err && <div className="kps-wrap kps-note">The keyword sheet could not be loaded: {err}</div>}
        {!model && !err && <div className="kps-wrap"><div className="kps-skel" /></div>}
        {model && (
          path === '/' ? <Home model={model} />
            : page?.prototype ? <PrototypePage page={page} />
            : hubOf ? <SectionIndex section={hubOf} model={model} />
            : page ? <NotWritten page={page} />
            : section ? <SectionIndex section={section} model={model} />
            : <NoSuchPage path={path} />
        )}
      </main>

      {model && <SiteFooter model={model} />}
    </div>
  )
}

/* ------------------------------------------------------------ header */

/** One line above the header pointing at the newest guide, as Mentlio does with its research. */
function Announcement({ model }) {
  const guide = model.site.find((p) => p.url === '/ai-cost-tracking' && p.prototype)
  if (!guide) return null
  return (
    <div className="kps-announce">
      <div className="kps-wrap">
        <Link to={sitePath(guide.url)}>New guide: how to track AI coding costs across developers, teams and projects →</Link>
      </div>
    </div>
  )
}

function Header({ model, page, path }) {
  const [open, setOpen] = useState(null)
  const ref = useRef(null)

  // Close on navigation, on Escape, and on a click anywhere outside the bar.
  useEffect(() => { setOpen(null) }, [path])
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => { if (e.key === 'Escape') setOpen(null) }
    const onDown = (e) => { if (!ref.current?.contains(e.target)) setOpen(null) }
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onDown)
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('mousedown', onDown) }
  }, [open])

  // A dropdown claims a page by its section; a single link only by URL prefix.
  // A page a dropdown claims is that dropdown's alone: /blog/ai-coding-roi is a
  // guide, so it lights "Guides", not "Blog".
  const inDropdown = (m) => page && m.sections.includes(page.section) && !(m.except || []).includes(page.url)
  const claimed = MENU.some((m) => m.sections && inDropdown(m))
  const isOn = (m) => (m.to ? page?.url === m.to || (!claimed && page?.url?.startsWith(`${m.to}/`))
    : inDropdown(m))

  return (
    <header className="kps-top" ref={ref}>
      <div className="kps-wrap kps-top-in">
        <Link to="/kite-pulse" className="kps-brand">Kite <span>Pulse</span></Link>
        <nav className="kps-nav" aria-label="Kite Pulse">
          {MENU.map((m) => (m.to ? (
            <Link key={m.label} to={sitePath(m.to)} className={isOn(m) ? 'on' : undefined}>{m.label}</Link>
          ) : (
            <div key={m.label} className="kps-dd">
              <button type="button" aria-expanded={open === m.label} className={isOn(m) ? 'on' : undefined}
                      onClick={() => setOpen(open === m.label ? null : m.label)}>
                {m.label} <span aria-hidden="true" className="kps-caret">▾</span>
              </button>
              {open === m.label && (
                <div className="kps-dd-panel">
                  {m.sections.map((name) => {
                    const list = pagesOf(model, [name], m.except)
                    const s = sectionByName(name)
                    return (
                      <div key={name} className="kps-dd-col">
                        <Link to={sectionHref(s)} className="kps-dd-h">{name}</Link>
                        {list.map((p) => (
                          <Link key={p.url} to={sitePath(p.url)} className="kps-dd-a">
                            {linkName(p)}
                            {p.proposed && <i className="kps-chip kps-chip-new">Proposed</i>}
                          </Link>
                        ))}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )))}
        </nav>
        <Link to="/kite-pulse#book-a-demo" className="kps-btn">Book a demo</Link>
      </div>
    </header>
  )
}

/* ------------------------------------------------------------ home */

// From the Product Guide, "Problems it solves": the problem, what it looks
// like today, and how Kite Pulse helps - verbatim.
const PROBLEMS = [
  ['Output counts no longer tell the story',
    'More commits and pull requests, yet delivery feels no faster. Nobody can say where the time went.',
    'Measures active time, sessions, retries and abandoned approaches from the sessions themselves.'],
  ['AI spend is a black box',
    'Several tools, several subscriptions, one monthly bill. No view per person or per project.',
    'Shows AI cost by person, project, tool and period, plus a billable view with a markup.'],
  ['Plan limits arrive as a surprise',
    'A developer hits their AI plan\'s usage limit mid-task and loses half a day.',
    'Shows how much of each plan\'s limit is used, for each person and across the team.'],
  ['History is scattered across tools',
    'Claude Code, Codex, Gemini, Cursor and Copilot each keep their own records, in their own format.',
    'Brings every supported tool into one consistent view.'],
]

// From the Product Guide, "Key features": one tab per group, its own words.
const FEATURE_TABS = [
  { id: 'usage', label: 'Usage & cost', links: ['/ai-cost-tracking', '/plan-headroom', '/shadow-ai'], points: [
    'Team AI Usage: tokens used per developer, per tool and per period, with an estimated cost per tool where it can be worked out.',
    'Plan headroom (a tab on Team AI Usage): who is close to a Claude plan limit (the 5-hour window, the weekly window, or a model\'s weekly window), worst first.',
    'Tool Accounts: how many separate accounts each AI tool is used under. It reveals shared logins, or one person holding two accounts.',
  ] },
  { id: 'team', label: 'Team', links: ['/features', '/engineering-intelligence'], points: [
    'Org Overview is a live control room: who is online, coding, idle or offline, sessions today, active time, a timeline of each person\'s day, and their current project.',
    'Collaboration shows who works on what together: each shared project, the people contributing, and how many sessions each spent there.',
  ] },
  { id: 'projects', label: 'Projects', links: ['/features'], points: [
    'Organization Projects lists every project with its health (active, stable or dormant), sessions, contributors and last activity.',
    'Duplicate Detection groups folders that look like the same repository on different machines, and offers to merge them.',
  ] },
  { id: 'personal', label: 'Personal', links: ['/features'], points: [
    'My Scorecard & Insights shows active hours, sessions, messages, lines changed, commits and projects, led by a "Top 3 to act on" list.',
    'Working style: a label such as builder, explorer, debugger or communicator, worked out from the person\'s own tool mix.',
  ] },
]

// From the Product Guide, "What the desktop program reads, and why".
const READS = [
  ['Session history of the AI tools an admin has switched on', 'That is where those tools keep their conversations',
    'The conversation record, with secrets removed and encrypted'],
  ['Folder names inside project folders, and each project\'s git settings', 'To tell projects apart',
    'Folder paths and the repository address (host, organisation, repository) only'],
  ['The account each AI tool is signed in with', 'To link a tool account to the right person',
    'The account email and plan details only'],
]

// From the Product Guide, "Frequently asked questions".
const FAQ = [
  ['Does Kite Pulse read my source code?',
    'No. It reads the session records your AI tools already keep, plus folder names and repository addresses to tell projects apart. Secrets in those records are removed on your computer before upload.'],
  ['Which AI tools does it support?',
    'Ten today: Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, Cline, Roo Code, Kilo Code, OpenCode and Aider. An admin picks which ones are collected.'],
  ['Does our data go to a vendor\'s cloud?',
    'No. Data goes only to the Kite Pulse server your team runs, on your own network or your own cloud account.'],
  ['Do we need an AI service or API key to use it?',
    'No. All the activity, usage, project and admin features work without one. Only the optional AI-assisted features need a key, and an admin turns them on.'],
  ['Are the cost figures exact?',
    'Kite Pulse shows exact token counts. Where it can be worked out, it adds an estimated cost per tool. It is a guide for decisions, not a replacement for the AI vendor\'s invoice.'],
]

function Home({ model }) {
  const [tab, setTab] = useState(FEATURE_TABS[0].id)
  const feature = FEATURE_TABS.find((t) => t.id === tab)
  const byUrl = (u) => model.site.find((p) => p.url === u)
  const tools = pagesOf(model, ['Integrations'])
  const guides = pagesOf(model, ['Guides & tools'])
  const home = byUrl('/')

  return (
    <>
      <section className="kps-hero">
        <div className="kps-wrap kps-hero-in">
          {home?.main && <span className="kps-eyebrow">{home.main}</span>}
          <h1>AI coding analytics: see how your team really uses AI coding assistants</h1>
          <p className="kps-lede">
            Kite Pulse shows a team how its software is really being built, now that much of that work
            happens in conversation with AI coding assistants.
          </p>
          <div className="kps-row">
            <Link to="#book-a-demo" className="kps-btn">Book a demo</Link>
            <Link to="#platform" className="kps-btn kps-btn-ghost">See the platform</Link>
          </div>
        </div>
      </section>

      <section className="kps-band" id="problem">
        <div className="kps-wrap kps-stack">
          <div className="kps-stack-s">
            <span className="kps-eyebrow">The problem</span>
            <h2>AI coding assistants changed the unit of work: developers now direct an AI that writes much of the code.</h2>
            <p className="kps-lede">
              Organisations are spending heavily on these tools but have no truthful way to see what they get back.
            </p>
          </div>
          <div className="kps-grid kps-grid-2">
            {PROBLEMS.map(([title, today, helps]) => (
              <div key={title} className="kps-panel">
                <h3>{title}</h3>
                <p className="kps-muted">{today}</p>
                <p><b>Kite Pulse:</b> {helps}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="kps-band" id="platform">
        <div className="kps-wrap kps-stack">
          <div className="kps-stack-s">
            <span className="kps-eyebrow">The platform</span>
            <h2>A single place to see AI-assisted development across people, projects and tools.</h2>
          </div>
          <div className="kps-tabs" role="tablist" aria-label="Platform">
            {FEATURE_TABS.map((t) => (
              <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
          <div className="kps-feature" role="tabpanel">
            <div className="kps-stack-s">
              <ul className="kps-points">{feature.points.map((pt) => <li key={pt}>{pt}</li>)}</ul>
              <div className="kps-row">
                {feature.links.map((u) => byUrl(u)).filter(Boolean).map((p) => (
                  <Link key={p.url} to={sitePath(p.url)}>{linkName(p)} →</Link>
                ))}
              </div>
            </div>
            <div className="kps-placeholder" role="img" aria-label="Sample dashboard, not built yet">
              <span>Sample dashboard</span>
              <small>Placeholder. The clickable sample dashboard the keyword sheet plans for the home page is not built yet.</small>
            </div>
          </div>
        </div>
      </section>

      <section className="kps-band" id="privacy">
        <div className="kps-wrap kps-stack">
          <div className="kps-stack-s">
            <span className="kps-eyebrow">Privacy</span>
            <h2>Historian, not critic</h2>
            <p className="kps-lede">
              Kite Pulse only works if developers trust it, so privacy is built into what it collects and who can see it.
            </p>
          </div>
          <div className="kps-scroll"><table className="kps-table">
            <thead><tr><th>What it reads</th><th>Why</th><th>What is sent to the server</th></tr></thead>
            <tbody>{READS.map((r) => <tr key={r[0]}>{r.map((c) => <td key={c}>{c}</td>)}</tr>)}</tbody>
          </table></div>
          <p>
            The program does not open or upload a project&apos;s source files. Data goes only to the server the team
            configured; there is no vendor cloud in between.
          </p>
          <div className="kps-row">
            {['/privacy', '/self-hosted', '/security'].map((u) => byUrl(u)).filter(Boolean).map((p) => (
              <Link key={p.url} to={sitePath(p.url)}>{linkName(p)} →</Link>
            ))}
          </div>
        </div>
      </section>

      <section className="kps-band" id="integrations">
        <div className="kps-wrap kps-stack">
          <div className="kps-stack-s">
            <span className="kps-eyebrow">Integrations</span>
            <h2>One view across many tools</h2>
            <p className="kps-lede">
              Ten AI coding tools in one consistent picture, instead of ten separate dashboards or none.
            </p>
          </div>
          <div className="kps-tools">
            {tools.map((p) => <Link key={p.url} to={sitePath(p.url)} className="kps-tool">{linkName(p)}</Link>)}
          </div>
        </div>
      </section>

      {guides.length > 0 && (
        <section className="kps-band" id="guides">
          <div className="kps-wrap kps-stack">
            <div className="kps-stack-s">
              <span className="kps-eyebrow">Guides &amp; tools</span>
              <h2>Guides and tools</h2>
            </div>
            <div className="kps-grid">
              {[...guides].sort((a, b) => Number(!!b.prototype) - Number(!!a.prototype))
                .map((p) => <PageCard key={p.url} page={p} big={!!p.prototype} />)}
            </div>
          </div>
        </section>
      )}

      <section className="kps-band" id="faq">
        <div className="kps-wrap kps-stack">
          <h2>Frequently asked questions</h2>
          <div className="kps-faq">
            {FAQ.map(([q, a], i) => (
              <details key={q} open={i === 0}><summary>{q}</summary><p>{a}</p></details>
            ))}
          </div>
        </div>
      </section>

      <section className="kps-band" id="book-a-demo">
        <div className="kps-wrap">
          <div className="kps-cta">
            <h2>A single place to see AI-assisted development across people, projects and tools, running on a server the team controls.</h2>
            <div className="kps-row">
              <button type="button" className="kps-btn kps-btn-inv" disabled aria-describedby="demo-note">Book a demo</button>
            </div>
            <small id="demo-note">Placeholder. There is no booking link yet.</small>
          </div>
        </div>
      </section>
    </>
  )
}

/* ------------------------------------------------------------ sections */

function SectionIndex({ section, model }) {
  const pages = pagesOf(model, [section.name])
  return (
    <section className="kps-band kps-band-first">
      <div className="kps-wrap kps-stack">
        <div className="kps-stack-s">
          <span className="kps-eyebrow">{section.name}</span>
          <h1 className="kps-h1">{section.name}</h1>
          <p className="kps-lede">{SECTION_BLURBS[section.name]}</p>
        </div>
        {pages.length === 0
          ? <p className="kps-note">No pages planned in this section yet.</p>
          : <div className="kps-grid">{pages.map((p) => <PageCard key={p.url} page={p} />)}</div>}
      </div>
    </section>
  )
}

function PageCard({ page, big }) {
  return (
    <Link to={sitePath(page.url)} className={`kps-card${big ? ' kps-card-big' : ''}`}>
      <span className="kps-card-k">
        {page.type || page.section}
        {page.proposed ? <i className="kps-chip kps-chip-new">Proposed</i>
          : !page.prototype && <i className="kps-chip">Not written yet</i>}
      </span>
      <span className="kps-card-t">{linkName(page)}</span>
      {!isMissingMain(page) && <span className="kps-card-p">{headline(page)}</span>}
      <span className="kps-card-u">{page.url}</span>
    </Link>
  )
}

/* ------------------------------------------------------------ pages */

// WHAT TURNS A PROTOTYPE INTO A PAGE OF THIS SITE (2026-10-22). Added to the
// prototype's HTML before it is shown, never saved into the file - the admin's
// Preview tab still shows the prototype as made, SEO notes and all.
//   hidden   its own logo (the site header has one), the "Show SEO notes"
//            switch, the SEO notes, and its "Prototype of ..." footer
//   kept     its sticky bars' controls (the running estimate, plan switches)
//            and the pricing page's "prices are placeholders" warning - that
//            one is true of the page, not of the prototype
//   posted   its height, so the frame grows to fit and the page scrolls with
//            the site; and in-page links (#setup), which the frame cannot
//            scroll the site for, so the site does it
const EMBED = `<style>
.ledger .brand,.topbar .brand,.toggle,.seo,body>footer{display:none!important}
</style>
<script>
(function(){
  function post(){ parent.postMessage({ kp: 'height', h: document.documentElement.scrollHeight }, '*') }
  if (window.ResizeObserver) new ResizeObserver(post).observe(document.body)
  window.addEventListener('load', post); post()
  document.addEventListener('click', function(e){
    var a = e.target.closest && e.target.closest('a[href^="#"]'); if (!a) return
    var el = document.getElementById(a.getAttribute('href').slice(1)); if (!el) return
    e.preventDefault()
    parent.postMessage({ kp: 'scroll', top: el.getBoundingClientRect().top + window.scrollY }, '*')
  })
})()
</script>`
const embed = (html) => (html.includes('</body>') ? html.replace('</body>', `${EMBED}</body>`) : html + EMBED)

// Room for the site's sticky header when scrolling to a section of the page.
const HEADER_ROOM = 72

/**
 * A BUILT PAGE, shown as part of the site: the site's header above it, the
 * site's footer below it, and the page itself at its full height in between.
 * `allow-scripts` without `allow-same-origin` gives it a unique origin: its
 * calculators run, but it cannot read this app's storage or session token.
 * `allow-popups` lets its vendor links open in a new tab.
 */
function PrototypePage({ page }) {
  const { html, err } = usePrototype(page.prototype.file)
  const frame = useRef(null)
  const [height, setHeight] = useState(null)

  useEffect(() => {
    const onMessage = (e) => {
      // Only this page's own frame; any other window's message is ignored.
      if (!frame.current || e.source !== frame.current.contentWindow || !e.data || typeof e.data !== 'object') return
      if (e.data.kp === 'height' && Number.isFinite(e.data.h)) setHeight(Math.ceil(e.data.h))
      if (e.data.kp === 'scroll' && Number.isFinite(e.data.top)) {
        const top = frame.current.getBoundingClientRect().top + window.scrollY + e.data.top - HEADER_ROOM
        window.scrollTo({ top, behavior: 'smooth' })
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  if (err) return <div className="kps-wrap kps-note">This page could not be loaded: {err}</div>
  if (!html) return <div className="kps-wrap"><div className="kps-skel" /></div>
  return (
    <iframe ref={frame} className="kps-frame" title={headline(page)} srcDoc={embed(html)}
            sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
            style={height ? { height } : undefined} />
  )
}

/** A page with no content yet: its plan, said as a plan. */
function NotWritten({ page }) {
  return (
    <section className="kps-band kps-band-first">
      <div className="kps-wrap kps-stack">
        <div className="kps-stack-s">
          <span className="kps-eyebrow">{page.section} · {page.url}</span>
          <h1 className="kps-h1">{headline(page)}</h1>
          {page.proposed ? (
            <p className="kps-note">
              Proposed page. The site structure needs it, but the keyword sheet&apos;s Page Map does not list it yet.
            </p>
          ) : (
            <p className="kps-note">
              This page is planned but not written yet. <Link to={manageHref(page.url)}>Open its brief</Link>
            </p>
          )}
        </div>

        {page.notes && (
          <div className="kps-panel">
            <h2>{page.proposed ? 'Why it is proposed' : 'What this page will cover'}</h2>
            <p className="kps-pre">{page.notes}</p>
          </div>
        )}

        {page.faq.length > 0 && (
          <div className="kps-panel">
            <h2>Questions it will answer</h2>
            <ul>{page.faq.map((k) => <li key={k.id}>{k.keyword}</li>)}</ul>
          </div>
        )}
      </div>
    </section>
  )
}

function NoSuchPage({ path }) {
  return (
    <section className="kps-band kps-band-first">
      <div className="kps-wrap kps-stack-s">
        <h1 className="kps-h1">No page here</h1>
        <p className="kps-lede">There is no Kite Pulse page at <code>{path}</code>.</p>
        <p><Link to="/kite-pulse">Go to the Kite Pulse home page</Link></p>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------ footer */

function SiteFooter({ model }) {
  const byUrl = (u) => model.site.find((p) => p.url === u)
  return (
    <footer className="kps-foot">
      <div className="kps-wrap kps-foot-in">
        <div className="kps-foot-brand">
          <div className="kps-brand">Kite <span>Pulse</span></div>
          <p>A single place to see AI-assisted development across people, projects and tools.</p>
        </div>
        {FOOTER.map((col) => {
          const links = col.sections ? pagesOf(model, col.sections, col.except).map((p) => [sitePath(p.url), linkName(p)])
            : col.hubs ? col.hubs.map((n) => [sectionHref(sectionByName(n)), n])
            : col.urls.map(byUrl).filter(Boolean).map((p) => [sitePath(p.url), linkName(p)])
          return (
            <div key={col.title} className="kps-foot-col">
              <span className="kps-foot-h">{col.title}</span>
              {links.map(([to, label]) => <Link key={to} to={to}>{label}</Link>)}
            </div>
          )
        })}
      </div>
    </footer>
  )
}
