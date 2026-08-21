/**
 * The real backend. One module, one place to look.
 *
 * Base is `/api`, proxied to the FastAPI app in dev (see vite.config.js) and
 * set with VITE_API_URL in a deployed build.
 *
 * Endpoints, as they actually exist in judge/app.py:
 *
 *   GET  /health                     no database needed
 *   GET  /capabilities               no database needed
 *   POST /ask/requirements           no database needed — deterministic Q3
 *   POST /ask/revise                 no database needed — Q3 after an edit
 *   POST /ask/understand             needs OPENROUTER_API_KEY — the one LLM call
 *   GET  /models/{id}                needs the database
 *   GET  /capabilities/{key}         needs the database
 *   GET  /filtered  /coverage  /changelog    need the database
 *
 * The database-backed reads answer 503 when DATABASE_URL is unset, and the
 * backend is explicit that this is not the same as a board with nothing on it.
 * `BoardUnreadable` keeps that distinction all the way to the screen.
 */

const BASE = import.meta.env.VITE_API_URL || '/api'

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

/** 503 from a read surface: the board cannot be read, which is not emptiness. */
export class BoardUnreadable extends ApiError {
  constructor(message, body) {
    super(message, 503, body)
    this.name = 'BoardUnreadable'
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError('Cannot reach the API. Is the backend running on port 8000?', 0, null)
  }

  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }

  if (!res.ok) {
    // FastAPI puts the message in `detail`; the backend writes real sentences there
    const detail = (data && (data.detail || data.message)) || `Request failed (${res.status})`
    if (res.status === 503) throw new BoardUnreadable(detail, data)
    throw new ApiError(detail, res.status, data)
  }
  return data
}

/* ------------------------------------------------------------------ reads */

export const health = () => request('/health')
export const listCapabilities = () => request('/capabilities')
export const capabilityPage = (key) => request(`/capabilities/${encodeURIComponent(key)}`)
/**
 * Model ids can contain a slash — `google/gemini-2.5-flash`. The handoff is
 * explicit that the slash must NOT be percent-encoded, so each segment is
 * encoded and the separators are kept.
 *
 * The backend route is `{model_version_id:path}` as of ae280be, so a
 * vendor-prefixed id resolves. Every id the registry actually holds today is
 * an `mv_…` hash with no slash in it, but the helper handles both.
 */
export const modelPath = (id) => String(id).split('/').map(encodeURIComponent).join('/')
export const modelPage = (id) => request(`/models/${modelPath(id)}`)

/**
 * The registry with what each provider advertises — price, context window,
 * feature flags. One call; the roster used to be reconstructed from twelve
 * capability pages.
 *
 * None of this is evidence. It is what a vendor says about itself, and the UI
 * has to keep saying so: no amount of cheapness makes a model recommendable
 * here, and a page that puts price beside consensus without marking the
 * difference is the one mistake this board exists to avoid.
 */
export const listModels = () => request('/models')
export const filteredPage = (limit = 200) => request(`/filtered?limit=${limit}`)
export const coveragePage = () => request('/coverage')
export const changelogPage = (days = 30) => request(`/changelog?days=${days}`)

/* ------------------------------------------------------------------ ask */

/**
 * Q3. Deterministic — the same task always produces the same requirements.
 * Needs no API key and no database, which is why it is the page that works
 * end to end today.
 */
export const askRequirements = (payload) =>
  request('/ask/requirements', { method: 'POST', body: payload })

/** Q3 again, over a profile the user has corrected. No model runs. */
export const askRevise = (profile, acceptedAssumptions = []) =>
  request('/ask/revise', {
    method: 'POST',
    body: { profile, accepted_assumptions: acceptedAssumptions },
  })

/** Q1 — the LLM call. 429 when the extraction budget is spent, 422 on refusal. */
export const askUnderstand = (text, shape = 'task') =>
  request('/ask/understand', { method: 'POST', body: { text, shape } })

/**
 * OUR spend against OUR shared daily cap — not OpenRouter's ceilings, which are
 * different numbers on a different schedule. Covers both LLM stages under one
 * limit; see judge/spend_ledger.py.
 */
export const adminUsage = (hours = 24, days = 14) =>
  request(`/admin/usage?hours=${hours}&days=${days}`)

/* ------------------------------------------------------------------ display */

export const fmtInt = (n) =>
  n == null ? '—' : new Intl.NumberFormat('en-US').format(n)

export const fmtTokens = (n) => {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`
  if (n >= 1000) return `${Math.round(n / 1000)}k`
  return String(n)
}

/**
 * Price, in USD per million tokens.
 *
 * Three states that must not collapse into each other, which is rule 6 at the
 * last layer before a human reads it:
 *
 *   null → "no rate"   the five routers, which dispatch to other models
 *   0    → "Free"      ten models that genuinely cost nothing
 *   n    → "$0.075"    everything else
 *
 * Returning "$0.00" for null would put the word free on models that bill.
 */
export const fmtPrice = (n) => {
  if (n == null) return 'no rate'
  if (n === 0) return 'Free'
  // A rate below the rounding floor must not become "$0" — that is the NULL
  // mistake wearing a different hat, a real charge displayed as no charge.
  // Today's cheapest is $0.002/Mtok so nothing hits this, but providers ship
  // sub-$0.001 rates and the failure would be silent when one does.
  if (n < 0.001) return '<$0.001'
  if (n < 1) return `$${n.toFixed(3).replace(/0+$/, '').replace(/\.$/, '')}`
  return `$${n % 1 === 0 ? n : n.toFixed(2)}`
}

/** Backend capability keys are dotted; this is the human label. */
export const capLabel = (key) =>
  (key || '')
    .split('.')
    .pop()
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())

export const TIER = {
  1: { label: 'Trivial', note: 'almost anything qualifies — pick on price' },
  2: { label: 'Small', note: 'many cheap models qualify' },
  3: { label: 'Moderate', note: 'mid-tier and up' },
  4: { label: 'Hard', note: 'few models; cost is secondary' },
  5: { label: 'Frontier', note: 'one or two, or nothing does this reliably yet' },
}

export const ERROR_COST = {
  experimental: { tone: 'mute', note: 'a wrong answer costs a rerun' },
  internal: { tone: 'info', note: 'errors get noticed internally' },
  'customer-facing': { tone: 'warn', note: 'requires praised, not merely uncriticised' },
  irreversible: { tone: 'fail', note: 'writes, sends, payments — unevidenced picks are suppressed' },
}
