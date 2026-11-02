import { useCallback, useEffect, useState } from 'react'
import '../styles/follow.css'

/**
 * THE FOLLOW LIST (2026-11-02, prototype, feat/hooks-prototype): the models a
 * visitor runs, followed once and used by every page that lists models - the
 * model page (its trend and "since you last looked"), AI updates ("Only my
 * models"), the evidence feed's picker (yours first). One list, not a page of
 * its own: the pages that already show prices, retirements and reports
 * personalise, rather than a new page repeating them.
 *
 * NO ACCOUNT. The list and each model's last look live in this browser only
 * (localStorage); nothing is sent anywhere but the ids a page asks about.
 * Storage that is blocked means no memory, and every page still works.
 */

const LIST_KEY = 'mb-follow'
const SEEN_KEY = 'mb-follow-seen'
const EVENT = 'mb-follow-change'
export const MAX_FOLLOWED = 12

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch { /* storage blocked: no memory, still works */ }
}

export const followedIds = () => {
  const ids = read(LIST_KEY, [])
  return Array.isArray(ids) ? ids.filter((x) => typeof x === 'string') : []
}

/** [ids, toggle(id), isFollowed(id)] - kept in step across components and tabs. */
export function useFollowed() {
  const [ids, setIds] = useState(followedIds)
  useEffect(() => {
    const sync = () => setIds(followedIds())
    window.addEventListener(EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])
  const toggle = useCallback((id) => {
    const now = followedIds()
    const next = now.includes(id) ? now.filter((x) => x !== id) : [...now, id].slice(-MAX_FOLLOWED)
    write(LIST_KEY, next)
    window.dispatchEvent(new Event(EVENT))
  }, [])
  const isFollowed = useCallback((id) => ids.includes(id), [ids])
  return [ids, toggle, isFollowed]
}

/** When this browser last looked at a model's page; null the first time. */
export const lastLook = (id) => read(SEEN_KEY, {})?.[id] ?? null

/** Record this look - called once the page has been open a moment. */
export function markLook(id) {
  const seen = read(SEEN_KEY, {})
  write(SEEN_KEY, { ...(seen && typeof seen === 'object' ? seen : {}), [id]: new Date().toISOString() })
}
