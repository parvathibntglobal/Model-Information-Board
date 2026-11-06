import { useEffect, useState } from 'react'
import { adminHeldModels } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconGrid } from './Icons'

/**
 * Models the board holds claims about but has not seated (#602).
 *
 * A verified claim whose model has no registry row is HELD in
 * `unresolved_entry` by the name as written, instead of being dropped. This
 * lists each held name against `seating_bar` in contract/tracked_models.yaml.
 * A name that meets the bar is put to a person to seat; nothing is seated
 * automatically. Once seated, `scripts/attribute_unresolved_entries.py` files
 * its held rows onto the board.
 *
 * ⚠ A LOWER BOUND. Nobody searches for an unseated model, so its count is only
 *   what threads found for other models happened to say about it.
 */
export default function HeldModelsPanel() {
  const [state, setState] = useState({ data: null, err: null })
  const [all, setAll] = useState(false)

  useEffect(() => {
    let alive = true
    adminHeldModels()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const held = data?.held || []
  const shown = all ? held : held.slice(0, 12)
  const bar = data?.seating_bar || {}
  const meeting = held.filter((h) => h.meets_bar).length

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconGrid width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Held, not seated</span>
        </div>
        {data && !data.reason && (
          <span className="dim tnum" style={{ fontSize: 11 }}>
            {held.length} name(s) · {meeting} meet the bar · {data.filed ?? 0} entries filed after seating
          </span>
        )}
      </div>
      <div className="card-body stack stack-3">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Verified claims about a model with no registry row, kept by the name as
          written. A name with at least {bar.held_entries ?? '—'} entries from{' '}
          {bar.distinct_authors ?? '—'} distinct authors is put to a person to seat;
          nothing is seated automatically. The counts are a lower bound: an unseated
          model is not searched for.
        </p>
        {err && <Notice icon={<IconAlert />}>Held models could not be loaded: {err}</Notice>}
        {data?.reason && <Notice icon={<IconAlert />}>{data.reason}</Notice>}
        {data && !data.reason && held.length === 0 && (
          <span className="dim" style={{ fontSize: 11 }}>No held entries.</span>
        )}
        {shown.length > 0 && (
          <table className="table">
            <thead>
              <tr><th>Name as written</th><th>Entries</th><th>Authors</th><th>Documents</th><th>Held</th><th /></tr>
            </thead>
            <tbody>
              {shown.map((h) => (
                <tr key={h.surface}>
                  <td className="mono" style={{ fontSize: 11 }}>{h.surface}</td>
                  <td className="tnum">{h.entries}</td>
                  <td className="tnum">{h.authors}</td>
                  <td className="tnum">{h.documents}</td>
                  <td className="dim tnum" style={{ fontSize: 11 }}>
                    {h.first_held === h.last_held ? h.first_held : `${h.first_held} – ${h.last_held}`}
                  </td>
                  <td>{h.meets_bar && <Badge tone="warn">meets bar</Badge>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {held.length > 12 && (
          <button type="button" className="btn btn-ghost" style={{ alignSelf: 'flex-start' }}
                  onClick={() => setAll((v) => !v)}>
            {all ? 'Show fewer' : `Show all ${held.length}`}
          </button>
        )}
      </div>
    </section>
  )
}
