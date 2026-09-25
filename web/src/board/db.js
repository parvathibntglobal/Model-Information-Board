// Board dataset — filled at runtime from `GET /board`, never hardcoded.
//
// The three sections are DISCOVERED by the classifier: it reads what engineers
// wrote and names the job, capability or metric they discussed. So there is no
// list of eight jobs here, and an empty board is a real state — nobody has
// discussed anything yet — rather than a loading bug.
//
// WHAT THIS ADAPTER DELIBERATELY LEAVES EMPTY
// -------------------------------------------
// The demo board carried five blocks per page, and only some of them come from
// evidence. `pick` (one model named the winner), `conds` (four conditions where
// the pick stops holding), `nots` ("what this is not"), `lim` (what a metric
// cannot tell you) and `vol` (search volume) were all WRITTEN BY HAND.
//
// A classifier does not produce them, and this adapter does not invent them.
// They arrive as empty and `views.js` omits the block entirely — because a
// fabricated "the pick" is exactly the synthesised claim rule 3 forbids, and a
// made-up condition would be worse than a missing one: it reads as a finding.
// When an editor writes them, they get a home; until then the page shows what
// the evidence actually says and no more.
export const DB = {
  jobs: [], caps: [], mets: [], posts: [], metsWithheld: {},
  // PARENT HEADINGS, AS A RENDER ORDER OVER THE SAME OBJECTS.
  //
  // `caps` and `mets` stay FLAT and are not replaced. Every lookup on this
  // board is by slug - `byS(DB.caps, slug)`, the model pages, the routes - and
  // a nested shape would mean two answers to "what is a leaf". So these hold
  // {kind:'parent', name, leaves, children:[leaf…]} or {kind:'leaf', …} rows
  // whose leaf objects are THE SAME OBJECTS as in `caps`/`mets`, re-ordered.
  //
  // Empty when the payload predates grouping, and the views fall back to the
  // flat list - so an older API renders exactly as it did.
  capGroups: [], metGroups: [],
  // COMPUTED PER REQUEST, NEVER CARRIED AS A LITERAL. The ungrouped count was
  // 19 in the proposal, 20 in review and 21 by the time the page was written -
  // three answers in one day. Anything that states it reads this.
  parentCoverage: {},
}

/** Was the board read at all? Distinguishes "nothing found" from "never asked". */
export let boardLoaded = false

/**
 * What to call a model on the board: the registry's name, or the id if there
 * is none.
 *
 * THIS DERIVED A NAME FROM THE ID AND IGNORED THE ONE IT WAS SENT. The previous
 * version was `String(id || '').split('/').pop()`, which reads well on a slug —
 * `anthropic/claude-fable-5-1` becomes `claude-fable-5-1` — and returns the
 * whole string on an id with no slash. Polled registry rows are `mv_` hashes,
 * so **29 of 64 board rows (45%), across 11 models, named their model with a
 * hash**: `mv_a2b4f7fc3fa679c2` where the page should read `Anthropic: Claude
 * Opus 4.8`.
 *
 * `model_label` has been in the payload since #260 — `board_sections()` puts it
 * on every entry in `models[]`, `quotes[]` and `figures[]`, and `judge/app.py`
 * returns those dicts unchanged. Nothing needed fetching; this file needed to
 * read a field it was already being handed. A producer sent it, no consumer
 * read it, and nothing tested that a consumer existed — the API-side form of
 * #275.
 *
 * THE FALLBACK IS THE POINT, and `web/src/routes/Admin.jsx:76` had the pattern
 * right all along: `m.display_name || m.model_version_id`. An absent label is
 * not a reason to render nothing, and deriving from the id is still the best
 * available answer when there is no name — it just must not be the FIRST
 * answer. Rule 6, on a display: a missing value stays missing rather than
 * becoming a definite one, and the id is the honest stand-in.
 */
const modelName = (m) =>
  (m && m.model_label) || String((m && m.model_version_id) || '').split('/').pop()

