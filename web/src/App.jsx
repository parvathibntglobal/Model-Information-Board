import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import Landing from './routes/Landing'
import Board from './routes/Board'
import Blogs from './routes/Blogs'
import ModelDetail from './routes/ModelDetail'
import Models from './routes/Models'
import Compare from './routes/Compare'
import Admin from './routes/Admin'
import Login from './routes/Login'
import { getSession, signOut } from './auth'

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
  // THE ONE ROUTE THAT IS NOT A DOCUMENT. /admin fills the viewport and scrolls
  // inside its own panes, so that its side nav cannot move - see `.adm-page`.
  // A footer under a viewport-locked layout would put the page back into the
  // scroll it just left, and the nav would ride up with it again.
  const onAdmin = loc.pathname === '/admin'

  return (
    <>
      <ScrollToTop />
      {!onLogin && <Nav session={session} onSignOut={handleSignOut} />}

      <main>
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

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {!onLogin && !onAdmin && <Footer />}
    </>
  )
}
