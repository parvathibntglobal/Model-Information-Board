/**
 * THE TOKEN COUNTER'S ARITHMETIC (2026-10-12). Pure functions, no tokenizer and
 * no DOM, so node can test them where CI installs no frontend dependencies.
 *
 * A cost here is a COUNT times a MEASUREMENT: tokens counted in the browser,
 * times the provider's advertised rate per million tokens. Rule 3 permits both;
 * nothing is scored. Rule 6 governs the rate: a NULL rate is "no rate", never
 * free and never the cheapest, so a model without one is listed apart rather
 * than priced at $0 or dropped.
 */

export const PER_MILLION = 1_000_000

/** USD for `tokens` at `ratePerMillion`, over `calls` calls. Null when either is unknown. */
export function costOf(tokens, ratePerMillion, calls = 1) {
  if (tokens == null || ratePerMillion == null) return null
  return (tokens * ratePerMillion * calls) / PER_MILLION
}

/**
 * A cost as text. A real charge never prints as "$0": a value below the floor
 * says so (the `fmtPrice` rule, one layer later). Zero is only ever a free rate.
 */
export function fmtUsd(n) {
  if (n == null) return '—'
  if (n === 0) return '$0'
  if (n < 0.000001) return '<$0.000001'
  if (n < 1) return `$${n.toPrecision(3)}`
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export const countWords = (text) => (text.match(/\S+/g) || []).length
export const countLines = (text) => (text ? text.split('\n').length : 0)

/**
 * 'exact' only when the tokenizer library itself names the model's encoding as
 * the one this page counts with. Anything it does not know - a newer OpenAI
 * model it has not listed, every other provider - is an 'estimate'. Unknown is
 * never promoted to exact (rule 12): `encodingNameFor` returns null for a model
 * the library does not list.
 */
export function exactnessOf(m, encodingNameFor, encoding = 'o200k_base') {
  if (!encodingNameFor || (m.provider || '').toLowerCase() !== 'openai' || !m.canonical_id) return 'estimate'
  const name = m.canonical_id.split('/').pop()
  return encodingNameFor(name) === encoding ? 'exact' : 'estimate'
}

const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '')

/**
 * The cost table. `direction` picks the rate: 'input' prices the text as a
 * prompt, 'output' as an answer the model writes.
 *
 * Returns `priced` (a rate exists, possibly 0) and `unpriced` (no rate for that
 * direction). `sort` is 'name' unless the reader asks for 'cost': the order is a
 * control the reader chose, beside the figure it orders by.
 */
export function priceRows(models, { tokens, direction = 'input', calls = 1, query = '', sort = 'name', encodingNameFor } = {}) {
  const key = direction === 'output' ? 'price_out' : 'price_in'
  const q = norm(query)
  const priced = []
  const unpriced = []
  for (const m of models || []) {
    if (q && ![m.display_name, m.provider, m.canonical_id].some((s) => norm(s).includes(q))) continue
    const rate = m[key]
    const row = {
      id: m.canonical_id || m.model_version_id,
      mvId: m.model_version_id,
      name: m.display_name || m.canonical_id || m.model_version_id,
      provider: m.provider,
      rate: rate ?? null,
      exactness: exactnessOf(m, encodingNameFor),
      fit: fitOf(tokens, m, direction),
      one: costOf(tokens, rate, 1),
      many: costOf(tokens, rate, calls),
    }
    if (rate == null) unpriced.push(row)
    else priced.push(row)
  }
  const byName = (a, b) => a.name.localeCompare(b.name)
  priced.sort(sort === 'cost' ? (a, b) => (a.rate - b.rate) || byName(a, b) : byName)
  unpriced.sort(byName)
  return { priced, unpriced }
}

/**
 * WILL IT FIT. As input, the text must fit the context window and what is
 * left is the room for the answer; as output, it must fit `max_output_tokens`.
 * A model that publishes no limit is 'unknown', never 'fits' (rule 6). Null
 * while the text is not counted yet.
 */
export function fitOf(tokens, m, direction = 'input') {
  if (tokens == null) return null
  const limit = direction === 'output' ? m.max_output_tokens : m.advertised_context
  if (limit == null) return { state: 'unknown', limit: null }
  if (tokens > limit) return { state: 'over', limit, by: tokens - limit }
  return { state: 'fits', limit, room: limit - tokens }
}

/** A month, for "per month". Stated on the page, not implied. */
export const DAYS_PER_MONTH = 30

/**
 * One model priced for a WORKLOAD: `inTok` in and `outTok` out per call,
 * `callsPerDay` calls, `cachedShare` (0-1) of the input read from cache.
 *
 * Null when a rate the workload needs is missing (an input rate when inTok > 0,
 * an output rate when outTok > 0). A cached share on a model with no cached
 * price is priced WITHOUT caching and says so (`cache: 'none'`): the reader
 * sees which rows that happened to, rather than a missing rate turning into a
 * cheaper or dearer number silently.
 */
export function workloadCost(m, { inTok = 0, outTok = 0, callsPerDay = 1, cachedShare = 0, days = DAYS_PER_MONTH } = {}) {
  if ((inTok > 0 && m.price_in == null) || (outTok > 0 && m.price_out == null)) return null
  const share = Math.min(1, Math.max(0, cachedShare))
  let cache = 'off'
  let inRate = m.price_in ?? 0
  if (share > 0 && inTok > 0) {
    if (m.price_cached_read != null) {
      inRate = (1 - share) * m.price_in + share * m.price_cached_read
      cache = 'applied'
    } else {
      cache = 'none'
    }
  }
  const perCall = (inTok * inRate + outTok * (m.price_out ?? 0)) / PER_MILLION
  return { perCall, perDay: perCall * callsPerDay, perMonth: perCall * callsPerDay * days, cache }
}

/**
 * The workload table. A call fits when input + output fit the context window
 * and the output fits `max_output_tokens`; a missing limit makes it 'unknown'.
 */
export function workloadRows(models, { inTok = 0, outTok = 0, callsPerDay = 1, cachedShare = 0, query = '', sort = 'name', encodingNameFor } = {}) {
  const q = norm(query)
  const priced = []
  const unpriced = []
  for (const m of models || []) {
    if (q && ![m.display_name, m.provider, m.canonical_id].some((s) => norm(s).includes(q))) continue
    const cost = workloadCost(m, { inTok, outTok, callsPerDay, cachedShare })
    const ctx = fitOf(inTok + outTok, m, 'input')
    const out = fitOf(outTok, m, 'output')
    const fit = ctx.state === 'over' || out.state === 'over' ? 'over'
      : ctx.state === 'unknown' || out.state === 'unknown' ? 'unknown' : 'fits'
    const row = {
      id: m.canonical_id || m.model_version_id,
      mvId: m.model_version_id,
      name: m.display_name || m.canonical_id || m.model_version_id,
      provider: m.provider,
      exactness: exactnessOf(m, encodingNameFor),
      fit,
      ...(cost || { perCall: null, perDay: null, perMonth: null, cache: null }),
    }
    if (cost == null) unpriced.push(row)
    else priced.push(row)
  }
  const byName = (a, b) => a.name.localeCompare(b.name)
  priced.sort(sort === 'cost' ? (a, b) => (a.perMonth - b.perMonth) || byName(a, b) : byName)
  unpriced.sort(byName)
  return { priced, unpriced }
}
