import { useCallback, useEffect, useState } from 'react'
import { draftFeedSummary, feedSummaries, reviewFeedSummary } from '../api'
import { PolarityChip, Posted, SourceLine } from '../evidence/parts'
import '../styles/blog-live.css'
import '../styles/evidence.css'

/**
 * ADMIN -> FEED SUMMARIES (2026-10-21, PROPOSED): the one-page summary on each
 * model's evidence feed (judge/feed/summary.py).
 *
 * A model drafts it from the feed's paraphrases; a person reads it here and
 * approves or rejects it. Only an approved summary is ever shown, and a new
 * approval replaces the last. Code has already refused a draft that cites a
 * report it was not given, carries a number its citations do not, or copies a
 * source's words. What code cannot judge - whether each paragraph says what
 * its reports say - is the reviewer's call, so every cited report is shown
 * under its paragraph exactly as a reader will see it, and the soft checks'
 * flags ("most", "many": a quantity claimed in words) are marked.
 */

const TABS = [['pending', 'Waiting'], ['approved', 'Approved'], ['rejected', 'Rejected'], ['superseded', 'Replaced']]

const day = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : 'no date')

function Draft({ s, onDecide, busy }) {
  const [note, setNote] = useState('')
  const flagged = new Map()
  for (const f of s.flags || []) flagged.set(f.paragraph, [...(flagged.get(f.paragraph) || []), f])
  return (
    <div className="qb-item">
      <div className="qb-meta">
        <b>{s.model.label}</b>
        <span className="dim mono">{s.model.canonical}</span>
        <span className="dim">drafted {day(s.generated_at)} by <span className="mono">{s.proposer_model}</span></span>
      </div>
      <p className="dim">
        Written from the newest {s.reports_used} of {s.reports_available} paraphrased reports, up to {day(s.newest_report_at)}.
        {(s.flags || []).length > 0 && ` ${(s.flags || []).length} flagged for a quantity word.`}
      </p>
      {s.paragraphs.map((p, i) => {
        const flags = flagged.get(i + 1) || []
        return (
          <div key={i} className={`stack stack-1${flags.length ? ' ev-flagged' : ''}`}>
            <p className="qb-q" style={{ margin: 0 }}>{p.text}</p>
            {flags.map((f, j) => <span key={j} className="ev-flag">⚑ {f.detail}</span>)}
            <details>
              <summary className="dim">The {p.cites.length} {p.cites.length === 1 ? 'report' : 'reports'} this paragraph cites</summary>
              <div className="ev-list" style={{ marginTop: 8 }}>
                {p.cites.map((c) => {
                  const r = s.cited[c]
                  if (!r || r.gone) return <p key={c} className="ev-dim">A cited report has since been removed from the board.</p>
                  return (
                    <div key={c} className="ev-item">
                      <div className="ev-meta"><Posted at={r.posted_at} /><PolarityChip polarity={r.polarity} /></div>
                      {r.paraphrase ? <p className="ev-text">{r.paraphrase}</p> : <p className="ev-text ev-dim">No paraphrase.</p>}
                      <SourceLine source={r.source} />
                    </div>
                  )
                })}
              </div>
            </details>
          </div>
        )
      })}
      {s.review_note && <p className="dim qb-why">Review note: {s.review_note}</p>}
      {s.state === 'pending' && (
        <div className="qb-actions">
          <button type="button" className="btn" disabled={busy} onClick={() => onDecide(s.id, 'approve', note)}>Approve</button>
          <input className="lv-search qb-note" placeholder="Note (optional)" value={note}
                 onChange={(e) => setNote(e.target.value)} />
          <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => onDecide(s.id, 'reject', note)}>Reject</button>
        </div>
      )}
    </div>
  )
}

export default function FeedSummaryPanel() {
  const [tab, setTab] = useState('pending')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [model, setModel] = useState('')
  const [drafting, setDrafting] = useState(false)
  const [last, setLast] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    feedSummaries(tab).then((d) => { setData(d); setErr(null) }).catch((e) => setErr(e.message))
  }, [tab])
  useEffect(() => { load() }, [load])

  const draft = async () => {
    setDrafting(true); setLast(null)
    try { setLast(await draftFeedSummary(model.trim())); load() } catch (e) { setLast({ error: e.message, status: e.status }) }
    setDrafting(false)
  }
  const decide = async (id, decision, note) => {
    setBusy(true)
    try { await reviewFeedSummary(id, decision, note); load() } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  if (err && !data) return <p className="dim">The summaries could not be read: {err}</p>
  if (!data) return <div className="skel" style={{ height: 160 }} />
  const c = data.counts || {}
  return (
    <div className="stack stack-3">
      <p className="dim qb-intro">
        The one-page summary on each model&apos;s evidence feed, drafted by a language model from the feed&apos;s
        paraphrases and shown to readers only once approved here. Code has checked each draft&apos;s citations,
        numbers and wording; check that every paragraph says what the reports it cites say.
      </p>
      <div className="qb-stats">
        <span><b>{c.approved || 0}</b> approved</span>
        <span><b>{c.pending || 0}</b> waiting</span>
        <span><b>{c.rejected || 0}</b> rejected</span>
        <span className="dim"><b>{c.superseded || 0}</b> replaced</span>
      </div>

      <div className="qb-draft">
        <input className="lv-search" placeholder="Model id, e.g. anthropic/claude-opus-5.5" value={model}
               onChange={(e) => setModel(e.target.value)} aria-label="Model id" />
        <button type="button" className="btn" disabled={drafting || !model.trim()} onClick={draft}>
          {drafting ? <><span className="spin" /> Drafting…</> : 'Draft a summary'}
        </button>
        <span className="dim">One paid call. The draft lands under Waiting and replaces any older waiting draft.</span>
      </div>
      {last && (last.error
        ? (
          <p className="lv-note lv-warn">
            {last.status === 409 ? 'Not drafted: ' : last.status === 502 ? 'The model could not be reached: ' : 'Drafting failed: '}
            {last.error}
          </p>
        )
        : last.stored
          ? <p className="lv-note">Stored for review, written from {last.reports_used} of {last.reports_available} paraphrased reports{(last.flags || []).length ? `, ${last.flags.length} flagged` : ''}.</p>
          : <p className="lv-note lv-warn">Refused by the checks, twice: {last.refused}</p>)}

      <div className="lv-seg" role="group" aria-label="Which summaries">
        {TABS.map(([k, label]) => (
          <button key={k} type="button" className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      {data.items.length === 0
        ? <p className="lv-empty">{tab === 'pending' ? 'Nothing is waiting. Draft a summary above.' : 'None yet.'}</p>
        : data.items.map((s) => <Draft key={s.id} s={s} onDecide={decide} busy={busy} />)}
    </div>
  )
}
