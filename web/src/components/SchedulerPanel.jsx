import { useEffect, useState } from 'react'
import { adminScheduler } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconClock } from './Icons'

/**
 * Scheduler: the scheduled per-model fetches - how they are set up, who is due
 * next, and what the scheduled runs did.
 *
 * WIRED (2026-10-06) to GET /admin/scheduler (`judge/scheduler_status.py`),
 * read-only. The scheduler is a GitHub Action
 * (.github/workflows/scheduled-fetches.yml) running
 * scripts/run_scheduled_fetches.py, so:
 *   setup   the workflow's cron line and limits, and the secret / variable
 *           NAMES it needs - never values
 *   policy  contract/scheduler.yaml (cadence, thread caps)
 *   queue   the runner's own selection against this database
 *   runs    the workflow's runs from GitHub: the record of what the schedule
 *           did (fetch_log cannot tell a scheduled fetch from a button fetch)
 *
 * ⚠ NO BUTTONS THAT CHANGE ANYTHING. "Run now" is the workflow's Run workflow
 *   button on GitHub and spends money; the panel links to it. The on/off switch
 *   is not shown (decided 2026-10-06).
 */

function at(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso
    : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function mins(m) {
  if (m == null) return '—'
  if (m < 1) return '< 1 m'
  const r = Math.round(m)
  const h = Math.floor(r / 60)
  return h ? `${h} h ${r % 60} m` : `${r} m`
}

function Cell({ k, v, sub }) {
  return (
    <div className="adm-plan-cell">
      <span className="label">{k}</span>
      <span className="adm-plan-v">{v}</span>
      {sub && <span className="dim" style={{ fontSize: 11 }}>{sub}</span>}
    </div>
  )
}

export default function SchedulerPanel() {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    adminScheduler()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const setup = data?.setup || {}
  const pol = data?.policy || {}
  const q = data?.queue || {}
  const gh = data?.github || {}
  const links = data?.links || {}
  const last = (gh.runs || [])[0]
  const cron = (setup.crons || [])[0]

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconClock width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Scheduler — scheduled fetches of the tracked models</span>
        </div>
        {data && <span className="label">read-only</span>}
      </div>

      <div className="card-intro">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          A GitHub Action fetches the tracked models on a schedule: each night it picks the models that are
          due and runs the same fetch the Fetch button runs, one model at a time. Everything here is
          read-only.
        </p>
      </div>

      <div className="card-body stack stack-4">
        {err && <Notice icon={<IconAlert />}>The scheduler could not be read: {err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 200 }} />}

        {data && (
          <>
            {/* ── at a glance ─────────────────────────────────────────── */}
            <div className="adm-plan-grid">
              <Cell k="Schedule" v={cron ? cron.words : '—'} sub={cron ? `cron "${cron.expr}"` : null} />
              <Cell k="Next run" v={data.next_run ? at(data.next_run) : '—'}
                    sub={data.next_run ? 'GitHub may start it a little late' : null} />
              <Cell k="Last run" v={last ? at(last.started_at) : 'none yet'}
                    sub={last ? `${last.event === 'schedule' ? 'scheduled' : 'started by hand'} · ${last.conclusion || last.status}` : null} />
              <Cell k="Due now" v={q.unreadable ? '—' : `${(q.due || []).length} of ${q.tracked ?? '—'} tracked`} />
              <Cell k="Cadence" v={pol.cadence_days ? `every ${pol.cadence_days} days` : '—'}
                    sub="after a model's last successful fetch" />
              <Cell k="Threads per fetch" v={pol.first_fetch_thread_cap ? `${pol.first_fetch_thread_cap} first · ${pol.refresh_thread_cap} refresh` : '—'} />
            </div>

            {/* ── how it is set up ────────────────────────────────────── */}
            <div className="stack stack-2">
              <span className="label">How the cron job is set up</span>
              {setup.unreadable ? <Notice icon={<IconAlert />}>{setup.unreadable}</Notice> : (
                <div className="tablewrap"><table>
                  <tbody>
                    <tr><th scope="row">Where it runs</th>
                      <td>GitHub Actions workflow <strong>{setup.workflow}</strong> on <span className="mono">{setup.runs_on}</span>
                        <span className="dim mono" style={{ display: 'block', fontSize: 11 }}>{setup.file}</span></td></tr>
                    <tr><th scope="row">When</th>
                      <td>{(setup.crons || []).map((c) => c.words).join(', ') || 'no schedule'}
                        {setup.manual_run && <span className="dim"> · can also be started by hand{setup.manual_inputs?.length ? ` (options: ${setup.manual_inputs.join(', ')})` : ''}</span>}</td></tr>
                    <tr><th scope="row">Limits</th>
                      <td>job stops at {setup.timeout_minutes} min; no new model is started after {setup.deadline_minutes} min
                        {setup.one_at_a_time && <span className="dim"> · one run at a time</span>}</td></tr>
                    <tr><th scope="row">What it does</th>
                      <td>Picks the due models (never fetched first, then the oldest), runs a fetch for each, and posts a
                        summary to the issue named by <span className="mono">SCHEDULER_ISSUE</span>.</td></tr>
                    <tr><th scope="row">Needs</th>
                      <td>
                        <span className="dim" style={{ fontSize: 11 }}>secrets</span>{' '}
                        {(setup.secrets || []).map((s) => <span key={s} className="mono kw-chip">{s}</span>)}
                        <br />
                        <span className="dim" style={{ fontSize: 11 }}>variables</span>{' '}
                        {(setup.variables || []).map((s) => <span key={s} className="mono kw-chip">{s}</span>)}
                        <span className="dim" style={{ display: 'block', fontSize: 11, marginTop: 4 }}>
                          Names only. Whether each is set is visible only in the repository settings.
                        </span>
                      </td></tr>
                  </tbody>
                </table></div>
              )}
            </div>

            {/* ── controls: links, not buttons ────────────────────────── */}
            <div className="stack stack-1">
              <span className="label">Controls (on GitHub)</span>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                {links.workflow && <a className="btn btn-ghost" href={links.workflow} target="_blank" rel="noopener noreferrer">Run now / see all runs ↗</a>}
                {links.secrets && <a className="btn btn-ghost" href={links.secrets} target="_blank" rel="noopener noreferrer">Secrets ↗</a>}
              </div>
              <span className="dim" style={{ fontSize: 11 }}>
                "Run now" is the workflow's <strong>Run workflow</strong> button; it fetches every due model and spends money.
              </span>
            </div>

            {/* ── queue ───────────────────────────────────────────────── */}
            <div className="stack stack-1">
              <span className="label">Queue — who the next run would fetch, in order</span>
              {q.unreadable ? <Notice icon={<IconAlert />}>The queue could not be worked out: {q.unreadable}</Notice> : (
                <div className="tablewrap"><table>
                  <thead><tr><th>#</th><th>Model</th><th>Last success</th><th>Why it is due</th><th className="r">Thread cap</th></tr></thead>
                  <tbody>
                    {(q.due || []).length === 0 ? (
                      <tr><td colSpan={5} className="dim">Nobody is due: every tracked model was fetched within {pol.cadence_days} days.</td></tr>
                    ) : q.due.map((d, i) => (
                      <tr key={d.model_version_id}>
                        <td className="dim tnum">{i + 1}</td>
                        <td><strong style={{ fontSize: 'var(--fs-sm)' }}>{d.name}</strong></td>
                        <td className="dim">{d.last_success ? at(d.last_success) : 'never'}</td>
                        <td className="dim">{d.reason}</td>
                        <td className="r tnum">{d.thread_cap}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              )}
              {(q.not_due || []).length > 0 && (
                <span className="dim" style={{ fontSize: 11 }}>
                  Not due yet: {q.not_due.map((n) => n.name).join(', ')}.
                </span>
              )}
            </div>

            {/* ── log ─────────────────────────────────────────────────── */}
            <div className="stack stack-1">
              <span className="label">Log — every run of the scheduled workflow</span>
              {gh.unreadable ? <Notice icon={<IconAlert />}>The workflow's runs could not be read from GitHub: {gh.unreadable}</Notice> : (
                <div className="tablewrap"><table>
                  <thead><tr><th>Started</th><th>How</th><th>Result</th><th className="r">Took</th><th>Run</th></tr></thead>
                  <tbody>
                    {(gh.runs || []).length === 0 ? (
                      <tr><td colSpan={5} className="dim">No run yet.</td></tr>
                    ) : gh.runs.map((r) => (
                      <tr key={r.id}>
                        <td>{at(r.started_at)}</td>
                        <td className="dim">{r.event === 'schedule' ? 'scheduled' : r.event === 'workflow_dispatch' ? 'by hand' : r.event}</td>
                        <td>
                          {r.status !== 'completed'
                            ? <Badge tone="info">{r.status}</Badge>
                            : r.conclusion === 'success'
                              ? <span className="run-ok">✓ success</span>
                              : <Badge tone="fail">{r.conclusion}</Badge>}
                        </td>
                        <td className="r tnum">{mins(r.minutes)}</td>
                        <td>{r.url && <a className="mb-link" href={r.url} target="_blank" rel="noopener noreferrer">#{r.number} ↗</a>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              )}
              <span className="dim" style={{ fontSize: 11 }}>
                Each fetch a run makes also appears under Runs, like any other fetch.
              </span>
            </div>
          </>
        )}
      </div>
    </section>
  )
}