/**
 * Evidence state, COUNTED and never scored.
 *
 *   contested  both praise and criticism are present. A real disagreement, and
 *              it is shown as a split rather than averaged into a middle.
 *   verified   two or more VOICES and no disagreement among them. This counts
 *              PEOPLE; it is not a quality judgement and not a gate verdict.
 *   single     one voice. Its own state on purpose: one voice is not
 *              corroboration, and calling it "not discussed" would be false.
 *   none       nothing at all.
 *
 * IT COUNTS VOICES, NOT QUOTES, AND THAT IS THE WHOLE CORRECTION. It used to
 * take `reports`, which the API incremented once per QUOTE - so the
 * ethical-reasoning page read "3 reports · verified" from three figures stated
 * in ONE Hacker News comment by ONE author. The threshold was working
 * correctly on a number that was wrong, and the word it produced - "verified" -
 * is the one this board must never be wrong about.
 *
 * `voices` is distinct authors. Two comments by one person are one voice,
 * which is the only reading under which this function's own docstring ("one
 * voice is not corroboration") is true.
 */
function evidenceState(voices, quotes) {
  if (!voices) return 'n'
  const pol = new Set((quotes || []).map((q) => q.polarity))
  if (pol.has('positive') && pol.has('negative')) return 'c'
  return voices >= 2 ? 'v' : 's'
}

/** "1 report · 3 figures" — never one number standing for both. */
function evidenceLabel(item) {
  const reports = item.reports || 0
  const quotes = item.quote_count ?? (item.quotes || []).length
  const r = `${reports} report${reports === 1 ? '' : 's'}`
  // Only said when the two differ. "1 report · 1 figure" is noise, and a
  // reader seeing "3 reports" where three quotes came from one comment is
  // exactly what this is here to prevent.
  return quotes > reports ? `${r} · ${quotes} figures` : r
}

/**
 * "1 positive · 11 negative · 1 both" — the split, in reports.
 *
 * ON EVERY BEST-FOR AND CAPABILITY ROW, since 2026-09-25. `best_for` filtered
 * its negatives out until then, so it had no split to show; it has one now,
 * and `board_sections` sends `report_split` for both sections. Metric rows get
 * none and render as they did.
 *
 * ⚠ POSITIVE AND NEGATIVE ARE ALWAYS NAMED, 0 INCLUDED. They were named only
 *   where non-zero, because "0 negative" on a positive-only row was noise. It
 *   is not noise now: the list is ORDERED on these two numbers (at least one
 *   positive, then neutral-only, then negatives and none positive), so both
 *   are the evidence for where the row sits. The intro's last clause - a model
 *   enters the first group on one positive however many problems it has - is
 *   only checkable if a reader can see "1 positive · 11 negative".
 *
 * `neutral` and `both` stay conditional. `both` is said only where it applies:
 *   one report can be positive AND negative, so the split does not partition
 *   the report count (positive + negative - both + neutral = reports), and on
 *   the two biggest capability pages the top row is one of those.
 */
function splitPhrase(m) {
  const sp = m.report_split
  if (!sp) return ''
  const parts = [`${sp.positive || 0} positive`, `${sp.negative || 0} negative`]
  if (sp.neutral) parts.push(`${sp.neutral} neutral`)
  if (sp.both) parts.push(`${sp.both} both`)
  return parts.join(' · ')
}

/** One quote, as the tuple views.js renders.
 *
 * [quote, who, document_id, isNegative, url] — the shape views.js renders.
 *
 * `url` IS THE FIFTH ELEMENT AND IT IS NEW. "open the source" was underlined
 * text pointing nowhere because this tuple carried only the document id;
 * `board_sections` now joins `document` for its url, and views.js turns it
 * into an anchor when the scheme is http(s).
 */
const quoteTuple = (q) => [
  q.quote,
  modelName(q) || 'unattributed',
  q.document_id,
  q.polarity === 'negative',
  q.url || null,
]

/**
 * The quotes of one section, split by the model each was reported about.
 *
 * THE CATEGORY PAGE NO LONGER RENDERS QUOTES, so this is where they go. It
 * used to send every quote to one block on the category page, which showed
 * the 12 the API sent of however many the section held; now each model's
 * reports live on that model's own page and all of them are there.
 *
 * Keyed on `model_key` — the registry id `board_sections` groups the model
 * list on — so a model named under both id shapes partitions as one model
 * rather than two.
 *
 * A QUOTE WITH NO MODEL IS COUNTED, NOT DROPPED. `board_entry.model_version_id`
 * is nullable, and a quote without one belongs to no model row and so has no
 * page to appear on. 0 of 1,249 rows are in that state today, which is why
 * this is three lines rather than a surface — but silently losing them would
 * be an absence we caused, so the count comes back and the page says it.
 */
