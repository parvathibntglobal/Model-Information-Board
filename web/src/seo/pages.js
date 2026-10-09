/**
 * PER-PAGE <head> TEXT: what each route says its title and description are.
 *
 * Pure functions, no DOM - `useHead` (./head.js) applies what these return.
 * Item 1 of the SEO plan (2026-10-08): the whole site shared one <title> and
 * one description, so every model, job, capability and metric page looked the
 * same to a search engine and to a browser tab. Nothing here makes the site
 * indexable - `index.html`'s `noindex, nofollow` still governs every page, and
 * a page can only make robots STRICTER (see head.js).
 *
 * WHAT A DESCRIPTION MAY SAY. Names and the section's own definition, never a
 * count: a number in a description is cached by whoever reads it and goes
 * stale with nothing on the page to correct it (rule 11). And never a
 * platform name - descriptions are for the public view, which withholds some
 * sources entirely (`contract/publication.yaml`); a definition that names one
 * is dropped for the template sentence rather than published.
 */

export const SITE = 'Model Information Board'
/** Search engines show about 60 characters of a title, ~155 of a description. */
export const TITLE_MAX = 60
export const DESCRIPTION_MAX = 155

const PLATFORM = /\b(reddit|subreddit|twitter|tweets?|x\.com|arxiv|hacker ?news|hn|dev\.to|hugging ?face|github)\b/i

/** `Name | Model Information Board`; the name alone when both would not fit;
 *  the name clipped when even it is too long. */
export function fullTitle(name) {
  if (!name) return null
  const clean = squash(name)
  const both = `${clean} | ${SITE}`
  return both.length <= TITLE_MAX ? both : clip(clean, TITLE_MAX)
}

/** One line, whitespace collapsed, cut at a word boundary with an ellipsis. */
export function clip(text, max = DESCRIPTION_MAX) {
  const t = squash(text)
  if (t.length <= max) return t
  const cut = t.slice(0, max - 1)
  const at = cut.lastIndexOf(' ')
  return `${(at > max * 0.6 ? cut.slice(0, at) : cut).replace(/[,;:\s]+$/, '')}…`
}

function squash(s) {
  return String(s ?? '').replace(/\s+/g, ' ').trim()
}

/** A definition sentence, unless it is empty or names a platform. */
function usable(definition) {
  const d = squash(definition)
  return d && !PLATFORM.test(d) ? d : ''
}

function withDefinition(lead, definition) {
  const d = usable(definition)
  return clip(d ? `${lead} ${d.endsWith('.') ? d : `${d}.`}` : lead)
}

/* ── the pages ─────────────────────────────────────────────────────────── */

const BOARD_TABS = {
  best: ['AI models by job', 'Which AI models engineers report working for each job, from coding agents to code review, in their own words.'],
  cap: ['AI models by capability', 'How AI models behave on each capability, as engineers report it in production, in their own words.'],
  met: ['AI model metrics', 'Figures engineers report for AI models, such as cost per token and latency, each with the quote it came from.'],
}

/** `/board?tab=` */
export function boardHub(tab) {
  const [title, description] = BOARD_TABS[tab] || BOARD_TABS.best
  return { title: fullTitle(title), description, canonical: tab && tab !== 'best' ? `/board?tab=${tab}` : '/board' }
}

// Breadcrumbs (SEO item 6): the board, then the tab a section lives on.
const BOARD_CRUMB = { name: 'Board', path: '/board' }

const SECTION = {
  jobs: { path: 'jobs', tab: { name: 'Jobs', path: '/board' }, title: (n) => `Best AI models for ${n}`, lead: (n) => `Which AI models engineers report working for ${n}.` },
  capabilities: { path: 'capabilities', tab: { name: 'Capabilities', path: '/board?tab=cap' }, title: (n) => `${n}: how AI models compare`, lead: (n) => `How AI models handle ${n}, as engineers report it.` },
  metrics: { path: 'metrics', tab: { name: 'Metrics', path: '/board?tab=met' }, title: (n) => `${n} by AI model`, lead: (n) => `${n} figures engineers report for AI models, each with its quote.` },
}

