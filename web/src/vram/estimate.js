/**
 * THE LOCAL VRAM TOOL'S GROUPING (docs/proposals/can-i-run-it.md).
 *
 * Every constant comes from GET /local-models, which reads contract/ - this file
 * has none of its own (rules 5 and 12). The ONE figure a row shows is the
 * measured file size. What is computed here decides only the group - a word -
 * and is never shown as a number (rule 3).
 *
 *   weights   the measured GGUF file size (the sum of its parts)
 *   cache     bytes per element x (full elements x tokens
 *             + windowed elements x min(tokens, window + window_extra_tokens))
 *             + a fixed recurrent state
 *   need      weights + cache + runtime allowance (once per card when split)
 *   budget    memory x cards (a graphics card) | memory x the Mac's GPU share
 *   group     fits | tight | wont | unknown. "unknown" (can't tell) when the
 *             file plus allowance fit but the cache is unknown (rule 6), or is
 *             only an upper bound that does not fit: a bound can prove fits or
 *             tight, never won't fit (#559 review).
 */

export const GIB = 2 ** 30

/** The context the model can take: the reader's pick, capped at the model's own maximum. */
export function effectiveContext(cache, tokens) {
  const max = cache && cache.max_context
  return max && max < tokens ? { tokens: max, capped: true } : { tokens, capped: false }
}

/** Bytes beyond the file, or null when the header did not let us know (rule 6). */
export function cacheBytes(cache, tokens, bytesPerElement, windowExtra) {
  // Required, never defaulted (rule 12): a missing constant must fail, not count 0.
  if (typeof windowExtra !== 'number') throw new Error('cacheBytes: window_extra_tokens is required')
  if (!cache || cache.basis === 'unknown' || cache.full_elements == null) return null
  // llama.cpp holds window + one micro-batch for a windowed layer.
  const windowed = (cache.windowed || []).reduce((s, w) => s + w.elements * Math.min(tokens, w.window + windowExtra), 0)
  return bytesPerElement * (cache.full_elements * tokens + windowed) + (cache.fixed_bytes || 0)
}

/** The memory a model may use on this hardware. */
export function budgetBytes(device, cards) {
  if (device.kind === 'unified') return device.memory_gib * GIB * device.gpu_share
  return device.memory_gib * GIB * cards
}

/**
 * One model on one hardware choice: its group, and the facts the row states in
 * words. `null` when the model has no measured size for this quantization -
 * never a guessed one.
 */
export function estimate(model, { quant, tokens, cacheType, device, cards }, constants) {
  const file = model.quants[quant]
  if (!file || file.bytes == null) return null
  const n = device.kind === 'unified' ? 1 : cards
  const ctx = effectiveContext(model.cache, tokens)
  const cache = cacheBytes(model.cache, ctx.tokens, constants.kv_cache_bytes[cacheType], constants.window_extra_tokens)
  const overhead = constants.runtime_overhead_gib * GIB * (constants.overhead_per_card ? n : 1)
  const budget = budgetBytes(device, n)
  const floor = file.bytes + overhead
  const upperBound = !!(model.cache && model.cache.basis === 'upper_bound')
  let group
  if (floor > budget) group = 'wont' // certain whatever the cache is
  else if (cache == null) group = 'unknown'
  else {
    const need = floor + cache
    if (need <= constants.fits_at_most * budget) group = 'fits'
    else if (need <= budget) group = 'tight'
    else group = upperBound ? 'unknown' : 'wont' // a bound over budget proves nothing
  }
  return {
    fileBytes: file.bytes,
    group,
    context: ctx,
    cacheKnown: cache != null,
    upperBound,
  }
}

/**
 * GiB, to two decimals under 10, one under 100, whole above. GiB and not "GB"
 * because both sides use it: a GPU maker's "8 GB" is 8 GiB, while Hugging Face
 * prints file sizes in decimal GB (Qwen3 8B Q4_K_M: "5.03 GB" there, 4.68 GiB
 * here). Labelling GiB as GB would make our size disagree with theirs.
 */
export function fmtGiB(bytes) {
  if (bytes == null) return '—'
  const g = bytes / GIB
  return `${g < 10 ? g.toFixed(2) : g < 100 ? g.toFixed(1) : Math.round(g)} GiB`
}
