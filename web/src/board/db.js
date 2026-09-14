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
export const DB = { jobs: [], caps: [], mets: [], posts: [] }

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

function commonFields(item) {
  // VOICES, not reports. An absent `voices` falls back to `reports` so an
  // older payload degrades to the previous behaviour rather than to 'none'.
  const st = evidenceState(item.voices ?? item.reports, item.quotes)
  return {
    slug: item.slug,
    name: item.name,
    card: item.definition,
    ev: evidenceLabel(item),
    st,
    vol: '', // search volume is editorial, and absent is honest
    // One row per model named in this section. `d` and `p` stay empty: a
    // description and a price are facts from the registry, not from this quote.
    rows: (item.models || []).map((m) => ({
      m: modelName(m),
      v: '',
      d: '',
      p: '',
      e: `${m.reports} report${m.reports === 1 ? '' : 's'}`,
      s: st,
      dim: false,
    })),
    // [quote, who, document_id, isNegative, url] — the shape views.js renders.
    //
    // `url` IS THE FIFTH ELEMENT AND IT IS NEW. "open the source" was
    // underlined text pointing nowhere because this tuple carried only the
    // document id; `board_sections` now joins `document` for its url, and
    // views.js turns it into an anchor when the scheme is http(s).
    qs: (item.quotes || []).map((q) => [
      q.quote,
      modelName(q) || 'unattributed',
      q.document_id,
      q.polarity === 'negative',
      q.url || null,
    ]),
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
function groupFigures(m) {
  const byKey = new Map()
  for (const f of m.figures || []) {
    const model = modelName(f)
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
    const key = [model, f.value, unit].join('\u001f')
    if (!byKey.has(key)) {
      byKey.set(key, { model, value: f.value, unit, bases: [], sources: [] })
    }
    const group = byKey.get(key)
    if (f.basis && !group.bases.includes(f.basis)) group.bases.push(f.basis)
    const id = f.document_id || ''
    // ONE ENTRY PER DOCUMENT, and it carries which basis it supports so the
    // mapping survives the grouping — a reader can still see which report was
    // the vendor's statement and which was the measurement.
    const seen = group.sources.find((s) => s.id === id)
    if (seen) {
      if (f.basis && !seen.bases.includes(f.basis)) seen.bases.push(f.basis)
    } else {
      group.sources.push({ id, url: f.url || null, bases: f.basis ? [f.basis] : [] })
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
  return [...byKey.values()].map((g) => ({
    ...g,
    basis: [...g.bases].sort((a, b) => rank(a) - rank(b)).join(' · '),
  }))
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
    }
  })

  DB.posts = d.posts || []
  boardLoaded = true
  return DB
}
