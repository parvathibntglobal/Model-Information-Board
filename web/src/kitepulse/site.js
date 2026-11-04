import { useEffect, useMemo, useState } from 'react'

/**
 * KITE PULSE - shared by the admin panel (KitePulsePanel.jsx) and the site
 * preview (KitePulseSite.jsx), so the two cannot disagree about which section
 * a page is in or which pages have a prototype. See README.md in this folder.
 *
 * Everything comes from the keyword research sheet, converted to
 * `data/sheet.json` by `import_sheet.py`. The JSON is a dynamic import, so its
 * ~330 KB is a separate chunk only these two screens download.
 */

// THE WEBSITE'S SECTIONS, in display order. `slug` is the section's address
// under /kite-pulse, where its pages are listed.
//
// ⚠ A section with a `hub` has NO list address of its own: the Page Map
// already has that page (`/integrations`, `/blog`, `/glossary`), and it IS the
// section index. A second address for the same list would be two pages saying
// one thing.
export const SECTIONS = [
  { name: 'Home', slug: null },
  { name: 'Product', slug: 'product' },
  { name: 'Trust', slug: 'trust' },
  { name: 'Solutions', slug: 'solutions' },
  { name: 'Guides & tools', slug: 'guides' },
  { name: 'Glossary', slug: 'glossary', hub: '/glossary' },
  { name: 'Integrations', slug: 'integrations', hub: '/integrations' },
  { name: 'Blog', slug: 'blog', hub: '/blog' },
  { name: 'Compare', slug: 'compare' },
  { name: 'Help', slug: 'help' },
  { name: 'Legal', slug: 'legal' },
]

// THE SITE'S STRUCTURE (2026-10-22), after reviewing mentlio.com, a direct
// competitor: a short top bar with a few dropdowns, a demo button, and a
// four-column footer. The page addresses stay the keyword sheet's.
//
// A menu entry is either a dropdown of pages (`sections`, minus `except`) or
// one page (`to`). Footer columns work the same way, plus `hubs`: links to
// section lists rather than to pages.
export const MENU = [
  { label: 'Product', sections: ['Product', 'Trust'], except: ['/pricing', '/about'] },
  { label: 'Solutions', sections: ['Solutions'] },
  { label: 'Guides', sections: ['Guides & tools', 'Glossary'] },
  { label: 'Integrations', to: '/integrations' },
  { label: 'Blog', to: '/blog' },
  { label: 'Pricing', to: '/pricing' },
  { label: 'Docs', to: '/docs' },
]
export const FOOTER = [
  { title: 'Product', sections: ['Product', 'Trust'], except: ['/pricing', '/about'] },
  { title: 'Solutions', sections: ['Solutions'] },
  { title: 'Resources', hubs: ['Guides & tools', 'Glossary', 'Blog', 'Compare'] },
  { title: 'Company', urls: ['/about', '/pricing', '/docs', '/changelog', '/faq', '/legal/privacy-policy', '/legal/terms'] },
]

