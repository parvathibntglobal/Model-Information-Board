import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  comparePage, listModels, fetchAll, fmtPrice, fmtTokens, BoardUnreadable, modelPath,
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
          <Link to="/models" className="mb-link">models list</Link> to compare what
          engineers have actually reported about them — counted, side by side, with no
          synthesised score and no winner picked for you.
          {/* ⚠ THIS PROMISED "what their providers advertise against what
              engineers have actually reported". The spec sheet came off this
              page on 2026-09-23, so the page's own empty state described a
              comparison it no longer makes - the first thing a reader sees
              before picking anything. */}
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
  const { models, missing } = state.data
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
        {/* THE NAMES WITHOUT THE VENDOR PREFIX ("Anthropic: Claude Opus 5" ->
            "Claude Opus 5"): shorter, and the form people search ("claude vs
            gpt"). The full name is still on each card below. */}
        <h1>{models.map((m) => shortName(m.display_name)).join('  vs  ')}</h1>
        {/* ONE LINE, 2026-10-01. The page opened with four blocks of method -
            the backend's summary and three paragraphs - before a single figure.
            What they said is kept, once: counted, never scored, no winner, and
            the rows lead back to the board. */}
        <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '76ch' }}>
          What engineers reported about each model, side by side, with every row linked back to the
          board. Counted, never scored — no winner is picked.
        </p>
        <HowToRead />
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

      {anyReports && (
        <>
          <HeadToHead models={models} />
          <StickyNames models={models} />
          <FaceOff models={models} />
        </>
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
          How each report was phrased is shown beside how many there were: twelve complaints and
          twelve recommendations are both "12 reports".
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
            ['Jobs — discovered', (m) => {
              const bf = m.reported?.best_for || []
              if (!bf.length) return <span className="dim">no job named yet</span>
              return <Listed unit="job" items={bf.map((b) => ({
                label: b.name, reports: b.reports,
              }))} />
            }],
            ['Discussed under', (m) => {
              const caps = m.reported?.discovered?.capabilities || []
              if (!caps.length) return <span className="dim">nothing yet</span>
              return <Listed unit="capability" items={caps.map((c) => ({
                label: c.name || c.slug, reports: c.reports,
              }))} />
            }],
            ['Metrics reported', (m) => {
              const mets = m.reported?.discovered?.metrics || []
              if (!mets.length) return <span className="dim">none</span>
              // A FIGURE TRAVELS WITH ITS BASIS (rule 7). `stated` is what the
              // vendor advertised, `reported` is what somebody measured, and
              // they are never merged into one number.
              return <Listed unit="metric" items={mets.map((x) => {
                const f = (x.figures || [])[0]
                return {
                  label: `${x.name}${f ? `: ${f.value} (${f.basis})` : ''}`,
                  reports: x.reports,
                }
              })} />
            }],
          ]}
        />

        <CommonAxes models={models} />
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
/**
 * Every item, one per line, under a count.
 *
 * ⚠ THREE VERSIONS, AND THE FIRST TWO WERE BOTH WRONG. `mets.slice(0, 3)`
 *   showed three of nine and read as three — a count with no denominator
 *   (rule 7), where a model with three metrics and one with thirty render
 *   identically. Replacing it with `+6 more` in a `title` attribute fixed the
 *   honesty and not the usefulness: a tooltip is not openable, it is invisible
 *   on touch, and @parvathibntglobal's reading is the right one — **on a
 *   comparison page the list IS the content.** Hiding it behind a hover is
 *   hiding the thing somebody came to compare.
 *
 * ⚠ AND SEMICOLON-JOINED PROSE WAS THE OTHER HALF OF THE PROBLEM. `reasoning;
 *   code generation; long context; tool use` in one cell beside the same shape
 *   in the next cell cannot be read across — the eye has no line to follow. A
 *   comparison of lists wants lists.
 *
 * So: the count first, because that is what makes two columns comparable at a
 * glance, then every item on its own line. Nothing is cut and nothing needs
 * opening. A cell with forty entries is tall, and a tall cell a reader can
 * read beats a short one they cannot.
 */
//: ⚠ "15 capabilitys" WAS ON THE PAGE. Two of the three units this component
//:   is given do not take a bare `s`, and they are the two most common.
const PLURALS = { capability: 'capabilities', job: 'jobs', metric: 'metrics' }

