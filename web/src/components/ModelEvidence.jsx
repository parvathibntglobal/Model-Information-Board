import { useEffect, useState } from 'react'
import { BoardUnreadable, modelEvidence } from '../api'
import { Badge, Notice, Unreadable } from './ui'
import { IconAlert, IconLayers } from './Icons'

/**
 * The evidence behind one model, grouped by the sections the classifier found.
 *
 * THIS IS THE MODEL PAGE'S HALF OF THE BOARD'S CORPUS. The board asks "who has
 * been reported doing this"; this asks "what has been said about this one". Same
 * rows, different question — and it reads its own endpoint rather than filtering
 * the board payload, so how the board sorts cannot move what a model shows.
 *
 * THE QUOTES ARE THE PAGE. Every one was verified by exact substring against the
 * text the extractor was given, so what a reader sees is what an engineer wrote,
 * resolved back to the raw span. No summary stands in for them, because a
 * summary is the one thing here nobody can check.
 *
 * THREE EMPTY SECTIONS IS A REAL ANSWER. A tracked model nobody has discussed
 * renders as an absence we found — not as a spinner, and not as a zero score.
 * Silence is not criticism.
 */

const SECTIONS = [
  ['best_for', 'Jobs', 'Jobs engineers report running on this model.'],
  ['capabilities', 'Capabilities', 'Behaviours reported, well or badly.'],
  ['metrics', 'Metrics', 'Figures, copied as written. Stated and reported are never merged.'],
]

/**
 * A harvested URL is untrusted, and JSX does not vet an href.
 *
 * React escapes text nodes, so a quote cannot inject markup here the way it
 * could through the board's `dangerouslySetInnerHTML`. An href is different:
 * `javascript:alert(1)` in a JSX href executes, and no amount of escaping
 * changes that. So the SCHEME is checked and only http(s) is allowed.
 *
 * Returns null when there is nothing usable, and the caller then renders plain
 * text — no link is better than a dead or dangerous one.
 */
function safeHref(u) {
  if (!u) return null
  try {
    const parsed = new URL(String(u))
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : null
  } catch { return null }
}

//: How many quotes an entry shows before the rest go behind a disclosure. Four
//: fits an entry beside its neighbours; the remainder opens, it is not dropped.
const QUOTES_SHOWN = 4

/**
 * One verified quote, with its polarity and a link back to the source.
 *
 * EXTRACTED SO THE FIRST FOUR AND THE REST CANNOT DIVERGE. They were two copies
 * of the same markup — or rather they were one copy and a count, and the count
 * led nowhere. A reader opening the overflow must see quotes rendered exactly
 * as the ones above them, including the link that makes a quote checkable.
 */
function Quote({ q }) {
  const href = safeHref(q.url)
  return (
    <div className="row" style={{ gap: 8, alignItems: 'flex-start' }}>
      <Badge tone={q.polarity === 'negative' ? 'fail'
        : q.polarity === 'positive' ? 'pass' : 'mute'}>{q.polarity}</Badge>
      <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-2)' }}>
        “{q.quote}”
        {/* THE SOURCE, LINKED. The payload used to carry only a document id, so
            the quote could not be checked against what the person actually
            wrote — which is the one thing this panel is for. */}
        {href ? (
          <>
            {' '}
            <a href={href} target="_blank" rel="noopener noreferrer"
               className="mb-link" style={{ whiteSpace: 'nowrap' }}>
              open the source ↗
            </a>
          </>
        ) : (
          <span className="dim" style={{ fontSize: 10 }}> · no link recorded</span>
        )}
      </span>
    </div>
  )
}

