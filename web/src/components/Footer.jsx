import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { faqPage, modelCatalog } from '../api'
import { fmtDate, modelPagePath } from '../catalog/format'

/**
 * The site footer: what the site is, where to go, and where it reads from.
 *
 * REWORKED 2026-10-15 FOR THE PUBLIC PAGES. It linked the Board, its tabs and
 * /models - none of them published - and said reports were "quoted word for
 * word", when the public pages publish counts. Every link now opens a page a
 * visitor can see, in the nav's own words and order: the tools, then the
 * Models menu's entries.
 *
 * POPULAR MODELS ARE READ, NOT TYPED: the six models with the most engineer
 * voices in `/model-catalog` (the All models page's own order), each opening
 * its /ai-models page. The hand-typed list went stale as soon as the data moved.
 * The column is left out if the catalogue cannot be read.
 *
 * THE PLATFORMS ARE READ TOO: from `/faq`, the same public-view list the FAQ's
 * "Where do the reports come from?" answer counts, so the two cannot disagree.
 */

const TOOLS = [
  { t: 'Best AI model picker', to: '/best-ai-model' },
  { t: 'AI model pricing & specs table', to: '/ai-model-pricing' },
  { t: 'LLM cost calculator', to: '/token-counter' },
  { t: 'Can I run it? VRAM calculator', to: '/local-llm-vram-calculator' },
  { t: 'AI model comparison', to: '/compare' },
]

const MODELS = [
  { t: 'All models', to: '/ai-models' },
  { t: 'Latest AI model releases', to: '/ai-models/latest' },
  { t: 'AI model reviews', to: '/reviews' },
  { t: 'Evidence feed', to: '/evidence' },
  { t: 'By job', to: '/reviews/jobs' },
  { t: 'By capability', to: '/reviews/capabilities' },
]

const SITE = [
  { t: 'Home', to: '/' },
  { t: 'Blogs', to: '/blogs' },
  { t: 'AI glossary', to: '/glossary' },
  { t: 'Tools', to: '/tools' },
  { t: 'Discussions', to: '/discussions' },
  { t: 'Methodology', to: '/methodology' },
  { t: 'FAQ', href: '/#faq' },
]

export default function Footer() {
  const [platforms, setPlatforms] = useState(null)
  const [popular, setPopular] = useState(null)

  useEffect(() => {
    let alive = true
    faqPage().then((f) => alive && setPlatforms(f?.platforms || [])).catch(() => {})
    modelCatalog().then((c) => {
      if (!alive || c?.reason) return
      const top = (c.models || []).filter((m) => m.voices > 0)
        .sort((a, b) => b.voices - a.voices || a.name.localeCompare(b.name)).slice(0, 6)
      setPopular({ top, polled: c.polled_at ? c.polled_at.slice(0, 10) : null })
    }).catch(() => {})
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
              Find the best AI model for the job, counted from what engineers reported in real work —
              working, failing or neither, filed by job, capability and metric.
            </p>
            <p className="footer-promise">No paid placement · free to use</p>
          </div>

          <nav className="footer-col" aria-label="Tools">
            <span className="footer-h">Tools</span>
            {TOOLS.map((l) => <Link key={l.t} to={l.to}>{l.t}</Link>)}
          </nav>

          <nav className="footer-col" aria-label="Models">
            <span className="footer-h">Models</span>
            {MODELS.map((l) => <Link key={l.t} to={l.to}>{l.t}</Link>)}
          </nav>

          {popular?.top?.length > 0 && (
            <nav className="footer-col" aria-label="Most discussed models">
              <span className="footer-h">Most discussed</span>
              {popular.top.map((m) => <Link key={m.id} to={modelPagePath(m.id)}>{m.name}</Link>)}
            </nav>
          )}

          <nav className="footer-col" aria-label="Site">
            <span className="footer-h">Site</span>
            {SITE.map((l) => (l.href ? <a key={l.t} href={l.href}>{l.t}</a> : <Link key={l.t} to={l.to}>{l.t}</Link>))}
          </nav>

          {platforms && platforms.length > 0 && (
            <div className="footer-col">
              <span className="footer-h">Reports from</span>
              {platforms.map((p) => <span key={p}>{p}</span>)}
            </div>
          )}
        </div>

        <div className="footer-in">
          <span>© {new Date().getFullYear()} Model Information Board</span>
          <span>
            Counts from public reports · specs and prices as providers advertise them
            {popular?.polled && <> · model list read {fmtDate(popular.polled)}</>}
          </span>
        </div>
      </div>
    </footer>
  )
}