// PAGES THE SITE STRUCTURE NEEDS THAT THE KEYWORD SHEET DOES NOT LIST YET
// (2026-10-22). Kept apart from the sheet's pages, so no count of the sheet's
// Page Map changes, and marked "proposed" wherever they show. Add them to the
// sheet's Page Map to make them real; then delete them here.
export const PROPOSED = [
  { url: '/glossary', type: 'Glossary',
    notes: 'An index of short definitions, one page per term. Mentlio ranks with /glossary/tokenmaxxing.' },
  { url: '/glossary/tokenmaxxing', type: 'Glossary', main: 'tokenmaxxing',
    notes: 'Keyword rows 581 (Main) and 582 (FAQ, "what is tokenmaxxing") target /blog/measure-developer-productivity-ai today, and the Page Map notes ask whether tokenmaxxing needs its own page. Mentlio answered that with /glossary/tokenmaxxing. Moving the two rows here would answer it for us.' },
  { url: '/changelog', type: 'Docs',
    notes: 'What changed in each Kite Pulse release. Mentlio has one; it shows a product that is maintained.' },
  // Article Plan categories 1-2 (2026-11-03): the 30 articles in
  // docs/Kite Pulse - Article Production Plan (Categories 1-2).md, built as
  // interactive blog posts. Their keyword rows still target other URLs in the
  // sheet; move them to these URLs in the Page Map to make the pages real.
  { url: '/blog/self-hosted-ai-usage-tracking', type: 'Blog', main: 'self-hosted ai usage tracking',
    notes: 'Article Plan 1.2: The Three Parts of Kite Pulse: Desktop Program, Your Server, Web Console' },
  { url: '/blog/secret-masking', type: 'Blog', main: 'secret masking',
    notes: 'Article Plan 1.3: From a Developer\'s Laptop to the Console: a Session\'s Journey in Six Steps' },
  { url: '/blog/software-engineering-intelligence', type: 'Blog', main: 'software engineering intelligence',
    notes: 'Article Plan 1.6: How Kite Pulse Is Different from Other Engineering Tools' },
  { url: '/blog/employer-see-claude-code-prompts', type: 'Blog', main: 'can my employer see my claude code prompts',
    notes: 'Article Plan 1.7: What Kite Pulse Is Not' },
  { url: '/blog/glossary-of-common-ai-terms', type: 'Blog', main: 'glossary of common ai terms',
    notes: 'Article Plan 1.8: Kite Pulse Terms in Plain Words' },
  { url: '/blog/claude-code-estimated-cost', type: 'Blog', main: 'claude code estimated cost',
    notes: 'Article Plan 1.9: Where the Numbers Come From' },
  { url: '/blog/ai-assisted-development-analytics', type: 'Blog', main: 'ai assisted development analytics',
    notes: 'Article Plan 1.11: One Loop: Capture, Understand, Act, Learn' },
  { url: '/blog/ai-usage-dashboard-for-developers', type: 'Blog', main: 'ai usage dashboard for developers',
    notes: 'Article Plan 1.12: A Map of the Console' },
  { url: '/blog/duplicate-repository-detection', type: 'Blog', main: 'duplicate repository detection',
    notes: 'Article Plan 2.2: Automatic Project Detection' },
  { url: '/blog/personal-claude-code-usage-stats', type: 'Blog', main: 'personal claude code usage stats',
    notes: 'Article Plan 2.4: Workspace: Is My Work Being Captured?' },
  { url: '/blog/developer-scorecard', type: 'Blog', main: 'developer scorecard',
    notes: 'Article Plan 2.5: My Scorecard & Insights: a Top 3 to Act On' },
  { url: '/blog/developer-working-style', type: 'Blog', main: 'developer working style',
    notes: 'Article Plan 2.6: How You Work: My Activity, Work Patterns, Working Style and Private Prompt Statistics' },
  { url: '/blog/search-past-ai-coding-sessions', type: 'Blog', main: 'search past ai coding sessions',
    notes: 'Article Plan 2.7: My Sessions: Finding the Session You Need' },
  { url: '/blog/claude-code-session-replay', type: 'Blog', main: 'claude code session replay',
    notes: 'Article Plan 2.8: Inside One Session: Playback, Summary and Segments' },
  { url: '/blog/claude-code-activity-log', type: 'Blog', main: 'claude code activity log',
    notes: 'Article Plan 2.9: What the Agent Did: a Step-by-Step Record Without Message Text' },
  { url: '/blog/ai-agent-stuck-notification', type: 'Blog', main: 'ai agent stuck notification',
    notes: 'Article Plan 2.10: Notices in the Bell: Plan Limit Reached, AI Agent Stuck and Claude Code Out of Date' },
  { url: '/blog/what-is-my-team-working-on', type: 'Blog', main: 'what is my team working on dashboard',
    notes: 'Article Plan 2.11: Team Overview, All Developers and Organisation Overview' },
  { url: '/blog/claude-code-multi-agent-dashboard', type: 'Blog', main: 'claude code multi agent dashboard',
    notes: 'Article Plan 2.12: The Developer Page: One Person in Full' },
  { url: '/blog/team-collaboration-insights', type: 'Blog', main: 'team collaboration insights',
    notes: 'Article Plan 2.13: Collaboration, Teams, and Leave & On-Call' },
  { url: '/blog/failing-commands-analytics', type: 'Blog', main: 'failing commands analytics',
    notes: 'Article Plan 2.14: Work Problems, Insight Rules and the Insights Catalog' },
  { url: '/blog/developer-pain-points', type: 'Blog', main: 'developer pain points',
    notes: 'Article Plan 2.15: Workflows & Pain Points: Where Work Repeats and Where It Slows Down' },
  { url: '/blog/project-health-dashboard', type: 'Blog', main: 'project health dashboard',
    notes: 'Article Plan 2.16: All Projects and the Project Page' },
  { url: '/blog/shared-ai-tool-accounts', type: 'Blog', main: 'shared ai tool accounts',
    notes: 'Article Plan 2.22: Tool Accounts: Shared, Separate and Personal Accounts' },
  { url: '/blog/ai-coding-seat-cost-tracking', type: 'Blog', main: 'ai coding seat cost tracking',
    notes: 'Article Plan 2.23: Hourly Rates & Seat Prices' },
  { url: '/blog/claude-code-tokens-per-second', type: 'Blog', main: 'claude code tokens per second',
    notes: 'Article Plan 2.24: Generation Rate: How Fast AI Replies Arrive' },
  { url: '/blog/claude-code-skills-used-across-team', type: 'Blog', main: 'claude code skills used across team',
    notes: 'Article Plan 2.25: Agent Setup: Claude Code Skills, Commands, Agents and MCP Servers Across the Team' },
  { url: '/blog/scheduled-engineering-reports', type: 'Blog', main: 'scheduled engineering reports email',
    notes: 'Article Plan 2.28: Company Reports and Scheduled Reports' },
  { url: '/blog/role-based-access-control-dashboard', type: 'Blog', main: 'role based access control dashboard',
    notes: 'Article Plan 2.29: Who Sees What: Roles & Permissions, Accounts and Sign-in' },
  { url: '/blog/audit-log-for-admin-actions', type: 'Blog', main: 'audit log for admin actions',
    notes: 'Article Plan 2.31: Data Rights: Export, Erase, Audit Log and Retention' },
  { url: '/blog/credential-leak-detection', type: 'Blog', main: 'credential leak detection',
    notes: 'Article Plan 2.32: Leaked Credentials and Security Watch' },
]

