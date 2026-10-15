import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  comparePage, listModels, fetchAll, fmtPrice, fmtTokens, BoardUnreadable, modelPath, modelCatalog,
} from '../api'
import { Badge, Notice, Unreadable } from '../components/ui'
import { IconAlert, IconSearch } from '../components/Icons'
import Freshness from '../components/Freshness'
import { useHead } from '../seo/head'
import { comparePage as compareHead } from '../seo/pages'

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
  // OPENED FROM REPORTS (`?from=reports`, 2026-10-14). Reports is counts only and
  // never quotes, so a comparison started there leaves out "In their words".
  // Opened from the Models list, the page is unchanged.
  const fromReports = sp.get('from') === 'reports'
  const ids = (sp.get('ids') || '').split(',').map((s) => s.trim()).filter(Boolean)
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  //: The registry, for the picker. Loaded lazily - a reader who never opens
  //: the picker never pays for it, and a comparison that renders is more
  //: urgent than a list nobody has asked for yet.
  const [roster, setRoster] = useState(null)
  // PER-PAGE <head> (seo/pages.js): names once the comparison has loaded.
  useHead(compareHead(ids, (state.data?.models || []).map((m) => m.display_name)))

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
    // keep `from` so changing the models does not bring the quotes back
    setSp(fromReports ? { ids: trimmed.join(','), from: 'reports' } : { ids: trimmed.join(',') })
  }

  const dropModel = (id) => setIds(ids.filter((x) => x !== id))
  const addModel = (id) => { if (!ids.includes(id)) setIds([...ids, id]) }

  if (ids.length < 2) {
    return (
      <div className="shell section-tight stack stack-3">
        <span className="eyebrow">AI model comparison</span>
        <h1>Compare models side by side</h1>
        <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '70ch' }}>
          Pick two or three models to compare what engineers have actually reported
          about them — counted, side by side, with no synthesised score and no winner
          picked for you.
          {/* ⚠ THIS PROMISED "what their providers advertise against what
              engineers have actually reported". The spec sheet came off this
              page on 2026-09-23, so the page's own empty state described a
              comparison it no longer makes - the first thing a reader sees
              before picking anything. */}
        </p>
        <StartCompare picked={ids}
                      onCompare={(chosen) => setSp(fromReports ? { ids: chosen.join(','), from: 'reports' } : { ids: chosen.join(',') })} />
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
        {!fromReports && (
          <p style={{ marginTop: 'var(--s3)' }}>
            <Link to="/catalog" className="mb-link">← All models</Link>
          </p>
        )}
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
        {/* NO "← All models" FROM REPORTS: the reader came from Reports → AI
            models, not from the models list. */}
        {!fromReports && <Link to="/catalog" className="mb-link" style={{ fontSize: 'var(--fs-xs)' }}>← All models</Link>}
        <span className="eyebrow">AI model comparison</span>
        {/* THE NAMES WITHOUT THE VENDOR PREFIX ("Anthropic: Claude Opus 5" ->
            "Claude Opus 5"): shorter, and the form people search ("claude vs
            gpt"). The full name is still on each card below. */}
        <h1>{models.map((m) => shortName(m.display_name)).join('  vs  ')}</h1>
        <Freshness modelIds={models.map((m) => m.model_version_id)} />
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
          <SameTest models={models} />
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
        {/* ⚠ "WHAT ENGINEERS SAID, COUNTED" CAME OFF THIS PAGE 2026-10-15, at the
            product owner's request: the per-model table of posts, platforms and
            every job, capability and metric with its entry count. What it alone
            showed - a section only ONE of the models was discussed on - is not
            on this page any more; each model's own page still lists them all.
            What stays is where the models CAN be compared: the sections they
            share, with how each report was phrased, and the metrics' figures. */}
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
        Change the selection on {fromReports
          ? <Link to="/reports" className="mb-link">Models</Link>
          : <>the <Link to="/catalog" className="mb-link">models list</Link></>}.
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

/**
 * PICK THE MODELS, ON THE PAGE (2026-10-14). The page opened from the Models
 * menu used to say "tick two or three models on the models list" and link to
 * the roster behind sign-in, so a comparison could not be started from here.
 * Now it searches the models we collect reports for - a comparison is of what
 * engineers reported, so a model we do not track would be an empty column -
 * most engineer voices first. `picked` arrives from the address: a model
 * page's "Compare with" opens this with its model already chosen.
 */
