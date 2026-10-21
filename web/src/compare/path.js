/**
 * THE COMPARISON'S ADDRESS (2026-10-20): `/compare/grok-4.6-vs-gpt-6-sol`.
 *
 * It was `/compare?ids=x-ai/grok-4.6,openai/gpt-6-sol`: a query string, so a
 * search engine read it as one page with parameters; the slash and the comma
 * came out percent-encoded wherever the link was shared; and the words people
 * search - "grok 4.6 vs gpt 6 sol" - were not in the address. The path names
 * each model by the part of its readable id after the provider, joined by
 * `-vs-`, which is what the search reads like.
 *
 * READ BACK THROUGH THE CATALOGUE. A model's own name (`grok-4.6`) is unique
 * across the catalogue's providers (648 models, checked 2026-10-20), so the
 * page resolves each name to its full id there (`resolveSlugs`). An address
 * written with the full id (`x-ai--grok-4.6`) also resolves, so a name that is
 * ever shared by two providers can still be named exactly.
 *
 * `?ids=` STILL WORKS. An old link opens the page, which moves to the readable
 * path when every id is a readable one. An internal registry id (`mv_...`) has
 * no readable name, so a comparison of those keeps the query form.
 *
 * ONE CANONICAL PER SET OF MODELS: the names sorted, so A-vs-B and B-vs-A are
 * one page to a search engine. Pure functions - tested through node.
 */
export const SEP = '-vs-'
const FULL = '--'

/** A readable id is `provider/model`; an internal key (`mv_...`) is not. */
export const isReadable = (id) => typeof id === 'string' && /^[^/\s,]+\/[^/\s,]+$/.test(id) && !id.startsWith('mv_')

/** The model's own name: the part of its id after the provider. */
export const slugOf = (id) => id.split('/')[1]

const query = (from) => (from === 'reports' ? 'from=reports' : '')

/** Where a comparison of `ids` lives. `from: 'reports'` keeps the counts-only view. */
export function comparePath(ids, { from } = {}) {
  const list = (ids || []).map((s) => String(s).trim()).filter(Boolean)
  const q = query(from)
  if (list.length >= 2 && list.every(isReadable)) {
    return `/compare/${list.map((id) => encodeURIComponent(slugOf(id))).join(SEP)}${q ? `?${q}` : ''}`
  }
  if (!list.length) return `/compare${q ? `?${q}` : ''}`
  return `/compare?ids=${encodeURIComponent(list.join(','))}${q ? `&${q}` : ''}`
}

/** The canonical: the same models in one order, whichever order they were picked in. */
export function canonicalComparePath(ids) {
  const list = (ids || []).filter(Boolean)
  if (list.length >= 2 && list.every(isReadable)) {
    return `/compare/${list.map(slugOf).sort().map(encodeURIComponent).join(SEP)}`
  }
  return list.length >= 2 ? `/compare?ids=${[...list].sort().join(',')}` : '/compare'
}

/** The names in a `/compare/<a>-vs-<b>` path segment, in their order. */
export function parsePair(pair) {
  let text = String(pair || '')
  try { text = decodeURIComponent(text) } catch { /* keep the raw text */ }
  return text.split(SEP).map((s) => s.trim()).filter(Boolean)
}

/**
 * Each name to its catalogue id. `models` is the catalogue's list (each with an
 * `id`). Returns { ids, unknown }: the ids found, in order, and the names that
 * matched no model - or more than one, which is not guessed between.
 */
export function resolveSlugs(slugs, models) {
  const byName = new Map()
  const all = new Set()
  for (const m of models || []) {
    if (!m || !isReadable(m.id)) continue
    all.add(m.id)
    const name = slugOf(m.id)
    byName.set(name, byName.has(name) ? null : m.id)   // null marks a name two providers share
  }
  const ids = []
  const unknown = []
  for (const s of slugs || []) {
    const full = s.includes(FULL) ? s.replace(FULL, '/') : null
    const id = full && all.has(full) ? full : byName.get(s)
    if (id) ids.push(id)
    else unknown.push(s)
  }
  return { ids, unknown }
}
