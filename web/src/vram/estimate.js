/**
 * THE LOCAL VRAM TOOL'S ARITHMETIC (docs/proposals/can-i-run-it.md).
 *
 * Every constant comes from GET /local-models, which reads contract/ - this file
 * has none of its own (rules 5 and 12). The FIGURE a row shows is the measured
 * file size; what is computed here is the estimate that decides the group,
 * which the page labels as one (rule 3).
 *
 *   weights   the measured GGUF file size (the sum of its parts)
 *   cache     bytes per element x (full elements x tokens
 *             + windowed elements x min(tokens, window))
 *   total     weights + cache + runtime overhead (once per card when split)
 *   budget    memory x cards (a graphics card) | memory x Mac GPU share (a Mac)
 *   group     fits | tight | wont
 */

export const GIB = 2 ** 30

/** The context the model can take: the reader's pick, capped at the model's own maximum. */
export function effectiveContext(cache, tokens) {
  const max = cache && cache.max_context
  return max && max < tokens ? { tokens: max, capped: true } : { tokens, capped: false }
}

/** Bytes the KV cache takes, or null when the header did not let us know (rule 6). */
export function cacheBytes(cache, tokens, bytesPerElement) {
  if (!cache || cache.basis === 'unknown' || cache.full_elements == null) return null
  const windowed = (cache.windowed || []).reduce((s, w) => s + w.elements * Math.min(tokens, w.window), 0)
  return bytesPerElement * (cache.full_elements * tokens + windowed)
}

/** The memory a model may use on this hardware. */
export function budgetBytes(device, cards, constants) {
  if (device.kind === 'unified') return device.memory_gib * GIB * constants.apple_gpu_share
  return device.memory_gib * GIB * cards
}

/**
 * One model on one hardware choice. `null` when the model has no measured size
 * for this quantization - never a guessed one.
 */
export function estimate(model, { quant, tokens, cacheType, device, cards }, constants) {
  const file = model.quants[quant]
  if (!file || file.bytes == null) return null
  const n = device.kind === 'unified' ? 1 : cards
  const ctx = effectiveContext(model.cache, tokens)
  const cache = cacheBytes(model.cache, ctx.tokens, constants.kv_cache_bytes[cacheType])
  const overhead = constants.runtime_overhead_gib * GIB * (constants.overhead_per_card ? n : 1)
  const total = file.bytes + (cache || 0) + overhead
  const budget = budgetBytes(device, n, constants)
  const group = total <= constants.fits_at_most * budget ? 'fits' : total <= budget ? 'tight' : 'wont'
  return {
    fileBytes: file.bytes,
    cacheBytes: cache,
    overheadBytes: overhead,
    total,
    budget,
    group,
    context: ctx,
    upperBound: model.cache && model.cache.basis === 'upper_bound',
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
