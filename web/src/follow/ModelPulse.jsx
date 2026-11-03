import { useEffect, useState } from 'react'
import { launchVerdictWeek, watchModels } from '../api'
import { lastLook, markLook } from './follow'
import { Period } from './LaunchVerdict'

/**
 * ONE MODEL'S PULSE, on its page (2026-11-02, prototype): the two things no
 * other page shows - what is NEW since this browser last looked, and reports
 * per week over the last weeks by the post's own date, the launch week marked
 * (judge/watch.py). Prices, retirement and the reports themselves stay where
 * they already are: the price card, Lifecycle, the voices and the feed.
 *
 * EACH WEEK SHOWS ITS THREE SIDES and opens (2026-11-03 review: "not very
 * interactive, does not show how many positive or negative"): working,
 * problems and neutral are separate parts of the bar with their counts, and a
 * click on a week shows that week's people, topics and quotes
 * (judge/verdict.py, /verdict/week).
 *
 * Counts only (rule 3). A busy problem week is shown, never flagged: the
 * busiest weeks are launch weeks, and counts follow how often we collect.
 */

const fmtShort = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }) : '')

function WeekDetail({ id, week }) {
  const [w, setW] = useState(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let alive = true
    setW(null)
    setFailed(false)
    launchVerdictWeek(id, week)
      .then((d) => alive && setW(d))
      .catch(() => alive && setFailed(true))
    return () => { alive = false }
  }, [id, week])
  if (failed) return <p className="lv-none">That week could not be read.</p>
  if (!w) return <div className="skel" style={{ height: 120 }} />
  return (
    <div className="pl-week">
      <header className="lv-win-h">
        <h3>Week of {fmtShort(w.from)}</h3>
        <span>{fmtShort(w.from)} – {fmtShort(w.to)}{w.state === 'open' ? ' · so far' : ''}</span>
      </header>
      <Period w={w} modelId={id} />
    </div>
  )
}

function Trend({ id, m }) {
  const [open, setOpen] = useState(null)
  const total = (w) => w.negative + w.positive + w.neutral
  const max = Math.max(1, ...m.trend.map(total))
  const released = m.release_date ? m.release_date.slice(0, 10) : null
  const last = m.trend.length - 1
  const sums = m.trend.reduce((a, w) => ({ positive: a.positive + w.positive, negative: a.negative + w.negative,
    neutral: a.neutral + w.neutral }), { positive: 0, negative: 0, neutral: 0 })
  return (
    <figure className="pl-trend">
      <p className="pl-key">
        Over these {m.trend.length} weeks: <span className="pl-key-pos">{sums.positive} working</span>
        <span className="pl-key-neg">{sums.negative} problems</span>
        <span className="pl-key-rest">{sums.neutral} neutral</span>
      </p>
      <div className="pl-bars" role="group" aria-label="Reports per week; choose a week to see what was reported">
        {m.trend.map((w, i) => {
          const all = total(w)
          const end = new Date(new Date(w.week).getTime() + 7 * 86400000).toISOString().slice(0, 10)
          const launch = released && released >= w.week && released < end
          const on = open === w.week
          const h = (k) => `${(w[k] / max) * 100}%`
          return (
            <button key={w.week} type="button" className={`pl-bar${on ? ' pl-on' : ''}`} aria-pressed={on}
                    disabled={!all} onClick={() => setOpen(on ? null : w.week)}
                    title={`Week of ${fmtShort(w.week)}${i === last ? ' (so far)' : ''}: ${w.positive} working, ${w.negative} problems, ${w.neutral} neutral`}>
              <span className="pl-bar-n">{all || ''}</span>
              <span className="pl-bar-col">
                <span className="pl-bar-rest" style={{ height: h('neutral') }} />
                <span className="pl-bar-pos" style={{ height: h('positive') }} />
                <span className="pl-bar-neg" style={{ height: h('negative') }} />
              </span>
              <span className="pl-bar-lab">{launch ? 'launch' : i === last ? 'now' : fmtShort(w.week)}</span>
            </button>
          )
        })}
      </div>
      <figcaption>
        Reports per week by the post&apos;s own date: <span className="pl-key-pos">working</span>,{' '}
        <span className="pl-key-neg">problems</span> and <span className="pl-key-rest">neutral</span>, each post
        counted once per side. Counts follow how often we collect, and a launch week is usually the busiest.
        {!open && ' Choose a week to see who reported what.'}
      </figcaption>
      {open && <WeekDetail id={id} week={open} />}
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
  if (!m) return <section className="card"><div className="skel" style={{ height: 150 }} /></section>
  const ns = m.new_since
  const all = m.reports.positive + m.reports.negative + m.reports.neutral
  return (
    <section className="card stack stack-2" aria-label="What is new on this model">
      <h2 className="mp2-h">What&apos;s new</h2>
      <p className="pl-since">
        {ns
          ? <>Since you last looked ({fmtShort(since)}): <b className="pl-neg">{ns.negative}</b> new problem {ns.negative === 1 ? 'report' : 'reports'}, <b className="pl-pos">{ns.positive}</b> working, <b>{ns.neutral}</b> neutral.</>
          : <>In the last 30 days: <b className="pl-neg">{m.reports.negative}</b> problem {m.reports.negative === 1 ? 'report' : 'reports'}, <b className="pl-pos">{m.reports.positive}</b> working, <b>{m.reports.neutral}</b> neutral{all ? '' : ' - nobody has reported on it in that time'}. Next time you open this page, it shows what is new since now.</>}
      </p>
      <Trend id={id} m={m} />
    </section>
  )
}
