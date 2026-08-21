import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { listCapabilities, capabilityPage, capLabel, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Unreadable } from '../components/ui'
import { IconAlert, IconArrow } from '../components/Icons'

/**
 * The vocabulary, and what the board knows about each capability.
 *
 * `/capabilities` needs no database, so the list always renders. Opening one
 * calls `/capabilities/{key}`, which does — and answers 503 when there is no
 * database, which is a different thing from a capability nobody has discussed.
 */
export default function Board() {
  const [caps, setCaps] = useState(null)
  const [err, setErr] = useState(null)
  const [params, setParams] = useSearchParams()
  const selected = params.get('cap')

  useEffect(() => {
    listCapabilities().then(setCaps).catch((e) => setErr(e.message))
  }, [])

  const silent = (caps || []).filter((c) => c.requires_positive_consensus)
  const loud = (caps || []).filter((c) => !c.requires_positive_consensus)

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="eyebrow">The board</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>The vocabulary</h1>
        <p className="muted" style={{ maxWidth: '64ch' }}>
          Consensus counting needs a shared key — if one quote is filed under
          “tool calling” and another under “function calling reliability”, they
          never group.{' '}
          {/* Counted, not written down. The list lives in
              contract/capabilities.yaml and is meant to change; a hardcoded
              "twelve" becomes a false statement the day someone adds one, and
              nothing in the build would catch it. */}
          {caps
            ? `These ${caps.length} are what the pipeline tags against.`
            : 'The list below is what the pipeline tags against.'}
        </p>
      </div>

      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!caps && !err && <div className="skel" style={{ height: 240 }} />}

      {caps && (
        <>
          <div className="grid g2">
            <Reveal>
              <CapGroup
                title="Fails silently"
                note="You would not find out you were wrong, so these require positive consensus. An absence of complaints is not evidence."
                tone="warn"
                caps={silent}
                selected={selected}
                onSelect={(k) => setParams(k ? { cap: k } : {})}
              />
            </Reveal>
            <Reveal delay={90}>
              <CapGroup
                title="Fails loudly"
                note="Errors surface in seconds and a validation retry is a real mitigation, so weaker evidence is acceptable."
                tone="info"
                caps={loud}
                selected={selected}
                onSelect={(k) => setParams(k ? { cap: k } : {})}
              />
            </Reveal>
          </div>

          {selected && <CapabilityDetail key={selected} capKey={selected} />}
        </>
      )}
    </div>
  )
}

function CapGroup({ title, note, tone, caps, selected, onSelect }) {
  return (
    <section className="card card-flush" style={{ height: '100%' }}>
      <div className="card-head">
        <span className="label">{title}</span>
        <Badge tone={tone}>{caps.length}</Badge>
      </div>
      <div className="card-body stack stack-2">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{note}</p>
        <ul className="stack stack-1" style={{ marginTop: 6 }}>
          {caps.map((c) => (
            <li key={c.key}>
              <button
                className={`caplink${selected === c.key ? ' on' : ''}`}
                onClick={() => onSelect(selected === c.key ? null : c.key)}
              >
                <span className="stack" style={{ gap: 3, alignItems: 'flex-start' }}>
                  <strong style={{ fontSize: 'var(--fs-sm)' }}>{capLabel(c.key)}</strong>
                  <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{c.key}</span>
                  <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                    “{c.sounds_like.slice(0, 2).join('” · “')}”
                  </span>
                </span>
                <IconArrow width={13} height={13} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

function CapabilityDetail({ capKey }) {
  const [page, setPage] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  useEffect(() => {
    setPage(null); setErr(null); setUnreadable(null)
    capabilityPage(capKey)
      .then(setPage)
      .catch((e) => (e instanceof BoardUnreadable ? setUnreadable(e.message) : setErr(e.message)))
  }, [capKey])

  if (unreadable) return <Unreadable detail={unreadable} />
  if (err) return <Notice icon={<IconAlert />}>{err}</Notice>
  if (!page) return <div className="skel" style={{ height: 160 }} />

  return (
    <Reveal>
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <span className="label">{capLabel(page.key)}</span>
            <Badge tone={page.failure_mode === 'silent' ? 'warn' : 'info'}>{page.failure_mode}</Badge>
          </div>
          <span className="label">{page.models.length} models</span>
        </div>
        <div className="card-body stack stack-3">
          <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{page.summary}</p>

          {page.models.length === 0 && (
            <p className="dim" style={{ fontSize: 'var(--fs-sm)' }}>
              No models in the registry yet.
            </p>
          )}

          {page.models.map((m) => (
            <div key={m.model_version_id} className="modelrow">
              <div className="stack" style={{ gap: 3 }}>
                <Link
                  to={`/models/${encodeURIComponent(m.model_version_id)}`}
                  state={{ from: '/board', name: m.display_name }}
                >
                  <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.display_name || m.model_version_id}</strong>
                </Link>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
                  {m.model_version_id}
                </span>
                {m.phrases.map((p) => (
                  <span key={p} className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{p}</span>
                ))}
              </div>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                {m.state === 'unreported'
                  ? <Badge tone="mute">nobody has discussed this</Badge>
                  : <Badge tone="pass">{m.voices} {m.voices === 1 ? 'voice' : 'voices'}</Badge>}
                {m.conditional && <Badge tone="warn">conditional</Badge>}
                {m.buckets.map((b) => (
                  <span key={b.bucket} className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
                    {b.bucket}:{b.status}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </Reveal>
  )
}