function quotesByModel(item) {
  const byKey = new Map()
  const orphans = []
  for (const q of item.quotes || []) {
    const key = q.model_key || q.model_version_id
    if (!key) { orphans.push(q); continue }
    if (!byKey.has(key)) byKey.set(key, [])
    byKey.get(key).push(quoteTuple(q))
  }
  return { byKey, orphans: orphans.length }
}

function commonFields(item) {
  // VOICES, not reports. An absent `voices` falls back to `reports` so an
  // older payload degrades to the previous behaviour rather than to 'none'.
  const st = evidenceState(item.voices ?? item.reports, item.quotes)
  const { byKey, orphans } = quotesByModel(item)
  return {
    slug: item.slug,
    name: item.name,
    card: item.definition,
    ev: evidenceLabel(item),
    st,
    vol: '', // search volume is editorial, and absent is honest
    // THE DENOMINATORS THE MODEL LIST IS DRAWN FROM, for the line above it.
    // `ev` already carries reports and figures for the hub card, but that
    // label says nothing about voices and nothing about how many models the
    // list holds - and a list of 20 rows with no stated population is rule 7's
    // failure in its plainest form.
    repTotal: item.reports || 0,
    voiTotal: item.voices ?? item.reports ?? 0,
    // Reports that name no model, so they appear under none. See above.
    orphans,
    // One row per model named in this section. `d` and `p` stay empty: a
    // description and a price are facts from the registry, not from this quote.
    rows: (item.models || []).map((m) => {
      const key = m.model_key || m.model_version_id
      return {
        m: modelName(m),
        // THE DRILL-DOWN KEY. It can contain a slash — `model_version.id`
        // holds canonical ids for 166 of 1,249 rows — so every reader of it
        // must treat it as the rest of a path, never as one segment.
        key,
        v: '',
        d: '',
        p: '',
        // REPORTS AND VOICES ARE DIFFERENT NUMBERS, so both are said. 131 of
        // 636 (section, slug, model) groups hold more quotes than documents
        // and 22 hold more documents than voices, so neither stands for the
        // other. The floor marker rides with the report count for the same
        // reason it does everywhere else: an open vocabulary can name one
        // section twice, so the count is ">= N" until somebody merges them.
        e: `≥${m.reports} report${m.reports === 1 ? '' : 's'} · `
          + `${m.voices ?? m.reports} voice${(m.voices ?? m.reports) === 1 ? '' : 's'}`,
        // ⚠ THIS MODEL'S STATE, NOT THE SECTION'S — the whole of the badge fix.
        //
        // This was `s: st`, the section's state stamped onto every row. On
        // `capability/reasoning` that put "contested" — read off 39 voices —
        // on all 20 rows, including a model with one voice and one report.
        // Measured 2026-09-18 over every model row these two page types
        // render, 173 of 414 (42%) carried a state that was not their own,
        // and 48 said "corroborated" above a single voice.
        //
        // IT IS THE SAME FUNCTION, fed this model's own numbers. The verdict
        // has one definition and this is not a second one. `polarities`
        // arrives from `board_sections` rather than being read off the quote
        // list, because it has to be complete: computing it here would judge
        // a model on whichever of its quotes happened to be nearby.
        //
        // An older payload without `polarities` degrades to voices alone —
        // corroborated or one voice, never 'not discussed' — for the same
        // reason `item.voices ?? item.reports` does above: a missing value
        // must not become a definite claim that nobody discussed this.
        s: evidenceState(
          m.voices ?? m.reports,
          (m.polarities || []).map((polarity) => ({ polarity })),
        ),
        // WHICH OF THE THREE GROUPS THE ROW IS IN, from `board_sections`.
        // `ranked()` opens a heading where it changes. Absent on metric rows
        // and on an older payload, which then render with no headings.
        g: m.group || null,
        // The polarity split, or '' where the section does not have one.
        sp: splitPhrase(m),
        qs: byKey.get(key) || [],
        dim: false,
      }
    }),
    rel: [],
  }
}

