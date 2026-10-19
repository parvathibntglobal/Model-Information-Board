import { useCallback, useEffect, useState } from 'react'
import { draftQuizQuestions, quizBank, reviewQuizQuestion } from '../api'
import { Badge } from './ui'
import '../styles/blog-live.css'

/**
 * ADMIN -> QUIZ (2026-10-15): the question bank behind the daily quiz.
 *
 * A model drafts general questions on a topic (judge/quiz_bank.py); a person
 * reads each one here and approves or rejects it. Only approved questions are
 * ever shown to a reader. Code has already refused drafts with the wrong
 * shape; whether the marked answer is RIGHT is the reviewer's call, so the
 * explanation is shown beside it to check against.
 */

const TABS = [['pending', 'Waiting'], ['approved', 'Approved'], ['rejected', 'Rejected']]
const TONE = { easy: 'pass', medium: 'mute', hard: 'warn' }

function Item({ q, onDecide, busy }) {
  const [note, setNote] = useState('')
  return (
    <div className="qb-item">
      <div className="qb-meta">
        <span>{q.topic}</span>
        <Badge tone={TONE[q.difficulty] || 'mute'}>{q.difficulty}</Badge>
        <span className="dim mono">{q.model}</span>
      </div>
      <p className="qb-q">{q.question}</p>
      <ol className="qb-opts">
        {q.options.map((o, i) => (
          <li key={i} className={i === q.answer_index ? 'qb-right' : ''}>
            {i === q.answer_index && <b>✓ </b>}{o}
          </li>
        ))}
      </ol>
      <p className="qb-why"><span className="label">Why</span> {q.explanation}</p>
      {q.review_note && <p className="dim qb-why">Review note: {q.review_note}</p>}
      <div className="qb-actions">
        {q.state !== 'approved' && (
          <button type="button" className="btn" disabled={busy} onClick={() => onDecide(q.id, 'approved', note)}>Approve</button>
        )}
        {q.state !== 'rejected' && (
          <>
            <input className="lv-search qb-note" placeholder="Why reject? (optional)" value={note}
                   onChange={(e) => setNote(e.target.value)} />
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => onDecide(q.id, 'rejected', note)}>Reject</button>
          </>
        )}
        {q.state !== 'pending' && (
          <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => onDecide(q.id, 'pending', '')}>Back to waiting</button>
        )}
      </div>
    </div>
  )
}

export default function QuizPanel() {
  const [tab, setTab] = useState('pending')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [topic, setTopic] = useState('')
  const [drafting, setDrafting] = useState(false)
  const [last, setLast] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    quizBank(tab)
      .then((d) => { setData(d); setErr(null); setTopic((t) => t || d.counts.topics[0] || '') })
      .catch((e) => setErr(e.message))
  }, [tab])
  useEffect(() => { load() }, [load])

  const draft = async () => {
    setDrafting(true); setLast(null)
    try { setLast(await draftQuizQuestions(topic)); load() } catch (e) { setLast({ error: e.message }) }
    setDrafting(false)
  }
  const decide = async (id, decision, note) => {
    setBusy(true)
    try { await reviewQuizQuestion(id, decision, note); load() } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  if (err && !data) return <p className="dim">The question bank could not be read: {err}</p>
  if (!data) return <div className="skel" style={{ height: 160 }} />
  const c = data.counts
  return (
    <div className="stack stack-3">
      <p className="dim qb-intro">
        General questions about how language models work, drafted by <code>{c.model}</code> and shown on the
        daily quiz only once approved here. Code has checked each draft's shape; check that the marked answer is
        right before approving.
      </p>
      <div className="qb-stats">
        <span><b>{c.approved}</b> approved</span>
        <span><b>{c.pending}</b> waiting</span>
        <span><b>{c.rejected}</b> rejected</span>
        <span className="dim">
          Drafting so far: {c.spend.calls} {c.spend.calls === 1 ? 'call' : 'calls'}, ${c.spend.usd.toFixed(4)} provider-reported
          {c.spend.unpriced_calls > 0 && `, ${c.spend.unpriced_calls} with no reported cost`}
        </span>
      </div>

      <div className="qb-draft">
        <select value={topic} onChange={(e) => setTopic(e.target.value)} aria-label="Topic">
          {c.topics.map((t) => {
            const n = c.by_topic[t] || { approved: 0, pending: 0 }
            return <option key={t} value={t}>{t} ({n.approved} approved, {n.pending} waiting)</option>
          })}
        </select>
        <button type="button" className="btn" disabled={drafting || !topic} onClick={draft}>
          {drafting ? <><span className="spin" /> Drafting…</> : 'Draft questions'}
        </button>
        <span className="dim">One paid call on this topic. Drafts land under Waiting.</span>
      </div>
      {last && (last.error
        ? <p className="lv-note lv-warn">Drafting failed: {last.error}</p>
        : (
          <p className="lv-note">
            {last.proposed} drafted · {last.stored} stored · {last.already_in_bank} already in the bank
            {Object.keys(last.refused || {}).length > 0 && ` · refused: ${Object.entries(last.refused).map(([w, n]) => `${n} ${w}`).join('; ')}`}
            {last.cost_usd != null ? ` · $${Number(last.cost_usd).toFixed(4)}` : ' · no cost reported'}
          </p>
        ))}

      <div className="lv-seg" role="group" aria-label="Which questions">
        {TABS.map(([k, label]) => (
          <button key={k} type="button" className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      {data.items.length === 0
        ? <p className="lv-empty">{tab === 'pending' ? 'Nothing is waiting. Draft some questions above.' : `No ${tab} questions yet.`}</p>
        : data.items.map((q) => <Item key={q.id} q={q} onDecide={decide} busy={busy} />)}
    </div>
  )
}
