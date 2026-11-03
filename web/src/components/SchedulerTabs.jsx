import { useSearchParams } from 'react-router-dom'
import SchedulerPanel from './SchedulerPanel'
import FeedSchedulesPanel from './FeedSchedulesPanel'

/**
 * Admin -> Scheduler, one tab per scheduled job (Parvathi, 2026-11-02):
 *
 *   Model fetches     the nightly per-model fetches (SchedulerPanel, as before)
 *   Benchmarks        benchmarks.yml: AI benchmarks' own run and switch
 *   AI updates feeds  registry-poll.yml: new models and prices for AI updates
 *
 * The open tab is in the address (`?s=scheduler&job=benchmarks`), so a link
 * can open one directly; an unknown or absent `job` opens the first.
 */
const TABS = [
  ['fetches', 'Model fetches'],
  ['benchmarks', 'Benchmarks'],
  ['registry-poll', 'AI updates feeds'],
]

export default function SchedulerTabs() {
  const [params, setParams] = useSearchParams()
  const asked = params.get('job')
  const tab = TABS.some(([k]) => k === asked) ? asked : TABS[0][0]

  const open = (key) => {
    const next = new URLSearchParams(params)
    if (key === TABS[0][0]) next.delete('job')
    else next.set('job', key)
    setParams(next, { replace: true })
  }

  return (
    <div className="stack stack-4">
      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }} role="tablist" aria-label="Scheduled jobs">
        {TABS.map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key}
                  className={`chip${tab === key ? ' chip-on' : ''}`} onClick={() => open(key)}>
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === 'fetches' ? <SchedulerPanel /> : <FeedSchedulesPanel only={tab} />}
      </div>
    </div>
  )
}
