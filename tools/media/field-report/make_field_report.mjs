// FIELD REPORT direction (approved 2026-11-19): a 3-page LinkedIn document
// carousel (1080x1350) for one model's weeks, made from a SPEC (JSON) so any
// model renders. Build a spec from the board with build_spec.py; SPEC.md lists
// the fields. Philosophy: FIELD_REPORT_PHILOSOPHY.md.
// Inks checked with the dataviz validator on #F3EFE6: blue #24548A / red
// pencil #C45A2C pass lightness, chroma, CVD (protan dE 19.0) and contrast.
// Run: CHROME=<chrome.exe> node make_field_report.mjs <spec.json> <outdir>
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { chromium } from 'playwright-core'

const [specPath, out] = process.argv.slice(2)
if (!specPath || !out) throw new Error('usage: node make_field_report.mjs <spec.json> <outdir>')
const S = JSON.parse(readFileSync(specPath, 'utf8'))

// ── THE SPEC, CHECKED: a missing or wrong field refuses (no defaults) ───────
function need(obj, key, type, where) {
  const v = obj?.[key]
  const ok = type === 'array' ? Array.isArray(v) : typeof v === type && v !== ''
  if (!ok) throw new Error(`spec: ${where}${key} must be a ${type}, not ${JSON.stringify(v)}`)
  return v
}
const ISO = /^\d{4}-\d{2}-\d{2}$/
for (const k of ['title', 'subtitle', 'path', 'release_date', 'read_on', 'start']) need(S, k, 'string', '')
for (const k of ['release_date', 'read_on', 'start']) {
  if (!ISO.test(S[k])) throw new Error(`spec: ${k} must be YYYY-MM-DD, not ${S[k]}`)
}
need(S, 'weeks', 'array', '')
need(S, 'proofs', 'array', '')
if (S.weeks.length < 1 || S.weeks.length > 4) {
  throw new Error(`spec: a field-report carousel shows 1 to 4 weeks, not ${S.weeks.length}`)
}
S.weeks.forEach((w, i) => {
  for (const k of ['from', 'to']) {
    if (!ISO.test(need(w, k, 'string', `weeks[${i}].`))) throw new Error(`spec: weeks[${i}].${k} must be YYYY-MM-DD`)
  }
  for (const k of ['people', 'posts', 'pos', 'neg']) {
    const v = need(w, k, 'number', `weeks[${i}].`)
    if (!Number.isInteger(v) || v < 0) throw new Error(`spec: weeks[${i}].${k} must be a whole number >= 0`)
  }
  if (w.people > w.posts) throw new Error(`spec: weeks[${i}] has more people (${w.people}) than posts (${w.posts})`)
  if (w.pos > w.posts || w.neg > w.posts) throw new Error(`spec: weeks[${i}] counts more report posts than posts`)
})
S.proofs.forEach((p, i) => {
  if (!['positive', 'negative'].includes(p.side)) throw new Error(`spec: proofs[${i}].side must be positive or negative`)
  for (const k of ['text', 'platform']) need(p, k, 'string', `proofs[${i}].`)
  if (!ISO.test(need(p, 'date', 'string', `proofs[${i}].`))) throw new Error(`spec: proofs[${i}].date must be YYYY-MM-DD`)
  const wk = need(p, 'week', 'number', `proofs[${i}].`)
  if (wk < 1 || wk > S.weeks.length) throw new Error(`spec: proofs[${i}].week ${wk} is not a week shown`)
})
if (S.proofs.length > 2) throw new Error('spec: page III holds at most 2 proof cards')

// ── formatting ──────────────────────────────────────────────────────────────
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const dm = (iso) => { const [, m, d] = iso.split('-').map(Number); return `${d} ${MON[m - 1]}` }
const dmy = (iso) => `${dm(iso)} ${iso.slice(0, 4)}`
const WORD = ['', 'one', 'two', 'three', 'four']
const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const n = S.weeks.length
const sinceRelease = S.start === S.release_date
const lastTo = S.weeks[n - 1].to
const kicker1 = sinceRelease
  ? `Field report · first ${WORD[n]} week${n > 1 ? 's' : ''} after release`
  : `Field report · ${dm(S.start)} to ${dm(lastTo)}`
const maxPeople = Math.max(...S.weeks.map((w) => w.people))
const busiest = maxPeople > 0 && S.weeks.filter((w) => w.people === maxPeople).length === 1 && n > 1
  ? S.weeks.findIndex((w) => w.people === maxPeople) : -1

