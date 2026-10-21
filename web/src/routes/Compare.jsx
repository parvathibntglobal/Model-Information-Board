import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  comparePage, listModels, fetchAll, fmtPrice, fmtTokens, BoardUnreadable, modelPath, modelCatalog,
} from '../api'
import { Badge, Notice, Unreadable } from '../components/ui'
import { IconAlert, IconSearch } from '../components/Icons'
import Freshness from '../components/Freshness'
import { getSession } from '../auth'
import { useHead } from '../seo/head'
import { comparePage as compareHead } from '../seo/pages'
import { evidencePath } from '../catalog/format'

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
  //
  // NOT SIGNED IN COUNTS THE SAME (2026-10-15): the backend sends a visitor
  // the counts only (judge/app.py: compare_page), so the page leaves out what
  // it no longer has rather than showing an empty "In their words".
  const fromReports = sp.get('from') === 'reports' || !getSession()
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

  // A MODEL IS DROPPED BY EITHER OF ITS IDS. The address may name it by its
  // readable id (`anthropic/claude-sonnet-5`, what every link from the home
  // page and the Models pages uses) or by its registry id (`mv_...`); the
  // chip knows both. Dropping by the registry id alone left a readable-id
  // address untouched, so the x did nothing (2026-10-15).
  const dropModel = (m) => setIds(ids.filter((x) => x !== m.model_version_id && x !== m.canonical_id))
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
      || (r.categories || []).some((c) => c.state !== 'none')
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
        {/* ONE LINE, 2026-10-01; reworded 2026-10-19 for the category score.
            It said "Counted, never scored", which the page no longer is: it
            shows one score per category (CLAUDE.md rule 3, second exception).
            @parvathibntglobal asked on #541 that this line change in the same
            change as the scores, so the page never says "never scored" while
            showing one. What stays true: no overall winner is picked. */}
        <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '76ch' }}>
          What engineers reported about each model, side by side: a score per category with the reports it comes from,
          and each model&apos;s price and specs. Compare models within a category; no overall winner is picked.
        </p>
        <HowToRead method={state.data.category_method} />
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
          So there is no score to show. That is an absence we found rather than a judgement
          we made — a model here may be excellent and simply unwritten-about. What each
          provider advertises is below; it is the provider&apos;s claim, not a finding.
        </p>
      ) : (
      <div className="stack stack-2">
        {/* SCORES IN PLACE OF LISTS (2026-10-19, at the product owner's
            request). The page listed the jobs and capabilities the models
            share, each with its report count. It now shows one score per
            category over eight categories, with the counts beside each score.
            Every job, capability and metric is still on each model's own page
            and on the reports pages. */}
        <CategoryScores models={models} method={state.data.category_method} />
      </div>
      )}

      <PriceAndSpecs models={models} />

      {/* ⚠ THE PROVIDER'S SPECIFICATION IS BACK, 2026-10-19, at the product
             owner's request, in place of the metrics block. It came off on
             2026-09-23 because a spec sheet beside counted reports reads as a
             finding; the risk is the same today, so the table carries its own
             label - the provider's figures, not measured here - sits below
             the scores rather than among them, and highlights nothing. A model
             nobody has written about now shows its specs and no score, which
             is the honest pair: a claim we can show, a finding we cannot. */}

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
              onClick={() => onDrop(m)}
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
 * The three counts as chips, in the board's own polarity colours.
 *
 * ⚠ A ZERO IS DROPPED, NOT DIMMED, and that is the one judgement call here.
 *   `3 positive · 2 neutral` is read correctly as "no negatives"; a `0
 *   negative` chip beside it says the same thing louder and turns a scannable
 *   cell into nine chips across three columns. What must never be dropped is a
 *   non-zero, which is why every count present is rendered whatever its size.
 */
