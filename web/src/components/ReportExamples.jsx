import { useEffect, useState } from 'react'
import { useInView } from './ui'

/**
 * THREE EXAMPLES FROM REPORTS (2026-10-15), for the landing's "LLM
 * leaderboard alternative" section: one model reported working, one disputed,
 * one with problems, each with a small positive / negative / neutral chart.
 *
 * REAL COUNTS, FIXED AT A DATE: the three were picked from `/reports` on the
 * team's 2026-10-15 database (newest report 12 Oct) as real cases with all
 * three bars, so the chart reads at a glance; the panel names that date on its
 * face, because the live counts move on. They replaced sample figures that had
 * GPT-6 Astra "mixed" on reasoning and DeepSeek V4 Flash failing on long
 * context - neither true of the data. The verdicts follow the Reports rule
 * (`verdict` below).
 */

/** The same fixed rule over the counts the Reports pages use - never a score. */
function verdict(s) {
  const p = s.positive, n = s.negative
  if (!p && !n) return { t: 'No side taken', c: 'neutral' }
  if (!n) return { t: 'Reported working', c: 'working' }
  if (!p) return { t: 'Problems reported, none working', c: 'problems' }
  if (p >= 3 * n) return { t: 'Mostly working', c: 'working' }
  if (n >= 3 * p) return { t: 'Mostly problems', c: 'problems' }
  return { t: 'Mixed reports', c: 'mixed' }
}

const SAMPLES = [
  { label: 'Working', axis: 'Coding agents', model: 'GPT-6 Astra', people: 10, reports: 10,
    split: { positive: 8, negative: 1, neutral: 1 } },
  { label: 'Disputed', axis: 'Reasoning', model: 'Kimi K3', people: 7, reports: 7,
    split: { positive: 4, negative: 2, neutral: 1 } },
  { label: 'Problems', axis: 'Vision', model: 'DeepSeek V4 Flash', people: 9, reports: 10,
    split: { positive: 1, negative: 8, neutral: 1 } },
].map((ex) => ({ ...ex, v: verdict(ex.split) }))

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
  const examples = SAMPLES
  const n = examples.length
  const [at, setAt] = useState(0)
  // it slides only while on screen (components/ui.jsx: useInView)
  const [el, setEl] = useState(null)
  const inView = useInView(el)
  useEffect(() => {
    if (!inView) return undefined
    const t = setInterval(() => setAt((i) => (i + 1) % n), SLIDE_MS)
    return () => clearInterval(t)
  }, [n, inView])
  return (
    <figure className="hc-set" ref={setEl}>
      <figcaption className="entry-cap">Examples from Reports · as of 12 Oct</figcaption>
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
