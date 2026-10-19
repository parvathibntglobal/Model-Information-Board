import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { refAnswers, refAnswersFor } from '../api'
import NotFound from '../components/NotFound'
import { useHead } from '../seo/head'
import { answersHead, answersForHead } from '../seo/pages'
import { answersPath, day, engineers, issuesPath, modelHref, reports, shortName, wallPath } from './live'

/**
 * ANSWERS (2026-10-15): "Does <model> support <feature>?" - the questions
 * people search for, answered with what the catalogue ADVERTISES beside what
 * engineers REPORT (judge/blog_reference.py).
 *
 * THREE ADVERTISED STATES, NEVER TWO. Listed, not listed, and NOT PUBLISHED -
 * the last is something the feed did not tell us, never a "no" (rule 6).
 */

function advertised(a, name) {
  if (!a.in_catalogue) return ['unknown', `${name} is not in OpenRouter's catalogue today, so what it advertises is not known here.`]
  if (a.key === 'prompt_caching') {
    return a.advertised
      ? ['yes', 'OpenRouter publishes a cached-read price for it.']
      : ['unknown', 'OpenRouter publishes no cached-read price for it. That is not the same as no caching.']
  }
  if (a.advertised === true) return ['yes', `OpenRouter lists ${a.label} for it.`]
  if (a.advertised === false) return ['no', `OpenRouter does not list ${a.label} among the features it publishes for it.`]
  return ['unknown', 'OpenRouter publishes no feature list for it, so this is not known.']
}

export function AnswersIndex() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [q, setQ] = useState('')
  useHead(answersHead())
  useEffect(() => { refAnswers().then(setData).catch((e) => setErr(e.message)) }, [])
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (data?.models || []).filter((r) => !needle || r.model.name.toLowerCase().includes(needle))
  }, [data, q])

  return (
    <div className="shell lv-page">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><span>Answers</span></div>
      <header className="lv-head">
        <span className="lv-kicker">Reference · Q&amp;A</span>
        <h1>What does each model support?</h1>
        <p className="lv-sub">
          {data ? `Does it support ${data.features.join(', ')}?` : 'Does it support tool calling, structured output, image input?'}{' '}
          Each answer puts what the provider advertises beside what engineers report.
        </p>
      </header>
      {err && <p className="lv-note">The list could not be read: {err}</p>}
      {!data && !err && <div className="skel" style={{ height: 240 }} />}
      {data && (
        <>
          <div className="lv-bar">
            <input className="lv-search" type="search" placeholder="Find a model" value={q}
                   onChange={(e) => setQ(e.target.value)} aria-label="Find a model" />
          </div>
          <div className="gl-grid">
            {rows.map((r) => (
              <Link key={r.model.id} to={answersPath(r.model.id)} className="gl-card">
                <b>{shortName(r.model.name)}</b>
                <span className="lv-meta">{engineers(r.engineers)} reporting</span>
              </Link>
            ))}
          </div>
          {rows.length === 0 && <p className="lv-empty">No model matches.</p>}
        </>
      )}
    </div>
  )
}

export function AnswersFor({ rest }) {
  const id = rest.split('/').slice(1).map(decodeURIComponent).join('/')
  const [state, setState] = useState({ d: null, err: null, notFound: false })
  useHead(state.notFound ? false : answersForHead(state.d, `/blogs/${rest}`))

  useEffect(() => {
    setState({ d: null, err: null, notFound: false })
    refAnswersFor(id)
      .then((d) => setState({ d, err: null, notFound: false }))
      .catch((e) => setState({ d: null, err: e.message, notFound: e.status === 404 }))
  }, [id])

  if (state.notFound) return <NotFound what="model" back={{ to: '/blogs/answers', label: 'Answers' }} />
  const d = state.d
  const name = d ? shortName(d.model.name) : ''
  return (
    <div className="shell lv-page lv-narrow">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><Link to="/blogs/answers">Answers</Link><span>/</span><span>{name || '…'}</span></div>
      {state.err && <p className="lv-note">This page could not be read: {state.err}</p>}
      {!d && !state.err && <div className="skel" style={{ height: 240 }} />}
      {d && (
        <>
          <header className="lv-head">
            <span className="lv-kicker">Q&amp;A</span>
            <h1>What {name} supports</h1>
            <p className="lv-links">
              <Link to={modelHref(d.model)}>{name}'s page →</Link>
              <Link to={issuesPath(d.model.id)}>Known issues →</Link>
            </p>
          </header>
          {d.answers.map((a) => {
            const [tone, said] = advertised(a, name)
            const reported = a.working + a.problems + a.neutral
            return (
              <section key={a.key} id={a.key} className="qa">
                <h2>Does {name} support {a.label}?</h2>
                <p className={`qa-ad qa-${tone}`}>
                  <b>{tone === 'yes' ? 'Advertised.' : tone === 'no' ? 'Not listed.' : 'Not published.'}</b> {said}
                </p>
                {!a.mapped ? (
                  <p className="lv-note">No board topic is mapped to {a.label}, so engineers' reports are not summarised here.</p>
                ) : reported === 0 ? (
                  <p className="lv-none">No engineer has reported on {name}'s {a.label} yet.</p>
                ) : (
                  <>
                    <p className="qa-rep">
                      <b>Reported:</b> {engineers(a.working)} {reports(a.working)} it working, {a.problems} {reports(a.problems)} problems
                      {a.neutral ? `, ${a.neutral} mention it` : ''}.
                    </p>
                    {[a.sample_working, a.sample_problems].filter(Boolean).map((q, k) => (
                      <blockquote key={k} className={`lv-quote qa-q-${q.polarity}`}>
                        <p>{q.quote}</p>
                        <footer>
                          <span>{q.source}</span>{q.written && <span>{day(q.written)}</span>}
                          {q.url && <a href={q.url} target="_blank" rel="noopener noreferrer">Read the original ↗</a>}
                        </footer>
                      </blockquote>
                    ))}
                    <p className="lv-links">
                      {a.topics.map((t) => <Link key={t.slug} to={wallPath('capability', t.slug, d.model.id)}>Every report on {t.name.toLowerCase()} →</Link>)}
                    </p>
                  </>
                )}
              </section>
            )
          })}
          <footer className="lv-foot">
            <p>
              "Advertised" is what OpenRouter's catalogue lists for the model - a provider's claim, not a test.
              "Reported" counts engineers in the board's public reports. Which board topics count for each feature
              is decided by the team, not computed.
            </p>
          </footer>
        </>
      )}
    </div>
  )
}
