/**
 * THE LANDING'S REPORT FIGURES, READ LIVE FROM `/reports` (2026-11-11).
 *
 * WHY. The picker preview (ToolsShowcase.jsx) and the "Examples from Reports"
 * panel (ReportExamples.jsx) showed counts fixed from the 2026-10-15 database,
 * labelled "as of 12 Oct" with no year. A month on, they no longer matched the
 * Reports page a click away. Both now pick from the same `/reports` payload
 * that page reads, by the rules the fixed figures were chosen by, and name the
 * newest report date instead of a hard-coded one.
 *
 * Plain ESM, no JSX: tests load it in node (tests/js/page_dates.mjs).
 */

/** The display name without its vendor prefix: "OpenAI: GPT-6 Astra" -> "GPT-6 Astra". */
export function shortLabel(m) {
  const l = m.label || m.key || ''
  return l.includes(':') ? l.split(':').slice(1).join(':').trim() : l
}

/** The vendor as the label or the canonical id names it. */
export function providerLabel(m) {
  const l = m.label || ''
  if (l.includes(':')) return l.split(':')[0].trim()
  return m.canonical && m.canonical.includes('/') ? m.canonical.split('/')[0] : ''
}

/** The Reports rule over a split - never a score. Same as Reports' own. */
export function verdict(s) {
  const p = s.positive || 0
  const n = s.negative || 0
  if (!p && !n) return { t: 'No side taken', c: 'neutral' }
  if (!n) return { t: 'Reported working', c: 'working' }
  if (!p) return { t: 'Problems reported, none working', c: 'problems' }
  if (p >= 3 * n) return { t: 'Mostly working', c: 'working' }
  if (n >= 3 * p) return { t: 'Mostly problems', c: 'problems' }
  return { t: 'Mixed reports', c: 'mixed' }
}

const byPeople = (a, b) => (b.voices || 0) - (a.voices || 0) || (b.reports || 0) - (a.reports || 0)

/**
 * The `n` models with the most people on one job, as the picker's results:
 * `{name, by, people, pos, neg}`. A model with no positive or negative report
 * is skipped - its ring would have nothing to draw. [] when the job is absent.
 */
export function topForJob(view, jobName, n = 3) {
  const want = String(jobName).toLowerCase()
  const axis = (view?.axes || []).find((a) => a.kind === 'job' && String(a.name).toLowerCase() === want)
  if (!axis) return []
  return [...axis.models]
    .filter((m) => (m.split?.positive || 0) + (m.split?.negative || 0) > 0)
    .sort(byPeople)
    .slice(0, n)
    .map((m) => ({
      name: shortLabel(m),
      by: providerLabel(m),
      people: m.voices,
      pos: m.split.positive,
      neg: m.split.negative,
    }))
}

const WANTED = [['Working', 'working'], ['Disputed', 'mixed'], ['Problems', 'problems']]

/**
 * One working, one disputed and one problems example across every job and
 * capability, each the case with the most people, preferring cases with all
 * three bars (the fixed examples were picked so). Metrics are left out: their
 * reports are figures, not working / not working. A model is used once.
 * Fewer than three when the data has no case of a kind.
 */
export function examplesFrom(view) {
  const cases = []
  for (const a of view?.axes || []) {
    if (a.kind === 'metric') continue
    for (const m of a.models || []) {
      const s = m.split || {}
      cases.push({
        axis: a.name, model: shortLabel(m), people: m.voices, reports: m.reports,
        split: { positive: s.positive || 0, negative: s.negative || 0, neutral: s.neutral || 0 },
        v: verdict(s),
        full: (s.positive || 0) > 0 && (s.negative || 0) > 0 && (s.neutral || 0) > 0,
        voices: m.voices, key: m.key,
      })
    }
  }
  const used = new Set()
  const out = []
  for (const [label, c] of WANTED) {
    const pool = cases.filter((x) => x.v.c === c && !used.has(x.key))
    const pick = [...pool].sort((x, y) => (y.full - x.full) || byPeople(x, y))[0]
    if (!pick) continue
    used.add(pick.key)
    out.push({ label, axis: pick.axis, model: pick.model, people: pick.people,
               reports: pick.reports, split: pick.split, v: pick.v })
  }
  return out
}