function Polarity({ split, open }) {
  if (!split.total) return <span className="dim" style={{ fontSize: 11 }}>none</span>
  const chips = [
    ['positive', 'pass'],
    ['negative', 'fail'],
    ['neutral', 'mute'],
    ['other', 'mute'],
  ].filter(([k]) => split[k] > 0)

  return (
    <span className="row" style={{ gap: 4, flexWrap: 'wrap' }}>
      {chips.map(([k, tone]) => {
        const badge = (
          <Badge key={k} tone={tone}>
            <span className="tnum">{split[k]}</span>{' '}
            {/* ⚠ THE WORD, NOT JUST THE COLOUR. Three coloured numbers with no
                labels is identity by colour alone, and red/green is the pair
                most readers lose. */}
            {k === 'other' ? 'unlabelled' : k}
          </Badge>
        )
        // EACH CHIP OPENS ITS REPORTS (2026-10-21): the evidence feed, one side.
        // These are ENTRIES; the feed lists the reports holding them and says both.
        return open && k !== 'other' ? (
          <Link key={k} to={open(k)} className="ev-chiplink"
                title={`Open the reports behind these ${split[k]} ${k} entries`}>{badge}</Link>
        ) : badge
      })}
    </span>
  )
}

/* ══════════════════════════════════════════════════════════════════════
   THE SHOWCASE PARTS, added 2026-10-01: the method text collapsed, a
   head-to-head header, and a names bar that stays on screen. None of them
   scores or ranks: every number on them is a count. The one score on this
   page is the category score, further down, under its own conditions.
   ══════════════════════════════════════════════════════════════════════ */

/** The score for `p` positive of `n` sided reports, worked out from the
 *  contract's z (judge/category_scores.py does the same in Python), so the
 *  examples in the method note are computed, never typed (rule 11). */
function wilsonExample(p, n, z) {
  const ph = p / n
  const zz = z * z
  const lo = (ph + zz / (2 * n) - z * Math.sqrt((ph * (1 - ph) + zz / (4 * n)) / n)) / (1 + zz / n)
  return `${p} positive of ${n} scores ${Math.round(100 * lo)}`
}

/** The page's method, kept but folded away: the short line above says it.
 *  The minimum comes from the payload (`category_method`, read from
 *  contract/category_scores.yaml), never typed here. */
function HowToRead({ method }) {
  return (
    <details className="cmp-how">
      <summary>How to read this comparison</summary>
      <ul>
        <li>
          Each category score, out of 100, sums up the reports engineers wrote about a model in that area. It is
          the lower bound of a confidence interval on the share of reports calling the model working: few reports
          score lower than the same share from many.
          {method?.wilson_z != null && <> {wilsonExample(3, 3, method.wilson_z)} and {wilsonExample(20, 20, method.wilson_z)}.</>}
        </li>
        <li>
          {method?.min_sided_reports != null
            ? `Below ${method.min_sided_reports} reports that took a side, there is no score, only the counts.`
            : 'With too few reports that took a side, there is no score, only the counts.'}
          {' '}No reports at all is shown as no reports: nobody wrote about it, which is not a low score.
        </li>
        <li>Compare models within a category. A model&apos;s scores in different categories are not comparable.</li>
        <li>A bigger number is more writing, not a better model: the counts on the cards track how widely a model
          is used as much as how well it works.</li>
        <li>Positive, negative and neutral say how each report was phrased, not whether it was right.</li>
        <li>Price and specs are what each provider advertises, not measured here.</li>
        <li>No overall winner is picked.</li>
      </ul>
    </details>
  )
}