mkdirSync(out, { recursive: true })
const F = (f) => new URL(`../fonts/${f}`, import.meta.url).href
const C = { paper: '#F3EFE6', rule: '#DDD6C7', ink: '#1F2328', graphite: '#6A6862', dot: '#34373C',
  blue: '#24548A', red: '#C45A2C', margin: '#B9B2A3' }

// Seeded jitter: the hand tremor the philosophy allows in the marks, and only there.
let seed = 20261119
const rnd = () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296)
const j = (a) => (rnd() * 2 - 1) * a

// One dot per person, five to a column. The pitch shrinks to fit the column,
// never below a legible size; past that, one dot per person no longer fits.
const DOT_ROOM = 560
function dots(count) {
  if (count === 0) return '<p class="fig" style="margin:0">nobody posted about it this week</p>'
  const cols = Math.ceil(count / 5)
  const pitchX = Math.min(17, DOT_ROOM / cols)
  if (pitchX < 7) throw new Error(`${count} people is too many for one dot each; use the data card`)
  const k = pitchX / 17, r = 4.6 * k, pitchY = 13.5 * Math.max(k, 0.75)
  const w = cols * pitchX, h = 5 * pitchY
  let s = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">`
  for (let i = 0; i < count; i++) {
    const cx = Math.floor(i / 5) * pitchX + pitchX / 2 + j(0.5 * k)
    const cy = (i % 5) * pitchY + pitchY / 2 + j(0.5 * k)
    s += `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${(r + j(0.35 * k)).toFixed(2)}" fill="${C.dot}"/>`
  }
  return s + '</svg>'
}

// Tally gates: four strokes and a fifth across, one stroke per post. Wraps to
// a second row when a week has more posts than one row holds; refuses past two.
const TALLY_ROOM = 660
function tally(count, color) {
  if (count === 0) return `<span class="fig" style="margin:0">none</span>`
  const h = 30, step = 5.4, gate = 4 * step + 9.6
  const perRow = Math.floor(TALLY_ROOM / gate)
  const gates = Math.ceil(count / 5)
  const rows = Math.ceil(gates / perRow)
  if (rows > 2) throw new Error(`${count} posts need ${rows} rows of tallies; use the data card`)
  const w = Math.max(Math.min(gates, perRow) * gate, 10), rowH = h + 8, H = rows * rowH + (rows - 1) * 6
  let s = `<svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" aria-hidden="true">`
  s += `<g stroke="${color}" stroke-width="2.1" stroke-linecap="round" fill="none">`
  for (let g = 0; g < gates; g++) {
    const x0 = (g % perRow) * gate + 3, y0 = Math.floor(g / perRow) * (rowH + 6)
    const inGate = Math.min(5, count - g * 5)
    for (let q = 0; q < Math.min(4, inGate); q++) {
      const x = x0 + q * step
      s += `<line x1="${(x + j(0.8)).toFixed(1)}" y1="${(y0 + 4 + j(1.2)).toFixed(1)}" x2="${(x + j(0.8)).toFixed(1)}" y2="${(y0 + 4 + h + j(1.2)).toFixed(1)}"/>`
    }
    if (inGate === 5) {
      s += `<line x1="${(x0 - 3 + j(0.8)).toFixed(1)}" y1="${(y0 + h - 1 + j(1.5)).toFixed(1)}" x2="${(x0 + 3 * step + 4 + j(0.8)).toFixed(1)}" y2="${(y0 + 9 + j(1.5)).toFixed(1)}"/>`
    }
  }
  return s + '</g></svg>'
}

const footer = (plate, path = true) => `<footer>
  <span>Model Information Board</span>
  <span class="path">${path ? esc(S.path) : 'Field report No. 01'}</span>
  <span>Plate ${plate} of III</span></footer>`

