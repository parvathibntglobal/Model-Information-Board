import { NavLink, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { health } from '../api'
import { Badge } from './ui'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/board', label: 'Board' },
  { to: '/blogs', label: 'Blogs' },
  { to: '/models', label: 'Models' },
  // The FAQ is a SECTION of the landing page, not a route — same as the demo,
  // where the nav links to #faq. Kept as an anchor so the eleven answers are
  // in the landing page's own DOM: that is where the FAQPage structured data
  // belongs, and it is what an answer engine reads.
  { to: '/#faq', label: 'FAQ', anchor: true },
  { to: '/admin', label: 'Admin' },
]

export default function Nav({ session, onSignOut }) {
  // The badge reports the backend, not a build flag. If the API is down the
  // nav says so rather than the pages failing one by one.
  const [api, setApi] = useState('checking')
  useEffect(() => {
    let alive = true
    health().then(() => alive && setApi('ok')).catch(() => alive && setApi('down'))
    return () => { alive = false }
  }, [])

  return (
    <header className="nav">
      <div className="nav-in">
        <Link to="/" className="brand" aria-label="ModelBoard home">
          <span className="brand-mark"><span /></span>
          ModelBoard
        </Link>

        <nav className="nav-links">
          {session && LINKS.map((l) => (
            l.anchor ? (
              // A PLAIN ANCHOR, not a NavLink. `to="/#faq"` matches the route
              // `/`, so NavLink would light up Home and FAQ at once — and the
              // browser needs a real href to jump to a section anyway.
              <a key={l.to} href={l.to} className="nav-link">{l.label}</a>
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
          <Badge tone={api === 'ok' ? 'pass' : api === 'down' ? 'fail' : 'mute'}>
            {api === 'ok' ? 'api live' : api === 'down' ? 'api down' : 'checking'}
          </Badge>

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
