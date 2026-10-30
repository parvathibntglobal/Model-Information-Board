import { NavLink, Link, useLocation } from 'react-router-dom'
import { MODEL_TYPES } from '../catalog/types'
import ThemeToggle from './ThemeToggle'

// THE PUBLIC SECTIONS, in the demo's order (model-information-board-home-demo.html,
// 2026-10-14): what a reader browses. Every route still sits behind the sign-in
// wall for now; which of these open to the public is decided later.
const LINKS = [
  { to: '/', label: 'Home', end: true },
  // BLOGS, A HOVER MENU (2026-10-20): the posts and the glossary - the
  // short definitions a reader looks up for the basics.
  { to: '/blogs', label: 'Blogs', items: [
    { to: '/blogs', label: 'Blog posts' },
    { to: '/glossary', label: 'AI glossary' },
  ] },
  // HOVER MENUS. The label still opens its own page on click; hovering lists
  // what is inside it, the way the demo's sections are split.
  { to: '/tools', label: 'Tools', items: [
    { to: '/best-ai-model', label: 'Best AI model picker' },
    { to: '/ai-model-pricing', label: 'AI model pricing & specs table' },
    { to: '/token-counter', label: 'LLM cost calculator' },
    { to: '/local-llm-vram-calculator', label: 'Can I run it? VRAM calculator' },
  ] },
  // MODELS, A MEGA MENU (2026-10-14): explore on the left, the seven model
  // types on the right. Every model OpenRouter lists lives at /ai-models; the
  // counted reports (/reviews) are one entry here and each model's detail.
  { to: '/ai-models', label: 'Models', mega: {
    explore: [
      { to: '/ai-models', label: 'All models', note: 'Every provider, every model' },
      { to: '/ai-models/latest', label: 'Latest AI model releases', note: 'The newest listings' },
      { to: '/compare', label: 'AI model comparison', note: 'Up to three, side by side' },
      { to: '/reviews', label: 'AI model reviews', note: 'Ranked by engineer reports' },
      // THE EVIDENCE FEED (2026-10-21, PROPOSED): the reports behind a count, each
      // in our own words with its source. Every count on these pages links in too.
      { to: '/evidence', label: 'Evidence feed', note: 'The reports behind every count' },
      // On every page through the menu (2026-10-21): the footer is on the home page only.
      { to: '/methodology', label: 'How we count reports', note: 'Methodology' },
    ],
    types: MODEL_TYPES.map((t) => ({ to: `/ai-models/${t.key}`, key: t.key, label: `${t.label} models`, note: t.note })),
  } },
  // INSIGHTS, A HOVER MENU (2026-10-30, Parvathi): what is moving in AI models -
  // benchmark scores now, the published model updates and price changes next.
  // Its own menu: Blogs is writing and Models is the catalogue (#589 review).
  // No page of its own yet, so the label opens its first item.
  { to: '/ai-benchmarks', label: 'Insights', items: [
    { to: '/ai-benchmarks', label: 'AI benchmarks' },
  ] },
  { to: '/discussions', label: 'Discussions' },
  // The FAQ is a SECTION of the landing page, not a route — same as the demo,
  // where the nav links to #faq. Kept as an anchor so the answers are in the
  // landing page's own DOM: that is where the FAQPage structured data belongs,
  // and it is what an answer engine reads.
  { to: '/#faq', label: 'FAQ', anchor: true },
]

// BEHIND "LOG IN": the full board, the model pages and the admin console - the
// only pages that still need a sign-in (2026-10-15). Shown to everyone: a
// visitor who picks one is taken to /login and brought back once signed in.
// NOFOLLOW (2026-10-21): every public page carries these four links, and each
// ends at a sign-in wall that robots.txt disallows and the page marks noindex;
// telling crawlers not to follow them keeps their time on the public pages.
const SIGNED_IN = [
  { to: '/models', label: 'Models', nofollow: true },
  { to: '/board', label: 'Board', nofollow: true },
  { to: '/benchmarks', label: 'Benchmarks', nofollow: true },
  { to: '/price-changes', label: 'Price changelog', nofollow: true },
  // A line under each, so a reader knows which to open (#585 review).
  { to: '/news', label: 'News', desc: "Outside AI headlines, from publishers' feeds", nofollow: true },
  { to: '/updates', label: 'Updates', desc: 'From our own registry, prices and benchmarks', nofollow: true },
  { to: '/admin', label: 'Admin', nofollow: true },
  { to: '/seo-keywords', label: 'SEO keywords', nofollow: true },
]