//: ⚠ THE POLARITY BAR IS GONE FROM THIS PAGE, and so are `PolarityBar`,
//:   `axisPolarity` and the `POLARITY_ORDER` beside them. Removed rather than
//:   left unread: a component nothing renders is the orphan of #438 one layer
//:   down, and it reads as wired from either end.
//:
//:   It showed positive/neutral/negative per axis as a proportional bar.
//:   @parvathibntglobal removed the column 2026-09-25 - the page now shows the
//:   axis and its report count, and nothing else.
//:
//: ⚠ ONE THING WENT WITH IT THAT WAS DOING REAL WORK. The bar was the only
//:   surface on which a `best_for` row whose every report is a complaint was
//:   legible: `2 of 2 negative` under a heading that recommends. 6 of 155
//:   model-axis pairs are in that state, `evidence_for_model` does not filter
//:   them, and this page renders them under the board's heading. That
//:   over-claim is now silent again rather than fixed. It is the open section
//:   question - see @anoojntglobal-sudo's #469, which groups by exactly this.

function Listed({ items, unit, upTo = 12 }) {
  if (!items.length) return null
  const shown = items.slice(0, upTo)
  const rest = items.slice(upTo)

  //: ⚠ NOT `unit + "s"`. That rendered "15 capabilitys" on the page. English
  //:   plurals are not a string operation, and two of the three words this
  //:   component is given are exactly the ones that break it.
  const plural = items.length === 1 ? unit : PLURALS[unit] || `${unit}s`

  const line = (x, i) => (
    <li key={i} className="cmp-line">
      <span className="cmp-line-name">{typeof x === 'string' ? x : x.label}</span>
      {typeof x !== 'string' && (
        <span className="cmp-line-n tnum">{x.reports}</span>
      )}
    </li>
  )

  return (
    <div className="stack stack-1" style={{ gap: 4 }}>
      {/* ⚠ THE REPEATED WORDS LIVE HERE NOW, SAID ONCE. Every line used to
          carry "reports" and "positive" — two words times thirty rows times
          three columns, and the numbers they labelled were the part a reader
          was actually trying to compare. */}
      <div className="cmp-line cmp-line-head dim">
        <span className="cmp-line-name">{items.length} {plural}</span>
        <span className="cmp-line-n">reports</span>
      </div>
      <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
        {shown.map(line)}
      </ul>
      {rest.length > 0 && (
        <details>
          <summary className="dim" style={{ fontSize: 11, cursor: 'pointer' }}>
            show the other {rest.length}
          </summary>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {rest.map((x, i) => line(x, i + upTo))}
          </ul>
        </details>
      )}
    </div>
  )
}


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


//: The three discovered sections, in the order the model page's tabs use.
//: `best_for` is the stored key and "Jobs" is the word a reader sees.
const SECTIONS = [
  ['best_for', 'Jobs'],
  ['capabilities', 'Capabilities'],
  ['metrics', 'Metrics'],
]

/**
 * The axes EVERY compared model was discussed on, keyed by slug.
 *
 * ⚠ THE TABLE ABOVE LISTS THREE MODELS AND COMPARES NONE OF THEM. Each cell
 *   holds one model's own axes, so `coding-agent 7` and `coding-agent 3` sit at
 *   different positions in two different lists and the reader aligns them by
 *   eye. That view is worth keeping — it is what each model was discussed on,
 *   in full — but the comparison is a different question and needs its own
 *   answer.
 *
 * ⚠ ALL OF THEM, NOT MOST. An axis two of three models share still leaves a
 *   cell to fill for the third, and the only honest thing to put there is
 *   "nobody wrote about this" — which is a real fact and reads as a zero
 *   (rule 6). Restricting to axes every model carries means every cell in this
 *   table is a count somebody reported, and no cell needs a caveat.
 *
 *   The cost is stated rather than hidden: axes held by some-but-not-all are
 *   counted in the note and are not rows here. They are in the table above.
 *
 * ⚠ THE SLUG IS THE KEY AND THE NAME IS THE LABEL. `COALESCE(ruling_target,
 *   slug)` is what the store groups by, so a reviewer merging two slugs merges
 *   these rows with it. `name` is the extractor's phrasing and can differ
 *   between models for one slug, so the first is used and the slug decides
 *   they are the same row.
 */
