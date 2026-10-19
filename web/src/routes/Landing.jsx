import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Hero from '../components/Hero'
import ReportExamples from '../components/ReportExamples'
import ToolsShowcase from '../components/ToolsShowcase'
import ModelsShowcase from '../components/ModelsShowcase'
import Faq from '../components/Faq'
import BlogShowcase from '../components/BlogShowcase'
import { Reveal, useInView } from '../components/ui'

// "LLM leaderboard alternative" (rewritten 2026-10-15 for the counts-only
// public pages): what the board gives, as a slim list, and three real
// examples from Reports (components/ReportExamples.jsx) in place of the one
// quoted entry with its source link it used to show; the heading and
// paragraph on the right. The list follows the demo
// (model-information-board-home-demo.html).
const GIVES = [
  'Real production work, filed by job',
  'Split by job, capability and metric',
  'People, each counted once, not posts',
  'Working, failing and neutral kept apart',
  'Every statement checked against its source',
  // "No scores" dropped 2026-10-19: CLAUDE.md rule 3 now permits one score,
  // the category score on Compare (#540), so the promise would be false there.
  'No paid placement, free to use',
]

// The closing call to action (reworked 2026-10-15 for the public pages): a line
// that swipes through what a visitor can do here, each line paired with the
// button that does it. As a line arrives its button lights up and a bar fills
// under it, so the copy and the actions move together; hovering a button
// shows its line and holds it there. No Board button: the Board is not
// published. JS drives the swap rather than a CSS loop, so reduced motion can
// stop it outright - the global rule would only shorten a looping animation,
// which flickers instead of stopping. Screen readers get every line once, as
// text; the moving copy is hidden from them.
const CLOSING = [
  { line: 'Find the best AI model for the job.', to: '/model-picker', cta: 'Pick a model' },
  { line: 'Browse every AI model, by provider and type.', to: '/catalog', cta: 'Browse models' },
  { line: 'Price your prompt on every model.', to: '/tools', cta: 'Try the tools' },
  { line: 'Go deeper with evidence-based AI blogs.', to: '/blogs', cta: 'Read the blogs' },
]
const CLOSING_MS = 2800