/**
 * One row per distinct figure, carrying every report that states it.
 *
 * The key is model + value + basis + unit. `basis` is IN it because a stated
 * figure and a reported one are different facts — this page says exactly that
 * in its own subtitle, so merging them here would contradict the page.
 *
 * Sources are de-duplicated BY DOCUMENT, not by row. An article that states a
 * figure twice is one report; two articles stating it are two, and that second
 * case is corroboration rather than repetition. `board_entries.py` learned this
 * on 2026-09-11 for `reports`, after a page said "3 reports · verified" about
 * three figures from one comment by one person.
 *
 * Order is preserved: first appearance wins, so the table does not reshuffle
 * when a new quote arrives for a figure already on it.
 */
// -- WHAT A FIGURE ACTUALLY MEASURES, TAKEN FROM ITS OWN QUOTE --------------
//
// THE PROBLEM THIS EXISTS FOR, IN ONE CELL. `cost-per-token` held BOTH of
// these for Claude Fable 5.1, in one column, under one unit:
//
//     $0.25 / MTok   "Cache read price | $0.25 / MTok"
//     $50   / MTok   "Official output price | $50 / MTok"
//
// They do not disagree. They are answers to different questions, and only the
// quote said which - so a reader met the same model name twice with a 200x
// spread and no way to tell why without opening both sources.
//
// COPIED, NEVER INFERRED, AND `null` IS A CORRECT ANSWER. The label comes from
// words that are really in the quote. Measured over the 269 figures rendering
// on 2026-09-21: `cost-per-token` says which side for 44 of 113,
// `time-to-first-token` for 1 of 15, `tokens-per-second` for 1 of 18. So the
// common case is that the evidence does not say, and the page has to be able
// to say THAT rather than pick the likely one - filing an unmarked price as
// "input" because most prices are input is exactly the substitution that put a
// Terminal-bench figure on the SWE-bench page (#368, rule 6).
//
// Ordered, and the order matters: "cache read" contains "read", and an
// input/output price pair mentions both words in one sentence. First match
// wins, most specific first.
const SUBAXIS = [
  ['cache write', /cache\s*writ|write\s*cach/],
  ['cache read', /cache\s*read|read\s*cach|cached\s*input/],
  ['output', /\boutput\b|\bcompletion\b|\bgenerated\b/],
  ['input', /\binput\b|\bprompt\b|\buncached\b/],
  ['per request or task', /\bblended\b|per\s*request|\bper\s*task\b/],
]

export function subAxisOf(quote) {
  const q = (quote || '').toLowerCase()
  if (!q) return null
  const hit = SUBAXIS.find(([, re]) => re.test(q))
  return hit ? hit[0] : null
}

// -- ONE MEASUREMENT, HOWEVER IT WAS SPELLED ------------------------------
//
// WHAT THE PAGE SHOWED. DeepSeek V4 Flash, cost per token, four rows:
//
//     output   $0.25/M                            10 reports
//     output   $0.25 per million output tokens     3 reports
//     output   $0.25/M output tokens               1 report
//     output   $0.25                               stated and reported
//
// One price, one unit, one axis, four rows - because the group key was the
// VERBATIM STRING, so a writer's choice of abbreviation split a figure that
// fifteen reports agree on. It read as four findings and buried the
// corroboration, which is the same defect `groupFigures` was already built
// to fix one level down.
//
// EXACTLY ONE MAGNITUDE, OR NOTHING. The denominator words are removed
// first, then every remaining number is counted. Two numbers means the
// string is not a single figure - `$10/1M input and $50/1M output`,
// `$0.66 off-peak or $1.32 at peak` - and those keep their verbatim key and
// never merge. Refusing to canonicalise is always available and is what
// makes this safe.
//
// MEASURED BEFORE SHIPPING, over every figure the board publishes: 220
// groups become 204, sixteen rows removed, and every one of the sixteen was
// read by eye. They are the same number written two or three ways -
// `$10 / MTok` with `$10`, `$15 per million` with `$15.00/M`,
// `60 tokens per second` with `60 tokens/sec`. No merge changed a value.
//
// THE UNIT STAYS IN THE KEY, so `8.7c per task` never meets `$8.70`, and
// nothing is averaged: an exact agreement collapses and a disagreement
// stays two rows, exactly as before.
const FIGURE_DENOMINATORS = [
  /per\s*(?:one\s*)?(?:1\s*)?million\s+(?:input\s+|output\s+|cached\s+)?tokens?/g,
  /per\s*(?:1\s*)?m(?:illion)?\s*tok(?:ens?)?/g,
  /\/\s*1?\s*m(?:tok|illion)?\b/g,
  /per\s*1?m\b/g,
  /per\s*token/g,
  /\bmtok\b/g,
  /\b1m\b/g,
]

