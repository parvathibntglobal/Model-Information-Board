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
              const label = { capability: 'capability', metric: 'metric', best_for: 'best-for' }
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
            // ⚠ THE HEADING SAYS "BEST FOR" AND THE ROWS ARE NOT ALL
            //   RECOMMENDATIONS. `evidence_for_model` does not filter negative
            //   `best_for` rows - deliberately, because the board's own caveat
            //   sends readers to the model page to read them - so this row can
            //   show a job whose every report is a complaint. 6 of 155
            //   model-axis pairs are in that state.
            //
            //   Not resolved here. What IS new is that the polarity renders
            //   beside each row, so a reader can see `2 of 2 negative` instead
            //   of a bare count that reads as endorsement.
            ['Best for — discovered', (m) => {
              const bf = m.reported?.best_for || []
              if (!bf.length) return <span className="dim">no job named yet</span>
              return <Listed unit="job" items={bf.map((b) => ({
                label: b.name, reports: b.reports,
                polarity: axisPolarity(m, 'best_for', b.slug),
              }))} />
            }],
            ['Discussed under', (m) => {
              const caps = m.reported?.discovered?.capabilities || []
              if (!caps.length) return <span className="dim">nothing yet</span>
              return <Listed unit="capability" items={caps.map((c) => ({
                label: c.name || c.slug, reports: c.reports,
                polarity: axisPolarity(m, 'capability', c.slug),
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
                  polarity: axisPolarity(m, 'metric', x.slug),
                }
              })} />
            }],
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
/**
 * How one axis was phrased, as a proportional bar.
 *
 * FORM CHOSEN BEFORE COLOR, per the visualization guidance: positive /
 * neutral / negative is an ordered-scale share — Likert-shaped — and the
 * default form for that is a **stacked bar with a neutral midpoint**, not a
 * number and not a pie of two slices.
 *
 * ⚠ THREE WORDS PER ROW, ON UP TO 33 ROWS, IN THREE COLUMNS WAS THE PROBLEM.
 *   Each line read `Reasoning — 5 reports  3 of 5 positive`: the words
 *   "reports" and "positive" repeated on every line of every column, and the
 *   eye had nothing to compare because line lengths varied with the name. The
 *   repeated words move to the column header, said once, and the numbers
 *   become a mark the eye can scan down.
 *
 * ⚠ AND THE BAR IS A PROPORTION, WHICH REMOVES A CONTRADICTION. The line used
 *   to carry `1 report · 9 of 9 positive` — true twice over, since `reports`
 *   counts documents and the split counts entries, and one document can carry
 *   nine. A proportion has no denominator to disagree with the number beside
 *   it, and the exact counts are in the title.
 *
 * COLOR: the repository's own `--fail` / `--pass` with a neutral grey between
 * them — a diverging pair with a grey midpoint, which is the rule for
 * polarity. Validated against the dark surface with the skill's script: CVD
 * separation ΔE 8.5 (protan), normal-vision 16.7, contrast ≥ 3:1 on all
 * three. Its lightness-band and chroma-floor checks fail by design on a
 * diverging ramp and are not applicable here.
 *
 * A 2px surface gap separates the segments, so identity does not rest on hue
 * alone for a reader who cannot tell the two poles apart.
 */
//: ⚠ "15 capabilitys" WAS ON THE PAGE. Two of the three units this component
//:   is given do not take a bare `s`, and they are the two most common.
const PLURALS = { capability: 'capabilities', job: 'jobs', metric: 'metrics' }

const POLARITY_ORDER = [
  ['negative', 'var(--fail)'],
  ['neutral', 'var(--text-3)'],
  ['unrecorded', 'var(--text-3)'],
  ['positive', 'var(--pass)'],
]

function PolarityBar({ counts }) {
  if (!counts) return null
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  if (!total) return null
  const segments = POLARITY_ORDER
    .filter(([key]) => counts[key] > 0)
    .map(([key, color]) => ({ key, color, n: counts[key] }))
  return (
    <span
      role="img"
      aria-label={segments.map((x) => `${x.n} ${x.key}`).join(', ')}
      title={`${segments.map((x) => `${x.n} ${x.key}`).join(' · ')}`
             + ` — ${total} board entr${total === 1 ? 'y' : 'ies'}`}
      style={{
        display: 'inline-flex', gap: 2, width: 64, height: 6,
        borderRadius: 3, overflow: 'hidden', flex: '0 0 auto',
      }}
    >
      {segments.map((x) => (
        <span
          key={x.key}
          style={{ background: x.color, width: `${(x.n / total) * 100}%`,
                   borderRadius: 2 }}
        />
      ))}
    </span>
  )
}


//: `{section}:{slug}` is the key the endpoint builds, and the section names
//: are the DATABASE's - `capability`, singular - not the payload's plural
//: `capabilities`. Getting that wrong returns undefined and renders nothing,
//: which looks exactly like an axis with no entries.
function axisPolarity(m, section, slug) {
  return (m.reported?.polarity?.by_axis || {})[`${section}:${slug}`]
}


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
        <>
          <span className="cmp-line-n tnum">{x.reports}</span>
          <PolarityBar counts={x.polarity} />
        </>
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
        <span style={{ width: 64, flex: '0 0 auto' }}>how it went</span>
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