const css = `
@font-face { font-family: Gloock; src: url(${F('Gloock-Regular.ttf')}); }
@font-face { font-family: Instrument; font-style: italic; src: url(${F('InstrumentSerif-Italic.ttf')}); }
@font-face { font-family: Plex; font-weight: 400; src: url(${F('IBMPlexMono-Regular.ttf')}); }
@font-face { font-family: Plex; font-weight: 700; src: url(${F('IBMPlexMono-Bold.ttf')}); }
@font-face { font-family: Crimson; src: url(${F('CrimsonPro-Regular.ttf')}); }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: ${C.paper}; }
section { position: relative; width: 1080px; height: 1350px; overflow: hidden; color: ${C.ink};
  background:
    linear-gradient(90deg, transparent 151px, ${C.margin} 151px, ${C.margin} 152px, transparent 152px),
    repeating-linear-gradient(180deg, transparent 0 35px, ${C.rule} 35px 36px),
    ${C.paper};
  padding: 92px 96px 0 188px; }
section::after { content: ''; position: absolute; inset: 0; pointer-events: none; opacity: .5;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .35  0 0 0 0 .31  0 0 0 0 .24  0 0 0 .09 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
.kicker { font: 400 15px/1 Plex; letter-spacing: .18em; text-transform: uppercase; color: ${C.graphite}; }
h1 { font: 400 92px/1.0 Gloock; letter-spacing: -.01em; margin-top: 30px; }
h2 { font: 400 54px/1.08 Gloock; margin-top: 30px; max-width: 760px; }
.sub { font: italic 400 38px/1.15 Instrument; color: ${C.graphite}; margin-top: 14px; }
.margin-note { position: absolute; left: 34px; width: 100px; text-align: right;
  font: italic 400 21px/1.15 Instrument; color: ${C.graphite}; }
.row { position: relative; display: grid; grid-template-columns: 210px 1fr; align-items: center; column-gap: 26px; }
.wk { font: 700 15px/1.3 Plex; letter-spacing: .08em; text-transform: uppercase; }
.wk small { display: block; font-weight: 400; letter-spacing: .02em; text-transform: none; color: ${C.graphite}; font-size: 15px; }
.fig { font: 400 16px/1.35 Plex; color: ${C.graphite}; margin-top: 10px; }
.fig b { font-weight: 700; color: ${C.ink}; font-size: 19px; }
.foot { position: absolute; left: 188px; right: 96px; font: 400 23px/1.4 Crimson; color: ${C.graphite}; }
footer { position: absolute; left: 188px; right: 96px; bottom: 54px; display: flex; justify-content: space-between;
  font: 400 13px/1 Plex; letter-spacing: .06em; color: ${C.graphite}; border-top: 1px solid ${C.margin}; padding-top: 16px; }
footer .path { letter-spacing: 0; }
.legend { display: flex; gap: 40px; margin-top: 30px; font: 400 16px/1 Plex; color: ${C.ink}; }
.legend i { display: inline-block; width: 26px; height: 2.4px; vertical-align: middle; margin-right: 12px; }
.card { position: relative; background: #FBF9F4; border: 1px solid ${C.rule}; padding: 34px 40px 30px 52px;
  box-shadow: 0 1px 0 #E7E1D4, 0 14px 28px -22px rgba(60,50,30,.35); }
.card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 8px; background: var(--tab); }
.card .tag { font: 700 14px/1 Plex; letter-spacing: .16em; text-transform: uppercase; color: var(--tab); }
.card p.note { font: 400 33px/1.32 Crimson; margin-top: 18px; color: ${C.ink}; }
.card .src { font: 400 14px/1 Plex; color: ${C.graphite}; margin-top: 22px; letter-spacing: .04em; }
`

const p1 = `<section>
  <p class="kicker">${esc(kicker1)}</p>
  <h1>${esc(S.title)}</h1>
  <p class="sub">${esc(S.subtitle)}</p>
  <div style="margin-top: 108px; display: grid; row-gap: 84px;">
    ${S.weeks.map((w, i) => `<div class="row">
      ${i === busiest ? '<p class="margin-note" style="left:-154px; top: 18px;">the busiest week</p>' : ''}
      <div><p class="wk">Week ${i + 1}<small>${dm(w.from)} – ${dm(w.to)}</small></p>
        <p class="fig"><b>${w.people}</b> people<br>${w.posts} posts</p></div>
      <div>${dots(w.people)}</div></div>`).join('')}
  </div>
  <p class="foot" style="bottom: 128px;">Each dot is one engineer who posted publicly about using it. Counted by the board from ${sinceRelease ? `release, ${dm(S.start)},` : dm(S.start)} to ${dmy(lastTo)}; read ${dmy(S.read_on)}.</p>
  ${footer('I')}
</section>`

