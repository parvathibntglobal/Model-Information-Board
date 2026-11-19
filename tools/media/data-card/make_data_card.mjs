// SIGNAL BLOCK (data card) direction: a 3-page LinkedIn document carousel
// (1080x1350) on ONE topic, a count across models. Topic data comes from a
// JSON spec (SPEC.md); this file holds only the design. First spec:
// specs/usage-limits-2026-11-19.json (approved 2026-11-19).
// Philosophy: DATA_CARD_PHILOSOPHY.md. Inks checked with the dataviz validator
// on #FAF8F3: vermilion #D2452A / cobalt #1D66A6 pass all six checks.
// Run: CHROME=<chrome.exe> node make_data_card.mjs <spec.json> <outdir>
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { chromium } from 'playwright-core'

const [specPath, out] = process.argv.slice(2)
if (!specPath || !out) throw new Error('usage: node make_data_card.mjs <spec.json> <outdir>')
const S = JSON.parse(readFileSync(specPath, 'utf-8'))

// ── THE SPEC IS CHECKED, NEVER DEFAULTED (rule 12) ────────────────────────
const fail = (field, why) => { throw new Error(`spec ${specPath}: \`${field}\` ${why}`) }
const str = (v, f) => (typeof v === 'string' && v.trim() ? v : fail(f, 'must be a non-empty string'))
const int = (v, f) => (Number.isInteger(v) && v >= 0 ? v : fail(f, `must be a whole number >= 0, not ${JSON.stringify(v)}`))
const arr = (v, f) => (Array.isArray(v) ? v : fail(f, 'must be a list'))
const date = (v, f) => (/^\d{4}-\d{2}-\d{2}$/.test(str(v, f)) && !isNaN(Date.parse(v)) ? v : fail(f, 'must be a date YYYY-MM-DD'))
const sum = (xs, k) => xs.reduce((a, x) => a + x[k], 0)

str(S.slug, 'slug'); str(S.topic, 'topic'); str(S.filed_under, 'filed_under'); str(S.path, 'path')
str(S.population, 'population'); str(S.headline, 'headline'); str(S.not_a_measurement, 'not_a_measurement')
str(S.page2_note, 'page2_note')
date(S.window?.from, 'window.from'); date(S.window?.to, 'window.to'); date(S.read_on, 'read_on')
for (const side of ['negative', 'positive'])
  for (const k of ['stat', 'legend', 'bar']) str(S.sides?.[side]?.[k], `sides.${side}.${k}`)
const T = S.totals ?? fail('totals', 'is missing')
for (const k of ['people', 'negative', 'positive', 'models', 'entries', 'no_author_entries']) int(T[k], `totals.${k}`)
const ROWS = arr(S.rows, 'rows')
ROWS.forEach((r, i) => {
  str(r.model, `rows[${i}].model`)
  for (const k of ['people', 'negative', 'positive']) int(r[k], `rows[${i}].${k}`)
  if (r.people < 1) fail(`rows[${i}].people`, 'is 0: a model with no report is left off, not drawn as 0')
  if (r.negative > r.people || r.positive > r.people) fail(`rows[${i}]`, 'has more people on a side than in all')
  if (i && r.people > ROWS[i - 1].people) fail(`rows[${i}]`, 'is out of order: rows go most people first')
})
if (ROWS.length > 8) fail('rows', `has ${ROWS.length}; page 2 holds 8 - fold the rest into \`rest\``)
// The models beyond the 8 rows, in one line. Their side counts are SUMS over
// those models of each model's people on that side (one person on two of them
// counts twice); `neither` = per-model people with neither side.
const R = S.rest ?? fail('rest', 'is missing')
for (const k of ['models', 'people_min', 'people_max', 'negative', 'positive', 'neither']) int(R[k], `rest.${k}`)
if (R.models === 0) {
  for (const k of ['people_min', 'people_max', 'negative', 'positive', 'neither'])
    if (R[k]) fail(`rest.${k}`, 'must be 0 when rest.models is 0')
} else {
  if (R.people_min < 1 || R.people_min > R.people_max) fail('rest.people_min', 'must be 1..people_max')
  if (ROWS.length && R.people_max > ROWS.at(-1).people) fail('rest.people_max', 'is more than the smallest row; that model belongs in rows')
  if (R.negative + R.positive + R.neither < R.models * R.people_min)
    fail('rest', 'counts fewer side-takers than its models x people_min')
  for (const k of ['negative', 'positive', 'neither'])
    if (R[k] > R.models * R.people_max) fail(`rest.${k}`, 'is more than its models x people_max')
}
const SOURCES = arr(S.sources, 'sources')
SOURCES.forEach((s, i) => { str(s.platform, `sources[${i}].platform`); int(s.people, `sources[${i}].people`) })
// People whose posts are only on platforms the publication contract does not
// name in public (contract/publication.yaml `withheld_from_public`): one row,
// never a per-platform number for those platforms. 0 and 0 when none.
const NN = S.sources_not_named ?? fail('sources_not_named', 'is missing ({people, platforms}; 0 and 0 when none)')
int(NN.people, 'sources_not_named.people'); int(NN.platforms, 'sources_not_named.platforms')
if (SOURCES.length + (NN.people ? 1 : 0) > 8) fail('sources', 'with the not-named row is more than the 8 page 3 holds')
const H2 = arr(S.page2_head, 'page2_head').map((l, i) => str(l, `page2_head[${i}]`))
const H3 = arr(S.page3_head, 'page3_head').map((l, i) => str(l, `page3_head[${i}]`))

