// Board + blogs view builders, ported verbatim from the SEO demo.
// They return HTML strings; BoardView renders them and wires clicks to the router.
// `./db.js` WITH THE EXTENSION, so `node` can load this file directly and a
// test can render the board instead of reading its source. Vite resolves an
// explicit extension unchanged; node will not resolve one that is missing, and
// every one of the 28 tests over this file was a string search for that
// reason. A defect in WHERE a card lands is not visible in the source text
// (#431), so the render has to be executable.
import { DB } from './db.js'
import { goAttrs } from './links.js'
import { nameIndex, nameKey, namePattern, shortName } from './modelnames.js'
import { sourceName } from '../sourceName.js'

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
// THE BOARD'S FRESHNESS LINE: two dates, never merged (see components/Freshness.jsx).
function freshLine() {
  const f = DB.freshness
  return f ? datesLine(f.updated_at, f.newest_report_at) : ''
}

// THE SAME LINE FOR ONE SECTION, OR ONE MODEL WITHIN IT, from the dates the
// board payload carries per section and per model. Nothing when undated.
function datesLine(updated, newest) {
  if (!updated) return ''
  const day = (iso) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  const tail = newest
    ? ` · newest report written <time datetime="${esc(newest)}">${day(newest)}</time>`
    : ''
  return `<p class="freshness dim">Updated <time datetime="${esc(updated)}">${day(updated)}</time>${tail}</p>`
}

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
  return '<p class="crumb">'+parts.map(([t,h])=>h?`<a${goAttrs(h)}>${esc(t)}</a>`:t).join('<i>/</i>')+'</p>';
}
function ranked(rows, route, level){
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
  //
  // THE GROUP BOUNDARY IS DRAWN WHERE THE RULE ACTS. Rows carrying `g` arrive
  // in `board_sections`' three groups, and a heading opens each one, so the
  // reader sees the threshold rather than inferring it from the order. Rows
  // without `g` (metric) render as they always did.
  const counts = {};
  rows.forEach(r => { if(r.g) counts[r.g] = (counts[r.g]||0) + 1; });
  let open = null;
  return '<div class="ranked">'+rows.map((r)=>{
    const [cls,lbl]=stOf(r.s);
    // A ROW THAT OPENS SOMEWHERE IS A LINK (SEO item 3): an <a> with a real
    // href, so a crawler can follow it and Ctrl-click opens it. One that opens
    // nothing stays a <div> - an <a> with no destination is not a link.
    // THE READABLE ID IN THE ADDRESS (`r.slug`), the key only as a fallback.
    const go = route && r.key ? goAttrs(`${route}:${r.slug || r.key}`) : '';
    const tag = go ? 'a' : 'div';
    // THE SPLIT IS ITS OWN LINE, not more words inside `.st`. That span
    // already carries two counts and a state label, and `.right` is
    // `white-space:nowrap` - a fourth clause in it would push the row wider
    // than a phone. Empty on metric, where there is no split.
    const sp = r.sp ? `<span class="split">${esc(r.sp)}</span>` : '';
    const head = r.g && r.g !== open ? groupHead(r.g, counts[r.g], level) : '';
    open = r.g || open;
    return `${head}<${tag} class="rank${r.dim?' dim':''}${go?' open':''}"${go}><span class="n">${go?'›':'·'}</span>
      <div><b>${esc(r.m)}</b><span class="vend">${esc(r.v)}</span><p>${esc(r.d)}</p></div>
      <div class="right"><span class="price">${esc(r.p)}</span><span class="st ${cls}">${esc(r.e)} · ${esc(lbl)}</span>${sp}</div></${tag}>`;
  }).join('')+'</div>';
}

/** The three group headings, in the words the intro line uses for them.
 *
 * Keyed on `board_sections`' GROUP_ORDER. An unknown key renders its own name
 * rather than nothing, so a fourth group added upstream shows up as a heading
 * somebody has to name instead of vanishing into the one above it. */
