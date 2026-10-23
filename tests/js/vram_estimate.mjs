// Runs web/src/vram/estimate.js on fixed inputs and prints the results as JSON,
// for tests/test_local_models.py. No DOM, no network.
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const v = await import(pathToFileURL(resolve('web/src/vram/estimate.js')).href)
const GIB = 2 ** 30
const constants = {
  kv_cache_bytes: { f16: 2, q8_0: 1.0625 }, runtime_overhead_gib: 1, overhead_per_card: true,
  apple_gpu_share: 0.75, fits_at_most: 0.85,
}
// Llama 3.1 8B: 4.58 GiB file, 65,536 cache elements per token, 128K max context.
const llama = {
  quants: { Q4_K_M: { bytes: 4.58 * GIB } },
  cache: { basis: 'exact', full_elements: 65536, windowed: [], max_context: 131072 },
}
const gemma = {
  quants: { Q4_K_M: { bytes: 6.63 * GIB } },
  cache: { basis: 'exact', full_elements: 8192, windowed: [{ window: 1024, elements: 163840 }], max_context: 131072 },
}
const unknown = { quants: { Q4_K_M: { bytes: 2 * GIB } }, cache: { basis: 'unknown', full_elements: null, windowed: [], max_context: null } }
const missing = { quants: { Q4_K_M: { bytes: null } }, cache: llama.cache }
const small = { quants: { Q4_K_M: { bytes: 4 * GIB } }, cache: { ...llama.cache, max_context: 4096 } }

const card = (gib) => ({ kind: 'discrete', memory_gib: gib })
const mac = (gib) => ({ kind: 'unified', memory_gib: gib })
const at = (m, opts) => v.estimate(m, { quant: 'Q4_K_M', tokens: 8192, cacheType: 'f16', cards: 1, ...opts }, constants)

console.log(JSON.stringify({
  llama8gb: at(llama, { device: card(8) }),
  llama6gb: at(llama, { device: card(6) }),
  llama12gb: at(llama, { device: card(12) }),
  llama7_5gb: at(llama, { device: card(7.5) }),
  llamaQ8cache: at(llama, { device: card(8), cacheType: 'q8_0' }),
  llamaTwoCards: at(llama, { device: card(4), cards: 2 }),
  llamaMac8: at(llama, { device: mac(8) }),
  llamaMacIgnoresCards: at(llama, { device: mac(16), cards: 3 }),
  gemma32k: at(gemma, { device: card(12), tokens: 32768 }),
  unknown: at(unknown, { device: card(8) }),
  missing: at(missing, { device: card(8) }),
  capped: at(small, { device: card(8), tokens: 131072 }),
  fmt: [v.fmtGiB(4.68 * GIB), v.fmtGiB(15.33 * GIB), v.fmtGiB(111.39 * GIB), v.fmtGiB(null)],
}))
