import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { modelPage, capLabel, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Unreadable } from '../components/ui'
import { IconAlert, IconArrow, IconExternal } from '../components/Icons'

const STATE = {
  published:    { tone: 'pass', label: 'published' },
  insufficient: { tone: 'warn', label: 'below the gate' },
  unreported:   { tone: 'mute', label: 'nobody has discussed this' },
}

export default function ModelDetail() {
  // `/models/*` rather than `/models/:id`, because an id can contain a
  // slash — google/gemini-2.5-flash is one path segment to us, two to the router.
  const id = useParams()['*']
  const [page, setPage] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  useEffect(() => {
    setPage(null); setErr(null); setUnreadable(null)
    modelPage(id)
      .then(setPage)
      .catch((e) => (e instanceof BoardUnreadable ? setUnreadable(e.message) : setErr(e.message)))
  }, [id])

  return (
    <div className="shell section-tight stack stack-4">
      <Link to="/board" className="row" style={{ gap: 8, fontSize: 'var(--fs-xs)', color: 'var(--text-2)' }}>
        <IconArrow width={13} height={13} style={{ transform: 'rotate(180deg)' }} /> Back to the board
      </Link>

      <div className="stack stack-1">
        <span className="eyebrow">Model</span>
        <h1 style={{ fontSize: 'var(--fs-display)', wordBreak: 'break-word' }}>{id}</h1>
      </div>

      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!page && !err && !unreadable && <div className="skel" style={{ height: 280 }} />}

      {page && (
        <>
          <Notice>{page.summary}</Notice>

          {page.unbound_phrases.length > 0 && (
            <div className="notice" style={{ borderColor: 'var(--fail)', background: 'var(--fail-dim)' }}>
              <IconAlert style={{ flex: 'none', marginTop: 2, color: 'var(--fail)' }} />
              <div>
                <strong style={{ color: 'var(--text)' }}>Phrases with no evidence behind them</strong>
                <p style={{ marginTop: 4 }}>
                  {page.unbound_phrases.join(', ')}
                </p>
                <p style={{ marginTop: 6 }}>
                  These are <strong>not rendered below</strong>. A published phrase with no
                  quote ids is an unfalsifiable claim, and showing it anyway would make a
                  backend defect permanent.
                </p>
              </div>
            </div>
          )}

          <Reveal>
            <section className="card card-flush">
              <div className="card-head">
                <span className="label">Every capability, not only the evidenced ones</span>
                <span className="label">{page.capabilities.length}</span>
              </div>
              <div className="card-body stack stack-3">
                {page.capabilities
                  .filter((c) => !page.unbound_phrases.includes(c.key))
                  .map((c) => {
                  const st = STATE[c.state] || STATE.unreported
                  return (
                    <div key={c.key} className="caprow">
                      <div className="stack" style={{ gap: 5 }}>
                        <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
                          <strong style={{ fontSize: 'var(--fs-sm)' }}>{capLabel(c.key)}</strong>
                          <Badge tone={st.tone}>{st.label}</Badge>
                          {c.needs_positive_consensus && <Badge tone="warn">needs positive consensus</Badge>}
                        </div>
                        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{c.headline}</span>

                        {c.conditions.map((s) => (
                          <div key={s.bucket} className="slice">
                            <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{s.bucket}</span>
                            <span style={{ fontSize: 'var(--fs-xs)' }}>{s.phrase || s.status}</span>
                            <span className="label">
                              {s.voices} {s.voices === 1 ? 'voice' : 'voices'} · {s.platforms}pf
                            </span>
                            {s.note && <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{s.note}</span>}
                            {s.quote_ids.length > 0 && (
                              <div className="wrapf" style={{ marginTop: 4 }}>
                                {s.quote_ids.map((qid) => (
                                  <Quote key={qid} q={page.quotes[qid]} id={qid} />
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          </Reveal>
        </>
      )}
    </div>
  )
}

function Quote({ q, id }) {
  if (!q) return <span className="badge badge-fail">missing quote {id}</span>
  // Published content is quote + attribution + link. Some documents have no
  // URL yet, and an unattributed quote is worse than no quote.
  if (!q.permalink) {
    return <span className="badge badge-warn">quote withheld — no source link</span>
  }
  return (
    <blockquote className="mcard-quote" style={{ width: '100%' }}>
      “{q.text}”
      <cite className="mcard-cite">
        {q.platform} · {q.claimed_at} ·{' '}
        <a href={q.permalink} target="_blank" rel="noreferrer" style={{ color: 'var(--text-2)' }}>
          open <IconExternal width={10} height={10} />
        </a>
      </cite>
    </blockquote>
  )
}
