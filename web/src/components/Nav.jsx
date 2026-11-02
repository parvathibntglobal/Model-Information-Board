import { NavLink, Link, useLocation } from 'react-router-dom'
import { MODEL_TYPES } from '../catalog/types'
import ThemeToggle from './ThemeToggle'

// THE PUBLIC SECTIONS, in the demo's order (model-information-board-home-demo.html,
// 2026-10-14): what a reader browses. Every route still sits behind the sign-in
// wall for now; which of these open to the public is decided later.
//
// THE ORDER (2026-10-30, Parvathi): Home, then the writing (Blogs), the tools,
// what is moving (Insights), the catalogue (Models) and the community.
// Discussions and the FAQ sit under one "Community" menu instead of two bare
// links at the end.
const LINKS = [
  { to: '/', label: 'Home', end: true },
  // BLOGS, A HOVER MENU (2026-10-20): the posts and the glossary - the
  // short definitions a reader looks up for the basics.
  { to: '/blogs', label: 'Blogs', items: [
    { to: '/blogs', label: 'Blog posts' },
    { to: '/blogs/guides', label: 'Guides' },
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
  // INSIGHTS, A HOVER MENU (2026-10-30, Parvathi): what is moving in AI models -
  // benchmark scores and the approved model updates; price changes next.
  // Its own menu: Blogs is writing and Models is the catalogue (#589 review).
  // No page of its own yet, so the label opens its first item.
  { to: '/ai-benchmarks', label: 'Insights', items: [
    { to: '/ai-benchmarks', label: 'AI benchmarks', desc: 'Scores and leaderboard ranks, model by model' },
    // 2026-10-30: the updates a person approved on /updates (Parvathi).
    { to: '/ai-news-headlines', label: 'AI updates', desc: 'Launches, price moves and retirements' },
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
      // "How we count reports" moved to Community (2026-10-30): it explains the
      // site, where readers look for "about" pages.
    ],
    types: MODEL_TYPES.map((t) => ({ to: `/ai-models/${t.key}`, key: t.key, label: `${t.label} models`, note: t.note })),
  } },
  // COMMUNITY, A HOVER MENU (2026-10-30, Parvathi): the discussions and the FAQ.
  // The FAQ is a SECTION of the landing page, not a route — same as the demo,
  // where the nav links to #faq. Kept as an anchor so the answers are in the
  // landing page's own DOM: that is where the FAQPage structured data belongs,
  // and it is what an answer engine reads.
  { to: '/discussions', label: 'Community', items: [
    { to: '/discussions', label: 'Discussions' },
    { to: '/#faq', label: 'FAQ', anchor: true },
    // In the menu as well as the footer, so it is one hover away on every page.
    { to: '/methodology', label: 'How we count reports' },
  ] },
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
        {items.map((i) => (i.anchor ? (
          // A PLAIN ANCHOR (the FAQ): the browser needs a real href to jump to a
          // section, and `/#faq` must not light up as the page being shown.
          <a key={i.to} href={i.to} role="menuitem" className="nav-menu-item">{i.label}</a>
        ) : (
          <Link key={i.to} to={i.to} role="menuitem" rel={i.nofollow ? 'nofollow' : undefined}
                className={`nav-menu-item${isHere(i.to, loc) ? ' on' : ''}`}>
            {i.label}
            {i.desc && <span className="nav-menu-desc">{i.desc}</span>}
          </Link>
        )))}
      </div>
    </div>
  )
}

/**
 * THE ACCOUNT MENU (2026-10-30, Parvathi): signed in, one round button with the
 * account's initial stands where "Log in", the email and "Sign out" stood. It
 * opens to who is signed in, the signed-in pages, and Sign out - so the top bar
 * keeps one row of section menus at any screen width.
 */
function AccountMenu({ email, loc, onSignOut, caret }) {
  const initial = (email || '?').trim().charAt(0).toUpperCase()
  return (
    <div className={`nav-menu end nav-account${SIGNED_IN.some((i) => isHere(i.to, loc)) ? ' on' : ''}`}>
      <button type="button" className="nav-account-btn" aria-haspopup="true" aria-label={`Account: ${email}`}>
        <span className="nav-avatar" aria-hidden="true">{initial}</span>{caret}
      </button>
      <div className="nav-menu-pop" role="menu">
        <div className="nav-account-who">
          <span className="nav-account-label">Signed in as</span>
          <span className="nav-account-mail" title={email}>{email}</span>
        </div>
        {SIGNED_IN.map((i) => (
          <Link key={i.to} to={i.to} role="menuitem" rel={i.nofollow ? 'nofollow' : undefined}
                className={`nav-menu-item${isHere(i.to, loc) ? ' on' : ''}`}>
            {i.label}
            {i.desc && <span className="nav-menu-desc">{i.desc}</span>}
          </Link>
        ))}
        <button type="button" role="menuitem" className="nav-menu-item nav-signout" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </div>
  )
}

/**
 * SIGNED OUT, ONE CONTROL (2026-10-30, Parvathi): "Sign in ▾" replaces the
 * separate "Log in ▾" menu and "Sign in" button. Clicking it signs in; hovering
 * shows the Sign in action first, then the pages behind it - each still taken
 * to /login and brought back once signed in (nofollow, as before).
 */
function SignInMenu({ loc, caret }) {
  return (
    <div className="nav-menu end nav-signin">
      <Link to="/login" rel="nofollow" className="btn btn-primary nav-signin-btn" aria-haspopup="true">
        Sign in {caret}
      </Link>
      <div className="nav-menu-pop" role="menu">
        <div className="nav-account-who">
          <Link to="/login" rel="nofollow" role="menuitem" className="btn btn-primary nav-signin-go">Sign in</Link>
          <span className="nav-account-label">Then open the team&apos;s pages:</span>
        </div>
        {SIGNED_IN.map((i) => (
          <Link key={i.to} to={i.to} role="menuitem" rel="nofollow"
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
        </nav>

        <div className="nav-right">
          <ThemeToggle />
          {session ? (
            <AccountMenu email={session.email} loc={loc} onSignOut={onSignOut} caret={caret} />
          ) : (
            <SignInMenu loc={loc} caret={caret} />
          )}
        </div>
      </div>
    </header>
  )
}
