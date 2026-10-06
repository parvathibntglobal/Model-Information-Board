import { useState } from 'react'
import { Badge } from './ui'
import { prettyModel } from '../modelNames'

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
  const { extract, blogs } = callers
  // The ledger's stages plus the blog generator, which calls a model
  // directly and records its cost in its own run history instead.
  // The Ask box is planned and nothing calls it, so it is not a place a
  // model is used today (deprioritised 2026-10-06). Reading + blog drafts.
  const places = (extract ? 1 : 0) + (blogs ? 1 : 0)

  return (
    <div className="stack stack-3">
      <div className="stack stack-1">
        <span className="label">Where an AI model is used</span>
        {/* PLAIN WORDS FIRST. This read "the spend ledger refuses any other
            caller - extract, ask": true, and written for whoever built the
            ledger. The count still comes from `spend_ledger.STAGES`; only the
            sentence around it changed. */}
        <p style={{ fontSize: 'var(--fs-sm)', margin: 0, maxWidth: '72ch', lineHeight: 1.65 }}>
          An AI model is used in{' '}
          <strong>{places === 3 ? 'three places' : places === 2 ? 'two places' : `${places} places`}</strong>{' '}
          — nothing else in the project calls one.
        </p>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, maxWidth: '72ch', lineHeight: 1.65 }}>
          Reading only <strong style={{ color: 'var(--text)' }}>reads and sorts</strong>;
          blog drafts are written, then checked by code. A model never decides
          which model is best: every count, ranking and comparison on the site is worked
          out by our own code.
        </p>
      </div>

      {/* ONE UNDER THE OTHER, EXTRACTION FIRST. They were side by side, which
          gave the Ask box - a step no page reaches yet - the same weight as the
          one that runs on every fetch. Stacked, the order says which matters:
          the live use leads, the planned one follows. Same shape for both, so
          they still read the same way: what it is for, whether it runs, how
          big its prompt is, what it is told. */}
      <div className="stack stack-3">
        <Caller
          n={1}
          title="Reading what engineers wrote"
          status="live"
          does="Reads each post and puts what the writer said onto the board — the jobs they used a model for, how it behaved, and any figures they quoted — each with the writer's exact words."
          when="Every time a model is fetched, once for each post that comes back."
          part={extract}
          retries="If the answer comes back in the wrong shape, the model is shown the exact error and gets one more try. If a quote is too long, it is told how to shorten it."
        />
        <Caller
          n={2}
          title="Writing blog drafts"
          status="live"
          does="Reads whole engineering discussions and writes one essay as a draft; code then checks every quote and figure against the discussions and rejects the draft if any fails."
          when="Only when someone presses Generate in Admin → Blogs, on a local development backend. Its cost is recorded per run in the blog run history, not in the spend ledger."
          part={blogs}
        />
      </div>

      {/* THE LEFT-OVER FIELDS, ONLY WHILE THEY ARE LEFT OVER. Computed from the
          schema actually sent, so the day the prompt stops asking for them this
          disappears on its own - nobody has to remember to delete a warning. */}
      {extract?.closed_twelve_fields?.length > 0 && (
        <div className="stack stack-1"
             style={{ borderLeft: '2px solid var(--warn)', paddingLeft: 12 }}>
          <span className="label">One thing to tidy up</span>
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0,
                                      maxWidth: '72ch', lineHeight: 1.65 }}>
            The reading step still asks the model for{' '}
            {extract.closed_twelve_fields.map((f, i) => (
              <span key={f}>
                {i > 0 && (i === extract.closed_twelve_fields.length - 1 ? ' and ' : ', ')}
                <span className="mono" style={{ color: 'var(--text)' }}>{f}</span>
              </span>
            ))}
            . These belonged to the old list of twelve fixed capabilities, and nothing
            keeps the answers any more — so we pay for them and throw them away.
            Removing them means changing the prompt, which is being decided
            separately in #434.
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
        </div>

        {/* THE MODEL, NAMED - read from the code on this request, not typed. */}
        {part?.model && (
          <span style={{ fontSize: 'var(--fs-xs)' }}>
            <span className="label" style={{ marginRight: 6 }}>Model</span>
            <strong>{prettyModel(part.model)}</strong>{' '}
            <span className="dim mono" style={{ fontSize: 11 }}>{part.model}</span>
          </span>
        )}

        {/* LABELLED, BECAUSE TWO UNLABELLED PARAGRAPHS READ AS ONE. "What it
            does" and "When it runs" are different questions, and a reader
            scanning for one should not have to read the other to find it.

            The internal stage key (`extract`, `ask`) is not on the card: it is
            the name the code uses, not the name a reader uses. */}
        <dl className="stack stack-1" style={{ margin: 0, fontSize: 'var(--fs-xs)', lineHeight: 1.6 }}>
          <div>
            <dt className="label" style={{ display: 'inline', marginRight: 6 }}>What it does</dt>
            <dd style={{ display: 'inline', margin: 0 }}>{does}</dd>
          </div>
          <div>
            <dt className="label" style={{ display: 'inline', marginRight: 6 }}>When it runs</dt>
            <dd className="dim" style={{ display: 'inline', margin: 0 }}>{when}</dd>
          </div>
        </dl>

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
            <span className="label" style={{ marginTop: 4 }}>
              What the model is told{' '}
              <span className="dim tnum" style={{ textTransform: 'none', letterSpacing: 0,
                                                   fontWeight: 400 }}>
                · {part.prompt_chars.toLocaleString()} characters of instructions, in short
              </span>
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