/** Whether `to` (which may carry a query) is the page being shown. */
function isHere(to, { pathname, search }) {
  const [path, query] = to.split('?')
  if (query) return pathname === path && new URLSearchParams(search).toString() === new URLSearchParams(query).toString()
  return pathname === path || pathname.startsWith(`${path}/`)
}

/** THE MODELS MEGA MENU: the same hover/focus behaviour as `Menu`, laid out
 *  as two columns - links to explore, and a tile per model type. */
function MegaMenu({ head, mega, loc, lit }) {
  return (
    <div className={`nav-menu nav-mega${lit ? ' on' : ''}`}>
      {head}
      <div className="nav-menu-pop" role="menu">
        <div className="nav-mega-in">
          <div className="nav-mega-col">
            <span className="nav-mega-h">Explore</span>
            {mega.explore.map((i) => (
              <Link key={i.to} to={i.to} role="menuitem"
                    className={`nav-mega-link${isHere(i.to, loc) && !loc.search ? ' on' : ''}`}>
                {i.label}<small>{i.note}</small>
              </Link>
            ))}
          </div>
          <div className="nav-mega-types">
            <span className="nav-mega-h">By type</span>
            {mega.types.map((t) => (
              <Link key={t.to} to={t.to} role="menuitem"
                    className={`nav-mega-tile t-${t.key}${isHere(t.to, loc) ? ' on' : ''}`}>
                <i aria-hidden="true" /><span>{t.label}<small>{t.note}</small></span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * A HOVER MENU. CSS opens it on :hover and :focus-within, so a keyboard reaches
 * the items by tabbing, the same as a mouse. `head` is the label: a link to the
 * section's own page, or (for Log in) a plain button.
 */
function Menu({ head, items, loc, lit, end }) {
  return (
    <div className={`nav-menu${lit ? ' on' : ''}${end ? ' end' : ''}`}>
      {head}
      <div className="nav-menu-pop" role="menu">
        {items.map((i) => (
          <Link key={i.to} to={i.to} role="menuitem" rel={i.nofollow ? 'nofollow' : undefined}
                className={`nav-menu-item${isHere(i.to, loc) ? ' on' : ''}`}>
            {i.label}
            {i.desc && <span className="nav-menu-desc">{i.desc}</span>}
          </Link>
        ))}
      </div>
    </div>
  )
}

export default function Nav({ session, onSignOut }) {
  const loc = useLocation()
  const caret = <span className="nav-caret" aria-hidden="true">▾</span>

  return (
    <header className="nav">
      <div className="nav-in">
        <Link to="/" className="brand" aria-label="Model Information Board home">
          <span className="brand-mark"><span /></span>
          Model Information Board
        </Link>

        <nav className="nav-links">
          {LINKS.map((l) => (
            l.anchor ? (
              // A PLAIN ANCHOR, not a NavLink. `to="/#faq"` matches the route
              // `/`, so NavLink would light up Home and FAQ at once — and the
              // browser needs a real href to jump to a section anyway.
              <a key={l.to} href={l.to} className="nav-link">{l.label}</a>
            ) : l.mega ? (
              <MegaMenu key={l.to} mega={l.mega} loc={loc}
                        lit={[...l.mega.explore, ...l.mega.types].some((i) => isHere(i.to, loc))}
                        head={<Link to={l.to} className="nav-link nav-menu-btn" aria-haspopup="true">{l.label} {caret}</Link>} />
            ) : l.items ? (
              <Menu key={l.to} items={l.items} loc={loc}
                    lit={isHere(l.to, loc) || l.items.some((i) => isHere(i.to, loc))}
                    head={<Link to={l.to} className="nav-link nav-menu-btn" aria-haspopup="true">{l.label} {caret}</Link>} />
            ) : (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => `nav-link${isActive ? ' on' : ''}`}
            >
              {l.label}
            </NavLink>
            )
          ))}
          <Menu items={SIGNED_IN} loc={loc} end
                lit={SIGNED_IN.some((i) => isHere(i.to, loc))}
                head={session
                  ? <button type="button" className="nav-link nav-menu-btn" aria-haspopup="true">Log in {caret}</button>
                  : <Link to="/login" rel="nofollow" className="nav-link nav-menu-btn" aria-haspopup="true">Log in {caret}</Link>} />
        </nav>

        <div className="nav-right">
          <ThemeToggle />
          {session ? (
            <>
              <span className="who"><span className="who-mail">{session.email}</span></span>
              <button className="btn btn-ghost" onClick={onSignOut}>Sign out</button>
            </>
          ) : (
            <Link to="/login" className="btn btn-primary">Sign in</Link>
          )}
        </div>
      </div>
    </header>
  )
}