const GROUPS = {
  working: ['Reported working', 'at least one report of it working'],
  neutral: ['Only neutral reports', 'nobody reported it working or failing'],
  problems: ['Reported problems', 'reports of it failing, none of it working'],
};
// A REAL HEADING (SEO item 4, 2026-10-09). This was `<p role="heading"
// aria-level="3">`: a screen reader heard a heading and nothing that reads the
// tag tree did, so the page's main structure was invisible to it. `level` is
// the page's outline, passed by each caller and never defaulted: 2 where the
// list sits straight under the page's <h1> (jobs, capabilities), 3 where it
// sits inside a section that already has an <h2> (metrics). The look is
// unchanged - `.rank-group` neutralises the global heading styles.
function groupHead(g, n, level){
  const [title, gloss] = GROUPS[g] || [g, ''];
  return `<h${level} class="rank-group"><b>${esc(title)}</b>
    <span>${n} model${n===1?'':'s'}${gloss ? ` · ${esc(gloss)}` : ''}</span></h${level}>`;
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
  const head = `${n} model${n===1?'':'s'}, named in ≥${rep} report${rep===1?'':'s'}`
    + ` by ${voi} voice${voi===1?'':'s'}.`;
  // ⚠ THE ORDERING SENTENCE IS LOAD-BEARING. It said "ordered by report count,
  //   which is a count and not a score" until 2026-09-25, and that stopped
  //   being true when the first sort key became a threshold on a polarity
  //   label: a judgement, not a count. So it states the rule instead.
  //
  //   Ordering by POSITIVE COUNT was weighed and is still refused: it put
  //   Claude Sonnet 5 (+2 −6) at #1 on `instruction-following` and answers
  //   "who does this best", which is a merit ranking whatever it is counted
  //   from. The groups answer the narrower question "has anyone reported this
  //   working?", and the last clause is what keeps that honest: Claude Opus 5
  //   heads that page on 1 positive and 11 negatives, and the sentence has to
  //   be true of that row.
  //
  //   An older payload with no groups keeps the old sentence, which is true of
  //   it.
  if(!(item.rows || []).some(r => r.g)){
    return `${head} Ordered by report count, which is a count and not a score.${split}`
      + ` Open one to read every report it holds.`;
  }
  // THE FIRST GROUP'S ORDER IS DESCRIBED IN WORDS, NEVER AS A FORMULA OR A
  //   NUMBER. `board_sections` orders it by a Wilson lower bound it does not
  //   emit (z in contract/board_ordering.yaml); this sentence is what a reader
  //   gets instead, and "the same record" is deliberate: at these sample sizes
  //   three of three still sits above seven of ten, so a line claiming that few
  //   reports always lose to many would be false.
  return `${head} Listed in three groups: models with at least one report of it working,`
    + ` then models with only neutral reports, then models with reports of problems and`
    + ` none of it working. Within the first group, models whose reports more`
    + ` consistently say it worked come first, and a record built on few reports counts`
    + ` for less than the same record on many, so two reports of it working, with none`
    + ` against, sit below six of six. The other two groups are ordered by report count.`
    + ` No score is shown: each row shows its counts. A model enters the first group on a`
    + ` single positive report, however many problem reports it also has. Positive and`
    + ` negative are the extractor’s reading of each quote, so one mislabelled report`
    + ` can move a model.${split} Open one to read every report it holds.`;
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
// `suppressedNote` WAS HERE, naming the models `best_for` dropped entirely
// because every report they had on a job was a problem report. Nothing is
// dropped any more - those models are the third group - so there is nothing
// for it to say (2026-09-25).
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
      // THE PLATFORM'S NAME, read off the link, in place of "open the source"
      // on every quote; the old words stay as the accessible label.
      ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer" aria-label="open the source on ${esc(sourceName(href))}">${esc(sourceName(href))} ↗</a>`
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
    // NO INTERNAL ID IN THE CITATION. `g.src` is our database key
    // ("devto:4796515") - meaningless to a reader, and the link beside it
    // already names the platform and opens the post. It still groups quotes
    // from one post above; it is just not printed.
    return `<div class="qb${anyNeg?' neg':''}">${many}${body}<cite>${esc(g.who)} · ${cite}</cite></div>`;
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
  return '<div class="related">'+list.map(([h,t])=>`<a${goAttrs(h)}>${esc(t)}</a>`).join('')+'</div>';
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
function card(x, route, note){
  const [cls,lbl]=stOf(x.st);
  // No text, no empty paragraph: a job card is the name and its counts.
  const body = x.card ? `<p>${esc(x.card)}</p>` : '';
  // `note` is a short line about where the card was filed, never about the
  // evidence (heading boxes, 2026-10-14).
  const filed = note ? `<p class="filed-by">${esc(note)}</p>` : '';
  return `<a class="icard"${goAttrs(`${route}:${x.slug}`)}><b>${esc(x.name)}</b>${body}${filed}
    <div class="meta"><span class="${cls}">${esc(x.ev)} · ${esc(lbl)}</span><span>${esc(x.vol)}</span></div></a>`;
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
  return `<a class="icard"${goAttrs(`metric:${x.slug}`)}><b>${esc(x.name)}</b><p>${esc(x.card)}</p>
    <div class="meta"><span>unit · ${esc(x.unit)}</span><span>${esc(who)}</span></div></a>`;
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
//
// ⚠ IT RETURNS A BLOCK AND SPLICES NOTHING, AND THAT IS THE WHOLE OF #431.
//   This used to return `</div>…<div class="igrid">` - closing the caller's
//   grid and opening one nothing ever closed. The grid a card landed in was
//   then whichever heading had opened one LAST, so an ungrouped leaf ranking
//   below the first parent was drawn inside that parent's grid, under its
//   heading. Every one of the 69 ungrouped leaves rendered that way and none
//   at the top level: `instruction-following` (38 reports, rank 2 of 215) read
//   as belonging to "Reasoning and maths", and the last heading in each
//   section absorbed the tail - 35 cards under a "Writing and language" that
//   printed its own, smaller, leaf count directly above them.
//
//   A heading that swallows leaves it does not own is the one thing a parent
//   must never look like, so the markup is now well-formed by construction:
//   this emits a heading and `groupedGrid` wraps each RUN of cards in its own
//   `.igrid`. Nothing here opens an element it does not close.
function parentHead(g){
  // The id is the parent's slug, so a link can open the board at a group
  // (`/board?tab=cap#parent-software-engineering`, the landing hero's chip).
  return `<div class="phead-row" id="parent-${esc(g.parent)}"><div class="parent-h">
    <h3>${esc(g.name)}</h3><span>${g.leaves} ${g.leaves===1?'leaf':'leaves'}</span></div>
    <p>Grouped for reading. Each of these is its own measurement — nothing here is
    merged, and there is no total for the group.</p></div>`;
}

//: HOW MANY LEAVES A HEADING SHOWS BEFORE THE REST ARE FOLDED.
//
// ⚠ GROUPING DID NOT SHORTEN THIS PAGE AND WAS NEVER GOING TO. Every leaf
//   still draws: capability renders 199 cards under 8 headings, metric 112
//   under 6, and the biggest single heading holds 33 and 50. The headings made
//   the list navigable and made it EIGHT ROWS LONGER.
//
// The obvious fix is to make a heading clickable, and it is refused: behind a
// click the leaves exist only for a reader who already suspected they were
// there, which is the reader who does not need them. The one who reads the
// heading and moves on sees a category — a merge, which is the one thing a
// parent must never look like.
//
// So the leaves stay on the page and the TAIL folds. Six is enough to show
// what kind of thing is under a heading and short enough that eight headings
// fit on a screen. The fold says how many it is hiding, never just "more".
const LEAF_PREVIEW = 6;

/** Cards in a grid of their own, or nothing at all when there are none.

    EVERY RUN OF CARDS GETS ITS OWN `.igrid`, rather than one grid the headings
    cut holes in. An empty run emits NO element: an `.igrid` with no children
    still takes its `gap` and would leave a 12px hole under a heading. */
const gridBlock = (cards) => cards ? `<div class="igrid">${cards}</div>` : '';

/** One section, leaves under their headings, ungrouped leaves in their own rank.

    ⚠ AN UNGROUPED LEAF IS NOT THE LAST HEADING'S (#431). Consecutive ungrouped
      leaves are collected into a run and emitted as their OWN grid, outside
      every heading - which is what "interleave by rank with no heading" meant
      and what the previous splice could not express. A leaf with `parent: null`
      is not an unfiled leaf waiting for a heading; it is a leaf ruled to sit
      beside the headings, and 37 capability and 32 metric slugs are that
      deliberately (2026-09-23). Rendering them under the nearest heading above
      is the same error as merging them into it, arrived at by punctuation. */
function groupedGrid(groups, flat, draw){
  // NO GROUPS MEANS RENDER AS BEFORE. An older payload carries no `grouped`,
  // and a board that silently showed nothing would be worse than one that
  // shows what it always did.
  if(!groups || !groups.length) return gridBlock(flat.map(draw).join(''));
  const out = [];
  let run = [];
  const flushRun = () => { if(run.length){ out.push(gridBlock(run.join(''))); run = []; } };
  for(const g of groups){
    if(g.kind !== 'parent'){ run.push(draw(g.leaf)); continue; }
    // THE RUN CLOSES BEFORE THE HEADING OPENS. Otherwise the leaves standing
    // in their own rank would be swept under the heading that follows them,
    // which is the same defect as the one above it, facing the other way.
    flushRun();
    const hidden = g.children.length - LEAF_PREVIEW;
    // ⚠ `hidden="until-found"`, NOT `hidden`, AND THE DIFFERENCE IS THE WHOLE
    //   CLAIM. Plain `hidden` resolves to `display:none`, which removes the
    //   tail from FIND-IN-PAGE and from the ACCESSIBILITY TREE — so a comment
    //   promising those two while the CSS says `display:none` is promising
    //   the opposite of what ships. `until-found` keeps the tail folded,
    //   lets Ctrl+F match inside it, and makes the browser reveal it and fire
    //   `beforematch`. Where it is unsupported it degrades to plain `hidden`,
    //   which is no worse than having no fold at all.
    //
    //   `board.css` must NOT set `display:none` on this element: the UA rule
    //   for `[hidden=until-found]` is `content-visibility:hidden`, and an
    //   author `display:none` overrides it and takes the feature away. Nor
    //   `display:contents`, which generates no box for `content-visibility`
    //   to apply to. Tested in `test_the_board_renders_its_parents.py`.
    const shown = g.children.slice(0, LEAF_PREVIEW).map(draw).join('');
    if(hidden <= 0){ out.push(parentHead(g) + gridBlock(shown)); continue; }
    const rest = g.children.slice(LEAF_PREVIEW).map(draw).join('');
    const id = `leaves-${esc(g.parent)}`;
    // THE TAIL AND ITS BUTTON STAY INSIDE THIS HEADING'S GRID, which is what
    // their `grid-column:1 / -1` is for. They belong to this parent; an
    // ungrouped leaf does not, and that is the distinction the splice lost.
    out.push(parentHead(g) + gridBlock(shown
      + `<div class="leaf-rest" id="${id}" data-rest="${esc(g.parent)}"
              hidden="until-found">${rest}</div>`
      // NAMES THE COUNT, NOT "MORE". "+27 more" is a number a reader can
      // decide on; "more" is a promise they have to spend a click to price.
      //
      // `aria-expanded` and `aria-controls` because without them a screen
      // reader announces the label and nothing else — not that this is a
      // disclosure, and not what it opens.
      + `<p class="leaf-fold"><button type="button" data-expand="${esc(g.parent)}"
           aria-expanded="false" aria-controls="${id}">
         Show the other ${hidden} under ${esc(g.name)}</button></p>`));
  }
  flushRun();
  return out.join('');
}

/* ---------- heading boxes (2026-10-14) ----------
 *
 * A TAB WITH HUNDREDS OF LEAVES SHOWS ITS HEADINGS FIRST, AS BOXES, and a box
 * opens its leaves. Capabilities had 736 leaves on the local copy that day, and
 * a list that long is not something a reader chooses from.
 *
 * A BOX IS STILL A WAY TO READ THE LIST, NOT A MEASUREMENT. It carries a count
 * of LEAVES - the only number a parent may carry (contract/slug_parents.yaml) -
 * and never a sum of reports or voices. The page a box opens says so in words,
 * because a thing you can click into reads as a category.
 *
 * NOT-YET-FILED LEAVES GET A BOX OF THEIR OWN, labelled as exactly that. They
 * are not dropped (rule 4: an absence we caused must say so) and they are not
 * filed under a heading invented to hold them (no `other` parent). */
const BOXED = {
  // JOBS TOO, the same day: 341 job leaves on the local copy, none under a
  // heading until then. Metrics keep their in-list headings for now.
  best: { groups: () => DB.jobGroups, flat: () => DB.jobs, draw: (j, note) => card(j, 'job', note),
          one: 'job', many: 'jobs', tab: 'Jobs' },
  cap: { groups: () => DB.capGroups, flat: () => DB.caps, draw: (c, note) => card(c, 'cap', note),
         one: 'capability', many: 'capabilities', tab: 'Capabilities' },
};
const UNFILED = 'unfiled';
const UNFILED_NAME = 'Not yet under a heading';

function boxParts(tab){
  const B = BOXED[tab];
  const groups = B.groups() || [];
  return { B, parents: groups.filter(g => g.kind === 'parent'),
           loose: groups.filter(g => g.kind !== 'parent').map(g => g.leaf) };
}

function hbox(tab, key, name, leaves, B, extra){
  const n = leaves.length;
  const shown = leaves.slice(0, 4).map(l => `<li>${esc(l.name)}</li>`).join('');
  const more = n > 4 ? `<li class="more">and ${n - 4} more</li>` : '';
  return `<a class="hbox${extra || ''}"${goAttrs(`group:${tab}:${key}`)}>
    <h3>${esc(name)}</h3><span class="hbox-n">${n} ${n === 1 ? B.one : B.many}</span>
    <ul>${shown}${more}</ul><span class="hbox-go">Open</span></a>`;
}

function boxGrid(tab){
  const { B, parents, loose } = boxParts(tab);
  // AN OLDER PAYLOAD CARRIES NO HEADINGS: render the flat list it always did,
  // rather than a page of no boxes.
  if(!parents.length) return gridBlock(B.flat().map(B.draw).join(''));
  return `<div class="hboxes">${parents.map(g => hbox(tab, g.parent, g.name, g.children, B)).join('')}
    ${loose.length ? hbox(tab, UNFILED, UNFILED_NAME, loose, B, ' hbox-unfiled') : ''}</div>`;
}

/** What the box grid covers, computed from what it will draw. */
function boxNote(tab){
  const { B, parents, loose } = boxParts(tab);
  if(!parents.length) return '';
  const filed = parents.reduce((t, g) => t + g.children.length, 0);
  return `<p class="axisdiv"><b>${parents.length} headings over ${filed} of ${filed + loose.length} ${B.many}.</b>
    Open a heading to see its ${B.many}.${loose.length ? ` The other ${loose.length} are not yet under a
    heading and have a box of their own.` : ''} A heading is a way to read the list, not a claim
    that what is under it is one thing.</p>`;
}

/** One heading's leaves, at full width, every one of them. */
function vGroup(tab, key, pane){
  const { B, parents, loose } = boxParts(tab);
  const g = key === UNFILED
    ? (loose.length ? { name: UNFILED_NAME, children: loose } : null)
    : parents.find(p => p.parent === key);
  if(!g) return null;
  const n = g.children.length;
  const lead = key === UNFILED
    ? `The extractor named these and nobody has filed them under a heading yet. They are shown
       here rather than left out, and each is its own ${B.one}.`
    : `Grouped for reading. Each of these ${n} ${n === 1 ? B.one : B.many} is its own measurement,
       nothing here is merged, and there is no total for the heading.`;
  // A LEAF THE EXTRACTOR FILED HERE SAYS SO. The contract's filings were
  // read by a person; the extractor's are a proposal until somebody does.
  const byX = g.byExtractor || new Set();
  const grid = gridBlock(g.children.map(c => byX.has(c.slug)
    ? B.draw(c, 'Filed here by the extractor, not yet reviewed') : B.draw(c)).join(''));
  const xNote = byX.size ? `<p class="sub">${byX.size} of these ${byX.size === 1 ? 'was' : 'were'} filed
    here by the extractor and nobody has reviewed ${byX.size === 1 ? 'it' : 'them'} yet; ${byX.size === 1 ? 'it is' : 'they are'} marked.</p>` : '';
  return `<div class="shell phead">${crumb([['Board','board'],[B.tab,`board:${tab}`],[g.name,null]])}
    <h1>${esc(g.name)}</h1>${freshLine()}
    <p class="sub">${lead}</p>${xNote}
    <p class="backline"><a${goAttrs(`board:${tab}`)}>All ${esc(B.tab.toLowerCase())} headings</a></p></div>
    <div class="shell">${pane.side ? `<div class="jobbody"><div class="joblist">${grid}</div>${pane.side}</div>` : grid}</div>`;
}

/** The heading a leaf is filed under on a boxed tab, for its breadcrumb. */
function groupOf(tab, slug){
  if(!BOXED[tab]) return null;
  const { parents, loose } = boxParts(tab);
  const g = parents.find(p => p.children.some(c => c.slug === slug));
  if(g) return [g.name, `group:${tab}:${g.parent}`];
  return loose.some(l => l.slug === slug) ? [UNFILED_NAME, `group:${tab}:${UNFILED}`] : null;
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
function vBoard(tab, group){
  tab = tab||'best';
  const empty = '<p class="muted" style="padding:8px 0">Nothing here yet.</p>';
  // ⚠ THE PANE NO LONGER WRAPS `grid` IN AN `.igrid` (#431). Each builder
  //   emits its own grids, so a heading can sit BETWEEN two of them instead of
  //   inside one it has to cut open. Anything added here that returns bare
  //   cards must wrap them in `gridBlock` or they will render as a column.
  // ONE SHORT HEADING PER TAB, in the words people search for (2026-10-05).
  //   Kept beside the panes rather than inside them, so each pane still opens
  //   on its intro.
  const TAB_H = {best:'Best AI model for each job', cap:'What each AI model can do, as reported',
    met:'AI model performance and API pricing in engineer discussions'};
  const panes = {
    best: {intro:'Jobs engineers named when they said what they were running a model for. Each opens a page listing every model reported on that job. Problem reports are shown, not filtered.',
      // The ordering statement sits BESIDE the cards: one rule for every job
      // page, stated once where the pages are chosen (see orderPanel).
      side: orderPanel('job'),
      // BOXES, NOT A LIST (2026-10-14), as on the Capabilities tab.
      note: boxNote('best'),
      grid: DB.jobs.length ? boxGrid('best') : empty},
    cap: {intro:'A capability means one thing across every model page. These are the definitions the board rules by — written so an answer engine can quote them, and so two claims can be compared without arguing about words.',
      // BOXES, NOT A LIST (2026-10-14): the headings first, a box opens one.
      note: boxNote('cap'),
      // Same rule, same place, as the Jobs tab (2026-09-28).
      side: orderPanel('capability'),
      grid: DB.caps.length ? boxGrid('cap') : empty},
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
  // ONE HEADING'S PAGE. An unknown heading says so above the boxes rather
  // than quietly showing the boxes as if the link had worked (rule 12).
  let missing = '';
  if(group && BOXED[tab]){
    const page = vGroup(tab, group, p);
    if(page) return page;
    missing = `<p class="withheld">There is no heading called “${esc(group)}” here. These are the
      headings there are.</p>`;
  }
  const note = missing + (p.note || '');
  // THE H1 NAMES WHAT THE PAGE IS, in the words people search for (2026-10-05);
  //   the "Board" tag above it keeps the page's own name, styled like the
  //   landing page's Board badge so the two read as one place.
  return `<div class="shell phead">${crumb([['Board',null]])}
    <span class="go-badge go-board page-tag">Board</span>
    <h1>AI models compared by job, capability and metric</h1>${freshLine()}
    <p class="sub">Three ways into the same evidence. <b>Jobs</b> lists what was reported on a job.
    <b>Capabilities</b> defines what a claim means, so a claim on one model page can be compared with a
    claim on another. <b>Metrics</b> are the axes, and what each one refuses to average.</p></div>
    <div class="shell">
      <div class="tabs" role="tablist">
        <button role="tab" aria-selected="${tab==='best'}" data-tab="best">Jobs</button>
        <button role="tab" aria-selected="${tab==='cap'}" data-tab="cap">Capabilities</button>
        <button role="tab" aria-selected="${tab==='met'}" data-tab="met">Metrics</button>
      </div>
      <h2 class="tab-h">${TAB_H[tab]}</h2>
      <p class="muted" style="max-width:70ch;margin-bottom:20px;line-height:1.6">${p.intro}</p>
      ${note}
      ${p.side ? `<div class="jobbody"><div class="joblist">${p.grid}</div>${p.side}</div>` : p.grid}
    </div>`;
}

/** One line of figures under a job's heading: the evidence, counted.
 *
 * Models, reports (a floor, so ≥), voices, and how many models sit in each of
 * the three groups. Only groups that exist are named, so a page with no neutral
 * model does not print "0 only neutral". */
function statLine(j){
  const rows = j.rows || [];
  if(!rows.length) return '';
  const n = rows.length, rep = j.repTotal, voi = j.voiTotal;
  const by = {};
  rows.forEach(r => { if(r.g) by[r.g] = (by[r.g] || 0) + 1; });
  const groups = [['working','reported working'],['neutral','only neutral'],['problems','reported problems']]
    .filter(([k]) => by[k]).map(([k, label]) => `${by[k]} ${label}`);
  return `<p class="statline"><span>${n} model${n===1?'':'s'} · ≥${rep} report${rep===1?'':'s'}`
    + ` · ${voi} voice${voi===1?'':'s'}</span>${groups.length ? `<span>${groups.join(' · ')}</span>` : ''}</p>`;
}

/** How every job's or capability's list is ordered, ONCE, beside the cards on
 * its tab.
 *
 * It sat in a side column on every job page, identical on all 98, and read as
 * part of each job (2026-09-28 review); capability pages carried the same rule
 * as a paragraph above the list. It is one rule for every page, so it is
 * stated once where the pages are chosen, and each page keeps the one sentence
 * rule 3 requires of it - `orderLine` - with a link back here.
 *
 * ⚠ EVERY SENTENCE HERE IS LOAD-BEARING, AND SHORTER IS THE ONLY LICENCE TAKEN.
 *   The order in words and "no score is shown" are rule 3's conditions (#472);
 *   the single-positive clause is the one the order has to be true of (Claude
 *   Opus 5 heads a working group on 1 positive and 11 negatives); the
 *   extractor's-reading clause is rule 2's disclosure; the floor and the
 *   both-counted note keep the counts honest (rule 7). */
function orderPanel(noun){
  return `<aside class="jobaside">
      <h3>How each ${noun}’s list is ordered</h3>
      <p>Three groups: models with at least one report of it working, then models with only
      neutral reports, then models with reports of problems and none of it working.</p>
      <p>Within the first group, models whose reports more consistently say it worked come
      first, and a record built on few reports counts for less than the same record on many.
      The other two groups are ordered by report count.</p>
      <p>No score is shown: each row shows its counts. A model enters the first group on a
      single positive report, however many problem reports it also has.</p>
      <p class="fine">Positive and negative are the extractor’s reading of each quote, so one
      mislabelled report can move a model. A report that says both is counted under each.
      Report counts are floors (≥).</p>
      <p class="fine">Open a ${noun}, then a model, to read every report it holds.</p>
    </aside>`;
}

/** The ONE sentence a job page must carry about its own order (rule 3, #472:
 *  "the page says in words what the order rewards"). The full statement is on
 *  the Jobs tab; this is not a summary of it that may drift, it is the part the
 *  rule requires on the page itself. */
function orderLine(tab){
  return `<p class="orderline">Models with a report of it working come first, those whose
    reports more consistently say it worked ahead; then only-neutral, then problems only.
    No score is shown. <a${goAttrs(`board:${tab}`)}>How this list is ordered</a></p>`;
}

/** "What counts here" is the extractor's `definition`, LABELLED as its counting
 *  rule. It was rendered as the page's description, and it is not one: the
 *  extractor is told to write the test a report has to meet. Below the list,
 *  because it is the fine print of how rows got onto it. */
function jobRule(j){
  if(!j.rule) return '';
  return `<div class="shell jobrule"><h2>What counts here</h2><p>${esc(j.rule)}</p>
    <p class="fine">The extractor’s counting rule: the test a report had to meet to be filed
    under this job. It is not a description of the job.</p></div>`;
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
  // THE PAGE SHAPE (2026-09-28): a full-width lead saying what the job IS, one
  // line of figures, one sentence on the order, then the list at full width.
  // The full ordering statement is on the Jobs tab beside the cards, once,
  // rather than in a side column repeated on all 98 pages. What stays here is
  // what rule 3 (as amended, #472) requires of THIS page: the words saying what
  // its order rewards.
  //
  // THREE KINDS OF TEXT, KEPT APART:
  //   the job        `about`, hand-written (contract/job_about.yaml), or nothing
  //   the evidence   the stat line, the group headings, each row's counts
  //   the rules      the order line, and "What counts here" below the list
  const head = groupOf('best', j.slug);
  return `<div class="shell phead jobhead">${crumb([['Board','board'],['Jobs','board:best'],
    ...(head ? [head] : []),[j.name,null]])}
    <h1>${esc(j.h1)}</h1>${datesLine(j.freshUpdated, j.freshNewest)}
    ${j.about ? `<p class="lead">${esc(j.about)}</p>` : ''}
    ${statLine(j)}
    ${j.rows && j.rows.length ? orderLine('best') : ''}</div>
    ${j.pick ? sec('The pick','','',`<div class="defbox"><div class="l">${ev}</div>
      <p><b>${esc(w)}</b> at ${esc(pr)}.</p><p>${esc(why)}</p></div>`) : ''}
    <div class="shell">${ranked(j.rows,'jobmodel:'+j.slug, 2) + orphanNote(j)}</div>
    ${jobRule(j)}
    ${sec('Conditions that change the answer','Where the pick stops holding',
      'Most disagreements between engineers are condition mismatches rather than contradictions. These are the ones the reports keep naming.',conds(j.conds))}
    ${sec('Related','','',related(j.rel))}`;
}

function vCap(slug){
  const c = byS(DB.caps,slug); if(!c) return vBoard('cap');
  // The quote block left this page too - see `vJob` above for why. On
  // `capability/reasoning` it was 9 blocks of the 43 reports the page holds.
  //
  // THE JOB PAGE'S SHAPE (2026-09-28): the definition as the lead, one line of
  // figures, one sentence on the order, then the list at full width. The
  // subtitle that was identical on all 297 pages is on the Capabilities tab
  // already, and the ordering paragraph that sat above the list is stated once
  // beside the cards there (`orderPanel`).
  //
  // THE LEAD IS WHAT THE CAPABILITY IS, THEN ITS DEFINITION, LABELLED. The
  // hand-written `about` (contract/capability_about.yaml) says what it is; the
  // definition is the rule every model page resolves against, so unlike a
  // job's counting rule it stays at the top rather than in the fine print. With
  // no `about`, the definition is the lead on its own.
  const head = groupOf('cap', c.slug);
  return `<div class="shell phead jobhead">${crumb([['Board','board'],['Capabilities','board:cap'],
    ...(head ? [head] : []),[c.name,null]])}
    <h1>${esc(c.name)}</h1>${datesLine(c.freshUpdated, c.freshNewest)}
    ${c.about ? `<p class="lead">${esc(c.about)}</p>` : ''}
    ${c.d1 ? `<p class="deflabel">Definition</p><p class="${c.about ? 'defline' : 'lead'}">${esc(c.d1)}</p>` : ''}
    ${c.d2 ? `<p class="lead">${esc(c.d2)}</p>` : ''}
    ${statLine(c)}
    ${c.rows && c.rows.length ? orderLine('cap') + splitNote(c) : ''}</div>
    ${sec('What this is not','Three things filed elsewhere',
      'Capability boundaries exist so a disagreement is a disagreement rather than two people using one word for two things.',conds(c.nots))}
    <div class="shell">${ranked(c.rows,'capmodel:'+c.slug, 2) + orphanNote(c)}</div>
    ${sec('Related','','',related(c.rel))}`;
}

/** WHAT `both` MEANS, said once, on a page whose rows carry a split. It was a
 *  clause of `listIntro`'s paragraph; the paragraph is gone from this page and
 *  the clause is not, because a row reading "+2 −1 (1 both)" does not add up
 *  without it. */
function splitNote(item){
  if(!(item.rows || []).some(r => r.sp)) return '';
  return `<p class="orderline">A report that says both is counted under each, and the row says so.</p>`;
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
  // THE SPLIT RIDES WITH THE COUNTS. Nothing is filtered from this page any
  // more - `best_for` hid its problem reports until 2026-09-25 and this page
  // said how many - so the honest line is the row's own positive and negative
  // counts, the same ones the category page ordered it by.
  const split = row.sp ? ` · ${esc(row.sp)}` : '';
  const empty = `<p class="muted" style="padding:8px 0">The board holds no readable report for this
    model under this ${kind === 'job' ? 'job' : 'capability'}. That is what the board has, not a page
    that failed to load.</p>`;
  return `<div class="shell phead">${crumb(crumbs)}
    <h1>${esc(row.m)} on ${esc(item.name)}</h1>${datesLine(row.freshUpdated, row.freshNewest)}
    <p class="sub">Every report the board holds for this model under this
    ${kind === 'job' ? 'job' : 'capability'}: ${counts}${split}. One report is one source document, so two
    quotes from one comment are one report. The report count is a floor \u2014 an open vocabulary can
    name one section two ways until the duplicates are merged.</p>
    <p style="margin-top:14px"><a${goAttrs(`model:${key}`)}>Everything said about
    ${esc(row.m)}, across every job, capability and metric \u2192</a></p></div>
    ${qs.length ? sec('Reports',reportsHeading(qs),'',quotes(qs)) : sec('Reports','','',empty)}`;
}

function vJobModel(slug, key){
  const j = byS(DB.jobs,slug); if(!j) return vBoard('best');
  return vModelIn('job', j, key,
    [['Board','board'],['Jobs','board:best'],[j.name,'job:'+j.slug],
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
      const tag = mixed && (s.bases || []).length
        ? `<span class="qmeta">${esc(s.bases.join(' · '))}</span> `
        : '';
      const link = href
        ? `<a class="srclink" href="${esc(href)}" target="_blank" rel="noopener noreferrer" aria-label="open the source on ${esc(sourceName(href))}">${esc(sourceName(href))} ↗</a>`
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
    ? ranked(rows, 'metmodel:' + m.slug, 3)
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
    <h1>${esc(m.name)}</h1>${datesLine(m.freshUpdated, m.freshNewest)}${alsoSpelled}<p class="sub">An axis the board found figures for. Open a model to see every
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
    <h1>${esc(row.m)} on ${esc(m.name)}</h1>${datesLine(row.freshUpdated, row.freshNewest)}
    <p class="sub">Every figure the board publishes for this model on this axis: ${esc(row.e)}. Each is
    copied as the text wrote it, beside the words it came from. A stated figure and a reported one are
    different facts from different sources, so they sit side by side rather than being averaged.</p>
    <p style="margin-top:14px"><a${goAttrs(`model:${key}`)}>Everything said about
    ${esc(row.m)}, across every job, capability and metric →</a></p></div>
    ${groups.length ? sec('Recorded figures','What was measured, and what it came to',
      'Two figures under one unit are not necessarily two answers to one question. Where the evidence names what it measured, that name is copied here; where it does not, the row says so.',
      figureRows(groups) + coverage) : sec('Recorded figures','','',empty)}
    ${sec('Related','','',related(m.rel))}`;
}

// ── Blogs: the essay layout from the standalone HTML drafts ─────────────────
//
// Everything sits under `.essay` with its own `--es-*` palette (board.css), so
// the drafts look like the HTML pages the team reviewed without the essay CSS
// leaking into the rest of the app — the HTML used `--bg`/`--text`/`--accent`,
// which are app tokens here.

/** WHERE A POST STANDS IN REVIEW, read from the store rather than from the
 *  file. The generator stamps every post `status: draft`, and these pages used
 *  to print that - "draft" and "not yet reviewed by a person" - on posts a
 *  person had approved (found 2026-10-14, 26 approved posts all labelled draft).
 *  `published_at` is the latest approval (judge/blog_store.py:published), and
 *  `review` is the state Admin's preview carries. APPROVED IS NOT PUBLISHED:
 *  nothing derived has gone outside the team (contract/sources.yaml,
 *  `derived_publication: false`), and the wording keeps saying so. */
function reviewOf(p){
  if(p.published_at || p.review === 'approved') return 'approved';
  return p.review || 'draft';
}
const day = (ts) => ts ? String(ts).slice(0, 10) : '';

// THE PAGES OFFERED UNDER THE INDEX. Only the post directory since 2026-10-19
// (anooj): the live and reference pages - where engineers disagree, this week,
// the daily quiz, glossary, known issues, answers - are off the blog page and
// unrouted (web/src/routes/Blogs.jsx). Their code stays in web/src/blogs/ and
// judge/blog_live.py, so restoring one is a line here and one there.
const LIVE = [
  ['live:directory', 'Directory', 'Every post, by the model it covers, its topic, its title or its date.', 'Reference'],
];
// A POST'S PICTURE, OR NOTHING. An AI picture is an inline JPEG/PNG/WebP; a
// FIGURE DRAWN FOR THE POST (2026-10-16) is an inline SVG, shown through <img>
// so it can run no script. Any other src draws nothing - never a placeholder.
function pictureSrc(v){
  const src = String((v && v.src) || '');
  const ok = v && v.kind === 'figure'
    ? /^data:image\/svg\+xml;base64,[A-Za-z0-9+/=]+$/.test(src)
    : /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(src);
  return ok ? src : '';
}
function coverOf(p){
  if(p.cover && pictureSrc(p.cover)) return p.cover;
  const b = (p.body || []).find(x => x[0] === 'image' && pictureSrc(x[1]));
  return b ? b[1] : null;
}

// THE BLOGS LANDING, LAID OUT LIKE A RESEARCH BLOG (2026-10-16, team ask:
// "like bair.berkeley.edu/blog - the design with pictures, not the content").
// One centred column, newest first: the title, a byline with the format, date
// and reading time, the post's own picture full width, the dek, and a link on.
// Ten to a page. A post with no picture shows none - nothing stands in.
const BLOGS_PER_PAGE = 10;
function vBlogs(){
  const meta = DB.postsMeta || { reason: null, skipped: [] };
  // THREE STATES (rule 4): drafts, a configured backend with none, and a
  // backend that is not set up to serve them. The last two must not read alike.
  const empty = meta.reason
    ? `<p class="es-empty">${esc(meta.reason)}</p>`
    : '<p class="es-empty">No posts yet.</p>';
  const skipped = (meta.skipped || []).length
    ? `<p class="es-empty">Could not be read: ${
        meta.skipped.map(x=>`${esc(x.file)} (${esc(x.why)})`).join('; ')}</p>` : '';
  const when = p => String(((p.provenance || {}).generated_at) || '');
  const all = [...DB.posts].sort((a, b) => when(b).localeCompare(when(a)) || String(a.title).localeCompare(String(b.title)));
  const pages = Math.max(1, Math.ceil(all.length / BLOGS_PER_PAGE));
  let page = 1;
  try { page = Math.min(pages, Math.max(1, parseInt(new URLSearchParams(location.search).get('page') || '1', 10) || 1)); } catch { page = 1; }
  const shown = all.slice((page - 1) * BLOGS_PER_PAGE, page * BLOGS_PER_PAGE);
  const cards = shown.map(p => {
    const c = coverOf(p);
    const draft = reviewOf(p) !== 'approved' ? '<span class="bl-draft">draft</span>' : '';
    return `<article class="bl-post">
      <h2 class="bl-title"><a ${goAttrs(`post:${p.slug}`)}>${esc(p.title)}</a></h2>
      <div class="bl-by"><span class="bl-kind">${esc(p.kicker || p.tag)}</span><span>${esc((p.meta || [])[0] || '')}</span>${
        p.read ? `<span>${esc(p.read)} min read</span>` : ''}${draft}</div>
      ${c ? `<a class="bl-fig${c.kind === 'figure' ? ' drawn' : ''}" ${goAttrs(`post:${p.slug}`)}><img src="${pictureSrc(c)}" alt="${esc(c.alt || '')}" loading="lazy" decoding="async"></a>` : ''}
      <p class="bl-ex">${esc(p.dek || '')}</p>
      <a class="bl-more" ${goAttrs(`post:${p.slug}`)}>Continue reading &rarr;</a>
    </article>`;
  }).join('');
  const pager = pages > 1 ? `<nav class="bl-pager" aria-label="More posts">${
    page > 1 ? `<a href="/blogs${page - 1 > 1 ? `?page=${page - 1}` : ''}">&larr; Newer</a>` : '<span></span>'}<span class="bl-pg">Page ${page} of ${pages}</span>${
    page < pages ? `<a href="/blogs?page=${page + 1}">Older &rarr;</a>` : '<span></span>'}</nav>` : '';
  return `<div class="essay"><div class="es-wrap">
    <header class="es-hub"><span class="go-badge go-blogs page-tag">Blogs</span>
      <h1>How AI models behave in production</h1>
      <p class="es-dek">Long-form engineering essays on running frontier models in real systems — the failure
      modes, the architecture that contains them, and the economics that decide what is worth building.</p></header>
    ${DB.posts.length ? `<div class="es-draft">${DB.posts.every(x=>reviewOf(x)==='approved')
      ? '<b>Approved by the team, not yet published outside it.</b>'
      : '<b>Drafts for team review.</b>'} Written by a language model - since 16 October 2026 by Claude Code -
      from engineers' public reports and published research, and checked in code: every quote is matched against
      its source text, and every figure against the source or the price registry. Pictures are labelled with how
      they were made.${DB.posts.every(x=>reviewOf(x)==='approved')
      ? ' A person on the team read each post and approved it before it appeared here.'
      : ' Posts marked draft have not been approved by a person yet.'}</div>
      <a class="bl-dir"${goAttrs('live:directory')}>Find a post: all ${DB.posts.length} by model, topic or title &rarr;</a>
      <div class="bl-list">${cards}</div>${pager}` : empty}
    ${skipped}
    <nav class="lv-explore lv-in-essay" aria-label="Live pages">${LIVE.map(([go, t, d, k]) =>
      `<a class="lv-tile"${goAttrs(go)}><span class="lv-kicker">${k}</span><b>${t}</b><span>${d}</span></a>`).join('')}</nav>
  </div></div>`;
}

// Inline text: escaped first, then the generator's marks — `code`, **bold**
// and «verbatim fragment». Nothing else is markup. Posts show NO evidence
// bookmarks (team decision, 2026-10-01); an {En} left in an older draft file is
// dropped rather than printed.
// QUOTE CREDITS (re-reviewed 2026-10-13): a post carries `cite` (fragment ->
// number) and `sources` (platform, who, what, link). Set by vPost while it
// renders, keyed by the ESCAPED fragment because essayText matches after esc().
let CITE = null, SRC = null;
function citeMark(q){
  const n = CITE && CITE[q];
  return n ? `<sup class="es-cite"><a href="#es-src-${n}" aria-label="Source ${n}">${n}</a></sup>` : '';
}
function essayText(v){
  return esc(v)
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>')
    .replace(/«([^»]+)»/g,(m,q)=>`<q class="es-iq">${q}</q>${citeMark(q)}`)
    .replace(/\{E\d+\}/g,'');
}

// THE PLATFORM'S OWN POST (re-reviewed 2026-10-13). Rebuilt here from the
// fields the generator fetched, never from HTML a file supplied, and only for
// URLs of the expected shape - anything else draws nothing. The platform's
// script turns the blockquote into the post, with its author and date; a
// deleted post disappears from the page with it. (embeds.js loads the scripts.)
function embedBlock(v){
  if(!v) return '';
  const cap = `<figcaption>${v.caption ? `<span class="cap">${essayText(v.caption)}</span>` : ''}
    <span class="prov">Embedded from ${v.platform === 'x' ? 'X' : 'Reddit'}. The author, text and date are shown by
    ${v.platform === 'x' ? 'X' : 'Reddit'}; if the post is deleted it disappears here too.</span></figcaption>`;
  if(v.platform === 'reddit'){
    const u = String(v.url || ''), m = u.match(/^https:\/\/www\.reddit\.com\/r\/(\w+)\/comments\/\w+/);
    const author = /^[\w-]{1,40}$/.test(v.author || '') ? v.author : '';
    if(!m) return '';
    return `<figure class="es-embed es-embed-reddit"><blockquote class="reddit-embed-bq" style="height:316px">
      <a href="${esc(u)}">${esc(v.title || 'View this post on Reddit')}</a><br> by
      ${author ? `<a href="https://www.reddit.com/user/${esc(author)}/">u/${esc(author)}</a>` : 'a Reddit user'} in
      <a href="https://www.reddit.com/r/${esc(m[1])}/">${esc(m[1])}</a></blockquote>${cap}</figure>`;
  }
  if(v.platform === 'x'){
    const m = String(v.url || '').match(/^https:\/\/(?:x|twitter)\.com\/(\w+)\/status\/(\d+)/);
    if(!m) return '';
    return `<figure class="es-embed es-embed-x"><blockquote class="twitter-tweet" data-theme="dark" data-dnt="true">
      <a href="https://twitter.com/${esc(m[1])}/status/${esc(m[2])}">View this post on X</a></blockquote>${cap}</figure>`;
  }
  return '';
}

// THE SOURCE LIST: one numbered line per quoted post, as cited in the text.
function sourcesBlock(p){
  const s = (p.sources || []).filter(x => /^https:\/\//.test(x.url || ''));
  if(!s.length) return '';
  return `<section class="es-sources"><h2>Sources</h2><ol>${s.map(x =>
    `<li id="es-src-${esc(x.n)}"><span class="plat">${esc(x.platform)}</span>
      <a href="${esc(x.url)}" rel="nofollow noopener" target="_blank">${esc(x.what)}</a>${x.who ? ` by ${esc(x.who)}` : ''}${x.posted ? ` · ${esc(x.posted)}` : ''}</li>`).join('')}</ol>
    <p class="es-note">Every quote was matched to its source word for word, in code. Embedded posts are shown by their own platform.</p>${
    // arXiv's acknowledgement, attached by the server to every post that cites
    // an arXiv paper (judge/publication.py with_credits, 2026-10-19).
    p.acknowledgement ? `<p class="es-note es-ack">${esc(p.acknowledgement)}</p>` : ''}</section>`;
}

function routeBadge(r){
  const x = String(r||'').toLowerCase();
  const tone = x.includes('opus') ? 'p' : x.includes('sonnet') ? 'b'
    : (x.includes('haiku') || /\blow\b/.test(x)) ? 'g' : 'y';
  // `t-` prefix: a bare `b` collided with the decision tree's `.b` branch card.
  return `<span class="es-bdg t-${tone}">${esc(r)}</span>`;
}

function essayCode(src){
  // Comments dimmed, as in the HTML drafts. Escaped before the span is added.
  return esc(String(src||'').replace(/\s+$/,'')).split('\n').map(l=>{
    const k = l.indexOf('#'); return k >= 0 ? l.slice(0,k)+`<span class="c">${l.slice(k)}</span>` : l;
  }).join('\n');
}

function essayBlock([t,v]){
  if(t==='h2'){
    const h = typeof v === 'string' ? { text: v } : v;
    // The tree's question already sits in its root box, so its heading names
    // the block instead of printing the question twice.
    if (h.num === 'Decision tree') return `<h2${h.id?` id="es-${esc(h.id)}"`:''}>Decision tree</h2>`;
    return `<h2${h.id?` id="es-${esc(h.id)}"`:''}>${h.num?`<span class="num">${esc(h.num)}</span>`:''}${essayText(h.text)}</h2>`;
  }
  if(t==='h3') return `<h3>${esc(v)}</h3>`;
  if(t==='ul') return '<ul>'+v.map(li=>`<li>${essayText(li)}</li>`).join('')+'</ul>';
  // THE QUOTE BOX SAID ONLY "Engineer report", and a reader could not tell
  // whose words they were or why they were boxed (2026-10-06). It now says.
  if(t==='quote'){
    const n = CITE && CITE[esc(v)], src = n && SRC ? SRC[n] : null;
    return `<figure class="es-voice"><figcaption class="who">${src ? `${esc(src.platform)}${src.who ? ` · ${esc(src.who)}` : ''}` : 'An engineer, in their own words'}</figcaption>
    <blockquote>${esc(v)}</blockquote>
    <div class="src">${src ? `Copied exactly from <a href="${esc(src.url)}" rel="nofollow noopener" target="_blank">${esc(src.what)}</a>. Not the writer's words.`
      : "Copied exactly from a public engineering discussion this post was written from. Not the writer's words."}</div></figure>`;
  }
  if(t==='embed') return embedBlock(v);
  // The tag already says "Illustrative"; a label that opens with it would read twice.
  if(t==='code') return `<div class="es-codehead"><span class="es-illus">Illustrative</span>${esc(String(v.label||'').replace(/^\s*illustrative[\s:·-]*/i,'').replace(/^./,c=>c.toUpperCase()))}</div>
    <pre class="es-pre">${essayCode(v.source)}</pre>`;
  if(t==='table'){
    const matrix = v.kind === 'matrix', prices = v.kind === 'prices';
    const cell = (c,k,r) => {
      if(matrix && k===r.length-1) return `<td class="route">${routeBadge(c)}</td>`;
      if(prices && k>0) return `<td class="n">${esc(c)}</td>`;
      return `<td>${k===0?`<b>${essayText(c)}</b>`:essayText(c)}</td>`;
    };
    return `<div class="es-tbl"><table><thead><tr>${(v.cols||[]).map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead>
      <tbody>${(v.rows||[]).map(r=>`<tr>${r.map((c,k)=>cell(c,k,r)).join('')}</tr>`).join('')}</tbody></table></div>
      ${v.note?`<p class="es-note">${esc(v.note)}</p>`:''}`;
  }
  if(t==='tree') return `<div class="es-dtree"><div class="q">${essayText(v.question)}</div>
    <div class="br">${(v.branches||[]).map(b=>`<div class="b"><div class="cond">${essayText(b.condition)}</div>
      <div class="out">${essayText(b.outcome)}</div>${routeBadge(b.route)}</div>`).join('')}</div></div>`;
  // A TABLE, CHART OR DIAGRAM (generator, 2026-10-13), one per section at most.
  if(t==='visual') return visualBlock(v);
  // A GENERATED PICTURE (generator, 2026-10-13): always labelled as AI-made,
  // and only ever an inline JPEG/PNG/WebP - any other src is not drawn.
  if(t==='image'){
    const src = pictureSrc(v);
    if(!src) return '';
    const fig = v.kind === 'figure';
    return `<figure class="es-fig es-fig-image${fig ? ' es-drawn' : ''}${v.cover ? ' es-cover' : ''}"><img src="${src}" alt="${esc(v.alt || '')}" loading="lazy" decoding="async">
      <figcaption>${v.caption ? `${essayText(v.caption)} ` : ''}<span class="es-ai">${fig ? 'Figure drawn by Claude Code for this post' : 'AI-generated illustration'}</span></figcaption></figure>`;
  }
  // EVERY PARAGRAPH IN FULL (2026-10-13). Skim mode showed one line per
  // paragraph by default and read as an incomplete post, so it is gone. Posts
  // written before carry {text, skim}: the paragraph is shown, the line is not.
  const text = v && typeof v === 'object' ? v.text : v;
  const para = `<p class="es-para">${essayText(text)}</p>`;
  return para + linkCards(para);
}

// "READ THE ORIGINAL" (2026-10-14, team ask: let a reader go straight to the
// arXiv paper or dev.to article). One card per linked source, after the
// paragraph that first quotes it. Reddit and X never reach here: they are
// embedded by their platforms and never quoted, so they have no source line.
let CARDED = null;
const READ_AS = { 'arXiv': 'Read the paper on arXiv', 'dev.to': 'Read the article on dev.to',
  'an engineering blog': 'Read the original post', 'GitHub': 'Read it on GitHub',
  'Hacker News': 'Read the thread on Hacker News', 'Hugging Face': 'Read it on Hugging Face',
  'Medium': 'Read the article on Medium' };
function linkCards(html){
  if(!SRC || !CARDED) return '';
  const fresh = [...html.matchAll(/href="#es-src-(\d+)"/g)].map(m => Number(m[1]))
    .filter(n => { if(CARDED.has(n)) return false; CARDED.add(n); return /^https:\/\//.test((SRC[n] || {}).url || ''); });
  return fresh.map(n => { const s = SRC[n];
    const meta = [s.who ? `by ${esc(s.who)}` : '', s.posted ? esc(s.posted) : ''].filter(Boolean).join(' · ');
    return `<a class="es-linkcard" href="${esc(s.url)}" rel="nofollow noopener" target="_blank">
      <span class="plat">${esc(s.platform)}</span><span class="what">${esc(s.what)}</span>${meta ? `<span class="meta">${meta}</span>` : ''}
      <span class="go">${esc(READ_AS[s.platform] || 'Read the original')} →</span></a>`; }).join('');
}

// THE THREE VISUALS. Drawn as HTML and inline SVG from the post's own data:
// no image files, nothing fetched, and every chart value was checked against
// the sources by the generator before the post was written.
function visualBlock(v){
  if(!v || !v.kind) return '';
  const cap = v.caption ? `<figcaption>${essayText(v.caption)}</figcaption>` : '';
  if(v.kind === 'table'){
    return `<figure class="es-fig es-fig-table"><div class="es-tbl"><table><thead><tr>${(v.columns||[]).map(c=>`<th>${essayText(c)}</th>`).join('')}</tr></thead>
      <tbody>${(v.rows||[]).map(r=>`<tr>${r.map((c,k)=>`<td>${k===0?`<b>${essayText(c)}</b>`:essayText(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${cap}</figure>`;
  }
  if(v.kind === 'chart'){
    const bars = (v.bars||[]).filter(b => Number.isFinite(Number(b.value)));
    if(!bars.length) return '';
    const max = Math.max(...bars.map(b => Number(b.value))) || 1;
    const row = 30, labelW = 38, h = bars.length * row + 8;
    const fmt = n => { const x = Number(n); return Number.isInteger(x) ? x.toLocaleString('en-US') : String(x); };
    const svg = bars.map((b, i) => {
      const w = Math.max(0.5, (Number(b.value) / max) * (96 - labelW - 14));
      const y = i * row + 6;
      return `<text x="0" y="${y + 15}" class="lbl">${esc(String(b.label).replace(/[«»]/g,''))}</text>`
        + `<rect x="${labelW}%" y="${y + 3}" width="${w}%" height="18" rx="4" class="bar"/>`
        + `<text x="${labelW + w + 1}%" y="${y + 16}" class="val">${esc(fmt(b.value))}</text>`;
    }).join('');
    return `<figure class="es-fig es-fig-chart"><div class="unit">${esc(v.unit || '')}</div>
      <svg viewBox="0 0 100 ${h}" preserveAspectRatio="none" width="100%" height="${h}" role="img" aria-label="${esc(String(v.caption||'Chart').replace(/[«»]/g,''))}">${svg}</svg>${cap}</figure>`;
  }
  if(v.kind === 'diagram'){
    const steps = (v.steps||[]).map((st, i) => `<li><span class="n">${i + 1}</span><span>${essayText(st)}</span></li>`).join('');
    return `<figure class="es-fig es-fig-flow"><ol>${steps}</ol>${cap}</figure>`;
  }
  return '';
}

// ── per-format layouts (reworked 2026-10-06) ──────────────────────────────
//
// THE 2026-10-05 LAYOUTS CHANGED AN ACCENT AND A LABEL, AND THE PAGE STAYED ONE
// PAGE. Was, over the 12 drafts on 2026-10-06: 12 of 12 opened on the same
// "The short answer" box, 9 of 12 carried no layout at all (written before
// formats existed), and a "which one to pick" block - the matrix or the
// decision tree - closed 10 of them. Each layout now owns three things, built
// from data the post already holds and never from new prose:
//   open   what the reader meets first   (a log, a face-off, a receipt, a map)
//   tools  where the matrix and tree go  (top, mid or end - per format)
//   end    what the page closes on       (open questions, a checklist, cards)
const LAYOUTS = {
  report:    { label: 'Observation', lead: 'Bottom line',             tools: 'mid' },
  versus:    { label: 'Question',    lead: 'The split',               tools: 'top' },
  ledger:    { label: 'Cost line',   lead: 'Where the money goes',    tools: 'mid' },
  runbook:   { label: 'Step',        lead: 'Before you start',        tools: 'top' },
  blueprint: { label: 'Component',   lead: 'The pattern in one line', tools: 'end' },
  brief:     { label: 'Point',       lead: 'The verdict',             tools: 'top' },
  critique:  { label: 'Argument',    lead: 'The argument',            tools: 'mid' },
  // TOPIC POSTS (2026-10-16): general AI, from the blog's own harvest. A
  // synthesis opens on the terms a newcomer meets; an explainer closes on a quiz.
  synthesis: { label: 'Idea',        lead: 'In one line',             tools: 'end' },
  explainer: { label: 'Step',        lead: 'In one line',             tools: 'end' },
  // MORE TOPIC STYLES (2026-10-16): one interactive block each.
  mechanism: { label: 'Part',        lead: 'The short version',       tools: 'end' },
  myths:     { label: 'Reality',     lead: 'The short version',       tools: 'end' },
  radar:     { label: 'Signal',      lead: 'What is new',             tools: 'end' },
  debate:    { label: 'Claim',       lead: 'The question',            tools: 'end' },
  fieldguide:{ label: 'Rule',        lead: 'The one thing to know',   tools: 'end' },
  paper:     { label: 'Finding',     lead: 'The papers in one line',  tools: 'end' },
};
// Posts written before `layout` was exported carry their format in
// provenance; the first three carry only a kicker. A post matching none renders
// the plain page - visibly unstyled, never silently given some other format's.
const FORMAT_LAYOUT = { 'field-report': 'report', 'head-to-head': 'versus', 'cost-teardown': 'ledger',
  'migration-guide': 'runbook', 'architecture-pattern': 'blueprint', 'release-analysis': 'brief',
  'evaluation-critique': 'critique', 'topic-synthesis': 'synthesis', 'topic-explainer': 'explainer',
  'under-the-hood': 'mechanism', 'myth-vs-reality': 'myths', 'research-radar': 'radar', 'debate': 'debate',
  'field-guide': 'fieldguide', 'paper-walkthrough': 'paper' };
const KICKER_LAYOUT = { 'Model deep dive': 'report', 'Routing guide': 'versus', 'Capability analysis': 'brief' };
function layoutOf(p){
  if(LAYOUTS[p.layout]) return p.layout;
  return FORMAT_LAYOUT[(p.provenance || {}).format] || KICKER_LAYOUT[p.kicker] || null;
}

// The body as parts: sections, and the matrix, tree and price sheet lifted out
// so each layout can place them. Every post's body has this shape (2026-10-06).
function splitPost(body){
  const out = { pre: [], sections: [], matrix: null, tree: null, prices: null };
  let cur = null;
  for(let i = 0; i < body.length; i++){
    const [t, v] = body[i], nx = body[i + 1];
    if(t === 'h2' && v && v.num === 'Matrix' && nx && nx[0] === 'table'){ out.matrix = { head: v, table: nx[1] }; i++; cur = null; continue; }
    if(t === 'h2' && v && v.num === 'Decision tree' && nx && nx[0] === 'tree'){ out.tree = nx[1]; i++; cur = null; continue; }
    if(t === 'h3' && nx && nx[0] === 'table' && nx[1] && nx[1].kind === 'prices') continue;
    if(t === 'table' && v && v.kind === 'prices'){ out.prices = v; continue; }
    if(t === 'h2'){ cur = { head: typeof v === 'string' ? { text: v } : v, blocks: [] }; out.sections.push(cur); continue; }
    (cur ? cur.blocks : out.pre).push(body[i]);
  }
  return out;
}

const wordsIn = s => (String(s || '').replace(/<[^>]+>/g, ' ').match(/\S+/g) || []).length;
const pad2 = n => String(n).padStart(2, '0');

// THE POST'S OWN PRICE SHEET: registry list prices at generation, as the post
// printed them. A missing price stays "not published" (rule 6).
function sheetRows(prices){
  return prices ? (prices.rows || []).map(r => ({ name: String(r[0] || ''), pin: r[1], pout: r[2], cached: r[3] })) : [];
}
const nameRx = n => new RegExp(`(?<![\\w.\\-])${rxEsc(n)}(?![\\w\\-]|\\.\\d)`, 'i');
// EXACT NAME FIRST; else the ONE row whose name contains it as a whole phrase -
// a title's "Opus 5" is the sheet's "Claude Opus 5" (2026-10-08). nameRx will
// not match "Opus 5" inside "Opus 5.5", and two candidate rows match nothing:
// a price shown against the wrong model is worse than none.
const rowFor = (rows, name) => {
  const n = String(name || '').trim();
  const exact = rows.find(r => r.name.toLowerCase() === n.toLowerCase());
  if(exact || !n) return exact || null;
  const within = rows.filter(r => nameRx(n).test(r.name));
  return within.length === 1 ? within[0] : null;
};
const rowsIn = (rows, text) => rows.filter(r => r.name && nameRx(r.name).test(String(text || '')));
const perM = (v, side) => String(v || '').startsWith('$') ? `${esc(v)} ${side}` : `${side}put not published`;
function vsNames(p){
  const sp = p.special;
  if(sp && sp.type === 'picks') return [...new Set((sp.items || []).map(x => x.pick))];
  const m = String(p.title || '').split(':')[0].split(/\s+vs\.?\s+/i).map(s => s.trim()).filter(Boolean);
  return m.length === 2 ? m : [];
}

function sectionHtml(s, label, n, after = ''){
  const h = { ...s.head };
  if(label && /^\d+$/.test(h.num || '')) h.num = `${label} ${n}`;
  return essayBlock(['h2', h]) + after + s.blocks.map(essayBlock).join('');
}

// ── the tools: clickable versions of the matrix and the tree ──────────────
// CSS-only state (radio, checkbox, <details>), so BoardView needs no handler
// and nothing a reader clicks is sent anywhere.
let _mx = 0;
function matrixTable(m, filter){
  const v = m.table, rows = v.rows || [];
  const routes = [...new Set(rows.map(r => String(r[r.length - 1] || '').trim()))];
  // A pill per route only when routes are names; a route written as a sentence
  // made a wall of pills nobody could scan (2026-10-06).
  const can = filter && routes.length >= 2 && routes.length <= 4 && routes.every(r => r.length <= 32);
  const id = `es-mx${++_mx}`;
  const pills = can ? `<div class="es-pills" role="radiogroup" aria-label="Filter rows by route"><span>Show</span>
      <label><input type="radio" name="${id}" checked>All rows</label>${routes.map((r, k) =>
      `<label><input type="radio" name="${id}" class="f${k}">${esc(r)}</label>`).join('')}</div>` : '';
  // data-l carries the column name so a phone can show each row as a card,
  // every cell under its own label (board.css, max-width 640px).
  const col = k => esc((v.cols || [])[k] || '');
  const body = rows.map(r => `<tr class="g${routes.indexOf(String(r[r.length - 1] || '').trim())}">${r.map((c, k) =>
    k === r.length - 1 ? `<td class="route" data-l="${col(k)}">${routeBadge(c)}</td>`
      : `<td${k ? ` data-l="${col(k)}"` : ''}>${k === 0 ? `<b>${essayText(c)}</b>` : essayText(c)}</td>`).join('')}</tr>`).join('');
  return `<section class="es-mx"><h2 id="es-matrix">${essayText(m.head.text)}</h2>${pills}
    <div class="es-tbl"><table><thead><tr>${(v.cols || []).map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
    <tbody>${body}</tbody></table></div></section>`;
}
function matrixCards(m){
  return `<section class="es-mcards"><h2 id="es-matrix">${essayText(m.head.text)}</h2><div class="grid">${(m.table.rows || []).map(r =>
    `<div class="mc"><h4>${essayText(r[0])}</h4><p class="bad"><b>Breaks</b>${essayText(r[1])}</p>
      <p class="good"><b>Holds</b>${essayText(r[2])}</p><p class="rt"><b>Use</b>${routeBadge(r[3])}</p></div>`).join('')}</div></section>`;
}
function treeClick(tr, title){
  return `<section class="es-ctree"><div class="lbl">${esc(title)}</div><div class="q">${essayText(tr.question)}</div>
    <p class="hint">Open the branch that matches your situation.</p>${(tr.branches || []).map(b =>
    `<details class="br"><summary>${essayText(b.condition)}</summary><div class="out">${essayText(b.outcome)}</div>${routeBadge(b.route)}</details>`).join('')}</section>`;
}

// ── openings and endings, one pair per layout ─────────────────────────────
function leadBox(conf, p, cls = ''){
  return `<div class="es-open ${cls}"><div class="lbl">${esc(conf.lead)}</div><p>${essayText(p.lead)}</p></div>`;
}
function tocList(secs, cls, tag){
  return `<ol class="${cls}">${secs.map((s, i) => {
    const t = essayText(s.head.text);
    const k = `<span class="k">${tag(i + 1)}</span>`;
    return `<li>${s.head.id ? `<a data-toc="es-${esc(s.head.id)}">${k}<span>${t}</span></a>` : `${k}<span>${t}</span>`}</li>`;
  }).join('')}</ol>`;
}
function findingsCol(sp, status, title, cls){
  if(!sp || sp.type !== 'findings') return '';
  const it = (sp.items || []).filter(x => x.status === status);
  return `<section class="es-fcol ${cls}"><div class="lbl">${esc(title)}</div><ul>${it.length
    ? it.map(x => `<li>${essayText(x.finding)}</li>`).join('') : '<li class="none">None recorded.</li>'}</ul></section>`;
}
function faceoff(p, rows, asOf){
  const names = vsNames(p);
  if(names.length !== 2) return '';
  const sp = p.special && p.special.type === 'picks' ? p.special : null;
  const side = (n, k) => {
    const r = rowFor(rows, n);
    const picks = sp ? sp.items.filter(x => x.pick === n) : [];
    return `<div class="side s${k}"><div class="nm">${esc(n)}</div>${r
      ? `<div class="px"><span>${esc(r.pin)}</span><i>in</i><span>${esc(r.pout)}</span><i>out</i></div>
         <div class="unit">list price per 1M tokens${asOf ? ` · ${esc(asOf)}` : ''}</div>`
      : '<div class="unit">Not in this post\'s price sheet</div>'}${picks.length
      ? `<div class="when">Pick it when</div><ul>${picks.map(x => `<li>${essayText(x.when)}</li>`).join('')}</ul>` : ''}</div>`;
  };
  return `<section class="es-face">${side(names[0], 0)}<div class="vs">vs</div>${side(names[1], 1)}</section>`;
}
function receipt(p, rows, conf, asOf){
  const subj = rowsIn(rows, p.title);
  const show = subj.length ? subj : rows.slice(0, 1);
  const sp = p.special && p.special.type === 'drivers' ? p.special : null;
  return `<section class="es-receipt"><div class="lbl">The rate card</div>${show.length ? show.map(r =>
    `<div class="line"><b>${esc(r.name)}</b><span class="dots"></span><span>${perM(r.pin, 'in')}</span><span>${perM(r.pout, 'out')}</span>${
      String(r.cached || '').startsWith('$') ? `<span class="dim">${esc(r.cached)} cached</span>` : ''}</div>`).join('')
    : '<div class="line"><span class="dim">No list price in this post.</span></div>'}
    <div class="unit">Registry list prices per 1M tokens${asOf ? `, ${esc(asOf)}` : ''}.</div>${sp ? `<div class="lbl">On the bill</div><ol class="items">${sp.items.map((x, k) =>
    `<li><span class="k">${pad2(k + 1)}</span><span><b>${essayText(x.driver)}</b> ${essayText(x.mechanism)}</span></li>`).join('')}</ol>` : ''}
    <div class="es-open in"><div class="lbl">${esc(conf.lead)}</div><p>${essayText(p.lead)}</p></div></section>`;
}
function leverList(items){
  return `<section class="es-levers"><div class="lbl">Your levers</div><p class="hint">Tick each lever your system already pulls.</p>
    <ul>${items.map(x => `<li><label><input type="checkbox"><span><b>${essayText(x.name)}</b> ${essayText(x.lever)}</span></label></li>`).join('')}</ul>
    <div class="tally">Ticked <span class="ct"></span> of ${items.length}</div></section>`;
}
function layerMap(p, secs, conf){
  const sp = p.special && p.special.type === 'layers' ? p.special : null;
  const bands = sp
    ? sp.items.map((x, k) => `<details class="band" style="margin-left:${k * 12}px"><summary>${essayText(x.layer)}</summary>
        <p>${essayText(x.role)}</p><p class="fail"><b>Contains</b>${essayText(x.failure_contained)}</p></details>`).join('')
    : secs.map((s, k) => `<a class="band" style="margin-left:${k * 12}px" ${s.head.id ? `data-toc="es-${esc(s.head.id)}"` : ''}>${essayText(s.head.text)}</a>`).join('');
  return `<section class="es-map"><div class="lbl">The architecture${sp ? ' · open a layer' : ' · jump to a component'}</div>
    <div class="stack">${bands}</div><p class="cap"><b>${esc(conf.lead)}</b> ${essayText(p.lead)}</p></section>`;
}
function claimWall(sp){
  const cls = st => st === 'holds' ? 'ok' : st === 'partly holds' ? 'part' : 'none';
  return `<section class="es-claimw"><div class="es-pills" role="radiogroup" aria-label="Filter claims"><span>Show</span>
      <label><input type="radio" name="es-cl" checked>All claims</label>
      <label><input type="radio" name="es-cl" class="fo">Holds</label>
      <label><input type="radio" name="es-cl" class="fp">Partly holds</label>
      <label><input type="radio" name="es-cl" class="fn">Does not hold</label></div>
    <div class="grid">${sp.items.map(x => `<div class="cl c-${cls(x.status)}"><span class="stamp">${esc(x.status)}</span>
      <h4>${essayText(x.claim)}</h4><p>${essayText(x.finding)}</p></div>`).join('')}</div></section>`;
}
// THE GLOSSARY of a topic synthesis: the terms a newcomer meets, defined once.
function glossaryBox(sp){
  return `<section class="es-gloss"><div class="lbl">${esc(sp.title || 'Terms')}</div><dl>${sp.items.map(x =>
    `<div><dt>${essayText(x.term)}</dt><dd>${essayText(x.meaning)}</dd></div>`).join('')}</dl></section>`;
}
// THE QUIZ of an explainer. CSS-only state like the other tools: a radio per
// option, the right one marked in the markup, and the explanation shown once
// any option of that question is picked (board.css .es-quiz). Nothing a reader
// picks is sent anywhere or kept.
let _qz = 0;
function quizBox(sp){
  const id = `es-qz${++_qz}`;
  return `<section class="es-quiz"><div class="lbl">${esc(sp.title || 'Quiz')}</div>${sp.items.map((q, i) =>
    `<fieldset class="q"><legend><span class="n">${pad2(i + 1)}</span>${essayText(q.question)}</legend>${
      (q.options || []).map((o, k) => `<label class="opt ${k === q.answer ? 'right' : 'wrong'}">`
        + `<input type="radio" name="${id}-${i}"><span>${essayText(o)}</span></label>`).join('')}
      <p class="why"><b>Why:</b> ${essayText(q.explanation)}</p></fieldset>`).join('')}</section>`;
}
// A SPECIAL ITEM'S SOURCE: the paper's or post's own title and link, which
// export resolved from the writer's SOURCE number (generate_sample_blogs.py).
function refLink(it){
  const r = it && it.ref;
  if(!r || !/^https:\/\//.test(r.url || '')) return '';
  return `<a class="es-ref" href="${esc(r.url)}" rel="nofollow noopener" target="_blank">${esc(r.platform)} · ${esc(r.title)}</a>`;
}
// LAB (under the hood): steps to run, ticked off as you go.
function labBox(sp){
  return `<section class="es-levers es-lab"><div class="lbl">${esc(sp.title || 'Try it yourself')}</div><ol>${sp.items.map(x =>
    `<li><label><input type="checkbox"><span><b>${essayText(x.step)}</b> ${essayText(x.how)}`
    + `<em class="look">You should see: ${essayText(x.look_for)}</em></span></label></li>`).join('')}</ol>
    <div class="tally">Done <span class="ct"></span> of ${sp.items.length}</div></section>`;
}
// MYTHS: a card per belief; open it to see what the evidence says.
function mythCards(sp){
  const cls = v => v === 'true' ? 'ok' : v === 'partly true' ? 'part' : 'none';
  return `<section class="es-myths"><div class="lbl">${esc(sp.title || 'Myth or not')}</div>
    <p class="hint">Guess first, then open a card.</p><div class="grid">${sp.items.map(x =>
    `<details class="mc m-${cls(x.verdict)}"><summary><span class="q">${essayText(x.myth)}</span>`
    + `<span class="tap">Open</span></summary><span class="stamp">${esc(x.verdict)}</span>`
    + `<p>${essayText(x.reality)}</p></details>`).join('')}</div></section>`;
}
// RADAR: filter by stage; each item links to the paper or post it came from.
function radarList(sp){
  const stages = ['new idea', 'early results', 'in use'];
  const k = st => Math.max(0, stages.indexOf(st));
  return `<section class="es-radar"><div class="lbl">${esc(sp.title || 'On the radar')}</div>
    <div class="es-pills" role="radiogroup" aria-label="Filter by stage"><span>Show</span>
      <label><input type="radio" name="es-rd" checked>Everything</label>${stages.map((st, i) =>
      `<label><input type="radio" name="es-rd" class="f${i}">${esc(st)}</label>`).join('')}</div>
    <div class="grid">${sp.items.map(x => `<div class="rd s${k(x.stage)}"><span class="stage">${esc(x.stage)}</span>
      <h4>${essayText(x.item)}</h4><p>${essayText(x.what)}</p><p class="why">${essayText(x.why)}</p>${refLink(x)}</div>`).join('')}</div></section>`;
}
// DEBATE: the sides beside each other, each with where it breaks.
function sidesBox(sp){
  return `<section class="es-sides"><div class="lbl">${esc(sp.title || 'Two sides')}</div><div class="grid">${sp.items.map((x, i) =>
    `<div class="side"><span class="n">${String.fromCharCode(65 + i)}</span><h4>${essayText(x.side)}</h4>`
    + `<p>${essayText(x.case)}</p><details><summary>Where it breaks</summary><p>${essayText(x.weakness)}</p></details></div>`).join('')}</div></section>`;
}
// FIELD GUIDE: a checklist with a tally, like the runbook's.
function checklistBox(sp){
  return `<section class="es-levers"><div class="lbl">${esc(sp.title || 'Before you ship')}</div><ul>${sp.items.map(x =>
    `<li><label><input type="checkbox"><span><b>${essayText(x.check)}</b> ${essayText(x.why)}</span></label></li>`).join('')}</ul>
    <div class="tally">Checked <span class="ct"></span> of ${sp.items.length}</div></section>`;
}
// PAPER WALKTHROUGH: what was measured, under what setup, and by whom.
function resultsBox(sp){
  return `<section class="es-results"><div class="lbl">${esc(sp.title || 'What was measured')}</div>${sp.items.map(x =>
    `<div class="rs"><p class="r">${essayText(x.result)}</p><p class="set">${essayText(x.setup)}</p>${refLink(x)}</div>`).join('')}</section>`;
}
function probeList(sp){
  return `<section class="es-probe"><div class="lbl">${esc(sp.title || 'What the measures test')}</div>${sp.items.map(x =>
    `<details><summary><b>${essayText(x.measure)}</b><span>${essayText(x.tests)}</span></summary>
      <p><b>Misses</b>${essayText(x.misses)}</p></details>`).join('')}</section>`;
}

/* ---------- interactive posts, phase 1 (docs/proposals/interactive-blogs.md) ----------
 * OPT-IN PER POST: `"interactive": true`. Three things, none of them typed by the
 * model that wrote the post:
 *   entity links  a model's name links to its PUBLIC page (/catalog/model/...);
 *                 first mention per paragraph, longest name first, so "GPT-6.1
 *                 Sol Pro" is never split into "GPT-6.1 Sol" (rule 10: the whole
 *                 identifier). Every registry model, by its display name or its
 *                 vendor-dropped one - board/modelnames.js. "A vs B" links to
 *                 /compare with both.
 *   model cards   on hover or focus: list price, context, board entries - read
 *                 from /models when the page loads (DB.blogModels), so they are
 *                 today's figures, not the post's
 *   provenance    a verbatim «» fragment says it is quoted; a $ figure outside a
 *                 quote says it is the list price at generation (the generator
 *                 refuses any number found in neither the sources nor the price
 *                 sheet, which is what makes that sentence true)
 */
const rxEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// WHICH WRITTEN NAME MEANS WHICH MODEL: board/modelnames.js. Every model in the
// registry (DB.blogModels, loaded by routes/Blogs.jsx), under its display name
// and its vendor-dropped name ("Opus 5.5"), separators folded, and a name that
// fits two models linked to neither.
let _ents = null;
function entityIndex(){
  const ms = DB.blogModels || [];
  if(_ents && _ents.src === ms) return _ents;
  return (_ents = { src: ms, ...nameIndex(ms) });
}
// "A vs B", "A vs. B", "A versus B": one link to the comparison of the two.
const VS = '(\\s+(?:vs\\.?|versus)\\s+)';
const usd = v => v == null ? null : `$${Number(v) < 1 ? String(+Number(v).toFixed(4)) : Number(v).toFixed(2)}`;
function modelCard(m, text){
  // Rule 6: an absent figure says it is absent - never $0, never blank.
  const pin = usd(m.price_in), pout = usd(m.price_out);
  const price = pin && pout ? `${pin} in · ${pout} out per 1M tokens` : 'No list price published';
  const ctx = m.advertised_context
    ? `${Number(m.advertised_context).toLocaleString('en-US')}-token context` : 'Context window not published';
  const n = m.board && m.board.entries != null ? m.board.entries : null;
  const rep = n == null ? 'Board entries not counted' : `${n} board ${n === 1 ? 'entry' : 'entries'}`;
  const pop = `<span class="es-pop" role="tooltip"><b>${esc(shortName(m))}</b><span>${esc(price)}</span>`
    + `<span>${esc(ctx)}</span><span>${esc(rep)}</span>`;
  // THE PUBLIC MODEL PAGE (links.js `catmodel`), never `/models/*`, which is
  // behind the sign-in. A model is linked only when the catalog has its page
  // (DB.blogCatalogIds, from /model-catalog): 28 of 270 registry models had
  // none on 2026-10-19, and an internal id never does. Until that list loads,
  // or if it cannot, every name keeps its card and no link - a link that may
  // 404 is not drawn on the chance that it would not (rule 12).
  if(!hasPage(m)) return `<span class="es-ent" tabindex="0">${text}${pop}</span></span>`;
  return `<a class="es-ent" tabindex="0"${goAttrs(`catmodel:${m.canonical_id}`)}>${text}`
    + `${pop}<span class="go">Open the model page →</span></span></a>`;
}
const hasPage = m => Boolean(m.canonical_id && DB.blogCatalogIds && DB.blogCatalogIds.has(m.canonical_id));
/** "A vs B" as one link to /compare, when both are distinct models with public pages. */
function compareLink(a, b, text){
  return `<a class="es-vs"${goAttrs(`compare:${a.canonical_id},${b.canonical_id}`)}>${text}</a>`;
}
const QUOTE_TIP = 'Quoted verbatim from a practitioner report this post was written from';
// A MODEL THE POST PRICES BUT THE BOARD DOES NOT TRACK - GLM 5 in the
// DeepSeek post - had no card and nothing said why (rule 4). Its card says it
// is untracked, from the post's own price sheet. If the board's model list did
// not load, "untracked" would be a guess, so the card says the list is missing.
function sheetCard(r, text, asOf){
  const loaded = Array.isArray(DB.blogModels);
  const price = String(r.pin).startsWith('$') && String(r.pout).startsWith('$')
    ? `${r.pin} in · ${r.pout} out per 1M tokens${asOf ? ` (list price, ${asOf})` : ''}` : 'No list price published';
  return `<span class="es-ent off" tabindex="0">${text}<span class="es-pop" role="tooltip"><b>${esc(r.name)}</b>`
    + `<span>${esc(loaded ? 'Not in the model registry here: no reports are collected for it yet.'
      : 'The board model list did not load, so whether it is in the registry is unknown.')}</span>`
    + `<span>${esc(price)}</span></span></span>`;
}
function interactivize(html, p, rows = []){
  const { byKey, ambiguous, forms } = entityIndex();
  const asOf = String((p.provenance && p.provenance.generated_at) || '').slice(0, 10);
  // A price-sheet name the registry does not hold. NOT one the registry holds
  // twice: that model is tracked, the text just does not say which one, and
  // its card would wrongly say "not tracked".
  const extra = new Map(rows.map(r => [nameKey(r.name), r])
    .filter(([k]) => k.length >= 4 && !byKey.has(k) && !ambiguous.has(k)));
  const pat = namePattern([...forms, ...[...extra.values()].map(r => r.name)]);
  // A pair first, then a single name, in ONE pass, so a link is never drawn
  // inside another one.
  const rx = pat ? new RegExp(`(${pat})${VS}(${pat})|(${pat})`, 'gi') : null;
  const one = (m0) => {
    const k = nameKey(m0);
    if(seen.has(k) || !(byKey.has(k) || extra.has(k))) return m0;
    seen.add(k);
    return byKey.has(k) ? modelCard(byKey.get(k), m0) : sheetCard(extra.get(k), m0, asOf);
  };
  const priceTip = esc(`List price from the model registry when this post was generated`
    + `${asOf ? ` (${asOf})` : ''}. Hover the model name for today's price.`);
  // A <label> is skipped like a heading: a link inside a filter pill or a
  // checkbox would navigate instead of toggling.
  let inCode = 0, inLink = 0, inQ = 0, inHead = 0, inLabel = 0, seen = new Set();
  return html.split(/(<[^>]+>)/).map(seg=>{
    if(seg.startsWith('<')){
      const t = seg.toLowerCase();
      if(/^<(p|li|td|th)[\s>]/.test(t)) seen = new Set();
      if(/^<(code|pre)[\s>]/.test(t)) inCode++;
      else if(/^<\/(code|pre)>/.test(t)) inCode = Math.max(0, inCode - 1);
      else if(/^<a[\s>]/.test(t)) inLink++;
      else if(t.startsWith('</a')) inLink = Math.max(0, inLink - 1);
      else if(/^<h[1-4][\s>]/.test(t)) inHead++;
      else if(/^<\/h[1-4]>/.test(t)) inHead = Math.max(0, inHead - 1);
      else if(/^<label[\s>]/.test(t)) inLabel++;
      else if(t.startsWith('</label')) inLabel = Math.max(0, inLabel - 1);
      else if(/^<q[\s>]/.test(t)){
        inQ++;
        if(t.includes('es-iq')) return seg.replace('<q class="es-iq"', `<q class="es-iq" title="${QUOTE_TIP}"`);
      }
      else if(t.startsWith('</q')) inQ = Math.max(0, inQ - 1);
      return seg;
    }
    if(!seg || inCode || inLink || inHead || inLabel) return seg;
    let out = inQ ? seg : seg.replace(/\$\d[\d,]*(?:\.\d+)?/g,
      m=>`<span class="es-num" tabindex="0" title="${priceTip}">${m}</span>`);
    if(rx) out = out.replace(rx, (m0, a, mid, b, single)=>{
      if(single !== undefined) return one(single);
      const ma = byKey.get(nameKey(a)), mb = byKey.get(nameKey(b));
      // Every pair is linked, even after its names were linked once in the
      // paragraph: the comparison is a different page from either model's.
      if(ma && mb && ma !== mb && ma.canonical_id && mb.canonical_id){
        seen.add(nameKey(a)); seen.add(nameKey(b));
        return compareLink(ma, mb, m0);
      }
      return one(a) + mid + one(b);
    });
    return out;
  }).join('');
}

/* TWO ARRANGEMENTS PER FORMAT (2026-10-08): two head-to-heads had one page.
 * A post generated from now on records its own (`arrangement`, alternated per
 * format by the generator), so a reviewer's preview and the published page
 * agree. An older post alternates by its order among posts of its format. */
function arrangementOf(p, L){
  if(p.arrangement === 'a' || p.arrangement === 'b') return p.arrangement;
  if(!L) return 'a';
  const when = q => String((q.provenance || {}).generated_at || '');
  const same = (DB.posts || []).filter(q => layoutOf(q) === L)
    .sort((x, y) => when(x).localeCompare(when(y)) || String(x.slug).localeCompare(String(y.slug)));
  return same.findIndex(q => q.slug === p.slug) % 2 === 1 ? 'b' : 'a';
}
/** Both models' list prices on one line - the head-to-head B opening. */
function priceStrip(names, rows, asOf){
  if(names.length !== 2) return '';
  const cell = n => { const r = rowFor(rows, n);
    return `<div class="side"><b>${esc(n)}</b>${r ? `<span>${perM(r.pin, 'in')}</span><span>${perM(r.pout, 'out')}</span>`
      : '<span class="dim">no price in this post</span>'}</div>`; };
  return `<div class="es-pstrip">${cell(names[0])}<i>vs</i>${cell(names[1])}`
    + `<span class="unit">list price per 1M tokens${asOf ? ` · ${esc(asOf)}` : ''}</span></div>`;
}

function vPost(slug){
  const p = byS(DB.posts,slug); if(!p) return vBlogs();
  const L = layoutOf(p);
  const conf = L ? LAYOUTS[L] : { label: null, lead: 'In brief', tools: 'end' };
  // EVERY POST OPENS ON A PICTURE (2026-10-14): its cover, or - for a post
  // written before covers - its first generated picture, lifted out of its
  // section. A post with no picture opens without one; nothing stands in.
  let body = p.body || [], cover = p.cover || null;
  if(!cover){
    const k = body.findIndex(b => b[0] === 'image');
    if(k >= 0){ cover = body[k][1]; body = body.slice(0, k).concat(body.slice(k + 1)); }
  }
  const parts = splitPost(body), secs = parts.sections, sp = p.special;
  const V = arrangementOf(p, L);
  const rows = sheetRows(parts.prices);
  const pv = p.provenance || {};
  const asOf = String(pv.generated_at || '').slice(0, 10);
  _mx = 0; _qz = 0;
  CITE = Object.fromEntries(Object.entries(p.cite || {}).map(([k, n]) => [esc(k), n]));
  SRC = Object.fromEntries((p.sources || []).map(s => [s.n, s]));
  CARDED = new Set();

  // THE TOOLS - the matrix and the tree - go where the format puts them, and
  // never close the page: "which one to pick" ended 10 of 12 drafts.
  const tools = [];
  if(parts.matrix) tools.push(L === 'blueprint' ? matrixCards(parts.matrix) : matrixTable(parts.matrix, true));
  if(parts.tree) tools.push(`<div id="es-decision">${treeClick(parts.tree,
    L === 'runbook' ? 'Does this move apply to you?' : L === 'brief' ? 'Adopt it now?' : 'Find your case')}</div>`);

  let secHtml;
  if(L === 'versus' && V === 'b'){
    // ARRANGEMENT B: every question on screen at once, each opening in place -
    // the reader picks the question they came for instead of scrolling cards.
    secHtml = [`<div class="es-qgrid">${secs.map((s, i) =>
      `<details class="es-qtile"${s.head.id ? ` id="es-${esc(s.head.id)}"` : ''}${i === 0 ? ' open' : ''}>`
      + `<summary><span class="n">${pad2(i + 1)}</span><span>${essayText(s.head.text)}</span></summary>`
      + `${s.blocks.map(essayBlock).join('')}</details>`).join('')}</div>`];
  } else if(L === 'versus'){
    // A question card: the answer paragraph shows, the reasoning folds.
    secHtml = secs.map((s, i) => {
      let k = s.blocks.findIndex(b => b[0] === 'p');
      // A PICTURE RIGHT AFTER THE ANSWER STAYS IN VIEW (2026-10-16): folded into
      // "The reasoning", a drawn figure never loaded until the card was opened.
      while(k >= 0 && s.blocks[k + 1] && s.blocks[k + 1][0] === 'image') k++;
      const head = k < 0 ? s.blocks : s.blocks.slice(0, k + 1), rest = k < 0 ? [] : s.blocks.slice(k + 1);
      const more = rest.filter(b => b[0] === 'p').length;
      return `<section class="es-qcard">${sectionHtml({ head: s.head, blocks: head }, conf.label, i + 1)}${rest.length
        ? `<details class="why"><summary>The reasoning${more ? ` · ${more} more paragraph${more === 1 ? '' : 's'}` : ''}</summary>${
          rest.map(essayBlock).join('')}</details>` : ''}</section>`;
    });
  } else if(L === 'runbook'){
    secHtml = secs.map((s, i) => `<section class="es-step">${sectionHtml(s, conf.label, i + 1,
      '<label class="es-tick"><input type="checkbox" class="es-done">Mark this step done</label>')}</section>`);
  } else {
    // Arrangement B sets each section as a spread: its heading in a left
    // column beside the text, on a wide screen.
    secHtml = secs.map((s, i) => `<section class="es-sec${V === 'b' ? ' es-spread' : ''}">${sectionHtml(s, conf.label, i + 1)}</section>`);
  }
  const toolHtml = tools.join(''), half = Math.ceil(secHtml.length / 2);
  // Arrangement B moves the tools: top -> end, mid -> top, end -> top.
  const toolsAt = V === 'b' ? ({ top: 'end', mid: 'top', end: 'top' })[conf.tools] : conf.tools;
  let middle = toolsAt === 'top' ? toolHtml + secHtml.join('')
    : toolsAt === 'mid' ? secHtml.slice(0, half).join('') + toolHtml + secHtml.slice(half).join('')
    : secHtml.join('') + toolHtml;
  middle = parts.pre.map(essayBlock).join('') + middle;
  if(L === 'runbook') middle = `<div class="es-run">${middle}<div class="es-prog">Steps done: <span class="ct"></span> of ${secs.length}<span class="all"> · every step ticked</span></div></div>`;

  // OPENINGS AND ENDINGS. One pair per format; none of them is the old box.
  let open, end = '';
  if(L === 'report' && V === 'b'){
    // ARRANGEMENT B: a scoreboard - what holds beside what is still open.
    open = leadBox(conf, p, 'strip') + (sp && sp.type === 'findings'
      ? `<div class="es-score">${findingsCol(sp, 'established', 'What holds', 'ok')}`
        + `${findingsCol(sp, 'not established', 'Still open', 'open')}</div>`
      : `<nav class="es-log"><div class="lbl">Observations</div>${tocList(secs, '', n => `OBS-${pad2(n)}`)}</nav>`);
  } else if(L === 'report'){
    open = leadBox(conf, p, 'strip')
      + `<nav class="es-log"><div class="lbl">Observations</div>${tocList(secs, '', n => `OBS-${pad2(n)}`)}</nav>`
      + findingsCol(sp, 'established', 'What holds', 'ok');
    end = findingsCol(sp, 'not established', 'Still open', 'open');
  } else if(L === 'versus' && V === 'b'){
    // ARRANGEMENT B: the split first, as a statement; prices in a strip; the
    // "pick it when" lists move to the sidebar.
    open = leadBox(conf, p, 'verdict') + priceStrip(vsNames(p), rows, asOf);
  } else if(L === 'versus'){
    open = faceoff(p, rows, asOf) + leadBox(conf, p, 'split');
  } else if(L === 'ledger'){
    open = receipt(p, rows, conf, asOf);
    const lv = sp && sp.type === 'drivers' ? sp.items.map(x => ({ name: x.driver, lever: x.lever }))
      : parts.matrix ? (parts.matrix.table.rows || []).map(r => ({ name: r[0], lever: r[2] })) : [];
    end = lv.length ? leverList(lv) : '';
  } else if(L === 'runbook'){
    open = leadBox(conf, p, 'before');
    const st = sp && sp.type === 'steps' ? sp.items : null;
    end = st ? `<section class="es-levers"><div class="lbl">${esc(sp.title || 'Checks')}</div><ul>${st.map(x =>
      `<li><label><input type="checkbox"><span><b>${essayText(x.step)}</b> ${essayText(x.check)}</span></label></li>`).join('')}</ul>
      <div class="tally">Checked <span class="ct"></span> of ${st.length}</div></section>` : '';
  } else if(L === 'blueprint'){
    open = layerMap(p, secs, conf);
  } else if(L === 'brief'){
    open = leadBox(conf, p, 'verdict') + (sp && sp.type === 'claims' ? claimWall(sp)
      : `<nav class="es-points"><div class="lbl">In ${secs.length} points</div>${tocList(secs, '', pad2)}</nav>`);
  } else if(L === 'critique'){
    open = leadBox(conf, p, 'thesis')
      + `<nav class="es-chain"><div class="lbl">The argument in ${secs.length} steps</div>${tocList(secs, '', String)}</nav>`;
    if(sp && sp.type === 'probes' && sp.items && sp.items.length) end = probeList(sp);
  } else if(L === 'mechanism'){
    open = leadBox(conf, p, 'strip')
      + `<nav class="es-points"><div class="lbl">The machinery, in order</div>${tocList(secs.filter(s => s.head.num !== 'FAQ'), '', pad2)}</nav>`;
    if(sp && sp.type === 'lab' && sp.items && sp.items.length) end = labBox(sp);
  } else if(L === 'myths'){
    open = leadBox(conf, p, 'verdict') + (sp && sp.type === 'myths' && sp.items && sp.items.length ? mythCards(sp) : '');
  } else if(L === 'radar'){
    open = leadBox(conf, p, 'strip') + (sp && sp.type === 'radar' && sp.items && sp.items.length ? radarList(sp) : '');
  } else if(L === 'debate'){
    open = leadBox(conf, p, 'thesis') + (sp && sp.type === 'positions' && sp.items && sp.items.length ? sidesBox(sp) : '');
  } else if(L === 'fieldguide'){
    open = leadBox(conf, p, 'before');
    if(sp && sp.type === 'checklist' && sp.items && sp.items.length) end = checklistBox(sp);
  } else if(L === 'paper'){
    open = leadBox(conf, p, 'strip') + (sp && sp.type === 'results' && sp.items && sp.items.length ? resultsBox(sp) : '');
  } else if(L === 'synthesis'){
    open = leadBox(conf, p, 'strip') + (sp && sp.type === 'glossary' && sp.items && sp.items.length ? glossaryBox(sp) : '');
  } else if(L === 'explainer'){
    const steps = secs.filter(s => s.head.num !== 'FAQ');  // the FAQ is not a step
    open = leadBox(conf, p, 'strip')
      + `<nav class="es-points"><div class="lbl">In ${steps.length} steps</div>${tocList(steps, '', pad2)}</nav>`;
    if(sp && sp.type === 'quiz' && sp.items && sp.items.length) end = quizBox(sp);
  } else {
    open = leadBox(conf, p);
  }
  let main = open + middle + end;

  // READING TIME, COUNTED: the words on the page at 230 a minute. One mode
  // only since 2026-10-13 - the skim/full toggle is gone with the skim lines.
  const mins = Math.max(1, Math.round(wordsIn(main) / 230));
  // INTERACTIVE BY DEFAULT since 2026-10-06; a post can still opt out.
  if(p.interactive !== false) main = interactivize(main, p, rows);
  const mode = `<div class="es-mode"><span class="es-readtime">${mins} min read</span>
    <p>Dotted names open a model card. <q class="es-iq">Quoted</q> words are an engineer's, copied exactly.</p></div>`;

  // A POST ABOUT TWO MODELS OPENS THE COMPARISON OF THEM (2026-10-19). Only
  // when both names in the title (or the picks) resolve to two different models
  // with public pages; "Humans vs Machines" resolves to nothing and gets none.
  const [va, vb] = vsNames(p).map(n => entityIndex().byKey.get(nameKey(n)));
  const cmp = va && vb && va !== vb && va.canonical_id && vb.canonical_id
    ? `<p class="es-cmp"><a${goAttrs(`compare:${va.canonical_id},${vb.canonical_id}`)}>Compare ${
      esc(shortName(va))} and ${esc(shortName(vb))} side by side →</a></p>` : '';
  const toc = [...secs.filter(s => s.head.id).map(s => [`es-${s.head.id}`, s.head.text]),
    ...(parts.matrix ? [['es-matrix', parts.matrix.head.text]] : []), ...(parts.tree ? [['es-decision', 'Decision tree']] : [])]
    .map(([id, t]) => `<li><a data-toc="${esc(id)}">${essayText(t)}</a></li>`).join('');
  const tags = (p.tags||[]).map(t=>`<span class="es-tag">${esc(t)}</span>`).join('');
  const dec = (p.decisions||[]).map(d=>`<li>${essayText(d)}</li>`).join('');
  const picksSide = L === 'versus' && V === 'b' && sp && sp.type === 'picks'
    ? `<div class="es-scard">${vsNames(p).map(n => `<div class="lbl">Pick ${esc(n)} when</div><ul class="dec">${
        sp.items.filter(x => x.pick === n).map(x => `<li>${essayText(x.when)}</li>`).join('')}</ul>`).join('')}</div>` : '';
  // CONTINUE READING, COMPUTED (2026-10-15). `p.rel` was the same three links
  // on every post - written by the generator, related to nothing. Now: other
  // posts sharing a model (its tags other than the format), most shared first,
  // then posts in the same format. A join, never "you'll like".
  const own = new Set((p.tags || []).filter(t => t !== p.tag));
  const rel = (DB.posts || []).filter(q => q.slug !== p.slug)
    .map(q => ({ q, shared: (q.tags || []).filter(t => own.has(t)).length, same: q.tag === p.tag }))
    .filter(x => x.shared > 0 || x.same)
    .sort((a, b) => (b.shared - a.shared) || (b.same - a.same) || a.q.title.localeCompare(b.q.title))
    .slice(0, 4)
    .map(({ q, shared }) => `<a class="es-rel"${goAttrs(`post:${q.slug}`)}>${esc(q.title)}${
      shared ? `<span class="es-rel-why"> · same model</span>` : `<span class="es-rel-why"> · ${esc(q.tag)}</span>`}</a>`).join('');
  const sheet = rows.length ? `<div class="es-scard es-sheet"><div class="lbl">Price sheet${asOf ? ` · ${esc(asOf)}` : ''}</div>
    <table><thead><tr><th></th><th>In</th><th>Out</th></tr></thead><tbody>${rows.map(r =>
    `<tr><td>${esc(r.name)}</td><td>${esc(r.pin)}</td><td>${esc(r.pout)}</td></tr>`).join('')}</tbody></table>
    <p>Registry list prices per 1M tokens when the post was written. A price the provider does not publish says so; it is never zero.</p></div>` : '';
  const page = `<div class="essay${L?' layout-'+L:''} arr-${V}"><div class="es-wrap">
    <div class="es-crumb"><a${goAttrs('blogs')}>All essays</a></div>
    <header class="es-hero"><div class="es-kicker">${esc(p.kicker||p.tag)}</div><h1>${esc(p.title)}</h1>
      <p class="es-dek">${esc(p.dek)}</p>
      <div class="es-byline">${(p.meta||[]).map(m=>`<span>${esc(m)}</span>`).join('')}</div>
      ${tags?`<div class="es-tags">${tags}</div>`:''}</header>
    <div class="es-layout">
      <article class="es-article">
        ${cover ? essayBlock(['image', { ...cover, cover: true }]) : ''}${mode}${cmp}${main}
        ${sourcesBlock(p)}
        <footer class="es-foot">
          <p>Written by <code>${esc(pv.model)}</code>${pv.generated_at?` on ${esc(String(pv.generated_at).slice(0,10))}`:''}
          from engineers' public discussions, then checked in code: ${esc(pv.checks||'not recorded')}.
          ${reviewOf(p)==='approved'
            ? `Read and approved by a person on the team${p.published_at?` on ${esc(day(p.published_at))}`:''}.`
            : reviewOf(p)==='rejected' ? '<b>Rejected in review.</b>' : '<b>Not yet reviewed by a person.</b>'}
          Code samples are illustrative patterns. Prices are published list prices. No model is scored or ranked.</p>
          <p>${reviewOf(p)==='approved' ? 'Approved by the team; not yet published outside it.'
            : 'Draft — not for external publication.'}</p>
        </footer>
      </article>
      <aside class="es-side">
        ${toc?`<div class="es-scard"><div class="lbl">On this page</div><ol>${toc}</ol></div>`:''}
        ${picksSide}
        ${sheet}
        ${dec?`<div class="es-scard"><div class="lbl">Decisions it supports</div><ul class="dec">${dec}</ul></div>`:''}
        ${rel?`<div class="es-scard"><div class="lbl">Continue reading</div>${rel}</div>`:''}
      </aside>
    </div>
  </div></div>`;
  CITE = null; SRC = null; CARDED = null;
  return page;
}
export { vBoard, vJob, vCap, vMet, vJobModel, vCapModel, vMetModel, vBlogs, vPost }
