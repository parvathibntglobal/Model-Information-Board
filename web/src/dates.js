/**
 * ONE CLOCK FOR EVERY DATE A PAGE SHOWS (2026-11-11).
 *
 * WHY. Dates on one page came from two clocks. The "Updated …" line and the
 * board's section dates were formatted in the READER'S timezone, while the
 * footer's "model list read", the benchmarks "Updated" and the news cards'
 * "Today / Yesterday" were UTC. Near midnight, the header and the footer of the
 * same page named different days. Every date here is a UTC calendar date, as
 * the data is stored.
 *
 * "TODAY" IS A CALENDAR DAY, NOT 24 HOURS. `Math.floor((now - at) / 86400000)`
 * counted rolling 24-hour windows, so a fetch at 23:00 UTC yesterday read
 * "Last checked today (2026-11-09)" on 10 Nov: the word and the date beside it
 * disagreed. `daysAgo` counts UTC calendar days between the two dates.
 *
 * Plain ESM, no JSX: tests load it in node (tests/js/page_dates.mjs).
 */

const DAY_MS = 86400000

/** Midnight UTC of the calendar day `iso` falls on, in ms; NaN when unreadable. */
export function utcDayStart(iso) {
  const t = typeof iso === 'number' ? iso : Date.parse(iso)
  if (Number.isNaN(t)) return NaN
  const d = new Date(t)
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
}

/** Whole UTC calendar days from `iso` to `now`; null when `iso` is unreadable. */
export function daysAgo(iso, now = Date.now()) {
  const then = utcDayStart(iso)
  if (Number.isNaN(then)) return null
  return Math.round((utcDayStart(now) - then) / DAY_MS)
}

/** "today", "1 day ago", "12 days ago" by UTC calendar day; null when unreadable. */
export function agoDays(iso, now = Date.now()) {
  const days = daysAgo(iso, now)
  if (days == null) return null
  return days <= 0 ? 'today' : days === 1 ? '1 day ago' : `${days} days ago`
}

/** "9 Nov 2026" in UTC, in the reader's locale; null when missing or unreadable. */
export function fmtDayUtc(iso, opts = { day: 'numeric', month: 'short', year: 'numeric' }) {
  if (!iso) return null
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  return new Date(t).toLocaleDateString(undefined, { ...opts, timeZone: 'UTC' })
}

/** "5 min ago", "23 h ago" - whole units, never rounded up to the next one. */
export function agoShort(iso, now = Date.now()) {
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  const mins = Math.floor((now - t) / 60000)
  if (mins < 60) return `${Math.max(mins, 1)} min ago`
  if (mins < 24 * 60) return `${Math.floor(mins / 60)} h ago`
  return null
}