// Stated totals against what the rows imply. People are DISTINCT across
// models and platforms, so a sum is an upper bound, not an equality.
const shownPeople = sum(ROWS, 'people') + R.models * R.people_max
if (ROWS.length + R.models !== T.models) fail('totals.models', `is ${T.models}; rows ${ROWS.length} + rest ${R.models}`)
if (T.people > shownPeople) fail('totals.people', `is ${T.people}, more than the ${shownPeople} the models hold`)
if (ROWS.length && T.people < ROWS[0].people) fail('totals.people', 'is fewer than the largest row')
for (const side of ['negative', 'positive']) {
  if (T[side] > T.people) fail(`totals.${side}`, 'is more than totals.people')
  if (T[side] > sum(ROWS, side) + R[side]) fail(`totals.${side}`, 'is more than the rows and rest hold')
}
if (T.people && sum(SOURCES, 'people') + NN.people < T.people) fail('sources', 'and sources_not_named hold fewer people than totals.people; every person posted somewhere')
if (SOURCES.some((s) => s.people > T.people) || NN.people > T.people) fail('sources', 'has a platform with more people than totals.people')
if (T.entries < T.people + T.no_author_entries) fail('totals.entries', 'is fewer than people + no_author_entries')

// ── DERIVED, NOT STATED ───────────────────────────────────────────────────
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const d = (iso) => { const [y, m, dd] = iso.split('-').map(Number); return { y, m, dd } }
const fmt = (iso, withYear) => { const x = d(iso); return `${x.dd} ${MON[x.m - 1]}${withYear ? ` ${x.y}` : ''}` }
const WF = d(S.window.from), WT = d(S.window.to)
const windowDays = Math.round((Date.UTC(WT.y, WT.m - 1, WT.dd) - Date.UTC(WF.y, WF.m - 1, WF.dd)) / 86400000)
if (windowDays < 1) fail('window', 'ends before it starts')
const windowText = `${fmt(S.window.from, WF.y !== WT.y)} to ${fmt(S.window.to, true)}`
const WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten']
const fill = (t) => t.replaceAll('{window_days}', String(windowDays))
  .replaceAll('{platforms_word}', WORDS[SOURCES.length + NN.platforms] ?? String(SOURCES.length + NN.platforms))
  .replaceAll('{people}', String(T.people))
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
const NEG = S.sides.negative, POS = S.sides.positive
const PATH = esc(S.path), TOPIC = esc(S.topic)
const none = T.people === 0

mkdirSync(out, { recursive: true })
const F = (n) => new URL(`../fonts/${n}`, import.meta.url).href
const C = { ground: '#FAF8F3', ink: '#141414', soft: '#5E5B55', rule: '#D9D5CB', block: '#F3C234',
  problem: '#D2452A', held: '#1D66A6' }

const footer = (n) => `<footer><span>Model Information Board</span><span>${PATH}</span><span>${n} / 3</span></footer>`

