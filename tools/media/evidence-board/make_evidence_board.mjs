// PINNED TESTIMONY (evidence board) direction: a 3-page LinkedIn document
// carousel (1080x1350) on ONE model - a case file, one pin per person, and
// pinned report cards for and against. Topic data comes from a JSON spec
// (SPEC.md); this file holds only the design. First spec:
// specs/minimax-m2.7-2026-11-19.json (approved 2026-11-19).
// Card text = the board's stored feed_paraphrase rows (restatements, never
// quotes). Philosophy: EVIDENCE_BOARD_PHILOSOPHY.md. Inks checked with the
// dataviz validator: stamps indigo #4A44B5 / red #B8352B on #F4EDDD, pins
// #6F7FE8 / #DD5E47 on #263430 - all six checks pass for both pairs.
// Run: CHROME=<chrome.exe> node make_evidence_board.mjs <spec.json> <outdir>
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { chromium } from 'playwright-core'

const [specPath, out] = process.argv.slice(2)
if (!specPath || !out) throw new Error('usage: node make_evidence_board.mjs <spec.json> <outdir>')
const S = JSON.parse(readFileSync(specPath, 'utf-8'))

// ── THE SPEC IS CHECKED, NEVER DEFAULTED (rule 12) ────────────────────────
const fail = (field, why) => { throw new Error(`spec ${specPath}: \`${field}\` ${why}`) }
const str = (v, f) => (typeof v === 'string' && v.trim() ? v : fail(f, 'must be a non-empty string'))
const int = (v, f) => (Number.isInteger(v) && v >= 0 ? v : fail(f, `must be a whole number >= 0, not ${JSON.stringify(v)}`))
const num = (v, f) => (typeof v === 'number' && v >= 0 && isFinite(v) ? v : fail(f, `must be a price >= 0, not ${JSON.stringify(v)}`))
const arr = (v, f) => (Array.isArray(v) ? v : fail(f, 'must be a list'))
const date = (v, f) => (/^\d{4}-\d{2}-\d{2}$/.test(str(v, f)) && !isNaN(Date.parse(v)) ? v : fail(f, 'must be a date YYYY-MM-DD'))

for (const k of ['slug', 'model', 'path', 'population', 'kicker', 'card_caption', 'cards_head']) str(S[k], k)
date(S.read_on, 'read_on'); date(S.first_post, 'first_post'); date(S.last_post, 'last_post')
if (S.first_post > S.last_post) fail('first_post', 'is after last_post')
if (!('note' in S)) fail('note', 'is missing (a string, or null for no sticky note)')
if (S.note !== null) str(S.note, 'note')
const PRICES = arr(S.prices, 'prices')
PRICES.forEach((p, i) => {
  date(p.date, `prices[${i}].date`)
  for (const k of ['input_from', 'input_to', 'output_from', 'output_to']) num(p[k], `prices[${i}].${k}`)
  if (i && p.date < PRICES[i - 1].date) fail(`prices[${i}]`, 'is out of date order')
  if (i && (p.input_from !== PRICES[i - 1].input_to || p.output_from !== PRICES[i - 1].output_to))
    fail(`prices[${i}]`, 'does not start where the previous change ended')
})
if (PRICES.length > 5) fail('prices', `has ${PRICES.length}; the case card holds 5`)
const P = S.people ?? fail('people', 'is missing')
for (const k of ['all', 'for', 'against', 'neither', 'entries', 'no_author_entries']) int(P[k], `people.${k}`)
for (const k of ['for', 'against', 'neither']) if (P[k] > P.all) fail(`people.${k}`, 'is more than people.all')
if (P.for + P.against + P.neither < P.all) fail('people', 'rows hold fewer than people.all; every person sits in at least one')
if (P.entries < P.all + P.no_author_entries) fail('people.entries', 'is fewer than all + no_author_entries')
for (const k of ['for', 'against', 'neither']) if (P[k] > 40) fail(`people.${k}`, 'is over 40: the pin rows hold two lines of 20')
const CARDS = arr(S.cards, 'cards')
if (CARDS.length < 1 || CARDS.length > 6) fail('cards', `has ${CARDS.length}; page 2 holds 1 to 6`)
CARDS.forEach((c, i) => {
  if (c.side !== 'for' && c.side !== 'against') fail(`cards[${i}].side`, 'must be "for" or "against"')
  for (const k of ['what', 'source', 'text']) str(c[k], `cards[${i}].${k}`)
  date(c.date, `cards[${i}].date`)
  if (c.text.length > 160) fail(`cards[${i}].text`, `is ${c.text.length} characters; a card holds 160`)
  if (c.date < S.first_post || c.date > S.last_post) fail(`cards[${i}].date`, 'is outside first_post..last_post')
})
if (CARDS.some((c) => c.side === 'for') && P.for === 0) fail('cards', 'has a "for" card but people.for is 0')
if (CARDS.some((c) => c.side === 'against') && P.against === 0) fail('cards', 'has an "against" card but people.against is 0')
const H3 = arr(S.page3_head, 'page3_head').map((l, i) => str(l, `page3_head[${i}]`))
const XS = arr(S.extra_stats, 'extra_stats')
if (XS.length !== 2) fail('extra_stats', 'must hold exactly 2 (the case card has four cells)')
XS.forEach((x, i) => {
  int(x.value, `extra_stats[${i}].value`); str(x.label, `extra_stats[${i}].label`)
  if (x.counts === 'price_changes') {
    if (x.value !== PRICES.length) fail(`extra_stats[${i}].value`, `is ${x.value}; prices holds ${PRICES.length}`)
  } else if (x.counts === 'people_since') {
    date(x.since, `extra_stats[${i}].since`)
    if (x.value === 0 && S.last_post >= x.since) fail(`extra_stats[${i}]`, `says 0 since ${x.since} but last_post is ${S.last_post}`)
    if (x.value > 0 && S.last_post < x.since) fail(`extra_stats[${i}]`, `says ${x.value} since ${x.since} but last_post is ${S.last_post}`)
  } else if (x.counts !== 'other') fail(`extra_stats[${i}].counts`, 'must be "price_changes", "people_since" or "other"')
})