// PAGES THE SHEET LISTS THAT THIS PHASE OF THE SITE LEAVES OUT (2026-11-02).
// The Product menu is eight pages. /reports is folded into /features and
// /plan-headroom, /parallel-ai-agents into /ai-agent-office, and
// /enterprise-brain is The Brain, a hidden feature (master prompt R3) that is
// not part of this phase. Left out of the site only: the admin's view of the
// sheet still lists them.
export const HIDDEN = new Set(['/reports', '/parallel-ai-agents', '/enterprise-brain'])

// A page goes in the FIRST section whose test it passes, so the order of
// matching is separate from the order of display: `/blog/ai-coding-roi` is an
// interactive guide and must be caught before the `/blog` prefix claims it.
const MATCH = [
  ['Home', (p) => p.url === '/'],
  ['Glossary', (p) => p.url.startsWith('/glossary')],
  ['Integrations', (p) => p.url.startsWith('/integrations')],
  ['Compare', (p) => p.url.startsWith('/compare')],
  ['Legal', (p) => p.url.startsWith('/legal')],
  ['Guides & tools', (p) => p.type === 'Interactive guide' || p.type === 'Interactive tool'],
  ['Blog', (p) => p.url.startsWith('/blog')],
  ['Trust', (p) => p.type === 'Trust'],
  // The sheet types /pricing and /about as "Solution"; they are product pages.
  ['Product', (p) => p.type === 'Feature' || p.url === '/pricing' || p.url === '/about'],
  ['Solutions', (p) => p.type === 'Solution'],
  ['Help', (p) => p.type === 'Docs' || p.type === 'FAQ'],
]
// A page no test claims is listed under "Other", never dropped.
export const sectionOf = (p) => (MATCH.find(([, test]) => test(p)) || ['Other'])[0]

