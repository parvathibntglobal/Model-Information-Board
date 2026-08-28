import { useCallback, useEffect, useState } from 'react'
import {
  BoardUnreadable,
  capabilityCandidates,
  deleteCapability,
  editCapability,
  ruleCapability,
} from '../api'
import { Badge, Notice, Unreadable } from './ui'
import { IconAlert, IconLayers } from './Icons'

/**
 * Capability discovery review. The extractor proposes a key none of the twelve
 * name; here an admin adopts / declines / merges / edits / deletes it.
 *
 * Adopting records the decision — the vocabulary itself changes in a
 * contract/capabilities.yaml PR, never from this page, because a ruling must not
 * grow the vocabulary sideways. Declining keeps the evidence; deleting discards
 * it, so the two are separate actions rather than one.
 */
export default function CapabilityReview() {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })

  const load = useCallback(() => {
    capabilityCandidates()
      .then((d) => setState({ data: d, err: null, unreadable: null }))
      .catch((e) =>
        setState({
          data: null,
          err: e instanceof BoardUnreadable ? null : e.message,
          unreadable: e instanceof BoardUnreadable ? e.message : null,
        }),
      )
  }, [])
  useEffect(() => { load() }, [load])

  const { data, err, unreadable } = state
  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Proposed capabilities — the extractor&apos;s, awaiting a ruling</span>
        </div>
        {data && (
          <span className="label">
            {data.summary.unruled_keys} unruled · {data.summary.keys} keys
          </span>
        )}
      </div>
      <div className="card-body stack stack-3">
        {unreadable && <Unreadable detail={unreadable} compact />}
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && !unreadable && <div className="skel" style={{ height: 120 }} />}
        {data && (
          <>
            <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
              The model proposes a key; you rule. Adopting one is a
              contract/capabilities.yaml PR, not a button here — this records the
              decision and the evidence behind it.
            </p>
            <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{data.note}</p>
            {data.candidates.length === 0 && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>Nothing proposed yet.</p>
            )}
            {data.candidates.map((g) => (
              <GroupCard key={g.proposed_key} group={g} onDone={load} />
            ))}
          </>
        )}
      </div>
    </section>
  )
}

const INPUT = {
  fontSize: 'var(--fs-xs)',
  padding: '4px 8px',
  borderRadius: 6,
  border: '1px solid var(--bg-3, rgba(127,127,127,.3))',
  background: 'var(--bg-2, transparent)',
  color: 'var(--text)',
  minWidth: 200,
}

function GroupCard({ group, onDone }) {
  const [action, setAction] = useState(null) // 'adopt' | 'merge' | 'edit' | null
  const [target, setTarget] = useState('')
  const [newKey, setNewKey] = useState(group.proposed_key)
  const [newDef, setNewDef] = useState(group.definitions[0] || '')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const run = async (fn) => {
    setBusy(true)
    setErr(null)
    try {
      await fn()
      setAction(null)
      onDone()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const ruled = group.ruling
  const ruledTone = ruled === 'adopted' ? 'pass' : ruled === 'declined' ? 'fail' : 'info'

  return (
    <div className="caprow" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 8 }}>
      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        <strong className="mono" style={{ fontSize: 'var(--fs-sm)' }}>{group.proposed_key}</strong>
        <Badge tone="mute">≥ {group.count} doc{group.count === 1 ? '' : 's'}</Badge>
        {group.verified < group.count && (
          <Badge tone="warn">{group.count - group.verified} unverified</Badge>
        )}
        {ruled && (
          <Badge tone={ruledTone}>
            {ruled}{group.ruling_target ? ` → ${group.ruling_target}` : ''}
          </Badge>
        )}
      </div>

      {group.definitions.map((d, i) => (
        <span key={i} className="dim" style={{ fontSize: 'var(--fs-xs)' }}>&ldquo;{d}&rdquo;</span>
      ))}
      {group.examples.slice(0, 2).map((ex) => (
        <span key={ex.id} style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          {ex.quote_verified ? '' : '⚠ '}&ldquo;{ex.quote}&rdquo;
        </span>
      ))}

      {err && <Notice icon={<IconAlert />}>{err}</Notice>}

      {action === 'adopt' || action === 'merge' ? (
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          <input
            style={INPUT}
            placeholder={action === 'adopt' ? 'adopt as key…' : 'merge into key…'}
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
          <button
            type="button"
            className="chip chip-on"
            disabled={busy || !target.trim()}
            onClick={() =>
              run(() =>
                ruleCapability(group.proposed_key, action === 'adopt' ? 'adopted' : 'merged', target.trim()),
              )
            }
          >
            Confirm {action}
          </button>
          <button type="button" className="chip" onClick={() => setAction(null)}>Cancel</button>
        </div>
      ) : action === 'edit' ? (
        <div className="stack stack-1">
          <input style={INPUT} value={newKey} onChange={(e) => setNewKey(e.target.value)} placeholder="key" />
          <input style={INPUT} value={newDef} onChange={(e) => setNewDef(e.target.value)} placeholder="definition" />
          <div className="row" style={{ gap: 6 }}>
            <button
              type="button"
              className="chip chip-on"
              disabled={busy}
              onClick={() =>
                run(() =>
                  editCapability(group.proposed_key, {
                    new_key: newKey.trim() && newKey.trim() !== group.proposed_key ? newKey.trim() : null,
                    new_definition: newDef,
                  }),
                )
              }
            >
              Save
            </button>
            <button type="button" className="chip" onClick={() => setAction(null)}>Cancel</button>
          </div>
        </div>
      ) : (
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          <button type="button" className="chip" disabled={busy} onClick={() => setAction('adopt')}>Adopt</button>
          <button type="button" className="chip" disabled={busy} onClick={() => run(() => ruleCapability(group.proposed_key, 'declined'))}>Decline</button>
          <button type="button" className="chip" disabled={busy} onClick={() => setAction('merge')}>Merge</button>
          <button type="button" className="chip" disabled={busy} onClick={() => setAction('edit')}>Edit</button>
          <button
            type="button"
            className="chip"
            disabled={busy}
            onClick={() => {
              if (
                window.confirm(
                  `Delete all ${group.count} proposal(s) for "${group.proposed_key}"?\n\n` +
                    'Declining keeps the evidence; deleting discards it.',
                )
              ) {
                run(() => deleteCapability(group.proposed_key))
              }
            }}
          >
            Delete
          </button>
        </div>
      )}
    </div>
  )
}
