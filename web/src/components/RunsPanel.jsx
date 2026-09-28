import { useEffect, useState } from 'react'
import { adminRuns } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconGauge } from './Icons'

/**
 * Every fetch run this database has seen, newest first.
 *
 * WHAT HAD NO READER BEFORE THIS. The fetch log is per-run and behind a model's
 * own fold, so "how is this run going" was answerable and "what has been
 * running, and did any of it finish" was not. A run that died was found by
 * someone noticing a page had stopped moving.
 *
 * THE BOARD'S MODELS, NOT THE LOG'S. The log keeps runs for models since dropped
 * from the board; those answer a question nobody has, so the backend filters to
 * the tracked list and says how many rows that left out.
 *
 * ⚠ ALIVE IS A MEASUREMENT, NOT A STATUS, and this panel keeps the two apart on
 *   purpose. A run with no end record is not alive — a killed process writes
 *   nothing. What IS measurable is silence: the heartbeat beats every 60s, so a
 *   gap is evidence, and the row says how many beats are missing rather than
 *   converting that into a verdict the log does not hold.
 *
 * ⚠ NO MACHINE AT ALL, NOT EVEN AS A RELATION. This board is hosted and has one
 *   account, so every run a reader sees here is a run of this board — "another
 *   host" was a distinction with nothing on the other side of it. The column is
 *   still written and nothing reads it onto a page.
 */

// A status is a claim about an outcome, so each gets its own tone rather than
// all rendering alike. `abandoned` is the one to look at twice: nothing is
// known about why it stopped, only that it stopped reporting.
const STATUS_TONE = (status, looksDead) => {
  if (looksDead) return 'fail'
  if (!status) return 'mute'
  if (status === 'ok') return 'pass'
  if (status === 'abandoned' || status === 'error') return 'fail'
  return 'warn'
}

function when(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
}

export default function RunsPanel() {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    const load = () => adminRuns()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    load()
    // A LIVE PAGE, because the whole point is watching something move. 20s
    // rather than the usage panel's 15s: this is a heavier query and the thing
    // it watches ticks once a minute, so a faster poll would measure nothing
    // new.
    const t = setInterval(load, 20000)
    return () => { alive = false; clearInterval(t) }
  }, [])

  const { data, err } = state
  const runs = data?.runs || []

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconGauge width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Runs — every fetch of a tracked model</span>
        </div>
        {data && (
          <span className="label">
            {data.count} run(s) · {data.tracked_models} tracked model(s)
          </span>
        )}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          {data?.denominator
            ? <>Read from {data.denominator}</>
            : <>Read from the shared fetch log.</>}
          {/* ⚠ RULE 4/7. A caused absence says it was caused. "52 runs" with no
              mention of what was filtered out would read as every run there has
              ever been. */}
          {data?.runs_for_untracked_models > 0 && (
            <> {data.excluded_note}</>
          )}
          {/* ⚠ RULE 4 again, the other direction: a tracked model that CANNOT
              appear here says so, rather than its blank reading as "never
              fetched". */}
          {data?.unmatchable_note && <> {data.unmatchable_note}</>}
        </p>
      </div>

      <div className="card-body stack stack-3">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 200 }} />}

        {data && (
          <div className="row" style={{ gap: 16, flexWrap: 'wrap', alignItems: 'baseline' }}>
            <span className="row" style={{ gap: 6, alignItems: 'baseline' }}>
              <Badge tone="pass">running</Badge>
              <span className="dim" style={{ fontSize: 11 }}>{data.running_now}</span>
            </span>
            <span className="row" style={{ gap: 6, alignItems: 'baseline' }}>
              <Badge tone="fail">unfinished and silent</Badge>
              <span className="dim" style={{ fontSize: 11 }}>{data.unfinished_and_silent}</span>
            </span>
          </div>
        )}

        {/* ⚠ THE CAVEAT TRAVELS WITH THE NUMBER. "unfinished and silent" is not
            "dead" and the difference is a real one — the reaper does not rule
            for 45 minutes, and inside that window a corpse and a slow thread
            read identically. Stating it beside the count is the only place a
            reader would see it. */}
        {data?.note && (
          <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
            {data.note}
          </p>
        )}

        {data && runs.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-sm)' }}>
            No run has been recorded in the shared log.
          </p>
        )}

        {runs.map((r) => (
          <details key={r.run_id} className="disc">
            <summary>
              {r.model || r.run_id}
              <Badge tone={STATUS_TONE(r.status, r.looks_dead)}>
                {r.looks_dead ? 'silent' : (r.status || 'running')}
              </Badge>
              {r.ran_minutes != null && (
                <span className="n">{r.ran_minutes} min</span>
              )}
            </summary>
            <div className="disc-body stack stack-2">
              <div className="grid g2" style={{ gap: 'var(--s2)' }}>
                <Field k="started" v={when(r.started_at)} />
                <Field k="last line" v={when(r.last_at)} />
                <Field k="log lines" v={r.lines} />
                <Field
                  k="documents inserted"
                  v={r.documents_inserted}
                  /* ⚠ RULE 6. A run that reported no insert count and a run that
                     inserted nothing are different facts. */
                  absent="not reported by this run"
                />
              </div>

              {/* WHERE IT GOT TO, which is the whole value of a row with no end
                  record. A dead run is far more useful named by its last stage
                  than by the fact that it is dead. */}
              {r.last_stage && (
                <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, lineHeight: 1.6 }}>
                  <span className="mono">{r.last_stage}</span>{' '}
                  {r.last_stage_name}
                  {r.last_stage_detail ? ` — ${r.last_stage_detail}` : ''}
                </p>
              )}

              {/* THE EVIDENCE FOR "SILENT", not a second badge saying the same
                  thing. A reader who disagrees with the reading can see what it
                  was read from. */}
              {!r.finished && r.silent_minutes != null && (
                <p className="dim" style={{ fontSize: 11, margin: 0 }}>
                  No line for {r.silent_minutes} min
                  {r.missed_heartbeats ? ` — ${r.missed_heartbeats} heartbeat(s) missed` : ''}.
                  {r.looks_dead
                    ? ' Longer than three beats, so this is more likely stopped than slow.'
                    : ' Within the heartbeat, so this is reporting normally.'}
                </p>
              )}

              {r.detail && (
                <p className="dim" style={{ fontSize: 11, margin: 0, lineHeight: 1.6 }}>
                  {r.detail}
                </p>
              )}

              {/* ⚠ RULE 4. The reaper's verdict is not the run's own word. A
                  reader deciding whether to trust "abandoned" needs to know
                  which of the two wrote it, and only this line says so. */}
              {r.ruled_by_reaper && (
                <p className="dim" style={{ fontSize: 11, margin: 0 }}>
                  Ruled by the reaper, not reported by the run. Why it stopped is
                  recorded nowhere and is not being guessed at.
                </p>
              )}

              <p className="mono dim" style={{ fontSize: 10, margin: 0 }}>{r.run_id}</p>
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}

/** A label and its value, or the reason there is no value — never a blank. */
function Field({ k, v, absent }) {
  return (
    <div className="stack stack-1">
      <span className="label" style={{ fontSize: 10 }}>{k}</span>
      <span style={{ fontSize: 'var(--fs-sm)' }}>
        {v == null || v === ''
          ? <span className="dim">{absent || 'not recorded'}</span>
          : v}
      </span>
    </div>
  )
}
