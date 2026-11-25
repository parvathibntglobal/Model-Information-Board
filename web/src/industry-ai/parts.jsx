/**
 * Shared by the "AI in industries" summary (routes/IndustryAI.jsx) and one
 * domain's page (routes/IndustryAIDomain.jsx): the labels and the bar list, so
 * the two pages can never name a type, platform or reason differently.
 */

export const TYPE_LABEL = {
  use_case: 'Use cases', how_to: 'How-to & tips', tool_or_product: 'Tools & products',
  research: 'Research', news: 'News', discussion: 'Discussion',
}
export const STAGE_LABEL = { deployed: 'deployed', pilot: 'pilot', first_hand: 'first-hand' }
export const PLATFORM_LABEL = {
  reddit: 'Reddit', x: 'X', github: 'GitHub', hackernews: 'Hacker News', devto: 'dev.to',
  bluesky: 'Bluesky', feeds: 'Blogs & feeds', instagram: 'Instagram',
}
// What a row IS, read from the platform's own id and link (judge/industry_ai/view.py
// `_KIND`). X and Bluesky replies are not told apart from posts: nothing stored says.
export const KIND_LABEL = {
  post: 'Post', comment: 'Comment', issue: 'GitHub issue', pull_request: 'Pull request',
  discussion: 'GitHub discussion', story: 'HN story', article: 'Article', unknown: 'Unknown',
}
export const REASON_LABEL = {
  no_ai_term: 'No AI term', no_domain_term: 'No industry term',
  // Two windows, named apart (#650 review). No day counts here: they live in
  // contract/industry_ai.yaml (run.window_days, watch.lookback_days), so a number
  // written in this file would go stale the day the contract changes (rule 11).
  outside_window: 'Older than the run window',
  outside_watch_window: 'Watched post older than the watch window (from first sight)',
  shared_link: 'Same article shared elsewhere',
  repeat_post: 'Same author, same post again', near_duplicate: 'Near-duplicate text',
  too_short: 'Too short', bot: 'Bot account', non_english: 'Not English', spam: 'Spam or scam',
  promo: 'Sponsored or affiliate', hiring: 'Hiring or job ad', signup_ad: 'Sign-up ad',
}

export const n = (v) => (v ?? 0).toLocaleString('en-GB')

/** When the API counted this answer (judge/industry_ai/cache.py: recounted on a visit after 10 minutes; recounted while the visitor waits when over an hour old). */
export function countedAt(iso) {
  if (!iso) return null
  const t = new Date(iso)
  return Number.isNaN(t.getTime()) ? null : `${t.toISOString().slice(11, 16)} UTC`
}

export function Bars({ counts, labels, order, onPick, picked }) {
  const keys = (order || Object.keys(counts)).filter((k) => counts[k])
  if (!keys.length) return <p className="dim iai-none">None yet.</p>
  const max = Math.max(...keys.map((k) => counts[k]))
  return (
    <ul className="iai-bars">
      {keys.map((k) => (
        <li key={k} className={picked === k ? 'iai-picked' : undefined}>
          {onPick
            ? <button type="button" className="iai-bar-label iai-pick" onClick={() => onPick(k)}>{labels?.[k] || k}</button>
            : <span className="iai-bar-label">{labels?.[k] || k}</span>}
          <span className="iai-bar-track"><span className="iai-bar" style={{ width: `${(100 * counts[k]) / max}%` }} /></span>
          <span className="iai-bar-n tnum">{n(counts[k])}</span>
        </li>
      ))}
    </ul>
  )
}
