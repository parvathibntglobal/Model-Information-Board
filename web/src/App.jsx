import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import Landing from './routes/Landing'
import Ask from './routes/Ask'
import Board from './routes/Board'
import Articles from './routes/Articles'
import ModelDetail from './routes/ModelDetail'
import Models from './routes/Models'
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

  return (
    <>
      <ScrollToTop />
      {!onLogin && <Nav session={session} onSignOut={handleSignOut} />}

      <main>
        <Routes>
          {/* signing in drops you on the landing page; you go on to Ask from there */}
          <Route
            path="/login"
            element={session ? <Navigate to="/" replace /> : <Login onSignedIn={setSession} />}
          />

          <Route path="/"        element={<Require session={session}><Landing /></Require>} />
          <Route path="/ask"     element={<Require session={session}><Ask /></Require>} />
          <Route path="/articles" element={<Require session={session}><Articles /></Require>} />
          <Route path="/board"   element={<Require session={session}><Board /></Require>} />
          <Route path="/models"     element={<Require session={session}><Models /></Require>} />
          <Route path="/models/*"   element={<Require session={session}><ModelDetail /></Require>} />
          <Route path="/admin"   element={<Require session={session}><Admin /></Require>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {!onLogin && <Footer />}
    </>
  )
}