function sharedAxes(models, section) {
  const bySlug = new Map()
  models.forEach((m) => {
    (m.reported?.discovered?.[section] || []).forEach((it) => {
      const slug = it.slug || it.name
      if (!slug) return
      if (!bySlug.has(slug)) bySlug.set(slug, { slug, name: it.name || slug, per: {} })
      bySlug.get(slug).per[m.model_version_id] = it
    })
  })

  const all = [...bySlug.values()]
  const every = all.filter(
    (r) => models.every((m) => r.per[m.model_version_id])
  )
  // Ordered by total reports, which is a COUNT and not a score (rule 3): the
  // axis people wrote about most across these models leads. Every number it
  // sorts on is printed on the row.
  every.sort((a, b) => {
    const t = (r) => Object.values(r.per).reduce((s, it) => s + (it.reports || 0), 0)
    return t(b) - t(a) || a.name.localeCompare(b.name)
  })
  return { every, total: all.length }
}

/**
 * How one axis was PHRASED for one model: the three polarities, counted.
 *
 * ⚠ THIS COUNTS ENTRIES AND `reports` COUNTS DOCUMENTS, which is why the two
 *   are never shown as one number. `polarity` is a column on `board_entry`, so
 *   a split of anything else would have to be invented: a document carrying
 *   one positive and two negative entries has no polarity of its own, and
 *   giving it one is a synthesised value (rule 3).
 *
 *   The page said `1 report · 9 of 9 positive` once, which is two populations
 *   on one line reading as a proportion of the first. The fix is not to pick
 *   one - both are true and they answer different questions - it is to name
 *   the unit each belongs to.
 *
 * ⚠ NO NULLS TO HANDLE, VERIFIED RATHER THAN ASSUMED. Measured 2026-09-28 over
 *   `board_entry`: 931 positive, 638 neutral, 502 negative, zero null. An
 *   unlabelled entry would be missing from the chips and present in the total,
 *   so `other` catches anything that is not one of the three rather than
 *   letting it disappear.
 */
function polarityOf(item) {
  const q = item?.quotes || []
  const out = { positive: 0, negative: 0, neutral: 0, other: 0, total: q.length }
  q.forEach((x) => {
    const p = x.polarity
    if (p === 'positive' || p === 'negative' || p === 'neutral') out[p] += 1
    else out.other += 1
  })
  return out
}

/**
 * The three counts as chips, in the board's own polarity colours.
 *
 * ⚠ A ZERO IS DROPPED, NOT DIMMED, and that is the one judgement call here.
 *   `3 positive · 2 neutral` is read correctly as "no negatives"; a `0
 *   negative` chip beside it says the same thing louder and turns a scannable
 *   cell into nine chips across three columns. What must never be dropped is a
 *   non-zero, which is why every count present is rendered whatever its size.
 */
function Polarity({ split }) {
  if (!split.total) return <span className="dim" style={{ fontSize: 11 }}>none</span>
  const chips = [
    ['positive', 'pass'],
    ['negative', 'fail'],
    ['neutral', 'mute'],
    ['other', 'mute'],
  ].filter(([k]) => split[k] > 0)

  return (
    <span className="row" style={{ gap: 4, flexWrap: 'wrap' }}>
      {chips.map(([k, tone]) => (
        <Badge key={k} tone={tone}>
          <span className="tnum">{split[k]}</span>{' '}
          {/* ⚠ THE WORD, NOT JUST THE COLOUR. Three coloured numbers with no
              labels is identity by colour alone, and red/green is the pair
              most readers lose. */}
          {k === 'other' ? 'unlabelled' : k}
        </Badge>
      ))}
    </span>
  )
}

/**
 * Only the axes all the compared models share, as a count-against-count table.
 *
 * Separate from the table above on purpose. That one answers "what was each of
 * these discussed on"; this one answers "where can these actually be compared",
 * and merging them produced a table where most cells said "not reported".
 */
