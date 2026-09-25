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
import { cached } from './cache'

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

// ⚠ NOTHING HERE READS THE CLOSED CAPABILITY VOCABULARY ANY MORE, ruled
//   2026-09-24. `listCapabilities`, `capabilityPage` and `capLabel` are gone:
//   they served `cell.capability_key`, the ratified twelve from the first
//   plan, and measured that day 0 of 196 models on the roster carried a
//   non-empty list — every cell is `insufficient` and e5.5 writes none.
//
//   The board's own open sections (`board_entry.slug`) are what this UI
//   reads. `/capabilities` still answers; no page asks it.

// ── Tracked registry (UI-only narrowing) ─────────────────────────────────────
// The board is tracking exactly two models for now, and shows no evidence until
// engineer reports land for them. The shared database still holds the full
// 342-model registry and every evidence cell — this narrows only what the UI
// reads, and writes nothing. Delete this block (and the three overrides below)
// to restore the live registry straight from the API.
//
// IT NOW NARROWS THE LIVE ROSTER INSTEAD OF REPLACING IT, AND THAT WAS A REAL
// DEFECT RATHER THAN A STYLE CHOICE. `listModels` used to resolve a hardcoded
// two-element array, so the page read "2 models in the registry, 0 with any
// evidence" off two literals and NOTHING WRITTEN TO THE DATABASE COULD EVER
// CHANGE IT. A fetch that harvested, extracted and stored 13 board entries for
// minimax/minimax-m3 left the page identical - and the page was not wrong
// about what it had been handed; it had been handed a constant.
//
// The literals also had to state each model's price, context and evidence
// count - figures with no source, which go stale the moment anything is
// fetched (rule 3: a displayed number is counted or measured). Filtering the
// live roster keeps the narrowing and removes the invention.
// The tracked set moved to `contract/tracked_models.yaml`.
//
// It was a Set here, matched against both `model_version_id` and `canonical_id`
// - correct, and the right size for four models. Thirty needs three things a
// Set cannot hold: a model the registry does not carry at all, WHY its rate is
// absent, and the order the page shows them in. All three now come from the
// contract, and the backend joins them to the registry row.
//
// The dual-id matching it did is not lost: the backend indexes by both fields
// for exactly the reason recorded here - a polled model carries an `mv_` id and
// its canonical id separately, and matching one field would drop the other kind.

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
/**
 * The tracked set, chosen by `contract/tracked_models.yaml` and joined to the
 * registry by the backend.
 *
 * WHAT CHANGED AND WHY, because #292 had just replaced a hardcoded array with
 * this client-side filter and the filter was the right shape for four models.
 * It does not carry thirty. Three things the set could not express:
 *
 *   - A MODEL THE REGISTRY DOES NOT HOLD. 17 of the 30 are image, video and
 *     speech models; the OpenRouter poll carries none of them, so a filter over
 *     `/models` drops them silently and the page is shorter than the list it is
 *     built from. A missing row reads as "not tracked" rather than "no rate is
 *     published for this kind", and those are opposite claims (rule 6).
 *   - WHY a rate is absent. `no rate` on a text model means the provider has not
 *     published one; on an image model it means the column is in the wrong unit.
 *     `tracked_kind` carries that distinction.
 *   - The ORDER. The four the board holds evidence for lead the page, and that
 *     is editorial.
 *
 * And the set lived in the frontend, which is where rule 5 says configuration
 * does not go: `contract/` is versioned and reviewable, a constant in a bundle
 * is neither - which is exactly how the hosted build and the local one came to
 * disagree about how many models existed.
 *
 * `?tracked=1` is ADDITIVE on the backend. Plain `/models` still returns all
 * 344, so nothing that wanted the catalogue lost it.
 */
