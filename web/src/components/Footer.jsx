import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { faqPage } from '../api'

/**
 * The site footer: what the board is, where to go, and where it reads from.
 *
 * EVERY LINK OPENS A PAGE THAT EXISTS. The first landing demo's footer also
 * offered "Describe a task" (the Ask flow, since removed) and "Open-source &
 * alternatives" (no such page yet); both are left out until they are real.
 *
 * THE MODELS COLUMN names tracked models the landing page does not already
 * show, so the footer adds names rather than repeating them; each is a model
 * page by registry id.
 *
 * THE PLATFORMS ARE READ, NOT TYPED: they come from `/faq`, the same list the
 * FAQ's "Where does the evidence come from?" answer uses, and the column is
 * left out if it cannot be read.
 */

const EXPLORE = [
  { t: 'AI model comparison', to: '/compare' },
  { t: 'Best AI model for the job', to: '/board?tab=best' },
  { t: 'Capabilities', to: '/board?tab=cap' },
  { t: 'Metrics & benchmarks', to: '/board?tab=met' },
]

const SITE = [
  { t: 'Board', to: '/board' },
  { t: 'Models', to: '/models' },
  { t: 'Blogs', to: '/blogs' },
  { t: 'FAQ', href: '/#faq' },
]

const MODELS = [
  { t: 'Claude Fable 5.1', id: 'anthropic/claude-fable-5-1' },
  { t: 'Claude Opus 5.5', id: 'anthropic/claude-opus-5.5' },
  { t: 'Claude Opus 4.6', id: 'anthropic/claude-opus-4.6' },
  { t: 'GPT-5.5 Codex', id: 'openai/gpt-5.5' },
  { t: 'Grok 4.6', id: 'x-ai/grok-4.6' },
  { t: 'GLM 5.3', id: 'z-ai/glm-5.3' },
]

export default function Footer() {
  const [platforms, setPlatforms] = useState(null)

  useEffect(() => {
    let alive = true
    faqPage().then((f) => alive && setPlatforms(f?.platforms || [])).catch(() => {})
    return () => { alive = false }
  }, [])

  return (
    <footer className="footer">
      <div className="shell">
        <div className="footer-grid">
          <div className="footer-brand">
            <Link to="/" className="brand" aria-label="Model Information Board home">
              <span className="brand-mark"><span /></span>
              Model Information Board
            </Link>
            <p>
              What engineers publicly report about AI models — quoted word for word, filed by job,
              capability and metric, and kept current.
            </p>
          </div>

          <nav className="footer-col" aria-label="Explore">
            <span className="footer-h">Explore</span>
            {EXPLORE.map((l) => <Link key={l.t} to={l.to}>{l.t}</Link>)}
          </nav>

          <nav className="footer-col" aria-label="Site">
            <span className="footer-h">Site</span>
            {SITE.map((l) => (l.href ? <a key={l.t} href={l.href}>{l.t}</a> : <Link key={l.t} to={l.to}>{l.t}</Link>))}
          </nav>

          <nav className="footer-col" aria-label="Models">
            <span className="footer-h">Models</span>
            {MODELS.map((m) => <Link key={m.id} to={`/models/${m.id}`}>{m.t}</Link>)}
          </nav>

          {platforms && platforms.length > 0 && (
            <div className="footer-col">
              <span className="footer-h">Evidence from</span>
              {platforms.map((p) => <span key={p}>{p}</span>)}
            </div>
          )}
        </div>

        <div className="footer-in">
          <span className="mono">Model Information Board</span>
          <span>Live backend · nothing on these pages is synthesised by the frontend</span>
        </div>
      </div>
    </footer>
  )
}
