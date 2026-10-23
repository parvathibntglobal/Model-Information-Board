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
  { url: '/security', type: 'Trust',
    notes: 'How Kite Pulse keeps data safe: secrets stripped on the device, data only on the team\'s own server, the audit log and leaked-credential checks (Product Guide, "Privacy and trust"). Mentlio has a /security page; the keyword sheet has no page or keyword rows for it.' },
  { url: '/glossary', type: 'Glossary',
    notes: 'An index of short definitions, one page per term. Mentlio ranks with /glossary/tokenmaxxing.' },
  { url: '/glossary/tokenmaxxing', type: 'Glossary', main: 'tokenmaxxing',
    notes: 'Keyword rows 581 (Main) and 582 (FAQ, "what is tokenmaxxing") target /blog/measure-developer-productivity-ai today, and the Page Map notes ask whether tokenmaxxing needs its own page. Mentlio answered that with /glossary/tokenmaxxing. Moving the two rows here would answer it for us.' },
  { url: '/changelog', type: 'Docs',
    notes: 'What changed in each Kite Pulse release. Mentlio has one; it shows a product that is maintained.' },
]

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
    site: [...pages, ...proposed],
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

/** Address of a Kite Pulse page inside this app's preview. */
export const sitePath = (url) => (url === '/' ? '/kite-pulse' : `/kite-pulse${url}`)
