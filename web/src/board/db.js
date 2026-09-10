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

const shortModel = (id) => String(id || '').split('/').pop()

/**
 * Evidence state, COUNTED and never scored.
 *
 *   contested  both praise and criticism are present. A real disagreement, and
 *              it is shown as a split rather than averaged into a middle.
 *   verified   two or more reports and no disagreement among them. This counts
 *              REPORTS; it is not a quality judgement and not a gate verdict.
 *   single     exactly one report. Its own state on purpose: one voice is not
 *              corroboration, and calling it "not discussed" would be false.
 *   none       nothing at all.
 */
function evidenceState(reports, quotes) {
  if (!reports) return 'n'
  const pol = new Set((quotes || []).map((q) => q.polarity))
  if (pol.has('positive') && pol.has('negative')) return 'c'
  return reports >= 2 ? 'v' : 's'
}

function commonFields(item) {
  const st = evidenceState(item.reports, item.quotes)
  return {
    slug: item.slug,
    name: item.name,
    card: item.definition,
    ev: String(item.reports),
    st,
    vol: '', // search volume is editorial, and absent is honest
    // One row per model named in this section. `d` and `p` stay empty: a
    // description and a price are facts from the registry, not from this quote.
    rows: (item.models || []).map((m) => ({
      m: shortModel(m.model_version_id),
      v: '',
      d: '',
      p: '',
      e: `${m.reports} report${m.reports === 1 ? '' : 's'}`,
      s: st,
      dim: false,
    })),
    // [quote, who, document_id, contested, url] — the shape views.js renders.
    //
    // `url` IS THE FIFTH ELEMENT AND IT IS NEW. "open the source" was
    // underlined text pointing nowhere because this tuple carried only the
    // document id; `board_sections` now joins `document` for its url, and
    // views.js turns it into an anchor when the scheme is http(s).
    qs: (item.quotes || []).map((q) => [
      q.quote,
      shortModel(q.model_version_id) || 'unattributed',
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
        shortModel(f.model_version_id),
        f.value,
        f.basis,
        f.unit || m.unit || '',
      ]),
    }
  })

  DB.posts = d.posts || []
  boardLoaded = true
  return DB
}
