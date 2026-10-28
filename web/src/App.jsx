import { Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom'
import { Suspense, lazy, useCallback, useEffect, useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import Landing from './routes/Landing'
import { getSession, signOut } from './auth'
import NotFound from './components/NotFound'

/**
 * ROUTE-LEVEL CODE SPLITTING (SEO item 10, 2026-10-09). The whole app was one
 * 544.6 kB script (159.3 kB gzipped) that every visitor downloaded before the
 * first paint - the admin console included, which a reader never opens. The
 * front door stays in the first download: the shell and Landing. Every
 * other page is its own chunk, fetched when it is first visited.
 *
 * A DEPLOY REPLACES THE CHUNKS. A tab opened before it still names the old
 * files, so the import fails; this reloads ONCE to pick up the new build
 * instead of rendering nothing. The flag stops a loop: if the reload does not
 * fix it, the error is thrown and shows (rule 12), never swallowed.
 */
/** An address that moved: forwards to the new one, keeping its query, so a
 *  shared search (`?model=...`) still opens as it was sent. */
function MovedTo({ path }) {
  const { search } = useLocation()
  return <Navigate to={path + search} replace />
}

/** /catalog, /catalog/new, /catalog/model/<id> -> /ai-models, /ai-models/latest, /ai-models/<id>. */
function CatalogMoved() {
  const rest = (useParams()['*'] || '').replace(/^model\//, '').replace(/^new$/, 'latest')
  return <MovedTo path={rest ? `/ai-models/${rest}` : '/ai-models'} />
}

/** /reports/<anything> -> /reviews/<anything> (2026-10-21). */
function ReportsMoved() {
  const rest = useParams()['*'] || ''
  return <MovedTo path={rest ? `/reviews/${rest}` : '/reviews'} />
}

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

// LOGIN LEFT THE FIRST DOWNLOAD (2026-10-21): every public visitor fetched the
// sign-in page and its two animations (AuraField, OrbitHub) and none of them
// uses it. A team member waits one small request on /login instead.
const Login = page(() => import('./routes/Login'))
const Board = page(() => import('./routes/Board'))
const Blogs = page(() => import('./routes/Blogs'))
const Glossary = page(() => import('./routes/Glossary'))
const Tools = page(() => import('./routes/Tools'))
const Methodology = page(() => import('./routes/Methodology'))
const ModelPicker = page(() => import('./routes/ModelPicker'))
const Reports = page(() => import('./routes/Reports'))
const Catalog = page(() => import('./routes/Catalog'))
const Evidence = page(() => import('./routes/Evidence'))
const Discussions = page(() => import('./routes/Discussions'))
const Benchmarks = page(() => import('./routes/Benchmarks'))
const ModelDetail = page(() => import('./routes/ModelDetail'))
const Models = page(() => import('./routes/Models'))
const Compare = page(() => import('./routes/Compare'))
const TokenCounter = page(() => import('./routes/TokenCounter'))
const VramCalculator = page(() => import('./routes/VramCalculator'))
const ModelFinder = page(() => import('./routes/ModelFinder'))
const Admin = page(() => import('./routes/Admin'))
const BlogLogs = page(() => import('./routes/BlogLogs'))
const Keywords = page(() => import('./routes/Keywords'))
const PriceChanges = page(() => import('./routes/PriceChanges'))
const News = page(() => import('./routes/News'))
const KitePulse = page(() => import('./kitepulse/KitePulseSite'))

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
 * Route guard - FOR THE SIGNED-IN SURFACES ONLY (2026-10-15, Parvathi): the
 * Board, the old model pages (/models), Admin and SEO keywords. Every published page - home,
 * Blogs, Tools and the three tools, the Models pages, Compare, Discussions,
 * FAQ - opens without signing in, and reads the backend's public endpoints
 * (judge/gate.py: PUBLIC_READ_PATHS). A visitor who opens a guarded page is
 * sent to /login and returned there once signed in.
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
  // KITE PULSE IS ANOTHER PRODUCT'S SITE (kitepulse/KitePulseSite.jsx): it brings its
  // own header and footer, and the board's nav above it would make it read as
  // a board page.
  const onKitePulse = loc.pathname === '/kite-pulse' || loc.pathname.startsWith('/kite-pulse/')

  return (
    <>
      <ScrollToTop />
      {!onLogin && !onKitePulse && <Nav session={session} onSignOut={handleSignOut} />}

      <main>
        <Suspense fallback={PAGE_LOADING}>
        <Routes>
          {/* signing in returns you to the guarded page you asked for, or the
              Models list - the first of the signed-in surfaces */}
          <Route
            path="/login"
            element={session ? <Navigate to={loc.state?.from || '/models'} replace /> : <Login onSignedIn={setSession} />}
          />

          <Route path="/"        element={<Landing />} />
          <Route path="/board/*" element={<Require session={session}><Board /></Require>} />
          <Route path="/blogs/*" element={<Blogs />} />
          <Route path="/glossary/*" element={<Glossary />} />
          <Route path="/tools"       element={<Tools />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="/best-ai-model" element={<ModelPicker />} />
          <Route path="/best-ai-model/:job" element={<ModelPicker />} />
          <Route path="/alternatives/:model" element={<ModelPicker />} />
          {/* the tool was briefly "AI model finder" here; an old link still opens it */}
          <Route path="/ai-model-finder" element={<MovedTo path="/best-ai-model" />} />
          <Route path="/reviews/*"   element={<Reports />} />
          {/* THE ADDRESSES THAT SAY WHAT PEOPLE SEARCH (2026-10-21): these pages
              were /reports, /model-picker and /model-finder; an old link still
              opens and moves to the same page. */}
          <Route path="/reports/*"   element={<ReportsMoved />} />
          <Route path="/model-picker" element={<MovedTo path="/best-ai-model" />} />
          <Route path="/model-finder" element={<MovedTo path="/ai-model-pricing" />} />
          <Route path="/ai-models/*" element={<Catalog />} />
          {/* The Models pages were /catalog until 2026-10-21; an old link moves to the same page. */}
          <Route path="/catalog/*"   element={<CatalogMoved />} />
          {/* THE EVIDENCE FEED (2026-10-21, PROPOSED): public, like Reports - the
              reports behind every count, paraphrased, each with its source. */}
          <Route path="/evidence/*"  element={<Evidence />} />
          <Route path="/discussions" element={<Discussions />} />
          <Route path="/models"     element={<Require session={session}><Models /></Require>} />
          {/* BEFORE `/models/*`, and outside it. The comparison is entered from
              the models list. A model id contains a slash
              (`anthropic/claude-fable-5-1`), so the path names each model by
              the part after the provider instead - see the route below. */}
          <Route path="/compare"    element={<Compare />} />
          {/* THE READABLE ADDRESS (2026-10-20): /compare/grok-4.6-vs-gpt-6-sol,
              each model named by its own name, which is unique in the catalogue
              (compare/path.js). `?ids=` still opens and moves here. */}
          <Route path="/compare/:pair" element={<Compare />} />
          {/* Entered from the models list, beside Compare; top-level paths for the
              same reason as /compare - `/models/*` is a model id. */}
          <Route path="/token-counter" element={<TokenCounter />} />
          <Route path="/local-llm-vram-calculator" element={<VramCalculator />} />
          <Route path="/ai-model-pricing"  element={<ModelFinder />} />
          <Route path="/models/*"   element={<Require session={session}><ModelDetail /></Require>} />
          <Route path="/admin"   element={<Require session={session}><Admin /></Require>} />
          <Route path="/benchmarks" element={<Require session={session}><Benchmarks /></Require>} />
          <Route path="/seo-keywords" element={<Require session={session}><Keywords /></Require>} />
          <Route path="/price-changes" element={<Require session={session}><PriceChanges /></Require>} />
          <Route path="/news" element={<Require session={session}><News /></Require>} />
          <Route path="/keywords" element={<MovedTo path="/seo-keywords" />} />
          <Route path="/admin/blog-logs"  element={<Require session={session}><BlogLogs /></Require>} />
          {/* Signed in only: an internal preview of another product's site. */}
          <Route path="/kite-pulse/*" element={<Require session={session}><KitePulse /></Require>} />

          {/* NOT A REDIRECT (SEO item 7): an unknown address says so, at that address. */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense>
      </main>

      {onHome && <Footer />}
      {/* HOVER PREVIEWS OFF (2026-10-19, anooj): components/HoverPreview.jsx
          is kept; mounting it here again turns them back on. */}
    </>
  )
}
