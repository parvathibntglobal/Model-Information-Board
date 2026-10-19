import { DAYS_PER_MONTH } from './cost'
import { PERSONAS, personaOf } from './personas'
import '../styles/personas.css'

const compact = (n) => (n >= 1e9 ? `${+(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M`
  : n >= 1e3 ? `${+(n / 1e3).toFixed(1)}K` : String(n))

/**
 * START FROM A TYPICAL WORKLOAD: one card per persona. A card shows its numbers
 * and a bar of how each call splits between input and output; choosing it
 * fills the four fields. Editing any field leaves every card unselected, and
 * the readout then says "your own numbers" - the numbers on screen are always
 * the ones being priced, whichever way they got there.
 *
 * `value` is { inTok, outTok, perDay, cached }; `onPick` receives the same shape.
 */
export default function PersonaPicker({ value, onPick }) {
  const current = personaOf(value)
  const month = value.perDay * DAYS_PER_MONTH
  return (
    <div className="ps">
      <div className="ps-head">
        <span className="eyebrow">Start from a typical workload</span>
        <span className="ps-note">Illustrative starting points, not measurements. Replace them with your own numbers.</span>
      </div>
      <div className="ps-cards" role="radiogroup" aria-label="Typical workloads">
        {PERSONAS.map((p) => {
          const share = p.inTok + p.outTok ? (p.inTok / (p.inTok + p.outTok)) * 100 : 50
          const on = current?.key === p.key
          return (
            <button key={p.key} type="button" role="radio" aria-checked={on} className={`ps-card${on ? ' on' : ''}`}
                    onClick={() => onPick({ inTok: p.inTok, outTok: p.outTok, perDay: p.perDay, cached: p.cached })}>
              <b>{p.name}</b>
              <small>{p.scene}</small>
              <span className="ps-bar" aria-hidden="true"><i style={{ width: `${share}%` }} /></span>
              <span className="ps-nums">
                <span>{compact(p.inTok)} in</span><span>{compact(p.outTok)} out</span>
                <span>{compact(p.perDay)}/day</span><span>{p.cached}% cached</span>
              </span>
            </button>
          )
        })}
      </div>
      <p className="ps-readout">
        <b>{current ? current.name : 'Your own numbers'}:</b>{' '}
        {compact(value.inTok * month)} input and {compact(value.outTok * month)} output tokens a month,
        over {compact(month)} calls ({DAYS_PER_MONTH} days of {compact(value.perDay)}).
      </p>
    </div>
  )
}