/** `/board/{jobs|capabilities|metrics}/:slug`, from the section's own row. */
export function boardSection(seg, item) {
  const s = SECTION[seg]
  if (!s || !item) return null
  const canonical = `/board/${s.path}/${item.slug}`
  return {
    title: fullTitle(s.title(item.name)),
    description: withDefinition(s.lead(item.name), item.card),
    canonical,
    breadcrumbs: [BOARD_CRUMB, s.tab, { name: squash(item.name), path: canonical }],
  }
}

/** `/board/{seg}/:slug/:model` - one model's reports in one section. */
export function boardModelInSection(seg, item, modelKey, modelName) {
  const s = SECTION[seg]
  if (!s || !item || !modelKey) return null
  const m = squash(modelName || modelKey)
  const title = seg === 'jobs' ? `${m} for ${item.name}` : `${m}: ${item.name}`
  const section = `/board/${s.path}/${item.slug}`
  const canonical = `${section}/${modelKey}`
  return {
    title: fullTitle(title),
    description: clip(`What engineers report about ${m} on ${item.name}, quoted exactly as they wrote it.`),
    canonical,
    breadcrumbs: [BOARD_CRUMB, s.tab, { name: squash(item.name), path: section }, { name: m, path: canonical }],
  }
}

export function modelsIndex() {
  return {
    title: fullTitle('AI models compared'),
    description: 'Every AI model the board tracks, with what engineers report about each one in production and its list price per token.',
    canonical: '/models',
  }
}

/** `/models/*`. `id` is the route key as the URL carries it. */
export function modelPage(id, name) {
  const m = squash(name || id)
  return {
    title: fullTitle(`${m}: what engineers report`),
    description: clip(`What engineers report about ${m} in production: the jobs it works for, its capabilities and the figures they measured, in their own words.`),
    canonical: `/models/${id}`,
    breadcrumbs: [{ name: 'Models', path: '/models' }, { name: m, path: `/models/${id}` }],
  }
}

/** `/compare?ids=`. The canonical sorts the ids, so A-vs-B and B-vs-A are one page. */
export function comparePage(ids, names) {
  const list = (names && names.length ? names : ids).map(squash).filter(Boolean)
  if (list.length < 2) {
    return { title: fullTitle('Compare AI models'), description: 'Put two or three AI models side by side on what engineers report about each.', canonical: '/compare' }
  }
  return {
    title: fullTitle(list.join(' vs ')),
    description: clip(`${list.join(' vs ')}: what engineers report about each, side by side, by the jobs, capabilities and metrics they share.`),
    canonical: `/compare?ids=${[...ids].sort().join(',')}`,
  }
}

export function blogIndex() {
  return {
    title: fullTitle('Notes on AI models'),
    description: 'Long-form notes on AI models, written from what engineers report in production.',
    canonical: '/blogs',
  }
}

/** `/blogs/:slug`, from the post itself. A post the reader may not see gets the index's head. */
export function blogPost(post) {
  if (!post) return blogIndex()
  const text = usable(post.dek) || usable(post.lead) || 'A note on AI models, written from what engineers report in production.'
  const canonical = `/blogs/${post.slug}`
  return {
    title: fullTitle(post.title),
    description: clip(text),
    canonical,
    breadcrumbs: [{ name: 'Blogs', path: '/blogs' }, { name: squash(post.title), path: canonical }],
    // Article markup (SEO item 11): only what the post carries; structured.js
    // leaves out any field that is missing rather than filling it.
    article: {
      slug: post.slug,
      title: post.title,
      dek: usable(post.dek) || null,
      published_at: post.published_at || null,
      provenance: { generated_at: (post.provenance && post.provenance.generated_at) || null },
    },
  }
}

/** Never indexed, whatever index.html says later. */
export const PRIVATE = {
  login: { title: fullTitle('Sign in'), noindex: true },
  admin: { title: fullTitle('Admin'), noindex: true },
  blogLogs: { title: fullTitle('Blog run logs'), noindex: true },
  notFound: { title: fullTitle('Page not found'), noindex: true },
}

/**
 * Whether a page is `noindex`: it asked to be, or its canonical path is not on
 * the indexable list (SEO item 5, `contract/indexing.yaml`). An unknown list
 * (`null`: loading, or the request failed) counts as "not on it" - a page that
 * cannot ask is never indexed by default. A page with no canonical has nothing
 * to look up and keeps index.html's robots.
 */
export function noindexFor(head, indexable) {
  if (!head) return false
  if (head.noindex) return true
  if (!head.canonical) return false
  return !(indexable && indexable.has(head.canonical))
}
