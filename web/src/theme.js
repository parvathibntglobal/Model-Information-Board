// The site's light / dark theme (2026-10-28).
//
// index.html sets <html data-theme> before the first paint, from the visitor's
// saved choice or their device's setting; the colours are tokens.css. This
// module reads and changes it. Until the visitor chooses, the page follows the
// device, including a change made while the page is open.

const KEY = 'mb-theme'
const META = { light: '#F7F7F8', dark: '#0C0C0E' }

export const THEME_EVENT = 'mb-theme'

export function currentTheme() {
  if (typeof document === 'undefined') return 'dark' // no page (a build step): the original look
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'
}

function chosen() {
  try {
    const t = localStorage.getItem(KEY)
    return t === 'light' || t === 'dark' ? t : null
  } catch {
    return null // storage blocked: the device decides
  }
}

function apply(theme) {
  document.documentElement.setAttribute('data-theme', theme)
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', META[theme])
  window.dispatchEvent(new CustomEvent(THEME_EVENT, { detail: theme }))
}

/** The visitor chose: apply it and remember it. */
export function setTheme(theme) {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    /* storage blocked: this visit only */
  }
  apply(theme)
}

/** Follow the device's setting while the visitor has not chosen. Returns the
 * function that stops following. */
export function followDevice() {
  const media = window.matchMedia?.('(prefers-color-scheme: light)')
  if (!media) return () => {}
  const onChange = (e) => {
    if (!chosen()) apply(e.matches ? 'light' : 'dark')
  }
  media.addEventListener('change', onChange)
  return () => media.removeEventListener('change', onChange)
}
