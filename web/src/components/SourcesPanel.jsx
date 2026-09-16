import { useEffect, useState } from 'react'
import { adminSources } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconLayers } from './Icons'

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

        {sources.map((s) => (
          <div key={s.id} className="stack stack-1"
               style={{ borderLeft: '2px solid var(--line)', paddingLeft: 12 }}>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
              <strong style={{ fontSize: 'var(--fs-sm)' }}>{s.id}</strong>
              {s.method
                ? <Badge tone={METHOD_TONE(s.method)}>{s.method}</Badge>
                : <Badge tone="fail">not described</Badge>}
              {/* THE WHOLE OF WHAT IS SAID ABOUT CREDENTIALS. */}
              <Badge tone="mute">{s.uses_credential ? 'uses a key' : 'no key'}</Badge>
              {s.metered && <Badge tone="warn">metered quota</Badge>}
            </div>

            {s.detail && (
              <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0 }}>
                {s.detail}
              </p>
            )}

            {s.credential_note && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0 }}>
                {s.credential_note}
              </p>
            )}

            {/* ⚠ RULE 4. `terms_document_read: false` means NOBODY HAS READ the
                platform's terms document — not that it was read and found
                wanting. The two are opposite claims and only one is about the
                platform. */}
            {s.terms_document_read === false && (
              <span className="dim" style={{ fontSize: 11, color: 'var(--warn)' }}>
                The platform&rsquo;s terms document has not been read. That is an
                absence on our side, not a finding about them — what was checked
                is recorded in the ruling below.
              </span>
            )}

            {s.undescribed && (
              <Notice icon={<IconAlert />}>
                This platform is in the contract and this page has not been taught
                how it is reached. Unknown, which is different from &ldquo;no key&rdquo;.
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
        ))}

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