// ── DERIVED, NOT STATED ───────────────────────────────────────────────────
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const fmt = (iso, withYear) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MON[m - 1]}${withYear ? ` ${y}` : ''}` }
const money = (x) => { let s = x.toFixed(4).replace(/0+$/, ''); if (/\.\d$/.test(s)) s += '0'; if (s.endsWith('.')) s += '00'; return `$${s}` }
const WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six']
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
const sameYear = S.first_post.slice(0, 4) === S.last_post.slice(0, 4)
const span = `${fmt(S.first_post, !sameYear)} to ${fmt(S.last_post, true)}`

mkdirSync(out, { recursive: true })
const F = (n) => new URL(`../fonts/${n}`, import.meta.url).href
const PATH = esc(S.path)
const C = { felt: '#263430', feltHi: '#2E3E39', card: '#F4EDDD', ink: '#24231F', soft: '#6B675D',
  onFelt: '#E9E2D2', onFeltSoft: '#A9B3AD', forInk: '#4A44B5', againstInk: '#B8352B',
  forPin: '#6F7FE8', againstPin: '#DD5E47', neutralPin: '#B7B1A3' }

const pins = (n, color) => Array.from({ length: n }, () => `<i class="pin" style="--p:${color}"></i>`).join('')
// A row with no one in it says so; it is never an empty row that reads as a gap.
const pinsOr = (n, color) => (n ? pins(n, color) : `<span class="typed" style="font-size: 19px; color:${C.onFeltSoft};">no one</span>`)
const footer = (n) => `<footer><span>Model Information Board</span><span>${PATH}</span><span>${n} / 3</span></footer>`

const css = `
@font-face { font-family: Young; src: url(${F('YoungSerif-Regular.ttf')}); }
@font-face { font-family: DMMono; src: url(${F('DMMono-Regular.ttf')}); }
@font-face { font-family: Arsenal; src: url(${F('ArsenalSC-Regular.ttf')}); }
@font-face { font-family: Hand; src: url(${F('NothingYouCouldDo-Regular.ttf')}); }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: ${C.felt}; }
section { position: relative; width: 1080px; height: 1350px; overflow: hidden; color: ${C.onFelt};
  background: radial-gradient(120% 90% at 30% 20%, ${C.feltHi} 0%, ${C.felt} 60%); padding: 70px 72px 0; }
