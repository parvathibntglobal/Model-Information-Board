// Render real board views and list every link-like element: its tag, href and
// data-go. For tests/test_board_links_are_real_links.py (SEO item 3).
//
// Usage: node tests/js/board_links.mjs <payload.json> -> JSON on stdout
import fs from 'node:fs'
import { setBoardData } from '../../web/src/board/db.js'
import { vBoard, vCap, vMet, vCapModel } from '../../web/src/board/views.js'
import { goPath } from '../../web/src/board/links.js'

setBoardData(JSON.parse(fs.readFileSync(process.argv[2], 'utf8')))

const TAG = /<([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>/g
const unattr = (s) => s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<')
  .replace(/&gt;/g, '>').replace(/&amp;/g, '&')

function links(html) {
  const out = []
  for (const [, tag, attrs] of html.matchAll(TAG)) {
    const go = /\bdata-go="([^"]*)"/.exec(attrs)
    if (!go) continue
    const href = /\bhref="([^"]*)"/.exec(attrs)
    const cls = (/\bclass="([^"]*)"/.exec(attrs) || [, ''])[1]
    out.push({ tag, cls, go: unattr(go[1]), href: href ? unattr(href[1]) : null, expected: goPath(unattr(go[1])) })
  }
  return out
}

const views = {
  hubBest: vBoard('best'),
  hubCap: vBoard('cap'),
  hubMet: vBoard('met'),
  cap: vCap(process.argv[3]),
  met: vMet(process.argv[4]),
  capModel: vCapModel(process.argv[3], process.argv[5]),
}
process.stdout.write(JSON.stringify(Object.fromEntries(Object.entries(views).map(([k, h]) => [k, links(h)]))))
