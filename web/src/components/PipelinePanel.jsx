import { useEffect, useState } from 'react'
import { pipelineStatus, BoardUnreadable } from '../api'
import { Badge, Notice, Unreadable } from './ui'
import { IconAlert } from './Icons'

/**
 * The evidence pipeline, stage by stage. COUNTS, not money — the sibling of
 * UsagePanel on the same admin page.
 *
 * Two halves, both read straight off the backend:
 *  - the funnel: per stage, rows grouped by the status column that partitions
 *    it, as a stacked bar plus the counts. Every bar carries its denominator
 *    (rule 7); a stage with no rows says "not run yet", never a green zero
 *    (rule 4).
 *  - the run ledger: job_run's last row per stage — when, whether it finished,
 *    and its outcome. "not finished" is running-or-killed, kept distinct from a
 *    reported failure (rule 6), because the two are different repairs.
 *
 * No poll: the pipeline moves once a night, so this reads once on mount rather
 * than every 15s like the spend meter.
 */

// Bar/segment colours by tone. Fallbacks so the bar renders even before the
// theme vars load — a colourless bar would read as one undivided bucket.
const TONE = {
  pass: 'var(--pass)',
  warn: 'var(--warn, #d08770)',
  fail: 'var(--fail)',
  mute: 'var(--surface-3))',
}


export default function PipelinePanel() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  useEffect(() => {
    let alive = true
    pipelineStatus()
      .then((d) => {
        if (!alive) return
        setData(d)
        setErr(null)
        setUnreadable(null)
      })
      .catch((e) => {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message)
      })
    return () => {
      alive = false
    }
  }, [])

  // ⚠ E1-E7 ONLY, AND THE TWO THAT GO ARE NOT COUNTS OF A FETCH.
  //   E8 (`cell -> label_change`) has never run, so its row said "not run yet"
  //   in a list where every other row is a number. E9 (`last_swept_at`) counts
  //   how stale the REGISTRY is - a real fact, and not a stage a fetch passes
  //   through, so it read as an eighth step that does not exist.
  //
  //   They are still in the payload. Removed from this view, not from the
  //   endpoint, because "never run" is a fact somebody may want to surface
  //   deliberately rather than beside seven throughput numbers.
  const stages = (data?.stages || []).filter((s) => !['E8', 'E9'].includes(s.id))

  return (
    <div className="stack stack-3">
      {unreadable && <Unreadable detail={unreadable} compact />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!data && !err && !unreadable && <div className="skel" style={{ height: 160 }} />}

      {data && (
        <>
          <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
            <span className="label">How many rows are sitting at each stage</span>
            {data.pipeline_version && (
              <span className="dim mono" style={{ fontSize: 11 }}>{data.pipeline_version}</span>
            )}
          </div>
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch',
                                      margin: 0, lineHeight: 1.6 }}>
            The same stages described above, as counts. Every figure is counted rather than
            derived, and a stage with no rows reports as not-yet-run rather than a clean zero.
          </p>

          <div className="stack stack-3">
            {stages.map((s) => <Stage key={s.id} s={s} />)}
          </div>
        </>
      )}
    </div>
  )
}

function Stage({ s }) {
  return (
    <div className="stack stack-1">
      <div className="row-between" style={{ gap: 10, flexWrap: 'wrap' }}>
        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <span className="label" style={{ opacity: 0.6 }}>{s.id}</span>
          <strong style={{ fontSize: 'var(--fs-sm)' }}>{s.name}</strong>
          <Badge tone="mute">{s.lane}</Badge>
        </div>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{s.flow}</span>
      </div>

      {s.unreadable ? (
        <Notice icon={<IconAlert />}>This stage could not be read: {s.unreadable}</Notice>
      ) : !s.measured ? (
        <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
          Not run yet — no {s.unit}. An empty stage, which is not the same as a stage that
          ran and found nothing.
        </span>
      ) : (
        <>
          <div
            style={{
              display: 'flex', height: 12, borderRadius: 6, overflow: 'hidden',
              background: 'var(--surface-3))',
            }}
            role="img"
            aria-label={`${s.total} ${s.unit}`}
          >
            {s.buckets.map((b) => (b.n > 0 ? (
              <div
                key={b.key}
                title={`${b.label}: ${b.n}`}
                style={{ width: `${(b.n / s.total) * 100}%`, background: TONE[b.tone] }}
              />
            ) : null))}
          </div>
          <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
            {s.buckets.map((b) => (
              <span key={b.key} style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-2)' }}>
                <span style={{
                  display: 'inline-block', width: 8, height: 8, borderRadius: 2,
                  background: TONE[b.tone], marginRight: 6,
                }} />
                {b.label} <span className="tnum">{b.n}</span>
              </span>
            ))}
            <span className="label" style={{ marginLeft: 'auto' }}>{s.total} {s.unit}</span>
          </div>
          {s.caveat && (
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{s.caveat}</span>
          )}
        </>
      )}
    </div>
  )
}

