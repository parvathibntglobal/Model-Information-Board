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

        {/* GROUPED BY SECTION AND FOLDED. This was one flat list of every
            discovered slug, which grows with every fetch and buries the reason
            to look. Duplicates can only occur WITHIN a section - "function
            calling" and "tool calling" are both capabilities, never a
            capability and a metric - so grouping by section is not just tidier,
            it puts the comparison a reader is actually making side by side.

            The summary carries the count AND how many still need a ruling, so a
            folded panel says whether there is anything to do inside it. Native
            <details>, same as the FAQ: the rows stay in the DOM for ctrl-F and
            for a screen reader whether or not the panel is open. */}
        {SECTION_ORDER.filter((sec) => groups.some((g) => g.section === sec)).map((sec) => {
          const inSection = groups.filter((g) => g.section === sec)
          const unruled = inSection.filter((g) => !g.ruling).length
          return (
            <details key={sec} className="disc">
              <summary>
                {SECTION_LABEL[sec] || sec}
                <span className="n">
                  {inSection.length} section{inSection.length === 1 ? '' : 's'}
                  {unruled > 0
                    ? ` · ${unruled} awaiting a ruling`
                    : ' · all ruled'}
                </span>
              </summary>
              <div className="disc-body stack stack-3">
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
                  Showing {(g.quotes || []).length} of {g.entries} quotes. A
                  section-wide ruling covers all {g.entries}, including the
                  {' '}{g.entries - (g.quotes || []).length} not listed here.
                </span>
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
          )
        })}
              </div>
            </details>
          )
        })}
      </div>
    </section>
  )
}
