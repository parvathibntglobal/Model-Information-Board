import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'
import react from '@vitejs/plugin-react'

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
 * Set SITE_URL (in the repo .env or the environment) once the board has one.
 *
 * The sitemap lists the pages that exist for anyone: the landing, the board
 * and its three tabs, models and blogs. Admin and sign-in are kept out of it
 * and disallowed in robots.txt.
 */
const SITEMAP_PATHS = ['/', '/board', '/board?tab=cap', '/board?tab=met', '/models', '/blogs']

function seoFiles(siteUrl) {
  const site = (siteUrl || '').trim().replace(/\/+$/, '')
  const esc = (u) => u.replace(/&/g, '&amp;')
  return {
    name: 'seo-files',
    transformIndexHtml(html) {
      if (!site) return html
      return html.replace('</title>', `</title>
    <link rel="canonical" href="${site}/" />
    <meta property="og:url" content="${site}/" />`)
    },
    generateBundle() {
      const robots = ['User-agent: *', 'Allow: /', 'Disallow: /admin', 'Disallow: /login']
      if (site) robots.push('', `Sitemap: ${site}/sitemap.xml`)
      this.emitFile({ type: 'asset', fileName: 'robots.txt', source: robots.join('\n') + '\n' })
      if (!site) return
      const urls = SITEMAP_PATHS.map((p) => `  <url><loc>${esc(site + p)}</loc></url>`).join('\n')
      this.emitFile({
        type: 'asset',
        fileName: 'sitemap.xml',
        source: `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`,
      })
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

  return {
    plugins: [react(), seoFiles(env.SITE_URL || process.env.SITE_URL),
      ...(process.env.SINGLE_FILE ? [viteSingleFile()] : [])],

    // NOT A SECRET ONCE IT IS HERE. Anything `define` injects is readable by
    // anyone who loads the page — view-source, devtools, the built bundle. This
    // is a development convenience so the dev server can reach a token-gated
    // API; a deployed build must get its credential from a session the server
    // issues, never from a value compiled into the client.
    define: {
      'import.meta.env.VITE_API_TOKEN': JSON.stringify(token),
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
