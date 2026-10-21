/**
 * THE SPEC FINDER'S LOGIC (2026-10-12). Pure, so node can test it.
 *
 * Filters on what each model is ADVERTISED to do - what it reads and writes,
 * feature flags, context window, list price. Vendor claims, not evidence; the
 * page says so. Since 2026-10-15 the page feeds it the whole catalogue (every
 * model OpenRouter lists, every output type) through `fromCatalog`, and what a
 * model reads and writes is one more requirement here, not a second finder.
 *
 * THREE OUTCOMES, NEVER TWO (rule 6). A filter on a value the provider has not
 * published cannot say "no": `judge/`'s hard filter once read an absent
 * `supports_tools` as "cannot" and took a candidate list from 11 models to 1,
 * with nothing on the page to disagree with. So a model is
 *
 *   match      every filter it was asked passes on a published value
 *   unknown    nothing fails, but at least one value it needs is unpublished -
 *              shown in its own group, naming what is missing
 *   ruled out  a PUBLISHED value fails a filter - counted, by reason
 */

export const FLAGS = [
  { key: 'supports_tools', label: 'Tool calling' },
  { key: 'supports_vision', label: 'Vision input' },
  { key: 'supports_structured_output', label: 'Structured output' },
  { key: 'supports_reasoning', label: 'Reasoning mode' },
  { key: 'supports_caching', label: 'Prompt caching' },
]

/** What a model can be asked to read, and to write - OpenRouter's modalities. */
export const INPUTS = ['text', 'image', 'audio', 'video', 'file']
export const OUTPUTS = ['text', 'image', 'video', 'speech', 'audio', 'transcription', 'decisions', 'embeddings', 'rerank']

/**
 * A catalogue model (GET /model-catalog) in the shape `judge` reads. A price
 * OpenRouter does not publish per token stays NULL - unknown to a ceiling,
 * never free - and a `:free` variant is a published 0 (rule 6).
 */
export function fromCatalog(m, providerName) {
  const f = m.features || {}
  const free = m.price_state === 'free'
  const perToken = m.price_state === 'priced'
  return {
    model_version_id: m.id,
    canonical_id: m.id,
    display_name: m.name,
    provider: providerName || m.provider,
    inputs: m.inputs,
    outputs: m.outputs,
    supports_tools: f.tools ?? null,
    supports_vision: f.vision_input ?? null,
    supports_structured_output: f.structured_output ?? null,
    supports_reasoning: f.reasoning ?? null,
    supports_caching: f.prompt_caching ?? null,
    advertised_context: m.context ?? null,
    max_output_tokens: m.max_output_tokens ?? null,
    price_in: free ? 0 : perToken ? m.price_in : null,
    price_out: free ? 0 : perToken ? m.price_out : null,
    listed_at: m.listed_at,
    voices: m.voices || 0,
    board: { entries: m.reports || 0 },
  }
}

/** Context floors offered, in tokens. 0 = any. */
export const CONTEXT_STEPS = [0, 32_000, 128_000, 200_000, 400_000, 1_000_000]

const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '')

/** One model against the filters: { outcome, unknown: [what], failed: [what] }. */
export function judge(m, { need = [], ins = [], outs = [], minContext = 0, maxIn = null, maxOut = null } = {}) {
  const unknown = []
  const failed = []
  // WHAT IT READS AND WRITES. A model whose modalities are not published at
  // all is unknown, not ruled out.
  for (const [want, have, verb] of [[ins, m.inputs, 'Reads'], [outs, m.outputs, 'Writes']]) {
    for (const x of want) {
      if (have == null) unknown.push(`${verb} ${x}`)
      else if (!have.includes(x)) failed.push(`${verb} ${x}`)
    }
  }
  for (const key of need) {
    const flag = FLAGS.find((f) => f.key === key)
    const label = flag ? flag.label : key
    const v = m[key]
    if (v == null) unknown.push(label)
    else if (!v) failed.push(label)
  }
  if (minContext > 0) {
    if (m.advertised_context == null) unknown.push('Context window')
    else if (m.advertised_context < minContext) failed.push('Context window')
  }
  if (maxIn != null) {
    if (m.price_in == null) unknown.push('Input rate')
    else if (m.price_in > maxIn) failed.push('Input rate')
  }
  if (maxOut != null) {
    if (m.price_out == null) unknown.push('Output rate')
    else if (m.price_out > maxOut) failed.push('Output rate')
  }
  const outcome = failed.length ? 'out' : unknown.length ? 'unknown' : 'match'
  return { outcome, unknown, failed }
}

const SORTS = {
  name: () => 0,
  // nulls last in both: an unpublished figure is not the cheapest or the largest
  price: (a, b) => (a.price_in ?? Infinity) - (b.price_in ?? Infinity),
  context: (a, b) => (b.advertised_context ?? -1) - (a.advertised_context ?? -1),
  newest: (a, b) => (b.listed_at || '').localeCompare(a.listed_at || ''),
  // A COUNT, shown on every row beside the order it makes (rule 3).
  voices: (a, b) => (b.voices || 0) - (a.voices || 0),
}

/**
 * Every model, sorted into the three outcomes. `query` narrows by name first
 * and is not counted as ruling anything out. `reportedOnly` keeps models with
 * at least one board entry; it is a count, so it is a filter like any other.
 */
export function findModels(models, { need = [], ins = [], outs = [], minContext = 0, maxIn = null, maxOut = null, query = '', sort = 'name', reportedOnly = false } = {}) {
  const q = norm(query)
  const match = []
  const unknown = []
  const outBy = {}
  let out = 0
  for (const m of models || []) {
    if (q && ![m.display_name, m.provider, m.canonical_id].some((s) => norm(s).includes(q))) continue
    if (reportedOnly && !((m.board && m.board.entries) > 0)) continue
    const v = judge(m, { need, ins, outs, minContext, maxIn, maxOut })
    if (v.outcome === 'out') {
      out += 1
      for (const f of v.failed) outBy[f] = (outBy[f] || 0) + 1
    } else (v.outcome === 'match' ? match : unknown).push({ m, unknown: v.unknown })
  }
  const by = SORTS[sort] || SORTS.name
  const order = (a, b) => by(a.m, b.m) || (a.m.display_name || '').localeCompare(b.m.display_name || '')
  match.sort(order)
  unknown.sort(order)
  return { match, unknown, out, outBy }
}
