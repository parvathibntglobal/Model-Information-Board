import { useEffect, useState } from 'react'
import { guideFacts } from '../api'
import { comparePath } from '../compare/path'

/**
 * THE VERIFIED-FACTS BOX INSIDE A MIGRATION GUIDE (2026-10-30, anooj).
 *
 * The guide is written; this box is not. It is the registry's published
 * figures for the guide's two models and a checklist worded by
 * contract/migrations.yaml (judge/migrations.py `guide`), read when the page
 * opens - so the numbers are today's, whenever the guide was written.
 *
 * WRITTEN INTO THE POST'S SLOT, NOT PORTALLED. The post is an HTML string
 * (board/views.js vPost) that BoardView replaces whenever the page re-renders,
 * which would orphan a portal; this writes the box again after each render.
 * Every value is escaped: it is HTML built from data.
 */
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

const WORD = {
  up: { price: 'Dearer', share: 'Larger', tokens: 'Larger', date: 'Later' },
  down: { price: 'Cheaper', share: 'Smaller', tokens: 'Smaller', date: 'Earlier' },
}
const TONE = { Cheaper: 'pass', Larger: 'pass', Gained: 'pass', Dearer: 'warn', Smaller: 'warn', Lost: 'fail' }

function changeOf(r) {
  if (r.field === 'retirement_date') return r.from || r.to ? 'Dated' : 'None published'
  if (r.change === 'same') return 'Same'
  if (r.change === 'unknown') return 'Not published'
  if (r.change === 'gained') return 'Gained'
  if (r.change === 'lost') return 'Lost'
  return WORD[r.change]?.[r.kind] || r.change
}

const cell = (v) => (v == null ? '<span class="gf-none">not published</span>' : esc(v))

function rowsHtml(rows) {
  return rows.map((r) => {
    const word = changeOf(r)
    const tone = TONE[word]
    return `<tr><th scope="row">${esc(r.label)}</th><td>${cell(r.from)}</td><td>${cell(r.to)}</td>`
      + `<td><span class="gf-change${tone ? ` gf-${tone}` : ''}">${esc(word)}</span></td></tr>`
  }).join('')
}

function table(rows, a, b) {
  return `<div class="gf-scroll"><table class="gf-table"><thead><tr><th scope="col">Published fact</th>`
    + `<th scope="col">${esc(a)}</th><th scope="col">${esc(b)}</th><th scope="col">Change</th></tr></thead>`
    + `<tbody>${rowsHtml(rows)}</tbody></table></div>`
}

export function factsHtml(d, today = new Date().toISOString().slice(0, 10)) {
  const a = d.from.name
  const b = d.to.name
  // WHAT DIFFERS FIRST: the rows that change, then every fact behind a fold, so
  // a long same-same table does not bury the two lines that matter.
  const moved = d.rows.filter((r) => !['same', 'unknown'].includes(r.change) && r.field !== 'release_date')
  const order = d.order === 'title' ? `in the order this guide names them` : `from the older model to the newer one`
  return `<section class="gf-box" aria-label="Verified facts">
<div class="gf-head"><span class="gf-tag">Verified facts</span><span class="gf-when">published figures, read ${esc(today)}</span></div>
<h3 class="gf-title">What changes from ${esc(a)} to ${esc(b)}</h3>
<p class="gf-order">Shown ${esc(order)}. Written by code from each provider's published figures, not by the guide's writer.</p>
${moved.length ? table(moved, a, b) : '<p class="gf-same">No published figure differs between the two.</p>'}
<details class="gf-all"><summary>All ${d.rows.length} published facts</summary>${table(d.rows, a, b)}</details>
<h4 class="gf-sub">Before you switch</h4>
<ol class="gf-check">${d.checklist.map((x) => `<li>${esc(x)}</li>`).join('')}</ol>
<p class="gf-meta">On the board: <b>${d.reports.from.toLocaleString('en-US')}</b> reports on ${esc(a)} and <b>${d.reports.to.toLocaleString('en-US')}</b> on ${esc(b)}.
 <a href="${esc(comparePath([d.from.id, d.to.id]))}">See them side by side, job by job</a></p>
<p class="gf-note">Prices are per million tokens, as each provider lists them. "Not published" is unknown, not zero and not "no". Not covered here: ${esc(d.not_covered.join(', '))} - check ${esc(d.to.provider_name)}'s own documentation.</p>
</section>`
}

export default function GuideFacts({ slug, html, active }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!active || !slug) return undefined
    let alive = true
    setData(null)
    // A GUIDE WITHOUT ITS FACTS STILL READS: on failure the slot stays empty
    // and the written guide is untouched.
    guideFacts(slug).then((d) => alive && setData(d)).catch(() => {})
    return () => { alive = false }
  }, [slug, active])

  useEffect(() => {
    if (!data) return
    const el = document.getElementById('guide-facts')
    if (el) el.innerHTML = factsHtml(data)
  }, [data, html])

  return null
}
