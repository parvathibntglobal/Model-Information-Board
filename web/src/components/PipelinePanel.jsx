import { useEffect, useState } from 'react'
import { pipelineStatus, BoardUnreadable } from '../api'
import { Badge, Notice, Unreadable } from './ui'
import { IconAlert, IconLayers } from './Icons'

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

// job_run.outcome → badge tone. 'refused' is a deliberate decline (a gate, a
// missing input), NOT an error — it must not render red (schema comment).
const OUTCOME_TONE = { ok: 'pass', refused: 'warn', error: 'fail' }

const when = (ts) => (ts ? ts.replace('T', ' ').slice(0, 16) : '—')

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

  return (
    <section className="card card-flush">
      <div className="card-head">
        <span className="eyebrow">
          <IconLayers width={14} height={14} /> Evidence pipeline — stage by stage
        </span>
        {data?.pipeline_version && <span className="label">{data.pipeline_version}</span>}
      </div>
      <div className="card-body stack stack-3">
        {unreadable && <Unreadable detail={unreadable} compact />}
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && !unreadable && <div className="skel" style={{ height: 200 }} />}

        {data && (
          <>
            <p className="muted" style={{ margin: 0 }}>{data.summary}</p>

            <div className="stack stack-3">
              {data.stages.map((s) => <Stage key={s.id} s={s} />)}
            </div>

            {/* THE DISCARDS THIS PANEL CANNOT COUNT, said once rather than
                faked as a zero on every affected stage. */}
            {data.caveats?.map((c, i) => (
              <p key={i} className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{c}</p>
            ))}

            <RunLedger runs={data.runs} measured={data.runs_measured} />
          </>
        )}
      </div>
    </section>
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

function RunLedger({ runs, measured }) {
  // Two different silences, kept apart. Unreadable = the ledger table is not on
  // this database; empty = it is there and nothing has run. Neither is allowed
  // to vanish into a missing section (rule 4).
  if (!measured) {
    return (
      <div className="stack stack-1">
        <span className="label">Last run per stage</span>
        <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
          The <code>job_run</code> ledger could not be read on this database — the run
          history is unavailable, which is not the same as no runs.
        </span>
      </div>
    )
  }
  if (!runs.length) {
    return (
      <div className="stack stack-1">
        <span className="label">Last run per stage</span>
        <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
          No pass recorded yet — <code>job_run</code> is empty. The pipeline has run
          nothing on this database, which is different from a pass that did nothing.
        </span>
      </div>
    )
  }
  return (
    <div className="stack stack-2">
      <span className="label">Last run per stage — job_run ledger</span>
      {runs.map((r) => {
        const io = [
          r.items_in != null ? `${r.items_in} in` : null,
          r.items_out != null ? `${r.items_out} out` : null,
        ].filter(Boolean).join(' → ')
        return (
          <div key={r.stage} className="row-between" style={{ gap: 10, flexWrap: 'wrap' }}>
            <div className="row" style={{ gap: 8 }}>
              <strong style={{ fontSize: 'var(--fs-xs)' }}>{r.stage}</strong>
              {r.running
                ? <Badge tone="mute">not finished</Badge>
                : <Badge tone={OUTCOME_TONE[r.outcome] || 'mute'}>{r.outcome || 'unknown'}</Badge>}
            </div>
            <span className="dim" style={{ fontSize: 11 }}>
              {io && <>{io} · </>}
              {when(r.started_at)}
              {r.finished_at && !r.running ? ` → ${when(r.finished_at)}` : ''}
            </span>
          </div>
        )
      })}
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        “not finished” is a stage still running or killed, never a reported failure — a
        crash and a refusal are opposite repairs, so they are not both shown as red.
      </span>
    </div>
  )
}
