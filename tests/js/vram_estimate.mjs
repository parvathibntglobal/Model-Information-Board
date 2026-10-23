// Runs web/src/vram/estimate.js on fixed inputs and prints the results as JSON,
// for tests/test_local_models.py. No DOM, no network.
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const v = await import(pathToFileURL(resolve('web/src/vram/estimate.js')).href)
const GIB = 2 ** 30
const constants = {
  kv_cache_bytes: { f16: 2, q8_0: 1.0625 }, window_extra_tokens: 512, runtime_overhead_gib: 1, overhead_per_card: true,
  fits_at_most: 0.85,
}
// Llama 3.1 8B: 4.58 GiB file, 65,536 cache elements per token, 128K max context.
const llamaCache = { basis: 'exact', full_elements: 65536, windowed: [], fixed_bytes: 0, max_context: 131072 }
const llama = { quants: { Q4_K_M: { bytes: 4.58 * GIB } }, cache: llamaCache }
const bounded = { quants: { Q4_K_M: { bytes: 4.58 * GIB } }, cache: { ...llamaCache, basis: 'upper_bound' } }
const gemmaCache = { basis: 'exact', full_elements: 8192, windowed: [{ window: 1024, elements: 163840 }], fixed_bytes: 0, max_context: 131072 }
const hybridCache = { basis: 'exact', full_elements: 32768, windowed: [], fixed_bytes: 156893184, max_context: 262144 }
const unknownCache = { basis: 'unknown', full_elements: null, windowed: [], fixed_bytes: null, max_context: null }
const unknown = { quants: { Q4_K_M: { bytes: 2 * GIB } }, cache: unknownCache }
const unknownBig = { quants: { Q4_K_M: { bytes: 9 * GIB } }, cache: unknownCache }
const missing = { quants: { Q4_K_M: { bytes: null } }, cache: llamaCache }
const small = { quants: { Q4_K_M: { bytes: 4 * GIB } }, cache: { ...llamaCache, max_context: 4096 } }

const card = (gib) => ({ kind: 'discrete', memory_gib: gib })
const mac = (gib, share) => ({ kind: 'unified', memory_gib: gib, gpu_share: share })
const at = (m, opts) => v.estimate(m, { quant: 'Q4_K_M', tokens: 8192, cacheType: 'f16', cards: 1, ...opts }, constants)

console.log(JSON.stringify({
  // need = 4.58 file + 1 cache + 1 runtime = 6.58 GiB
  llama8gb: at(llama, { device: card(8) }),
  llama7_5gb: at(llama, { device: card(7.5) }),
  llama6gb: at(llama, { device: card(6) }),
  llamaTwoSmallCards: at(llama, { device: card(4), cards: 2 }),
  llamaMac8: at(llama, { device: mac(8, 0.66) }),
  llamaMac16: at(llama, { device: mac(16, 0.66), cards: 3 }),
  boundOver: at(bounded, { device: card(6) }),   // floor 5.58 fits, the bound 6.58 does not
  boundFits: at(bounded, { device: card(12) }),
  exactOver: at(llama, { device: card(6) }),
  unknown8gb: at(unknown, { device: card(8) }),
  unknownTooBig: at(unknownBig, { device: card(8) }),
  missing: at(missing, { device: card(8) }),
  capped: at(small, { device: card(8), tokens: 131072 }),
  cache: {
    llama8k: v.cacheBytes(llamaCache, 8192, 2, 512),
    llama8kQ8: v.cacheBytes(llamaCache, 8192, 1.0625, 512),
    gemma32k: v.cacheBytes(gemmaCache, 32768, 2, 512),
    hybrid8k: v.cacheBytes(hybridCache, 8192, 2, 512),
    unknown: v.cacheBytes(unknownCache, 8192, 2, 512),
    noWindowExtra: (() => { try { v.cacheBytes(llamaCache, 8192, 2); return 'returned' } catch { return 'throws' } })(),
  },
  budget: {
    twoCards: v.budgetBytes(card(24), 2),
    mac16: v.budgetBytes(mac(16, 0.66), 3),
  },
  fmt: [v.fmtGiB(4.68 * GIB), v.fmtGiB(15.33 * GIB), v.fmtGiB(111.39 * GIB), v.fmtGiB(null)],
}))
