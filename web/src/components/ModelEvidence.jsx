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
  ['best_for', 'Best for', 'Jobs engineers report running on this model.'],
  ['capabilities', 'Capabilities', 'Behaviours reported, well or badly.'],
  ['metrics', 'Metrics', 'Figures, copied as written. Stated and reported are never merged.'],
]

export default function ModelEvidence({ modelVersionId }) {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })

  useEffect(() => {
    let alive = true
    if (!modelVersionId) return undefined
    setState({ data: null, err: null, unreadable: null })
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
          <strong style={{ color: 'var(--text-1)' }}>discovered, not chosen from a list</strong>{' '}
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

        {/* ALL THREE, ALWAYS. Omitting an empty section made "nothing said
            about jobs yet" indistinguishable from "this board has no jobs
            section" — rule 4 applied to the page's own structure. An empty one
            is listed and says so. Skipped entirely only when the model has
            nothing at all, where the message above covers it. */}
        {data && totals.sections > 0 && SECTIONS.map(([key, title, blurb]) => {
          const items = data[key] || []
          if (!items.length) {
            return (
              <div key={key} className="stack stack-1">
                <span className="label">{title}</span>
                <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, maxWidth: '70ch' }}>
                  Nothing named here yet. {blurb} Other sections below carry evidence, so
                  this one is an absence rather than a gap in what the board looks for.
                </p>
              </div>
            )
          }
          return (
            <div key={key} className="stack stack-2">
              <div className="stack stack-1">
                <span className="label">{title} · {items.length}</span>
                <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{blurb}</span>
              </div>

              {items.map((it) => (
                <div key={it.slug} className="stack stack-1"
                     style={{ borderLeft: '2px solid var(--line)', paddingLeft: 12 }}>
                  <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                    <strong style={{ fontSize: 'var(--fs-sm)' }}>{it.name || it.slug}</strong>
                    <span className="label">
                      {it.reports} report{it.reports === 1 ? '' : 's'}
                    </span>
                  </div>
                  {it.definition && (
                    <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>
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

                  {(it.quotes || []).slice(0, 4).map((q, i) => (
                    <div key={i} className="row" style={{ gap: 8, alignItems: 'flex-start' }}>
                      <Badge tone={q.polarity === 'negative' ? 'fail'
                        : q.polarity === 'positive' ? 'pass' : 'mute'}>{q.polarity}</Badge>
                      <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-2)' }}>
                        “{q.quote}”
                      </span>
                    </div>
                  ))}
                  {(it.quotes || []).length > 4 && (
                    <span className="dim" style={{ fontSize: 11 }}>
                      +{it.quotes.length - 4} more quote(s)
                    </span>
                  )}
                </div>
              ))}
            </div>
          )
        })}

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
