import { useEffect, useState } from 'react'
import { health, coveragePage, filteredPage, changelogPage, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Stat, Unreadable } from '../components/ui'
import UsagePanel from '../components/UsagePanel'
import PipelinePanel from '../components/PipelinePanel'
import { IconAlert, IconGauge, IconLayers, IconFilter } from '../components/Icons'

/**
 * Operations. `/health` needs nothing; the three read surfaces need the
 * database and each is allowed to be unreadable on its own, so one missing
 * page does not blank the others.
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

export default function Admin() {
  const hp = useSurface(health)
  const cov = useSurface(coveragePage)
  const filt = useSurface(() => filteredPage(50))
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
            <div className="grid g3">
              <Stat n={hp.data.environment} l="environment" />
              <Stat n={hp.data.capabilities_loaded} l="capabilities loaded" />
              <Stat n={cov.data ? 'yes' : 'no'} l="database readable" />
            </div>
          )}
        </section>
      </Reveal>

        {/* API usage — placed below Service deliberately. Service answers
            "is the board up"; this answers "what are we spending", and the
            two are read at different moments. Two paid APIs, different units. */}
        <Reveal>
          <UsagePanel />
        </Reveal>

      {/* evidence pipeline — the funnel. Placed after usage and before the
          coverage/filtered detail: it is the whole-pipeline picture those two
          panels then zoom into (what triage threw, what the board does not
          know). Counts, never money — the sibling of the panel above it. */}
      <Reveal>
        <PipelinePanel />
      </Reveal>

      {/* coverage */}
      <Reveal>
        <section className="card card-flush">
          <div className="card-head">
            <div className="row" style={{ gap: 8 }}>
              <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
              <span className="label">Coverage — what the board does not know</span>
            </div>
            {cov.data?.pipeline_version && (
              <span className="label">{cov.data.pipeline_version}</span>
            )}
          </div>
          <div className="card-body stack stack-3">
            {cov.unreadable && <Unreadable detail={cov.unreadable} compact />}
            {cov.err && <Notice icon={<IconAlert />}>{cov.err}</Notice>}
            {!cov.data && !cov.err && !cov.unreadable && <div className="skel" style={{ height: 120 }} />}

            {cov.data && (
              <>
                <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{cov.data.summary}</p>
                {!cov.data.measured_at_all && (
                  <Notice icon={<IconAlert />}>
                    Nothing has been measured yet — this is a board that has not run,
                    which is different from a board with nothing on it.
                  </Notice>
                )}
                {cov.data.kinds.map((k) => (
                  <div key={k.kind} className="caprow">
                    <div className="stack" style={{ gap: 4 }}>
                      <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
                        <strong style={{ fontSize: 'var(--fs-sm)' }}>{k.kind}</strong>
                        <Badge tone={k.measured ? 'pass' : 'mute'}>
                          {k.measured ? 'measured' : 'not measured'}
                        </Badge>
                        {k.truncated && <Badge tone="warn">truncated</Badge>}
                      </div>
                      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{k.headline}</span>
                    </div>
                    <span className="label">{k.rows} rows · {k.subjects} subjects</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </section>
      </Reveal>

      <div className="grid g2">
        {/* filtered */}
        <Reveal>
          <section className="card card-flush" style={{ height: '100%' }}>
            <div className="card-head">
              <div className="row" style={{ gap: 8 }}>
                <IconFilter width={14} height={14} style={{ color: 'var(--text-3)' }} />
                <span className="label">Filtered — and the rule that threw it</span>
              </div>
              {filt.data && (
                <span className="label">
                  {filt.data.total_filtered} of {filt.data.total_documents}
                </span>
              )}
            </div>
            <div className="card-body stack stack-2">
              {filt.unreadable && <Unreadable detail={filt.unreadable} compact />}
              {filt.err && <Notice icon={<IconAlert />}>{filt.err}</Notice>}
              {!filt.data && !filt.err && !filt.unreadable && <div className="skel" style={{ height: 120 }} />}
              {filt.data && (
                <>
                  <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{filt.data.summary}</p>
                  {filt.data.documents.length === 0 && (
                    <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>Nothing filtered yet.</p>
                  )}
                  {filt.data.documents.slice(0, 12).map((d) => (
                    <div key={d.document_id} className="stack" style={{ gap: 4 }}>
                      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                        {d.triggers.map((t) => <Badge key={t.rule} tone="fail">{t.rule}</Badge>)}
                        {!d.explained && <Badge tone="warn">no rule recorded</Badge>}
                      </div>
                      <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)', wordBreak: 'break-all' }}>
                        {d.url || d.document_id}
                      </span>
                      {d.headline && (
                        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{d.headline}</span>
                      )}
                    </div>
                  ))}
                  <p className="dim" style={{ fontSize: 'var(--fs-xs)', marginTop: 6 }}>
                    Rejected content is stored, never deleted. A filter you cannot inspect
                    cannot be trusted.
                  </p>
                </>
              )}
            </div>
          </section>
        </Reveal>

        {/* changelog */}
        <Reveal delay={90}>
          <section className="card card-flush" style={{ height: '100%' }}>
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
    </div>
  )
}
