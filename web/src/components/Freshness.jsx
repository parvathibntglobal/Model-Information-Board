import { useEffect, useState } from 'react'
import { freshness } from '../api'

/**
 * How fresh this page's evidence is - two dates, never merged into one:
 *
 *   Updated               when the newest entry shown here was ADDED
 *   newest report written when the newest source post behind it was WRITTEN
 *
 * A page updated today from posts written months ago is fresh in one sense and
 * not the other, so both are said. Read from `GET /freshness`, over exactly the
 * entries the board shows (declined ones out; withheld sources out on a public
 * view).
 *
 * `modelIds` narrows it to those models (a model page, a comparison); without
 * it the dates are the whole board's. A model with no entries says so in words
 * rather than showing an empty date (rule 4). If the dates cannot be read the
 * line is simply not rendered - a missing freshness line is better than a
 * wrong one.
 */

const fmt = (iso) => (iso
  ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  : null)

const latest = (values) => values.filter(Boolean).sort().at(-1) || null

export default function Freshness({ modelIds = null, style }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    let alive = true
    freshness().then((d) => alive && setData(d)).catch(() => {})
    return () => { alive = false }
  }, [])

  if (!data) return null

  let updated = data.updated_at
  let newest = data.newest_report_at
  if (modelIds) {
    const rows = modelIds.map((id) => data.models?.[id]).filter(Boolean)
    if (!rows.length) {
      return (
        <p className="freshness dim" style={style}>
          No reports on the board for {modelIds.length === 1 ? 'this model' : 'these models'} yet.
        </p>
      )
    }
    updated = latest(rows.map((r) => r.updated_at))
    newest = latest(rows.map((r) => r.newest_report_at))
  }
  if (!updated) return null

  return (
    <p className="freshness dim" style={style}>
      Updated <time dateTime={updated}>{fmt(updated)}</time>
      {newest && (
        <> · newest report written <time dateTime={newest}>{fmt(newest)}</time></>
      )}
    </p>
  )
}
