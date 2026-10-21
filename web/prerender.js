/**
 * Pre-render the public pages into dist/ (SEO, 2026-10-20). Runs after
 * `vite build` as part of `npm run build`.
 *
 * WHY: the app builds every page in the browser, so a crawler or AI tool that
 * runs no JavaScript was handed index.html's empty <div id="root">. This opens
 * each public page in a headless browser, waits for its data, and saves the
 * finished HTML - title, description, canonical, structured data, headings and
 * text - as that page's file (seo-build.js `prerenderFile`).
 *
 * ALWAYS: dist/index.html is copied to dist/shell.html, the empty page nginx
 * answers for any address with no file of its own (web/nginx.conf.template).
 * Without it the home page's saved HTML would be the fallback for every route.
 *
 * ONLY WHEN THE SITE IS OPEN (SITE_URL + PUBLIC_SITE=1, the robots.txt switch)
 * or PRERENDER=1: a closed build is noindex, so nothing reads the saved pages.
 * When it runs, a page that fails to render FAILS THE BUILD - shipping some
 * pages empty and some full looks complete and is not (rule 12).
 *
 * WHERE THE DATA COMES FROM: the API the bundle was built against
 * (VITE_API_URL). The browser loads from a local server here, so a call to
 * another origin would meet CORS; every request off that origin is fetched by
 * node and handed back instead. `/api` (the dev default) is proxied to
 * PRERENDER_API, else BACKEND_URL, else 127.0.0.1:8000. Images, fonts and
 * media are not fetched: they never change the HTML.
 *
 * NO OTHER SITE IS LOADED (2026-10-21). A blog post embeds Reddit and X posts in
 * frames; fetching those made every post wait out the network-idle limit (15 s)
 * and left requests hanging into the pages after it. A frame's tag is saved
 * whatever it loads, so anything that is neither this build nor its API is
 * refused, and every fetch made here gives up after FETCH_MS.
 *
 * THE BROWSER: CHROME_PATH (the Dockerfile installs Alpine's chromium), else
 * Chrome or Edge where they normally live.
 */
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, extname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { loadEnv } from 'vite'
import puppeteer from 'puppeteer-core'
import { prerenderFile, prerenderPaths, readPaths, shellScript, siteOf } from './seo-build.js'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(HERE, '..')
const DIST = join(HERE, 'dist')
const env = { ...loadEnv('production', REPO_ROOT, ''), ...process.env }

const shellPath = join(DIST, 'index.html')
if (!existsSync(shellPath)) throw new Error('prerender: dist/index.html is missing - run vite build first')
// Pages are rendered from THIS shell, the build's own index.html. A dist/ that
// was pre-rendered already has the home page there, so it is refused rather
// than guessed at: `npm run build` writes a fresh one.
const SHELL = readFileSync(shellPath, 'utf8')
if (SHELL.includes('id="shell-head"')) {
  throw new Error('prerender: dist/ is already pre-rendered - run `npm run build` again')
}

const { open } = siteOf(env.SITE_URL, env.PUBLIC_SITE)

// THE SHELL nginx SERVES FOR EVERY OTHER ADDRESS (2026-10-21) - a mistyped one,
// a sign-in page, a comparison pair, a picker search - says `noindex` and names
// no canonical. The open build's index.html says `index` with the home page's
// canonical, so without this every unknown address read as a copy of the home
// page to a crawler that runs no script. Every page worth indexing is saved as
// a file of its own, so none of them is served this. Not the shell pages are
// RENDERED from: a noindex start would make every page noindex (head.js only
// tightens robots).
const served = open
  ? SHELL.replace(/<meta name="robots" content="[^"]*"\s*\/?>/, '<meta name="robots" content="noindex, nofollow" />')
    .replace(/\s*<link rel="canonical"[^>]*>/, '').replace(/\s*<meta property="og:url"[^>]*>/, '')
  : SHELL
writeFileSync(join(DIST, 'shell.html'), served)
if (!open && env.PRERENDER !== '1') {
  console.log('prerender: skipped - the site is closed (set PRERENDER=1 to render anyway). dist/shell.html written.')
  process.exit(0)
}

