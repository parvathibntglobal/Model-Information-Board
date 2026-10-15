import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { liveQuiz } from '../api'
import { useHead } from '../seo/head'
import { liveQuiz as quizHead } from '../seo/pages'
import { day, modelHref, shortName, wallPath } from './live'

/**
 * WHICH MODEL WAS THIS? (2026-10-15). A real quote, shown exactly as written;
 * the reader picks the model it is about.
 *
 * NOTHING IS BLANKED OUT. The server only draws quotes whose text names none
 * of the model's names, maker, family or known aliases, so the quote needs no
 * editing to be a question (judge/blog_live.py `quiz`). The same day gives
 * every reader the same questions.
 *
 * A reader's answers are kept in this browser only, so a reload does not lose
 * them. That is a convenience: a blocked storage simply starts fresh.
 */

const KEY = (d) => `mib-quiz:${d}`
const load = (d) => { try { return JSON.parse(localStorage.getItem(KEY(d)) || '{}') } catch { return {} } }
const save = (d, v) => { try { localStorage.setItem(KEY(d), JSON.stringify(v)) } catch { /* storage blocked */ } }
const shift = (iso, n) => {
  const t = new Date(`${iso}T00:00:00Z`)
  t.setUTCDate(t.getUTCDate() + n)
  return t.toISOString().slice(0, 10)
}

function Question({ q, n, picked, onPick }) {
  const done = picked != null
  const right = done && picked === q.answer.id
  return (
    <section className={`lv-q${done ? (right ? ' right' : ' wrong') : ''}`}>
      <div className="lv-q-head">
        <span className="lv-q-n">{n}</span>
        <span>An engineer {q.polarity === 'positive' ? 'reporting it working' : 'reporting problems'} · {q.topic}</span>
      </div>
      <blockquote className="lv-q-quote">{q.quote}</blockquote>
      <div className="lv-opts">
        {q.options.map((o) => (
          <button key={o.id} type="button" disabled={done} onClick={() => onPick(o.id)}
                  className={done && o.id === q.answer.id ? 'is-answer' : done && o.id === picked ? 'is-picked' : ''}>
            {shortName(o.name)}
          </button>
        ))}
      </div>
      {done && (
        <div className="lv-reveal">
          <b>{right ? 'Right.' : `It was ${shortName(q.answer.name)}.`}</b>{' '}
          <span className="dim">{q.source}{q.written ? `, ${day(q.written)}` : ''}.</span>{' '}
          {q.url && <a href={q.url} target="_blank" rel="noopener noreferrer">Read the original ↗</a>}
          <div className="lv-links">
            <Link to={wallPath(q.section, q.slug, q.answer.id)}>Every report on {shortName(q.answer.name)} · {q.topic} →</Link>
            <Link to={modelHref(q.answer)}>{shortName(q.answer.name)}'s page →</Link>
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
  const pick = (qid, mid) => {
    const next = { ...answers, [qid]: mid }
    setAnswers(next)
    save(z.day, next)
  }
  const answered = z ? z.questions.filter((q) => answers[q.id] != null) : []
  const right = answered.filter((q) => answers[q.id] === q.answer.id).length

  return (
    <div className="shell lv-page lv-narrow">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><span>Daily quiz</span></div>
      <header className="lv-head">
        <span className="lv-kicker">Daily · new questions every day</span>
        <h1>Which model was this?</h1>
        <p className="lv-sub">Real quotes from engineers, exactly as they wrote them. Pick the model each one is about.</p>
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
      {z && z.questions.length === 0 && <p className="lv-empty">There are not enough quotes to make a quiz for this day.</p>}
      {z && z.questions.map((q, i) => (
        <Question key={q.id} q={q} n={i + 1} picked={answers[q.id] ?? null} onPick={(m) => pick(q.id, m)} />
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
            Drawn at random by code from {z.pool.quotes} quotes about {z.pool.models} models, from public sources.
            A quote is used only when its text contains none of the model's names, its maker, its family or any
            spelling in our alias list - so nothing is blanked out. If one gives the answer away, that is a gap in
            the list, not a trick.
          </p>
          <p>
            The answer is the model the extractor attached the quote to, and which side it is on is the extractor's
            reading of it. Wrong choices are other models with reports, never one the quote names.
          </p>
        </footer>
      )}
    </div>
  )
}
