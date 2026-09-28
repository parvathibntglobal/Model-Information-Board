import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  comparePage, listModels, fetchAll, fmtPrice, fmtTokens, BoardUnreadable,
} from '../api'
import { Badge, Notice, Unreadable } from '../components/ui'
import { IconAlert, IconSearch } from '../components/Icons'

//: The endpoint's own cap (`COMPARE_MAX` in judge/app.py). Repeated here rather
//: than fetched because the picker has to refuse BEFORE the request: a reader
//: who ticks a fourth model should be told by the control, not by a 422.
const COMPARE_MAX = 3

/**
 * Two or three models side by side — `/compare?ids=a,b[,c]`.
 *
 * THE DEMO'S TABLE HAD NINE ROWS AND THIS ONE CANNOT. Verdict, best-for, cost,
 * context and report counts all have a source in the database. Licence,
 * benchmark standing, the one-line blurb and the "core differentiation" line do
 * not — they were written by hand for the mock-up. So they are listed at the
 * bottom with the reason, rather than dropped: a shorter table with no
 * explanation reads as "the board compared everything it could", which is a
 * different and false claim.
 *
 * ADVERTISED AND REPORTED ARE NEVER IN THE SAME BLOCK. A price is the vendor's
 * claim about itself; a report count is what somebody found. The demo put
 * "Cost / M tokens" and "First-hand reports" in one column of one table, which
 * is exactly the mistake that makes a spec look like evidence. Here the two
 * halves are separated with a heading each, and the reported half says plainly
 * when it is empty.
 *
 * NO WINNER IS COMPUTED. There is no highlight on the cheapest cell, no "best
 * value" ribbon, no total. Picking a winner from a spec sheet is the
 * recommendation this board refuses to make without evidence — and with 0
 * reports on every model, a comparison IS a spec sheet and says so.
 */