export const listModels = async (limit = 100, offset = 0) => {
  const data = await request(`/models?tracked=1&limit=${limit}&offset=${offset}`)
  // ⚠ A BACKEND THAT IGNORES `tracked` MUST NOT LOOK LIKE ONE THAT HONOURED IT.
  //
  // FastAPI drops unknown query parameters silently, so a server older than the
  // parameter answers `?tracked=1` with the WHOLE REGISTRY and a 200. That
  // happened: the page rendered 344 rows and nothing anywhere said the filter
  // had not been applied - it simply looked like the tracked set had grown by
  // 314. The previous version filtered client-side and so could not fail this
  // way; moving the filter to the server removed a check nobody had noticed was
  // one.
  //
  // `tracked_kind` is the tell. The tracked endpoint puts it on every row and
  // the plain roster puts it on none, so its absence across the whole page
  // means the flag did not land. Refusing is rule 4: a filter that silently did
  // not happen is worse than a page that says it could not.
  const models = data.models || []
  const honoured = models.length === 0 || models.some((m) => m.tracked_kind)
  if (!honoured) {
    throw new Error(
      `The registry page asked for the tracked models and the server returned ` +
      `all ${data.count} instead, which means it does not know the \`tracked\` ` +
      `parameter yet. Showing the whole registry here would misread as the ` +
      `tracked set having grown. Restart the backend so it picks up the change.`
    )
  }
  return data
}

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
 * from a list. Returns { jobs, caps, mets, counts, report_counts_are_a_floor,
 * grouped, parent_coverage }.
 *
 * `grouped` is the SAME leaves under their parent headings - `{jobs, caps,
 * mets}`, each a list of `{kind:'parent', name, leaves, children}` or
 * `{kind:'leaf', …}`. It is additive: `caps`/`mets`/`jobs` are unchanged and
 * still authoritative for anything that looks a leaf up by slug.
 *
 * `best_for` is DELIBERATELY UNGROUPED (#412), so `grouped.jobs` comes back as
 * flat leaves with `parent: null` - confirmed against staging rather than
 * assumed, 74 rows, 0 parents.
 *
 * `parent_coverage` is computed per request and MUST NOT be copied into the
 * UI as a literal: the ungrouped count read 19, 20 and 21 within one day.
 *
 * `reports` on each section IS A FLOOR and the UI must say so: the vocabulary
 * is open, so one section can arrive under two names until the duplicates are
 * merged. Rendering it as an exact total would overstate what was counted.
 */
export const boardPage = () => request('/board')

export const coveragePage = () => request('/coverage')

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

// Every prompt this project sends to a model, COMPOSED by the backend from the
// real builders rather than transcribed. A copy in the frontend would drift the
// first time somebody edits a prompt and not this file, and then the page would
// be confidently wrong about the one thing it exists to show.
export const adminPrompts = () => cached('prompts', () => request('/admin/prompts'))

// CACHED, like the three reference surfaces beside it. Each is derived from a
// contract file or the registry, so nothing a reader does on this page can
// change one - and the admin page remounts a section on every click, so without
// this each visit paid the full remote round trip again. Runs, Usage, Database
// and Board sections are deliberately NOT cached: see web/src/api/cache.js.
//
// Every platform the harvest reaches, read from `contract/sources.yaml` - the
// same file the harvest reads. Whether an arm uses a key is a BOOLEAN in this
// payload; no key, fingerprint or prefix is in it.
export const adminSources = () => cached('sources', () => request('/admin/sources'))

// What each fetch stage does, in words. The LIST is parsed from the file that
// emits the stages and the WORDS come from contract/pipeline_stages.yaml, so a
// new stage shows up described as undescribed rather than silently missing.
// Carries no counts - those are on the fetch log, attached to their run.
export const adminStages = () => cached('stages', () => request('/admin/stages'))

// The search terms each platform is actually sent, per tracked model. Composed
// through the same `_variants_for` the harvest calls, and sliced by each arm's
// real budget - so these are the terms that would go out on the next fetch.
export const adminKeywords = () => cached('keywords', () => request('/admin/keywords'))

// What adding or dropping a tracked model would mean. WRITES NOTHING - it
// derives the spellings, counts what the corpus attests, finds alias collisions
// and composes the exact contract entry, and a person commits it.
//
// The board's model list is versioned config (rule 5). A button that wrote it
// from here would put it in two places that can disagree, and on the hosted
// deployment the filesystem is ephemeral, so the YAML edit would die at the next
// deploy while any rows it caused survived.
export const proposeModel = ({ action, registry = '', name = '', kind = 'text' }) =>
  request(
    `/admin/models/propose?action=${encodeURIComponent(action)}`
    + `&registry=${encodeURIComponent(registry)}`
    + `&name=${encodeURIComponent(name)}&kind=${encodeURIComponent(kind)}`,
  )

// Every fetch run this database has seen, newest first and across machines.
// The host is a RELATION ("this machine" / "another host"), never a name.
//
// `looks_dead` is a MEASUREMENT, not a status: a run with no end record may be
// a corpse, since a killed process writes nothing, and the missed heartbeats
// beside it are the evidence for that reading.
export const adminRuns = (limit) => request(`/admin/runs${limit ? `?limit=${limit}` : ''}`)

// Which database this is, what is in it, and whether the schema matches the
// migration files. The target is `host:port/dbname` from `writeguard.describe`
// - there is no credential in this payload and none can be derived from it.
export const adminDatabase = () => request('/admin/database')

// The signed-in account, the stack this runs on, the running commit and every
// operational cap - with whether each cap is the default or an override.
//
// CREDENTIALS ARE BOOLEANS HERE. `set` / `not set`, never a value, a prefix or
// a hash, in the payload as much as on the page.
export const adminSettings = () => request('/admin/settings')

// `entry_ids` IS OMITTED, NOT EMPTIED, when the whole section is meant.
//
// The backend treats `null` as "the whole slug" and `[]` as a mistake, because
// those are different intents and only one is safe to guess at: a caller that
// sent [] believed it had a selection. Sending `[]` here would turn "I ticked
// nothing yet" into "decline this capability", so the distinction is preserved
// across the wire rather than flattened in the client.
export const ruleBoardEntry = (section, slug, ruling, ruling_target = null, entry_ids = null) =>
  request('/admin/board-entries/rule', {
    method: 'POST',
    body: { section, slug, ruling, ruling_target, entry_ids: entry_ids?.length ? entry_ids : null },
  })

export const unruleBoardEntry = (section, slug, entry_ids = null) =>
  request('/admin/board-entries/unrule', {
    method: 'POST',
    body: { section, slug, ruling: 'adopted', entry_ids: entry_ids?.length ? entry_ids : null },
  })

// ⚠ NOTHING HERE REACHES `/admin/capability-candidates`, ON PURPOSE. Four
//   functions did — list, rule, edit, delete — and no component ever called
//   them. Rather than wire them up, the surface was ruled unwanted on
//   2026-09-24: `capability_key` is the closed twelve from the first plan,
//   and discovery moved to `board_entries`, whose vocabulary is open. Board
//   sections is the review surface; capabilities get no separate one.
//
//   The endpoint still answers and the extractor still proposes into it, so
//   this is a client that declines to call a live route rather than a route
//   that went away. The upstream half — the prompt field and the endpoint —
//   is #434, not deleted from this side.

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
