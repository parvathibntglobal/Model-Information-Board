// Runs web/src/tokens/cost.js on fixed inputs and prints JSON, for
// tests/test_token_counter.py. No tokenizer, no DOM, no network.
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const c = await import(pathToFileURL(resolve('web/src/tokens/cost.js')).href)

// A stand-in for the library's model map: knows gpt-4o, throws-as-null otherwise.
const encodingNameFor = (name) => ({ 'gpt-4o': 'o200k_base', 'gpt-4': 'cl100k_base' })[name] ?? null

const models = [
  { model_version_id: 'mv_1', canonical_id: 'openai/gpt-4o', display_name: 'GPT-4o', provider: 'openai', price_in: 2.5, price_out: 10, price_cached_read: 1.25, advertised_context: 100, max_output_tokens: 40 },
  { model_version_id: 'mv_2', canonical_id: 'openai/gpt-4', display_name: 'GPT-4', provider: 'openai', price_in: 30, price_out: 60 },
  { model_version_id: 'mv_3', canonical_id: 'openai/gpt-9', display_name: 'GPT-9', provider: 'openai', price_in: 1, price_out: 4 },
  { model_version_id: 'mv_4', canonical_id: 'anthropic/claude-x', display_name: 'Claude X', provider: 'anthropic', price_in: 3, price_out: null },
  { model_version_id: 'mv_5', canonical_id: 'openrouter/auto', display_name: 'Auto Router', provider: 'openrouter', price_in: null, price_out: null },
  { model_version_id: 'mv_6', canonical_id: 'free/model', display_name: 'Free Model', provider: 'free', price_in: 0, price_out: 0 },
  { model_version_id: 'mv_7', canonical_id: 'mirror/gpt-4o', display_name: 'Mirror 4o', provider: 'mirror', price_in: 2, price_out: 8 },
]

const opts = { tokens: 51, calls: 1000, encodingNameFor }
const pick = (r) => ({ ...r })

process.stdout.write(JSON.stringify({
  costOf: {
    basic: c.costOf(51, 10, 1000),
    one: c.costOf(51, 10),
    nullRate: c.costOf(51, null, 1),
    nullTokens: c.costOf(null, 10, 1),
    freeRate: c.costOf(51, 0, 1000),
  },
  fmtUsd: {
    nul: c.fmtUsd(null), zero: c.fmtUsd(0), tiny: c.fmtUsd(1e-9), small: c.fmtUsd(0.00051),
    sub: c.fmtUsd(0.51), big: c.fmtUsd(1234.5),
  },
  words: [c.countWords(''), c.countWords('  two words \n three'), c.countLines(''), c.countLines('a\nb')],
  input: c.priceRows(models, opts),
  output: c.priceRows(models, { ...opts, direction: 'output' }),
  byCost: c.priceRows(models, { ...opts, sort: 'cost' }).priced.map((r) => r.name),
  search: c.priceRows(models, { ...opts, query: 'gpt 4' }).priced.map((r) => r.name),
  noTokenizer: c.priceRows(models, { tokens: null, calls: 1 }).priced.map(pick),
  fit: {
    fits: c.fitOf(51, models[0], 'input'),
    over: c.fitOf(101, models[0], 'input'),
    outOver: c.fitOf(41, models[0], 'output'),
    unknown: c.fitOf(51, models[1], 'input'),
    notCounted: c.fitOf(null, models[0], 'input'),
  },
  workload: {
    plain: c.workloadCost(models[0], { inTok: 1000, outTok: 100, callsPerDay: 10 }),
    cached: c.workloadCost(models[0], { inTok: 1000, outTok: 0, callsPerDay: 1, cachedShare: 0.5 }),
    noCacheRate: c.workloadCost(models[2], { inTok: 1000, outTok: 0, cachedShare: 0.5 }),
    needsOut: c.workloadCost(models[3], { inTok: 10, outTok: 10 }),
    inOnly: c.workloadCost(models[3], { inTok: 10, outTok: 0 }),
    rows: c.workloadRows(models, { inTok: 50, outTok: 30, callsPerDay: 2, sort: 'cost' }),
  },
}))
