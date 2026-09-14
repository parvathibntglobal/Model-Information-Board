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
      rows: (m.figures || []).map((f) => [
        modelName(f),
        f.value,
        f.basis,
        f.unit || m.unit || '',
      ]),
      // THE SOURCE, PARALLEL TO `rows` RATHER THAN INSIDE IT.
      //
      // `document_id` has always been on every figure and this file dropped it,
      // so the only thing distinguishing two rows was discarded before render.
      // Thirteen SWE-bench figures from THREE articles rendered as thirteen
      // unattributed lines, and two of them were the same article twice — which
      // reads as corroboration and is one report. That is the same inflation
      // `board_entries.py` fixed for `reports` on 2026-09-11, reaching the page
      // by a second route.
      //
      // Kept OUT of `rows` deliberately: views.js escapes every cell of `rows`
      // with esc(), which is what makes that loop safe to render. A cell that
      // had to carry an anchor would make the cells polymorphic and put an
      // un-escaped branch inside the generic table. One controlled column
      // instead, built here and rendered explicitly there.
      srcs: (m.figures || []).map((f) => ({
        id: f.document_id || '',
        url: f.url || null,
      })),
    }
  })

  DB.posts = d.posts || []
  boardLoaded = true
  return DB
}
