import { useEffect, useState } from 'react'
import { adminUsageBilled } from '../api'
import { Badge, Notice, Stat } from './ui'
import { IconAlert } from './Icons'

/**
 * Admin -> API usage, the bottom block: what each recent run was BILLED, beside
 * what our ledger ESTIMATED, and which providers served its calls.
 *
 * The estimate is tokens x a configured price; the billed figure is what the
 * provider reported per call (#381). They differ because the price depends on
 * the upstream that served the call and on how much of the prompt was cached.
 * A run whose calls moved between upstreams cannot have kept a warm cache.
 *
 * CACHED TOKENS ARE NOT RECORDED for past runs, so no hit rate is shown - the
 * panel says so rather than estimating one (rule 6). Read-only.
 */

const usd = (n) => (n == null ? null : `$${n < 0.01 ? n.toFixed(4) : n.toFixed(3)}`)
const day = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '')

export default function BilledCostPanel() {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    adminUsageBilled()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const t = data?.totals
  return (
    <div className="stack stack-2" style={{ paddingTop: 'var(--s3)', borderTop: '1px solid var(--border-soft)' }}>
      <span className="label">Billed cost per run — what the provider charged, beside our estimate</span>
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!data && !err && <div className="skel" style={{ height: 120 }} />}
      {data && (
        <>
          <div className="grid g3">
            <Stat n={usd(t.billed_usd)} l={`billed over the last ${t.runs} runs`} />
            <Stat n={usd(t.estimated_usd)} l="our estimate for the same runs" />
            <Stat n={t.estimated_usd ? `${(t.billed_usd / t.estimated_usd).toFixed(1)}×` : '—'}
                  l="billed ÷ estimate" />
          </div>
          <div className="tablewrap"><table>
            <thead>
              <tr><th>Run</th><th>Threads</th><th>Billed</th><th>Estimated</th><th>Providers that served it</th></tr>
            </thead>
            <tbody>
              {data.runs.map((r) => (
                <tr key={r.run_id}>
                  <th>{r.model}<div className="dim" style={{ fontSize: 11 }}>{day(r.started_at)}</div></th>
                  <td className="tnum">{r.threads}</td>
                  <td className="tnum">
                    {usd(r.billed_usd)}
                    {r.threads_without_billed_cost > 0 && (
                      <div className="dim" style={{ fontSize: 11 }}>{r.threads_without_billed_cost} without a billed figure</div>
                    )}
                  </td>
                  <td className="tnum">{usd(r.estimated_usd)}</td>
                  <td>
                    {r.upstreams.length ? r.upstreams.join(', ') : <span className="dim">not recorded</span>}
                    {r.upstream_switches > 0 && (
                      <div style={{ marginTop: 4 }}>
                        <Badge tone="warn">switched {r.upstream_switches}×</Badge>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            A provider switch starts a cold prompt cache, so those calls cost more. Prompt-cache hit rate:
            not recorded for these runs.
          </span>
        </>
      )}
    </div>
  )
}
