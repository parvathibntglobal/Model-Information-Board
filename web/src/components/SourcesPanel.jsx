import { Fragment, useEffect, useState } from 'react'
import { adminSources } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconCaret, IconLayers } from './Icons'

/**
 * Every platform the harvest reaches, and how it reaches it.
 *
 * THE LIST COMES FROM THE CONTRACT. `/admin/sources` reads
 * `contract/sources.yaml` — the same file the harvest reads — so a platform
 * added there appears here without an edit to this component.
 *
 * ⚠ NO CREDENTIAL IS SHOWN. Not the key, not a fingerprint, not a prefix. The
 *   page says "uses a key" or "no key" and nothing else, because a page that
 *   shows even part of a credential has published it.
 *
 * WHY "PAID" IS RENDERED AS "METERED". What is measurable is that an arm draws
 * down a RapidAPI quota, which `collect/usage.py` records. The price per
 * request is not in our config, so a dollar figure here would be invented.
 */

// A method is a claim about money or about somebody's terms, so each gets a
// tone rather than all rendering alike: paid access and a robots-gated fetch
// are the two a reader should look at twice.
const METHOD_TONE = (m) => {
  if (!m) return 'fail'
  if (m.startsWith('paid')) return 'warn'
  if (m.startsWith('free')) return 'pass'
  return 'mute'
}

export default function SourcesPanel() {
  const [state, setState] = useState({ data: null, err: null })
  // Which platform's prose is open. One at a time: these are read to answer a
  // question about ONE row, and several open at once rebuilds the wall of
  // paragraphs the table replaced.
  const [open, setOpen] = useState(null)

  useEffect(() => {
    let alive = true
    adminSources()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const sources = data?.sources || []

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Sources — where the evidence comes from</span>
        </div>
        {data && <span className="label">{data.count} platform(s)</span>}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Read from <span className="mono">contract/sources.yaml</span>, the same file
          the harvest reads — so this is what actually runs, not a description of it.
          Each row says how the platform is reached and whether a key is used.{' '}
          <strong style={{ color: 'var(--text-1)' }}>No key is shown anywhere</strong>,
          and none is in the payload behind this page.
        </p>
      </div>

      <div className="card-body stack stack-3">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 180 }} />}

        {data?.by_method && (
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            {Object.entries(data.by_method).map(([method, ids]) => (
              <span key={method} className="row" style={{ gap: 6, alignItems: 'baseline' }}>
                <Badge tone={METHOD_TONE(method)}>{method}</Badge>
                <span className="dim" style={{ fontSize: 11 }}>{ids.length}</span>
              </span>
            ))}
          </div>
        )}

        {/* A TABLE, BECAUSE THE QUESTION IS A COMPARISON. Every row answers the
            same four questions - how is it reached, does it use a key, is it
            metered, have its terms been read - and the answers were buried in
            four paragraphs each, one platform after another. Twelve platforms
            made a page you had to read rather than scan, to compare things that
            differ in one column.

            The prose is not deleted; it moves behind the caret. The detail, the
            credential note and the ruling are what you read about ONE platform
            after the table has told you which one to look at. */}
        {sources.length > 0 && (
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>How it is reached</th>
                  <th>Key</th>
                  <th>Quota</th>
                  <th>Terms</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <Fragment key={s.id}>
                    <tr>
                      <td>
                        <button type="button" className="rowtoggle"
                                aria-expanded={open === s.id}
                                onClick={() => setOpen(open === s.id ? null : s.id)}>
                          <IconCaret width={13} height={13}
                                     className={`caret${open === s.id ? ' on' : ''}`} />
                          <strong>{s.id}</strong>
                        </button>
                      </td>
                      <td>
                        {s.method
                          ? <Badge tone={METHOD_TONE(s.method)}>{s.method}</Badge>
                          : <Badge tone="fail">not described</Badge>}
                      </td>
                      {/* THE WHOLE OF WHAT IS SAID ABOUT CREDENTIALS. Not the
                          key, not a fingerprint, not a prefix. */}
                      <td className="dim">{s.uses_credential ? 'uses a key' : 'no key'}</td>
                      <td>
                        {s.metered
                          ? <Badge tone="warn">metered</Badge>
                          : <span className="dim">unmetered</span>}
                      </td>
                      {/* ⚠ RULE 4. `terms_document_read: false` means NOBODY HAS
                          READ the platform's terms document - not that it was
                          read and found wanting. Two opposite claims, and only
                          one of them is about the platform, so the cell says
                          "not read by us" rather than anything shorter. */}
                      <td>
                        {s.terms_document_read === false
                          ? <span style={{ color: 'var(--warn)', fontSize: 'var(--fs-xs)' }}>
                              not read by us
                            </span>
                          : s.terms_reviewed_on
                            ? <span className="dim mono" style={{ fontSize: 11 }}>
                                {s.terms_reviewed_on}
                              </span>
                            : <span className="dim">—</span>}
                      </td>
                    </tr>

                    {open === s.id && (
                      <tr>
                        <td colSpan={5} style={{ background: 'var(--surface-2)' }}>
                          <div className="stack stack-1">
                            {s.detail && (
                              <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
                                {s.detail}
                              </p>
                            )}
                            {s.credential_note && (
                              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
                                {s.credential_note}
                              </p>
                            )}
                            {s.terms_document_read === false && (
                              <p style={{ fontSize: 11, color: 'var(--warn)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
                                The platform&rsquo;s terms document has not been read. That is
                                an absence on our side, not a finding about them — what was
                                checked is in the ruling below.
                              </p>
                            )}
                            {s.undescribed && (
                              <Notice icon={<IconAlert />}>
                                This platform is in the contract and this page has not been
                                taught how it is reached. Unknown, which is different from
                                &ldquo;no key&rdquo;.
                              </Notice>
                            )}
                            <span className="dim mono" style={{ fontSize: 11 }}>
                              {s.endpoint || 'no single endpoint — feed-based'}
                            </span>
                            <span className="dim mono" style={{ fontSize: 11 }}>
                              ruling {s.terms_ruling || '—'}
                              {s.terms_reviewed_on ? ` · reviewed ${s.terms_reviewed_on}` : ''}
                              {s.evidence ? ` · ${s.evidence}` : ''}
                            </span>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* DRIFT IN THE OTHER DIRECTION. A platform described here but absent
            from the contract would otherwise look live. */}
        {data?.described_but_not_in_contract?.length > 0 && (
          <Notice icon={<IconAlert />}>
            Described but not in the contract, so nothing harvests them:{' '}
            {data.described_but_not_in_contract.join(', ')}
          </Notice>
        )}

        {data && (
          <span className="dim" style={{ fontSize: 11 }}>{data.credentials_note}</span>
        )}
      </div>
    </section>
  )
}