function CommonAxes({ models }) {
  const groups = SECTIONS.map(([section, heading]) => ({
    section, heading, ...sharedAxes(models, section),
  }))
  const shared = groups.reduce((s, g) => s + g.every.length, 0)
  const named = groups.reduce((s, g) => s + g.total, 0)

  return (
    <div className="stack stack-2" style={{ marginTop: 'var(--s4)' }}>
      <span className="label">Where they can be compared directly</span>
      <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0,
                                  lineHeight: 1.6 }}>
        The axes <strong style={{ color: 'var(--text)' }}>every model here was
        discussed on</strong>, so each row is a count against a count with nothing
        missing. {/* RULE 7: the denominator. "4 shared" means one thing out of 12
                     and another out of 200. */}
        <span className="tnum">{shared}</span> of{' '}
        <span className="tnum">{named}</span> axes named across these{' '}
        {models.length} models. The rest were named for some and not others — they
        are in the table above, where an absent axis is simply not listed rather
        than being shown as a nought.
        {/* ⚠ SAID ONCE HERE RATHER THAN IN EVERY CELL. Three columns times
            however many rows is no place to explain a unit, and the cells
            carry the three numbers so a reader who wants to check can. */}
        {' '}The chips count <strong style={{ color: 'var(--text)' }}>entries</strong>,
        which is what a polarity belongs to. One post can carry several, so the
        entry count is not a count of people — the posts and the people are under
        each cell for exactly that reason.
      </p>

      {shared === 0 ? (
        /* ⚠ AN EMPTY TABLE HERE IS A FINDING, AND IT IS ABOUT THE CORPUS AND
           NOT THE MODELS. Engineers wrote about these models on different
           things; that is what the evidence says, and it is why the board
           cannot rank them against each other. Rendering an empty table with
           three column headings would say "we compared them and found
           nothing", which is a different and false claim. */
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0,
                                    lineHeight: 1.6 }}>
          <strong style={{ color: 'var(--text)' }}>No axis is shared by all{' '}
          {models.length}.</strong> Nobody has written about these models on the
          same job, behaviour or figure, so there is nothing to put side by side —
          a fact about what has been written, not about the models. Comparing two
          instead of three usually finds more.
        </p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="cmp-table">
            <thead>
              <tr>
                <th />
                {models.map((m) => (
                  <th key={m.model_version_id}>
                    {m.display_name}
                    {/* ⚠ THE PROVIDER'S NAME, NOT OURS, AND OMITTED RATHER
                        THAN FALLEN BACK. Same rule as the table above: a
                        reader cannot look up `mv_de3e701e07b8bfa9`, check it
                        or use it anywhere, so printing it is worse than
                        printing nothing.

                        This header shipped without it and the page's own test
                        did not catch it, because that test sliced the FIRST
                        `<thead>` and this table now comes first in the file.
                        It checks every header now. */}
                    {m.canonical_id && (
                      <span className="mono" style={{
                        display: 'block', fontSize: 10,
                        color: 'var(--text-3)', fontWeight: 400,
                      }}>
                        {m.canonical_id}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.filter((g) => g.every.length).map((g) => (
                <Fragment key={g.section}>
                  <tr className="cmp-group">
                    <th scope="colgroup" colSpan={models.length + 1}>
                      <span className="label">{g.heading}</span>
                      <span className="dim" style={{ fontSize: 11, fontWeight: 400,
                                                     textTransform: 'none', letterSpacing: 0 }}>
                        {' '}· {g.every.length} of {g.total} shared
                      </span>
                    </th>
                  </tr>
                  {g.every.map((a) => {
                    // The axis page is the same for every model, so it is read
                    // off whichever model's item carries it.
                    const axisPath = Object.values(a.per).find((it) => it.board_path)?.board_path
                    return (
                    <tr key={a.slug} className="cmp-axis">
                      <th scope="row">
                        {/* ⚠ THE AXIS LINKS TO WHERE ITS RANKING ALREADY LIVES,
                            rather than this page ranking it again. The board
                            orders every Jobs and Capabilities page by the rule in
                            `contract/board_ordering.yaml`; a second copy here would
                            be one more place for the two to disagree. Compare
                            stays counts, the board stays order, one click apart.

                            Plain text where the board has no page for this axis -
                            never a link that lands on nothing. `board_path` is
                            None exactly then, because the backend asked the
                            board's own function rather than assuming. */}
                        {axisPath
                          ? <Link to={`/board/${axisPath}`} className="mb-link"
                                  state={{ from: '/compare' }}
                                  title="See every model reported on this, in the board's order">
                              {a.name}
                            </Link>
                          : a.name}
                      </th>
                      {models.map((m) => {
                        const it = a.per[m.model_version_id]
                        const f = (it.figures || [])[0]
                        const split = polarityOf(it)
                        return (
                          <td key={m.model_version_id}>
                            {/* ⚠ THE CELL OPENS THIS MODEL'S REPORTS ON THIS AXIS,
                                which is where the quotes already are. The board's
                                claim is verbatim evidence and this table shows
                                counts; the link is what makes a count checkable
                                without a second copy of the quotes living here. */}
                            {it.board_model_path
                              ? <Link to={`/board/${it.board_model_path}`}
                                      state={{ from: '/compare' }}
                                      className="cmp-cell-link"
                                      title="Read what was said about this model here">
                                  <Polarity split={split} />
                                </Link>
                              : <Polarity split={split} />}
                            {/* ⚠ THREE COUNTS, ALL MEASURED, NONE DERIVED, and
                                the second and third are what stop the first
                                being read as people.

                                The chips split ENTRIES, because that is the
                                only population `polarity` exists on - it is a
                                column on `board_entry`. A document can carry
                                several entries for one axis, and does:
                                `metric/swe-bench` is 8 entries from ONE
                                document by ONE person, and 82 of 495 axis
                                rows run at 2x or more.

                                So an entry count alone would let one voluble
                                writer outrank four people. The line says
                                which number is which rather than picking one
                                (rule 7). */}
                            <span className="dim tnum"
                                  style={{ display: 'block', fontSize: 10, marginTop: 3 }}>
                              {split.total} {split.total === 1 ? 'entry' : 'entries'}
                              {' · '}{it.reports} post{it.reports === 1 ? '' : 's'}
                              {it.voices != null && (
                                <>{' · '}{it.voices} {it.voices === 1 ? 'person' : 'people'}</>
                              )}
                            </span>
                            {/* A FIGURE TRAVELS WITH ITS BASIS (rule 7).
                                `stated` is the vendor's claim and `reported` is
                                somebody's measurement; they are never merged. */}
                            {f && (
                              <span className="dim" style={{ display: 'block', fontSize: 11 }}>
                                {f.value} {f.basis}
                              </span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                    )
                  })}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ⚠ NO ROW IS MARKED AS A WINNER, and the higher count is not the
          better model. It is how many people wrote about it, which tracks how
          widely a model is used at least as much as how well it works — and
          the polarity of those reports is not on this table at all. */}
      {shared > 0 && (
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0,
                                    lineHeight: 1.6 }}>
          A bigger number is more writing, not a better model: it tracks how widely
          something is used as much as how well it works. The colours say how each
          entry was phrased and not whether it was right — open a model to read
          the quotes behind any of these.
        </p>
      )}
    </div>
  )
}

function Table({ models, rows }) {
  const rendered = rows.map(([label, cell]) => ({
    label,
    cells: models.map((m) => cell(m)),
  }))

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
            <tr key={r.label}>
              <th scope="row">{r.label}</th>
              {models.map((m, i) => <td key={m.model_version_id}>{r.cells[i]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


/* ══════════════════════════════════════════════════════════════════════
   THE SHOWCASE PARTS, added 2026-10-01: the method text collapsed, a
   head-to-head header, a names bar that stays on screen, and one quote per
   model on the sections they share, with how each was chosen.
   None of them scores or ranks: every number is a count already on this
   page, and no cell is compared against another model's.
   ══════════════════════════════════════════════════════════════════════ */

/** The page's method, kept but folded away: the short line above says it. */
function HowToRead() {
  return (
    <details className="cmp-how">
      <summary>How to read this comparison</summary>
      <ul>
        <li>Every number is a count of what engineers wrote. Nothing is scored and no winner is picked.</li>
        <li>A bigger number is more people writing, not a better model.</li>
        <li>Positive, negative and neutral say how each report was phrased, not whether it was right.</li>
        <li>A model nobody has written about is an absence we found, not a verdict.</li>
        <li>Every row links back to the board, where each section lists all its models.</li>
      </ul>
    </details>
  )
}

const modelLink = (m) => `/models/${modelPath(m.canonical_id || m.model_version_id)}`

/** One card per model: who it is and what was written about it, counted. */
function HeadToHead({ models }) {
  return (
    <div className="h2h" style={{ '--n': models.length }}>
      {models.map((m, i) => {
        const pol = m.reported?.polarity || {}
        const platforms = (pol.platforms || []).length
        const split = { positive: pol.positive || 0, negative: pol.negative || 0, neutral: pol.neutral || 0,
                        other: 0, total: pol.entries || 0 }
        return (
          <Fragment key={m.model_version_id}>
            {i > 0 && <span className="h2h-vs" aria-hidden="true">vs</span>}
            <div className="h2h-card">
              <span className="label">{m.provider}</span>
              <Link to={modelLink(m)} className="h2h-name">{m.display_name}</Link>
              {m.canonical_id && <span className="mono dim h2h-id">{m.canonical_id}</span>}
              {split.total ? (
                <>
                  <span className="tnum h2h-n">
                    <b>{split.total}</b> {split.total === 1 ? 'entry' : 'entries'}
                    {pol.documents != null && <> · <b>{pol.documents}</b> {pol.documents === 1 ? 'post' : 'posts'}</>}
                    {platforms > 0 && <> · <b>{platforms}</b> {platforms === 1 ? 'platform' : 'platforms'}</>}
                  </span>
                  <Polarity split={split} />
                </>
              ) : (
                <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>Nobody has written about it yet.</span>
              )}
            </div>
          </Fragment>
        )
      })}
    </div>
  )
}

/** The model names, kept on screen under the nav while the tables scroll. */
function StickyNames({ models }) {
  return (
    <div className="cmp-sticky" aria-hidden="true">
      {models.map((m, i) => (
        <Fragment key={m.model_version_id}>
          {i > 0 && <span className="cmp-sticky-vs">vs</span>}
          <span className="cmp-sticky-name">{m.display_name}</span>
        </Fragment>
      ))}
    </div>
  )
}

/* A quote that reads on its own: says something either way if it can, and is
   short enough for a card. Chosen for length and phrasing only - never for
   which model it favours. */
function quoteFor(item) {
  const qs = item?.quotes || []
  const fits = (q) => q.quote && q.quote.length >= 40 && q.quote.length <= 220
  return qs.find((q) => q.polarity !== 'neutral' && fits(q)) || qs.find(fits) || qs[0] || null
}

const hostName = (url) => {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return '' }
}

const FACEOFF_ROWS = 4

/** On the sections every model shares, one quote from each, side by side. */
function FaceOff({ models }) {
  const rows = [['best_for', 'Jobs'], ['capabilities', 'Capabilities']]
    .flatMap(([section, heading]) => sharedAxes(models, section).every.map((a) => ({ ...a, heading })))
    .slice(0, FACEOFF_ROWS)
  if (!rows.length) return null
  return (
    <div className="stack stack-2">
      <span className="label">In their words</span>
      {/* HOW THE QUOTES WERE CHOSEN, said on the page: without it a reader
          cannot tell a picked quote from a fair one. The rule is quoteFor's. */}
      <p className="faceoff-basis">
        <span className="faceoff-i" aria-hidden="true">i</span>
        <span>
          The {rows.length === 1 ? 'section' : `${rows.length} sections`} both models were discussed on most.
          For each, the first report on the board that says something clearly either way and fits on a
          card — chosen by wording and length, never by which model it favours. Open a section to read
          every report.
        </span>
      </p>
      <div className="faceoff">
        {rows.map((a) => {
          const axisPath = Object.values(a.per).find((it) => it.board_path)?.board_path
          return (
            <div key={a.slug} className="faceoff-row">
              <div className="faceoff-axis">
                <span className="faceoff-k">{a.heading}</span>
                {axisPath
                  ? <Link to={`/board/${axisPath}`} className="mb-link">{a.name}</Link>
                  : <span>{a.name}</span>}
              </div>
              <div className="faceoff-quotes" style={{ '--n': models.length }}>
                {models.map((m) => {
                  const q = quoteFor(a.per[m.model_version_id])
                  return (
                    <figure key={m.model_version_id} className="faceoff-q" data-polarity={q?.polarity || 'none'}>
                      <span className="faceoff-model">{m.display_name}</span>
                      {q ? (
                        <>
                          <blockquote>“{q.quote}”</blockquote>
                          <figcaption>
                            <span className="faceoff-pol">{q.polarity}</span>
                            {q.url && <> · <a href={q.url} target="_blank" rel="nofollow noopener noreferrer">{hostName(q.url)}</a></>}
                          </figcaption>
                        </>
                      ) : <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>no quote recorded</span>}
                    </figure>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** "Anthropic: Claude Opus 5" -> "Claude Opus 5". A name with no prefix is kept. */
function shortName(name) {
  const n = String(name || '')
  return n.includes(': ') ? n.split(': ').slice(1).join(': ') : n
}
