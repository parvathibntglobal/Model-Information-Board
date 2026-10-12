import { useEffect, useState } from 'react'
import { adminLostClaims } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert } from './Icons'

/**
 * Admin -> Runs, the bottom block: claims the model proposed that failed
 * validation and were never stored, per recent run and by error.
 *
 * Each error is folded to its shape (`board_entries.slug: ...`), written per
 * thread since 2026-09-23. A "board entry" error is #411's case: one bad entry
 * loses its whole claim, including the valid entries beside it. Runs from
 * before the shapes were recorded say so instead of reading as clean. Read-only.
 */

const day = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '')

export default function LostClaimsPanel() {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    adminLostClaims()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const errors = Object.entries(data?.by_error || {})
  const totalLost = (data?.runs || []).reduce((n, r) => n + (r.lost || 0), 0)
  return (
    <div className="stack stack-2">
      <span className="label">Lost claims — proposed by the model, failed validation, never stored</span>
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!data && !err && <div className="skel" style={{ height: 120 }} />}
      {data && (
        <>
          {errors.length > 0 ? (
            <div className="tablewrap"><table>
              <thead><tr><th>Why they failed (last {data.runs.length} runs)</th><th>Times</th></tr></thead>
              <tbody>
                {errors.map(([k, n]) => (
                  <tr key={k}>
                    <th>
                      <span className="mono" style={{ fontSize: 12 }}>{k}</span>
                      {k.startsWith('board_entries.') && (
                        <div style={{ marginTop: 4 }}>
                          <Badge tone="warn">one bad entry loses the whole claim</Badge>
                        </div>
                      )}
                    </th>
                    <td className="tnum">{n}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          ) : (
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No validation errors recorded in these runs.</span>
          )}
          <div className="tablewrap"><table>
            <thead><tr><th>Run</th><th>Threads</th><th>Verified</th><th>Failed the quote check</th><th>Lost to validation</th></tr></thead>
            <tbody>
              {data.runs.map((r) => (
                <tr key={r.run_id}>
                  <th>{r.model}<div className="dim" style={{ fontSize: 11 }}>{day(r.started_at)}</div></th>
                  <td className="tnum">{r.threads}</td>
                  <td className="tnum">{r.verified}</td>
                  <td className="tnum">{r.rejected}</td>
                  <td className="tnum">
                    {r.lost > 0 ? <Badge tone="warn">{r.lost}</Badge> : r.lost}
                    {!r.reasons_recorded && <div className="dim" style={{ fontSize: 11 }}>reasons not recorded</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
            {totalLost} claims lost across these runs. Counts are errors, not claims: one claim can fail more
            than one check. The errors tagged "one bad entry loses the whole claim" are issue #411.
          </span>
        </>
      )}
    </div>
  )
}
