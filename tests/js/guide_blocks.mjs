// Render one guide post through the real `vPost`, and classify posts with the
// real guideKinds.js, for tests/test_guide_packs.py (Guides phase B,
// 2026-10-30). The post - its body built by judge/guide_blocks.py's builders
// - arrives as a JSON file named on the command line. No DOM, no network.
import { readFileSync } from 'node:fs'
import { DB } from '../../web/src/board/db.js'
import { vPost } from '../../web/src/board/views.js'
import { GUIDE_FORMATS, isGuide, isMigrationGuide, isOfficialGuide, tabOf } from '../../web/src/blogs/guideKinds.js'

const post = JSON.parse(readFileSync(process.argv[2], 'utf-8'))
DB.posts = [post]
const html = vPost(post.slug)

const kinds = {}
for (const f of ['migration-guide', 'developer-guide', 'tutorial', 'error-fix', 'field-report', 'topic-synthesis', '']) {
  const p = { provenance: { plan_key: f ? `${f}:x` : null } }
  kinds[f || '(none)'] = { guide: isGuide(p), migration: isMigrationGuide(p), official: isOfficialGuide(p), tab: tabOf(p) }
}
process.stdout.write(JSON.stringify({ html, kinds, formats: GUIDE_FORMATS }))