const css = `
@font-face { font-family: Shoulders; font-weight: 700; src: url(${F('BigShoulders-Bold.ttf')}); }
@font-face { font-family: Shoulders; font-weight: 400; src: url(${F('BigShoulders-Regular.ttf')}); }
@font-face { font-family: ISans; font-weight: 400; src: url(${F('InstrumentSans-Regular.ttf')}); }
@font-face { font-family: ISans; font-weight: 700; src: url(${F('InstrumentSans-Bold.ttf')}); }
@font-face { font-family: Geist; src: url(${F('GeistMono-Regular.ttf')}); }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: ${C.ground}; }
section { position: relative; width: 1080px; height: 1350px; overflow: hidden; background: ${C.ground}; color: ${C.ink}; }
.pad { padding: 0 76px; }
.mono { font: 400 17px/1.3 Geist; letter-spacing: .06em; text-transform: uppercase; }
.block { background: ${C.block}; }
.huge { font: 700 600px/.78 Shoulders; letter-spacing: -.02em; }
.head { font: 700 92px/.92 Shoulders; text-transform: uppercase; letter-spacing: .005em; }
.lede { font: 400 34px/1.25 ISans; }
.small { font: 400 22px/1.4 ISans; color: ${C.soft}; }
.stat { border-top: 14px solid var(--c); padding-top: 18px; }
.stat b { display: block; font: 700 168px/.86 Shoulders; }
.stat span { display: block; font: 400 25px/1.25 ISans; margin-top: 12px; }
.legend { display: flex; gap: 46px; font: 400 22px/1 ISans; }
.legend i { display: inline-block; width: 34px; height: 18px; margin-right: 12px; vertical-align: -2px; }
.row { display: grid; grid-template-columns: 300px minmax(0, 1fr); column-gap: 24px; align-items: center; }
.row .name { font: 700 27px/1.1 ISans; }
.row .name small { display: block; font: 400 18px/1.3 Geist; color: ${C.soft}; margin-top: 6px; letter-spacing: .03em; }
.bar { display: flex; align-items: center; gap: 14px; height: 28px; }
.bar i { display: block; height: 24px; border-radius: 0 4px 4px 0; }
.bar b { font: 700 34px/1 Shoulders; }
.bar em { font: 400 18px/1 Geist; color: ${C.soft}; font-style: normal; }
footer { position: absolute; left: 76px; right: 76px; bottom: 46px; display: flex; justify-content: space-between;
  font: 400 15px/1 Geist; color: ${C.soft}; border-top: 2px solid ${C.ink}; padding-top: 16px; letter-spacing: .03em; }
`

// px per person: 44 (10 people = 440 px) until the largest row would pass 440.
const SCALE = Math.min(44, 440 / Math.max(1, ...ROWS.map((r) => Math.max(r.negative, r.positive))))
// A 0 here is a COUNT (0 of this model's people took that side), never "no
// data": a model with no report has no row at all (refused above).
const bar = (n, color, label) => `<div class="bar">${n ? `<i style="width:${n * SCALE}px; background:${color}"></i>` : ''}<b style="color:${C.ink}">${n}</b><em>${label}</em></div>`

const p1 = `<section>
  <div class="block pad" style="height: 800px; padding-top: 72px; position: relative;">
    <p class="mono">${TOPIC} · posts from ${windowText}</p>
    ${none
    ? `<p class="head" style="margin-top: 120px; font-size: 160px;">No reports</p>`
    : `<p class="huge" style="margin-top: 40px;">${T.people}</p>`}
    <p class="lede" style="position: absolute; left: 76px; right: 76px; bottom: 54px; font-weight: 700; font-size: 40px;">${none ? `on ${esc(S.filed_under)} in these ${windowDays} days` : esc(S.headline)}</p>
  </div>
  <div class="pad" style="display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 44px; margin-top: 64px;">
    <div class="stat" style="--c:${C.problem}"><b>${T.negative}</b><span>${esc(NEG.stat)}</span></div>
    <div class="stat" style="--c:${C.held}"><b>${T.positive}</b><span>${esc(POS.stat)}</span></div>
    <div class="stat" style="--c:${C.ink}"><b>${T.models}</b><span>models named</span></div>
  </div>
  <p class="small pad" style="position: absolute; bottom: 104px;">${none ? 'No one reported on this in the window: not a finding about the models.' : `Of ${T.people} people. One person can report on more than one model, and in both directions.`}</p>
  ${footer(1)}
</section>`

