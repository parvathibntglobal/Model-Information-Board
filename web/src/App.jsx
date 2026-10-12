import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Suspense, lazy, useCallback, useEffect, useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import Landing from './routes/Landing'
import Login from './routes/Login'
import { getSession, signOut } from './auth'
import NotFound from './components/NotFound'

/**
 * ROUTE-LEVEL CODE SPLITTING (SEO item 10, 2026-10-09). The whole app was one
 * 544.6 kB script (159.3 kB gzipped) that every visitor downloaded before the
 * first paint - the admin console included, which a reader never opens. The
 * front door stays in the first download: the shell, Login and Landing. Every
 * other page is its own chunk, fetched when it is first visited.
 *
 * A DEPLOY REPLACES THE CHUNKS. A tab opened before it still names the old
 * files, so the import fails; this reloads ONCE to pick up the new build
 * instead of rendering nothing. The flag stops a loop: if the reload does not
 * fix it, the error is thrown and shows (rule 12), never swallowed.
 */
function page(load) {
  return lazy(() => load().catch((err) => {
    let reloaded = false
    try { reloaded = sessionStorage.getItem('chunk-reload') === '1' } catch { /* storage blocked */ }
    if (!reloaded) {
      try { sessionStorage.setItem('chunk-reload', '1') } catch { /* storage blocked */ }
      window.location.reload()
      return new Promise(() => {})
    }
    throw err
  }).then((mod) => {
    try { sessionStorage.removeItem('chunk-reload') } catch { /* storage blocked */ }
    return mod
  }))
}

const Board = page(() => import('./routes/Board'))
const Blogs = page(() => import('./routes/Blogs'))
const ModelDetail = page(() => import('./routes/ModelDetail'))
const Models = page(() => import('./routes/Models'))
const Compare = page(() => import('./routes/Compare'))
const Admin = page(() => import('./routes/Admin'))
const BlogLogs = page(() => import('./routes/BlogLogs'))

/** What a page shows while its chunk downloads: the skeleton the pages use for data. */
const PAGE_LOADING = (
  <div className="shell section-tight">
    <div className="skel" style={{ height: 220 }} />
  </div>
)

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

/**
 * Route guard. Everything sits behind the front door; unauthenticated visitors
 * are sent to /login and returned to where they were headed once they are in.
 *
 * This is a demo gate — see src/auth.js. A guard in the client protects the
 * *view*, never the data; the backend must reject unauthenticated requests on
 * its own.
 */
function Require({ session, children }) {
  const loc = useLocation()
  if (!session) return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  return children
}

export default function App() {
  const [session, setSession] = useState(getSession)
  const loc = useLocation()

  const handleSignOut = useCallback(() => {
    signOut()
    setSession(null)
  }, [])

  const onLogin = loc.pathname === '/login'
  // The footer is the landing page's: its columns are a site map and a list of
  // evidence platforms, which belong where a visitor first arrives. The board,
  // model and compare pages end on their own content. /admin must never have
  // one: it fills the viewport and scrolls inside its own panes (`.adm-page`),
  // and a footer under that layout would put the page back into the scroll it
  // left, taking the side nav up with it.
  const onHome = loc.pathname === '/'

  return (
    <>
      <ScrollToTop />
      {!onLogin && <Nav session={session} onSignOut={handleSignOut} />}

      <main>
        <Suspense fallback={PAGE_LOADING}>
        <Routes>
          {/* signing in drops you on the landing page */}
          <Route
            path="/login"
            element={session ? <Navigate to="/" replace /> : <Login onSignedIn={setSession} />}
          />

          <Route path="/"        element={<Require session={session}><Landing /></Require>} />
          <Route path="/board/*" element={<Require session={session}><Board /></Require>} />
          <Route path="/blogs/*" element={<Require session={session}><Blogs /></Require>} />
          <Route path="/models"     element={<Require session={session}><Models /></Require>} />
          {/* BEFORE `/models/*`, and outside it. The comparison is entered from
              the models list, but its own URL is `/compare?ids=…`: a model id
              contains a slash (`anthropic/claude-fable-5-1`), so a path segment
              could not carry two of them, and the SEO plan's comparison
              keywords all target /compare. */}
          <Route path="/compare"    element={<Require session={session}><Compare /></Require>} />
          <Route path="/models/*"   element={<Require session={session}><ModelDetail /></Require>} />
          <Route path="/admin"   element={<Require session={session}><Admin /></Require>} />
          <Route path="/admin/blog-logs"  element={<Require session={session}><BlogLogs /></Require>} />

          {/* NOT A REDIRECT (SEO item 7): an unknown address says so, at that address. */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense>
      </main>

      {onHome && <Footer />}
    </>
  )
}
