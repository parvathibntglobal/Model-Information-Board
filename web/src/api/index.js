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

import { sessionToken } from '../auth'

const BASE = import.meta.env.VITE_API_URL || '/api'

/**
 * Sent as `Authorization: Bearer` when the API has a token configured.
 *
 * THIS IS NOT A SECRET THE BROWSER CAN KEEP. It ships in the bundle, exactly
 * like the demo hash in auth.js, so it authenticates the DEPLOYMENT and not the
 * person - it stops the internet at large reading the board, and stops nothing
 * that a viewer of this page could not already do. Per-user identity needs a
 * session the server issues; see the note at the top of src/auth.js.
 *
 * Left unset for local work, where the API is open in development anyway.
 */
const TOKEN = import.meta.env.VITE_API_TOKEN || ''

/**
 * The signed token from signing in, read fresh on every request.
 *
 * Read at CALL TIME rather than captured at module load: the user is signed
 * out when this module first evaluates, so a captured value would be '' for
 * the life of the tab and every request after sign-in would go unauthenticated.
 */
const bearer = () => sessionToken() || TOKEN

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
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(bearer() ? { Authorization: `Bearer ${bearer()}` } : {}),
      },
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

// ── Tracked registry (UI-only narrowing) ─────────────────────────────────────
// The board is tracking exactly two models for now, and shows no evidence until
// engineer reports land for them. The shared database still holds the full
// 342-model registry and every evidence cell — this narrows only what the UI
// reads, and writes nothing. Delete this block (and the three overrides below)
// to restore the live registry straight from the API.
const TRACKED = [
  {
    model_version_id: 'openai/gpt-6-astra', canonical_id: 'openai/gpt-6-astra',
    display_name: 'GPT 6 Astra', provider: 'OpenAI',
    price_in: null, price_out: null, advertised_context: null,
    state: 'unreported', phrases: [], conditional: false, voices: 0,
    // No `cells`/`published` here: the board renders discovered board_entry rows
    // (GET /board), and there is no cell or publication surface in the UI.
    evidence: { reports: 0, sections: [] },
  },
  {
    model_version_id: 'anthropic/claude-fable-5-1', canonical_id: 'anthropic/claude-fable-5-1',
    display_name: 'Claude Fable 5.1', provider: 'Anthropic',
    price_in: null, price_out: null, advertised_context: null,
    state: 'unreported', phrases: [], conditional: false, voices: 0,
    // No `cells`/`published` here: the board renders discovered board_entry rows
    // (GET /board), and there is no cell or publication surface in the UI.
    evidence: { reports: 0, sections: [] },
  },
]
const TRACKED_PAGE = { has_more: false, returned: TRACKED.length, limit: 500, offset: 0 }

export const capabilityPage = (key) =>
  Promise.resolve({
    key,
    failure_mode: 'silent',
    summary: 'No tracked model has reports for this capability yet.',
    models: [],
    count: 0,
    page: { has_more: false, returned: 0, limit: 500, offset: 0 },
  })
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
export const modelPage = (id) => {
  const raw = decodeURIComponent(String(id))
  const m = TRACKED.find((x) => x.model_version_id === raw || x.canonical_id === raw)
  return Promise.resolve({
    model_version_id: m ? m.model_version_id : raw,
    display_name: m ? m.display_name : raw,
    provider: m ? m.provider : null,
    price_in: m ? m.price_in : null,
    price_out: m ? m.price_out : null,
    advertised_context: m ? m.advertised_context : null,
    tracked: Boolean(m),
    summary: m
      ? `${m.display_name} is tracked. No engineer reports are in the registry yet, so every capability below stays undiscussed rather than judged.`
      : 'This model is not in the tracked set.',
    unbound_phrases: [],
    capabilities: [],
    quotes: {},
  })
}

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
export const listModels = () =>
  Promise.resolve({
    count: TRACKED.length,
    priced_at: null,
    summary: 'Two models are being tracked. Neither has engineer reports in the registry yet — capabilities stay undiscussed until someone reports one.',
    page: TRACKED_PAGE,
    models: TRACKED,
  })

/**
 * Every page of a list endpoint, followed to the end.
 *
 * `/models` and `/capabilities/{key}` now page at 100 by default. A client that
 * takes the first page and renders it is the worst outcome available here: the
 * roster would silently become "the first 100 of 342" with nothing on screen
 * saying so, and "no model matches" would start meaning "not in the first
 * hundred". Pagination that a caller ignores is worse than none.
 *
 * `has_more` is read from the response rather than inferred from
 * `returned === limit`, which is wrong on a last page that happens to be full.
 * The loop is bounded because a server that always says `has_more` should stop
 * a UI, not hang it.
 */
export const fetchAll = async (fetchPage, key = 'models') => {
  const first = await fetchPage(500, 0)
  const rows = [...(first[key] || [])]
  let meta = first.page
  let guard = 0

  while (meta?.has_more && guard++ < 40) {
    const next = await fetchPage(500, rows.length)
    rows.push(...(next[key] || []))
    meta = next.page
    if (!next[key]?.length) break     // no progress: stop rather than spin
  }

  return { ...first, [key]: rows, page: meta, truncated: Boolean(meta?.has_more) }
}
/**
 * Per-model fetch. Kicks off this model's evidence pipeline (harvest → …) in a
 * subprocess and returns a run id; poll fetchLog(runId) for live per-stage
 * progress. Append-only — it adds this model's rows, never edits existing ones.
 */
export const startFetch = (modelVersionId) =>
  request('/fetch/start', { method: 'POST', body: { model_version_id: modelVersionId } })
