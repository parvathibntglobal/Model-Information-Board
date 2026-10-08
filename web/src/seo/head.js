import { useEffect } from 'react'

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
 * NO CANONICAL WITHOUT `VITE_SITE_URL`, and no guess in its place. Falling back
 * to `window.location.origin` would produce a canonical on every build -
 * pointing at staging or localhost wherever the build ran, which tells a
 * search engine the real page is somewhere it must not be (rule 12: a fallback
 * that succeeds on a wrong input). Unset, the tag is left out and the console
 * says so once.
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

function setCanonical(path) {
  const existing = document.head.querySelector('link[rel="canonical"]')
  if (!path || !SITE_URL) {
    existing?.remove()
    if (path && !SITE_URL && !warnedNoSiteUrl) {
      warnedNoSiteUrl = true
      console.warn('seo: VITE_SITE_URL is not set, so no canonical link is written (no host is guessed).')
    }
    return null
  }
  const href = `${SITE_URL}${path.startsWith('/') ? path : `/${path}`}`
  const link = existing || Object.assign(document.createElement('link'), { rel: 'canonical' })
  link.setAttribute('href', href)
  if (!existing) document.head.appendChild(link)
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
  const url = setCanonical(h.canonical)
  setContent('meta[property="og:url"]', 'property', 'og:url', url)
}

/** Restore exactly what index.html shipped. */
export function resetHead() {
  applyHead(null)
}

/**
 * `useHead(head)` - apply on mount and whenever `head` changes; reset on leave.
 * `head` null means "not known yet" (data still loading): the defaults stay.
 */
export function useHead(head) {
  const key = head ? JSON.stringify(head) : ''
  useEffect(() => {
    applyHead(head)
    return resetHead
    // `key` stands for `head`: a fresh object with the same content must not re-apply.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
}
