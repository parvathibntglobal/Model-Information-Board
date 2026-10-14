import { NavLink, Link, useLocation } from 'react-router-dom'
import { MODEL_TYPES } from '../catalog/types'

// THE PUBLIC SECTIONS, in the demo's order (model-information-board-home-demo.html,
// 2026-10-14): what a reader browses. Every route still sits behind the sign-in
// wall for now; which of these open to the public is decided later.
const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/blogs', label: 'Blogs' },
  // HOVER MENUS. The label still opens its own page on click; hovering lists
  // what is inside it, the way the demo's sections are split.
  { to: '/tools', label: 'Tools', items: [
    { to: '/model-picker', label: 'Best AI model picker' },
    { to: '/model-finder', label: 'Model specs finder' },
    { to: '/token-counter', label: 'Token counter' },
  ] },
  // MODELS, A MEGA MENU (2026-10-14): explore on the left, the seven model
  // types on the right. Every model OpenRouter lists lives at /catalog; the
  // counted reports (/reports) are one entry here and each model's detail.
  { to: '/catalog', label: 'Models', mega: {
    explore: [
      { to: '/catalog', label: 'All models', note: 'Every provider, every model' },
      { to: '/catalog/new', label: 'New releases', note: 'The newest listings' },
      { to: '/compare', label: 'Compare models', note: 'Up to three, side by side' },
      { to: '/reports', label: 'Most reported', note: 'What engineers report about each' },
    ],
    types: MODEL_TYPES.map((t) => ({ to: `/catalog?type=${t.key}`, key: t.key, label: `${t.label} models`, note: t.note })),
  } },
  { to: '/discussions', label: 'Discussions' },
  // The FAQ is a SECTION of the landing page, not a route — same as the demo,
  // where the nav links to #faq. Kept as an anchor so the answers are in the
  // landing page's own DOM: that is where the FAQPage structured data belongs,
  // and it is what an answer engine reads.
  { to: '/#faq', label: 'FAQ', anchor: true },
]

// BEHIND "LOG IN": the full board, the model pages and the admin console. These
// are the signed-in surfaces; the menu groups them now so the later login work
// only has to change who may open them, not where they live.
const SIGNED_IN = [
  { to: '/models', label: 'Models' },
  { to: '/board', label: 'Board' },
  { to: '/admin', label: 'Admin' },
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
          <Link key={i.to} to={i.to} role="menuitem"
                className={`nav-menu-item${isHere(i.to, loc) ? ' on' : ''}`}>
            {i.label}
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
          {session && LINKS.map((l) => (
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
          {session && (
            <Menu items={SIGNED_IN} loc={loc} end
                  lit={SIGNED_IN.some((i) => isHere(i.to, loc))}
                  head={<button type="button" className="nav-link nav-menu-btn" aria-haspopup="true">Log in {caret}</button>} />
          )}
        </nav>

        <div className="nav-right">
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