export default function Compare() {
  const [sp, setSp] = useSearchParams()
  const ids = (sp.get('ids') || '').split(',').map((s) => s.trim()).filter(Boolean)
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  //: The registry, for the picker. Loaded lazily - a reader who never opens
  //: the picker never pays for it, and a comparison that renders is more
  //: urgent than a list nobody has asked for yet.
  const [roster, setRoster] = useState(null)
  //: Which sections have had their one-model axes opened, keyed by section.
  //: Per section rather than one flag, because opening Capabilities to read 59
  //: rows should not also open Metrics.
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    if (ids.length < 2) { setState({ data: null, err: null, unreadable: null }); return }
    let alive = true
    comparePage(ids)
      .then((d) => { if (alive) setState({ data: d, err: null, unreadable: null }) })
      .catch((e) => {
        if (!alive) return
        setState({
          data: null,
          err: e instanceof BoardUnreadable ? null : e.message,
          unreadable: e instanceof BoardUnreadable ? e.message : null,
        })
      })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp.get('ids')])

  //: ⚠ THE COMPARISON COULD NOT BE CHANGED FROM THE COMPARISON. `?ids=` was
  //:   read once and never written, so swapping one model meant going back to
  //:   /models, re-ticking two or three, and submitting again. The page you
  //:   land on to answer "which of these" was the one page that could not
  //:   answer "what about that one instead".
  //:
  //:   Writing the URL rather than local state on purpose: the URL IS the
  //:   comparison. A picker that held its own list would make the address bar
  //:   describe a different page from the one on screen, and this page's whole
  //:   value is that it can be sent to somebody.
  const setIds = (next) => {
    const trimmed = next.slice(0, COMPARE_MAX)
    if (trimmed.length < 2) return   // the endpoint needs two; refuse here
    setSp({ ids: trimmed.join(',') })
  }

  const dropModel = (id) => setIds(ids.filter((x) => x !== id))
  const addModel = (id) => { if (!ids.includes(id)) setIds([...ids, id]) }

  if (ids.length < 2) {
    return (
      <div className="shell section-tight stack stack-3">
        <span className="eyebrow">AI model comparison</span>
        <h1>Compare models side by side</h1>
        <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '70ch' }}>
          Tick two or three models on the{' '}
          <Link to="/models" className="mb-link">models list</Link> to compare what their
          providers advertise against what engineers have actually reported — in one view,
          with no synthesised score and no winner picked for you.
        </p>
      </div>
    )
  }

  if (state.unreadable) return <Unreadable detail={state.unreadable} />
  if (state.err) {
    return (
      <div className="shell section-tight">
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>That comparison could not be built.</strong>{' '}
          {state.err}
        </Notice>
        <p style={{ marginTop: 'var(--s3)' }}>
          <Link to="/models" className="mb-link">← All models</Link>
        </p>
      </div>
    )
  }
  if (!state.data) {
    return <div className="shell section-tight"><div className="skel" style={{ height: 260 }} /></div>
  }

  // `unsourced` is deliberately not destructured — the payload still carries
  // it and nothing on this page reads it. See the note further down.
  const { models, missing, summary } = state.data
  // ⚠ NOT `reported.reports`, AND GATING ON IT BLANKED THE PAGE. That counter
  //   comes from the legacy `cell` table and is **0 on all 348 models in the
  //   registry** (#194: `cell.status` is `insufficient` on 311 of 311), while
  //   79 models carry real board entries. It used to only add a paragraph
  //   above a table that rendered anyway, so its being permanently zero was
  //   invisible; the moment the table was gated on it, every comparison
  //   rendered empty.
  //
  //   The question this page is asking is "did anybody write about these",
  //   and the answer is in the evidence itself - entries, discovered sections
  //   - not in a score nothing has ever populated.
  const hasEvidence = (m) => {
    const r = m.reported || {}
    return (r.polarity?.entries || 0) > 0
      || (r.best_for || []).length > 0
      || (r.capabilities || []).length > 0
      || (r.discovered?.metrics || []).length > 0
  }
  const anyReports = models.some(hasEvidence)

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-2">
        <Link to="/models" className="mb-link" style={{ fontSize: 'var(--fs-xs)' }}>← All models</Link>
        <span className="eyebrow">AI model comparison</span>
        <h1>{models.map((m) => m.display_name).join('  vs  ')}</h1>
        <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '76ch' }}>{summary}</p>
      </div>

      <ChangeModels
        ids={ids}
        models={models}
        roster={roster}
        onLoad={() => fetchAll((l, o) => listModels(l, o))
          .then((d) => setRoster(d.models))
          .catch(() => setRoster([]))}
        onAdd={addModel}
        onDrop={dropModel}
      />

      {missing?.length > 0 && (
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>
            {missing.length} of the models asked for {missing.length === 1 ? 'is' : 'are'} not in
            the registry
          </strong>{' '}
          — <span className="mono">{missing.join(', ')}</span>. Named rather than dropped: a
          comparison quietly missing a column is a different comparison.
        </Notice>
      )}

      {/* ── WHAT ENGINEERS SAID. The whole page. ───────────────────────── */}

      {/* ⚠ NOBODY HAS WRITTEN ABOUT THESE: SAY IT ONCE AND STOP. This used to
             render as a table row reading "nobody has discussed this" in every
             column - the same sentence three times, under a heading, in a grid
             built for differences. A row where every cell is identical is a row
             carrying no comparison, and three of them is not three facts. */}
      {!anyReports ? (
        <p className="dim" style={{ fontSize: 'var(--fs-sm)', maxWidth: '76ch', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--text)' }}>
            Nobody has written about {models.length === 2 ? 'either' : 'any'} of these yet.
          </strong>{' '}
          So there is nothing to compare. That is an absence we found rather than a judgement
          we made — a model here may be excellent and simply unwritten-about — and it is why
          this page shows nothing instead of showing a specification and calling it a
          comparison.
        </p>
      ) : (
      <div className="stack stack-2">
        <span className="label">What engineers said, counted</span>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch' }}>
          Every number below is counted, never scored. How a report was PHRASED is counted
          separately from how many there were, because twelve complaints and twelve
          recommendations are both "12 reports" and are not the same finding.
        </p>
        <Table
          models={models}
          rows={[
            // ⚠ THIS ROW SAID "DOCUMENTS" AND MEANT SOMETHING ELSE. A
            //   document here is a Reddit post, a Hacker News COMMENT, a
            //   dev.to article or a GitHub issue reply — 29 of Claude Opus
            //   5's 92 are replies rather than posts. "92 documents" reads as
            //   92 articles, which is jargon and an overstatement at once.
            //
            //   So it names what they are, says how many are replies, and
            //   splits by platform — the last being the comparative fact,
            //   since one model discussed across five platforms and another
            //   across one are different kinds of evidence.
            ['Posts and comments', (m) => {
              const p = m.reported?.polarity || {}
              const n = p.documents || 0
              if (!n) return <span className="dim">none yet</span>
              const replies = p.replies || 0
              const platforms = p.platforms || []
              return (
                <div className="stack stack-1" style={{ gap: 2 }}>
                  <span className="tnum">
                    <strong>{n}</strong>{' '}
                    <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                      {replies > 0
                        ? `— ${n - replies} post${n - replies === 1 ? '' : 's'}, `
                          + `${replies} comment${replies === 1 ? '' : 's'}`
                        : `post${n === 1 ? '' : 's'}`}
                    </span>
                  </span>
                  {platforms.length > 0 && (
                    <span className="dim" style={{ fontSize: 10, lineHeight: 1.5 }}>
                      {platforms.map((x) => `${x.source} ${x.documents}`).join(' · ')}
                    </span>
                  )}
                </div>
              )
            }],
            // ⚠ THREE NUMBERS AND NEVER A RATIO. A net score, a percentage
            //   positive or a "sentiment" figure would be the 0-100 capability
            //   score this board refuses to compute (rule 3) - and it would
            //   pick a winner from a count of sentences.
            ['How it was phrased', (m) => {
              const p = m.reported?.polarity || {}
              if (!p.entries) return <span className="dim">nothing recorded</span>
              return (
                <span className="tnum" style={{ display: 'inline-flex', gap: 10, flexWrap: 'wrap' }}>
                  <span title="entries phrased as a problem">
                    <strong>{p.negative}</strong> negative
                  </span>
                  <span title="entries phrased as praise or a recommendation">
                    <strong>{p.positive}</strong> positive
                  </span>
                  <span className="dim" title="entries stating something without praise or complaint">
                    {p.neutral} neutral
                  </span>
                </span>
              )
            }],
            // RULE 7: the figures above are ENTRIES, and entries are not
            // people. One document can produce several, so the denominator
            // travels with them or "74 negative" means nothing.
            ['— out of', (m) => {
              const p = m.reported?.polarity || {}
              return p.entries
                ? <span className="dim tnum">{p.entries} entries, from {p.documents} posts and comments</span>
                : <span className="dim">—</span>
            }],
            // ⚠ ENTRIES PER SECTION, BECAUSE THE LIST LENGTHS BELOW ARE AXES
            //   AND NOT ENTRIES (rule 7). "63 capabilities" is 63 different
            //   things people discussed; it says nothing about how much was
            //   said. 63 axes from 70 entries is broad and thin, 12 axes from
            //   70 is narrow and heavily discussed, and the page showed only
            //   the first — so the broader model read as the better-covered
            //   one whatever the evidence behind it.
            ['Entries on the board', (m) => {
              const by = m.reported?.entries_by_section || {}
              const total = m.reported?.entries || 0
              if (!total) return <span className="dim">none</span>
              const order = ['capability', 'metric', 'best_for']
              const label = { capability: 'capability', metric: 'metric', best_for: 'job' }
              const parts = order.filter((k) => by[k]).map((k) => `${by[k]} ${label[k]}`)
              // Any section the order above does not know about, rather than
              // dropping it: a new section would otherwise vanish from a total
              // that still counts it.
              Object.keys(by).filter((k) => !order.includes(k)).forEach(
                (k) => parts.push(`${by[k]} ${k}`),
              )
              return (
                <span className="tnum">
                  <strong>{total}</strong>
                  {parts.length > 0 && (
                    <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                      {' '}— {parts.join(', ')}
                    </span>
                  )}
                </span>
              )
            }],
            // ⚠ THE HEADING SAID "BEST FOR" (NOW "JOBS", #469) AND THE ROWS ARE NOT ALL
            //   RECOMMENDATIONS. `evidence_for_model` does not filter negative
            //   `best_for` rows - deliberately, because the board's own caveat
            //   sends readers to the model page to read them - so this row can
            //   show a job whose every report is a complaint. 6 of 155
            //   model-axis pairs are in that state.
            //
            //   Not resolved here. What IS new is that the polarity renders
            //   beside each row, so a reader can see `2 of 2 negative` instead
            //   of a bare count that reads as endorsement.
            // ── THE THREE SECTIONS, ALIGNED ─────────────────────────────
            //
            // Each one contributes a heading row and then one row per axis,
            // built by `alignAxes`. They used to be three cells holding three
            // independent lists; see that function for why that was not a
            // comparison.
            ...SECTIONS.flatMap(([section, heading]) =>
              axisRows(models, section, heading, expanded, setExpanded)),
          ]}
        />
      </div>
      )}

      {/* ⚠ THE PROVIDER'S SPECIFICATION IS NOT ON THIS PAGE, 2026-09-23.

             It was the larger half: price in and out, cached read, context,
             max output, tools/vision/JSON/caching, lifecycle. All of it real
             and all of it published.

             It went because of what this board IS. The evidence here comes
             from engineers writing about models they used; a provider's spec
             sheet is the one thing on the page nobody reported, and putting it
             beside counted reports invites exactly the comparison the board
             exists to refuse - a published number read as a measured one. The
             old heading tried to hold that line in words ("the provider's
             claim about itself") and the line does not hold: a table is a
             table, and the two halves looked equally like findings.

             Price and context are still on every MODEL PAGE, where they are
             described rather than ranked, and still in `/compare`'s payload
             under `advertised` for anything that wants them.

             ⚠ WHAT THIS COSTS, SAID PLAINLY: two models nobody has written
             about now compare to almost nothing. That is the honest result -
             the board has no evidence about them - and it is better than a
             spec sheet standing in for evidence that does not exist. */}

      {/* ⚠ THE "WHAT IS NOT HERE" LIST IS GONE, 2026-09-23, and the reason is
             worth keeping because rule 4 nearly justified keeping it.

             It listed `licence`, `benchmark_standing` and `one_line` with an
             explanation each, under the argument that a shorter table with no
             explanation reads as "everything comparable has been compared".

             That argument is rule 4's and it does not reach this far. Rule 4 is
             about an absence WE CAUSED - a figure withheld by a gate, a thread
             we could not read - which a reader would otherwise take for an
             absence in the world. These three were never collected at all, so
             there is no caused absence to disclose, and the section was the
             board explaining its own history to somebody who came to compare
             two models.

             `unsourced` is still in the payload and still carries its reasons.
             If a row here ever becomes an absence we cause rather than one we
             never filled, this is where it goes back. */}

      <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Change the selection on the <Link to="/models" className="mb-link">models list</Link>.
      </p>
    </div>
  )
}

