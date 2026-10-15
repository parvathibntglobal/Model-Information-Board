/**
 * Board links: `data-go="kind:arg"` -> the app route it means.
 *
 * ONE MAPPING FOR BOTH HALVES OF A LINK (SEO item 3, 2026-10-08). The views
 * used to emit `data-go` only, with no `href`, and `BoardView` turned a click
 * into a route. So a crawler found no link at all - every job, capability,
 * metric and model page was reachable only by script - and Ctrl-click,
 * middle-click and "copy link" did nothing. Now every link carries the real
 * `href` from `goPath`, and `BoardView` navigates with the SAME function, so
 * the address a crawler follows and the one a click opens cannot disagree.
 *
 * Plain ESM with no JSX: `views.js` imports it and is also rendered by node in
 * tests (tests/js/board_render.mjs).
 */

export function goPath(go) {
  const i = go.indexOf(':')
  const kind = i === -1 ? go : go.slice(0, i)
  const arg = i === -1 ? '' : go.slice(i + 1)
  if (kind === 'board') return arg ? `/board?tab=${arg}` : '/board'
  // ONE HEADING'S BOX on a tab: `group:cap:agentic`. The tab comes first and
  // the heading after the FIRST colon, the same split as the drill-downs.
  if (kind === 'group') {
    const j = arg.indexOf(':')
    return j === -1 ? `/board?tab=${arg}` : `/board?tab=${arg.slice(0, j)}&group=${encodeURIComponent(arg.slice(j + 1))}`
  }
  if (kind === 'job') return `/board/jobs/${arg}`
  if (kind === 'cap') return `/board/capabilities/${arg}`
  if (kind === 'metric') return `/board/metrics/${arg}`
  // THE DRILL-DOWN, and the arg is two things: `slug:modelKey`. Split on the
  // FIRST colon only, because a model key can contain one - and it can contain
  // a slash too (`model_version.id` is canonical for 166 of 1,249 board rows),
  // which is why it goes last in the path and `Board.jsx` rejoins the tail.
  if (kind === 'jobmodel' || kind === 'capmodel' || kind === 'metmodel') {
    const j = arg.indexOf(':')
    const seg = kind === 'jobmodel' ? 'jobs' : kind === 'capmodel' ? 'capabilities' : 'metrics'
    return j === -1 ? `/board/${seg}` : `/board/${seg}/${arg.slice(0, j)}/${arg.slice(j + 1)}`
  }
  // Out to the model's own page, which holds every section rather than one.
  // ModelDetail redirects an internal id to the canonical URL (SEO item 2).
  if (kind === 'model') return `/models/${arg}`
  if (kind === 'blogs') return '/blogs'
  if (kind === 'post') return `/blogs/${arg}`
  if (kind === 'live') return `/blogs/${arg}`
  return '/board'
}

const ATTR = { '&': '&amp;', '"': '&quot;', '<': '&lt;', '>': '&gt;', "'": '&#39;' }
const attr = (s) => String(s).replace(/[&"<>']/g, (c) => ATTR[c])

/** ` href="…" data-go="…"` for an `<a>`: the real address, and the in-app route. */
export function goAttrs(go) {
  return ` href="${attr(goPath(go))}" data-go="${attr(go)}"`
}