function ClosingCta() {
  const [i, setI] = useState(0)
  const [held, setHeld] = useState(false)
  // it swipes only while on screen (components/ui.jsx: useInView)
  const [el, setEl] = useState(null)
  const inView = useInView(el)
  useEffect(() => {
    if (held || !inView || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    const t = setTimeout(() => setI((n) => (n + 1) % CLOSING.length), CLOSING_MS)
    return () => clearTimeout(t)
  }, [i, held, inView])
  const prev = (i + CLOSING.length - 1) % CLOSING.length
  return (
    <div className="closing" ref={setEl}>
      <span className="eyebrow">Model Information Board</span>
      <h2 className="closing-h">
        <span className="sr-only">{CLOSING.map((c) => c.line).join(' ')}</span>
        <span className="closing-swipe" aria-hidden="true">
          {CLOSING.map((c, n) => (
            <span key={c.line} className={`closing-line l${n}${n === i ? ' on' : ''}${n === prev ? ' out' : ''}`}>
              {c.line}
            </span>
          ))}
        </span>
      </h2>
      <p className="muted">Counted from what engineers reported in real work. No paid placement.</p>
      <div className="closing-actions" onMouseLeave={() => setHeld(false)}>
        {CLOSING.map((c, n) => (
          <Link key={c.to} to={c.to} className={`btn btn-lg closing-btn l${n}${n === i ? ' on' : ''}`}
                onMouseEnter={() => { setI(n); setHeld(true) }} onFocus={() => { setI(n); setHeld(true) }} onBlur={() => setHeld(false)}>
            {c.cta} <span aria-hidden="true">→</span>
            {n === i && !held && inView && <span className="closing-bar" key={`b${i}`} style={{ '--ms': `${CLOSING_MS}ms` }} aria-hidden="true" />}
          </Link>
        ))}
      </div>
    </div>
  )
}

export default function Landing() {
  return (
    <div className="landing">
      {/* ------------------------------------------------------------ hero */}
      <section className="hero shell">
        {/* NO SEARCH BOX HERE (2026-10-15): it searched the Board, behind the
            sign-in. The Best AI model picker is the public search; the chips
            below the hero open it. */}
        <Hero />

      </section>

      {/* NO COUNTS ROW (2026-10-15): "models discussed", "board entries" and
          "blogs" were the board's own totals, not something a visitor uses. */}

      {/* ---------------------------------------------------- why trust it */}
      <section className="section shell" id="not-a-leaderboard">
        {/* the label sits above the row, over the right-hand column */}
        <div className="trust trust-top">
          <span />
          <span className="eyebrow trust-label">LLM leaderboard alternative</span>
        </div>
        <div className="trust">
          <Reveal>
            <div className="trust-panel">
              {/* one line across the whole box: it introduces the list AND the examples */}
              <span className="gives-h">The Model Information Board gives you</span>
              <div className="gives">
                <ul>
                  {GIVES.map((g) => <li key={g}>{g}</li>)}
                </ul>
              </div>
              <ReportExamples />
            </div>
          </Reveal>
          <div className="section-head trust-head">
            {/* FOUR LINES, so the claim reads as a statement rather than a caption. */}
            <h2 className="trust-lines">
              <span>Leaderboards give you</span>
              <span>a score.</span>
              <span>This gives you</span>
              <span>the count.</span>
            </h2>
            <p>
              An AI leaderboard, a Chatbot Arena vote or a table of LLM rankings gives each model one number,
              averaged across tasks you may never run. The Model Information Board counts how many different
              engineers reported each model working or failing at the job they were doing, and shows the outcome
              of that research rather than republishing anyone&apos;s posts.
            </p>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ models + compare */}
      <section className="section-tight shell" id="models-and-compare">
        {/* THE SAME HEAD AS BOARD AND BLOGS: eyebrow, H2, badge on the right. */}
        <div className="section-head section-head-row">
          <div>
            <span className="eyebrow">Models and comparisons</span>
            <h2>Every AI model, compared on the evidence</h2>
          </div>
          <Link to="/catalog" className="go-badge go-models" aria-label="Open all models">Models <span aria-hidden="true">→</span></Link>
        </div>
        {/* SIX TURNING CARDS (2026-10-15): Compare, then the Models menu's
            entries, read from the published pages (components/ModelsShowcase.jsx). */}
        <ModelsShowcase />
      </section>

      {/* ------------------------------------------------------------- tools */}
      {/* THE TOOLS, NOT THE BOARD (2026-10-15): "Browse AI models by job,
          capability or metric" opened the Board, which is not published. Each
          tool plays a short preview and opens on a click. */}
      <section className="section-tight shell" id="tools">
        <div className="section-head section-head-row">
          <div>
            <span className="eyebrow">Free AI model tools</span>
            <h2>Pick, price and filter AI models</h2>
          </div>
          <Link to="/tools" className="go-badge go-models" aria-label="Open all tools">Tools <span aria-hidden="true">→</span></Link>
        </div>
        <ToolsShowcase />
      </section>

      {/* ------------------------------------------------------------- blogs */}
      {/* Title only for now: the posts are written later and fill this in. */}
      <section className="section-tight shell" id="blogs">
        <div className="section-head section-head-row">
          <div>
            <span className="eyebrow">From the evidence · blogs</span>
            <h2>AI model insights from engineer reports</h2>
          </div>
          <Link to="/blogs" className="go-badge go-blogs" aria-label="Open the blogs">Blogs <span aria-hidden="true">→</span></Link>
        </div>
        <BlogShowcase />
      </section>


      {/* FAQ, then the closing call to action. It is the one section
          that renders when the board cannot be read: `/faq` touches no
          database, and half of what it explains is why an empty board is a
          real state. */}
      <Faq />

      {/* ---------------------------------------------------- closing cta */}
      {/* AFTER THE FAQ (2026-10-15): the questions are answered first, then
          the four places to go next, as the last thing before the footer. */}
      <section className="section shell">
        <Reveal><ClosingCta /></Reveal>
      </section>

    </div>
  )
}
