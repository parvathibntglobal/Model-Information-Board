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

// THE COLUMNS FOLLOW THE TOP MENU (2026-10-30, Parvathi): Blogs, Tools, Insights,
// Models, then Community - so Insights' pages are reachable from here too. The
// old "Site" column is spread over them; Home is the brand's own link.
const BLOGS = [
  { t: 'Blog posts', to: '/blogs' },
  { t: 'Guides', to: '/blogs/guides' },
  { t: 'AI glossary', to: '/glossary' },
]

const INSIGHTS = [
  { t: 'AI benchmarks', to: '/ai-benchmarks' },
  { t: 'AI updates', to: '/ai-news-headlines' },
]

const COMMUNITY = [
  { t: 'Discussions', to: '/discussions' },
  { t: 'FAQ', href: '/#faq' },
  { t: 'How we count reports', to: '/methodology' },
]

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

/** A footer column; an `href` (the FAQ's section anchor) is a plain link. */
function Col({ title, links }) {
  return (
    <nav className="footer-col" aria-label={title}>
      <span className="footer-h">{title}</span>
      {links.map((l) => (l.href ? <a key={l.t} href={l.href}>{l.t}</a> : <Link key={l.t} to={l.to}>{l.t}</Link>))}
    </nav>
  )
}

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
            {platforms && platforms.length > 0 && (
              <p className="footer-from"><span className="footer-h">Reports from</span> {platforms.join(' · ')}</p>
            )}
          </div>

          <Col title="Blogs" links={BLOGS} />
          <Col title="Tools" links={TOOLS} />
          <Col title="Insights" links={INSIGHTS} />
          <Col title="Models" links={MODELS} />

          {popular?.top?.length > 0 && (
            <nav className="footer-col" aria-label="Most discussed models">
              <span className="footer-h">Most discussed</span>
              {popular.top.map((m) => <Link key={m.id} to={modelPagePath(m.id)}>{m.name}</Link>)}
            </nav>
          )}

          <Col title="Community" links={COMMUNITY} />
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
