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

        {sections.filter(({ sec }) => sec === active).map(({ sec, inSection, unruled }) => (
            <div key={sec} className="stack stack-3" role="tabpanel">
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
        {inSection.map((g) => {
          const key = `${g.section}:${g.slug}`
          const ruled = Boolean(g.ruling)
            // The ticked ids for this group, as an array the api client can send.
            const chosen = [...(picked[key] || EMPTY)]
          return (
            <div key={key} className="stack stack-1"
                 style={{ opacity: g.ruling === 'declined' ? 0.55 : 1 }}>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <strong style={{ fontSize: 'var(--fs-sm)' }}>{g.name || g.slug}</strong>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{g.slug}</span>
                <span className="label">
                  {g.documents} document{g.documents === 1 ? '' : 's'} · {g.models} model
                  {g.models === 1 ? '' : 's'}
                </span>
                {g.ruling && (
                  <Badge tone={g.ruling === 'declined' ? 'fail' : 'pass'}>
                    {g.ruling}{g.ruling_target ? ` → ${g.ruling_target}` : ''}
                  </Badge>
                )}
              </div>

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
              {/* The quotes ARE the evidence being ruled on, so they are shown
                  rather than linked — a decision made without reading them is
                  the one this panel exists to prevent. */}
              {(g.quotes || []).map((q) => (
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
                    <input
                      className="input"
                      style={{ maxWidth: 200, fontSize: 'var(--fs-xs)' }}
                      placeholder="merge into slug…"
                      value={mergeInto[key] || ''}
                      onChange={(e) => setMergeInto((m) => ({ ...m, [key]: e.target.value }))}
                    />
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
          )
        })}
            </div>
        ))}
      </div>
    </section>
  )
}
