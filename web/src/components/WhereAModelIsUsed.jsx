import { useState } from 'react'
import { Badge } from './ui'

/**
 * Where an AI model is used in this project, and what it is told there.
 *
 * Sits at the top of the Prompts section, above the prompts themselves. The
 * prompt list answers "what exactly do we send"; this answers the question a
 * reader has first - "where is a model used at all, and what is it for" - and
 * says it in plain words rather than in a 22,000-character prompt.
 *
 * ⚠ EVERY FACT HERE COMES FROM THE BACKEND, READ OR CHECKED ON THIS REQUEST.
 *   `judge/app.py:_where_a_model_is_used` builds it:
 *
 *     the stages allowed to call a model   `spend_ledger.STAGES`
 *     how long each prompt is              measured from the built prompt
 *     each plain-language point            carries the phrase it summarises,
 *                                          looked for in the live prompt
 *     the fields left over                 looked for in the schema actually sent
 *
 *   A point whose phrase has left the prompt is shown as DRIFTED rather than
 *   silently kept. A summary of a prompt is a claim about a prompt, and this
 *   admin page has already shipped two captions describing things that had
 *   changed underneath them.
 */
export default function WhereAModelIsUsed({ callers }) {
  if (!callers) return null
  const { stages = [], extract, ask } = callers

  return (
    <div className="stack stack-3">
      <div className="stack stack-1">
        <span className="label">Where a model is used</span>
        <p style={{ fontSize: 'var(--fs-sm)', margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
          In <strong>{stages.length === 2 ? 'exactly two places' : `${stages.length} places`}</strong>,
          and the spend ledger refuses any other caller —{' '}
          <span className="mono" style={{ fontSize: 11 }}>{stages.join(', ')}</span>.
          The model <strong>proposes and the code decides</strong>: it classifies and
          quotes, and plain code does all the counting and ranking.
        </p>
      </div>

      {/* Two cards side by side where there is room, stacked where there is
          not. Same shape for both, so the two can be compared at a glance: what
          it is for, whether it runs, how big its prompt is, what it is told. */}
      <div className="grid g2" style={{ gap: 'var(--s3)', alignItems: 'start' }}>
        <Caller
          n={1}
          title="Extraction"
          status="live"
          when="Runs on every fetch — once for each post or thread the harvest collects."
          does="Reads the post and files what engineers said onto the board: the jobs, capabilities and metrics, each with a verbatim quote."
          part={extract}
          retries="Two short retry prompts sit beside it: if the answer breaks the required format, the exact error goes back once; if a quote is too long, it is told specifically how to shorten it."
        />
        <Caller
          n={2}
          title="The Ask box"
          status="not built yet"
          when="Not reachable from the site yet — the backend route is wired and charges the ledger, but no page calls it."
          does="Turns a plain description of somebody's task into a structured list of requirements. Code does everything after that."
          part={ask}
        />
      </div>

      {/* THE LEFT-OVER FIELDS, ONLY WHILE THEY ARE LEFT OVER. Computed from the
          schema actually sent, so the day the prompt stops asking for them this
          disappears on its own - nobody has to remember to delete a warning. */}
      {extract?.closed_twelve_fields?.length > 0 && (
        <div className="stack stack-1"
             style={{ borderLeft: '2px solid var(--warn)', paddingLeft: 12 }}>
          <span className="label">Still asked for, no longer kept</span>
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0,
                                      maxWidth: '78ch', lineHeight: 1.6 }}>
            The extraction prompt still asks for{' '}
            {extract.closed_twelve_fields.map((f, i) => (
              <span key={f}>
                {i > 0 && (i === extract.closed_twelve_fields.length - 1 ? ' and ' : ', ')}
                <span className="mono" style={{ color: 'var(--text)' }}>{f}</span>
              </span>
            ))}
            . They belong to the old fixed list of twelve capabilities, and nothing
            saves the answers any more — so those tokens are paid for and thrown
            away. Removing them changes the prompt, which is why it is a separate
            decision (#434).
          </p>
        </div>
      )}
    </div>
  )
}

function Caller({ n, title, status, when, does, part, retries }) {
  const [open, setOpen] = useState(false)
  const points = part?.points || []
  const drifted = points.filter((p) => !p.found)

  return (
    <div className="card" style={{ padding: 'var(--s4)' }}>
      <div className="stack stack-2">
        <div className="row" style={{ gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="dim tnum" style={{ fontSize: 11 }}>{n}</span>
          <strong style={{ fontSize: 'var(--fs-sm)' }}>{title}</strong>
          <Badge tone={status === 'live' ? 'pass' : 'mute'}>{status}</Badge>
          {part?.stage && (
            <span className="mono dim" style={{ fontSize: 10 }}>stage: {part.stage}</span>
          )}
        </div>

        <p style={{ fontSize: 'var(--fs-xs)', margin: 0, lineHeight: 1.6 }}>{does}</p>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, lineHeight: 1.6 }}>{when}</p>

        {part?.unreadable && (
          <span className="dim" style={{ fontSize: 11 }}>
            Its prompt could not be built on this request ({part.unreadable}), so what
            it is told is not shown — not a statement that it is told nothing.
          </span>
        )}

        {points.length > 0 && (
          <>
            {/* THE SIZE IS MEASURED, not typed. It was "about 22,000
                characters" in a chat answer; on the page it is the count of the
                prompt that was built a moment ago. */}
            <span className="dim tnum" style={{ fontSize: 11 }}>
              Its prompt is {part.prompt_chars.toLocaleString()} characters. In plain
              terms it says:
            </span>

            <ol className="stack stack-1" style={{ margin: 0, paddingLeft: 18,
                                                  fontSize: 'var(--fs-xs)', lineHeight: 1.55 }}>
              {(open ? points : points.slice(0, 5)).map((p) => (
                <li key={p.title}>
                  <strong style={{ color: p.found ? 'var(--text)' : 'var(--text-3)' }}>
                    {p.title}.
                  </strong>{' '}
                  <span className="dim">{p.plain}</span>
                  {/* ⚠ DRIFTED, SAID ON THE LINE. The phrase this point
                      summarises is no longer in the prompt, so the summary may
                      be describing a rule the model is not told any more. */}
                  {!p.found && (
                    <>{' '}<Badge tone="warn">not in the prompt any more</Badge></>
                  )}
                </li>
              ))}
            </ol>

            {points.length > 5 && (
              <button type="button" className="linkish" style={{ alignSelf: 'flex-start' }}
                onClick={() => setOpen((v) => !v)}>
                {open ? 'show fewer' : `show all ${points.length}`}
              </button>
            )}

            {drifted.length > 0 && (
              <span className="dim" style={{ fontSize: 11 }}>
                {drifted.length} of {points.length} points no longer match the live
                prompt — the summary needs updating.
              </span>
            )}
          </>
        )}

        {retries && (
          <p className="dim" style={{ fontSize: 11, margin: 0, lineHeight: 1.6 }}>{retries}</p>
        )}
      </div>
    </div>
  )
}