export function canonicalFigure(value) {
  let v = String(value || '').toLowerCase()
  for (const re of FIGURE_DENOMINATORS) v = v.replace(re, ' ')
  const nums = v.match(/\d[\d,]*(?:\.\d+)?/g) || []
  if (nums.length !== 1) return null
  const n = Number(nums[0].replace(/,/g, ''))
  return Number.isFinite(n) ? n : null
}

function groupFigures(m) {
  const byKey = new Map()
  for (const f of m.figures || []) {
    const model = modelName(f)
    // THE KEY, SO THE DRILL-DOWN CAN FILTER ON IT. `model_key` is what
    // the model rows are grouped on; a label is a display string and
    // two spellings of one model share neither.
    const modelKey = f.model_key || f.model_version_id || ''
    const unit = f.unit || m.unit || ''
    // THE KEY IS THE FIGURE, AND `basis` IS NOT IN IT.
    //
    // It was, and the page still repeated a model: Claude Fable 5.1 appeared
    // twice on SWE-bench with the SAME 38.8%, once `stated` and once
    // `reported`. Two lines, one number, and it read as duplication.
    //
    // It is the opposite of duplication. A provider claiming 38.8% and somebody
    // who measured it independently arriving at 38.8% is the strongest evidence
    // this board can hold, and splitting it across two rows buried that.
    //
    // ⚠ THIS IS NOT THE MERGE THE PAGE FORBIDS. "the two are never merged"
    //   guards against AVERAGING - "2M advertised against ~200k reported-usable
    //   are two facts from two sources; averaging them would describe nothing
    //   that exists". Nothing is averaged here and nothing is dropped: the key
    //   still contains the VALUE, so two different figures stay two rows and a
    //   disagreement stays visible. Only an exact agreement collapses, and the
    //   row then names both bases rather than picking one.
    // The canonical magnitude when the string yields exactly one, the raw
    // text when it does not. `n:` and `v:` keep the two kinds of key from
    // ever colliding.
    const canon = canonicalFigure(f.value)
    const figureKey = canon === null ? 'v:' + f.value : 'n:' + canon
    const key = [modelKey || model, figureKey, unit].join('\u001f')
    if (!byKey.has(key)) {
      byKey.set(key, { model, modelKey, value: f.value, unit,
                       // EVERY WORDING, COUNTED. The row shows the one most
                       // reports used and says how many others there were:
                       // dropping them silently would hide that a figure was
                       // written four ways, and that is the reader's evidence
                       // that fifteen people agree rather than one saying it
                       // four times.
                       spellings: new Map(), bases: [], sources: [] })
    }
    const group = byKey.get(key)
    group.spellings.set(f.value, (group.spellings.get(f.value) || 0) + 1)
    if (f.basis && !group.bases.includes(f.basis)) group.bases.push(f.basis)
    const id = f.document_id || ''
    // ONE ENTRY PER DOCUMENT, and it carries which basis it supports so the
    // mapping survives the grouping — a reader can still see which report was
    // the vendor's statement and which was the measurement.
    const seen = group.sources.find((s) => s.id === id)
    if (seen) {
      if (f.basis && !seen.bases.includes(f.basis)) seen.bases.push(f.basis)
      // First quote wins. An article stating one figure twice is one report
      // (this file's own rule), and two wordings of one report would read as
      // corroboration that is not there.
      if (!seen.quote && f.quote) seen.quote = f.quote
    } else {
      // THE QUOTE RIDES WITH ITS REPORT, not with the row. A row groups on the
      // FIGURE, so two reports can state 38.8% in different words — and which
      // words belong to which report is the whole of what makes a figure
      // checkable. See views.js for why it is printed rather than hovered.
      group.sources.push({
        id, url: f.url || null, quote: f.quote || null,
        subAxis: subAxisOf(f.quote),
        bases: f.basis ? [f.basis] : [],
      })
    }
  }
  // `basis` stays on the group for the table cell: one word when there is one,
  // both when a figure is claimed and confirmed.
  //
  // ORDERED, not first-seen. Left to arrival order the same pair rendered
  // "stated · reported" on one row and "reported · stated" on the next, which
  // reads as a difference between the rows when there is none. The claim comes
  // before the confirmation because that is the order the two happen in.
  const ORDER = ['stated', 'reported']
  const rank = (b) => { const i = ORDER.indexOf(b); return i === -1 ? ORDER.length : i }
  return [...byKey.values()].map((g) => {
    // ONLY WHERE THE REPORTS AGREE. If two reports of one figure describe it
    // differently - one says "output", the other says nothing - the group
    // cannot claim either. A disagreement about WHAT WAS MEASURED is a
    // finding, and resolving it by majority would bury it.
    const named = [...new Set(g.sources.map((x) => x.subAxis).filter(Boolean))]
    // SHOWN AS THE TEXT WROTE IT - and where several texts wrote it
    // differently, as the most of them wrote it. Never reformatted into a
    // house style, because the page's own subtitle promises the figure
    // verbatim and a tidied string is not one.
    const spelled = [...g.spellings.entries()].sort((a, b) => b[1] - a[1]);
    return {
      ...g,
      value: spelled.length ? spelled[0][0] : g.value,
      otherSpellings: Math.max(0, spelled.length - 1),
      subAxis: named.length === 1 ? named[0] : null,
      subAxisDisputed: named.length > 1,
      basis: [...g.bases].sort((a, b) => rank(a) - rank(b)).join(' · '),
    }
  })
}

