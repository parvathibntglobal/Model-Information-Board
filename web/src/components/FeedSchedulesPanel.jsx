import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminSchedules } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconClock } from './Icons'

/**
 * Scheduler, under the nightly fetches (Parvathi, 2026-11-02): the GitHub
 * Actions that feed the two public sections.
 *
 *   AI benchmarks   its own workflow, benchmarks.yml, behind its own switch
 *                   BENCHMARKS_SCHEDULE_ENABLED - separate from the nightly
 *                   fetches' SCHEDULER_ENABLED
 *   AI updates      no workflow of its own: it is rebuilt on every read from
 *                   what the registry poll (launches, prices) and the
 *                   benchmarks runs wrote, so those are its feeds
 *
 * ONE TAB EACH inside Admin -> Scheduler (SchedulerTabs.jsx), beside the
 * nightly fetches' own tab.
 *
 * WIRED to GET /admin/schedules (judge/sections_status.py), read-only. Like the
 * nightly block, NO BUTTON CHANGES ANYTHING: a run is started on GitHub, or
 * from the signed-in Benchmarks page.
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

function Result({ r }) {
  if (r.status !== 'completed') return <Badge tone="info">{r.status}</Badge>
  if (r.conclusion === 'success') return <span className="run-ok">✓ success</span>
  return <Badge tone="fail">{r.conclusion}</Badge>
}

const TITLES = {
  benchmarks: 'AI benchmarks — the benchmarks run',
  'registry-poll': 'AI updates — the registry poll',
}

// bench_run_trigger_ck (contract/tables.sql).
const TRIGGERS = { scheduled: 'scheduled', manual_run: 'by hand (GitHub or CLI)', page_button: 'Run button' }

/** What the last benchmarks runs did, from the run's own record. */
function BenchRuns({ b }) {
  if (!b) return null
  if (b.unreadable) {
    return <span className="dim" style={{ fontSize: 11 }}>What each run did can't be read here: the benchmarks data did not answer ({b.unreadable}).</span>
  }
  if (!b.runs.length) return <span className="dim">No benchmarks run recorded yet.</span>
  return (
    <div className="tablewrap"><table>
      <thead><tr><th>Run</th><th>How</th><th>Result</th><th className="r">Sources</th><th className="r">Values</th><th className="r">Changes</th><th className="r">For review</th></tr></thead>
      <tbody>
        {b.runs.map((r) => (
          <tr key={r.id}>
            <td>{at(r.started_at)}{r.dry_run && <span className="dim"> · dry run</span>}</td>
            <td className="dim">{TRIGGERS[r.trigger] || r.trigger}</td>
            <td>{r.status === 'ok' ? <span className="run-ok">✓ ok</span>
              : <Badge tone={r.status === 'running' || r.status === 'dry_run' ? 'info' : 'fail'}>{r.status.replace('_', ' ')}</Badge>}</td>
            <td className="r tnum" title={r.sources_failed.length ? `not read: ${r.sources_failed.join(', ')}` : undefined}>
              {r.sources_read - r.sources_failed.length} of {r.sources_read}
            </td>
            <td className="r tnum">{r.totals?.cells ?? '—'}</td>
            <td className="r tnum">{r.totals?.changes ?? '—'}</td>
            <td className="r tnum">{r.totals?.open_review_items ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table></div>
  )
}

function Feed({ f }) {
  const s = f.setup || {}
  const gh = f.github || {}
  const last = (gh.runs || [])[0]
  const sw = f.switch
  return (
    <div className="stack stack-2">
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>Feeds {f.feeds}.</span>
      {s.unreadable ? <Notice icon={<IconAlert />}>{s.unreadable}</Notice> : (
        <div className="adm-plan-grid">
          {f.variable && (
            <Cell k="Switch" v={sw?.state === 'on' ? <span className="run-ok">● on</span>
                                : sw?.state === 'off' ? <Badge tone="fail">off</Badge>
                                : 'can’t be read here'}
                  sub={sw?.state ? `${f.variable} = ${JSON.stringify(sw.value)}` : `${f.variable} · ${sw?.unreadable || ''}`} />
          )}
          {!f.variable && <Cell k="Switch" v="none" sub="runs on every firing" />}
          <Cell k="Schedule" v={(s.crons || []).map((c) => c.words).join(' · ') || 'no schedule'}
                sub={s.manual_run ? 'can also be started by hand' : null} />
          <Cell k="Next run" v={f.next_run ? at(f.next_run) : '—'}
                sub={f.next_run ? (f.variable && sw?.state === 'off' ? 'fires, but does nothing while the switch is off' : 'GitHub may start it a little late') : null} />
          <Cell k="Last run" v={last ? at(last.started_at) : 'none yet'}
                sub={last ? `${last.event === 'schedule' ? 'scheduled' : 'started by hand'} · ${last.conclusion || last.status}` : null} />
        </div>
      )}
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
                <td><Result r={r} /></td>
                <td className="r tnum">{mins(r.minutes)}</td>
                <td>{r.url && <a className="mb-link" href={r.url} target="_blank" rel="noopener noreferrer">#{r.number} ↗</a>}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
      {f.key === 'benchmarks' && (
        <div className="stack stack-1">
          <span className="label">What each benchmarks run did</span>
          <BenchRuns b={f.bench_runs} />
        </div>
      )}
      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        {f.link && <a className="btn btn-ghost" href={f.link} target="_blank" rel="noopener noreferrer">Run now / see all runs ↗</a>}
        {f.key === 'benchmarks' && <Link className="btn btn-ghost" to="/benchmarks">Benchmarks page →</Link>}
        {f.key === 'registry-poll' && <Link className="btn btn-ghost" to="/updates">AI updates — Manage →</Link>}
      </div>
    </div>
  )
}

const INTROS = {
  benchmarks: 'AI benchmarks is filled by its own scheduled run, with its own switch, separate from the '
    + 'nightly fetches. The same run also gives AI updates its benchmark headlines. Everything here is read-only.',
  'registry-poll': 'AI updates has no job of its own: it is rebuilt from the data each time it is opened. '
    + 'The registry poll keeps its new models and price changes current; its benchmark headlines come '
    + 'from the benchmarks run (the Benchmarks tab). Everything here is read-only.',
}

/** One feed, `only` = its key (benchmarks | registry-poll). Each Scheduler
 *  tab mounts one, so each reads /admin/schedules when it is opened. */
export default function FeedSchedulesPanel({ only }) {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    adminSchedules()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const feed = data?.feeds.find((f) => f.key === only)

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconClock width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Scheduler — {TITLES[only] || only}</span>
        </div>
        {data && <span className="label">read-only</span>}
      </div>

      <div className="card-intro">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          {INTROS[only]}
        </p>
      </div>

      <div className="card-body stack stack-4">
        {err && <Notice icon={<IconAlert />}>This schedule could not be read: {err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 160 }} />}
        {data && (feed ? <Feed f={feed} /> : <p className="dim">This backend does not report that schedule.</p>)}
      </div>
    </section>
  )
}
