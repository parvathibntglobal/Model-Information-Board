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

/** Pages that exist for anyone, whatever the evidence: always in the sitemap. */
export const STRUCTURAL_PATHS = ['/', '/board', '/board?tab=cap', '/board?tab=met', '/models', '/blogs']

/** Never in a sitemap, and disallowed in robots.txt when open. */
export const PRIVATE_PATHS = ['/admin', '/login', '/compare']

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
export function sitemapXml(site, paths) {
  const keep = [...new Set([...STRUCTURAL_PATHS, ...paths])]
    .filter((p) => typeof p === 'string' && p.startsWith('/'))
    .filter((p) => !PRIVATE_PATHS.some((q) => p === q || p.startsWith(`${q}/`) || p.startsWith(`${q}?`)))
  if (keep.length > 50000) {
    throw new Error(`sitemap: ${keep.length} URLs is over the protocol's 50,000; split it before launch`)
  }
  const urls = keep.map((p) => `  <url><loc>${xml(site + p)}</loc></url>`).join('\n')
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
