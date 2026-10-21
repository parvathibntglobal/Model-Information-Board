/**
 * Structured data (JSON-LD) - SEO items 6 and 11, 2026-10-09.
 *
 * Pure builders: pages describe themselves with plain data (a breadcrumb trail,
 * a post) in their `useHead` head, and head.js turns it into
 * `<script type="application/ld+json">` with these. Node tests them through
 * tests/js/seo_pages.mjs.
 *
 * ABSOLUTE URLS OR NOTHING. Schema.org needs absolute URLs, so every builder
 * takes the site address and returns null without one - the same rule as the
 * canonical link: no host is guessed (rule 12). Until the site is open
 * (SITE_URL + PUBLIC_SITE=1 at build), no structured data is written at all.
 *
 * NOTHING HERE IS INVENTED. A field the data does not carry is left out, never
 * filled with a plausible value (rule 6): no image the post does not have, no
 * `datePublished` without a recorded approval, no person as author - the posts
 * are generated and reviewed, so the author is the board itself.
 */

export const ORG = 'Model Information Board'

function abs(site, path) {
  return `${site}${path.startsWith('/') ? path : `/${path}`}`
}

/** `trail`: [{ name, path }], outermost first; the last is the page itself. */
export function breadcrumbList(site, trail) {
  if (!site || !Array.isArray(trail) || trail.length < 2) return null
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: trail.map((t, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: t.name,
      item: abs(site, t.path),
    })),
  }
}

/**
 * A blog post. `post` carries what the post page has: slug, title, dek,
 * `published_at` (when it was approved, judge/blog_store.published) and
 * `provenance.generated_at` (when the draft was written).
 */
export function article(site, post) {
  if (!site || !post || !post.slug || !post.title) return null
  const out = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    // Search engines truncate a headline over 110 characters.
    headline: String(post.title).slice(0, 110),
    url: abs(site, `/blogs/${post.slug}`),
    mainEntityOfPage: abs(site, `/blogs/${post.slug}`),
    author: { '@type': 'Organization', name: ORG, url: abs(site, '/') },
    publisher: { '@type': 'Organization', name: ORG, url: abs(site, '/') },
    isAccessibleForFree: true,
  }
  if (post.description || post.dek) out.description = String(post.description || post.dek)
  if (Array.isArray(post.keywords) && post.keywords.length) out.keywords = post.keywords.join(', ')
  if (post.published_at) out.datePublished = post.published_at
  const created = post.provenance && post.provenance.generated_at
  if (created) out.dateCreated = created
  return out
}

/**
 * A board or model page, with when its newest entry was added (`modified`,
 * from the freshness dates). Only when that date exists - never the build or
 * render time standing in for one.
 */
export function webPage(site, head) {
  if (!site || !head || !head.canonical || !head.modified) return null
  return {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    url: abs(site, head.canonical),
    name: head.title,
    dateModified: head.modified,
  }
}

/** A glossary term (2026-10-20): schema.org DefinedTerm, in the glossary's set. */
export function definedTerm(site, t) {
  if (!site || !t || !t.name || !t.path) return null
  const out = {
    '@context': 'https://schema.org',
    '@type': 'DefinedTerm',
    name: t.name,
    description: t.description,
    url: abs(site, t.path),
    inDefinedTermSet: { '@type': 'DefinedTermSet', name: 'Glossary', url: abs(site, '/glossary') },
  }
  if (t.aka && t.aka.length) out.alternateName = t.aka
  return out
}

/**
 * A free tool that runs in the browser (2026-10-21): the cost calculator, the
 * pricing table, the picker and the comparison. Its name, address and
 * description are the page's own; "free" is what the site states. No rating,
 * no review count - the tools have none.
 */
export function webApplication(site, head) {
  if (!site || !head || !head.app || !head.app.name || !head.canonical) return null
  const out = {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: head.app.name,
    url: abs(site, head.canonical),
    applicationCategory: 'DeveloperApplication',
    operatingSystem: 'Any',
    isAccessibleForFree: true,
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
    publisher: { '@type': 'Organization', name: ORG, url: abs(site, '/') },
  }
  if (head.description) out.description = head.description
  return out
}

/**
 * A list the page shows, in the page's own order (2026-10-21): the models on
 * All models or one type, the newest releases, the models or jobs a reviews
 * page ranks. `list.items` is [{ name, path }]; nothing is listed that the
 * page does not show, and an empty list writes nothing.
 *
 * THE FIRST ITEM_LIST_MAX ONLY (review of #552): All models would otherwise
 * put every model in one script block, and a search engine gains nothing from
 * the length. `numberOfItems` counts what is listed here.
 */
export const ITEM_LIST_MAX = 100
export function itemList(site, list) {
  if (!site || !list || !Array.isArray(list.items)) return null
  const items = list.items.filter((it) => it && it.name && it.path).slice(0, ITEM_LIST_MAX)
  if (!items.length) return null
  const out = {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    numberOfItems: items.length,
    itemListElement: items.map((it, i) => ({ '@type': 'ListItem', position: i + 1, name: it.name, url: abs(site, it.path) })),
  }
  if (list.name) out.name = list.name
  return out
}

/** Everything a head asks for, built for `site`; [] when closed or nothing applies. */
export function structuredFor(site, head) {
  if (!site || !head) return []
  return [breadcrumbList(site, head.breadcrumbs), article(site, head.article), webPage(site, head),
    definedTerm(site, head.definedTerm), webApplication(site, head), itemList(site, head.list)]
    .filter(Boolean)
}
