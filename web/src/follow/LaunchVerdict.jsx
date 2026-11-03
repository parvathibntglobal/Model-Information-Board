import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { evidenceSummary, launchVerdict } from '../api'
import { evidencePath } from '../catalog/format'

/**
 * THE LAUNCH VERDICT, on a model's page (2026-11-03, prototype): "the launch is
 * the trailer; this is the review". What engineers say in short - the evidence
 * feed's summary, drafted by a language model and approved by a person
 * (/feed/summary) - then what they reported in each window after release
 * (contract/verdict.yaml), counted by person and by post, with their own words
 * (judge/verdict.py). The launch claim is the page's own description at the
 * top, so it is not repeated here (2026-11-03 review).
 *
 * Counts only (rule 3): no window is scored, and the windows are not compared
 * with a number. A window not yet begun says so; one still running says
 * "so far". A model with no release date or no listing text says so (rule 6).
 */

const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : '')
const fmtShort = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }) : '')
const n = (count, one, many) => `${count} ${count === 1 ? one : many}`

/** ONE REPORT, IN OUR WORDS (2026-11-03 review): the evidence feed's checked
 *  paraphrase, never the author's text, so Reddit and X reports can be read
 *  too. The source as the feed cites it: a link for most platforms; for
 *  Reddit and X only the platform's own embed, which lives in the feed - so
 *  this points there and types no link, handle or community of its own. */
function Said({ q, side, modelId }) {
  const src = q.source || {}
  return (
    <div className={`lv-q lv-q-${side}`}>
      <p>{q.text}</p>
      <footer>
        {q.on.length > 0 && <>on {q.on.join(', ')} · </>}
        {src.kind === 'link'
          ? <a href={src.url} target="_blank" rel="noopener noreferrer">{src.platform} ↗</a>
          : <Link to={evidencePath(modelId)}>{src.kind === 'embed' ? `${src.platform === 'x' ? 'X' : 'Reddit'} post, in the evidence feed` : 'in the evidence feed'}</Link>}
        , {fmtShort(q.at)}
      </footer>
    </div>
  )
}

/** WHAT ENGINEERS SAY, IN SHORT: the approved summary's first paragraphs, said
 *  as what it is - drafted by a model, approved by a person, from how many
 *  reports. None approved yet: nothing shown, never a stand-in. */
function Voice({ id }) {
  const [s, setS] = useState(null)
  useEffect(() => {
    let alive = true
    evidenceSummary(id).then((d) => alive && setS(d)).catch(() => alive && setS(false))
    return () => { alive = false }
  }, [id])
  const sum = s && s.state === 'approved' ? s.summary : null
  if (!sum) return null
  return (
    <figure className="lv-claim">
      <figcaption>What engineers say, in short</figcaption>
      {sum.paragraphs.slice(0, 2).map((p) => <p key={p.text} className="lv-voice">{p.text}</p>)}
      <p className="lv-voice-by">
        Drafted by a language model from {sum.reports_used} of {sum.reports_available} reports and
        {sum.revised ? ' revised and' : ''} approved by a person on {fmt(sum.reviewed_at)}.
        {s.reports_since > 0 ? ` ${n(s.reports_since, 'newer report', 'newer reports')} since.` : ''}{' '}
        <Link to={`${evidencePath(id)}?tab=summary`}>Read the full summary →</Link>
      </p>
    </figure>
  )
}

function Window({ w, modelId }) {
  const head = (
    <header className="lv-win-h">
      <h3>{w.label}</h3>
      <span>{fmtShort(w.from)} – {fmtShort(w.to)}{w.state === 'open' ? ' · so far' : ''}</span>
    </header>
  )
  if (w.state === 'not_yet') {
    return <div className="lv-win lv-win-empty">{head}<p className="lv-none">Not reached yet.</p></div>
  }
  return <div className="lv-win">{head}<Period w={w} modelId={modelId} /></div>
}

/** One period's reports: people and posts, the split by side, the most-named
 *  topics and the newest quotes. Shared by the verdict's windows and the
 *  "What's new" trend's selected week (ModelPulse.jsx). */
export function Period({ w, modelId }) {
  if (!w.posts) return <p className="lv-none">Nobody reported on it in these days, in what we collected.</p>
  const p = w.by_polarity
  return (
    <>
      <p className="lv-people"><b>{n(w.people, 'person', 'people')}</b> in {n(w.posts, 'post', 'posts')}</p>
      <p className="lv-split">
        <span className="lv-pos">{p.positive.posts} working</span>
        <span className="lv-neg">{p.negative.posts} problems</span>
        <span>{p.neutral.posts} neutral</span>
      </p>
      {w.topics.length > 0 && (
        <ul className="lv-topics" aria-label="Most reported">
          {w.topics.map((t) => (
            <li key={t.name}>
              <span>{t.name}</span>
              <span className="lv-pos">+{t.positive}</span>
              <span className="lv-neg">−{t.negative}</span>
            </li>
          ))}
        </ul>
      )}
      {w.said.negative.map((q) => <Said key={q.id} q={q} side="neg" modelId={modelId} />)}
      {w.said.positive.map((q) => <Said key={q.id} q={q} side="pos" modelId={modelId} />)}
      {w.said.negative.length + w.said.positive.length > 0 && (
        <p className="lv-said-note">In our words: each is the evidence feed&apos;s checked paraphrase of one post.</p>
      )}
    </>
  )
}

export default function LaunchVerdict({ id }) {
  const [v, setV] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    launchVerdict(id)
      .then((d) => alive && setV(d))
      .catch(() => alive && setFailed(true))
    return () => { alive = false }
  }, [id])

  if (failed || (v && !v.model)) return null
  if (!v) return <section className="card"><div className="skel" style={{ height: 200 }} /></section>
  return (
    <section className="card stack stack-2" aria-label="The launch verdict">
      <h2 className="mp2-h">The launch, and what engineers found</h2>
      <Voice id={id} />
      {v.windows ? (
        <>
          <div className="lv-wins">{v.windows.map((w) => <Window key={w.key} w={w} modelId={id} />)}</div>
          {v.first_problem_report && (
            <p className="lv-first">First problem report after release: {fmt(v.first_problem_report)}.</p>
          )}
        </>
      ) : (
        <p className="lv-none">No release date is recorded for this model, so the reports cannot be placed after its launch.</p>
      )}
      <p className="lv-note">
        Counted by each post&apos;s own date, on what engineers said this model is good or bad at. A post counts once per
        side. These are counts, not a score: a window&apos;s size follows when and how often we collected, as well as
        how many people wrote.
      </p>
    </section>
  )
}
