import { useCallback, useEffect, useState } from 'react'
import {
  BoardUnreadable,
  boardEntries,
  ruleBoardEntry,
  unruleBoardEntry,
} from '../api'
import { Badge, Notice, Unreadable } from './ui'
import { IconAlert, IconLayers } from './Icons'

/**
 * Review of the board sections the classifier DISCOVERED.
 *
 * THIS IS NOT A PUBLICATION QUEUE, and the difference from the capability
 * review below it is the thing to keep straight. A capability candidate waits
 * OUTSIDE the vocabulary until somebody admits it. These are already on the
 * board — the classifier found them and the board renders them — so an unruled
 * row here is live, not pending, and the panel says so rather than implying a
 * backlog that is holding something up.
 *
 * What review is actually for is the failure mode an open vocabulary has:
 * DUPLICATES. "function calling" and "tool calling" arriving from two threads
 * are one section under two names. Code normalises spelling and stops there —
 * deciding that two different WORDS mean one thing is a judgement, and a
 * synonym table silently merges two real sections the day it is wrong. So:
 *
 *   merge     fold this slug into another. The rows keep their evidence and
 *             the board counts them under the target.
 *   decline   take it off the board. The rows stay, so the decision is
 *             reversible and the evidence is not destroyed.
 *   adopt     reviewed, keep as is. Changes nothing except that somebody looked.
 *
 * Every ruling is undoable, deliberately: a review surface people cannot back
 * out of is one they hesitate to use, and hesitation is how a board fills with
 * rulings nobody was sure about.
 */

//: Best for first because it is the surface that makes a recommendation, so a
//: wrong slug there costs the most. Same order as the board itself.
const SECTION_ORDER = ['best_for', 'capability', 'metric']

const SECTION_LABEL = {
  best_for: 'Best for',
  capability: 'Capabilities',
  metric: 'Metrics',
}

// One shared empty set, so `picked[key] || EMPTY` does not allocate per render.
const EMPTY = new Set()

//: ── THE STATUS FILTERS ──────────────────────────────────────────────────
//:
//: `ruling` is set only when the WHOLE slug agrees, so a section with one
//: declined quote among nine unruled ones reports no ruling at all. That is
//: why `awaiting` matches on `unruled` rather than on the absence of a
//: ruling: a row with one quote left IS work, and a filter keyed on
//: `!g.ruling` would put it beside rows nobody has touched and call them the
//: same thing.
//:
//: Each filter is a predicate over a group, so the count on a chip and the
//: rows behind it cannot disagree - which they would the moment one was a
//: server number and the other a client filter.
const FILTERS = [
  { key: 'all', label: 'all', match: () => true,
    why: 'every section in this tab, ruled or not' },
  { key: 'awaiting', label: 'awaiting', match: (g) => g.unruled > 0,
    why: 'at least one quote nobody has ruled on — this is the work' },
  { key: 'adopted', label: 'adopted', match: (g) => g.ruling === 'adopted',
    why: 'reviewed and kept as is' },
  { key: 'declined', label: 'declined', match: (g) => g.ruling === 'declined',
    why: 'taken off the board; the rows and their evidence are kept' },
  { key: 'merged', label: 'merged', match: (g) => g.ruling === 'merged',
    why: 'folded into another slug, which the badge names' },
]

