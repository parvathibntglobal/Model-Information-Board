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

const SECTION_LABEL = {
  best_for: 'Best for',
  capability: 'Capabilities',
  metric: 'Metrics',
}

export default function BoardReview() {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  const [busy, setBusy] = useState(null)
  const [mergeInto, setMergeInto] = useState({})

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

        {groups.map((g) => {
          const key = `${g.section}:${g.slug}`
          const ruled = Boolean(g.ruling)
          return (
            <div key={key} className="stack stack-1"
                 style={{ opacity: g.ruling === 'declined' ? 0.55 : 1 }}>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <Badge tone="mute">{SECTION_LABEL[g.section] || g.section}</Badge>
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

              {g.definition && (
                <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch' }}>
                  {g.definition}
                </p>
              )}

              {/* The quotes ARE the evidence being ruled on, so they are shown
                  rather than linked — a decision made without reading them is
                  the one this panel exists to prevent. */}
              {(g.quotes || []).slice(0, 3).map((q, i) => (
                <div key={i} className="row" style={{ gap: 8, alignItems: 'flex-start' }}>
                  <Badge tone={q.polarity === 'negative' ? 'fail' : 'mute'}>{q.polarity}</Badge>
                  <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-2)' }}>
                    “{q.quote}”
                  </span>
                </div>
              ))}

              <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                {!ruled && (
                  <>
                    <button type="button" className="chip" disabled={busy === key}
                      onClick={() => act(() => ruleBoardEntry(g.section, g.slug, 'adopted'), key)}>
                      adopt
                    </button>
                    <button type="button" className="chip" disabled={busy === key}
                      onClick={() => act(() => ruleBoardEntry(g.section, g.slug, 'declined'), key)}>
                      decline
                    </button>
                    <input
                      className="input"
                      style={{ maxWidth: 200, fontSize: 'var(--fs-xs)' }}
                      placeholder="merge into slug…"
                      value={mergeInto[key] || ''}
                      onChange={(e) => setMergeInto((m) => ({ ...m, [key]: e.target.value }))}
                    />
                    <button type="button" className="chip" disabled={busy === key || !(mergeInto[key] || '').trim()}
                      onClick={() => act(
                        () => ruleBoardEntry(g.section, g.slug, 'merged', mergeInto[key]), key)}>
                      merge
                    </button>
                  </>
                )}
                {ruled && (
                  <button type="button" className="chip" disabled={busy === key}
                    onClick={() => act(() => unruleBoardEntry(g.section, g.slug), key)}>
                    undo ruling
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