export default function ModelEvidence({ modelVersionId }) {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })

  // ⚠ NULL MEANS "THE READER HAS NOT CHOSEN", NOT "JOBS". The opening tab is
  //   picked from the data once it lands — see `active` below — and a click
  //   pins it. Storing a default here instead would open Jobs on every model,
  //   including the ones whose Jobs section is empty and whose twelve
  //   capabilities are one tab away and invisible.
  const [picked, setPicked] = useState(null)

  useEffect(() => {
    let alive = true
    if (!modelVersionId) return undefined
    setState({ data: null, err: null, unreadable: null })
    setPicked(null)   // a different model is a different set of empty sections
    modelEvidence(modelVersionId)
      .then((d) => alive && setState({ data: d, err: null, unreadable: null }))
      .catch((e) => alive && setState({
        data: null,
        err: e instanceof BoardUnreadable ? null : e.message,
        unreadable: e instanceof BoardUnreadable ? e.message : null,
      }))
    return () => { alive = false }
  }, [modelVersionId])

  const { data, err, unreadable } = state
  const totals = data?.totals ?? { sections: 0, quotes: 0 }

  // One row per tab, counts included, computed once so the bar and the body
  // cannot disagree about how many entries a section holds.
  const tabs = SECTIONS.map(([key, title, blurb]) => ({
    key, title, blurb, items: data?.[key] || [],
  }))

  // ⚠ OPEN ON A TAB THAT HAS SOMETHING, and fall back to the first. A fixed
  //   default is the version where a reader lands on "Nothing named here yet"
  //   for a model with 29 entries under the next tab, and concludes the board
  //   has nothing. Every count is on the bar either way, so choosing a
  //   non-empty tab hides no absence — it only stops the page opening on one.
  const active = picked || (tabs.find((t) => t.items.length)?.key ?? tabs[0].key)
  const shown = tabs.find((t) => t.key === active) || tabs[0]

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Evidence — what engineers said, verbatim</span>
        </div>
        {data && (
          <span className="label">{totals.sections} section(s) · {totals.quotes} quote(s)</span>
        )}
      </div>

      {/* THE DISTINCTION THIS PANEL EXISTS FOR, said once at the top. Below it
          on this page sit capability cards keyed to a closed list of twelve;
          these sections are keyed to nothing at all — the classifier reads the
          evidence and names the job, the behaviour or the figure it discusses.
          A reader cannot tell those two apart from a heading reading
          "Evidence". */}
      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0 }}>
          Three ways into the same evidence, and the sections are{' '}
          <strong style={{ color: 'var(--text)' }}>discovered, not chosen from a list</strong>{' '}
          — whatever engineers actually discussed gets named here, whether or not it
          matches anything the board already tracks. Counts are a floor: one section can
          arrive under two names until somebody merges them.
        </p>
      </div>

      <div className="card-body stack stack-3">
        {unreadable && <Unreadable detail={unreadable} compact />}
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && !unreadable && <div className="skel" style={{ height: 140 }} />}

        {data && totals.sections === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-sm)', maxWidth: '70ch', lineHeight: 1.6 }}>
            <strong style={{ color: 'var(--text)' }}>Nobody has discussed this model yet.</strong>{' '}
            That is an absence we found, not a verdict we reached — not “good”, not
            “bad”, just nothing said. <strong style={{ color: 'var(--text)' }}>Fetch</strong>{' '}
            above searches eight platforms for it and fills this panel with whatever
            comes back; an empty result after a run is itself a finding.
          </p>
        )}

        {/* ⚠ ALL THREE TABS, ALWAYS, AND THE COUNT IS ON THE TAB. Stacked,
            this panel showed every section including the empty ones, because
            omitting one made "nothing said about jobs yet" indistinguishable
            from "this board has no jobs section" — rule 4 applied to the
            page's own structure.

            TABS PUT THAT PROPERTY AT RISK, and the count is what saves it: a
            section behind an unselected tab is hidden, so an absence would
            cost a click to discover and would look identical to a section
            that does not exist. `Metrics 0` on the bar is the whole fix. It
            is why the count is never suppressed when zero, and why an empty
            tab still renders a sentence rather than nothing. */}
        {data && totals.sections > 0 && (
          <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                className={`chip${t.key === active ? ' chip-on' : ''}`}
                onClick={() => setPicked(t.key)}
                aria-pressed={t.key === active}
              >
                {t.title} <span className="x">{t.items.length}</span>
              </button>
            ))}
          </div>
        )}

        {data && totals.sections > 0 && (
          <div key={shown.key} className="stack stack-2">
            <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>
              {shown.blurb}
            </span>

            {!shown.items.length && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, maxWidth: '70ch',
                                          lineHeight: 1.6 }}>
                <strong style={{ color: 'var(--text)' }}>Nothing named here yet.</strong>{' '}
                The other tabs carry evidence, so this is an absence rather than a gap
                in what the board looks for — nobody wrote about this model in these
                terms, which is not the same as the board having nowhere to put it.
              </p>
            )}

            {shown.items.map((it) => (
                <div key={it.slug} className="stack stack-1"
                     style={{ borderLeft: '2px solid var(--border)', paddingLeft: 12 }}>
                  <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                    <strong style={{ fontSize: 'var(--fs-sm)' }}>{it.name || it.slug}</strong>
                    <span className="label">
                      {it.reports} report{it.reports === 1 ? '' : 's'}
                    </span>
                  </div>
                  {/* ⚠ LABELLED, BECAUSE UNLABELLED IT READ AS A VERDICT.
                      `board_entry.definition` is "the test a report has to
                      meet" (contract/tables.sql:876) — the SECTION's scope, not
                      a finding about this model. Rendered bare it sat directly
                      above the quotes and was read as the board's own
                      assessment:

                        Japanese TTS                      1 report
                        Correctly reads Japanese text aloud, including
                        correct kanji readings.
                        NEGATIVE  "They are all really bad (more than 1/3 the
                                   expressions had an error in them somewhere)."

                      The board appeared to assert the model reads kanji
                      correctly, then quote someone saying it does not.

                      27 of the 125 distinct definitions on the board are in
                      that achieving voice, so this is not one bad row. The
                      prompt now asks for a scope rather than a verdict
                      (judge/extract/prompt.py) — but that only fixes rows
                      written from here on, and `board_entry` rows are not
                      rewritten. This label is what fixes the 27 already
                      stored, and it costs nothing for the 98 that were already
                      neutral. */}
                  {it.definition && (
                    <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>
                      <span className="label" style={{ marginRight: 6 }}>what counts here</span>
                      {it.definition}
                    </p>
                  )}

                  {/* Figures carry their basis and sit side by side. An advertised
                      2M and a measured ~200k are two facts from two sources, and
                      averaging them would describe a number nobody produced. */}
                  {(it.figures || []).length > 0 && (
                    <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
                      {it.figures.map((f, i) => (
                        <span key={i} className="row" style={{ gap: 5, alignItems: 'baseline' }}>
                          <strong className="tnum" style={{ fontSize: 'var(--fs-sm)' }}>{f.value}</strong>
                          <Badge tone={f.basis === 'reported' ? 'pass' : 'mute'}>{f.basis}</Badge>
                          {f.unit && <span className="dim" style={{ fontSize: 11 }}>{f.unit}</span>}
                        </span>
                      ))}
                    </div>
                  )}

                  {(it.quotes || []).slice(0, QUOTES_SHOWN).map((q, i) => (
                    <Quote key={i} q={q} />
                  ))}

                  {/* ⚠ "+3 MORE" WITH NOTHING BEHIND IT IS A DEAD END, and the
                      same shape was rejected on the compare page for the same
                      reason: it names what it is withholding and offers no way
                      to reach it. The quotes ARE this panel — every one
                      verified by exact substring — so the overflow opens
                      rather than announcing itself.

                      Still collapsed by default: an entry with 30 reports
                      would otherwise bury the next entry, and the tab it sits
                      in already made room by dropping the other two sections
                      off the screen. */}
                  {(it.quotes || []).length > QUOTES_SHOWN && (
                    <details>
                      <summary className="dim" style={{ fontSize: 11, cursor: 'pointer' }}>
                        {it.quotes.length - QUOTES_SHOWN} more quote
                        {it.quotes.length - QUOTES_SHOWN === 1 ? '' : 's'}
                      </summary>
                      <div className="stack stack-1" style={{ marginTop: 8 }}>
                        {it.quotes.slice(QUOTES_SHOWN).map((q, i) => (
                          <Quote key={i} q={q} />
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              ))}
          </div>
        )}

        {data && totals.sections > 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch', lineHeight: 1.6 }}>
            Every quote is verified by exact substring against the source text. Report
            counts say how many people spoke, never who was right.
          </p>
        )}
      </div>
    </section>
  )
}
