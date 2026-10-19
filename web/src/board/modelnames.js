/**
 * Which written names in a blog post mean which model (2026-10-19).
 *
 * WHY. A post names "Opus 5.5" and "GLM-5.3"; the registry says
 * "Anthropic: Claude Opus 5.5" and "Z.ai: GLM 5.3". The linker knew only the
 * second form, and only for the 31 tracked models, so most names in most posts
 * were plain text. Measured 2026-10-19 over the 150 published posts: "Opus 5"
 * 381 times, "Opus 5.5" 219, "Fable 5.1" 110 - none linked; 43 of 99 "A vs B"
 * phrases had both sides linkable.
 *
 * THE NAMES ARE DERIVED, NEVER WRITTEN. Two per model, both by rules the fetch
 * already applies (`collect/registry/propose.py`):
 *
 *   the display name without its vendor prefix   "Claude Opus 5.5"
 *   the vendor word dropped (`rule_variants`)    "Opus 5.5"
 *
 * The second keeps `rule_variants`' guards: the dropped word is a family word,
 * what remains opens with a family word, carries a version, has no date stamp
 * and no route suffix. So "Gemini 3.8 Flash" gives no "3.8 Flash", and
 * "Mistral Large 3" gives no "Large 3" - a reordering or a tier word is a
 * judgement, not a rendering. FAMILY_WORDS must equal the Python set;
 * tests/test_blog_model_links.py fails when they drift.
 *
 * A SEPARATOR IS NOT PART OF A NAME (rule 10): "GLM-5.3", "GLM 5.3" and
 * "GLM5.3" are one key. Nothing else is folded.
 *
 * A NAME THAT FITS TWO MODELS LINKS TO NEITHER (rule 10, and rule 12: a link
 * that can land on the wrong model is not a fallback). "DeepSeek V4 Pro" is
 * 0423 or 0813; the post does not say which, so it stays plain text. A missed
 * link costs a click; a wrong one tells the reader a different model's price.
 *
 * Plain ESM, no JSX: views.js imports it and tests render views.js in node.
 */

export const FAMILY_WORDS = new Set([
  'opus', 'sonnet', 'haiku', 'fable', 'claude', 'gemini', 'gpt', 'chatgpt',
  'qwen', 'llama', 'mistral', 'mixtral', 'deepseek', 'grok', 'codex', 'kimi',
  'glm', 'nova', 'phi', 'command', 'flash', 'pro', 'mini', 'turbo', 'air',
  'plus',
])

/** Shorter than this and a surface collides with ordinary words (MIN_SURFACE_CHARS). */
const MIN_CHARS = 4
const PLAIN = /^[0-9a-z.]+$/
const DATE_STAMP = /\d{6,}/

/** The display name without its vendor prefix: "Anthropic: Claude Opus 5.5" -> "Claude Opus 5.5". */
export function shortName(m) {
  const d = String(m.display_name || m.canonical_id || '')
  const i = d.indexOf(': ')
  return (i >= 0 ? d.slice(i + 2) : d).trim()
}

/** The matching key: casefolded, every separator removed. */
export const nameKey = (s) => String(s).toLowerCase().replace(/[\s\-_]+/g, '')

/** `rule_variants`' vendor drop, guards included, or null. Display casing kept. */
export function vendorDropped(name, canonicalId = '') {
  const local = String(canonicalId).split('/').pop()
  if (local.includes(':')) return null                     // guard 5: a route
  const vendor = String(canonicalId).includes('/') ? String(canonicalId).split('/')[0].toLowerCase() : ''
  const words = String(name).replace(/[-_]/g, ' ').trim().split(/\s+/)
  if (words.length < 3) return null
  const low = words.map((w) => w.toLowerCase())
  if (!FAMILY_WORDS.has(low[0]) && low[0] !== vendor) return null   // guard 1
  if (!FAMILY_WORDS.has(low[1])) return null                         // guard 2
  const rest = low.slice(1)
  if (!rest.every((w) => PLAIN.test(w))) return null                  // guard 6
  if (!/\d/.test(rest.join(' ')) || DATE_STAMP.test(rest.join(' '))) return null  // guards 3, 4
  return words.slice(1).join(' ')
}

/**
 * key -> model, over every model given, with ambiguous keys removed.
 * `names` is every written form to look for, longest first.
 */
export function nameIndex(models) {
  const owners = new Map()   // key -> Set of model ids
  const forms = new Map()    // key -> one written form, for the pattern
  for (const m of models || []) {
    const id = m.canonical_id || m.model_version_id
    const full = shortName(m)
    for (const n of [full, vendorDropped(full, m.canonical_id || '')]) {
      if (!n || nameKey(n).length < MIN_CHARS) continue
      const k = nameKey(n)
      if (!owners.has(k)) { owners.set(k, new Set()); forms.set(k, n) }
      owners.get(k).add(id)
    }
  }
  const byKey = new Map()
  const ambiguous = new Set()
  const byId = new Map((models || []).map((m) => [m.canonical_id || m.model_version_id, m]))
  for (const [k, ids] of owners) {
    if (ids.size === 1) byKey.set(k, byId.get([...ids][0]))
    else ambiguous.add(k)
  }
  return { byKey, ambiguous, forms: [...forms.entries()].filter(([k]) => byKey.has(k)).map(([, n]) => n) }
}

const rxEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** One name as a pattern in which any separator, or none, may stand between its words. */
const formPattern = (n) => n.split(/[\s\-_]+/).map(rxEsc).join('[\\s\\-]?')

/**
 * The pattern for every name: a boundary at both ends, and a name must not run
 * on into a version - "GPT-6" never matches inside "GPT-6.1". Longest first, so
 * "GPT-6.1 Sol Pro" is never split into "GPT-6.1 Sol".
 */
export function namePattern(forms) {
  if (!forms.length) return null
  const alt = [...forms].sort((a, b) => b.length - a.length).map(formPattern).join('|')
  return `(?<![\\w.\\-])(?:${alt})(?![\\w\\-]|\\.\\d)`
}
