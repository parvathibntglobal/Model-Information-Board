import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminSections, updatesList } from '../api'
import { Notice } from './ui'
import { IconAlert, IconGrid } from './Icons'

/**
 * Admin -> Board & content: the two public sections (Parvathi, 2026-11-02).
 *
 *   AiBenchmarksPanel  what /ai-benchmarks holds now, from the kept copy - no
 *                      build is started from here, so opening Admin never costs
 *                      the public page one
 *   AiUpdatesPanel     what people decided in Manage (update_review), and what
 *                      /ai-news-headlines holds now
 *
 * WIRED to GET /admin/sections (judge/sections_status.py), read-only. The
 * timing values are the contracts' own, sent by the backend, never written
 * here. How many updates WAIT for a person is not stored anywhere: it needs
 * the full build Manage runs, so it is counted only when asked.
 */

function secs(n) {
  if (n == null) return '—'
  if (n < 60) return `${n} s`
  const m = Math.round(n / 60)
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`
}

function at(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso
    : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
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

function useSections() {
  const [state, setState] = useState({ data: null, err: null })
  useEffect(() => {
    let alive = true
    adminSections()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])
  return state
}

function Card({ title, intro, children }) {
  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconGrid width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">{title}</span>
        </div>
        <span className="label">read-only</span>
      </div>
      <div className="card-intro">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>{intro}</p>
      </div>
      <div className="card-body stack stack-4">{children}</div>
    </section>
  )
}

export function AiBenchmarksPanel() {
  const { data, err } = useSections()
  const b = data?.benchmarks
  const k = b?.kept
  return (
    <Card
      title="AI benchmarks — the public page"
      intro="The public page shows the signed-in Benchmarks table's values with their source, link and date. A value marked for review stays signed-in only. Scores are changed on the Benchmarks page; when the run is scheduled is under Scheduler."
    >
      {err && <Notice icon={<IconAlert />}>This could not be read: {err}</Notice>}
      {!data && !err && <div className="skel" style={{ height: 120 }} />}
      {b?.unreadable && <Notice icon={<IconAlert />}>The page's state could not be read: {b.unreadable}</Notice>}
      {b && !b.unreadable && (
        <>
          {k ? (
            <div className="adm-plan-grid">
              <Cell k="Models on the page" v={k.models} sub={`${k.tracked_models} of them tracked`} />
              <Cell k="Benchmarks" v={k.benchmarks_listed} />
              <Cell k="Held back for review" v={k.withheld_for_review}
                    sub="on the signed-in table only until a person decides" />
              <Cell k="Last benchmarks run" v={k.last_run ? at(k.last_run.finished_at) || 'running' : 'none'}
                    sub={k.last_run?.status} />
              <Cell k="Table last checked" v={`${secs(k.checked_seconds_ago)} ago`}
                    sub={`rechecked at most every ${secs(b.recheck_seconds)}`} />
            </div>
          ) : (
            <p className="dim" style={{ margin: 0 }}>
              Not built on this server since it started; the first visit to the page builds it. It is not built from
              here, so opening Admin never slows the public page.
            </p>
          )}
          <span className="dim mono" style={{ fontSize: 11 }}>{b.setting} = {b.recheck_seconds}</span>
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            <Link className="btn btn-ghost" to={b.path}>Open the public page →</Link>
            <Link className="btn btn-ghost" to="/benchmarks">Benchmarks table →</Link>
          </div>
        </>
      )}
    </Card>
  )
}

const TIMING = [
  ['window_days', 'Manage looks back, by default', 'days'],
  ['max_window_days', 'The furthest any list looks back, the public page included', 'days'],
  ['home_days', 'A published headline stays on the home page', 'days'],
  ['home_limit', 'Headlines on the home page, at most', ''],
  ['home_cache_seconds', 'The public reads are kept for', 'seconds'],
  ['unread_cache_seconds', '…or, when part of the data could not be read', 'seconds'],
  ['cold_wait_seconds', 'A visitor waits for a build already running, at most', 'seconds'],
]

export function AiUpdatesPanel() {
  const { data, err } = useSections()
  const [waiting, setWaiting] = useState({ busy: false, n: null, err: null })
  const u = data?.updates
  const kinds = u?.kinds || {}
  const rows = u?.decisions ? Object.entries(u.decisions) : []
  const total = (key) => rows.reduce((n, [, v]) => n + (v[key] || 0), 0)

  const countWaiting = () => {
    setWaiting({ busy: true, n: null, err: null })
    updatesList()
      .then((d) => setWaiting({ busy: false, err: null,
        n: (d.updates || []).filter((x) => !x.gone && x.status === 'pending').length }))
      .catch((e) => setWaiting({ busy: false, n: null, err: e.message }))
  }

  return (
    <Card
      title="AI updates — the public page"
      intro="Headlines are rebuilt from the data on every read; only what people decide in Manage is stored. The public page shows every approved update. What keeps the data current is under Scheduler: the registry poll and the benchmarks run."
    >
      {err && <Notice icon={<IconAlert />}>This could not be read: {err}</Notice>}
      {!data && !err && <div className="skel" style={{ height: 120 }} />}
      {u?.unreadable && <Notice icon={<IconAlert />}>The page's state could not be read: {u.unreadable}</Notice>}
      {u && !u.unreadable && (
        <>
          <div className="adm-plan-grid">
            <Cell k="Approved" v={u.decisions ? total('approved') : '—'} sub="shown on the public page" />
            <Cell k="Declined" v={u.decisions ? total('declined') : '—'} />
            <Cell k="On the home page" v={u.decisions ? total('on_home') : '—'} sub="published at some point; old ones drop off by themselves" />
            <Cell k="Public page now" v={u.public_kept ? u.public_kept.updates : '—'}
                  sub={u.public_kept ? 'headlines in its kept copy' : 'nothing kept yet on this server'} />
            <Cell k="Waiting for review"
                  v={waiting.n != null ? waiting.n
                    : <button type="button" className="btn btn-ghost" onClick={countWaiting} disabled={waiting.busy}>
                        {waiting.busy ? 'Counting…' : 'Count'}
                      </button>}
                  sub={waiting.err ? `could not count: ${waiting.err}` : 'needs the full build Manage runs (about 12 s on the shared database)'} />
          </div>

          {!u.decisions && (
            <Notice icon={<IconAlert />}>The review tables are not in this database, so no decision can be counted.</Notice>
          )}
          {rows.length > 0 && (
            <div className="tablewrap"><table>
              <thead><tr><th>Kind</th><th className="r">Approved</th><th className="r">Declined</th><th className="r">On home</th></tr></thead>
              <tbody>
                {rows.sort(([a], [b]) => a.localeCompare(b)).map(([kind, v]) => (
                  <tr key={kind}>
                    <td>{kinds[kind] || kind}</td>
                    <td className="r tnum">{v.approved}</td>
                    <td className="r tnum">{v.declined}</td>
                    <td className="r tnum">{v.on_home}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}

          <div className="stack stack-1">
            <span className="label">Timing — {u.setting}</span>
            <div className="tablewrap"><table>
              <tbody>
                {TIMING.filter(([key]) => u.timing?.[key] != null).map(([key, words, unit]) => (
                  <tr key={key}>
                    <th scope="row">{words}</th>
                    <td className="tnum">{u.timing[key]} {unit}</td>
                    <td className="dim mono" style={{ fontSize: 11 }}>{key}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>

          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            <Link className="btn btn-ghost" to={u.path}>Open the public page →</Link>
            <Link className="btn btn-ghost" to="/updates">Manage →</Link>
          </div>
        </>
      )}
    </Card>
  )
}
