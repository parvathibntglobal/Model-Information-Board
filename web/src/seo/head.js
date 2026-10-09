import { useEffect } from 'react'
import { useIndexable } from './indexable'
import { noindexFor } from './pages'

/**
 * Apply a page's <head> - title, description, canonical, robots, og - and put
 * the site defaults back when the page goes.
 *
 * THE DEFAULTS ARE WHATEVER index.html SHIPPED, read once, not restated here.
 * So `index.html` stays the single place that says what an unconfigured page
 * shows - including `robots: noindex, nofollow`, which is what keeps the board
 * out of search engines today.
 *
 * ROBOTS CAN ONLY GET STRICTER. A page may ask for `noindex` (login, admin);
 * it can never turn index.html's `noindex` into `index`. Opening the site to
 * search engines is one deliberate edit to index.html, not something any page
 * can do by accident.
 *
 * NO CANONICAL UNTIL THE SITE IS OPEN, and no guess in its place. The address
 * comes from the build (vite.config.js injects `VITE_SITE_URL` only when
 * `SITE_URL` is set AND `PUBLIC_SITE=1` - the same switch as robots.txt and
 * the sitemap). Falling back to `window.location.origin` would produce a
 * canonical on every build, pointing at staging or localhost wherever it ran
 * (rule 12: a fallback that succeeds on a wrong input). Closed, the tag is left
 * out and the console says so once.
 *
 * LEAVING A PAGE RESTORES index.html'S OWN CANONICAL, if the build wrote one
 * (it does when the site is open: the landing's). The first version removed it,
 * so the landing would have lost its canonical after any visit elsewhere.
 */

// `?.`: Vite always defines `import.meta.env`; plain node (the head test) does not.
const SITE_URL = (import.meta.env?.VITE_SITE_URL || '').replace(/\/+$/, '')
let warnedNoSiteUrl = false
let defaults = null

function meta(selector, attr, name) {
  let el = document.head.querySelector(selector)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, name)
    document.head.appendChild(el)
  }
  return el
}

function readDefaults() {
  if (defaults) return defaults
  const get = (sel) => document.head.querySelector(sel)?.getAttribute('content') ?? null
  defaults = {
    title: document.title,
    description: get('meta[name="description"]'),
    robots: get('meta[name="robots"]'),
    ogTitle: get('meta[property="og:title"]'),
    ogDescription: get('meta[property="og:description"]'),
    canonical: document.head.querySelector('link[rel="canonical"]')?.getAttribute('href') ?? null,
    ogUrl: get('meta[property="og:url"]'),
  }
  return defaults
}

function setContent(selector, attr, name, value) {
  if (value == null) {
    document.head.querySelector(selector)?.remove()
    return
  }
  meta(selector, attr, name).setAttribute('content', value)
}

function writeCanonical(href) {
  const existing = document.head.querySelector('link[rel="canonical"]')
  if (!href) { existing?.remove(); return }
  const link = existing || Object.assign(document.createElement('link'), { rel: 'canonical' })
  link.setAttribute('href', href)
  if (!existing) document.head.appendChild(link)
}

/** The page's canonical when the site is open; otherwise index.html's own (or none). */
function setCanonical(path, d) {
  if (!path || !SITE_URL) {
    if (path && !SITE_URL && !warnedNoSiteUrl) {
      warnedNoSiteUrl = true
      console.warn('seo: the site is not open (SITE_URL and PUBLIC_SITE=1 at build), '
        + 'so no page canonical is written (no host is guessed).')
    }
    writeCanonical(d.canonical)
    return d.ogUrl
  }
  const href = `${SITE_URL}${path.startsWith('/') ? path : `/${path}`}`
  writeCanonical(href)
  return href
}

/** `noindex, nofollow` when the page or index.html asks for it; otherwise index.html's value. */
function robotsFor(base, noindex) {
  if (!noindex) return base
  return /noindex/i.test(base || '') ? base : 'noindex, nofollow'
}

/** Imperative form, for tests and for code outside a component. */
export function applyHead(head) {
  const d = readDefaults()
  const h = head || {}
  document.title = h.title || d.title
  setContent('meta[name="description"]', 'name', 'description', h.description || d.description)
  setContent('meta[name="robots"]', 'name', 'robots', robotsFor(d.robots, h.noindex))
  setContent('meta[property="og:title"]', 'property', 'og:title', h.title || d.ogTitle)
  setContent('meta[property="og:description"]', 'property', 'og:description', h.description || d.ogDescription)
  const url = setCanonical(h.canonical, d)
  setContent('meta[property="og:url"]', 'property', 'og:url', url)
}

/** Restore exactly what index.html shipped. */
export function resetHead() {
  applyHead(null)
}

/**
 * `useHead(head)` - apply on mount and whenever `head` or the indexable list
 * changes; reset on leave. `head` null means "not known yet" (data still
 * loading): the defaults stay. `false` means a child component owns the head.
 */
export function useHead(head) {
  const indexable = useIndexable()
  const effective = head ? { ...head, noindex: noindexFor(head, indexable) } : null
  const key = head === false ? 'skip' : effective ? JSON.stringify(effective) : ''
  useEffect(() => {
    // `false`: a child owns the head (NotFound inside Board, Blogs or
    // ModelDetail). A child's effect runs before its parent's, so applying or
    // resetting here would overwrite what the child just set.
    if (head === false) return undefined
    applyHead(effective)
    return resetHead
    // `key` stands for `effective`: a fresh object with the same content must not re-apply.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
}
