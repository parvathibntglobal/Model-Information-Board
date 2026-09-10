import { useEffect, useState } from 'react'
import { health, coveragePage, changelogPage, listModels, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Stat, Unreadable } from '../components/ui'
import UsagePanel from '../components/UsagePanel'
import BoardReview from '../components/BoardReview'
import CapabilityReview from '../components/CapabilityReview'
import FetchPanel from '../components/FetchPanel'
import { IconAlert, IconGauge } from '../components/Icons'

/**
 * Operations. `/health` needs nothing; the database-backed surfaces are each
 * allowed to be unreadable on their own, so one missing page does not blank the
 * others.
 */
function useSurface(fn, deps = []) {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  useEffect(() => {
    let alive = true
    fn()
      .then((d) => alive && setState({ data: d, err: null, unreadable: null }))
      .catch((e) => alive && setState({
        data: null,
        err: e instanceof BoardUnreadable ? null : e.message,
        unreadable: e instanceof BoardUnreadable ? e.message : null,
      }))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

/**
 * Collect evidence — the tracked models, each with a Fetch button and its
 * fetch-log history. Sweeping a model runs its evidence pipeline on demand and
 * appends new rows; the per-model history is served from the stored run logs.
 */
function CollectEvidence() {
  const [models, setModels] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    listModels()
      .then((d) => alive && setModels(d.models || []))
      .catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  return (
    <div className="stack stack-3">
      <div className="stack stack-1">
        <span className="label">Collect evidence — sweep a model on demand</span>
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          Each fetch runs a fresh harvest through the evidence pipeline and appends new rows.
          The fetch log and every past run are kept per model.
        </span>
      </div>
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!models && !err && <div className="skel" style={{ height: 120 }} />}
      {models && models.length === 0 && (
        <p className="dim" style={{ fontSize: 'var(--fs-sm)' }}>No models tracked yet.</p>
      )}
      {models && models.map((m) => (
        <div key={m.model_version_id} className="stack stack-1">
          <div className="row" style={{ gap: 10, flexWrap: 'wrap', alignItems: 'baseline' }}>
            <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.display_name || m.model_version_id}</strong>
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{m.model_version_id}</span>
            {m.provider && <Badge tone="mute">{m.provider}</Badge>}
          </div>
          <FetchPanel modelVersionId={m.model_version_id} />
        </div>
      ))}
    </div>
  )
}

export default function Admin() {
  const hp = useSurface(health)
  const cov = useSurface(coveragePage)
  const chg = useSurface(() => changelogPage(30))

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="eyebrow">Operations</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Pipeline health</h1>
        <p className="muted">Read straight off the backend. Nothing on this page is synthesised.</p>
      </div>

      {/* health — no database required, so this always answers */}
      <Reveal>
        <section className="card">
          <div className="row-between" style={{ marginBottom: 'var(--s3)' }}>
            <div className="row" style={{ gap: 8 }}>
              <IconGauge width={14} height={14} style={{ color: 'var(--text-3)' }} />
              <span className="label">Service</span>
            </div>
            {hp.data
              ? <Badge tone="pass">{hp.data.status}</Badge>
              : <Badge tone="fail">unreachable</Badge>}
          </div>
          {hp.err && <Notice icon={<IconAlert />}>{hp.err}</Notice>}
          {hp.data && (
            <div className="grid g2">
              {/* `capabilities_loaded` REMOVED — and the comment lives INSIDE
                  the div because `{cond && ( ... )}` takes ONE child, so a
                  comment beside the element is a second one and the build
                  refuses it.

                  It counted the ratified twelve: the closed vocabulary feeding
                  the legacy cell score, not the board's sections, which are
                  discovered from the evidence and unbounded. On a health panel
                  it read as "the board tracks 12 things", which is the one
                  thing it does not mean. `/health` still returns the figure;
                  nothing renders it as health. */}
              <Stat n={hp.data.environment} l="environment" />
              <Stat n={cov.data ? 'yes' : 'no'} l="database readable" />
            </div>
          )}
        </section>
      </Reveal>

      {/* API usage — placed below Service deliberately. Service answers
          "is the board up"; this answers "what are we spending". */}
      <Reveal>
        <UsagePanel />
      </Reveal>

      {/* collect evidence — the models, each with a fetch button and its
          fetch-log history. This is where a model gets swept on demand. */}
      <Reveal>
        <CollectEvidence />
      </Reveal>

      {/* board sections the classifier discovered. Placed ABOVE the capability
          review because it is the surface that now decides what the board shows,
          and because the two are easily confused: these are already live and are
          being consolidated, those are waiting outside the vocabulary to be let
          in. Adjacent so the difference is visible rather than assumed. */}
      <Reveal>
        <BoardReview />
      </Reveal>

      {/* capability discovery review — the extractor's proposed keys, awaiting a
          ruling. A decision the run produces, not a health signal. */}
      <Reveal>
        <CapabilityReview />
      </Reveal>

      {/* changelog */}
      <Reveal>
        <section className="card card-flush">
          <div className="card-head">
            <span className="label">Changelog — us, or the world</span>
            {chg.data && <span className="label">{chg.data.total_labels} labels · {chg.data.window_days}d</span>}
          </div>
          <div className="card-body stack stack-2">
            {chg.unreadable && <Unreadable detail={chg.unreadable} compact />}
            {chg.err && <Notice icon={<IconAlert />}>{chg.err}</Notice>}
            {!chg.data && !chg.err && !chg.unreadable && <div className="skel" style={{ height: 120 }} />}
            {chg.data && (
              <>
                <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{chg.data.summary}</p>
                {Object.entries(chg.data.by_driver).length === 0 && (
                  <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No label changes in the window.</p>
                )}
                {Object.entries(chg.data.by_driver).map(([driver, changes]) => (
                  <div key={driver} className="stack" style={{ gap: 6 }}>
                    <span className="label">{driver} · {changes.length}</span>
                    {changes.slice(0, 6).map((c) => (
                      <div key={c.change_id} className="row" style={{ gap: 8, alignItems: 'flex-start' }}>
                        <Badge tone={c.direction === 'gained' ? 'pass' : 'fail'}>{c.direction}</Badge>
                        <span style={{ fontSize: 'var(--fs-xs)' }}>{c.headline}</span>
                        {!c.evidenced && <Badge tone="warn">unevidenced</Badge>}
                      </div>
                    ))}
                  </div>
                ))}
              </>
            )}
          </div>
        </section>
      </Reveal>
    </div>
  )
}