const p2 = `<section class="pad" style="padding-top: 72px;">
  <p class="mono">${TOPIC} · people per model</p>
  <h2 class="head" style="margin-top: 26px;">${H2.map(esc).join('<br>')}</h2>
  <div class="legend" style="margin-top: 34px;"><span><i style="background:${C.problem}"></i>${esc(NEG.legend)}</span><span><i style="background:${C.held}"></i>${esc(POS.legend)}</span></div>
  <div style="margin-top: 40px; display: grid; row-gap: 22px;">
    ${ROWS.length ? ROWS.map((r) => `<div class="row">
      <p class="name">${esc(r.model)}<small>${r.people} people</small></p>
      <div style="display: grid; row-gap: 6px;">${bar(r.negative, C.problem, esc(NEG.bar))}${bar(r.positive, C.held, esc(POS.bar))}</div>
    </div>`).join('') : `<p class="lede">No model had a report in these ${windowDays} days.</p>`}
    ${R.models ? `<div class="row" style="border-top: 2px solid ${C.rule}; padding-top: 26px;">
      <p class="name">${R.models} more models<small>${R.people_min === R.people_max ? `${R.people_min} ${R.people_min === 1 ? 'person' : 'people'}` : `${R.people_min}–${R.people_max} people`} each</small></p>
      <p style="font: 400 24px/1.35 ISans;"><b style="font: 700 30px Shoulders">${R.negative}</b> ${esc(NEG.bar)} &nbsp;·&nbsp; <b style="font: 700 30px Shoulders">${R.positive}</b> ${esc(POS.bar)} &nbsp;·&nbsp; <b style="font: 700 30px Shoulders">${R.neither}</b> neither</p>
    </div>` : ''}
  </div>
  ${none ? '' : `<p class="small" style="margin-top: 26px;">${esc(fill(S.page2_note))}</p>`}
  ${footer(2)}
</section>`

const maxSrc = Math.max(1, NN.people, ...SOURCES.map((s) => s.people))
const notNamedRow = NN.people ? `<div class="row" style="grid-template-columns: 210px 1fr;">
      <p class="name">Not named<small>${NN.platforms} ${NN.platforms === 1 ? 'platform' : 'platforms'} we do not name in public</small></p>
      <div class="bar"><i style="width:${(NN.people / maxSrc) * 560}px; background:${C.soft}"></i><b>${NN.people}</b></div>
    </div>` : ''
const p3 = `<section>
  <div class="block pad" style="padding-top: 72px; padding-bottom: 46px;">
    <p class="mono">${TOPIC} · where the ${T.people} people posted</p>
    <h2 class="head" style="margin-top: 26px;">${H3.map((l) => esc(fill(l))).join('<br>')}</h2>
  </div>
  <div class="pad" style="margin-top: 64px; display: grid; row-gap: 34px;">
    ${SOURCES.map((s) => `<div class="row" style="grid-template-columns: 210px 1fr;">
      <p class="name">${esc(s.platform)}</p>
      <div class="bar"><i style="width:${(s.people / maxSrc) * 560}px; background:${C.ink}"></i><b>${s.people}</b></div>
    </div>`).join('')}${notNamedRow}
  </div>
  <div class="pad" style="position: absolute; left: 0; right: 0; bottom: 120px; display: grid; grid-template-columns: 1fr 1fr; column-gap: 44px; row-gap: 26px; border-top: 2px solid ${C.rule}; padding-top: 34px; margin: 0 76px; padding-left: 0; padding-right: 0;">
    <p class="small"><b style="color:${C.ink}">Counted, not scored.</b> Each figure is a count of people, from ${T.entries} reports the board filed under ${esc(S.filed_under)}.</p>
    <p class="small"><b style="color:${C.ink}">Read, then counted.</b> A language model read each post and proposed the label; code counted the people.</p>
    <p class="small"><b style="color:${C.ink}">Not a measurement</b> ${esc(S.not_a_measurement)}</p>
    <p class="small"><b style="color:${C.ink}">Read ${fmt(S.read_on, true)}</b> from the board's public-post corpus.</p>
  </div>
  ${footer(3)}
</section>`

const html = `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body>${p1}${p2}${p3}</body></html>`
const base = `data-card-${S.slug}`
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
    sec.querySelectorAll('p, h2, .row, .bar, .stat, .legend').forEach((el) => {
      const r = el.getBoundingClientRect()
      if (r.right > sr.right - 40 || r.left < sr.left || r.bottom > sr.bottom - 40) bad.push(`p${i + 1} out of bounds: ${el.className || el.tagName} ${Math.round(r.right - sr.left)}x${Math.round(r.bottom - sr.top)}`)
      if (!el.closest('footer') && r.bottom > fr.top - 8 && r.top < fr.bottom) bad.push(`p${i + 1} touches footer: ${el.className || el.tagName}`)
    })
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
console.log('fonts:', await page.evaluate(() => [...document.fonts].map((f) => `${f.family} ${f.weight} ${f.status}`).join(', ')))
await browser.close()
