// Runs web/src/seo/pages.js on a fixed set of inputs and prints the results as
// JSON, for tests/test_seo_head_text.py. No DOM, no network.
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const pages = await import(pathToFileURL(resolve('web/src/seo/pages.js')).href)
const sd = await import(pathToFileURL(resolve('web/src/seo/structured.js')).href)

const job = { slug: 'code-review', name: 'Code review', card: 'Reviewing diffs for bugs, style and risk before merge.' }
const leaky = { slug: 'x', name: 'Agents', card: 'Threads on Reddit and arXiv about agent loops.' }
const long = { slug: 'y', name: 'Very long section name that keeps going', card: 'word '.repeat(80) }

const out = {
  hub: pages.boardHub('cap'),
  hubDefault: pages.boardHub(undefined),
  job: pages.boardSection('jobs', job),
  cap: pages.boardSection('capabilities', job),
  met: pages.boardSection('metrics', { ...job, name: 'Cost per token' }),
  leaky: pages.boardSection('capabilities', leaky),
  long: pages.boardSection('capabilities', long),
  unknownSeg: pages.boardSection('nope', job),
  inSection: pages.boardModelInSection('jobs', job, 'anthropic/claude-opus-5', 'Claude Opus 5'),
  model: pages.modelPage('anthropic/claude-opus-5', 'Claude Opus 5'),
  compareAB: pages.comparePage(['b', 'a'], ['Model B', 'Model A']),
  compareBA: pages.comparePage(['a', 'b'], ['Model A', 'Model B']),
  compareOne: pages.comparePage(['a'], []),
  post: pages.blogPost({ slug: 's', title: 'Moving to a new model', dek: 'A short dek.' }),
  postNoDek: pages.blogPost({ slug: 's', title: 'T' }),
  postMissing: pages.blogPost(undefined),
  tokenCounter: pages.tokenCounter(),
  modelFinder: pages.modelFinder(),
  login: pages.PRIVATE.login,
  notFound: pages.PRIVATE.notFound,
  longTitle: pages.fullTitle('A model name long enough that the site name cannot also fit'),
  noindex: {
    unknownList: pages.noindexFor({ canonical: '/board' }, null),
    onList: pages.noindexFor({ canonical: '/board' }, new Set(['/board'])),
    offList: pages.noindexFor({ canonical: '/board/jobs/x' }, new Set(['/board'])),
    askedFor: pages.noindexFor({ canonical: '/board', noindex: true }, new Set(['/board'])),
    noCanonical: pages.noindexFor({ title: 't' }, null),
    noHead: pages.noindexFor(null, null),
  },
  structured: (() => {
    const site = 'https://board.example'
    const head = pages.boardModelInSection('jobs', job, 'anthropic/claude-opus-5', 'Claude Opus 5')
    const full = { slug: 's', title: 'T'.repeat(130), dek: 'A dek.', published_at: '2026-10-07T12:34:23+05:30',
      provenance: { generated_at: '2026-10-01T06:39:45+00:00' } }
    return {
      crumbs: sd.breadcrumbList(site, head.breadcrumbs),
      crumbsClosed: sd.breadcrumbList('', head.breadcrumbs),
      crumbsTooShort: sd.breadcrumbList(site, [{ name: 'Only', path: '/' }]),
      article: sd.article(site, full),
      articleBare: sd.article(site, { slug: 's', title: 'T' }),
      closedAll: sd.structuredFor('', pages.blogPost(full)),
      openPost: sd.structuredFor(site, pages.blogPost(full)).map((x) => x['@type']),
      postArticle: pages.blogPost(full).article,
      sectionCrumbs: pages.boardSection('capabilities', job).breadcrumbs,
      modelCrumbs: pages.modelPage('anthropic/claude-opus-5', 'Claude Opus 5').breadcrumbs,
    }
  })(),
  TITLE_MAX: pages.TITLE_MAX,
  DESCRIPTION_MAX: pages.DESCRIPTION_MAX,
}
process.stdout.write(JSON.stringify(out))