let extra = []
if (env.SEO_PATHS_FILE) {
  const file = resolve(REPO_ROOT, env.SEO_PATHS_FILE)
  extra = readPaths(readFileSync(file, 'utf8'), file).paths
}
const PATHS = prerenderPaths(extra)
const API = (env.PRERENDER_API || env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
// The API's own origin when the bundle names an absolute one (a deployed build).
const API_ORIGIN = (() => { try { return new URL(env.VITE_API_URL).origin } catch { return null } })()
const FETCH_MS = 20000

// ── a local static server for dist/, with the SPA fallback and the /api proxy ──
const TYPES = { '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
  '.txt': 'text/plain', '.xml': 'application/xml', '.woff2': 'font/woff2', '.png': 'image/png', '.ico': 'image/x-icon' }

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://local')
  if (url.pathname.startsWith('/api/')) {
    try {
      const r = await fetch(API + url.pathname.slice(4) + url.search,
        { headers: { accept: req.headers.accept || '*/*' }, signal: AbortSignal.timeout(FETCH_MS) })
      res.writeHead(r.status, { 'content-type': r.headers.get('content-type') || 'application/json' })
      res.end(Buffer.from(await r.arrayBuffer()))
    } catch (e) {
      res.writeHead(502).end(String(e.message))
    }
    return
  }
  const file = join(DIST, decodeURIComponent(url.pathname))
  if (file.startsWith(DIST) && extname(file) && existsSync(file)) {
    res.writeHead(200, { 'content-type': TYPES[extname(file)] || 'application/octet-stream' })
    res.end(readFileSync(file))
    return
  }
  // Every page is rendered from the shell, never from a page saved earlier in this run.
  res.writeHead(200, { 'content-type': 'text/html' }).end(SHELL)
})
await new Promise((ok) => server.listen(0, '127.0.0.1', ok))
const ORIGIN = `http://127.0.0.1:${server.address().port}`

const CANDIDATES = [env.CHROME_PATH, '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'].filter(Boolean)
const executablePath = CANDIDATES.find((p) => existsSync(p))
if (!executablePath) throw new Error('prerender: no browser found - set CHROME_PATH')

// THE BROWSER, TWO WAYS (2026-10-22). puppeteer's own launch is the normal
// path (the Docker image's chromium). On a desktop where that browser is
// already open, Edge 155 exits at once under puppeteer's launch (code 0), so
// the fallback starts it with a debugging port on a profile of its own and
// connects - the way a person would. Either way the same browser renders.
async function openBrowser() {
  const args = ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
  try {
    return { browser: await puppeteer.launch({ executablePath, headless: true, args }), child: null }
  } catch (first) {
    const port = 9400 + Math.floor(Math.random() * 400)
    const profile = mkdtempSync(join(tmpdir(), 'prerender-'))
    const child = spawn(executablePath, ['--headless=new', ...args, `--remote-debugging-port=${port}`,
      `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
    for (let i = 0; i < 40; i++) {
      await new Promise((ok) => setTimeout(ok, 250))
      try {
        const r = await fetch(`http://127.0.0.1:${port}/json/version`)
        if (r.ok) return { browser: await puppeteer.connect({ browserURL: `http://127.0.0.1:${port}` }), child }
      } catch { /* not up yet */ }
    }
    child.kill()
    throw new Error(`prerender: the browser would not start (${first.message.split(String.fromCharCode(10))[0]})`)
  }
}
const { browser, child: browserChild } = await openBrowser()

// What the page's head was in the shell - main.jsx puts it back before the app starts.
const shellHead = await (async () => {
  const page = await browser.newPage()
  await page.setContent(SHELL.replace(/<script[^>]*src=[^>]*><\/script>/g, ''))
  const head = await page.evaluate(() => {
    const get = (s) => document.head.querySelector(s)?.getAttribute('content') ?? null
    return { title: document.title, description: get('meta[name="description"]'), robots: get('meta[name="robots"]'),
      ogTitle: get('meta[property="og:title"]'), ogDescription: get('meta[property="og:description"]'),
      ogUrl: get('meta[property="og:url"]'),
      canonical: document.head.querySelector('link[rel="canonical"]')?.getAttribute('href') ?? null }
  })
  await page.close()
  return head
})()

