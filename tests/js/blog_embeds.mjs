// Render one post through the real `vPost`, for tests/test_blog_embed_mode.py:
// a credited quote, a Reddit embed, an X embed, and two embeds whose URLs are
// not the expected shape (they must draw nothing). No DOM, no network.
import { DB } from '../../web/src/board/db.js'
import { vPost } from '../../web/src/board/views.js'

DB.posts = [{
  slug: 'embeds', title: 'Embeds probe', kicker: 'Field report', tags: [], decisions: [],
  lead: 'Short answer.', meta: [], provenance: {},
  sources: [{ n: 1, platform: 'dev.to', who: 'someone', what: 'A write-up', url: 'https://dev.to/someone/a-write-up-1abc', posted: '2026-09-01' }],
  cite: { 'the part a keyword search cannot do': 1 },
  body: [
    ['h2', { text: 'First section', num: '01', id: 'first' }],
    ['p', 'One engineer said «the part a keyword search cannot do» and moved on.'],
    ['quote', 'the part a keyword search cannot do'],
    ['embed', { platform: 'reddit', url: 'https://www.reddit.com/r/LocalLLaMA/comments/1abcde/some_title/',
                title: 'Some title', author: 'someone_else', community: 'LocalLLaMA', caption: 'A Reddit thread on the topic.' }],
    ['embed', { platform: 'x', url: 'https://x.com/someone/status/1234567890', caption: 'An X post on the topic.' }],
    ['embed', { platform: 'reddit', url: 'https://evil.example/r/x/comments/1/', title: 'EVIL REDDIT', caption: 'x' }],
    ['embed', { platform: 'x', url: 'javascript:alert(1)', caption: 'EVIL X' }],
  ],
}]

const html = vPost('embeds')
process.stdout.write(JSON.stringify({ html }))
