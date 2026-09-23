// Board + blogs view builders, ported verbatim from the SEO demo.
// They return HTML strings; BoardView renders them and wires clicks to the router.
import { DB } from './db'

// ── ESCAPING, WHICH THIS FILE DID NOT HAVE ─────────────────────────────────
// Every builder below returns an HTML STRING and BoardView renders it through
// `dangerouslySetInnerHTML`. That makes this file an HTML sink, and until now
// all 59 interpolations went in raw — the landing demo this was ported from has
// an `esc()` and the port dropped it.
//
// It stopped being theoretical when the board got data: the 2026-09-10 run
// stored 716 Reddit comments and 35 Hacker News threads of arbitrary text, and
// a comment containing `<img src=x onerror=...>` would otherwise execute.
//
// `String(x ?? '')` rather than `x.replace(...)`: a null definition or a numeric
// count would throw, and a board that crashes on a missing value is worse than
// one that renders an empty cell.
const esc = (x) => String(x ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

// A HARVESTED URL IS UNTRUSTED, AND ESCAPING DOES NOT MAKE AN HREF SAFE.
// `javascript:alert(1)` is well-formed and survives escaping intact, so the
// SCHEME is what has to be checked. http and https only; anything else — a
// javascript:, data: or file: URL, or a value that will not parse — returns
// null and the caller renders plain text instead of a link.
//
// Relative URLs are rejected too. Every source here is an external platform
// permalink, so a relative href would point back at the board and read as a
// citation to ourselves.
function safeHref(u){
  if(!u) return null;
  try {
    const parsed = new URL(String(u));
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') ? parsed.href : null;
  } catch { return null; }
}

const byS = (arr,s) => arr.find(x=>x.slug===s);
// VOICES, NOT REPORTS, AND "verified" IS GONE. The old labels were
// 'verified' / 'single report', sitting next to a count that now reads
// "1 report · 3 figures" - which made the card say "1 report · 3 figures ·
// single report". Worse, 'verified' is already this codebase's word for
// `quote_verified`, a span that matched its source text; reusing it for "two
// or more people said so" overloaded the one term that has to stay precise.
const ST = {v:['ev-v','corroborated'], c:['ev-c','contested'], s:['ev-n','one voice'],
            n:['ev-n','not discussed']};
// A state we were not given renders as 'not discussed' rather than throwing:
// an unknown state is an absence, and absence is a real value on this board.
const stOf = (k) => ST[k] || ST.n;

function crumb(parts){
  return '<p class="crumb">'+parts.map(([t,h])=>h?`<a data-go="${esc(h)}">${esc(t)}</a>`:t).join('<i>/</i>')+'</p>';
}
function ranked(rows, route){
  if(!rows || !rows.length) return '';
  // NO RANK NUMERAL. This printed 01, 02, 03 from the array index, and the
  // heading above it said "the quotes behind the ranking" — so a list ordered
  // by REPORT COUNT read as a merit ranking, and a model with one complaint
  // read as the best choice for the job. There is no score anywhere in this
  // path: `board_sections` sorts by count and says so ("the ordering is a
  // COUNT, never a score"). The count is already on the right of every row,
  // which is the honest version of what the numeral was pretending to be.
  //
  // `route` MAKES THE ROW THE WAY IN. Given one, each row opens that model's
  // own page under this category and the marker becomes a chevron; without
  // one the list renders exactly as it did. It is a parameter rather than
  // always-on because the row is only worth clicking where a page exists to
  // land on, and inventing that link everywhere would be a promise this file
  // cannot keep.
  //
  // THE STATE ON EACH ROW IS NOW THAT ROW'S OWN — see `commonFields` in
  // db.js, which used to stamp the section's state onto every model.
  return '<div class="ranked">'+rows.map((r)=>{
    const [cls,lbl]=stOf(r.s);
    const go = route && r.key ? ` data-go="${esc(route)}:${esc(r.key)}"` : '';
    // THE SPLIT IS ITS OWN LINE, not more words inside `.st`. That span
    // already carries two counts and a state label, and `.right` is
    // `white-space:nowrap` - a fourth clause in it would push the row wider
    // than a phone. Empty on best-for and metric, where there is no split.
    const sp = r.sp ? `<span class="split">${esc(r.sp)}</span>` : '';
    return `<div class="rank${r.dim?' dim':''}${go?' open':''}"${go}><span class="n">${go?'›':'·'}</span>
      <div><b>${esc(r.m)}</b><span class="vend">${esc(r.v)}</span><p>${esc(r.d)}</p></div>
      <div class="right"><span class="price">${esc(r.p)}</span><span class="st ${cls}">${esc(r.e)} · ${esc(lbl)}</span>${sp}</div></div>`;
  }).join('')+'</div>';
}

/** The line above a model list, carrying what the list was drawn from.
 *
 * Rule 7 on a page rather than in an argument: "20 models" answers nothing
 * without saying 20 of what, counted how. The three numbers here are the
 * section's own — models listed, reports behind them, voices among those —
 * and the ordering is named as a count so the top row is not read as a pick.
 */
function listIntro(item){
  const n = (item.rows||[]).length;
  if(!n) return '';
  const rep = item.repTotal, voi = item.voiTotal;
  // WHAT `both` MEANS, SAID ONCE. The split counts a report under each
  // polarity it states, so a report saying both is counted twice and the row
  // names it - and that has to be explained somewhere a reader will see
  // before the arithmetic fails for them. Here rather than on 16 of 297 rows.
  //
  // Conditional on a split being present, so best-for and metric do not carry
  // a sentence about a column they do not have.
  const anySplit = (item.rows || []).some(r => r.sp);
  const split = anySplit
    ? ` The split counts a report under every polarity it states, so one that`
      + ` says both is counted under each and the row says so.`
    : '';
  // ⚠ THE ORDERING SENTENCE IS LOAD-BEARING AND STAYS. Ordering by POSITIVE
  //   reports was weighed and refused: on `capability/vision` it moves
  //   DeepSeek V4 Flash 0423 - 8 reports from 7 voices, the strongest
  //   agreement on the page - from #1 to #6, below five models holding one
  //   positive report from one voice. An ordering that answers "who does this
  //   best" is a merit ranking whatever it is counted from, and this section
  //   is deliberately not polarity-filtered (see `board_sections`) precisely
  //   because a bad result is evidence of the same standing as a good one.
  return `${n} model${n===1?'':'s'}, named in ≥${rep} report${rep===1?'':'s'}`
    + ` by ${voi} voice${voi===1?'':'s'}. Ordered by report count, which is a count`
    + ` and not a score.${split} Open one to read every report it holds.`;
}

/** Reports that name no model, and so appear under none.
 *
 * Renders nothing when there are none — a caveat about nothing is noise, and
 * 0 of 1,249 rows are in this state today. It exists because the alternative
 * to saying it is losing them silently, which is the one thing this board
 * must not do with an absence of its own making.
 */
function orphanNote(item){
  const n = item.orphans || 0;
  if(!n) return '';
  return `<p class="muted" style="margin-top:10px;max-width:74ch;font-size:.9rem">${n}
    report${n===1?' names':'s name'} no model, so ${n===1?'it is':'they are'} not listed
    above. ${n===1?'It is':'They are'} held by the board and counted in the total.</p>`;
}
/** The models this job drops entirely, named and linked.
 *
 * `best_for` claims suitability, so a problem report cannot fill it - and for
 * most models that means a row with some reports missing, which the drill-down
 * page says. For a model whose every report here is a problem report it means
 * NO ROW: the model is not on the page at all, and a reader cannot tell that
 * from a model nobody has ever discussed. Rule 4 on the largest thing this
 * filter can remove.
 *
 * It names each model rather than only counting them, because "1 model is not
 * listed" is not something a reader can act on and a link to what was actually
 * said is. Renders nothing on a capability page, where nothing is filtered.
 */
function suppressedNote(item){
  const list = item.suppressed || [];
  if(!list.length) return '';
  const names = list.map(x =>
    `<a data-go="model:${esc(x.key)}">${esc(x.m)}</a> (${x.n} report${x.n===1?'':'s'})`
  ).join(', ');
  return `<p class="muted" style="margin-top:14px;max-width:74ch;line-height:1.6">
    <b>${list.length} model${list.length===1?' is':'s are'} not listed above.</b>
    ${list.length===1?'Every report it has':'Every report they have'} on this job is a report of
    a problem, and <b>Best for</b> lists evidence that a model suits a job — so
    ${list.length===1?'it has':'they have'} no row here. The reports exist and the board kept them:
    ${names}.</p>`;
}
function conds(list){
  if(!list || !list.length) return '';
  return '<ul class="conds">'+list.map(([a,b])=>`<li><b>${esc(a)}</b><span>${esc(b)}</span></li>`).join('')+'</ul>';
}
function quotes(qs){
  if(!qs || !qs.length) return '';
  // [quote, who, document_id, isNegative, url]
  //
  // ONE BLOCK PER SOURCE, NOT PER QUOTE. The ethical-reasoning page listed
  // three quotes as three separate cards:
  //
  //     "it revived both men in 10 out of 20 rounds (50%)"
  //     "When people are watching, Fable 5.1 never shot, and it revived both
  //      men in 19 out of 20 rounds (95%)"
  //     "Fable 5.1 agent shot and killed the man with gold in 2 out of 20
  //      rounds (10%), and took his gold both times."
  //
  // All three are the same comment by the same author, and NONE of them stands
  // alone: read singly, none says what the scenario was or which condition its
  // figure belongs to. Three cards read as three independent observations.
  //
  // WHAT THIS DELIBERATELY DOES NOT DO is merge them into one readable
  // sentence. Those figures describe DIFFERENT conditions - 50% unobserved,
  // 95% observed, 10% shot-and-robbed - so composing them into prose would be
  // us writing a summary of somebody else's experiment: rule 3 (nothing
  // synthesised reaches a page) and rule 1 (no claim without a verbatim
  // quote). The context comes from the source we link, not from us.
  //
  // THE FOURTH SLOT IS `isNegative`, NOT `contested`. It was named contested
  // here while db.js filled it with `q.polarity === 'negative'`, and
  // `evidenceState` separately uses 'c' for genuinely contested. One letter
  // meaning two things is how a negative quote wore the colour for
  // disagreement.
  const groups = [];
  const seen = new Map();
  for (const row of qs){
    const key = row[2] || row[4] || String(seen.size);
    if(!seen.has(key)){
      seen.set(key, groups.length);
      groups.push({who:row[1], src:row[2], url:row[4], items:[]});
    }
    groups[seen.get(key)].items.push(row);
  }
  return '<div class="quotes">'+groups.map(g=>{
    const href = safeHref(g.url);
    // NO LINK IS BETTER THAN A DEAD ONE. A quote whose document row carries no
    // usable URL says so, rather than offering an underline that does nothing.
    const cite = href
      ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">open the source</a>`
      : '<span class="nosrc" title="This document has no usable link.">no link recorded</span>';
    const anyNeg = g.items.some(r=>r[3]);
    // A COUNT, NOT A SUMMARY. "3 figures from this one report" is arithmetic
    // over rows; saying what the three figures mean together would not be.
    const many = g.items.length > 1
      ? `<span class="qmeta">${g.items.length} figures from this one report — each states a different condition, so they are shown together rather than as separate findings</span>`
      : '';
    const body = g.items.map(row=>{
      // THE LABEL IS THE POINT, NOT THE BORDER. A negative quote used to be
      // marked only by switching a 3px left border from green to amber, with
      // no legend anywhere — so a reader could not know what amber meant, and
      // every other quote being green read as approval. Said in words instead.
      const tag = row[3] ? '<span class="ptag neg">reported as a problem</span>' : '';
      return `<div class="qi">${tag}<q>${esc(row[0])}</q></div>`;
    }).join('');
    return `<div class="qb${anyNeg?' neg':''}">${many}${body}<cite>${esc(g.who)} · ${esc(g.src)} · ${cite}</cite></div>`;
  }).join('')+'</div>';
}

/** The Reports heading, from the polarity actually present.
 *
 * It was the hardcoded string "What breaks it" on every capability page. On
 * ethical-reasoning one of the three quotes is positive ("never shot ... 95%"),
 * so the heading described the opposite of part of its own content. */
function reportsHeading(qs){
  if(!qs || !qs.length) return '';
  const neg = qs.filter(r=>r[3]).length;
  if(neg === qs.length) return 'What breaks it';
  return neg ? 'What was reported, good and bad' : 'What was reported';
}
function related(list){
  if(!list || !list.length) return '';
  return '<div class="related">'+list.map(([h,t])=>`<a data-go="${esc(h)}">${esc(t)}</a>`).join('')+'</div>';
}
function sec(eyebrow,h2,intro,inner){
  // An empty `inner` means the pipeline produced nothing for this block. Render
  // NOTHING rather than a heading over a void: the demo's `pick`, `conds`,
  // `nots` and `lim` blocks were written by hand, and a classifier does not
  // produce them. A fabricated pick is the synthesised claim rule 3 forbids,
  // and an invented condition is worse than a missing one because it reads as
  // a finding. So the block waits for an editor instead of guessing.
  if(!inner || !String(inner).trim()) return '';
  return `<div class="shell sec"><div class="sec-h">${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}
    ${h2?`<h2>${h2}</h2>`:''}${intro?`<p>${intro}</p>`:''}</div>${inner}</div>`;
}
function card(x, route){
  const [cls,lbl]=stOf(x.st);
  return `<div class="icard" data-go="${route}:${esc(x.slug)}"><b>${esc(x.name)}</b><p>${esc(x.card)}</p>
    <div class="meta"><span class="${cls}">${esc(x.ev)} · ${esc(lbl)}</span><span>${esc(x.vol)}</span></div></div>`;
}
function mcard(x){
  // HOW MANY MODELS, ON THE CARD, BEFORE THE CLICK.
  //
  // Measured 2026-09-21: 62 of 84 axes hold exactly ONE model. Every card
  // looked alike, so a reader opened three of them to find three single
  // observations presented as comparison tables. The count is the one fact
  // that decides whether opening it is worth doing, and it was the one fact
  // the card did not carry.
  const n = (x.mrows || []).length;
  const who = n === 1 ? '1 model' : `${n} models`;
  return `<div class="icard" data-go="metric:${esc(x.slug)}"><b>${esc(x.name)}</b><p>${esc(x.card)}</p>
    <div class="meta"><span>unit · ${esc(x.unit)}</span><span>${esc(who)}</span></div></div>`;
}

/* ---------- parent headings ---------- */
//
// A PARENT IS A HEADING ON THE GRID AND NEVER A ROUTE, and that is the whole
// design rather than a simplification of it. `contract/slug_parents.yaml`:
//
//     A parent groups for reading and never implies the leaves are the same
//     measurement.
//
// A heading renders its leaves UNDERNEATH, visible without a click, so a
// reader can never mistake the parent for the thing being measured. A parent
// PAGE would read as a category - you would click it, see leaves, click a
// leaf - and that shape says the leaves are one measurement however the prose
// denies it. It would also add a fourth level to board -> category -> model.
//
// ⚠ THE COUNT ON A HEADING IS `leaves` AND NOTHING ELSE. Never reports, never
//   models, never voices. Summing the children double-counts every document
//   under two leaves (55 against a true union of 51 on `software-engineering`)
//   and sums a figure that is already a floor. The line under the heading says
//   there is no total, because a reader who wants one should be told it does
//   not exist rather than left looking for it.
function parentHead(g){
  return `</div><div class="phead-row"><div class="parent-h">
    <h3>${esc(g.name)}</h3><span>${g.leaves} ${g.leaves===1?'leaf':'leaves'}</span></div>
    <p>Grouped for reading. Each of these is its own measurement — nothing here is
    merged, and there is no total for the group.</p></div><div class="igrid">`;
}

/** One grid, leaves under their headings, ungrouped leaves in their own rank. */
function groupedGrid(groups, flat, draw){
  // NO GROUPS MEANS RENDER AS BEFORE. An older payload carries no `grouped`,
  // and a board that silently showed nothing would be worse than one that
  // shows what it always did.
  if(!groups || !groups.length) return flat.map(draw).join('');
  return groups.map(g =>
    g.kind === 'parent'
      ? parentHead(g) + g.children.map(draw).join('')
      : draw(g.leaf)
  ).join('');
}

/** How much of a section has a heading. READ, NOT REMEMBERED - the ungrouped
 *  count was 19, 20 and 21 within one day. */
function parentNote(key){
  const c = (DB.parentCoverage || {})[key];
  if(!c || !c.parents) return '';
  return `<p class="axisdiv"><b>${c.parents} headings over ${c.grouped} of ${c.leaves}.</b>
    The other ${c.ungrouped} sit on their own — a heading is a way to read the list, not a
    claim about what belongs together, and nothing is filed under a catch-all.</p>`;
}

/* ---------- the withheld notice ---------- */
//
// A CAUSED ABSENCE HAS TO SAY IT WAS CAUSED (rule 4), AND IT TRAVELS WITH ITS
// DENOMINATOR (rule 7). This tab shows fewer figures than the database stores,
// and the reason is not that the models were never measured - it is that a
// stored figure has to be able to support itself before it is published.
//
// The reasons are listed rather than totalled because they send a reader to
// different places: "no quantity" and "figure not in its quote" are the
// extractor's prompt, while a relative claim is a figure filed in the wrong
// section. One number would send everybody to the same wrong place.
//
// AND IT SAYS NOTHING WAS DELETED, because that is the question a reader who
// remembers a figure will actually have.
const WITHHELD_WORDING = {
  'no quantity': 'state no quantity at all',
  'figure not in its quote': 'give a figure that is not in the quote beside it',
  'axis not in its quote': 'name a benchmark their own quote does not contain',
  'a relative claim, not a value on this axis':
    'are a comparison with another model, not a value on this axis',
  'the unit says money and the value carries no amount':
    'carry a unit their value cannot fill',
}

export function withheldNote(){
  const w = DB.metsWithheld || {}
  const entries = Object.entries(w).filter(([, n]) => n > 0)
  if(!entries.length) return ''
  entries.sort((a, b) => b[1] - a[1])
  const total = entries.reduce((t, [, n]) => t + n, 0)
  const parts = entries.map(([k, n]) => `${n} ${WITHHELD_WORDING[k] || k}`)
  return `<p class="withheld"><b>${total} recorded figure${total === 1 ? ' is' : 's are'} held back from this tab.</b>
    Of those, ${parts.join('; ')}.
    Nothing has been deleted &mdash; every one is still stored with its quote, and it appears here
    as soon as it can support itself.</p>`
}

/* ---------- views ---------- */
function vBoard(tab){
  tab = tab||'best';
  const empty = '<p class="muted" style="padding:8px 0">Nothing here yet.</p>';
  const panes = {
    best: {intro:'Jobs with enough reports to rank. Each opens a page that names the cheapest model engineers report doing it, the conditions that change the answer, and the criticisms that did not disqualify it.',
      grid: DB.jobs.length ? DB.jobs.map(j=>card(j,'job')).join('') : empty},
    cap: {intro:'A capability means one thing across every model page. These are the definitions the board rules by — written so an answer engine can quote them, and so two claims can be compared without arguing about words.',
      note: parentNote('caps'),
      grid: DB.caps.length ? groupedGrid(DB.capGroups, DB.caps, c=>card(c,'cap')) : empty},
    met: {intro:'The axes recorded on every model. Each page states the unit, where the figure came from, and the thing the number cannot tell you — which is usually more useful than the number. '
      // ⚠ THIS SENTENCE CAME OFF `metGrid`'s DIVIDER AND MUST NOT BE LOST.
      // That divider split the grid into comparing axes and single-model ones;
      // parents now group the same grid by subject and the two cannot both
      // own it. The SPLIT is redundant - `mcard` has printed "1 model" /
      // "N models" on every card since 2026-09-21, which is the same fact per
      // card - but the sentence is rule 4 content and is not redundant: an
      // axis holding one model is a real recorded figure, and a reader must
      // not read it as a failed comparison.
      + 'Many axes hold a single model. Each is a real recorded figure, and none of them is a comparison — there is nothing else measured on that axis yet.',
      note: withheldNote() + parentNote('mets'),
      // AXES THAT CAN COMPARE SOMETHING COME FIRST, and the rest are marked
      // rather than mixed in. An axis holding one model is a real observation
      // and belongs on the page; listing it between two comparisons implies it
      // is one. Stable within each half - `board_sections` already ordered
      // these by report count, and that ordering is a COUNT, never a score.
      grid: DB.mets.length ? groupedGrid(DB.metGroups, DB.mets, m=>mcard(m)) : empty}
  };
  const p = panes[tab];
  const note = p.note || '';
  return `<div class="shell phead">${crumb([['Board',null]])}
    <h1>The board</h1>
    <p class="sub">Three ways into the same evidence. <b>Best for</b> answers a job.
    <b>Capabilities</b> defines what a claim means, so a claim on one model page can be compared with a
    claim on another. <b>Metrics</b> are the axes, and what each one refuses to average.</p></div>
    <div class="shell">
      <div class="tabs" role="tablist">
        <button role="tab" aria-selected="${tab==='best'}" data-tab="best">Best for</button>
        <button role="tab" aria-selected="${tab==='cap'}" data-tab="cap">Capabilities</button>
        <button role="tab" aria-selected="${tab==='met'}" data-tab="met">Metrics</button>
      </div>
      <p class="muted" style="max-width:70ch;margin-bottom:20px;line-height:1.6">${p.intro}</p>
      ${note}
      <div class="igrid">${p.grid}</div>
    </div>`;
}

function vJob(slug){
  const j = byS(DB.jobs,slug); if(!j) return vBoard('best');
  // `pick` names ONE model the winner, and that is an editorial judgement no
  // classifier makes. Absent by default, so the block below is skipped rather
  // than filled with a guess.
  const [w,pr,ev,why] = j.pick || [];
  // THE VERBATIM-QUOTE BLOCK IS GONE FROM THIS LEVEL, and it is not lost.
  //
  // It rendered the 12 quotes the API sent - grouped by document, so 6 blocks
  // - of the 64 reports `best_for/coding-agent` actually holds. A 6-of-64
  // slice with nothing on the page saying it was a slice. Every one of those
  // reports is now on the page of the model it was reported about, and this
  // page is the way to them.
  return `<div class="shell phead">${crumb([['Board','board'],['Best for','board:best'],[j.name,null]])}
    <h1>${esc(j.h1)}</h1><p class="sub">${esc(j.sub)}</p></div>
    ${j.pick ? sec('The pick','','',`<div class="defbox"><div class="l">${ev}</div>
      <p><b>${esc(w)}</b> at ${esc(pr)}.</p><p>${esc(why)}</p></div>`) : ''}
    ${sec('Every model reported working for this job','Who got this working',
      listIntro(j), ranked(j.rows,'jobmodel:'+j.slug) + orphanNote(j) + suppressedNote(j))}
    ${sec('Conditions that change the answer','Where the pick stops holding',
      'Most disagreements between engineers are condition mismatches rather than contradictions. These are the ones the reports keep naming.',conds(j.conds))}
    ${sec('Related','','',related(j.rel))}`;
}

function vCap(slug){
  const c = byS(DB.caps,slug); if(!c) return vBoard('cap');
  // The quote block left this page too - see `vJob` above for why. On
  // `capability/reasoning` it was 9 blocks of the 43 reports the page holds.
  return `<div class="shell phead">${crumb([['Board','board'],['Capabilities','board:cap'],[c.name,null]])}
    <h1>${esc(c.name)}</h1><p class="sub">A capability the board found engineers discussing. This page is
    the definition every model page resolves against, so a report about one model can be compared with a
    report about another.</p></div>
    ${sec('','','',`<div class="defbox"><div class="l">definition</div><p>${esc(c.d1)}</p><p>${esc(c.d2)}</p></div>`)}
    ${sec('What this is not','Three things filed elsewhere',
      'Capability boundaries exist so a disagreement is a disagreement rather than two people using one word for two things.',conds(c.nots))}
    ${sec('Models with evidence','Who has been reported doing this',
      listIntro(c), ranked(c.rows,'capmodel:'+c.slug) + orphanNote(c) + suppressedNote(c))}
    ${sec('Related','','',related(c.rel))}`;
}

/* ---------- the drill-down: one model, inside one category ---------- */

/** Every report the board holds for one model under one section.
 *
 * WHAT "EVERY" MEANS HERE, because the page says the word. Every non-declined
 * `board_entry` row for this (section, slug, model), grouped by source
 * document, newest document first. No cap: the 12-quote cap that produced the
 * category page's slice is gone from the API, so this list is the whole of
 * what the board holds.
 *
 * It is scoped to this category, not to this model. The model's whole corpus
 * across every job, capability and metric has its own page already, and the
 * link out says so rather than this page quietly meaning one and saying the
 * other.
 *
 * ONE REPORT IS ONE SOURCE DOCUMENT. `quotes()` groups on document id, so two
 * figures from one comment render as one block with both inside it - the same
 * rule the counts on the row above were built on, applied to what the reader
 * sees.
 */
function vModelIn(kind, item, key, crumbs){
  const row = (item.rows||[]).find(r => r.key === key);
  // AN UNKNOWN MODEL GOES BACK, rather than rendering a page about nothing. A
  // hand-typed or stale key is not evidence that nobody discussed this model.
  if(!row) return kind === 'job' ? vJob(item.slug) : vCap(item.slug);
  const qs = row.qs || [];
  const [,lbl] = stOf(row.s);
  // THE COUNTS, AND WHAT EACH ONE COUNTED. `row.e` already reads
  // "at least N reports, M voices"; the quote count joins it here because this
  // is the page where the difference between a report and a quote is visible
  // on the screen - one block, two quotes inside it.
  const counts = `${esc(row.e)} \u00b7 ${qs.length} quote${qs.length===1?'':'s'} \u00b7 ${esc(lbl)}`;
  // BEST FOR DROPS THE COMPLAINTS, AND A PAGE SAYING "EVERY REPORT" HAS TO
  // SAY SO. The filter is right - `best_for` claims suitability and a problem
  // report cannot support one - but until now it was silent, and an absence we
  // caused reading as one we found is rule 4 exactly. The count is distinct
  // documents, the same unit as the report count beside it, and the link goes
  // where those reports are shown in full.
  const hidden = row.hidden || 0;
  const hiddenNote = hidden ? `<p class="muted" style="margin-top:12px;max-width:74ch;line-height:1.6">
    <b>${hidden} report${hidden===1?'':'s'} of a problem</b> with this model on this job
    ${hidden===1?'is':'are'} not shown here. <b>Best for</b> lists evidence that a model suits a
    job, so a complaint cannot fill it \u2014 but the complaint exists and the board kept it.
    <a data-go="model:${esc(key)}">Read it on the model page \u2192</a></p>` : '';
  const empty = `<p class="muted" style="padding:8px 0">The board holds no readable report for this
    model under this ${kind === 'job' ? 'job' : 'capability'}. That is what the board has, not a page
    that failed to load.</p>`;
  return `<div class="shell phead">${crumb(crumbs)}
    <h1>${esc(row.m)} on ${esc(item.name)}</h1>
    <p class="sub">Every report the board holds for this model under this
    ${kind === 'job' ? 'job' : 'capability'}: ${counts}. One report is one source document, so two
    quotes from one comment are one report. The report count is a floor \u2014 an open vocabulary can
    name one section two ways until the duplicates are merged.</p>
    ${hiddenNote}
    <p style="margin-top:14px"><a data-go="model:${esc(key)}">Everything said about
    ${esc(row.m)}, across every job, capability and metric \u2192</a></p></div>
    ${qs.length ? sec('Reports',reportsHeading(qs),'',quotes(qs)) : sec('Reports','','',empty)}`;
}

function vJobModel(slug, key){
  const j = byS(DB.jobs,slug); if(!j) return vBoard('best');
  return vModelIn('job', j, key,
    [['Board','board'],['Best for','board:best'],[j.name,'job:'+j.slug],
     [(j.rows.find(r=>r.key===key)||{}).m || key, null]]);
}

function vCapModel(slug, key){
  const c = byS(DB.caps,slug); if(!c) return vBoard('cap');
  return vModelIn('capability', c, key,
    [['Board','board'],['Capabilities','board:cap'],[c.name,'cap:'+c.slug],
     [(c.rows.find(r=>r.key===key)||{}).m || key, null]]);
}

/* ---------- metrics: the axis lists models, the leaf holds the figures -----
 *
 * WHY THIS CHANGED SHAPE, AND IT IS A MISSING LEVEL RATHER THAN A NEW DESIGN.
 *
 * Best-for and capabilities both go  board -> category -> MODEL -> reports.
 * Metrics went  board -> axis -> one flat table of every figure, and stopped.
 * `db.js` overwrote `commonFields`' model rows with the figure table, so the
 * model level was not merely unused here - it was discarded, which is why
 * `vJobModel` and `vCapModel` had no `vMetModel` beside them.
 *
 * WHAT A READER MET, on one axis, in one column, under one unit:
 *
 *     Claude Fable 5.1   $0.25 / MTok   stated   USD per 1M tokens
 *     Claude Fable 5.1   $50   / MTok   stated   USD per 1M tokens
 *
 * Those do not disagree. One is a cache read price and the other an output
 * price, and only the quote said so. Measured 2026-09-21 over the 269 figures
 * the board publishes, 34 (axis, model) cells hold two or more DIFFERENT
 * figures like that - the worst being six values over nineteen rows.
 *
 * AND 62 OF 84 AXES HOLD EXACTLY ONE MODEL. A table is a claim that its rows
 * are comparable; on three quarters of these pages there was nothing to
 * compare and the format was saying otherwise.
 *
 * So: the axis page lists each model ONCE, and the figures that were colliding
 * in one column move to that model's own page, where there is room to say what
 * each one measured.
 */

/** The figure table for one model on one axis.
 *
 * Every comment that was on the flat table applies here unchanged - the
 * grouping, the source list, the printed quote - because this IS that table,
 * scoped to one model instead of holding all of them at once.
 */
function figureRows(groups){
  // WHAT WAS MEASURED COMES FIRST, because on this page the model is fixed and
  // the sub-axis is the only thing telling two rows apart. On the old table it
  // did not exist as a column at all, which is the whole defect.
  const head = '<th>What was measured</th><th class="r">Figure</th><th>Basis</th><th>Unit</th>'
    + '<th>Reported by</th>';
  const body = groups.map((g)=>{
    const list = g.sources || [];
    const mixed = new Set(list.flatMap(s => s.bases || [])).size > 1;
    const one = (s) => {
      const href = safeHref(s.url);
      const ref = s.id ? ` title="${esc(s.id)}"` : '';
      const tag = mixed && (s.bases || []).length
        ? `<span class="qmeta">${esc(s.bases.join(' · '))}</span> `
        : '';
      const link = href
        ? `<a class="srclink" href="${esc(href)}"${ref} target="_blank" rel="noopener noreferrer">open the source</a>`
        : '<span class="nosrc" title="This document has no usable link.">no link recorded</span>';
      // THE QUOTE LEADS AND THE LINK FOLLOWS, and that ordering is the finding
      // rather than a preference. The words are what let a reader decide
      // whether $0.25 is an output price or a cache read price; "open the
      // source" is navigation, and it was set above the evidence in the
      // brighter of the two styles. So the quote comes first and carries the
      // readable colour, and the link sits under it dimmed.
      //
      // PRINTED, NOT PUT IN A `title`. A figure whose words are only in a
      // tooltip cannot be checked on a phone, and checking it is the point.
      const q = s.quote ? `<div class="figq">&ldquo;${esc(s.quote)}&rdquo;</div>` : '';
      return tag + q + link;
    };
    const many = mixed
      ? '<span class="qmeta">claimed by the provider and confirmed by a measurement</span>'
      : list.length > 1
        ? `<span class="qmeta">${list.length} reports state this figure</span>`
        : '';
    // WHY ONE ROW NOW HOLDS WORDINGS THAT LOOK DIFFERENT. `$0.25/M` and
    // `$0.25 per million output tokens` are one price, and splitting them
    // made fifteen agreeing reports read as four separate findings. Saying so
    // is what stops the merge looking like a figure that was tidied up.
    const spell = g.otherSpellings
      ? `<span class="qmeta">also written ${g.otherSpellings} other way${g.otherSpellings === 1 ? '' : 's'}, same figure</span>`
      : '';
    // "not stated" IS A VALUE AND IS RENDERED AS ONE (rule 6). 69 of the 113
    // `cost-per-token` figures name no side, and 14 of 15
    // `time-to-first-token` figures name nothing at all. Leaving the cell
    // blank would read as an oversight; filling it with the likely answer
    // would be the substitution that put a Terminal-bench figure on the
    // SWE-bench page. The evidence does not say, so the page does not say.
    const sub = g.subAxisDisputed
      ? '<span class="subax disp">reports disagree on what this measured</span>'
      : g.subAxis
        ? `<span class="subax">${esc(g.subAxis)}</span>`
        : '<span class="subax none">not stated</span>';
    return `<tr><td>${sub}</td><td class="r">${esc(g.value)}</td><td>${esc(g.basis)}</td>`
      + `<td>${esc(g.unit)}</td><td>${many}${spell}`
      + `${list.map(s=>`<div class="figsrc">${one(s)}</div>`).join('')}</td></tr>`;
  }).join('');
  return `<div class="tblwrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function vMet(slug){
  const m = byS(DB.mets,slug); if(!m) return vBoard('met');
  const rows = m.mrows || [];
  // ONE MODEL, ONE ROW. `ranked` is the same renderer the other two sections
  // use and it already allows for this one - "Empty on best-for and metric,
  // where there is no split".
  const list = rows.length
    ? ranked(rows, 'metmodel:' + m.slug)
    : `<p class="muted" style="padding:8px 0">The board holds no published figure on this axis.
       That is what the board has, not a page that failed to load.</p>`;
  // A COMPARISON IS ONLY CLAIMED WHERE ONE EXISTS. 62 of 84 axes hold a single
  // model, and a heading promising every model tracked, above one row,
  // overstates what was found.
  const only = rows.length === 1
    ? `<p class="muted" style="margin-top:10px;max-width:74ch;line-height:1.6;font-size:.9rem">
       <b>One model has a published figure on this axis.</b> This is an observation, not a
       ranking — there is nothing here to compare it against yet.</p>`
    : '';
  // SAID, NOT ASSUMED. Two writers spelling one benchmark two ways produce
  // two slugs, because the extractor is required to copy the name character
  // for character - that rule is what stops a Terminal-bench figure being
  // filed as SWE-bench. The spellings are folded here and the fold is
  // declared, so a reader who searched for the other one knows where it went.
  const alsoSpelled = (m.spelledAlso || []).length
    ? `<p class="muted" style="margin-top:8px;max-width:74ch;line-height:1.6;font-size:.9rem">
       Also written ${m.spelledAlso.map(x=>`<code>${esc(x)}</code>`).join(', ')} in the evidence.
       Those are the same axis and their figures are on this page &mdash; only the spelling differed.</p>`
    : '';
  return `<div class="shell phead">${crumb([['Board','board'],['Metrics','board:met'],[m.name,null]])}
    <h1>${esc(m.name)}</h1>${alsoSpelled}<p class="sub">An axis the board found figures for. Open a model to see every
    figure recorded for it here, what each one measured, and the words it came from — an output price
    and a cache-read price can share a unit without being the same measurement.</p></div>
    ${sec('','','',`<div class="defbox"><div class="l">unit · ${esc(m.unit)}</div><p>${esc(m.d1)}</p><p>${esc(m.d2)}</p></div>`)}
    ${sec('The number’s limits','What this metric cannot tell you',
      'Four things that change the figure and never appear beside it.',conds(m.lim))}
    ${sec('Models with figures on this axis','Who has been measured',
      listIntro(m), list + only)}
    ${sec('Related','','',related(m.rel))}`;
}

/** One model's figures on one axis - the level metrics never had. */
function vMetModel(slug, key){
  const m = byS(DB.mets,slug); if(!m) return vBoard('met');
  const row = (m.mrows||[]).find(r => r.key === key);
  // AN UNKNOWN MODEL GOES BACK to the axis, rather than rendering a page about
  // nothing. Same reasoning as `vModelIn`: a stale key is not evidence that
  // nobody measured this model.
  if(!row) return vMet(slug);
  const groups = (m.groups||[]).filter(g => (g.modelKey || '') === key);
  const named = groups.filter(g => g.subAxis).length;
  // RULE 7: THE FIGURE TRAVELS WITH ITS DENOMINATOR. "3 of 7 say what they
  // measured" is a different statement from "3 say what they measured", and
  // this page exists because the missing four are the problem.
  const coverage = groups.length
    ? `<p class="muted" style="margin-top:10px;max-width:74ch;line-height:1.6;font-size:.9rem">
       <b>${named} of ${groups.length} figure${groups.length===1?'':'s'}</b> say what they measured, in
       their own words. The rest are recorded as <b>not stated</b> — the evidence did not say which
       side of the axis it was on, and filing them under the likely one would be a guess wearing a
       label.</p>`
    : '';
  const empty = `<p class="muted" style="padding:8px 0">The board holds no published figure for this
    model on this axis.</p>`;
  return `<div class="shell phead">${crumb([['Board','board'],['Metrics','board:met'],
      [m.name,'metric:'+m.slug],[row.m,null]])}
    <h1>${esc(row.m)} on ${esc(m.name)}</h1>
    <p class="sub">Every figure the board publishes for this model on this axis: ${esc(row.e)}. Each is
    copied as the text wrote it, beside the words it came from. A stated figure and a reported one are
    different facts from different sources, so they sit side by side rather than being averaged.</p>
    <p style="margin-top:14px"><a data-go="model:${esc(key)}">Everything said about
    ${esc(row.m)}, across every job, capability and metric →</a></p></div>
    ${groups.length ? sec('Recorded figures','What was measured, and what it came to',
      'Two figures under one unit are not necessarily two answers to one question. Where the evidence names what it measured, that name is copied here; where it does not, the row says so.',
      figureRows(groups) + coverage) : sec('Recorded figures','','',empty)}
    ${sec('Related','','',related(m.rel))}`;
}

function vBlogs(){
  return `<div class="shell phead">${crumb([['Blogs',null]])}
    <h1>What we found while building the board</h1>
    <p class="sub">Not model reviews. Working notes from the engineers who built the pipeline — what broke,
    what the measurements said, and where our own assumptions turned out to be wrong. Every figure carries
    the population it was measured on, and every claim links to the evidence behind it.</p></div>
    <div class="shell sec"><div class="postlist">${DB.posts.length ? DB.posts.map(p=>
      `<div class="pcard${p.feat?' feat':''}" data-go="post:${esc(p.slug)}"><span class="tag">${esc(p.tag)}</span>
        <h3>${esc(p.title)}</h3><p>${esc(p.dek)}</p><p class="by">${esc(p.by)}</p></div>`).join('') : '<p class="muted" style="padding:8px 0">No posts yet.</p>'}</div>
      <p class="muted" style="margin-top:24px;max-width:70ch;line-height:1.6;font-size:.94rem">Posts are
      written against the board's own corpus. A post may cover one model, several, a job, a capability, or a
      change somebody noticed before a vendor announced it — and every figure in one is a bookmark into the
      evidence it came from.</p></div>`;
}

function vPost(slug){
  const p = byS(DB.posts,slug); if(!p) return vBlogs();
  const body = p.body.map(([t,v])=>{
    if(t==='h2') return `<h2>${esc(v)}</h2>`;
    if(t==='ul') return '<ul>'+v.map(li=>`<li>${esc(li)}</li>`).join('')+'</ul>';
    if(t==='quote') return `<blockquote>${esc(v)}</blockquote>`;
    return '<p>'+esc(v).replace(/\{E(\d+)\}/g,(m,n)=>`<span class="bm" data-ev="${n}">E${n}</span>`)+'</p>';
  }).join('');
  const ev = p.ev.map(([n,q,src])=>`<div class="evrow" id="ev${n}"><span class="id">E${n}</span>
    <div><q>${esc(q)}</q><span class="src">${esc(src)}</span></div><u>open evidence →</u></div>`).join('');
  return `<div class="shell phead">${crumb([['Blogs','blogs'],[p.title.slice(0,42)+'…',null]])}
    <h1>${esc(p.title)}</h1></div>
    <div class="shell"><div class="artmeta">${p.meta.map(m=>`<span>${m}</span>`).join('')}</div>
      <article class="article"><p class="lead">${p.lead}</p>${body}</article>
      <div class="evpanel" id="evidence"><h3>Evidence behind this post</h3>
        <p class="n">Every figure above is a bookmark into one of these. Demo data in this build — in
        production each row opens the stored quote with its verified offset and a link to the source.</p>
        ${ev}</div>
      ${related(p.rel)}
    </div>`;
}
export { vBoard, vJob, vCap, vMet, vJobModel, vCapModel, vMetModel, vBlogs, vPost }
