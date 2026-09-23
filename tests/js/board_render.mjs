// Render the board the way a browser does, and report WHERE each card landed.
//
// WHY THIS EXISTS. The 28 tests in `test_the_board_renders_its_parents.py` are
// searches over the SOURCE of `views.js`. That is enough to check what a
// builder says, and useless for checking what it produces: #428 filed all 69
// ungrouped leaves under the heading above them while the source still read
// `if(g.kind !== 'parent') return draw(g.leaf)`. The branch was right; the
// markup around it put the card in the wrong grid, and no string search over a
// correct-looking line can see that.
//
// So this imports the real `setBoardData` and the real `vBoard`, parses the
// HTML into an element tree, and prints for every card the heading whose grid
// ENCLOSES it - or null when it stands in its own rank. It knows nothing about
// what the answer should be; the assertions live in Python.
//
// Usage: node tests/js/board_render.mjs <payload.json>   ->  JSON on stdout
import fs from 'node:fs'
import { DB, setBoardData } from '../../web/src/board/db.js'
import { vBoard } from '../../web/src/board/views.js'

const VOID = new Set(['br', 'hr', 'img', 'input', 'meta', 'link', 'source'])
const TAG = /<(\/?)([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>/g

/** The element tree, which is the only thing that can answer "inside what?". */
function parse(html) {
  const root = { tag: '#root', cls: '', go: null, kids: [] }
  const stack = [root]
  for (const [, close, tag, attrs] of html.matchAll(TAG)) {
    if (close) {
      // Pop to the nearest matching open rather than underflowing the stack, so
      // malformed markup is REPORTED as a shape instead of crashing the probe.
      const at = stack.findLastIndex((n) => n.tag === tag)
      if (at > 0) stack.length = at
      continue
    }
    if (VOID.has(tag) || attrs.trimEnd().endsWith('/')) continue
    const node = {
      tag,
      cls: (/class="([^"]*)"/.exec(attrs) || [, ''])[1],
      go: (/data-go="[a-z]+:([^"]*)"/.exec(attrs) || [, null])[1],
      kids: [],
    }
    stack[stack.length - 1].kids.push(node)
    stack.push(node)
  }
  return root
}

const has = (n, c) => n.cls.split(/\s+/).includes(c)
function* walk(n) { yield n; for (const k of n.kids) yield* walk(k) }

/** Every card below `node`, tagged with the heading passed down to it. */
function cardsIn(node, heading, out) {
  for (const kid of node.kids) {
    if (kid.go) out.push({ slug: kid.go, under: heading })
    else cardsIn(kid, heading, out)
  }
}

/** One tab, as cards-with-their-heading plus the headings in document order.
 *
 * A HEADING OWNS THE GRID IMMEDIATELY AFTER IT AND NOTHING ELSE. That is the
 * whole rule this probe encodes, and it is deliberately strict: a grid with any
 * other element between it and a `.phead-row` belongs to no heading, because a
 * reader scanning down the page would not attach it to one either.
 */
function render(tab) {
  const html = vBoard(tab)
  // The headings that folded, by the parent slug their button names. Reported
  // rather than judged: whether a heading SHOULD fold is a question about
  // `LEAF_PREVIEW`, and this file holds no opinion about the answer.
  const folds = [...html.matchAll(/data-expand="([^"]*)"/g)].map((m) => m[1])
  // The tag-only parser keeps no text, so heading names are read off the HTML
  // in document order and consumed as each `.phead-row` is met.
  const names = [...html.matchAll(/<h3>([^<]*)<\/h3>/g)].map((m) => m[1])
  const cards = []
  const headings = []
  let seen = 0
  for (const node of walk(parse(html))) {
    let heading = null
    for (const kid of node.kids) {
      if (has(kid, 'phead-row')) {
        heading = names[seen++] ?? '(unnamed)'
        headings.push(heading)
      } else if (has(kid, 'igrid')) {
        cardsIn(kid, heading, cards)
        heading = null
      } else {
        heading = null
      }
    }
  }
  return { cards, headings, folds }
}

setBoardData(JSON.parse(fs.readFileSync(process.argv[2], 'utf-8')))
const report = {}
for (const [tab, flat, groups] of [
  ['best', DB.jobs, DB.jobGroups],
  ['cap', DB.caps, DB.capGroups],
  ['met', DB.mets, DB.metGroups],
]) {
  report[tab] = {
    ...render(tab),
    flat: flat.map((x) => x.slug),
    ungrouped: (groups || []).filter((g) => g.kind !== 'parent').map((g) => g.leaf.slug),
    grouped: Object.fromEntries(
      (groups || []).filter((g) => g.kind === 'parent')
        .map((g) => [g.name, g.children.map((c) => c.slug)]),
    ),
  }
}
process.stdout.write(JSON.stringify(report))