/**
 * One comparison table. Models are columns, facts are rows.
 *
 * Models across the top rather than down the side because a reader compares one
 * fact at a time — they scan a row, not a column — and because two or three
 * columns fit where two or three of these tables stacked would not.
 */
/* ⚠ `Listed`, `PLURALS` AND THE POLARITY BAR ALL LIVED HERE.

   `Listed` rendered ONE MODEL'S items as a list inside a single cell, which is
   what made this page three model pages side by side rather than a comparison.
   The rows are aligned on the slug now (`alignAxes`), so a section's axes are
   table rows and a model's count is a cell - there is no list inside a cell
   left to render.

   ⚠ ONE LESSON IS WORTH CARRYING OUT OF IT. `PLURALS` existed because
     `unit + "s"` put "15 capabilitys" on the page: English plurals are not a
     string operation and two of the three words here are exactly the ones that
     break it. It is gone rather than kept because nothing pluralises a unit any
     more - the three section headings are fixed strings, `Jobs`,
     `Capabilities`, `Metrics`. If a unit is ever derived again, this is the
     trap.

   ⚠ AND THE POLARITY BAR IS STILL GONE, along with `PolarityBar`,
     `axisPolarity` and `POLARITY_ORDER`. @parvathibntglobal removed the column
     2026-09-25. What went with it was the only surface on which a `best_for`
     row whose every report is a complaint was legible - `2 of 2 negative` under
     a heading that recommends. 6 of 155 model-axis pairs are in that state and
     this page still renders them under the board's heading. Silent again
     rather than fixed; it is @anoojntglobal-sudo's #469, which groups by
     exactly this. */

