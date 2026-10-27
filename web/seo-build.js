/**
 * robots.txt and sitemap.xml, as pure functions - for vite.config.js and for
 * tests (tests/js/seo_build.mjs). Moved out of vite.config.js on 2026-10-09
 * (SEO items 8 and 9) so the rules can be tested without running a build.
 *
 * CLOSED BY DEFAULT (review of #508, item 3). The site is login-only, so every
 * build says noindex and `Disallow: /`. Indexing opens only when BOTH
 * `SITE_URL` is set and `PUBLIC_SITE=1` - an explicit decision that the pages
 * are public, never a side effect of setting a URL.
 */

/**
 * Pages that exist for anyone, whatever the evidence: always in the sitemap.
 * THE PUBLIC PAGES (2026-10-20). Until then this named /board and /models,
 * which have been signed-in since 2026-10-15, and left out every public page.
 * Kept in step with contract/indexing.yaml's `always` list.
 */
export const STRUCTURAL_PATHS = [
  '/', '/blogs', '/tools', '/best-ai-model', '/ai-model-pricing', '/token-counter', '/local-llm-vram-calculator',
  '/ai-models', '/ai-models/latest', '/compare', '/reviews', '/reviews/jobs', '/reviews/capabilities', '/reviews/metrics',
  '/glossary', '/methodology',
]

/**
 * Never in a sitemap, and disallowed in robots.txt when open: the signed-in
 * pages. /compare left this list on 2026-10-20 - it is a public tool now; a
 * comparison of named models stays noindex through its own head instead.
 */
export const PRIVATE_PATHS = ['/admin', '/login', '/board', '/models', '/seo-keywords', '/keywords', '/benchmarks']

export function siteOf(siteUrl, publicSite) {
  const site = (siteUrl || '').trim().replace(/\/+$/, '')
  const open = Boolean(site) && String(publicSite || '').trim() === '1'
  return { site, open }
}

export function robotsTxt({ site, open }) {
  const lines = open
    ? ['User-agent: *', 'Allow: /', ...PRIVATE_PATHS.map((p) => `Disallow: ${p}`), '', `Sitemap: ${site}/sitemap.xml`]
    : ['User-agent: *', 'Disallow: /']
  return lines.join('\n') + '\n'
}

const XML = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }
const xml = (s) => String(s).replace(/[&<>"']/g, (c) => XML[c])

/**
 * The sitemap: the structural pages plus `paths`, the pages judge/seo.py found
 * worth indexing (`scripts/export_indexable_paths.py`). Never a private path,
 * each path once. No <lastmod>: no page has a recorded "last changed" date,
 * and an invented one is worse than none (rule 6).
 */
export function sitemapXml(site, paths, lastmod = {}) {
  const keep = sitemapPaths(paths)
  if (keep.length > 50000) {
    throw new Error(`sitemap: ${keep.length} URLs is over the protocol's 50,000; split it before launch`)
  }
  // <lastmod> ONLY FROM A REAL DATE (judge/seo.py's `lastmod`), as a plain
  // date. A path with no date gets none - never the build time standing in.
  const day = (iso) => (typeof iso === 'string' && /^\d{4}-\d{2}-\d{2}/.test(iso) ? iso.slice(0, 10) : null)
  const urls = keep.map((p) => {
    const d = day(lastmod && lastmod[p])
    return `  <url><loc>${xml(site + p)}</loc>${d ? `<lastmod>${d}</lastmod>` : ''}</url>`
  }).join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`
}

/**
 * The exported path list, validated. Throws rather than returning an empty
 * list: an OPEN build with no evidence pages would ship a six-page sitemap
 * that looks complete (rule 12) - so the paths file is required once open.
 */
export function readPaths(text, source) {
  let data
  try {
    data = JSON.parse(text)
  } catch (e) {
    throw new Error(`sitemap: ${source} is not JSON (${e.message})`)
  }
  if (!data || !Array.isArray(data.paths) || !data.generated_at) {
    throw new Error(`sitemap: ${source} needs "generated_at" and a "paths" list - re-run scripts/export_indexable_paths.py`)
  }
  return data
}

/**
 * PRE-RENDERING (SEO, 2026-10-20). After `vite build`, web/prerender.js opens
 * each public page in a headless browser, waits for its data, and saves the
 * finished HTML, so a crawler or AI tool that runs no JavaScript still reads
 * the title, headings, text and structured data. The app then starts over the
 * saved page as before (createRoot, no hydration), so a visitor sees nothing
 * different.
 *
 * WHICH PAGES: the structural ones plus judge/seo.py's indexable list - the
 * sitemap's own pages. A path with a query string is one file with parameters,
 * so it is left to the app; a private path is never saved.
 */
export function prerenderPaths(paths = []) {
  return sitemapPaths(paths).filter((p) => !p.includes('?') && !p.includes('#'))
}

/** The sitemap's path list, shared by sitemapXml and prerenderPaths. */
export function sitemapPaths(paths = []) {
  return [...new Set([...STRUCTURAL_PATHS, ...paths])]
    .filter((p) => typeof p === 'string' && p.startsWith('/'))
    .filter((p) => !PRIVATE_PATHS.some((q) => p === q || p.startsWith(`${q}/`) || p.startsWith(`${q}?`)))
}

/**
 * Where a page's HTML is saved in dist/: `/` is index.html, any other path is
 * `<path>.html` - `/reviews/jobs` -> `reviews/jobs.html`. Not
 * `<path>/index.html`: nginx would answer `/reviews` with a redirect to
 * `/reviews/`, a second address for every page. nginx serves these through
 * `try_files $uri $uri.html` (web/nginx.conf.template). Null for a path that
 * is not safe as a file name.
 */
export function prerenderFile(path) {
  if (path === '/') return 'index.html'
  let p
  try { p = decodeURIComponent(path) } catch { return null }
  if (!p.startsWith('/') || p.endsWith('/') || p.includes('\0') || /(^|\/)\.\.?(\/|$)|[\\:*"<>|]/.test(p)) return null
  return `${p.slice(1)}.html`
}

/**
 * THE SHELL'S HEAD, carried in each saved page. head.js treats whatever the
 * document had at start as "the defaults" and restores them on leaving a page;
 * a saved page starts with ITS head, so web/src/main.jsx puts the shell's back
 * (from this JSON) before the app starts, and removes the saved page's JSON-LD
 * so the app does not add a second copy.
 */
export const SHELL_HEAD_ID = 'shell-head'

export function shellScript(head) {
  const json = JSON.stringify(head).replace(/</g, '\\u003c')
  return `<script type="application/json" id="${SHELL_HEAD_ID}">${json}</script>`
}
