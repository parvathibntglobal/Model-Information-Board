// Runs web/src/dates.js and web/src/components/reportPicks.js on fixed inputs
// and prints JSON, for tests/test_page_dates.py. No DOM, no network.
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const d = await import(pathToFileURL(resolve('web/src/dates.js')).href)
const r = await import(pathToFileURL(resolve('web/src/components/reportPicks.js')).href)

const NOW = Date.parse('2026-11-10T19:00:00Z')
const m = (key, label, voices, pos, neg, neu = 0) => ({
  key, label, canonical: null, voices, reports: voices,
  split: { positive: pos, negative: neg, neutral: neu, both: 0 },
})
const view = {
  newest_report: '2026-11-09',
  axes: [
    { kind: 'job', name: 'Coding agents', models: [
      m('a', 'Alpha: Model A', 9, 7, 1, 1),
      m('b', 'Beta: Model B', 12, 10, 1, 1),
      m('c', 'Gamma: Model C', 5, 3, 1, 1),
      m('z', 'Zeta: Model Z', 4, 0, 0, 4),     // no side taken: no ring to draw
      m('d0', 'Delta: Model D0', 2, 1, 0, 0),
    ] },
    { kind: 'capability', name: 'Reasoning', models: [
      m('d', 'Delta: Model D', 7, 4, 2, 1),
      m('b', 'Beta: Model B', 3, 1, 1, 1),
    ] },
    { kind: 'capability', name: 'Vision', models: [m('e', 'Epsilon: Model E', 9, 1, 8, 1)] },
    { kind: 'metric', name: 'Speed', models: [m('f', 'Phi: Model F', 50, 0, 40, 1)] },
  ],
}

process.stdout.write(JSON.stringify({
  late_yesterday: d.agoDays('2026-11-09T23:00:00Z', NOW),
  earlier_today: d.agoDays('2026-11-10T00:30:00Z', NOW),
  eight_days: d.agoDays('2026-11-02T12:00:00Z', NOW),
  unreadable: d.agoDays('not a date', NOW),
  utc_day: d.fmtDayUtc('2026-11-09T23:30:00Z'),
  no_day: d.fmtDayUtc(null),
  h23_30: d.agoShort('2026-11-09T19:30:00Z', NOW),
  m59: d.agoShort('2026-11-10T18:01:00Z', NOW),
  past_a_day: d.agoShort('2026-11-08T19:00:00Z', NOW),
  picks: r.topForJob(view, 'Coding agents'),
  picks_no_job: r.topForJob(view, 'Translation'),
  examples: r.examplesFrom(view),
}))
