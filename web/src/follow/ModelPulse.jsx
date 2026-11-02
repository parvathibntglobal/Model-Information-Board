import { useEffect, useState } from 'react'
import { watchModels } from '../api'
import { lastLook, markLook } from './follow'

/**
 * ONE MODEL'S PULSE, on its page (2026-11-02, prototype): the two things no
 * other page shows - what is NEW since this browser last looked, and reports
 * per week over the last weeks by the post's own date, the launch week marked
 * (judge/watch.py). Prices, retirement and the reports themselves stay where
 * they already are: the price card, Lifecycle, the voices and the feed.
 *
 * Counts only (rule 3). A busy problem week is shown, never flagged: the
 * busiest weeks are launch weeks, and counts follow how often we collect.
 */

const fmtShort = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }) : '')

function Trend({ m }) {
  const max = Math.max(1, ...m.trend.map((w) => w.negative + w.positive + w.neutral))
  const released = m.release_date ? m.release_date.slice(0, 10) : null
  const last = m.trend.length - 1
  return (
    <figure className="pl-trend">
      <div className="pl-bars" role="img"
           aria-label={`Reports per week: ${m.trend.map((w) => `${fmtShort(w.week)} ${w.negative} problem of ${w.negative + w.positive + w.neutral}`).join('; ')}`}>
        {m.trend.map((w, i) => {
          const all = w.negative + w.positive + w.neutral
          const end = new Date(new Date(w.week).getTime() + 7 * 86400000).toISOString().slice(0, 10)
          const launch = released && released >= w.week && released < end
          return (
            <div key={w.week} className="pl-bar"
                 title={`Week of ${fmtShort(w.week)}${i === last ? ' (so far)' : ''}: ${w.negative} problem, ${all} in all`}>
              <span className="pl-bar-n">{all || ''}</span>
              <div className="pl-bar-col">
                <span className="pl-bar-rest" style={{ height: `${((all - w.negative) / max) * 100}%` }} />
                <span className="pl-bar-neg" style={{ height: `${(w.negative / max) * 100}%` }} />
              </div>
              <span className="pl-bar-lab">{launch ? 'launch' : i === last ? 'now' : fmtShort(w.week)}</span>
            </div>
          )
        })}
      </div>
      <figcaption>
        Reports per week by the post&apos;s own date: <span className="pl-key-neg">problems</span> and{' '}
        <span className="pl-key-rest">everything else</span>, each post counted once. Counts follow how often we
        collect, and a launch week is usually the busiest.
      </figcaption>
    </figure>
  )
}

export default function ModelPulse({ id }) {
  const [since] = useState(() => lastLook(id))
  const [m, setM] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    watchModels([id], since)
      .then((d) => alive && setM(d.models?.[0] || false))  // false: not in the registry
      .catch(() => alive && setFailed(true))
    return () => { alive = false }
  }, [id, since])

  useEffect(() => {
    if (!m) return undefined
    const t = setTimeout(() => markLook(id), 4000)
    return () => clearTimeout(t)
  }, [m, id])

  if (failed || m === false) return null
  if (!m) return <section className="card pl"><div className="skel" style={{ height: 150 }} /></section>
  const ns = m.new_since
  const all = m.reports.positive + m.reports.negative + m.reports.neutral
  return (
    <section className="card stack stack-2 pl" aria-label="What is new on this model">
      <h2 className="mp2-h">What&apos;s new</h2>
      <p className="pl-since">
        {ns
          ? <>Since you last looked ({fmtShort(since)}): <b className="pl-neg">{ns.negative}</b> new problem {ns.negative === 1 ? 'report' : 'reports'}, <b>{ns.positive}</b> working, <b>{ns.neutral}</b> neutral.</>
          : <>In the last 30 days: <b className="pl-neg">{m.reports.negative}</b> problem {m.reports.negative === 1 ? 'report' : 'reports'}, <b>{m.reports.positive}</b> working, <b>{m.reports.neutral}</b> neutral{all ? '' : ' - nobody has reported on it in that time'}. Next time you open this page, it shows what is new since now.</>}
      </p>
      <Trend m={m} />
    </section>
  )
}