async function render(page, path) {
  // THE INDEXABLE LIST DECIDES ROBOTS (web/src/seo/indexable.js): until it
  // arrives a page with a head of its own says noindex, so such a page is not
  // saved before it has. The home page keeps index.html's head and never asks.
  let asked = false
  const onRequest = (r) => { if (r.url().includes('/seo/indexable')) asked = true }
  page.on('request', onRequest)
  const indexable = page.waitForResponse((r) => r.url().includes('/seo/indexable'), { timeout: 60000 })
  indexable.catch(() => {})
  try {
    await page.goto(ORIGIN + path, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await page.waitForSelector('#root h1', { timeout: 30000 })
    // Data-driven pages fill in after the heading; wait until no loading skeleton is left.
    await page.waitForFunction(() => !document.querySelector('.skel'), { timeout: 30000 })
    await page.waitForNetworkIdle({ idleTime: 500, timeout: 15000 }).catch(() => {})
    if (asked) await indexable
  } finally {
    page.off('request', onRequest)
  }
  return page.evaluate(() => {
    const h1 = document.querySelector('#root h1')?.textContent || ''
    const notFound = document.title.startsWith('Page not found') || h1.startsWith('There is no')
    // Mark what the app wrote into the head, so main.jsx can take it out again.
    // Only the scripts the app writes (head.js `data-seo-ld`, the FAQ's
    // `data-faq`): index.html's own Organization / WebSite graph stays put.
    document.head.querySelectorAll('script[type="application/ld+json"][data-seo-ld], script[type="application/ld+json"][data-faq]')
      .forEach((el) => el.setAttribute('data-prerendered', ''))
    return { notFound, html: '<!doctype html>\n' + document.documentElement.outerHTML }
  })
}

const failed = []
let saved = 0
const t0 = Date.now()
// EVERY API READ ONCE PER RUN (2026-10-22). Each page asks for the same big
// answers - the catalogue, the reviews data, the model list, the indexable
// list - and one run is one snapshot of the API. So a GET is fetched once,
// by its full address, and every page and tab is handed that answer: the
// backend serves each address once per build instead of once per page, and a
// few tabs can then render at once. A failed fetch is not kept.
const apiOnce = new Map()
function fetchOnce(url) {
  if (!apiOnce.has(url)) {
    const p = fetch(url, { headers: { accept: 'application/json' }, signal: AbortSignal.timeout(FETCH_MS * 3) })
      .then(async (r) => ({ status: r.status, type: r.headers.get('content-type') || 'application/json',
        body: Buffer.from(await r.arrayBuffer()) }))
    p.catch(() => apiOnce.delete(url))
    apiOnce.set(url, p)
  }
  return apiOnce.get(url)
}

/** A tab with this script's request rules (see the notes at the top). */
async function openTab() {
  const page = await browser.newPage()
  await page.setRequestInterception(true)
  page.on('request', (req) => handle(req))
  return page
}

async function handle(req) {
  if (['image', 'media', 'font'].includes(req.resourceType())) return req.abort()
  const url = req.url()
  // The API: the dev default `/api` on this server, or the origin the bundle
  // names. Answered here - once per address per run, and with no CORS.
  const api = url.startsWith(`${ORIGIN}/api/`) || (API_ORIGIN && url.startsWith(API_ORIGIN))
  if (api) {
    try {
      if (req.method() === 'GET') {
        const r = await fetchOnce(url)
        return req.respond({ status: r.status, contentType: r.type,
          headers: { 'access-control-allow-origin': ORIGIN }, body: r.body })
      }
      const r = await fetch(url, { method: req.method(), headers: { accept: req.headers().accept || '*/*' },
        signal: AbortSignal.timeout(FETCH_MS), body: req.postData() })
      return req.respond({ status: r.status, contentType: r.headers.get('content-type') || 'application/json',
        headers: { 'access-control-allow-origin': ORIGIN }, body: Buffer.from(await r.arrayBuffer()) })
    } catch {
      return req.abort()
    }
  }
  if (url.startsWith(ORIGIN) || url.startsWith('data:')) return req.continue()
  // Any other site - an embedded post, a widget - is not loaded (see the note at the top).
  return req.abort()
}

async function saveOne(page, path) {
  const file = prerenderFile(path)
  const t1 = Date.now()
  if (!file) { failed.push(`${path}: not a safe file name`); return }
  try {
    // One retry: a slow API answer is not a broken page.
    const { notFound, html } = await render(page, path).catch(() => render(page, path))
    if (notFound) { failed.push(`${path}: renders "not found"`); return }
    const out = join(DIST, file)
    mkdirSync(dirname(out), { recursive: true })
    // Vite's preload links are written with the page's full address; the local one must not ship.
    const local = html.split(ORIGIN).join('')
    writeFileSync(out, local.replace('</head>', `${shellScript(shellHead)}</head>`))
    saved += 1
    if (env.PRERENDER_VERBOSE) console.log(`  ${path}  ${Date.now() - t1}ms`)
  } catch (e) {
    failed.push(`${path}: ${e.name || 'Error'} ${String(e.message).split('\n')[0]}`)
  }
}

// SEVERAL TABS AT ONCE (2026-10-22). One tab took 51 minutes for 1,334 pages,
// most of it each page waiting on its own API calls, while Railway's build has
// a time limit. PRERENDER_TABS tabs (default 4) take the next path from one
// queue; each page still renders alone in its tab, so nothing it saves differs.
const TABS = Math.max(1, Math.min(16, Number.parseInt(env.PRERENDER_TABS || '4', 10) || 4))
let next = 0
await Promise.all(Array.from({ length: Math.min(TABS, PATHS.length) }, async () => {
  const page = await openTab()
  while (next < PATHS.length) await saveOne(page, PATHS[next++])
  await page.close()
}))
await browser.close()
browserChild?.kill()
server.close()

console.log(`prerender: ${saved} of ${PATHS.length} pages saved in ${Math.round((Date.now() - t0) / 1000)}s (${TABS} tabs, ${apiOnce.size} API reads)`)
if (failed.length) {
  console.error(`prerender: ${failed.length} failed:\n  ${failed.slice(0, 40).join('\n  ')}`)
  process.exit(1)
}
