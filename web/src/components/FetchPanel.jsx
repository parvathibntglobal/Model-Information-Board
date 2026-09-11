import { useCallback, useEffect, useState } from 'react'
import { startFetch, stopFetch, fetchLog, fetchRuns } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert } from './Icons'

// `stopped` is deliberately NOT 'fail'. A run somebody chose to abandon and a
// run that broke are different facts, and colouring them the same loses the
// distinction the end record went to the trouble of recording.
const FETCH_TONE = { ok: 'pass', running: 'mute', skipped: 'mute', error: 'fail',
                     stopped: 'warn' }

function runTone(r) {
  if (!r.done) return 'mute'
  if (r.status === 'ok') return 'pass'
  if (r.status === 'error') return 'fail'
  if (r.status === 'stopped') return 'warn'
  return 'mute'
}

// Fields carried on a stage record that are bookkeeping, not "what happened".
const SKIP_FIELDS = new Set(['kind', 'id', 'name', 'status', 'at', 'detail'])

/**
 * One row per pipeline stage, in the order the run reached them. Each stage
 * writes a `running` record and then a terminal one (ok / skipped / error);
 * we merge them so a stage shows its final status alongside everything it
 * reported (variants, requests spent, sieve kept, documents added, dropped,
 * proposed, …) rather than repeating the stage as it churns.
 */
function collapseStages(records) {
  const byId = new Map()
  for (const r of records) {
    if (r.kind !== 'stage') continue
    byId.set(r.id, { ...(byId.get(r.id) || {}), ...r })   // later fields (the terminal record) win
  }
  return [...byId.values()]
}