// THE MODEL'S PAGE IN THE NEW DESIGN (2026-10-15): price, workload cost, specs
// and voices (/catalog/model/...). Was /models, the roster behind sign-in.
const modelLink = (m) => `/catalog/model/${modelPath(m.canonical_id || m.model_version_id)}`
// The evidence feed takes either id shape (judge/feed/items.py resolve_model).
const feedId = (m) => m.canonical_id || m.model_version_id

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
                  <Link to={evidencePath(feedId(m))} className="tnum h2h-n ev-open"
                        title={`Read the ${pol.documents ?? split.total} posts behind these counts`}>
                    <b>{split.total}</b> {split.total === 1 ? 'entry' : 'entries'}
                    {pol.documents != null && <> · <b>{pol.documents}</b> {pol.documents === 1 ? 'post' : 'posts'}</>}
                    {platforms > 0 && <> · <b>{platforms}</b> {platforms === 1 ? 'platform' : 'platforms'}</>}
                  </Link>
                  <Polarity split={split} open={(k) => evidencePath(feedId(m), { polarity: k })} />
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
   PRICE AND SPECS (2026-10-19, at the product owner's request). The metrics
   block ("measured in the same test") is replaced by what each provider
   advertises. These are the provider's own figures from the model registry,
   not measurements and not evidence, and the label says so. A value the
   provider does not publish says "not published" - never "No", never $0
   (rule 6). Nothing is highlighted as cheaper or bigger: the reader compares.
   ══════════════════════════════════════════════════════════════════════ */

const yesNo = (v) => (v == null ? 'Not published' : v ? 'Yes' : 'No')
const SPEC_ROWS = [
  ['Input price', 'per 1M tokens', (a) => (a.price_in == null ? 'Not published' : fmtPrice(a.price_in))],
  ['Output price', 'per 1M tokens', (a) => (a.price_out == null ? 'Not published' : fmtPrice(a.price_out))],
  ['Cached input', 'per 1M tokens', (a) => (a.price_cached_read == null ? 'Not published' : fmtPrice(a.price_cached_read))],
  ['Context window', 'tokens', (a) => (a.context == null ? 'Not published' : fmtTokens(a.context))],
  ['Max output', 'tokens', (a) => (a.max_output_tokens == null ? 'Not published' : fmtTokens(a.max_output_tokens))],
  ['Tool calling', null, (a) => yesNo(a.tools)],
  ['Vision', null, (a) => yesNo(a.vision)],
  ['Structured output', null, (a) => yesNo(a.structured_output)],
  ['Prompt caching', null, (a) => yesNo(a.caching)],
  // No "Status" row: `advertised.lifecycle` is read from model_version, where it
  // was NULL on all 270 registry models on 2026-10-19 (the lifecycle lives in
  // the model catalog). A row saying "not published" for every model says nothing.
]

function PriceAndSpecs({ models }) {
  const n = models.length
  return (
    <div className="stack stack-2" style={{ marginTop: 'var(--s4)' }}>
      <span className="label">Price and specs</span>
      <p className="st-basis">
        <span className="st-i" aria-hidden="true">i</span>
        <span>
          What each provider advertises, from the model registry: list prices per million tokens and the published
          limits and features. The provider&apos;s own figures, not measured here.
        </span>
      </p>
      <div className="st-grid" style={{ '--n': n }}>
        <div className="st-tr st-th">
          <span>Spec</span>
          {models.map((m) => <span key={m.model_version_id}>{shortName(m.display_name)}</span>)}
        </div>
        {SPEC_ROWS.map(([label, unit, read]) => (
          <div key={label} className="st-tr">
            <span className="st-axis-cell"><b>{label}</b>{unit && <span className="st-src">{unit}</span>}</span>
            {models.map((m) => {
              const v = read(m.advertised || {})
              return (
                <span key={m.model_version_id} className="st-cell">
                  <span className="st-cell-name">{shortName(m.display_name)}</span>
                  <span className={v === 'Not published' ? 'st-none' : 'st-fig'}>{v}</span>
                </span>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════
   SCORE PER CATEGORY (2026-10-19): CLAUDE.md rule 3's second exception, and
   the only visible score on the board. Replaces the lists of every job,
   capability and metric with their counts.

   The score and its formula are judge/category_scores.py and
   contract/category_scores.yaml. What this component must do, by the rule:
     - show the counts beside every score - a score alone is the breach;
     - show no score below the minimum, and say "too few reports" - distinct
       from "no reports" (rules 4 and 6);
     - say in words what it is: a summary of what engineers reported here,
       not a benchmark; and that it compares MODELS within a category.
   No cell is highlighted as the winner.
   ══════════════════════════════════════════════════════════════════════ */

// EACH COUNT OPENS ITS REPORTS (2026-10-21): the evidence feed filtered to this
// category (judge/category_scores.py `filer`, the same filing as the score) and
// one side, counted as the score counts it - a metric entry is neutral here. A
// zero links nowhere. `both` does not link: no one filter is "both sides", and
// the positive and negative lists each already include those reports.
function CountLink({ id, category, polarity, n }) {
  if (!n) return <>{n} {polarity}</>
  return (
    <Link to={evidencePath(id, { category, polarity })} className="ev-open"
          title={`Open the ${n} ${polarity} ${n === 1 ? 'report' : 'reports'} behind this count`}>
      {n} {polarity}
    </Link>
  )
}

function ScoreCell({ c, id }) {
  if (!c || c.state === 'none') return <span className="cs-none">No reports</span>
  const counts = (
    <span className="cs-counts">
      <CountLink id={id} category={c.key} polarity="positive" n={c.positive} /> ·{' '}
      <CountLink id={id} category={c.key} polarity="negative" n={c.negative} /> ·{' '}
      <CountLink id={id} category={c.key} polarity="neutral" n={c.neutral} />
      {c.both > 0 && <> · {c.both} both</>}
    </span>
  )
  // THE SCORE OPENS THE WHOLE CATEGORY: every report it was computed from.
  const all = `Open the ${c.reports} ${c.reports === 1 ? 'report' : 'reports'} in ${c.name}`
  if (c.state === 'too_few') {
    return (
      <>
        <Link to={evidencePath(id, { category: c.key })} className="cs-few ev-open" title={all}>
          Too few reports to score
        </Link>
        {counts}
      </>
    )
  }
  return (
    <>
      <Link to={evidencePath(id, { category: c.key })} className="cs-score tnum ev-open" title={all}>
        {c.score}<span className="cs-of">/100</span>
      </Link>
      {counts}
    </>
  )
}

function CategoryScores({ models, method }) {
  const n = models.length
  const cats = (models[0]?.reported?.categories || []).map((c) => ({ key: c.key, name: c.name }))
  const of = (m, key) => (m.reported?.categories || []).find((c) => c.key === key)
  return (
    <div className="stack stack-2">
      <span className="label">Score per category</span>
      <p className="st-basis">
        <span className="st-i" aria-hidden="true">i</span>
        <span>
          Each score sums up what engineers reported about a model in that area on this board, out of 100: more reports
          saying it worked, against fewer saying it failed, scores higher, and a share drawn from few reports scores lower
          than the same share from many. It is not a benchmark. Compare models along a row; a model&apos;s scores in
          different categories are not comparable with each other.
          {method?.min_sided_reports != null && <> Below {method.min_sided_reports} reports that took a side there is no score, only the counts.</>}
        </span>
      </p>
      <div className="st-grid" style={{ '--n': n }}>
        <div className="st-tr st-th">
          <span>Category</span>
          {models.map((m) => <span key={m.model_version_id}>{shortName(m.display_name)}</span>)}
        </div>
        {cats.map((cat) => (
          <div key={cat.key} className="st-tr">
            <span className="st-axis-cell"><b>{cat.name}</b></span>
            {models.map((m) => (
              <span key={m.model_version_id} className="st-cell cs-cell">
                <span className="st-cell-name">{shortName(m.display_name)}</span>
                <ScoreCell c={of(m, cat.key)} id={feedId(m)} />
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/** "Anthropic: Claude Opus 5" -> "Claude Opus 5". A name with no prefix is kept. */
function shortName(name) {
  const n = String(name || '')
  return n.includes(': ') ? n.split(': ').slice(1).join(': ') : n
}
