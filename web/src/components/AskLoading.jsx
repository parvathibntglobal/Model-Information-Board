import { useEffect, useRef, useState } from 'react'
import LiquidBar from './LiquidBar'

/**
 * The loading state for /ask.
 *
 * Composition follows the Aerith fluid-engine reference — centred, an
 * instrument readout, and a liquid-filled vessel as the progress bar. Palette
 * is ours: monochrome on near-black rather than emerald.
 *
 * Progress is honest about what it knows. It eases asymptotically toward 92%
 * while the request is still open, never claiming to be finished, then races to
 * 100% the moment the answer lands. A short hold gives completion a beat before
 * the results replace it.
 */

const STAGES = [
  { at: 0.00, label: 'Reading your task' },
  { at: 0.20, label: 'Splitting into roles' },
  { at: 0.44, label: 'Matching cells to conditions' },
  { at: 0.68, label: 'Pricing your workload' },
  { at: 0.86, label: 'Ranking by cost' },
]

/**
 * The backend answers `/ask/requirements` in tens of milliseconds, so
 * `complete` usually arrives while the vessel is barely wet. Racing from 2% to
 * 100% is a flicker, not an animation — so the fill is given MIN_FILL seconds
 * to build before the completion signal is allowed to act. A slow backend just
 * waits longer; the floor only ever affects the fast case.
 */
const MIN_FILL = 0.75

export default function AskLoading({ complete = false, onFinish }) {
  const [p, setP] = useState(0)
  const [fade, setFade] = useState(0)
  const done = useRef(false)
  const finish = useRef(onFinish)
  finish.current = onFinish

  useEffect(() => {
    let raf = 0
    let last = performance.now()
    let held = 0
    let value = 0
    let f = 0

    const startedAt = performance.now()

    function tick(now) {
      raf = requestAnimationFrame(tick)
      const dt = Math.min((now - last) / 1000, 1 / 30)
      last = now
      // Wall clock, not accumulated dt. dt is clamped to 1/30 so a throttled
      // tab (or a headless renderer) would take tens of real seconds to reach
      // the floor — the gate is about elapsed time, so it must read elapsed time.
      const age = (now - startedAt) / 1000

      f = Math.min(1, f + dt * 2.6)
      setFade(f)

      if (!complete || age < MIN_FILL) {
        value += (0.92 - value) * 0.85 * dt   // creeps, never arrives
      } else {
        value += (1.002 - value) * 6.0 * dt
        if (value > 0.995) {
          value = 1
          held += dt
          if (held > 0.30 && !done.current) {
            done.current = true
            finish.current?.()
          }
        }
      }
      setP(value)
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [complete])

  const pct = Math.min(100, Math.round(p * 100))
  const finished = p > 0.999
  // Everything on screen reads off `p` alone, so the number and the words can
  // never disagree the way they would if this keyed off `complete`.
  const stage = STAGES.reduce((acc, s) => (p >= s.at ? s : acc), STAGES[0])

  return (
    <section className="loader" aria-live="polite" aria-busy={!complete}>
      <div className="loader-in">
        <span className="loader-eyebrow">
          <span className="loader-dot" aria-hidden="true" /> Evidence engine
        </span>

        <h2 className="loader-title">Reading the evidence</h2>

        <p className="loader-copy">
          Matching your task against published cells. Counting independent
          voices, checking conditions, pricing your workload — only what
          cleared the gate can be recommended.
        </p>

        <div className="loader-row">
          <span className="loader-pct tnum">{pct}<i>%</i></span>
          <span className="loader-stage label">
            {finished ? 'Complete' : stage.label}
          </span>
        </div>

        <div className="lbar">
          <LiquidBar progress={p} fade={fade} />
          <span className="lbar-ticks" aria-hidden="true" />
        </div>

        <span className="loader-read label">
          <span className="loader-glyph" aria-hidden="true" />
          Cells read · <span className="tnum">{(p * 18).toFixed(1)}</span> / 18.0k
        </span>
      </div>
    </section>
  )
}
