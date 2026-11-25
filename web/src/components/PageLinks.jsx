import { Link } from 'react-router-dom'

/**
 * TOP-RIGHT LINKS ON A SIGNED-IN PAGE (2026-11-25, Parvathi): from the page the
 * team works on to the public page that shows the same data, and to its Admin
 * section (and Scheduler tab, when a job feeds it). Admin opens on the section
 * through its own `?s=` address, the Scheduler tab through `&job=`.
 *
 * `links` is [{ to, label, title? }]; at most three, so the corner never
 * crowds (a page's own actions stay beside them).
 */
export default function PageLinks({ links }) {
  const shown = (links || []).filter(Boolean)
  if (!shown.length) return null
  return (
    <nav className="page-links" aria-label="Related pages">
      {shown.map((l) => (
        <Link key={l.to} to={l.to} className="btn btn-ghost page-link" title={l.title}>
          {l.label} →
        </Link>
      ))}
    </nav>
  )
}

/** The Admin addresses these links use, in one place. */
export const ADMIN = {
  section: (id) => `/admin?s=${id}`,
  scheduler: (job) => `/admin?s=scheduler&job=${job}`,
}