/**
 * Change the comparison without leaving it.
 *
 * ⚠ IT WRITES THE URL, NOT LOCAL STATE. The address bar IS the comparison —
 *   this page's value is that it can be sent to somebody — so a picker holding
 *   its own list would put a different comparison on screen from the one the
 *   link describes.
 *
 * ⚠ AND IT REFUSES BEFORE THE REQUEST. The endpoint caps at three and answers
 *   422 above it; a reader who clicks a fourth should be told by the control
 *   rather than by an error. Dropping below two is refused for the same
 *   reason, and the last two chips say so instead of going dead silently.
 */



function ChangeModels({ ids, models, roster, onLoad, onAdd, onDrop }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    if (open && !roster) onLoad()
    if (open) inputRef.current?.focus()
  }, [open, roster, onLoad])

  const atCap = ids.length >= COMPARE_MAX
  const atFloor = ids.length <= 2

  const matches = useMemo(() => {
    if (!roster) return []
    const q = query.trim().toLowerCase()
    return roster
      .filter((m) => !ids.includes(m.model_version_id) && !ids.includes(m.canonical_id))
      .filter((m) => !q
        || (m.display_name || '').toLowerCase().includes(q)
        || (m.canonical_id || '').toLowerCase().includes(q))
      .slice(0, 8)
  }, [roster, query, ids])

  return (
    <div className="stack stack-2">
      <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {models.map((m) => (
          <span key={m.model_version_id} className="chip" style={{ gap: 6 }}>
            {m.display_name}
            <button
              type="button"
              onClick={() => onDrop(m.model_version_id)}
              disabled={atFloor}
              title={atFloor
                ? 'A comparison needs two models. Add one before removing this.'
                : `Remove ${m.display_name} from the comparison`}
              aria-label={`Remove ${m.display_name}`}
              style={{
                background: 'none', border: 0, padding: 0, lineHeight: 1,
                cursor: atFloor ? 'not-allowed' : 'pointer',
                color: atFloor ? 'var(--text-3)' : 'var(--text-2)',
              }}
            >
              ×
            </button>
          </span>
        ))}
        <button
          type="button"
          className="chip"
          onClick={() => setOpen((v) => !v)}
          disabled={atCap && !open}
          title={atCap
            ? `Three models is the maximum — a comparison of more is a table, not a comparison.`
            : 'Add another model to this comparison'}
        >
          {open ? 'Done' : atCap ? `${COMPARE_MAX} is the maximum` : '+ Add a model'}
        </button>
      </div>

      {open && !atCap && (
        <div className="stack stack-1" style={{ maxWidth: '46ch' }}>
          <label className="searchbar" style={{ margin: 0 }}>
            <IconSearch width={15} height={15} />
            <input
              ref={inputRef}
              type="search"
              value={query}
              placeholder="Search the registry"
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          {!roster && <div className="skel" style={{ height: 80 }} />}
          {roster && matches.length === 0 && (
            <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0 }}>
              {query.trim()
                ? `No model in the registry matches "${query.trim()}".`
                : 'Every model in the registry is already in this comparison.'}
            </p>
          )}
          {roster && matches.map((m) => (
            <button
              key={m.model_version_id}
              type="button"
              className="chip"
              style={{ justifyContent: 'flex-start', width: '100%' }}
              onClick={() => { onAdd(m.canonical_id || m.model_version_id); setOpen(false); setQuery('') }}
            >
              {m.display_name}
              <span className="dim mono" style={{ fontSize: 10, marginLeft: 6 }}>
                {m.canonical_id}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}


/**
 * The union of one section's axes across the compared models, keyed by slug.
 *
 * ⚠ THIS PAGE WAS NOT COMPARING ANYTHING. Each model's jobs, capabilities and
 *   metrics rendered as three INDEPENDENT lists in three cells. If Opus 5 had
 *   `coding-agent 7` and Sonnet 5 had `coding-agent 3`, they sat at different
 *   positions in two different lists and the reader aligned them by eye. Three
 *   model pages in a row, under a heading that said comparison.
 *
 *   Aligning on the slug is what makes a row a comparison:
 *
 *       coding-agent        7            3          not reported
 *
 * ⚠ AND THE EMPTY CELL IS THE DANGEROUS PART (rule 6). "not reported" means
 *   nobody wrote about this model in these terms. It does NOT mean the model
 *   is bad at it, and it does not mean we looked and found nothing — for most
 *   of these axes we never asked. A blank, a dash or a 0 would each be read as
 *   a score of zero, which is why the cell says words instead.
 *
 *   The stacked lists could not raise this question at all, because nothing
 *   lined up. Making the comparison possible is what makes the caveat
 *   necessary.
 *
 * ⚠ THE SLUG IS THE KEY AND THE NAME IS THE LABEL. `COALESCE(ruling_target,
 *   slug)` is what the store groups by, so a reviewer merging two slugs merges
 *   these rows too. `name` is the extractor's phrasing and can differ between
 *   models for the same slug — first one wins for the label, and it is the
 *   slug that decides they are the same row.
 */
//: The three discovered sections, in the order they appear on the model page's
//: tabs. `best_for` is the stored key and "Jobs" is the word a reader sees.
const SECTIONS = [
  ['best_for', 'Jobs'],
  ['capabilities', 'Capabilities'],
  ['metrics', 'Metrics'],
]

//: How many single-model axes show before the rest go behind a toggle. The
//: SHARED ones are never capped - they are the comparison, and hiding one
//: behind "show more" would hide the thing the page is for.
const SOLO_SHOWN = 4

/**
 * One section's rows for `Table`: a heading, the aligned axes, and a toggle.
 *
 * ⚠ SHARED AXES FIRST AND NEVER TRUNCATED. An axis two models were discussed
 *   on is the only row on this page that compares anything, so all of them
 *   render however many there are.
 *
 * ⚠ THE SINGLE-MODEL AXES ARE CAPPED AND COUNTED, NOT DROPPED. Claude Opus 5
 *   alone carries 63 discovered capabilities, so a full union across three
 *   models is a table nobody reads. Four show; the rest sit behind a count
 *   that opens - a count that names what it withholds and offers no way in is
 *   the dead end this page already rejected once.
 */
function axisRows(models, section, heading, expanded, setExpanded) {
  const axes = alignAxes(models, section)
  if (!axes.length) {
    return [{
      key: `${section}-head`,
      head: heading,
      note: 'nothing named yet — an absence we found, not a verdict',
    }]
  }

  const shared = axes.filter((a) => a.named_by > 1)
  const solo = axes.filter((a) => a.named_by === 1)
  const open = expanded[section]
  const shownSolo = open ? solo : solo.slice(0, SOLO_SHOWN)
  const hidden = solo.length - shownSolo.length

  const rows = [{
    key: `${section}-head`,
    head: heading,
    // RULE 7: "12 axes" alone says nothing about whether this page can compare
    // them. The split IS the finding - three models with 60 axes between them
    // and two in common have almost nothing to compare.
    note: shared.length
      ? `${axes.length} named · ${shared.length} by more than one model`
      : `${axes.length} named · none in common, so there is nothing to line up here`,
  }]

  ;[...shared, ...shownSolo].forEach((a) => {
    rows.push([
      a.name,
      (m) => {
        const it = a.per[m.model_version_id]
        // ⚠ WORDS, NOT A DASH AND NOT A ZERO. A blank cell beside "7" reads as
        //   nought out of seven; this model was not discussed in these terms
        //   at all, and for most axes nobody ever asked (rule 6).
        if (!it) return <span className="dim" style={{ fontSize: 11 }}>not reported</span>
        const f = (it.figures || [])[0]
        return (
          <span className="stack stack-1" style={{ gap: 1 }}>
            <span className="tnum">
              <strong>{it.reports}</strong>{' '}
              <span className="dim" style={{ fontSize: 11 }}>
                report{it.reports === 1 ? '' : 's'}
              </span>
            </span>
            {/* A FIGURE TRAVELS WITH ITS BASIS (rule 7). `stated` is the
                vendor's claim, `reported` is somebody's measurement, and they
                are never merged. */}
            {f && (
              <span className="dim" style={{ fontSize: 11 }}>
                {f.value} <em style={{ fontStyle: 'normal', opacity: .75 }}>{f.basis}</em>
              </span>
            )}
          </span>
        )
      },
      'cmp-axis',
    ])
  })

  if (hidden > 0 || (open && solo.length > SOLO_SHOWN)) {
    rows.push([
      '',
      (m) => (m === models[0] ? (
        <button
          type="button"
          className="mb-link"
          style={{ background: 'none', border: 0, padding: 0, fontSize: 11, cursor: 'pointer' }}
          onClick={() => setExpanded((e) => ({ ...e, [section]: !open }))}
        >
          {open
            ? `hide the ${solo.length - SOLO_SHOWN} named by one model only`
            : `show ${hidden} more named by one model only`}
        </button>
      ) : null),
    ])
  }

  return rows
}

function alignAxes(models, section) {
  const bySlug = new Map()
  models.forEach((m) => {
    const items = m.reported?.discovered?.[section] || []
    items.forEach((it) => {
      const slug = it.slug || it.name
      if (!slug) return
      if (!bySlug.has(slug)) bySlug.set(slug, { slug, name: it.name || slug, per: {} })
      bySlug.get(slug).per[m.model_version_id] = it
    })
  })

  return [...bySlug.values()]
    .map((r) => ({
      ...r,
      named_by: Object.keys(r.per).length,
      total: Object.values(r.per).reduce((s, it) => s + (it.reports || 0), 0),
    }))
    // ⚠ ORDERED BY HOW MANY MODELS NAMED IT, THEN BY REPORTS — two counts, not
    //   a score, and both are printed on the row (rule 3). An axis two models
    //   were discussed on is the comparison; an axis only one was discussed on
    //   is a fact about that model, and it sorts below rather than being
    //   dropped.
    .sort((a, b) => b.named_by - a.named_by
      || b.total - a.total
      || a.name.localeCompare(b.name))
}

function Table({ models, rows }) {
  const rendered = rows.filter(Boolean).map((row, i) => {
    // A HEADING SPANNING THE TABLE, so the aligned sections below read as
    // three groups rather than one 90-row list. `[label, cell]` is still the
    // ordinary row; an object is the group divider.
    if (!Array.isArray(row)) return { ...row, key: row.key || `head-${i}` }
    const [label, cell, cls] = row
    return { key: `${label}-${i}`, label, cls, cells: models.map((m) => cell(m)) }
  })

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="cmp-table">
        <thead>
          <tr>
            <th />
            {models.map((m) => (
              <th key={m.model_version_id}>
                <Link
                  to={`/models/${m.model_version_id}`}
                  state={{ from: '/compare', name: m.display_name }}
                  className="mb-link"
                  style={{ color: 'inherit' }}
                >
                  {m.display_name}
                </Link>
                {/* ⚠ THE PROVIDER'S NAME, NOT OURS. This printed
                    `mv_de3e701e07b8bfa9` under every column - an internal key
                    shown to a reader, who cannot look it up, check it, or use
                    it anywhere. `canonical_id` is the same model in the form
                    the provider writes it. Omitted entirely where there is
                    none, rather than falling back to the database id. */}
                {m.canonical_id && (
                  <span className="mono" style={{
                    display: 'block', fontSize: 10, color: 'var(--text-3)', fontWeight: 400,
                  }}>
                    {m.canonical_id}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rendered.map((r) => (
            r.head ? (
              <tr key={r.key} className="cmp-group">
                <th scope="colgroup" colSpan={models.length + 1}>
                  <span className="label">{r.head}</span>
                  {r.note && (
                    <span className="dim" style={{ fontSize: 11, fontWeight: 400,
                                                   textTransform: 'none', letterSpacing: 0 }}>
                      {' '}· {r.note}
                    </span>
                  )}
                </th>
              </tr>
            ) : (
              <tr key={r.key} className={r.cls}>
                <th scope="row">{r.label}</th>
                {models.map((m, i) => <td key={m.model_version_id}>{r.cells[i]}</td>)}
              </tr>
            )
          ))}
        </tbody>
      </table>
    </div>
  )
}
