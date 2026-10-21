// Render blog posts the way a browser does and list every link in them, plus
// the name module's FAMILY_WORDS. For tests/test_blog_model_links.py.
//
// Usage: node tests/js/blog_model_links.mjs <fixture.json> -> JSON on stdout
//   fixture: { posts: [...], models: [...], catalog_ids: [...] | null }
import fs from 'node:fs'
import { DB } from '../../web/src/board/db.js'
import { vPost } from '../../web/src/board/views.js'
import { FAMILY_WORDS } from '../../web/src/board/modelnames.js'

const fx = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
DB.posts = fx.posts
DB.blogModels = fx.models
DB.blogCatalogIds = fx.catalog_ids ? new Set(fx.catalog_ids) : undefined

const unattr = (s) => s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&')
const posts = {}
for (const p of fx.posts) {
  const html = vPost(p.slug)
  const links = [...html.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)].map(([, attrs, inner]) => ({
    cls: (/\bclass="([^"]*)"/.exec(attrs) || [, ''])[1],
    href: unattr((/\bhref="([^"]*)"/.exec(attrs) || [, ''])[1]),
    text: inner.replace(/<span class="es-pop"[\s\S]*$/, '').replace(/<[^>]+>/g, ''),
  }))
  const cards = [...html.matchAll(/<span class="es-ent( off)?" tabindex="0">([^<]*)/g)].map((m) => m[2])
  posts[p.slug] = { links, cards }
}
process.stdout.write(JSON.stringify({ family_words: [...FAMILY_WORDS].sort(), posts }))
