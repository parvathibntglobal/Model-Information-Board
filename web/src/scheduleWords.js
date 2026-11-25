/**
 * SCHEDULE WORDS (2026-11-25): shared by the Updates page's "When new updates
 * arrive" card and the AI in industries Info view, so both word a schedule,
 * a last run and a next run the same way. Everything comes from GET
 * /admin/schedules (judge/sections_status.py); nothing here is a time.
 */

// ONE TIME FORMAT, the schedule's own (judge/sections_status.py cron_words):
// UTC, then IST in brackets - so "next" and "last" read like the schedule.
const fmtUtc = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
const fmtIst = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
export function when(iso) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${fmtUtc.format(d)} UTC (${fmtIst.format(d)} IST)`
}

/** The schedule in words, "daily at A and B" rather than "daily at A and daily at B". */
export function scheduleWords(crons) {
  const words = (crons || []).map((c) => c.words)
  if (!words.length) return 'no schedule'
  const head = words[0].includes(' at ') ? `${words[0].split(' at ')[0]} at ` : null
  if (head && words.every((w) => w.startsWith(head))) {
    return head + words.map((w) => w.slice(head.length)).join(' and ')
  }
  return words.join(' and ')
}
