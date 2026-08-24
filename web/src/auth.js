/**
 * Sign-in. The credential is on the server; this holds only a token.
 *
 * WHAT THIS REPLACED, and why it had to go. This file used to contain:
 *
 *     const ACCOUNT = { email: 'demo@modelboard.dev', hash: '99235ef1…' }
 *
 * An unsalted SHA-256 of a short password, shipped in the bundle and compared
 * in the browser. Three separate problems, and the third is the one that
 * matters: it was READABLE by every visitor, it was CRACKABLE in minutes, and
 * the check ran on the attacker's own machine — so passing it was a matter of
 * calling `signIn` differently, or setting the sessionStorage key by hand.
 * A guard in the client protects the view. It never protected the data.
 *
 * Now: the password is posted once to `POST /auth/login`, checked against a
 * PBKDF2 hash in the server's `.env`, and what comes back is a signed token
 * with an expiry. The browser never holds anything that proves who you are for
 * longer than the token lasts, and nothing in the bundle identifies the
 * account. `judge/gate.py` accepts that token on every other route, so the API
 * is closed rather than the pages merely being hidden.
 *
 * WHAT IS STILL NOT TRUE HERE. One account, no roles, no revocation before
 * expiry — a signed token cannot be withdrawn, only outlived. That is stated
 * in `judge/login.py` beside the choice. Real per-user accounts need a session
 * table; this is the smallest honest thing above a lie.
 */

const KEY = 'modelboard.session'
const BASE = import.meta.env.VITE_API_URL || '/api'

/**
 * Sign in against the API.
 *
 * Every failure reads the same to the caller, because the server answers the
 * same way to a wrong address and a wrong password — a message that
 * distinguishes them tells a stranger which half they got right.
 */
export async function signIn(email, password) {
  let res
  try {
    res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    })
  } catch {
    throw new Error('Cannot reach the API. Is the backend running on port 8000?')
  }

  const body = await res.json().catch(() => null)

  if (!res.ok) {
    // 503 means sign-in is not CONFIGURED, which is a different thing from
    // wrong details, and the server says which variables are missing. Passing
    // that through beats "those details do not match" when the details were
    // fine and the server has no account at all.
    throw new Error(body?.detail || `Sign-in failed (${res.status})`)
  }

  const session = {
    email: body.email,
    token: body.token,
    expiresAt: body.expires_at,     // unix seconds, from the server
  }
  sessionStorage.setItem(KEY, JSON.stringify(session))
  return session
}

export function signOut() {
  sessionStorage.removeItem(KEY)
}

/**
 * The stored session, or null.
 *
 * EXPIRY IS CHECKED HERE TOO, even though the server rejects a stale token
 * anyway. Without it a returning visitor sees the whole shell render and then
 * every panel fail with 401 — the app looks broken rather than signed out.
 * The client check is for the UX; the server check is the one that matters,
 * and clock skew only ever makes this side sign you out slightly early.
 */
export function getSession() {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    const session = JSON.parse(raw)
    if (!session?.token) return null
    if (session.expiresAt && session.expiresAt * 1000 <= Date.now()) {
      sessionStorage.removeItem(KEY)
      return null
    }
    return session
  } catch {
    return null
  }
}

/** The bearer the API client sends, or '' when signed out. */
export function sessionToken() {
  return getSession()?.token || ''
}
