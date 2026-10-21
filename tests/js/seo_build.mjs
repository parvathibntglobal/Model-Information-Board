// Run web/seo-build.js (robots.txt and sitemap.xml rules) on fixed inputs and
// print the results as JSON, for tests/test_seo_build_files.py. No build, no DOM.
import { prerenderFile, prerenderPaths, readPaths, robotsTxt, shellScript, siteOf, sitemapXml, STRUCTURAL_PATHS }
  from '../../web/seo-build.js'

const site = 'https://board.example'
const tryRead = (text) => { try { readPaths(text, 'x.json'); return 'ok' } catch (e) { return e.message } }

process.stdout.write(JSON.stringify({
  sites: {
    none: siteOf('', '1'),
    urlOnly: siteOf('https://board.example/', ''),
    flagOnly: siteOf('', '1'),
    both: siteOf('https://board.example/', '1'),
  },
  robotsClosed: robotsTxt({ site: '', open: false }),
  robotsOpen: robotsTxt({ site, open: true }),
  sitemap: sitemapXml(site, ['/reviews/jobs/code-review', '/board', '/board/jobs/code-review', '/compare',
    '/admin', '/login', '/models/anthropic/claude-opus-4.6', '/seo-keywords',
    '/ai-models/anthropic/claude-opus-4.6', '/ai-models?type=text&x=1', 'not-a-path']),
  sitemapDated: sitemapXml(site, ['/reviews/jobs/code-review', '/ai-models/acme/model-t', '/blogs'], {
    '/reviews/jobs/code-review': '2026-10-06T13:00:39+05:30',
    '/ai-models/acme/model-t': 'not a date',
  }),
  structural: STRUCTURAL_PATHS,
  readPaths: {
    good: tryRead(JSON.stringify({ generated_at: '2026-10-09T00:00:00Z', paths: ['/'] })),
    noDate: tryRead(JSON.stringify({ paths: ['/'] })),
    noPaths: tryRead(JSON.stringify({ generated_at: 'x' })),
    notJson: tryRead('{nope'),
  },
  prerenderPaths: prerenderPaths(['/reviews/jobs/code-review', '/board', '/models/x/y', '/ai-models?type=text',
    '/blogs/a#top', '/ai-models/acme/model-t', '/reviews/jobs/code-review']),
  prerenderFiles: Object.fromEntries(['/', '/reviews/jobs', '/ai-models/openai/gpt-6-sol', '/glossary/gpt-5.5',
    '/a/../b', '/a%2F..%2Fb', '/x/', '/a:b', '/%E0%A4', '/a%5Cb', '/a%00b'].map((p) => [p, prerenderFile(p)])),
  shellScript: shellScript({ title: '</script><b>', robots: 'noindex' }),
}))
