import { useEffect, useState } from 'react'
import { adminPrompts } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconLayers } from './Icons'

/**
 * Every prompt the LIVE PIPELINE sends a language model.
 *
 * THE BACKEND COMPOSES THEM, THIS RENDERS THEM. `/admin/prompts` calls
 * `build_system_prompt` and `wrap_untrusted` exactly as `extract/runner.py`
 * does, so what is on this page is what was sent. A transcription here would
 * drift the first time somebody edits a prompt and not this file — and a page
 * that is confidently wrong about its one subject is worse than no page.
 *
 * FOUR, NOT ONE. The extractor's system prompt is the one people mean, but the
 * model reads three more strings and each can change its answer: the user
 * message carrying the document, and the two retry corrections. A page showing
 * only the system prompt would be describing a quarter of what it reads.
 *
 * WHY THE FULL TEXT AND NOT A SUMMARY. The prompt IS the instrument. A summary
 * of it is exactly the thing a reader cannot check, which is the same reason
 * `ModelEvidence` shows quotes rather than paraphrases.
 *
 * THE ASK BOX IS NAMED AND NOT SHOWN. Its routes are still wired and its
 * prompts still build, but no component calls them — so it is listed under
 * "built, but not sent", because a list that looks exhaustive and is not is
 * worse than no list.
 */
export default function PromptsPanel() {
  const [state, setState] = useState({ data: null, err: null })
  const [open, setOpen] = useState(null)

  useEffect(() => {
    let alive = true
    adminPrompts()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const prompts = data?.prompts || []

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Prompts — what we actually send a model</span>
        </div>
        {data && <span className="label">{data.count} prompt(s)</span>}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Every one of these is read by the model. Composed by the backend from the
          same builders the pipeline calls, so this is the text that was sent and
          <strong style={{ color: 'var(--text-1)' }}> not a copy of it</strong> — nothing
          here is transcribed. The harvested document is never part of a prompt: it goes
          inside the delimited block at call time, which is the first of the five
          defences against a post trying to give instructions.
        </p>
      </div>

      <div className="card-body stack stack-3">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 160 }} />}

        {prompts.map((p) => (
          <div key={p.id} className="stack stack-1"
               style={{ borderLeft: '2px solid var(--line)', paddingLeft: 12 }}>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
              <strong style={{ fontSize: 'var(--fs-sm)' }}>{p.title}</strong>
              {p.role && <Badge tone="mute">{p.role}</Badge>}
              {p.unreadable
                ? <Badge tone="fail">unreadable</Badge>
                : p.text
                  ? <span className="label">{p.text.length.toLocaleString()} chars</span>
                  : null}
            </div>

            {p.used_for && (
              <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', margin: 0 }}>
                {p.used_for}
              </p>
            )}

            <span className="dim mono" style={{ fontSize: 11 }}>
              {p.built_by}{p.called_from ? ` · called from ${p.called_from}` : ''}
            </span>

            {/* WHICH PART OF THIS TEXT VARIES, said plainly.
                The two retries are built per failure, so what is shown is the
                real wording with illustrative values in it — and a reader
                comparing this against a log needs to know which numbers move.

                This replaced a "transcribed, not composed" warning, which
                described a weakness in THIS PAGE (the wording had been copied
                out of runner.py) and read as though the prompt were somehow
                less real. It is not: the model reads every one of these. The
                wording moved into prompt.py and the page composes it. */}
            {p.example_input && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', margin: 0 }}>
                <strong style={{ color: 'var(--text-2)' }}>Shown with example values.</strong>{' '}
                {p.example_input}
              </p>
            )}

            {/* RULE 4 AT THE PANEL LEVEL. A prompt that could not be composed
                renders as a NAMED failure, not as a missing row — "we could not
                build it" and "there is no such prompt" are opposite claims. */}
            {p.unreadable && (
              <Notice icon={<IconAlert />}>
                This prompt could not be composed: {p.unreadable}
              </Notice>
            )}

            {p.closed_vocabulary && (
              <details className="disc">
                <summary>
                  The closed vocabulary appended to it
                  <span className="n">{p.closed_vocabulary.length} keys</span>
                </summary>
                <div className="disc-body stack stack-1">
                  <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>
                    One closed list, three open sections — the prompt&rsquo;s own
                    asymmetry. These keys feed the legacy cell score; the board&rsquo;s
                    sections are discovered and bounded by nothing.
                  </p>
                  <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                    {p.closed_vocabulary.map((k) => (
                      <span key={k} className="mono dim" style={{ fontSize: 11 }}>{k}</span>
                    ))}
                  </div>
                </div>
              </details>
            )}

            {p.text && (
              <>
                <button
                  type="button"
                  className="chip"
                  onClick={() => setOpen(open === p.id ? null : p.id)}
                >
                  {open === p.id ? 'Hide the prompt' : 'Read the prompt'}
                </button>
                {open === p.id && (
                  // `pre` with wrapping, not a scrolling box: the whitespace in
                  // these prompts is load-bearing — the delimiters, the indented
                  // examples — so it is preserved, and it wraps rather than
                  // scrolling sideways on a phone.
                  <pre className="mono" style={{
                    fontSize: 11, lineHeight: 1.55, whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word', background: 'var(--surface)',
                    border: '1px solid var(--border)', borderRadius: 'var(--r2)',
                    padding: 'var(--s3)', margin: 0, maxWidth: '100%',
                  }}>{p.text}</pre>
                )}
              </>
            )}
          </div>
        ))}

        {/* WHAT IS NOT HERE, NAMED. A list that looks exhaustive and is not is
            worse than no list — so the measurement scripts are named rather
            than quietly omitted. */}
        {data?.not_shown?.length > 0 && (
          <div className="stack stack-2">
            <span className="label">Built, but not sent by anything on this board</span>
            {data.not_shown.map((x) => (
              <div key={x.what} className="stack stack-1"
                   style={{ borderLeft: '2px solid var(--line)', paddingLeft: 12 }}>
                <strong style={{ fontSize: 'var(--fs-xs)' }}>{x.what}</strong>
                <span className="dim mono" style={{ fontSize: 11 }}>{x.where}</span>
                <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', margin: 0 }}>
                  {x.why}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
