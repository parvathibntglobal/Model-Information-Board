import { useEffect, useState } from 'react'
import { useInView } from './ui'
import { reportsPage } from '../api'
import { examplesFrom } from './reportPicks'
import { fmtDayUtc } from '../dates'

/**
 * THREE EXAMPLES FROM REPORTS (2026-10-15), for the landing's "LLM
 * leaderboard alternative" section: one model reported working, one disputed,
 * one with problems, each with a small positive / negative / neutral chart.
 *
 * READ LIVE (2026-11-11). They were real counts FIXED from the 2026-10-15
 * database, captioned with that fixed date, and a month later no longer matched the
 * Reports page a click away. They are now picked from the same `/reports`
 * payload by the same rule (components/reportPicks.js `examplesFrom`): the
 * case with the most people of each kind, preferring cases with all three
 * bars, and the caption names the newest report's date. Nothing is drawn
 * until the counts are read; if they cannot be read the panel is left out.
 */

function CountCard({ ex }) {
  const s = ex.split
  const max = Math.max(1, s.positive, s.negative, s.neutral)
  const bars = [['pos', 'positive', s.positive], ['neg', 'negative', s.negative], ['neu', 'neutral', s.neutral]]
  return (
    <div className="hc" data-verdict={ex.v.c}>
      <div className="hc-text">
        <span className="hc-ax">{ex.label} · <mark className="hc-axis">{ex.axis}</mark></span>
        <b className="hc-mn">{ex.model}</b>
        <span className="hc-ph">{ex.v.t}</span>
        <span className="hc-n">{ex.people} people · {ex.reports} reports</span>
      </div>
      <div className="hc-chart" role="img" aria-label={`${s.positive} positive, ${s.negative} negative, ${s.neutral} neutral reports`}>
        {bars.map(([c, word, v]) => (
          <span key={c} className={`hc-col hc-${v ? c : 'zero'}`}>
            <span className="hc-v">{v}</span>
            {/* the bar's own track, so its height is a share of the chart alone,
                not of the column that also holds the number and the label */}
            <span className="hc-bt"><span className="hc-b" style={{ height: v ? `${Math.max(6, (100 * v) / max)}%` : '2px' }} /></span>
            <span className="hc-l">{word}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

const SLIDE_MS = 3200

/**
 * ONE EXAMPLE AT A TIME, in the box the quoted entry used to fill: the three
 * slide in turn every three seconds, and each card's bars grow from the
 * baseline as it arrives, while on screen; the dots jump to an
 * example. With reduced motion the slides change without sliding and the bars
 * are drawn at full height (styles in app.css, `prefers-reduced-motion`).
 */
export default function ReportExamples() {
  const [view, setView] = useState(null)
  useEffect(() => {
    let alive = true
    reportsPage().then((d) => alive && setView(d)).catch(() => alive && setView({}))
    return () => { alive = false }
  }, [])
  const examples = view ? examplesFrom(view) : []
  const n = examples.length
  const [at, setAt] = useState(0)
  // it slides only while on screen (components/ui.jsx: useInView)
  const [el, setEl] = useState(null)
  const inView = useInView(el)
  useEffect(() => {
    if (!inView) return undefined
    if (!n) return undefined
    const t = setInterval(() => setAt((i) => (i + 1) % n), SLIDE_MS)
    return () => clearInterval(t)
  }, [n, inView])
  if (!n) return null
  const asOf = fmtDayUtc(view?.newest_report)
  return (
    <figure className="hc-set" ref={setEl}>
      <figcaption className="entry-cap">Examples from Reports{asOf ? ` · newest report ${asOf}` : ''}</figcaption>
      <div className="hc-stage" aria-live="polite">
        <div className="hc-track" style={{ transform: `translateX(-${at * 100}%)` }}>
          {examples.map((ex, i) => (
            <div key={ex.label} className={`hc-slide${i === at ? ' hc-on' : ''}`} aria-hidden={i !== at}>
              {/* the key restarts the bars' growth each time a card arrives */}
              <CountCard key={i === at ? `on${at}` : 'off'} ex={ex} />
            </div>
          ))}
        </div>
      </div>
      <div className="hc-foot">
        <span className="hc-cap">One working, one disputed, one with problems.</span>
        <span className="hc-dots" role="tablist" aria-label="Choose an example">
          {examples.map((ex, i) => (
            <button key={ex.label} type="button" role="tab" aria-selected={i === at} aria-label={`${ex.label}: ${ex.model}`}
                    className={`hc-dot hc-dot-${ex.v.c}${i === at ? ' hc-dot-on' : ''}`} onClick={() => setAt(i)} />
          ))}
        </span>
      </div>
    </figure>
  )
}
