// Render real board views over a fixed fixture and print each page's heading
// outline, for tests/test_board_headings_are_real.py (SEO item 4).
// Usage: node tests/js/board_headings.mjs  ->  JSON on stdout
import { setBoardData } from '../../web/src/board/db.js'
import * as V from '../../web/src/board/views.js'

const item = (slug, about, models = ['acme/m-1', 'acme/m-2']) => ({ slug, name: slug.replace(/-/g, ' '), definition: `Definition of ${slug}.`, about,
  reports: 4, voices: 3, quotes: [], figures: [], suppressed_models: [], unit: '%', spelled_also: [],
  models: models.map((m, i) => ({ model_version_id: m, model_label: m.split('/')[1], reports: 2, voices: 2, group: i ? 'neutral' : 'working', polarities: ['positive', 'positive'] })) })
setBoardData({ jobs: [item('code-review', 'About code review.'), item('data-extraction', null)],
  caps: [item('tool-use', 'About tool use.'), item('long-context', null)],
  mets: [item('cost-per-token'), item('latency')], metrics_withheld: {}, parent_coverage: {}, posts: [] })
const pages = { boardBest: V.vBoard('best'), job1: V.vJob('code-review'), job2: V.vJob('data-extraction'),
  cap1: V.vCap('tool-use'), cap2: V.vCap('long-context'), met1: V.vMet('cost-per-token'), met2: V.vMet('latency'),
  jobModel: V.vJobModel('code-review', 'acme/m-1'), capModel: V.vCapModel('tool-use', 'acme/m-1'), metModel: V.vMetModel('cost-per-token', 'acme/m-1') }
const strip = (h) => h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
const out = {}
for (const [k, h] of Object.entries(pages)) {
  out[k] = {
    levels: [...h.matchAll(/<h([1-6])\b/g)].map((m) => +m[1]),
    h1: strip((h.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/) || ['', ''])[1]),
    roleHeading: (h.match(/role="heading"/g) || []).length,
  }
}
process.stdout.write(JSON.stringify(out))