/** Populate `DB` from the `/board` payload. Called once, before the views render. */
export function setBoardData(payload) {
  const d = payload || {}

  DB.jobs = (d.jobs || []).map((j) => ({
    ...commonFields(j),
    h1: j.name,
    sub: j.definition,
    pick: null, // hand-written editorial; omitted rather than invented
    conds: [],
  }))

  DB.caps = (d.caps || []).map((c) => ({
    ...commonFields(c),
    d1: c.definition,
    d2: '',
    nots: [],
  }))

  DB.mets = (d.mets || []).map((m) => {
    const base = commonFields(m)
    const groups = groupFigures(m)
    return {
      ...base,
      unit: m.unit || '',
      // The other spellings this axis stands for. A page silently
      // covering `exploitbench` and `exploit-bench` is making a claim
      // the reader cannot check (rule 4).
      spelledAlso: m.spelled_also || [],
      d1: m.definition,
      d2: '',
      lim: [],
      // STATED AND REPORTED SIT SIDE BY SIDE AND ARE NEVER MERGED. 2M
      // advertised against ~200k reported-usable are two facts from two
      // sources; averaging them would describe nothing that exists. The figure
      // is shown as the text wrote it, hedge included.
      cols: ['Model', 'Figure', 'Basis', 'Unit'],
      num: [false, true, false, false],
      // ONE ROW PER FIGURE, NOT ONE ROW PER QUOTE.
      //
      // `figures[]` is one entry per board_entry, and a board_entry is one
      // QUOTE — so an article that states 38.8% twice sent two entries, and the
      // table printed the same model, figure, basis and unit on two lines with
      // nothing to tell them apart. Thirteen SWE-bench rows were ten distinct
      // figures.
      //
      // Marking the repeats was the first attempt and it was the weaker half of
      // the answer: it told a reader the two lines were one report and still
      // made them read two lines. Grouping is what the quotes view already does
      // 120 lines up in views.js, and what `board_entries.py` did for `reports`
      // on 2026-09-11 — "3 figures from ONE comment by ONE person" counted as
      // three reports until it stopped.
      //
      // WHAT IS NOT MERGED. The key keeps `basis`, because a stated 38.8% and a
      // reported 38.8% are two facts and this page says so in its own subtitle.
      // And DISTINCT DOCUMENTS ARE KEPT AND COUNTED rather than folded away:
      // two articles reporting the same figure is corroboration and is the most
      // valuable thing on the page. Only a repeat WITHIN one document collapses,
      // because that is one report either way.
      rows: groups.map((g) => [
        g.model,
        g.value,
        g.basis,
        g.unit,
      ]),
      // THE SOURCES FOR EACH ROW, PARALLEL TO `rows` RATHER THAN INSIDE IT.
      //
      // Kept out of `rows` deliberately: views.js escapes every cell of `rows`
      // with esc(), which is what makes that generic loop safe to render. A
      // cell that had to carry an anchor would make the cells polymorphic and
      // put an un-escaped branch inside it. One controlled column instead.
      srcs: groups.map((g) => g.sources),
      // -- THE MODEL LEVEL, WHICH THIS SECTION USED TO THROW AWAY ------------
      //
      // `commonFields` builds `rows` from `item.models` - ONE ROW PER MODEL -
      // for every section, and this mapping then overwrote it with the figure
      // table. That overwrite is why a metric page repeated a model name once
      // per figure, and why metrics was the only section with no drill-down:
      // `vJobModel` and `vCapModel` both partition `rows` by model, and there
      // were no model rows left to partition.
      //
      // Measured 2026-09-21: 34 (slug, model) cells hold two or more DIFFERENT
      // figures, the worst being 6 values over 19 rows. Every one of those
      // read as the same model contradicting itself.
      //
      // `figs` is the figure table, kept whole; `mrows` is the model level,
      // kept rather than discarded. Neither overwrites the other, and the
      // figure table is still what the leaf page renders - filtered to one
      // model instead of holding all of them at once.
      mrows: base.rows || [],
      groups,
    }
  })

  // RULE 4. The metrics tab renders fewer rows than the database holds,
  // because a figure that cannot support itself is held back. Without this the
  // page makes the opposite claim - that nobody measured these models - and
  // the two look identical to a reader. Counted by reason, because a figure
  // with no quantity sends you to the prompt and a mislabelled axis does not.
  // THE GROUPED VIEW, BUILT FROM THE FLAT ONES BY SLUG. The payload's grouped
  // rows carry their own copies of each leaf; we re-point them at the objects
  // already in `DB.caps`/`DB.mets` so a leaf is one object on this page no
  // matter which way it was reached. A slug the flat list does not have is
  // dropped rather than rendered from the payload's copy - that would be two
  // leaves with one slug, which is the shape parents exist NOT to create.
  const regroup = (rows, flat) => {
    const bySlug = new Map(flat.map((x) => [x.slug, x]))
    return (rows || []).flatMap((r) => {
      if (r.kind !== 'parent') {
        const leaf = bySlug.get(r.slug)
        return leaf ? [{ kind: 'leaf', leaf }] : []
      }
      const children = (r.children || []).map((c) => bySlug.get(c.slug)).filter(Boolean)
      // A PARENT WITH NOTHING UNDER IT IS NOT RENDERED. A heading over no
      // cards is a claim that something is there, and a reader who cannot see
      // the leaves under a parent is reading a merge.
      if (!children.length) return []
      // `leaves` COMES FROM WHAT WE WILL ACTUALLY DRAW, not from the payload's
      // count. If a leaf was dropped above, the heading must not still claim it.
      return [{ kind: 'parent', name: r.name, parent: r.parent, children,
                leaves: children.length }]
    })
  }
  const grouped = d.grouped || {}
  DB.capGroups = regroup(grouped.caps, DB.caps)
  DB.metGroups = regroup(grouped.mets, DB.mets)
  DB.parentCoverage = d.parent_coverage || {}

  DB.metsWithheld = d.metrics_withheld || {}
  DB.posts = d.posts || []
  boardLoaded = true
  return DB
}
