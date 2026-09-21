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
  // ONE OPEN AT A TIME, across all three groups: the list is what a
  // reader scans, and two open prompts is the wall this replaced.
  const [openId, setOpenId] = useState(null)

  useEffect(() => {
    let alive = true
    adminPrompts()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const prompts = data?.prompts || []
  const fields = data?.schema_fields || []

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
          <strong style={{ color: 'var(--text)' }}> not a copy of it</strong> — nothing
          here is transcribed. The harvested document is never part of a prompt: it goes
          inside the delimited block at call time, which is the first of the five
          defences against a post trying to give instructions.
        </p>
      </div>

      <div className="card-body stack stack-3">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 160 }} />}

        {/* ── SENT TO THE MODEL ──────────────────────────────────────────
            ONE LINE EACH, OPENED ON CLICK. Every prompt used to render in
            full, one after another: four texts totalling thousands of
            characters, each with its metadata, its vocabulary fold and its
            read button, so the page was a wall before you had chosen what to
            read. A reader arrives here wanting ONE of these.

            The row carries what decides which one: what it is, when it is
            sent, and how big. */}
        {data && <span className="label">Sent to the model</span>}

        {prompts.map((p) => {
          const open = openId === p.id
          return (
            <div key={p.id} className="axis">
              <button type="button" className="axis-row" aria-expanded={open}
                      onClick={() => setOpenId(open ? null : p.id)}>
                <span className="axis-name">{p.title}</span>
                {p.role && <Badge tone="mute">{p.role}</Badge>}
                <span className="axis-counts">
                  {p.unreadable
                    ? 'could not be composed'
                    : p.text
                      ? `${p.text.length.toLocaleString()} chars`
                      : 'no text'}
                </span>
              </button>

              {open && (
                <div className="axis-body stack stack-2">
                  {p.used_for && (
                    <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', margin: 0 }}>
                      {p.used_for}
                    </p>
                  )}

                  <span className="dim mono" style={{ fontSize: 11 }}>
                    {p.built_by}{p.called_from ? ` · called from ${p.called_from}` : ''}
                  </span>

                  {/* WHICH PART OF THIS TEXT VARIES, said plainly. The two
                      retries are built per failure, so what is shown is the
                      real wording with illustrative values in it — and a
                      reader comparing this against a log needs to know which
                      numbers move. */}
                  {p.example_input && (
                    <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', margin: 0 }}>
                      <strong style={{ color: 'var(--text)' }}>Shown with example values.</strong>{' '}
                      {p.example_input}
                    </p>
                  )}

                  {/* RULE 4 AT THE PANEL LEVEL. A prompt that could not be
                      composed renders as a NAMED failure, not as a missing
                      row — "we could not build it" and "there is no such
                      prompt" are opposite claims. */}
                  {p.unreadable && (
                    <Notice icon={<IconAlert />}>
                      This prompt could not be composed: {p.unreadable}
                    </Notice>
                  )}

                  {p.closed_vocabulary && (
                    <details className="fold">
                      <summary>
                        <span className="mono" style={{ fontSize: 11 }}>closed vocabulary</span>
                        <span className="dim" style={{ fontSize: 11 }}>
                          {p.closed_vocabulary.length} keys
                        </span>
                      </summary>
                      <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>
                        One closed list, three open sections — the prompt&rsquo;s own
                        asymmetry. These keys feed the legacy cell score; the
                        board&rsquo;s sections are discovered and bounded by nothing.
                      </p>
                      <div className="row" style={{ gap: 6, flexWrap: 'wrap', padding: '0 12px 12px 30px' }}>
                        {p.closed_vocabulary.map((k) => (
                          <span key={k} className="mono dim" style={{ fontSize: 11 }}>{k}</span>
                        ))}
                      </div>
                    </details>
                  )}

                  {p.text && (
                    // `pre` with wrapping, not a scrolling box: the whitespace
                    // in these prompts is load-bearing — the delimiters, the
                    // indented examples — so it is preserved, and it wraps
                    // rather than scrolling sideways on a phone.
                    <pre className="mono prompt-text">{p.text}</pre>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {/* ── THE TOOL-CALL SCHEMA, WHICH IS ALSO THE PROMPT ─────────────
            THE MISSING HALF OF THIS PAGE. The four texts above are the
            system message, the user message and two retry corrections; these
            seventeen field descriptions go in the same call and are what the
            model is asked to FILL IN. A page listing four strings and
            omitting these was describing a fraction of what the model reads.

            One row, opening to a list of folds, rather than seventeen rows:
            they are one object and a reader wants the field they came for. */}
        {fields.length > 0 && (
          <div className="axis">
            <button type="button" className="axis-row" aria-expanded={openId === '_schema'}
                    onClick={() => setOpenId(openId === '_schema' ? null : '_schema')}>
              <span className="axis-name">The tool-call schema</span>
              <Badge tone="mute">tool</Badge>
              <span className="axis-counts">{fields.length} fields</span>
            </button>
            {openId === '_schema' && (
              <div className="axis-body stack stack-2">
                <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0 }}>
                  These descriptions <em>are</em> instructions — they are sent as the
                  tool-call schema, so this is the wording itself and not a summary.
                  Read from <span className="mono">judge/extract/schema.py</span> when
                  this page loaded.
                </p>
                {fields.map((f) => (
                  <details key={`${f.object}:${f.field}`} className="fold">
                    <summary>
                      <span className="mono" style={{ fontSize: 11 }}>{f.field}</span>
                      <Badge tone={f.required ? 'warn' : 'mute'}>
                        {f.required ? 'required' : 'optional'}
                      </Badge>
                      <span className="dim" style={{ fontSize: 11 }}>{f.object}</span>
                    </summary>
                    <p style={{
                      fontSize: 'var(--fs-xs)', lineHeight: 1.65, maxWidth: '82ch',
                      margin: 0, color: 'var(--text-2)', whiteSpace: 'pre-wrap',
                    }}>
                      {f.asks}
                    </p>
                  </details>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── NOT SENT TO A MODEL ────────────────────────────────────────
            ⚠ THE HEADING IS THE POINT. These are the constraints the
            pipeline is built under, not instructions the extractor reads.
            Putting them on a page headed "prompts" without saying so would
            imply the model has been told them, which it has not. */}
        {data && (
          <div className="axis">
            <button type="button" className="axis-row" aria-expanded={openId === '_rules'}
                    onClick={() => setOpenId(openId === '_rules' ? null : '_rules')}>
              <span className="axis-name">The rules this is built under</span>
              <Badge tone="info">not sent</Badge>
              <span className="axis-counts">
                {data.rules_source_readable ? `${(data.rules || []).length} rules` : 'unreadable here'}
              </span>
            </button>
            {openId === '_rules' && (
              <div className="axis-body stack stack-2">
                {data.rules_source_readable ? (
                  <>
                    <ol style={{
                      margin: 0, paddingLeft: '1.5em', fontSize: 'var(--fs-xs)',
                      lineHeight: 1.7, color: 'var(--text-2)', maxWidth: '82ch',
                    }}>
                      {(data.rules || []).map((r) => (
                        <li key={r.n} value={r.n} style={{ marginBottom: 6 }}>{r.rule}</li>
                      ))}
                    </ol>
                    <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                      Headlines only. The argument under each one is what makes it
                      followable and it is long; a second copy of it here is the exact
                      failure the rules are about. Read from{' '}
                      <span className="mono">CLAUDE.md</span> at{' '}
                      <span className="mono">{data.read_from_source_at}</span>.
                    </p>
                  </>
                ) : (
                  /* RULE 4. A container ships the code without the repository,
                     so the file genuinely is not there — a different thing
                     from there being no rules, and a blank list says the
                     second. */
                  <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', lineHeight: 1.6 }}>
                    <span className="mono">CLAUDE.md</span> is not readable from this
                    process, so the rules cannot be listed. That is this deployment
                    shipping code without the repository around it — not an absence of
                    rules.
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* WHAT IS NOT HERE, NAMED. A list that looks exhaustive and is not is
            worse than no list — so the measurement scripts are named rather
            than quietly omitted. */}
        {data?.not_shown?.length > 0 && (
          <div className="stack stack-2" style={{ marginTop: 8 }}>
            <span className="label">Built, but not sent by anything on this board</span>
            {data.not_shown.map((x) => (
              <div key={x.what} className="stack stack-1"
                   style={{ borderLeft: '2px solid var(--border)', paddingLeft: 12 }}>
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
