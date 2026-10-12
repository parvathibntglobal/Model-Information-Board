// Runs web/src/finder/finder.js on fixed inputs and prints JSON, for
// tests/test_model_finder.py. No DOM, no network.
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const f = await import(pathToFileURL(resolve('web/src/finder/finder.js')).href)

const models = [
  { model_version_id: 'a', display_name: 'Alpha', provider: 'p', supports_tools: true, supports_vision: true,
    supports_caching: true, advertised_context: 200_000, price_in: 3, price_out: 15, board: { entries: 12 } },
  { model_version_id: 'b', display_name: 'Bravo', provider: 'p', supports_tools: false, supports_vision: true,
    supports_caching: null, advertised_context: 128_000, price_in: 0.5, price_out: 2, board: { entries: 0 } },
  { model_version_id: 'c', display_name: 'Charlie', provider: 'q', supports_tools: null, supports_vision: null,
    supports_caching: null, advertised_context: null, price_in: null, price_out: null, board: { entries: 3 } },
  { model_version_id: 'd', display_name: 'Delta', provider: 'q', supports_tools: true, supports_vision: false,
    supports_caching: true, advertised_context: 1_000_000, price_in: 1, price_out: 4 },
]
const names = (r) => ({ match: r.match.map((x) => x.m.display_name), unknown: r.unknown.map((x) => [x.m.display_name, x.unknown]), out: r.out, outBy: r.outBy })

process.stdout.write(JSON.stringify({
  none: names(f.findModels(models)),
  tools: names(f.findModels(models, { need: ['supports_tools'] })),
  toolsCaching: names(f.findModels(models, { need: ['supports_tools', 'supports_caching'] })),
  ctx: names(f.findModels(models, { minContext: 200_000 })),
  cheap: names(f.findModels(models, { maxIn: 1 })),
  reported: names(f.findModels(models, { reportedOnly: true })),
  byPrice: f.findModels(models, { sort: 'price' }).match.map((x) => x.m.display_name),
  byContext: f.findModels(models, { sort: 'context' }).match.map((x) => x.m.display_name),
  query: names(f.findModels(models, { query: 'del', need: ['supports_vision'] })),
}))
