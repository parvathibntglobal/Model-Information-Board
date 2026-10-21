/**
 * Load the platforms' embed scripts after a post renders (re-reviewed
 * 2026-10-13: Reddit and X appear in posts only as their official embeds).
 *
 * The post's HTML goes in through innerHTML, where a <script> never runs, so
 * the scripts are added here. Called after every render: X re-scans with
 * twttr.widgets.load(); Reddit's widgets.js scans once on load, so its script
 * is replaced to make it scan the new post.
 */
export function loadEmbeds(root = typeof document === 'undefined' ? null : document) {
  if (!root) return
  if (root.querySelector('blockquote.twitter-tweet')) {
    // X's own queue (its documented loader snippet): a call made while
    // widgets.js is still loading waits for it, rather than being skipped
    // because `twttr.widgets` does not exist yet.
    const t = window.twttr || (window.twttr = { _e: [], ready(f) { this._e.push(f) } })
    t.ready((tw) => tw.widgets.load())
    if (!document.getElementById('x-widgets')) addScript('x-widgets', 'https://platform.twitter.com/widgets.js')
  }
  if (root.querySelector('blockquote.reddit-embed-bq')) {
    const old = document.getElementById('reddit-widgets')
    if (old) old.remove()
    addScript('reddit-widgets', 'https://embed.reddit.com/widgets.js')
  }
}

function addScript(id, src) {
  const s = document.createElement('script')
  s.id = id
  s.async = true
  s.src = src
  s.charset = 'utf-8'
  document.body.appendChild(s)
}
