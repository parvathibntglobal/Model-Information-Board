import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { readPaths, robotsTxt, siteOf, sitemapXml } from './seo-build.js'

// The backend runs no CORS middleware, so in dev we proxy rather than ask them
// to add one. Everything the app fetches is under /api, which is stripped here.
const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

/** The repo root, where the ONE .env lives. */
const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url))


/**
 * robots.txt, sitemap.xml and the canonical link, written at build time.
 *
 * THE SITE HAS NO ADDRESS YET, so nothing here guesses one. A canonical link,
 * an og:url and every sitemap entry must be absolute URLs; with SITE_URL unset
 * the build writes robots.txt without a Sitemap line, writes no sitemap.xml,
 * and adds no canonical - better absent than pointing at a made-up domain.
 *
 * CLOSED BY DEFAULT (review of #508, item 3): indexing opens only when BOTH
 * `SITE_URL` is set and `PUBLIC_SITE=1`. The rules themselves live in
 * ./seo-build.js so they can be tested without a build.
 *
 * THE SITEMAP LISTS THE PAGES WORTH INDEXING (SEO item 8, 2026-10-09), not
 * only the six structural ones: `SEO_PATHS_FILE` names the JSON that
 * `scripts/export_indexable_paths.py` writes from judge/seo.py, the same list
 * that decides each page's `noindex`. An OPEN build without it FAILS rather
 * than shipping a six-page sitemap that looks complete (rule 12). A closed
 * build never reads it.
 */
function seoFiles(siteUrl, publicSite, pathsFile) {
  const { site, open } = siteOf(siteUrl, publicSite)
  let paths = []
  if (open) {
    if (!pathsFile) {
      throw new Error('PUBLIC_SITE=1 needs SEO_PATHS_FILE: run scripts/export_indexable_paths.py '
        + 'and point SEO_PATHS_FILE at its output, or the sitemap would list only the structural pages.')
    }
    const file = resolve(REPO_ROOT, pathsFile)
    paths = readPaths(readFileSync(file, 'utf8'), file).paths
  }
  return {
    name: 'seo-files',
    transformIndexHtml(html) {
      if (!open) return html
      html = html.replace('content="noindex, nofollow"', 'content="index, follow"')
      return html.replace('</title>', `</title>
    <link rel="canonical" href="${site}/" />
    <meta property="og:url" content="${site}/" />`)
    },
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: 'robots.txt', source: robotsTxt({ site, open }) })
      if (!open) return
      this.emitFile({ type: 'asset', fileName: 'sitemap.xml', source: sitemapXml(site, paths) })
    },
  }
}

export default defineConfig(({ mode }) => {
  // ONE .env FOR THE WHOLE PROJECT, at the repo root.
  //
  // Vite would normally read `web/.env`, which meant the API token had to be
  // written twice — once as API_TOKEN for the backend and once as
  // VITE_API_TOKEN here. Two copies of one secret is two things to rotate and
  // one to forget, so this reads the root file instead.
  //
  // The empty prefix is what makes that possible: `loadEnv(mode, dir, '')`
  // returns EVERY variable, not just VITE_-prefixed ones, so `API_TOKEN` is
  // visible. That is also why exactly one value is injected below and the
  // object is never spread — `env` here holds DATABASE_URL and
  // OPENROUTER_API_KEY too, and `define` puts whatever it is given into the
  // browser bundle in clear text.
  const env = loadEnv(mode, REPO_ROOT, '')
  const token = env.API_TOKEN || process.env.API_TOKEN || ''
  const siteUrl = env.SITE_URL || process.env.SITE_URL
  const publicSite = env.PUBLIC_SITE || process.env.PUBLIC_SITE
  // ONE SWITCH FOR EVERY CANONICAL. web/src/seo/head.js writes each page's
  // canonical from this - set only when the site is OPEN, from the same two
  // keys as robots.txt and the sitemap. (Item 1 first read a separate
  // VITE_SITE_URL: two names for one address is how they drift apart.)
  const { site: canonicalSite, open: siteOpen } = siteOf(siteUrl, publicSite)

  return {
    plugins: [react(), seoFiles(siteUrl, publicSite, env.SEO_PATHS_FILE || process.env.SEO_PATHS_FILE),
      ...(process.env.SINGLE_FILE ? [viteSingleFile()] : [])],

    // NOT A SECRET ONCE IT IS HERE. Anything `define` injects is readable by
    // anyone who loads the page — view-source, devtools, the built bundle. This
    // is a development convenience so the dev server can reach a token-gated
    // API; a deployed build must get its credential from a session the server
    // issues, never from a value compiled into the client.
    define: {
      'import.meta.env.VITE_API_TOKEN': JSON.stringify(token),
      'import.meta.env.VITE_SITE_URL': JSON.stringify(siteOpen ? canonicalSite : ''),
    },

    server: {
      proxy: {
        '/api': {
          target: BACKEND,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
        },
      },
    },
    build: process.env.SINGLE_FILE
      ? { assetsInlineLimit: 100_000_000, cssCodeSplit: false, outDir: 'dist-single' }
      : {},
  }
})