// PROTOTYPE PAGES, keyed by the Page Map URL. Each is a whole HTML document
// made as a Claude artifact and copied into `prototypes/`. They live under
// src/ and load as raw text, NOT in public/, so they get no address of their
// own on this site: the same page served from the Model Information Board's
// domain would compete with the real Kite Pulse page in search. `artifact` is
// where the prototype is edited; re-copy the file after changing it there.
export const PROTOTYPES = {
  '/ai-cost-tracking': { file: 'ai-cost-tracking', artifact: 'https://claude.ai/artifact/MW9gPq11m5pA4ULoAoiBec' },
  '/shadow-ai': { file: 'shadow-ai', artifact: 'https://claude.ai/artifact/M7e53egfYeGfSRC38aa3vN' },
  '/ai-coding-assistant-pricing': { file: 'ai-coding-assistant-pricing', artifact: 'https://claude.ai/artifact/C3rD3Ub6uJm2y5noHeJ3PN' },
  '/claude-code-usage-limits': { file: 'claude-code-usage-limits', artifact: 'https://claude.ai/artifact/WMFgbp6JCZxZoitFnENhZu' },
  '/blog/measure-developer-productivity-ai': { file: 'measure-developer-productivity-ai', artifact: 'https://claude.ai/artifact/Vgu3LkaSxjcPmEESmxzfBk' },
  '/blog/developer-experience-metrics': { file: 'developer-experience-metrics', artifact: 'https://claude.ai/artifact/Ung7TRao4PaUmSpoLDbMZJ' },
  '/ai-coding-analytics': { file: 'ai-coding-analytics', artifact: 'https://claude.ai/artifact/BgJQA795gFVyAQLTpazzLK' },
  '/engineering-intelligence': { file: 'engineering-intelligence', artifact: 'https://claude.ai/artifact/TmPhBF3zMcrMyQhtKS2WJQ' },
  // Written in Claude Code, not as artifacts: no `artifact` to edit them in.
  ...Object.fromEntries([
    'ai-coding-analytics-platform', 'engineering-ai-spend-report', 'ai-adoption-tracking',
    'token-usage-per-developer', 'token-usage-forecast', 'sprint-planning-claude-plan-limits',
    'control-claude-code-spend-small-team', 'developer-analytics-without-source-code',
    'developer-analytics-without-keystroke-tracking', 'ai-secret-scanning', 'stuck-ai-agent',
    'visualize-ai-agents-working', 'codex-gemini-cli-team-usage', 'cline-aider-roo-code-analytics',
    'ai-cost-per-project-agencies',
    // Second batch (2026-11-02): 8 Commercial, 7 Informational.
    'track-token-usage-without-prompts', 'cursor-shared-account', 'claude-code-session-analysis',
    'local-ai-coding-analytics', 'company-ai-usage-report', 'claude-code-agent-features-usage',
    'claude-md-version-control', 'ai-coding-tracker-freelancers', 'what-are-tokens-in-ai',
    'ai-coding-cost-per-developer', 'avoid-hitting-claude-limit', 'developer-experience-without-surveys',
    'is-claude-code-stuck', 'can-my-employer-see-my-claude-code-chats', 'engineering-team-health-metrics',
  ].map((file) => [`/blog/${file}`, { file, artifact: null }])),
  // The Product menu's pages (2026-11-02), also written in Claude Code.
  ...Object.fromEntries([
    'features', 'privacy', 'self-hosted', 'plan-headroom', 'skill-candidates',
    'ai-budgets', 'ai-agent-office', 'security',
  ].map((file) => [`/${file}`, { file, artifact: null }])),
  // The Solutions menu's role pages (2026-11-02).
  ...Object.fromEntries([
    'engineering-managers', 'finance', 'developers',
  ].map((file) => [`/solutions/${file}`, { file, artifact: null }])),
}
// One lazy chunk per prototype, downloaded only when it is shown.
const PROTOTYPE_FILES = import.meta.glob('./prototypes/*.html', { query: '?raw', import: 'default' })
export const loadPrototype = (file) => PROTOTYPE_FILES[`./prototypes/${file}.html`]

/** An empty sheet cell. Shown as a dash, never as 0 (rule 6). */
export const v = (x) => (x == null || x === '' ? '—' : x)
export const isMissingMain = (p) => !p.main || /^tbd\b/i.test(p.main)

