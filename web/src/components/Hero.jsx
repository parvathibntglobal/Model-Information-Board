import { Link } from 'react-router-dom'
import FluidCanvas from './FluidCanvas'
import { Reveal } from './ui'

/**
 * The landing hero: the SEO headline and copy on the left, two engineers'
 * quotes on the right (one positive, one negative) - and nothing else inside the frame, so the promise
 * reads first. The popular-search chips sit in a strip just under it; the
 * two calls to action are in the closing section (routes/Landing.jsx).
 *
 * THE QUOTES ARE FIXED, ON PURPOSE. They are verbatim board entries, chosen by
 * a person to be clear and concrete - one positive, one negative, from two
 * different platforms (Hacker News, dev.to) and two model families - and
 * checked against the shared board on 2026-09-29: each was a verified quote in
 * Best for · Coding agents, with the source linked below.
 * They are not re-read from `/board` because a live pick can surface an entry
 * before anyone has ruled on it, and the first thing a visitor reads should
 * not be the one place an unreviewed quote appears. Changing them is an edit
 * here, with the same check.
 *
 * THE FLUID SURFACE IS THE OLD HERO'S, kept: it listens on `.hero-frame` and
 * blends over the headline; the quote cards and controls sit above it. Its
 * "move the cursor" hint is gone - the surface answers the cursor anyway.
 *
 * THE CHIPS ARE LINKS, NOT DATA. Each names a search people make and opens
 * the board page that answers it.
 */

// Alphabetical, so the order carries no ranking.
const CHIPS = [
  { label: 'AI agents', to: '/board/capabilities/agentic-tool-use' },
  { label: 'AI summarization', to: '/board/capabilities/summarization' },
  { label: 'Claude vs GPT', to: '/compare?ids=anthropic/claude-opus-5,openai/gpt-6-astra' },
  { label: 'Context window', to: '/board/metrics/context-window' },
  { label: 'Cybersecurity', to: '/board/capabilities/cybersecurity' },
  { label: 'Instruction following', to: '/board/capabilities/instruction-following' },
  // A parent heading on the Capabilities tab (contract/slug_parents.yaml), not
  // one section: the link opens the tab at that group.
  { label: 'Software engineering', to: '/board?tab=cap#parent-software-engineering' },
]

// Verbatim, with the source each came from. Checked 2026-09-29.
const QUOTES = [
  {
    polarity: 'positive',
    quote: "Since then I've been using GLM 5.2 with openrouter + opencode and am spending less than $5/day for equivalent output.",
    model: 'GLM 5.2',
    source: 'Hacker News',
    url: 'https://news.ycombinator.com/item?id=48804953',
  },
  {
    polarity: 'negative',
    quote: 'halfway through a long task they started forgetting decisions made twenty messages earlier, truncating files mid-function, and contradicting their own plan',
    model: 'Claude Opus 4.8',
    source: 'dev.to',
    url: 'https://dev.to/yaseenyk04/budgeting-the-claude-context-window-before-it-truncates-you-57mm',
  },
]

// `children` sits between the frame and the chips: the landing passes its
// search box there, so the chips read as suggestions under it.
export default function Hero({ children }) {
  return (
    <>
      <div className="hero-frame hero-aurora">
        <span className="hero-corner tl" /><span className="hero-corner tr" />
        <span className="hero-corner bl" /><span className="hero-corner br" />
        <FluidCanvas />

        <div className="hero-split">
          <div className="hero-copy">
            <span className="hero-kicker">Model Information Board</span>
            <Reveal as="h1">Find the best AI model for the job — proven by the engineers who use it.</Reveal>
            <Reveal delay={120}>
            <p className="hero-sub">
            An <Link to="/compare"><strong>AI model comparison</strong></Link> built from what engineers report in
            production. Pick the work — a <Link to="/board/jobs/coding-agent">coding agent</Link>,
            a <Link to="/board/jobs/rag">RAG pipeline</Link>, <Link to="/board/jobs/code-review">code review</Link> — and
            read what they said about every model they used for it, failures included. If the <strong>best AI model
            for coding</strong> is an open-source or local LLM, it says so.
          </p>
            </Reveal>
          </div>

          <div className="hero-collage" aria-label="What engineers said">
            {QUOTES.map((q, i) => (
              <figure key={q.url} className={`hq hq${i}`} data-polarity={q.polarity}>
                <span className="hq-pol">{q.polarity}</span>
                <blockquote>“{q.quote}”</blockquote>
                <figcaption>
                  <b>{q.model}</b> · <a href={q.url} target="_blank" rel="nofollow noopener noreferrer">{q.source}</a>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>

      </div>

      {/* The chips stand still, arranged in a wrapping row (2026-10-06: they used
          to slide in a loop). Drawn once, so each chip is announced and reached
          once. */}
      {children}

      <nav className="hero-strip" aria-label="Popular searches">
        <div className="hero-set">
          {CHIPS.map((c) => (
            <Link key={c.label} to={c.to} className="chip">{c.label} →</Link>
          ))}
        </div>
      </nav>

    </>
  )
}