export default function BoardReview() {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  const [busy, setBusy] = useState(null)
  const [mergeInto, setMergeInto] = useState({})
  // Which quotes are ticked, per group. An ABSENT or EMPTY set means the
  // reviewer has not chosen any - it does NOT mean "all of them". The buttons
  // below say which of the two they are about to do, so the difference is on
  // screen rather than inferred from state nobody can see.
  const [picked, setPicked] = useState({})
  // WHICH OF THE THREE IS OPEN. `null` until the payload arrives, because the
  // right default is "the first section that actually has anything in it" and
  // that is not knowable before the fetch. Picking one here would open an empty
  // tab on a board that has discovered no `best_for` yet.
  const [openSection, setOpenSection] = useState(null)
  // WHICH ONE ROW IS OPEN, as `section:slug`. One at a time: the list is what
  // a reviewer scans, and two open bodies push the rest off screen again -
  // which is the crowding this replaced.
  const [openSlug, setOpenSlug] = useState(null)
  // STARTS AT `all`, because a panel that opens already filtered hides rows
  // nobody asked to hide. The counts on the chips say where the work is.
  const [statusFilter, setStatusFilter] = useState('all')

  const togglePicked = (key, id) =>
    setPicked((p) => {
      const next = new Set(p[key] || [])
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return { ...p, [key]: next }
    })

  const load = useCallback(() => {
    boardEntries()
      .then((d) => setState({ data: d, err: null, unreadable: null }))
      .catch((e) =>
        setState({
          data: null,
          err: e instanceof BoardUnreadable ? null : e.message,
          unreadable: e instanceof BoardUnreadable ? e.message : null,
        }),
      )
  }, [])
  useEffect(() => { load() }, [load])

  const act = async (fn, key) => {
    setBusy(key)
    try {
      await fn()
      load()
    } catch (e) {
      setState((s) => ({ ...s, err: e.message }))
    } finally {
      setBusy(null)
    }
  }

  const { data, err, unreadable } = state
  // A stale or changed payload must never blank the admin page: one panel's
  // assumption should not take the route down with it.
  const summary = data?.summary ?? { sections: 0, unruled: 0, entries: 0 }
  const groups = Array.isArray(data?.groups) ? data.groups : []

  // The three sections that actually have something in them, in the board's own
  // order, each with the two counts its chip carries. Computed once rather than
  // three times inside the render, and it is also what decides the default tab.
  const sections = SECTION_ORDER
    .filter((sec) => groups.some((g) => g.section === sec))
    .map((sec) => {
      const inSection = groups.filter((g) => g.section === sec)
      return {
        sec,
        inSection,
        unruled: inSection.filter((g) => !g.ruling).length,
      }
    })

  // FALL BACK RATHER THAN RENDER NOTHING. A chosen tab can stop existing - the
  // payload refreshes after a ruling - and a stale selection would leave the
  // chips showing with no panel under them.
  const active = sections.some((x) => x.sec === openSection)
    ? openSection
    : sections[0]?.sec

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Board sections — discovered, and already live</span>
        </div>
        {data && (
          <span className="label">
            {summary.sections} sections · {summary.entries} entries
          </span>
        )}
      </div>

      <div className="card-body stack stack-3">
        {unreadable && <Unreadable detail={unreadable} compact />}
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && !unreadable && <div className="skel" style={{ height: 120 }} />}

        {data && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', lineHeight: 1.6 }}>
            These are on the board now — ruling <strong>consolidates</strong>, it does not
            publish. The reason to look is duplicates: an open vocabulary can name one
            section two ways, and merging is the only place a synonym gets resolved.
            Counts are a floor for the same reason. Every ruling is undoable.
          </p>
        )}

        {data && groups.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-sm)' }}>
            Nothing discovered yet. Sections appear here once a fetch has run and the
            classifier has read some evidence — an empty list is an absence we found,
            not a page that failed to load.
          </p>
        )}

        {/* THREE CHIPS, ONE OPEN. These were three stacked <details> folds, which
            meant the two you were not reading still took up a row each and the
            one you were reading started somewhere down the page.

            Duplicates can only occur WITHIN a section - "function calling" and
            "tool calling" are both capabilities, never a capability and a
            metric - so a reader is only ever comparing inside one of these.
            Showing all three at once was showing two thirds of a page that
            cannot take part in the comparison being made.

            Real <button>s in a real tablist: each is tabbable, arrow keys are
            not hijacked, and `aria-selected` announces which is open. A div
            with an onClick would look the same and be none of that.

            THE COUNT AND THE UNRULED COUNT STAY ON THE CHIP, because that is
            what tells you whether there is anything to do in a tab you are not
            looking at - the whole thing a closed fold used to say. */}
        {sections.length > 0 && (
          /* The board's own chip vocabulary, not a second one. `.chip` /
             `.chip-on` is what every other filter row on this site uses, so
             these look and behave like a control a reader has already met. */
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}
               role="tablist" aria-label="Board sections">
            {sections.map(({ sec, inSection, unruled }) => (
              <button
                key={sec}
                type="button"
                role="tab"
                aria-selected={sec === active}
                className={`chip${sec === active ? ' chip-on' : ''}`}
                onClick={() => setOpenSection(sec)}
              >
                {SECTION_LABEL[sec] || sec}
                <span className="x">
                  {inSection.length}
                  {unruled > 0 ? ` · ${unruled} unruled` : ''}
                </span>
              </button>
            ))}
          </div>
        )}

        {sections.filter(({ sec }) => sec === active).map(({ sec, inSection, unruled }) => {
          // ── THE LIST, OR ONE SECTION'S PAGE. NEVER BOTH ─────────────────
          //
          // Opening a section REPLACES the list rather than expanding inside
          // it. Expanding in place was the first attempt and it keeps the
          // crowding it was meant to remove: the body is five quotes, four
          // controls and a receipt fold, so the rows below it are pushed off
          // screen anyway and the reader has lost the list without being
          // given a page.
          //
          // A page can also say what it is FOR at the top - which model's
          // evidence, how much is left - where a row expanding in a list has
          // no room for a heading.
          const openGroup = inSection.find((x) => `${x.section}:${x.slug}` === openSlug)
          return (
            <div key={sec} className="stack stack-3" role="tabpanel">
              {/* THE WAY BACK IS THE FIRST THING ON THE PAGE, because a view
                  that replaced another with no visible return is a trap. It
                  names the count it is returning to, so the click is a known
                  quantity. */}
              {openGroup && (
                <button type="button" className="linkish" style={{ alignSelf: 'flex-start' }}
                        onClick={() => setOpenSlug(null)}>
                  ← all {inSection.length} section{inSection.length === 1 ? '' : 's'} under{' '}
                  {(SECTION_LABEL[sec] || sec).toLowerCase()}
                </button>
              )}
              {!openGroup && (
              <p className="dim" style={{ fontSize: 11, margin: 0 }}>
                {/* ⚠ RULE 7. The figure travels with its denominator: "4 awaiting
                    a ruling" is a different fact in a section of 5 than in one
                    of 40. */}
                {inSection.length} section{inSection.length === 1 ? '' : 's'} under{' '}
                {(SECTION_LABEL[sec] || sec).toLowerCase()}
                {unruled > 0
                  ? ` · ${unruled} of ${inSection.length} awaiting a ruling`
                  : ' · all ruled'}
              </p>
              )}
        {/* ── the filter row ──────────────────────────────────────────
            A count of zero still renders its chip, disabled. A filter that
            appears and disappears as rulings land is one nobody can learn,
            and `declined 0` is a fact worth reading. */}
        {!openGroup && (
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          {FILTERS.map((f) => {
            const n = inSection.filter((x) => f.match(x)).length
            return (
              <button
                key={f.key}
                type="button"
                aria-pressed={statusFilter === f.key}
                disabled={n === 0 && f.key !== 'all'}
                className={`chip${statusFilter === f.key ? ' chip-on' : ''}`}
                onClick={() => setStatusFilter(f.key)}
                title={f.why}
              >
                {f.label}
                <span className="x">{n}</span>
              </button>
            )
          })}
        </div>
        )}

        {/* RULE 4: A FILTER HIDING EVERYTHING SAYS SO. An empty list under an
            active filter and an empty board look identical otherwise. */}
        {!openGroup
          && inSection.filter((g) => FILTERS.find((f) => f.key === statusFilter).match(g)).length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            Nothing in <strong>{SECTION_LABEL[sec] || sec}</strong> is{' '}
            <strong>{statusFilter}</strong>. That is this filter hiding rows, not an
            empty board — there {inSection.length === 1 ? 'is' : 'are'} {inSection.length}{' '}
            in total.
          </p>
        )}

        {(openGroup
          ? [openGroup]
          : inSection.filter((g) => FILTERS.find((f) => f.key === statusFilter).match(g))
        ).map((g) => {
          const key = `${g.section}:${g.slug}`
          const ruled = Boolean(g.ruling)
            // The ticked ids for this group, as an array the api client can send.
            const chosen = [...(picked[key] || EMPTY)]
          const open = openSlug === key
          return (
            <div key={key} className="axis"
                 style={{ opacity: g.ruling === 'declined' && !open ? 0.55 : 1 }}>
              {/* ── ONE LINE PER SECTION, OPENED ON CLICK ─────────────────
                  This was every group expanded, so a tab with thirty slugs was
                  thirty definitions and thirty fold headers before you reached
                  the one you came for. The panel exists to catch DUPLICATES,
                  and two names being compared have to be on screen together -
                  which they never were.

                  A REAL BUTTON, not a div with an onClick: tabbable, space and
                  enter both work, and `aria-expanded` is what tells a screen
                  reader the body below belongs to this row. */}
              <button
                type="button"
                className="axis-row"
                aria-expanded={open}
                onClick={() => setOpenSlug(open ? null : key)}
              >
                <span className="axis-name">{g.name || g.slug}</span>
                <span className="mono axis-slug">{g.slug}</span>
                <span className="axis-counts">
                  {g.documents} document{g.documents === 1 ? '' : 's'} · {g.models} model
                  {g.models === 1 ? '' : 's'}
                </span>
                {/* ⚠ RULE 7 ON THE LINE ITSELF. "5 quotes" says nothing about
                    how many are LEFT, which is what decides whether to open
                    this row. The queue is what remains, and it shortens. */}
                <span className="axis-left">
                  {g.unruled > 0 ? `${g.unruled} to rule` : 'all ruled'}
                </span>
                {g.ruling && (
                  <Badge tone={g.ruling === 'declined' ? 'fail' : 'pass'}>
                    {g.ruling}{g.ruling_target ? ` → ${g.ruling_target}` : ''}
                  </Badge>
                )}
              </button>

              {open && (
                <div className="axis-body stack stack-1">

              {/* Labelled for the same reason as ModelEvidence.jsx — see the
                  note there. This panel is worse if anything: the definition
                  sits above the very quotes a reviewer is ruling on, so a
                  definition in the achieving voice is an assertion placed
                  beside evidence that may contradict it, at the moment somebody
                  is deciding whether to publish that evidence. */}
              {g.definition && (
                <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch' }}>
                  <span className="label" style={{ marginRight: 6 }}>what counts here</span>
                  {g.definition}
                </p>
              )}

              {/* FOLDED, BECAUSE A SECTION IS LONG AND A LIST OF SECTIONS IS
                  WHAT A REVIEWER IS CHOOSING BETWEEN. Five quotes plus four
                  controls per section means three sections fill a screen, and
                  the duplicate pair this panel exists to catch is then never
                  on screen together.

                  ⚠ THE SUMMARY CARRIES WHAT DECIDES WHETHER TO OPEN IT — how
                    many quotes, and whether it still needs a ruling. A fold
                    whose label says only "quotes" makes a reviewer open every
                    one to find the work, which is the scrolling it replaced.

                  Native <details>, like the section folds above: the quotes
                  stay in the DOM for ctrl-F and for a screen reader whether or
                  not it is open, so nothing is hidden from search — only from
                  the first glance. */}
              <details className="disc">
                <summary>
                  Quotes and ruling
                  <span className="n">
                    {/* ⚠ RULE 7. "5 shown of 125" said nothing about how many
                        were LEFT, which is the number a reviewer works against.
                        The queue is what remains, and it shortens. */}
                    {g.unruled > 0
                      ? `${(g.quotes || []).length} of ${g.unruled} left to rule`
                      : 'all ruled'}
                    {g.ruled > 0 ? ` · ${g.ruled} done` : ''}
                  </span>
                </summary>
                <div className="disc-body stack stack-1">
              {/* ── THE QUOTES, GROUPED BY THE MODEL THEY ARE ABOUT ──────
                  A ruling is a judgement about whether a model is fairly
                  described, and the quotes arrived interleaved - four models
                  in five lines, with only an `mv_6d0dcdfbe2d7fa18` to tell
                  them apart, which is an internal key in the place a model
                  name belongs (#278).

                  Grouped, a reviewer reads one model's evidence together and
                  rules on it together. `select all` per model is the action
                  that was missing: ticking four boxes one at a time to
                  decline one model's quotes is the friction that makes people
                  rule the whole slug instead, which is the blunt instrument
                  #279 measured - six of twenty-one slugs held broken AND
                  sound quotes.

                  The quotes ARE the evidence, so they are shown rather than
                  linked: a decision made without reading them is the one this
                  panel exists to prevent. */}
              {byModel(g.quotes).map(([label, { named, quotes: qs }]) => {
                const ids = qs.map((q) => q.id)
                const allTicked = ids.every((id) => (picked[key] || EMPTY).has(id))
                return (
                  <div key={label} className="qmodel">
                    <div className="qmodel-head">
                      <span className={`qmodel-name${named ? '' : ' mono'}`}>{label}</span>
                      {/* ⚠ RULE 12: THE FALLBACK SAYS IT IS ONE. `label` is
                          `model_label || model_version_id`, so a payload
                          without the field renders `mv_9a8f4a62b182ff64` as
                          though that were the model's name - which reads as a
                          registry problem when it is a payload that predates
                          the field. Measured 2026-09-21: 0 of 719 review
                          quotes fail to resolve server-side, so an id here
                          means the response is older than the column, not
                          that the model is unknown. */}
                      {!named && (
                        <span className="label" title="This response carries no model names. It predates the field, so the raw id is being shown instead.">
                          id only — no name in this response
                        </span>
                      )}
                      <span className="label">
                        {qs.length} quote{qs.length === 1 ? '' : 's'}
                      </span>
                      {/* TICKS THIS MODEL'S QUOTES AND NOTHING ELSE, so the
                          buttons below - which already act on the selection -
                          become per-model rulings with no new endpoint and no
                          second code path to keep in step. */}
                      <button
                        type="button"
                        className="linkish"
                        onClick={() => setPicked((prev) => {
                          const next = new Set(prev[key] || [])
                          for (const id of ids) {
                            if (allTicked) next.delete(id)
                            else next.add(id)
                          }
                          return { ...prev, [key]: next }
                        })}
                      >
                        {allTicked ? 'clear' : `select all ${qs.length}`}
                      </button>
                    </div>
                    {qs.map((q) => (
                <label key={q.id} className="row"
                       style={{ gap: 8, alignItems: 'flex-start', cursor: 'pointer',
                                opacity: q.ruling === 'declined' ? 0.5 : 1 }}>
                  {/* ONE BOX PER QUOTE, because a section is not the unit a
                      reviewer disagrees with. On #279 six of twenty-one slugs
                      held broken AND sound quotes, and the only ruling
                      available took all of them off the board together. */}
                  <input
                    type="checkbox"
                    checked={(picked[key] || EMPTY).has(q.id)}
                    onChange={() => togglePicked(key, q.id)}
                    aria-label={`Select this quote: ${q.quote.slice(0, 60)}`}
                    style={{ marginTop: 3, flex: 'none' }}
                  />
                  <Badge tone={q.polarity === 'negative' ? 'fail' : 'mute'}>{q.polarity}</Badge>
                  <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-2)' }}>
                    “{q.quote}”
                  </span>
                  {/* A quote already ruled says so. Without this a declined
                      quote and a live one look identical in this list. */}
                  {q.ruling && (
                    <Badge tone={q.ruling === 'declined' ? 'fail' : 'pass'}>{q.ruling}</Badge>
                  )}
                </label>
                    ))}
                  </div>
                )
              })}
              {/* THE LIST IS CAPPED AT FIVE AND THE SECTION CAN HOLD MORE, so a
                  reviewer pressing "decline all 15" would be ruling on ten quotes
                  they were never shown. Naming the gap is the difference between a
                  decision and a guess - rule 7, in a review surface: the figure on
                  the button travels with what it was drawn from. */}
              {g.entries > (g.quotes || []).length && (
                <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                  {/* ⚠ THIS USED TO BE A DEAD END AND IS NOW A QUEUE.
                      The five shown were the five NEWEST regardless of ruling,
                      so ruling them showed the same five again and the other
                      120 could only ever be ruled wholesale. They are now the
                      OLDEST UNRULED five: rule them and the next five arrive. */}
                  {(g.quotes || []).length} of {g.unruled} still to rule, oldest
                  first. Ruling these reveals the next {Math.min(5, Math.max(0,
                  g.unruled - (g.quotes || []).length))}. A section-wide ruling
                  below covers all {g.entries} at once, including the
                  {' '}{g.entries - (g.quotes || []).length} not listed here.
                </span>
              )}

              {/* ⚠ WITHOUT THIS, A MISCLICK IS INVISIBLE. A ruled quote leaves
                  the queue and says nothing on its way out, so a wrong decline
                  would simply vanish from the page with no way to find it. The
                  receipt is a SAMPLE, so its count travels with it (rule 7). */}
              {(g.ruled_sample || []).length > 0 && (
                <details className="disc">
                  <summary>
                    Already ruled
                    <span className="n">
                      {g.ruled_sample.length} most recent of {g.ruled}
                    </span>
                  </summary>
                  <div className="disc-body stack stack-1">
                    {g.ruled_sample.map((q) => (
                      <div key={q.id} className="stack stack-1"
                           style={{ opacity: q.ruling === 'declined' ? 0.6 : 1 }}>
                        <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
                          <Badge tone={q.ruling === 'declined' ? 'fail' : 'pass'}>
                            {q.ruling}
                          </Badge>
                          <span className="dim" style={{ fontSize: 11 }}>
                            {q.model_version_id || 'no model recorded'}
                          </span>
                        </div>
                        <blockquote style={{ margin: 0, fontSize: 'var(--fs-xs)',
                                             color: 'var(--text-2)', lineHeight: 1.6 }}>
                          {q.quote}
                        </blockquote>
                      </div>
                    ))}
                    <span className="dim" style={{ fontSize: 11 }}>
                      Use the undo below to put any of these back in the queue.
                    </span>
                  </div>
                </details>
              )}

              <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                {!ruled && (
                  <>
                    {/* THE BUTTON NAMES ITS OWN SCOPE, and that is the whole
                        safety argument. An empty selection is ambiguous - it
                        means both "all of them" and "I have not ticked anything
                        yet" - so the broadest action must never be the DEFAULT
                        reading of it. The label changes with the selection, so
                        the control always states what it is about to do and
                        there is nothing invisible to get wrong. The api client
                        sends `null` rather than `[]` when nothing is ticked,
                        and the backend refuses `[]` outright. */}
                    <button type="button" className="chip" disabled={busy === key}
                      onClick={() => act(
                        () => ruleBoardEntry(g.section, g.slug, 'adopted', null, chosen), key)}>
                      {chosen.length
                        ? `adopt ${chosen.length} quote${chosen.length === 1 ? '' : 's'}`
                        : `adopt all ${g.entries}`}
                    </button>
                    <button type="button" className="chip" disabled={busy === key}
                      onClick={() => act(
                        () => ruleBoardEntry(g.section, g.slug, 'declined', null, chosen), key)}>
                      {chosen.length
                        ? `decline ${chosen.length} quote${chosen.length === 1 ? '' : 's'}`
                        : `decline all ${g.entries}`}
                    </button>
                    {/* ⚠ THE TARGETS ARE OFFERED, NOT REMEMBERED.
                        A merge target that is not already a slug in this
                        section creates an axis rather than folding into one,
                        and the only way to know which was to have the list in
                        your head. `aime` and `aime-2026` were two pages for
                        one benchmark and the fix needed the exact spelling of
                        the other one, typed from memory, with no way to check.

                        SCOPED TO THIS SECTION. A metric may not be merged into
                        a capability, and offering one would propose a move the
                        backend refuses. `g.slug` itself is excluded: folding a
                        slug into itself is not a merge. */}
                    <input
                      className="input"
                      list={`mergeopts-${key}`}
                      style={{ maxWidth: 220, fontSize: 'var(--fs-xs)' }}
                      placeholder="merge into slug…"
                      value={mergeInto[key] || ''}
                      onChange={(e) => setMergeInto((m) => ({ ...m, [key]: e.target.value }))}
                    />
                    <datalist id={`mergeopts-${key}`}>
                      {groups
                        .filter((o) => o.section === g.section && o.slug !== g.slug)
                        .map((o) => (
                          <option key={o.slug} value={o.slug}>
                            {o.name && o.name !== o.slug ? `${o.name} · ${o.entries}` : `${o.entries} entries`}
                          </option>
                        ))}
                    </datalist>
                    {/* AN UNKNOWN TARGET IS SAID BEFORE THE CLICK, not refused
                        after it. Typing a slug that does not exist is a real
                        thing to want - the page cannot know a new axis is
                        wrong - so this states what will happen rather than
                        blocking it. */}
                    {(mergeInto[key] || '').trim()
                      && !groups.some((o) => o.section === g.section
                        && o.slug === (mergeInto[key] || '').trim()) && (
                      <span className="mono" style={{ fontSize: 11, color: 'var(--warn)' }}>
                        no such slug in {g.section} — this creates one
                      </span>
                    )}
                    {/* MERGE FOLLOWS THE SELECTION TOO. Folding a whole slug
                        into another is one judgement about a word; moving a
                        single quote is "this was filed under the wrong
                        section". Both are real, and the label says which. */}
                    <button type="button" className="chip" disabled={busy === key || !(mergeInto[key] || '').trim()}
                      onClick={() => act(
                        () => ruleBoardEntry(g.section, g.slug, 'merged', mergeInto[key], chosen), key)}>
                      {chosen.length ? `move ${chosen.length}` : 'merge'}
                    </button>
                  </>
                )}
                {/* UNDO HAS TO REACH A QUOTE TOO, and this is the case that would
                    otherwise have no way back. `g.ruling` is now set only when the
                    WHOLE slug agrees, so a section with one declined quote reports
                    none - and a per-quote decline whose only undo was per-slug would
                    un-decline everything else in the section to fix one mistake.
                
                    Ticked quotes clear themselves; the section-wide undo stays for a
                    section-wide ruling. Same rule as above: the button says which. */}
                {chosen.length > 0 && (
                  <button type="button" className="chip" disabled={busy === key}
                    onClick={() => act(
                      () => unruleBoardEntry(g.section, g.slug, chosen), key)}>
                    undo on {chosen.length} quote{chosen.length === 1 ? '' : 's'}
                  </button>
                )}
                {ruled && chosen.length === 0 && (
                  <button type="button" className="chip" disabled={busy === key}
                    onClick={() => act(() => unruleBoardEntry(g.section, g.slug), key)}>
                    undo ruling on all {g.entries}
                  </button>
                )}
              </div>
                </div>
              </details>
                </div>
              )}
            </div>
          )
        })}
            </div>
          )
        })}
      </div>
    </section>
  )
}

/** The quotes for one section, grouped by the model each is about.
 *
 * ORDER IS FIRST APPEARANCE, not count and not alphabetical. The list arrives
 * oldest-unruled-first — that ordering is the queue, and it is what makes
 * ruling these five reveal the next five — so re-sorting the models would
 * scramble the only thing about the order that is load-bearing.
 *
 * A quote whose model did not resolve keeps its raw id as the heading. An id
 * nobody can resolve is still better than a blank where a model name belongs,
 * and it names the row to go and look at.
 */
function byModel(quotes) {
  const out = new Map()
  for (const q of quotes || []) {
    const label = q.model_label || q.model_version_id || 'unattributed'
    if (!out.has(label)) out.set(label, { named: Boolean(q.model_label), quotes: [] })
    out.get(label).quotes.push(q)
  }
  return [...out.entries()]
}