/** Every page with its keywords, section and prototype, computed once from the sheet. */
export function buildModel(data) {
  const byUrl = new Map()
  for (const k of data.keywords) {
    if (!k.url) continue
    if (!byUrl.has(k.url)) byUrl.set(k.url, [])
    byUrl.get(k.url).push(k)
  }
  const enrich = (p) => {
    const kws = byUrl.get(p.url) || []
    const role = (r) => kws.filter((k) => (k.role || '').toLowerCase() === r)
    return { ...p, section: sectionOf(p), kws, main_kws: role('main'), secondary: role('secondary'), faq: role('faq'),
      prototype: PROTOTYPES[p.url] || null }
  }
  const pages = data.pages.map(enrich)
  // A proposed page the sheet has since added is the sheet's, not proposed.
  const inSheet = new Set(pages.map((p) => p.url))
  const proposed = PROPOSED.filter((p) => !inSheet.has(p.url))
    .map((p) => enrich({ main: null, priority: null, status: null, ...p, proposed: true }))
  return {
    pages,
    proposed,
    // The whole site: what the preview renders and links. Every count of the
    // keyword sheet reads `pages`, never this.
    site: [...pages, ...proposed].filter((p) => !HIDDEN.has(p.url)),
    keywords: data.keywords, aeo: data.aeo, competitors: data.competitors, avoid: data.avoid,
  }
}

/** The sheet and its model. `err` when the JSON could not be loaded. */
export function useKitePulse() {
  const [state, setState] = useState({ data: null, err: null })
  useEffect(() => {
    let alive = true
    import('./data/sheet.json')
      .then((m) => alive && setState({ data: m.default, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])
  const model = useMemo(() => (state.data ? buildModel(state.data) : null), [state.data])
  return { ...state, model }
}

/** A prototype's HTML, loaded on demand. */
export function usePrototype(file) {
  const [state, setState] = useState({ html: null, err: null })
  useEffect(() => {
    let alive = true
    setState({ html: null, err: null })
    const load = file && loadPrototype(file)
    if (!load) {
      if (file) setState({ html: null, err: `No file web/src/kitepulse/prototypes/${file}.html` })
      return undefined
    }
    load().then((t) => alive && setState({ html: t, err: null }))
      .catch((e) => alive && setState({ html: null, err: e.message }))
    return () => { alive = false }
  }, [file])
  return state
}

// ARTICLE PLANS (2026-11-03): docs/*Article Production Plan*.md, one entry per
// planned article, keyed by its URL. Read from the documents themselves, so the
// plan is written in one place and the site shows whatever it says now.
const PLAN_FILES = import.meta.glob('./docs/*Article Production Plan*.md', { query: '?raw', import: 'default' })

/**
 * Entries of a plan document, by URL. Each entry is `### <n> · <title>`, then
 * `- **Field:** value` lines; an indented `- item` or `1. item` belongs to the
 * field above it. An entry with no URL field is skipped, not guessed at.
 */
export function parsePlans(text) {
  const byUrl = new Map()
  for (const block of text.split(/^### /m).slice(1)) {
    const [head, ...lines] = block.split(/\r?\n/)
    const [article, ...rest] = head.split(' · ')
    const fields = []
    for (const line of lines) {
      const field = line.match(/^- \*\*(.+?):\*\* ?(.*)$/)
      const item = line.match(/^\s+(?:-|\d+\.) (.*)$/)
      if (field) fields.push({ label: field[1], value: field[2], items: [] })
      else if (item && fields.length) fields[fields.length - 1].items.push(item[1])
    }
    const url = fields.find((f) => f.label === 'URL')?.value.trim()
    if (url) byUrl.set(url, { article: article.trim(), title: rest.join(' · ').trim(), fields })
  }
  return byUrl
}

/** `plan` is the entry for one URL, null when no plan document lists it; `err` when they could not be read. */
export function useArticlePlan(url) {
  const [state, setState] = useState({ plan: null, err: null })
  useEffect(() => {
    let alive = true
    setState({ plan: null, err: null })
    Promise.all(Object.values(PLAN_FILES).map((load) => load()))
      .then((texts) => {
        if (!alive) return
        const found = texts.map(parsePlans).find((m) => m.has(url))
        setState({ plan: found ? found.get(url) : null, err: null })
      })
      .catch((e) => alive && setState({ plan: null, err: e.message }))
    return () => { alive = false }
  }, [url])
  return state
}

/** Address of a Kite Pulse page inside this app's preview. */
export const sitePath = (url) => (url === '/' ? '/kite-pulse' : `/kite-pulse${url}`)
