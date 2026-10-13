import { Link, useLocation } from 'react-router-dom'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'

/**
 * "Not found", said plainly, at the address that was asked for (SEO item 7).
 *
 * Every missing page used to be a SOFT 404: an unknown address redirected to
 * the landing, an unknown job, capability or metric slug rendered the board
 * hub, and an unknown blog post rendered the blog index - each at the address
 * that was asked for. To a reader that is a link that silently went somewhere
 * else; to a search engine it is a real page with somebody else's content, at
 * an address that should not exist. This renders a not-found page instead,
 * keeps the address in the bar so the reader can see what they asked for, and
 * is always `noindex`.
 *
 * A browser-side app cannot send an HTTP 404 status - the host serves the same
 * index.html for every path - so `noindex` is what stops it being listed. When
 * the board is server-rendered (an open decision), this is where a 404 status
 * belongs.
 *
 * `what` names the kind of thing that was missing ("job", "model"), and `back`
 * is where to look for the real ones; without them it is the generic page.
 */
export default function NotFound({ what, back }) {
  const { pathname } = useLocation()
  useHead(PRIVATE.notFound)
  const where = back || { to: '/board', label: 'Browse the board' }
  return (
    <div className="shell section-tight stack stack-3">
      <span className="eyebrow">Not found</span>
      <h1>{what ? `There is no ${what} at this address` : 'There is no page at this address'}</h1>
      <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '70ch' }}>
        Nothing on the board answers to <code>{pathname}</code>. It may have been renamed or merged
        with another, or the link may be mistyped.
        {what === 'job' || what === 'capability' || what === 'metric'
          ? ' The board lists only what engineers have actually reported, so a section nobody has discussed is not here.'
          : ''}
      </p>
      <p style={{ fontSize: 'var(--fs-sm)' }}>
        <Link to={where.to} className="mb-link">{where.label}</Link>
        {where.to !== '/' && <> · <Link to="/" className="mb-link">Home</Link></>}
      </p>
    </div>
  )
}
