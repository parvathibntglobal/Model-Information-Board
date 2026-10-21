import { useEffect, useState } from 'react'
import { seoIndexable } from '../api'

/**
 * The set of paths worth indexing, from `GET /seo/indexable` (SEO item 5).
 *
 * Loaded once per page load and shared by every `useHead`. `null` means "not
 * known" - still loading, or the request failed - and `useHead` reads an
 * unknown answer as NOT indexable (rule 6: a missing value never becomes a
 * definite one, and "index this" is the definite one here). So a page that
 * cannot ask is `noindex`, never the reverse.
 */

let known = null
let pending = null
const waiting = new Set()

function load() {
  if (pending) return pending
  pending = seoIndexable()
    .then((d) => {
      known = new Set(d?.paths || [])
      waiting.forEach((fn) => fn(known))
    })
    .catch((e) => {
      console.warn('seo: could not read /seo/indexable, so every page stays noindex:', e.message)
    })
  return pending
}

/** The indexable paths, or null until (and unless) they arrive. */
export function useIndexable() {
  const [set, setSet] = useState(known)
  useEffect(() => {
    if (known) { setSet(known); return undefined }
    waiting.add(setSet)
    load()
    return () => { waiting.delete(setSet) }
  }, [])
  return set
}