/** The per-stage log of one run, shared by the live view and the history. */
function StageList({ records }) {
  const stages = collapseStages(records)
  const end = records.find((r) => r.kind === 'end')
  if (stages.length === 0 && !end) {
    return <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No stages recorded.</span>
  }
  return (
    <div className="stack stack-2">
      {stages.map((s) => {
        const nums = Object.entries(s)
          .filter(([k, v]) => !SKIP_FIELDS.has(k) && typeof v === 'number')
          .map(([k, v]) => `${v} ${k.replace(/_/g, ' ')}`)
        return (
          <div key={s.id} className="row" style={{ gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <Badge tone={FETCH_TONE[s.status] || 'mute'}>{s.id} · {s.name} · {s.status}</Badge>
            <span className="dim" style={{ fontSize: 'var(--fs-xs)', flex: 1, minWidth: 200 }}>
              {s.detail}
              {nums.length > 0 && (
                <span className="mono" style={{ color: 'var(--text-3)', marginLeft: s.detail ? 8 : 0 }}>
                  {nums.join(' · ')}
                </span>
              )}
            </span>
          </div>
        )
      })}
      {end && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>Run {end.status}. {end.detail}</span>
      )}
    </div>
  )
}

/**
 * Run THIS model's evidence pipeline on demand, watch it happen, and see every
 * past run for the model.
 *
 * Append-only: the fetch adds this model's rows, never edits or deletes existing
 * ones. The button POSTs /fetch/start (spawns the pipeline in a subprocess) and
 * polls /fetch/log for per-stage progress until the run writes its end record.
 * The history reads /fetch/runs — the run logs in var/fetch/ are the store.
 */
export default function FetchPanel({ modelVersionId, onDone }) {
  const [runId, setRunId] = useState(null)
  const [records, setRecords] = useState([])
  const [running, setRunning] = useState(false)
  const [err, setErr] = useState(null)
  const [stopping, setStopping] = useState(false)
  const [runs, setRuns] = useState(null)       // history summaries
  const [openRun, setOpenRun] = useState(null) // { run_id, records } of an expanded past run

  const loadHistory = useCallback(() => {
    fetchRuns(modelVersionId)
      .then((r) => setRuns(r.runs || []))
      .catch(() => setRuns([]))
  }, [modelVersionId])

  useEffect(() => { loadHistory() }, [loadHistory])

  useEffect(() => {
    if (!runId) return
    let alive = true
    const tick = async () => {
      try {
        const res = await fetchLog(runId)
        if (!alive) return
        setRecords(res.records || [])
        if (res.done) {
          setRunning(false); setStopping(false)
          clearInterval(timer); onDone?.(); loadHistory()
        }
      } catch (e) {
        if (alive) { setErr(e.message); setRunning(false); clearInterval(timer) }
      }
    }
    const timer = setInterval(tick, 1500)
    tick()
    return () => { alive = false; clearInterval(timer) }
  }, [runId])   // eslint-disable-line react-hooks/exhaustive-deps

  async function start() {
    setErr(null); setRecords([]); setRunning(true); setStopping(false); setOpenRun(null)
    try {
      const res = await startFetch(modelVersionId)
      setRunId(res.run_id)
    } catch (e) {
      setErr(e.message); setRunning(false)
    }
  }

  /**
   * Ask the run to stop. It ends at its next stage boundary.
   *
   * `running` IS NOT CLEARED HERE, on purpose. The run is still going until it
   * writes its `stopped` end record, and the poll above is what notices that.
   * Flipping the UI to "not running" on the click would claim the run had
   * ended while its next stage was still writing rows — the same
   * absence-as-fact mistake the pipeline is careful about everywhere else.
   */
  async function stop() {
    setStopping(true)
    try {
      const res = await stopFetch(runId)
      // The run had already finished, so nothing will read the request. Say so
      // rather than sitting on "Stopping…" over a run that ended a minute ago.
      if (res && res.was_running === false) { setStopping(false); setRunning(false); loadHistory() }
    } catch (e) {
      setErr(e.message); setStopping(false)
    }
  }

  async function toggleRun(rid) {
    if (openRun?.run_id === rid) { setOpenRun(null); return }
    try {
      const res = await fetchLog(rid)
      setOpenRun({ run_id: rid, records: res.records || [] })
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <section className="card">
      <div className="row-between" style={{ marginBottom: 'var(--s3)', flexWrap: 'wrap', gap: 8 }}>
        <div className="stack" style={{ gap: 2 }}>
          <span className="label">Fetch evidence for this model</span>
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            Runs a fresh harvest of this model’s discussion through the evidence pipeline.
            Append-only — it adds new rows, never changes existing ones.
          </span>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn btn-primary" type="button" onClick={start} disabled={running}>
            {running ? <><span className="spin" /> Fetching…</> : 'Fetch'}
          </button>
          {/* SHOWN ONLY WHILE A RUN IS LIVE, and only once it has a run id -
              there is nothing to stop before /fetch/start has answered. A
              permanently visible Stop over an idle panel would be a control
              that does nothing, which is how a reader learns to distrust the
              others. */}
          {running && runId && (
            <button
              className="btn"
              type="button"
              onClick={stop}
              disabled={stopping}
              title="Stops at the next stage boundary. Rows already written are kept — every write here is an append."
            >
              {stopping ? 'Stopping…' : 'Stop'}
            </button>
          )}
        </div>
      </div>

      {err && <Notice icon={<IconAlert />}>{err}</Notice>}

      {(runId || records.length > 0) && (
        <div className="stack stack-2" style={{ marginBottom: 'var(--s3)' }}>
          <span className="label">Current run</span>
          {records.length === 0 && !err && (
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>Starting…</span>
          )}
          {stopping && (
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
              Stop requested — the run finishes its current stage and then ends.
              Rows already written are kept: every write in this pipeline is an
              append, so a stopped run holds less evidence, never wrong evidence.
            </span>
          )}
          <StageList records={records} />
        </div>
      )}

      <div className="stack stack-2">
        <span className="label">Fetch history</span>
        {runs === null && <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>Loading…</span>}
        {runs && runs.length === 0 && (
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No runs yet.</span>
        )}
        {runs && runs.map((r) => (
          <div key={r.run_id} className="stack" style={{ gap: 6 }}>
            <button
              type="button"
              className="row-between"
              onClick={() => toggleRun(r.run_id)}
              style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', textAlign: 'left', width: '100%' }}
            >
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
                {new Date(r.started_at * 1000).toLocaleString()}
              </span>
              <span className="row" style={{ gap: 8 }}>
                <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                  +{r.documents_inserted} docs · {r.stages} stages
                </span>
                <Badge tone={runTone(r)}>{r.done ? (r.status || 'done') : 'running'}</Badge>
              </span>
            </button>
            {openRun?.run_id === r.run_id && (
              <div style={{ paddingLeft: 'var(--s2)' }}><StageList records={openRun.records} /></div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
