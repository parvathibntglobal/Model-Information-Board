import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminIndustryAi, adminSchedules } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconGrid } from './Icons'
import { when } from '../scheduleWords'

/**
 * Admin -> Board & content -> AI in industries (2026-11-25, Parvathi): the state
 * of the Industry AI data, for the team. A signed-in page, so this is not "what
 * the public page holds" like the two panels beside it, but what the stored data
 * is and whether it needs a hand:
 *
 *   rules       which rules version the stored labels carry, against the
 *               contract's - a mismatch means a `--relabel` is owed
 *   waiting     posts saved but not labelled (a labelling that failed)
 *   switches    the contract's harvest and observer switches, and the scheduled
 *               run's on/off switch (read from GitHub, as Scheduler does)
 *   runs        the last runs, with requests against each platform's cap
 *   retention   text cleared so far, and due at the next run
 *
 * WIRED to GET /admin/industry-ai (judge/industry_ai/view.py industry_ai_admin)
 * and GET /admin/schedules. Read-only. Every number comes from them (rule 11).
 */

const PLATFORM = {
  reddit: 'Reddit', x: 'X', github: 'GitHub', hackernews: 'Hacker News', devto: 'dev.to',
  bluesky: 'Bluesky', feeds: 'Blogs & feeds',
}
const n = (v) => (v ?? 0).toLocaleString('en-GB')

function Cell({ k, v, sub }) {
  return (
    <div className="adm-plan-cell">
      <span className="label">{k}</span>
      <span className="adm-plan-v">{v}</span>
      {sub && <span className="dim" style={{ fontSize: 11 }}>{sub}</span>}
    </div>
  )
}

function onOff(v) {
  if (v === true) return <span className="run-ok">● on</span>
  if (v === false) return <Badge tone="fail">off</Badge>
  return 'not set'
}

/** Requests a run used against the contract's caps, per platform. Watch
 *  requests are capped apart, so a platform's cap here is the keyword agent's. */
function Requests({ used, caps }) {
  const keys = Object.keys(used || {}).filter((k) => used[k])
  if (!keys.length) return <span className="dim">none</span>
  return keys.map((k) => (
    <span key={k} className="iai-adm-req">
      {PLATFORM[k] || k} <span className="tnum">{n(used[k])}</span>
      {caps?.[k] != null && <span className="dim tnum"> / {caps[k]}</span>}
    </span>
  ))
}

export default function IndustryAiAdminPanel() {
  const [state, setState] = useState({ data: null, err: null })
  const [sched, setSched] = useState(null)
  useEffect(() => {
    let alive = true
    adminIndustryAi()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    adminSchedules().then((d) => alive && setSched(d)).catch(() => alive && setSched({ feeds: [] }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const feed = sched?.feeds?.find((f) => f.key === 'industry-ai')
  const sw = feed?.switch?.state
  const items = data?.items
  const versions = Object.entries(data?.versions || {})
  const behind = versions.filter(([v]) => v !== data?.rules_version).reduce((s, [, c]) => s + c, 0)
  const r = data?.retention || {}

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconGrid width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">AI in industries — the stored data</span>
        </div>
        <span className="label">read-only</span>
      </div>
      <div className="card-intro">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          What the Industry AI agent and its observer have stored, and whether it needs a hand: labels made with
          older rules than the contract&apos;s, posts saved but not labelled, the last runs against their request
          caps, and text retention. The page itself is signed in; when the run is scheduled is under Scheduler.
        </p>
      </div>
      <div className="card-body stack stack-4">
        {err && <Notice icon={<IconAlert />}>This could not be read: {err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 160 }} />}
        {data?.unreadable && <Notice icon={<IconAlert />}>{data.unreadable}</Notice>}

        {data && (
          <div className="adm-plan-grid">
            <Cell k="Harvest (contract)" v={onOff(data.harvest_enabled)} sub="run.enabled: refuses every harvest when off" />
            <Cell k="Observer (contract)" v={onOff(data.watch_enabled)} sub="watch.enabled: a hand-started run can still add it" />
            <Cell k="Scheduled runs"
                  v={sw === 'on' ? onOff(true) : sw === 'off' ? onOff(false) : 'can’t be read here'}
                  sub={feed?.next_run ? `next due ${when(feed.next_run)}` : null} />
          </div>
        )}

        {items && (
          <>
            <div className="adm-plan-grid iai-adm-four">
              <Cell k="Posts stored" v={n(items.stored)} sub={`${n(items.kept)} kept`} />
              <Cell k="Rules version" v={<span className="mono">{data.rules_version || '–'}</span>}
                    sub={behind ? `${n(behind)} stored post(s) labelled with older rules` : 'every stored label is on it'} />
              <Cell k="Saved, not labelled" v={n(items.pending)}
                    sub={items.pending ? 'a labelling failed; the next run or --relabel labels them' : 'none waiting'} />
              <Cell k="Text cleared" v={n(items.text_cleared)}
                    sub={items.text_due == null ? 'retention not set'
                      : `${n(items.text_due)} due at the next run (after ${r.clear_text_after_days} days)`} />
            </div>
            {behind > 0 && (
              <Notice icon={<IconAlert />}>
                {n(behind)} stored post(s) carry labels from older rules than the contract&apos;s{' '}
                <span className="mono">{data.rules_version}</span>, so the page counts them by the old rules.
                A <code>--relabel</code> run (no requests) brings them up to date.
              </Notice>
            )}
            {versions.length > 0 && (
              <span className="dim" style={{ fontSize: 11 }}>
                Stored labels, by the rules that made them — {versions.map(([v, c]) => `${v} ${n(c)}`).join(' · ')}
              </span>
            )}

            <div className="stack stack-1">
              <span className="label">The last runs</span>
              <div className="tablewrap"><table>
                <thead><tr><th>Started</th><th>Run</th><th>Result</th><th>Keyword agent: used / cap</th><th>Observer: used / cap</th><th>Rules</th><th>Detail</th></tr></thead>
                <tbody>
                  {data.runs.length === 0 ? (
                    <tr><td colSpan={7} className="dim">No run recorded yet.</td></tr>
                  ) : data.runs.map((run) => (
                    <tr key={run.started_at}>
                      <td>{when(run.started_at)}</td>
                      <td className="dim">{run.mode}</td>
                      <td>{run.status === 'ok' ? <span className="run-ok">✓ ok</span>
                        : <Badge tone={run.status === 'running' ? 'info' : 'fail'}>{run.status}</Badge>}</td>
                      {/* EACH AGENT AGAINST ITS OWN CAP (#668 review, point 6, rule 7):
                          the run's total per platform is split by the observer's own
                          queries, so neither figure is set against the other's cap. */}
                      <td><Requests used={run.requests_keyword} caps={data.caps} /></td>
                      <td><Requests used={run.requests_watch} caps={data.watch_caps} /></td>
                      <td className="mono" style={{ whiteSpace: 'nowrap' }}>{run.rules_version}</td>
                      <td className="dim" style={{ fontSize: 11 }}>{run.detail || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
              <span className="dim" style={{ fontSize: 11 }}>
                Each agent&apos;s requests are shown against its own cap: the observer&apos;s are its own
                queries, the keyword agent&apos;s the rest of what the run spent. Reddit and X are metered.
              </span>
            </div>
          </>
        )}

        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <Link className="btn btn-ghost" to="/ai-in-industries">AI in industries →</Link>
          <Link className="btn btn-ghost" to="/ai-in-industries?view=info">Info: keywords and rules →</Link>
        </div>
      </div>
    </section>
  )
}
