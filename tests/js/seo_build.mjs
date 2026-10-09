// Run web/seo-build.js (robots.txt and sitemap.xml rules) on fixed inputs and
// print the results as JSON, for tests/test_seo_build_files.py. No build, no DOM.
import { readPaths, robotsTxt, siteOf, sitemapXml, STRUCTURAL_PATHS } from '../../web/seo-build.js'

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
  sitemap: sitemapXml(site, ['/board/jobs/code-review', '/board', '/compare', '/admin', '/login',
    '/models/anthropic/claude-opus-4.6', '/board?tab=cap&x=1', 'not-a-path']),
  structural: STRUCTURAL_PATHS,
  readPaths: {
    good: tryRead(JSON.stringify({ generated_at: '2026-10-09T00:00:00Z', paths: ['/'] })),
    noDate: tryRead(JSON.stringify({ paths: ['/'] })),
    noPaths: tryRead(JSON.stringify({ generated_at: 'x' })),
    notJson: tryRead('{nope'),
  },
}))