/**
 * Ask a running fetch to stop at its next stage boundary.
 *
 * COOPERATIVE, NOT A KILL. The backend writes a stop-request file the
 * subprocess notices in `Progress.stage()`, so the run ends between things it
 * was going to report and writes its own `stopped` end record rather than
 * vanishing. Nothing is undone: every write in the pipeline is an append, so a
 * stopped run holds LESS evidence, never wrong evidence.
 *
 * `was_running` comes back false when the run had already finished, so the UI
 * can stop saying "stopping…" over a run that ended a minute ago.
 */
export const stopFetch = (runId) =>
  request('/fetch/stop', { method: 'POST', body: { run_id: runId } })
export const fetchLog = (runId) =>
  request(`/fetch/log?run_id=${encodeURIComponent(runId)}`)
export const fetchRuns = (modelVersionId) =>
  request(`/fetch/runs?model_version_id=${encodeURIComponent(modelVersionId)}`)

export const filteredPage = (limit = 200) => request(`/filtered?limit=${limit}`)
/**
 * The board's three sections, DISCOVERED by the classifier rather than chosen
 * from a list. Returns { jobs, caps, mets, counts, report_counts_are_a_floor }.
 *
 * `reports` on each section IS A FLOOR and the UI must say so: the vocabulary
 * is open, so one section can arrive under two names until the duplicates are
 * merged. Rendering it as an exact total would overstate what was counted.
 */
export const boardPage = () => request('/board')

export const coveragePage = () => request('/coverage')
export const changelogPage = (days = 30) => request(`/changelog?days=${days}`)

/**
 * The landing page's FAQ, from `contract/faq.yaml`.
 *
 * NEEDS NO DATABASE, which is why the FAQ renders even when the board cannot
 * be read — half of what it explains is why an empty board is a real state.
 *
 * Each question carries `established`. Three of the eleven ask something about
 * MODELS rather than about how the board works, and the landing demo answered
 * those from demo data ("$0.14 in and $0.28 out"). Those arrive
 * `established: false` with an answer that says what the board cannot yet
 * support, and the page must render that answer rather than the demo's.
 */
export const faqPage = () => request('/faq')

/**
 * Two or three models side by side. `ids` is an array of model_version_ids.
 *
 * The response splits `advertised` from `reported` and never merges them: a
 * price is the vendor's claim about itself, a report count is what somebody
 * found. It also returns `unsourced` — the rows the landing demo showed that
 * this board has no source for (licence, benchmark standing, the hand-written
 * blurb) — so the page can say what is missing instead of quietly showing a
 * shorter table.
 */
export const comparePage = (ids) =>
  request(`/compare?ids=${encodeURIComponent((ids || []).join(','))}`)

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
 * Q4–Q7. The requirement, ranked against real cells. No model runs; the
 * justification is bound to quote ids. Abstains — and names the missing
 * capability — when no model has evidence clearing the bar.
 */
export const askRecommend = (payload) =>
  request('/ask/recommend', { method: 'POST', body: payload })

/**
 * OUR spend against OUR shared daily cap — not OpenRouter's ceilings, which are
 * different numbers on a different schedule. Covers both LLM stages under one
 * limit; see judge/spend_ledger.py.
 */
export const adminUsage = (hours = 24, days = 14) =>
  request(`/admin/usage?hours=${hours}&days=${days}`)

/**
 * The evidence pipeline, stage by stage. Counts (not money): how many rows sit
 * in each stage grouped by its status column, plus the job_run ledger for the
 * last pass. An empty stage reports as not-yet-run, never a clean zero.
 */
export const pipelineStatus = () => request('/admin/pipeline')

/**
 * Capabilities the extractor PROPOSED that none of the current keys name. The
 * model proposes, an admin rules. Adopting one is a contract/capabilities.yaml
 * PR, never a write here — these record the decision and its evidence.
 */
/**
 * Discovered board sections awaiting CONSOLIDATION, not publication.
 *
 * The distinction matters at the call site: an unruled row here is ALREADY on
 * the board, so this list is not a queue of things waiting to appear. It exists
 * because an open vocabulary produces duplicates - one section arriving under
 * two slugs - and only a person can decide two words mean one thing.
 */
/**
 * What has been said about ONE model, grouped by discovered section.
 *
 * Not a slice of the board payload: the board groups by section and this groups
 * by model, so deriving one from the other would make a model page move whenever
 * the board changed how it sorts. Same rows, asked a different question.
 *
 * Three empty sections is a real answer — a tracked model nobody has discussed —
 * and the page renders it as an absence rather than a spinner that never ends.
 */
export const modelEvidence = (id) => request(`/models/${modelPath(id)}/evidence`)

export const boardEntries = () => request('/admin/board-entries')

export const ruleBoardEntry = (section, slug, ruling, ruling_target = null) =>
  request('/admin/board-entries/rule', {
    method: 'POST',
    body: { section, slug, ruling, ruling_target },
  })

export const unruleBoardEntry = (section, slug) =>
  request('/admin/board-entries/unrule', {
    method: 'POST',
    body: { section, slug, ruling: 'adopted' },
  })

export const capabilityCandidates = () => request('/admin/capability-candidates')
export const ruleCapability = (proposed_key, ruling, ruling_target = null) =>
  request('/admin/capability-candidates/rule', {
    method: 'POST',
    body: { proposed_key, ruling, ruling_target },
  })
export const editCapability = (proposed_key, { new_key = null, new_definition = null }) =>
  request('/admin/capability-candidates/edit', {
    method: 'POST',
    body: { proposed_key, new_key, new_definition },
  })
export const deleteCapability = (proposed_key) =>
  request('/admin/capability-candidates/delete', {
    method: 'POST',
    body: { proposed_key },
  })

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
