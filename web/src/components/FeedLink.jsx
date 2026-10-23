import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { feedModels } from '../api'

/**
 * A COUNT THAT OPENS ITS REPORTS, FOR A SEATED MODEL ONLY (2026-10-23).
 *
 * The feed stores paraphrases for every model with reports and shows only the
 * ones the models page lists (judge/feed/items.py `seated_keys`). A count for
 * any other model stays the same number in plain text: a link would open a page
 * that says its reports are not shown.
 *
 * Plain text, too, until the seated list has loaded or if it cannot be read -
 * a missing list is not "every model is seated" (rule 6).
 */
let seated = null
let loading = null

function useSeated() {
  const [set, setSet] = useState(seated)
  useEffect(() => {
    if (seated) return undefined
    let alive = true
    loading = loading || feedModels().then((v) => { seated = new Set(v.ids || []); return seated })
    loading.then((s) => alive && setSet(s)).catch(() => { loading = null })
    return () => { alive = false }
  }, [])
  return set
}

/** The model id an `evidencePath` names: `/evidence/<id>?...`. */
export const feedModelOf = (to) => decodeURIComponent(to.split('?')[0].replace(/^\/evidence\//, ''))

/** `fallback`, when given, replaces the text for an unseated model - `null` for
 * a link that is only a way in ("Every report on X →") and is no count. */
export default function FeedLink({ to, className = 'ev-open', style, fallback, children, ...rest }) {
  const set = useSeated()
  if (to && set && set.has(feedModelOf(to))) {
    return <Link to={to} className={className} style={style} {...rest}>{children}</Link>
  }
  if (fallback !== undefined) return fallback
  // No title: "Read the N reports" would promise a page that does not open.
  return <span className={className.replace(/\bev-open\b/, '').trim() || undefined} style={style}>{children}</span>
}

export { useSeated }