const p2 = `<section>
  <p class="kicker">Field report · what each week's posts recorded</p>
  <h2>For it, in blue ink. Against it, in red pencil.</h2>
  <div class="legend"><span><i style="background:${C.blue}"></i>a post with a positive report</span><span><i style="background:${C.red}"></i>a post with a negative report</span></div>
  <div style="margin-top: 72px; display: grid; row-gap: 56px;">
    ${S.weeks.map((w, i) => w.posts === 0 ? `<div>
      <p class="wk" style="display:flex; gap: 18px; align-items: baseline;">Week ${i + 1}<small style="display:inline">${dm(w.from)} – ${dm(w.to)}</small></p>
      <p class="fig">nobody posted about it this week, so there is nothing to count for or against</p></div>` : `<div>
      <p class="wk" style="display:flex; gap: 18px; align-items: baseline;">Week ${i + 1}<small style="display:inline">${dm(w.from)} – ${dm(w.to)} · of ${w.posts} posts</small></p>
      <div style="display: grid; grid-template-columns: 132px 1fr; row-gap: 8px; align-items: center; margin-top: 12px;">
        <span class="fig" style="margin:0; color:${C.blue}"><b style="color:${C.blue}">${w.pos}</b> for</span>${tally(w.pos, C.blue)}
        <span class="fig" style="margin:0; color:${C.red}"><b style="color:${C.red}">${w.neg}</b> against</span>${tally(w.neg, C.red)}
      </div></div>`).join('')}
  </div>
  <p class="foot" style="bottom: 128px;">One stroke per post. A post can record both, so the two rows are not a split of the week; there is no score here, only the count.</p>
  ${footer('II')}
</section>`

const card = (p) => `<div class="card" style="--tab:${p.side === 'positive' ? C.blue : C.red}"><p class="tag">${p.side === 'positive' ? 'For' : 'Against'} · week ${p.week}</p>
      <p class="note">${esc(p.text)}</p>
      <p class="src">${esc(p.platform)} · ${dmy(p.date)} · restated by the board</p></div>`
const p3 = `<section>
  <p class="kicker">Field report · ${S.proofs.length === 2 ? 'two entries' : S.proofs.length === 1 ? 'one entry' : 'the record'} from the record</p>
  <h2>What the counts are made of</h2>
  <div style="margin-top: 64px; display: grid; row-gap: 46px;">
    ${S.proofs.length ? S.proofs.map(card).join('\n    ')
    : '<p class="foot" style="position:static; color:#1F2328">The board holds no restated report for these weeks yet. The counts stand on the reports themselves, each linked on the model page.</p>'}
  </div>
  <p class="foot" style="bottom: 128px;">Every entry, week by week, with its source: <span style="font: 400 19px Plex; color:${C.ink}">${esc(S.path)}</span></p>
  ${footer('III', false)}
</section>`

const html = `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body>${p1}${p2}${p3}</body></html>`
const slug = String(S.file_slug || S.title).toLowerCase().replace(/[^a-z0-9.]+/g, '-').replace(/^-|-$/g, '')
const file = `${out}/field-report-${slug}.html`
writeFileSync(file, html)
const browser = await chromium.launch({ executablePath: process.env.CHROME })
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } })
await page.goto(pathToFileURL(file).href)
await page.evaluate(() => document.fonts.ready)
// Layout guard: nothing may leave its page or cross the footer.
const problems = await page.evaluate(() => {
  const bad = []
  document.querySelectorAll('section').forEach((sec, i) => {
    const sr = sec.getBoundingClientRect(), fr = sec.querySelector('footer').getBoundingClientRect()
    sec.querySelectorAll('p, svg, .card, .row, .legend').forEach((el) => {
      const r = el.getBoundingClientRect()
      if (r.right > sr.right - 40 || r.left < sr.left || r.bottom > sr.bottom - 40) bad.push(`p${i + 1} out of bounds: ${el.className || el.tagName} ${Math.round(r.right - sr.left)}x${Math.round(r.bottom - sr.top)}`)
      if (!el.closest('footer') && r.bottom > fr.top - 8 && r.top < fr.bottom) bad.push(`p${i + 1} touches footer: ${el.className || el.tagName}`)
    })
    const foot = sec.querySelector('.foot')
    if (foot) {
      const fb = foot.getBoundingClientRect()
      sec.querySelectorAll('.row, .card, svg').forEach((el) => {
        const r = el.getBoundingClientRect()
        if (r.bottom > fb.top - 8 && r.top < fb.bottom) bad.push(`p${i + 1} overlaps the footnote: ${el.className || el.tagName}`)
      })
    }
  })
  return bad
})
if (problems.length) { console.log(problems.join('\n')); await browser.close(); process.exit(1) }
console.log('layout ok')
await page.pdf({ path: `${out}/field-report-${slug}.pdf`, width: '1080px', height: '1350px', printBackground: true })
const sections = await page.$$('section')
for (let i = 0; i < sections.length; i++) await sections[i].screenshot({ path: `${out}/field-report-${slug}-p${i + 1}.png` })
console.log('fonts:', await page.evaluate(() => [...document.fonts].map((f) => `${f.family} ${f.style} ${f.status}`).join(', ')))
await browser.close()
