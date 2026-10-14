// Render one post through the real `vPost`, for tests/test_blog_visuals.py.
// The post carries an old {text, skim} paragraph, a plain one, and one of each
// visual kind. No DOM, no network.
import { DB } from '../../web/src/board/db.js'
import { vPost } from '../../web/src/board/views.js'

DB.posts = [{
  slug: 'probe', title: 'Probe post', kicker: 'Field report', tags: [], decisions: [],
  lead: 'Short answer.', meta: [], provenance: {},
  body: [
    ['h2', { text: 'First section', num: '01', id: 'first' }],
    ['p', { text: 'FULL PARAGRAPH TEXT stays visible.', skim: 'SKIM LINE should never show.' }],
    ['p', 'A plain paragraph. Its second sentence must render too.'],
    ['visual', { kind: 'table', caption: 'Two models side by side.',
                 columns: ['Model', 'Context'], rows: [['Alpha', '1,048,576'], ['Beta', '204,800']] }],
    ['h2', { text: 'Second section', num: '02', id: 'second' }],
    ['visual', { kind: 'chart', caption: 'List input price.', unit: 'USD per 1M input tokens',
                 bars: [{ label: 'Alpha', value: 0.042 }, { label: 'Beta', value: 0.6 }] }],
    ['image', { src: 'data:image/jpeg;base64,/9j/AAAA', alt: 'Requests queueing at one gate', caption: 'One provider holds the line.' }],
    ['image', { src: 'https://evil.example/x.png', alt: 'should not draw', caption: 'REMOTE IMAGE' }],
    ['visual', { kind: 'diagram', caption: 'The request path.',
                 steps: ['Client sends the prompt', 'Router picks a provider', 'Provider answers'] }],
  ],
}]

const html = vPost('probe')
process.stdout.write(JSON.stringify({
  html,
  hasToggle: /m-skim|name="es-mode"/.test(html),
  readTime: (/(\d+) min read/.exec(html) || [])[1] || null,
}))
