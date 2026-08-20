/**
 * DEMO GATE — NOT AUTHENTICATION.
 *
 * This exists so the preview build has a front door and so the routing and
 * guards are already wired when the real backend lands. It is not security:
 *
 *   - Anyone can read this file in the shipped bundle.
 *   - The hash below is unsalted SHA-256 of a short password, which is minutes
 *     of work for anyone who wants it. Hashing rather than storing plaintext
 *     only keeps the password out of a casual `view-source`.
 *   - Nothing is verified anywhere but the browser, so the check can be skipped
 *     entirely from the console.
 *
 * Replace with POST /v1/auth/login returning an httpOnly session cookie.
 * See API-CONTRACT.md § Auth. Delete this file at that point.
 */

const ACCOUNT = {
  email: 'demo@modelboard.dev',
  hash: '99235ef1c3cd59a2ad08c0621d82c1d631ca6df99a23b4472c1f46adefaf3273',
}

const KEY = 'modelboard.session'

async function sha256(text) {
  const bytes = new TextEncoder().encode(text)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export async function signIn(email, password) {
  const hash = await sha256(password)

  // Both checks run either way, so a wrong address and a wrong password take
  // the same path — a faster "no such user" reply is an enumeration oracle.
  const emailOk = email.trim().toLowerCase() === ACCOUNT.email
  const passOk = hash === ACCOUNT.hash
  if (!emailOk || !passOk) throw new Error('Those details do not match an account.')

  const session = { email: ACCOUNT.email }
  sessionStorage.setItem(KEY, JSON.stringify(session))
  return session
}

export function signOut() {
  sessionStorage.removeItem(KEY)
}

/** Session lives in sessionStorage, so closing the tab ends it. */
export function getSession() {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}
