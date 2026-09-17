/**
 * A read-through cache for the admin page's REFERENCE surfaces.
 *
 * WHY THE ADMIN PAGE FELT SLOW EVEN AFTER THE QUERIES GOT FASTER. It mounts one
 * section at a time and remounts on every switch, so each click refetches from
 * scratch — and the database is remote. Measured 2026-09-17: 1.58s to open a
 * connection and 250ms per round trip, before any work. Clicking away and back
 * paid the whole cost again for an answer that had not changed.
 *
 * ⚠ ONLY THE SURFACES THAT CANNOT GO STALE DURING A SESSION ARE CACHED, and the
 *   distinction is the whole safety of this file:
 *
 *     Sources, Evidence stages, Prompts, Keywords  — derived from contract files
 *       and the registry. They change when somebody edits YAML and redeploys,
 *       which a reader cannot do from this page.
 *
 *     Runs, Usage, Database, Board sections  — NOT cached, at any TTL. These
 *       report live state, two of them poll, and one of them is a surface you
 *       act on. A stale reading on an operations page is worse than a spinner,
 *       which is the same reason each panel refetches on mount in the first
 *       place.
 *
 * A cache that lies is worse than a slow page, so this one is deliberately
 * small: it never serves an entry past its TTL, it never serves an error, and
 * `bust()` exists for the caller that knows better.
 */

const entries = new Map()

//: Long enough that clicking between sections is free, short enough that a
//: redeploy is picked up by the time anyone has read one panel. These do not
//: change from this page, so the number is about a deploy, not about staleness.
const DEFAULT_TTL_MS = 5 * 60 * 1000

export function cached(key, load, { ttl = DEFAULT_TTL_MS } = {}) {
  const hit = entries.get(key)
  if (hit && Date.now() - hit.at < ttl) return hit.promise

  const promise = load().catch((err) => {
    // A FAILURE IS NEVER CACHED. Caching one would keep a page broken for the
    // whole TTL after the backend came back, and the reader has no way to know
    // that retrying would work.
    entries.delete(key)
    throw err
  })
  entries.set(key, { at: Date.now(), promise })
  return promise
}

/** Drop one key, or everything. For a caller that has just changed the data. */
export function bust(key) {
  if (key === undefined) entries.clear()
  else entries.delete(key)
}
