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
 * `judge/app.py` has no auth route and no session concept, so there is nothing
 * to call yet. Replacing this means a real login endpoint returning an httpOnly
 * cookie, and the FastAPI app rejecting unauthenticated requests itself — a
 * guard in the browser protects the VIEW and never the data. That matters more
 * now than it did: `/ask/understand` spends money per request, so an unguarded
 * deployment is a stranger's spending endpoint. Delete this file at that point.
 *
 * (This block used to say "see API-CONTRACT.md § Auth". No such file exists in
 * this repo and no `/v1/` route does either — it was pointing at a plan, in the
 * voice of a reference.)
 */

const ACCOUNT = {
  email: 'demo@modelboard.dev',
  hash: '99235ef1c3cd59a2ad08c0621d82c1d631ca6df99a23b4472c1f46adefaf3273',
}

const KEY = 'modelboard.session'

async function sha256(text) {
  // `crypto.subtle` exists only in a SECURE CONTEXT — https, or localhost.
  // `npm run dev -- --host` and then opening http://192.168.x.x:5173 from a
  // phone or a colleague's laptop is the normal way to demo this, and there
  // `crypto.subtle` is undefined: sign-in would die on "cannot read properties
  // of undefined", which reads as a broken password rather than a browser rule.
  if (!globalThis.crypto?.subtle) {
    throw new Error(
      'Sign-in needs a secure context. Open this on http://localhost:5173 ' +
      'rather than an IP address, or serve it over https.'
    )
  }
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
