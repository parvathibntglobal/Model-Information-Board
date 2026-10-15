import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { liveQuiz } from '../api'
import { fmtCtx, fmtUsd, modelPagePath } from '../catalog/format'
import { useHead } from '../seo/head'
import { liveQuiz as quizHead } from '../seo/pages'
import { day } from './live'

/**
 * THE DAILY QUIZ (reworked 2026-10-15): general questions about the models,
 * each answered by a figure this site publishes - a price, a context window,
 * a date, what a model reads or writes, a feature it advertises, its maker,
 * or how many engineers wrote about it (judge/blog_live.py `quiz`).
 *
 * It used to show an engineer's quote and ask which model it was about. A
 * reader cannot know who wrote a quote or where, so that was a guess, not a
 * question. Now every choice shows its own figure once answered: the reader
 * learns why, not only what.
 *
 * The same day gives every reader the same questions. A reader's answers are
 * kept in this browser only - a convenience; blocked storage starts fresh.
 */

const KEY = (d) => `mib-quiz-v3:${d}`
const load = (d) => { try { return JSON.parse(localStorage.getItem(KEY(d)) || '{}') } catch { return {} } }
const save = (d, v) => { try { localStorage.setItem(KEY(d), JSON.stringify(v)) } catch { /* storage blocked */ } }
const shift = (iso, n) => {
  const t = new Date(`${iso}T00:00:00Z`)
  t.setUTCDate(t.getUTCDate() + n)
  return t.toISOString().slice(0, 10)
}

/** A choice's figure, in words. */
function figure(o) {
  if (o.unit === 'tokens') return `${fmtCtx(o.value)} tokens`
  if (o.unit === 'usd_per_m') return `${fmtUsd(o.value)} per 1M`
  if (o.unit === 'date') return day(o.value)
  if (o.unit === 'list') return o.value.join(', ')
  if (o.unit === 'yesno') return o.value ? 'advertises it' : 'does not advertise it'
  if (o.unit === 'engineers') return `${o.value} ${o.value === 1 ? 'engineer' : 'engineers'}`
  return null
}

/** A link target: `model:<id>` is a model's page; anything else is a path. */
const to = (target) => (target.startsWith('model:') ? modelPagePath(target.slice(6)) : target)

function Question({ q, n, picked, onPick }) {
  const done = picked != null
  const right = done && picked === q.answer
  const answer = q.options.find((o) => o.id === q.answer)
  return (
    <section className={`lv-q${done ? (right ? ' right' : ' wrong') : ''}`}>
      <div className="lv-q-head">
        <span className="lv-q-n">{n}</span>
        <span>{q.source}</span>
      </div>
      <h2 className="lv-q-prompt">{q.prompt}</h2>
      <div className="lv-opts">
        {q.options.map((o) => {
          const cls = done && o.id === q.answer ? 'is-answer' : done && o.id === picked ? 'is-picked' : ''
          const fig = done ? figure(o) : null
          return (
            <button key={o.id} type="button" disabled={done} onClick={() => onPick(o.id)} className={cls}>
              <span>{o.name}</span>
              {fig && <span className="lv-opt-fig">{fig}</span>}
            </button>
          )
        })}
      </div>
      {done && (
        <div className="lv-reveal">
          <b>{right ? 'Right.' : `It's ${answer?.name}.`}</b>{' '}
          <span className="dim">{q.explain}</span>
          <div className="lv-links">
            {q.links.map(([label, target]) => <Link key={target} to={to(target)}>{label} →</Link>)}
          </div>
        </div>
      )}
    </section>
  )
}

export default function Quiz() {
  const [dayIso, setDay] = useState(null)
  const [state, setState] = useState({ z: null, err: null })
  const [answers, setAnswers] = useState({})
  useHead(quizHead())

  useEffect(() => {
    setState({ z: null, err: null })
    liveQuiz(dayIso)
      .then((z) => { setState({ z, err: null }); setAnswers(load(z.day)) })
      .catch((e) => setState({ z: null, err: e.message }))
  }, [dayIso])

  const z = state.z
  const pick = (qid, choice) => {
    const next = { ...answers, [qid]: choice }
    setAnswers(next)
    save(z.day, next)
  }
  const answered = z ? z.questions.filter((q) => answers[q.id] != null) : []
  const right = answered.filter((q) => answers[q.id] === q.answer).length

  return (
    <div className="shell lv-page lv-narrow">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><span>Daily quiz</span></div>
      <header className="lv-head">
        <span className="lv-kicker">Daily · new questions every day</span>
        <h1>How well do you know language models?</h1>
        <p className="lv-sub">
          Five questions a day on how large language models work - tokens, attention, fine-tuning,
          retrieval, cost - and one from what this board has measured. Answer to see why.
        </p>
        {z && (
          <div className="lv-bar">
            <button type="button" className="btn btn-ghost" onClick={() => setDay(shift(z.day, -1))}>← Previous day</button>
            <span className="lv-note lv-inline">{z.day === z.latest_day ? `Today, ${day(z.day)}` : day(z.day)}</span>
            {z.day !== z.latest_day && <button type="button" className="btn btn-ghost" onClick={() => setDay(null)}>Today →</button>}
          </div>
        )}
      </header>
      {state.err && <p className="lv-note">The quiz could not be read: {state.err}</p>}
      {!z && !state.err && <div className="skel" style={{ height: 320 }} />}
      {z && z.questions.length === 0 && <p className="lv-empty">There is not enough data to make a quiz for this day.</p>}
      {z && z.general_shortfall > 0 && (
        <p className="lv-note">
          {z.approved_in_bank === 0
            ? 'No general questions have been approved yet, so today is drawn from the board instead.'
            : `Only ${z.approved_in_bank} general ${z.approved_in_bank === 1 ? 'question has' : 'questions have'} been approved so far, so ${z.general_shortfall} of today's ${z.general_shortfall === 1 ? 'comes' : 'come'} from the board instead.`}
        </p>
      )}
      {z && z.questions.map((q, i) => (
        <Question key={q.id} q={q} n={i + 1} picked={answers[q.id] ?? null} onPick={(c) => pick(q.id, c)} />
      ))}
      {z && z.questions.length > 0 && (
        <p className="lv-score">
          {answered.length < z.questions.length
            ? `${answered.length} of ${z.questions.length} answered`
            : `You got ${right} of ${z.questions.length}. New questions tomorrow.`}
        </p>
      )}
      {z && (
        <footer className="lv-foot">
          <p>
            General questions are drafted by a language model and each one is read and approved by a person on
            the team before it can appear here. If you think an answer is wrong, tell us.
          </p>
          <p>
            Questions from the board are built by code{z.catalogue_read ? ` from OpenRouter's catalogue as read on ${day(z.catalogue_read)}` : ''} and
            the board's public reports, and every answer is a published figure. A "which is highest" question is
            used only when the answer is clearly ahead, and a model whose figure is not published is never a choice.
          </p>
        </footer>
      )}
    </div>
  )
}