function StartCompare({ picked, onCompare }) {
  const [chosen, setChosen] = useState(picked)
  const [query, setQuery] = useState('')
  const [models, setModels] = useState(null)
  useEffect(() => {
    let alive = true
    modelCatalog()
      .then((v) => alive && setModels((v.models || []).filter((m) => m.in_registry)
        .sort((a, b) => b.voices - a.voices || a.name.localeCompare(b.name))))
      .catch(() => alive && setModels([]))
    return () => { alive = false }
  }, [])
  const byId = useMemo(() => Object.fromEntries((models || []).map((m) => [m.id, m])), [models])
  const q = query.trim().toLowerCase()
  const matches = (models || [])
    .filter((m) => !chosen.includes(m.id))
    .filter((m) => !q || m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q))
    .slice(0, 10)
  const atCap = chosen.length >= COMPARE_MAX
  return (
    <div className="card stack stack-3" style={{ maxWidth: 720 }}>
      <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {chosen.length === 0 && <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>No model picked yet.</span>}
        {chosen.map((id) => (
          <span key={id} className="chip chip-on" style={{ gap: 6 }}>
            {byId[id]?.name || id}
            <button type="button" onClick={() => setChosen(chosen.filter((x) => x !== id))}
                    aria-label={`Remove ${byId[id]?.name || id}`}
                    style={{ background: 'none', border: 0, padding: 0, lineHeight: 1, cursor: 'pointer', color: 'inherit' }}>×</button>
          </span>
        ))}
        <button type="button" className="btn btn-primary" disabled={chosen.length < 2}
                onClick={() => onCompare(chosen)} style={{ marginLeft: 'auto' }}
                title={chosen.length < 2 ? 'A comparison needs two models' : undefined}>
          Compare {chosen.length >= 2 ? chosen.length : ''} models
        </button>
      </div>
      {!atCap && (
        <label className="stack stack-1">
          <span className="label">Search models · up to {COMPARE_MAX}</span>
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)}
                 placeholder="Type a model, such as Claude Opus 5 or GPT-6 Astra" className="input" />
        </label>
      )}
      {!atCap && (models == null ? <div className="skel" style={{ height: 120 }} /> : (
        <div className="stack stack-1">
          {matches.map((m) => (
            <button key={m.id} type="button" className="row" onClick={() => { setChosen([...chosen, m.id]); setQuery('') }}
                    style={{ justifyContent: 'space-between', gap: 12, padding: '8px 10px', borderRadius: 8,
                      background: 'var(--surface)', border: '1px solid var(--border-soft)', color: 'var(--text)',
                      cursor: 'pointer', font: 'inherit', textAlign: 'left' }}>
              <span>{m.name} <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{m.id}</span></span>
              <span className="dim" style={{ fontSize: 'var(--fs-xs)', whiteSpace: 'nowrap' }}>
                {m.voices ? `${m.voices} ${m.voices === 1 ? 'voice' : 'voices'}` : 'no voices yet'}
              </span>
            </button>
          ))}
          {matches.length === 0 && <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>No tracked model matches “{query}”.</span>}
        </div>
      ))}
      {atCap && <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>{COMPARE_MAX} is the maximum - a comparison of more is a table, not a comparison.</span>}
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
  // METRICS ARE NOT COUNTED HERE (2026-10-15): "Measured in the same test"
  // shows their figures, where a count of entries per axis said nothing a
  // reader could compare.
  const groups = SECTIONS.filter(([section]) => section !== 'metrics').map(([section, heading]) => ({
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

// THE MODEL'S PAGE IN THE NEW DESIGN (2026-10-15): price, workload cost, specs
// and voices (/catalog/model/...). Was /models, the roster behind sign-in.
const modelLink = (m) => `/catalog/model/${modelPath(m.canonical_id || m.model_version_id)}`

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

/* ══════════════════════════════════════════════════════════════════════
   MEASURED IN THE SAME TEST (2026-10-15). Replaces "In their words", the one
   quote per model per section: one report of many cannot summarise a model,
   and picking it - however fairly - was the page choosing what a model is.

   A figure is comparable with another only when the same engineer measured
   both models in the same test: same task, same setup, same unit. So a row
   here is ONE POST that reports a measured figure for two or more of the
   compared models on one axis, and the figures sit side by side exactly as
   written. Nothing is parsed, averaged, converted or ranked (rule 3), and no
   cell is highlighted as better.

   LEFT OUT, AND SAID SO:
     - figures from SEPARATE tests: "$0.17 per task" and "$14.50 per task"
       came from different tasks, and side by side they read as a comparison
       they are not;
     - figures a post only QUOTES from a provider (basis 'stated' - list
       prices, advertised context): claims, not measurements. Measured on the
       local copy 2026-10-15, about half of all shown figures are of this
       kind, some of them out of date.
   ══════════════════════════════════════════════════════════════════════ */

const PLATFORM = { devto: 'dev.to', hackernews: 'Hacker News', github: 'GitHub', blog: 'a blog', huggingface: 'Hugging Face' }
const platformOf = (docId) => PLATFORM[String(docId || '').split(':')[0]] || 'the post'

/** Posts that measured two or more of these models on one axis, by axis. */
function sameTests(models) {
  const byKey = new Map()
  const quotedOnly = new Map()
  models.forEach((m) => {
    (m.reported?.discovered?.metrics || []).forEach((it) => {
      (it.figures || []).forEach((f) => {
        if (!f.document_id) return
        const k = `${it.slug}|${f.document_id}`
        const into = f.basis === 'reported' ? byKey : quotedOnly
        if (!into.has(k)) into.set(k, { slug: it.slug, name: it.name || it.slug, unit: it.unit, doc: f.document_id, url: f.url, per: {} })
        const row = into.get(k)
        const vals = (row.per[m.model_version_id] ||= [])
        if (!vals.includes(f.value)) vals.push(f.value)
      })
    })
  })
  const together = (map) => [...map.values()].filter((r) => Object.keys(r.per).length >= 2)
  const bySlug = new Map()
  together(byKey).forEach((t) => {
    if (!bySlug.has(t.slug)) bySlug.set(t.slug, { slug: t.slug, name: t.name, unit: t.unit, tests: [] })
    bySlug.get(t.slug).tests.push(t)
  })
  // Ordered by how many tests measured the axis - a count shown on each
  // heading - then by name. Never by any figure.
  const axes = [...bySlug.values()].sort((a, b) => b.tests.length - a.tests.length || a.name.localeCompare(b.name))
  const quoted = new Set(together(quotedOnly).map((t) => t.doc)).size
  return { axes, quoted }
}

function SameTest({ models }) {
  const { axes, quoted } = sameTests(models)
  const n = models.length
  const some = n === 2 ? 'both' : 'two or more'
  return (
    <div className="stack stack-2" style={{ marginTop: 'var(--s4)' }}>
      <span className="label">Measured in the same test</span>
      <p className="st-basis">
        <span className="st-i" aria-hidden="true">i</span>
        <span>
          Where one engineer measured {some} of these models in the same test, the figures can be read
          against each other: same task, same setup. Each row is one test, the figures exactly as written,
          linked to the post. Nothing is averaged, converted or ranked, and axes are ordered by how many
          tests measured them. Figures from separate tests are left out, because they measured different things.
        </span>
      </p>
      {axes.length === 0 ? (
        <p className="dim" style={{ fontSize: 'var(--fs-sm)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
          <strong style={{ color: 'var(--text)' }}>No single test measured {some} of these models.</strong>{' '}
          Figures measured in separate tests are not comparable, so they are not lined up here; each
          model&apos;s page lists the figures measured for it.
        </p>
      ) : (
        // ONE TABLE: the model names once, then a row per test - the axis, its
        // unit and the post on the left, the figures under each model.
        <div className="st-grid" style={{ '--n': n }}>
          <div className="st-tr st-th">
            <span>Axis · measured in</span>
            {models.map((m) => <span key={m.model_version_id}>{shortName(m.display_name)}</span>)}
          </div>
          {axes.flatMap((a) => a.tests.map((t, k) => (
            <div key={`${a.slug}|${t.doc}`} className="st-tr">
              <span className="st-axis-cell">
                <b>{a.name}</b>
                {a.tests.length > 1 && <span className="dim tnum"> · test {k + 1} of {a.tests.length}</span>}
                <span className="st-src">
                  {a.unit && <>{a.unit} · </>}
                  {t.url
                    ? <a href={t.url} target="_blank" rel="noopener noreferrer">{platformOf(t.doc)} ↗</a>
                    : platformOf(t.doc)}
                </span>
              </span>
              {models.map((m) => {
                const v = t.per[m.model_version_id]
                return (
                  <span key={m.model_version_id} className="st-cell">
                    <span className="st-cell-name">{shortName(m.display_name)}</span>
                    {v
                      ? v.map((x) => <span key={x} className="st-fig">{x}</span>)
                      : <span className="st-none">not in this test</span>}
                  </span>
                )
              })}
            </div>
          )))}
        </div>
      )}
      {quoted > 0 && (
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0 }}>
          {quoted} {quoted === 1 ? 'post' : 'posts'} only quoted the providers&apos; own figures for these models
          (list prices, advertised context) and {quoted === 1 ? 'is' : 'are'} left out: claims, not measurements.
        </p>
      )}
    </div>
  )
}

/** "Anthropic: Claude Opus 5" -> "Claude Opus 5". A name with no prefix is kept. */
function shortName(name) {
  const n = String(name || '')
  return n.includes(': ') ? n.split(': ').slice(1).join(': ') : n
}