section::after { content: ''; position: absolute; inset: 0; pointer-events: none; opacity: .55;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='1.3' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .1  0 0 0 0 .14  0 0 0 0 .12  0 0 0 .22 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
.card { position: relative; background: ${C.card}; color: ${C.ink}; padding: 40px 40px 30px;
  box-shadow: 0 2px 0 rgba(0,0,0,.18), 0 22px 30px -18px rgba(0,0,0,.6); transform: rotate(var(--r, 0deg)); }
.card::before { content: ''; position: absolute; top: 14px; left: 50%; width: 20px; height: 20px; margin-left: -10px; border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #fff8 0 18%, transparent 19%), var(--tack, #8A8578); box-shadow: 0 3px 4px rgba(0,0,0,.45); }
.kicker { font: 400 21px/1 Arsenal; letter-spacing: .22em; color: ${C.onFeltSoft}; }
h1 { font: 400 92px/1 Young; }
h2 { font: 400 56px/1.08 Young; color: ${C.onFelt}; }
.typed { font: 400 23px/1.5 DMMono; }
.stamp { display: inline-block; font: 400 21px/1 Arsenal; letter-spacing: .16em; padding: 9px 14px 8px;
  border: 3px solid currentColor; border-radius: 4px; transform: rotate(var(--s, -2deg)); opacity: .92; }
.src { font: 400 14.5px/1.3 DMMono; color: ${C.soft}; margin-top: 18px; white-space: nowrap; }
.pin { display: inline-block; width: 26px; height: 26px; border-radius: 50%; margin: 0 9px 9px 0;
  background: radial-gradient(circle at 34% 30%, #ffffff66 0 20%, transparent 22%), var(--p); box-shadow: 0 3px 4px rgba(0,0,0,.5); }
.pinrow { display: grid; grid-template-columns: 210px 1fr; align-items: center; column-gap: 20px; }
.pinrow p { font: 400 22px/1.25 Arsenal; letter-spacing: .1em; color: ${C.onFelt}; }
.pinrow p b { font: 400 40px/1 Young; letter-spacing: 0; display: block; margin-bottom: 4px; }
.note { font: 400 34px/1.2 Hand; color: #2D2A22; background: #E9D98E; padding: 22px 26px; transform: rotate(var(--r)); box-shadow: 0 16px 22px -14px rgba(0,0,0,.6); }
footer { position: absolute; left: 72px; right: 72px; bottom: 44px; display: flex; justify-content: space-between;
  font: 400 15px/1 DMMono; color: ${C.onFeltSoft}; border-top: 1px solid #ffffff33; padding-top: 16px; }
`

const p1 = `<section>
  <p class="kicker">${esc(S.kicker)}</p>
  <div class="card" style="--r:-1.2deg; margin-top: 34px; padding: 48px 44px 36px; --tack:#8A8578;">
    <h1>${esc(S.model)}</h1>
    <p class="typed" style="margin-top: 20px; color:${C.soft}; font-size: 19px;">${esc(S.card_caption)}</p>
    ${PRICES.length ? `<div style="margin-top: 22px; display: grid; grid-template-columns: 130px 1fr 1fr; row-gap: 10px; font: 400 25px/1.3 DMMono;">
      <span style="color:${C.soft}">date</span><span style="color:${C.soft}">input</span><span style="color:${C.soft}">output</span>
      ${PRICES.map((p) => `<span>${fmt(p.date, false)}</span><span>${money(p.input_from)} → ${money(p.input_to)}</span><span>${money(p.output_from)} → ${money(p.output_to)}</span>`).join('')}
    </div>` : ''}
  </div>
  <div style="margin-top: 64px;">
    <p class="kicker">Who reported on it · one pin per person</p>
    <div style="margin-top: 28px; display: grid; row-gap: 22px;">
      <div class="pinrow"><p><b>${P.for}</b>for it</p><div>${pinsOr(P.for, C.forPin)}</div></div>
      <div class="pinrow"><p><b>${P.against}</b>against it</p><div>${pinsOr(P.against, C.againstPin)}</div></div>
      <div class="pinrow"><p><b>${P.neither}</b>took no side</p><div>${pinsOr(P.neither, C.neutralPin)}</div></div>
    </div>
    <p class="typed" style="margin-top: 26px; font-size: 19px; color:${C.onFeltSoft};">${P.all} people in all, ${span}. One person can sit in more than one row.</p>
  </div>
  ${S.note === null ? '' : `<div class="note" style="--r: 2.2deg; position: absolute; right: 86px; bottom: 132px; width: 330px;">${esc(S.note)}</div>`}
  ${footer(1)}
</section>`

const card = (c, i) => `<div class="card" style="--r:${[-1.4, 1.1, 0.8, -1.0, -0.6, 1.3][i]}deg; --tack:${c.side === 'for' ? C.forPin : C.againstPin}; padding: 44px 32px 24px;">
  <span class="stamp" style="color:${c.side === 'for' ? C.forInk : C.againstInk}; --s:${i % 2 ? 2 : -2}deg; font-size: 18px;">${c.side === 'for' ? 'FOR' : 'AGAINST'} · ${esc(c.what.toUpperCase())}</span>
  <p class="typed" style="margin-top: 16px; font-size: 20px; line-height: 1.42;">${esc(c.text)}</p>
  <p class="src">${esc(c.source)} · ${fmt(c.date, true)} · restated by the board</p></div>`

const p2 = `<section>
  <p class="kicker">${WORDS[CARDS.length]} of the reports, as filed</p>
  <h2 style="margin-top: 18px;">${esc(S.cards_head)}</h2>
  <div style="margin-top: 42px; display: grid; grid-template-columns: 1fr 1fr; column-gap: 34px; row-gap: 28px;">
    ${CARDS.map(card).join('')}
  </div>
  ${footer(2)}
</section>`

const cell = (v, label) => `<p><b style="font: 400 60px/1 DMMono; display:block; margin-bottom: 8px;">${v}</b>${label}</p>`
const p3 = `<section>
  <p class="kicker">What the file holds, and what it does not</p>
  <h2 style="margin-top: 18px;">${H3.map(esc).join('<br>')}</h2>
  <div class="card" style="--r: -0.8deg; margin-top: 52px;">
    <div style="display: grid; grid-template-columns: 1fr 1fr; column-gap: 36px; row-gap: 26px; font: 400 22px/1.45 DMMono;">
      ${cell(P.entries, 'reports filed for the model, all time')}
      ${cell(P.all, P.no_author_entries
    ? `people behind them (${P.no_author_entries} reports carried no author and are not counted as people)`
    : 'people behind them; every report carried its author')}
      ${XS.map((x) => cell(x.value, esc(x.label))).join('\n      ')}
    </div>
  </div>
  <div class="card" style="--r: 1deg; position: absolute; left: 72px; right: 72px; bottom: 140px; --tack:#8A8578;">
    <p class="typed" style="font-size: 21px;">Counted, not scored. A language model read each post and proposed what it reported; code checked every quote and counted the people. The cards restate the reports and never quote them.</p>
    <p class="src" style="margin-top: 20px;">Read ${fmt(S.read_on, true)} · every report, with its source, on the model page</p>
  </div>
  ${footer(3)}
</section>`

const html = `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body>${p1}${p2}${p3}</body></html>`
const base = `evidence-board-${S.slug}`
const file = `${out}/${base}.html`
writeFileSync(file, html)
const browser = await chromium.launch({ executablePath: process.env.CHROME })
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } })
await page.goto(pathToFileURL(file).href)
await page.evaluate(() => document.fonts.ready)
const problems = await page.evaluate(() => {
  const bad = []
  document.querySelectorAll('section').forEach((sec, i) => {
    const sr = sec.getBoundingClientRect(), fr = sec.querySelector('footer').getBoundingClientRect()
    const els = [...sec.querySelectorAll('p, h1, h2, .card, .pinrow, .note')]
    els.forEach((el) => {
      const r = el.getBoundingClientRect()
      if (r.right > sr.right - 36 || r.left < sr.left + 20 || r.bottom > sr.bottom - 40) bad.push(`p${i + 1} out of bounds: ${el.className || el.tagName} ${Math.round(r.right - sr.left)}x${Math.round(r.bottom - sr.top)}`)
      if (!el.closest('footer') && r.bottom > fr.top - 8 && r.top < fr.bottom) bad.push(`p${i + 1} touches footer: ${el.className || el.tagName}`)
    })
    // cards, the note and the pin rows must not cover each other
    const boxes = [...sec.querySelectorAll('.card, .note, .pinrow, p.typed')].filter((el) => !el.closest('.card') || el.classList.contains('card')).map((el) => el.getBoundingClientRect())
    for (let a = 0; a < boxes.length; a++) for (let b = a + 1; b < boxes.length; b++) {
      const A = boxes[a], B = boxes[b]
      if (A.left < B.right - 4 && B.left < A.right - 4 && A.top < B.bottom - 4 && B.top < A.bottom - 4) bad.push(`p${i + 1} boxes overlap: ${a} and ${b}`)
    }
  })
  return bad
})
if (problems.length) {
  await browser.close()
  throw new Error(`layout check failed, nothing rendered:\n${problems.join('\n')}`)
}
console.log('layout ok')
await page.pdf({ path: `${out}/${base}.pdf`, width: '1080px', height: '1350px', printBackground: true })
const sections = await page.$$('section')
for (let i = 0; i < sections.length; i++) await sections[i].screenshot({ path: `${out}/${base}-p${i + 1}.png` })
console.log('fonts:', await page.evaluate(() => [...document.fonts].map((f) => `${f.family} ${f.status}`).join(', ')))
await browser.close()
