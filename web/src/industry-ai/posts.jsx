import { fmtDayUtc } from '../dates'
import { KIND_LABEL, PLATFORM_LABEL, REASON_LABEL, STAGE_LABEL, TYPE_LABEL, n } from './parts'

/**
 * ONE POST, as every Industry AI list shows it (2026-11-25): a domain's page
 * (routes/IndustryAIDomain.jsx) and AI Watch (routes/AIWatch.jsx). Moved here from
 * the domain page so the two pages can never show a post differently.
 */

export const SORT_LABEL = {
  newest: 'Newest posted', oldest: 'Oldest posted', engaged: 'Most engaged', first_seen: 'Newest found',
}
export const ENGAGEMENT_LABEL = {
  views: 'views', score: 'score', bookmarks: 'bookmarks', comments: 'comments', reposts: 'reposts',
  likes: 'likes', quotes: 'quotes', points: 'points', reactions: 'reactions',
}
/** "iai:retail:x:<query>" -> "X search: <query>"; "watch:reddit:r/x" -> "Reddit watch: r/x". */
export function queryLabel(key) {
  const [lane, a, b, ...rest] = String(key).split(':')
  if (lane === 'iai') return `${PLATFORM_LABEL[b] || b} search: ${rest.join(':')}`
  if (lane === 'watch') return `${PLATFORM_LABEL[a] || a} watch: ${[b, ...rest].join(':')}`
  return key
}
/** THE REVIEW FLAGS (iai-7, the 2026-11-26 kept-post review; support_chatter iai-8;
 *  collect/industry_ai/config.py FLAG_NAMES). Flags, never drops: the Info view says
 *  what each means. */
export const FLAG_LABEL = {
  github_tracking: 'GitHub to-do list',
  ai_far_from_industry: 'AI far from the industry word',
  market_chatter: 'Market chatter',
  reply_fragment: 'Short X reply',
  heavy_poster: 'Heavy poster',
  for_sale: 'For sale',
  weak_ai_long_post: 'Long post, weak AI word',
  support_chatter: 'Product support',
  // On a NOT READABLE picture post, shadow mode (#679 step 3; collect/industry_ai/rules.py
  // PICTURE_TEXT_FLAG / PICTURE_TEXT_AI_ONLY_FLAG): what its picture's text would decide.
  picture_text_would_pass: 'Its picture text would pass',
  picture_text_only_ai: 'Picture text adds only “ai”',
}
/** Set by the rules when the text that came with a post's media changed its outcome
 * (collect/industry_ai/rules.py MEDIA_TEXT_FLAG; judge never imports collect). */
export const MEDIA_TEXT_FLAG = 'terms_from_media_text'
const MEDIA_TEXT_LABEL = {
  alt_text: "the picture's alt text",
  quoted_post: 'the post it quotes',
  crosspost_parent: 'the original post it crossposts',
}
/** A kept post can be here on words that are not its author's (#680 review, point 2):
 * say which, so a post whose own words show no AI term is not left unexplained. */
export function MatchedInMedia({ it }) {
  if (!it.flags.includes(MEDIA_TEXT_FLAG)) return null
  const from = (it.media_text_from || []).map((k) => MEDIA_TEXT_LABEL[k] || k.replace(/_/g, ' '))
  return (
    <p className="dim iai-note">
      Matched partly on words that are not the author's own:{' '}
      {from.length ? from.join(' and ') : 'the text that came with its media'}.
    </p>
  )
}

export function flagLabel(f) {
  if (f === MEDIA_TEXT_FLAG) return 'matched on the text that came with its media'
  if (f.startsWith('also_matches:')) return `also matches ${f.slice(13).replace(/_/g, ' ')}`
  if (f.startsWith('domain_from_terms:')) return `filed by its words (${f.slice(18).replace(/_/g, ' ')})`
  if (FLAG_LABEL[f]) return FLAG_LABEL[f].toLowerCase()
  return f.replace(/_/g, ' ')
}
/** X keeps the handle in the link; other platforms give an id only. */
export function authorOf(it) {
  if (it.platform === 'x') {
    const m = /x\.com\/([^/]+)\/status/.exec(it.url || '')
    if (m && m[1] !== 'i') return `@${m[1]}`
  }
  if (it.platform === 'hackernews' && it.author_id) return it.author_id
  // Instagram stores the numeric account id; the handle is in its watch query.
  if (it.platform === 'instagram') {
    const k = (it.queries || []).find((q) => q.startsWith('watch:instagram:ig:'))
    if (k) return `@${k.slice(19)}`
  }
  return it.author_id ? `id ${it.author_id}` : 'no author id'
}
export const shorten = (s, max = 70) => (s.length > max ? `${s.slice(0, max - 1)}…` : s)

export function Item({ it, groupNames = {}, domainKey = null, domainNames = {} }) {
  const eng = Object.entries(it.engagement || {}).filter(([k, v]) => k !== 'upvote_ratio' && v)
  const flags = it.flags.filter((f) => !f.startsWith('person:'))
  const others = it.domains.filter((x) => x !== domainKey)
  return (
    <li className="card iai-item">
      <div className="iai-item-meta">
        <span className="chip">{KIND_LABEL[it.kind] || it.kind}</span>
        <span>{PLATFORM_LABEL[it.platform] || it.platform}</span>
        <span>{it.created_at ? fmtDayUtc(it.created_at) : 'no posting date'}</span>
        <span className="dim">{authorOf(it)}</span>
        {it.content_type && <span className="iai-tag">{TYPE_LABEL[it.content_type] || it.content_type}</span>}
        {it.stage && <span className="iai-tag">{STAGE_LABEL[it.stage] || it.stage}</span>}
        {it.verdict === 'dropped' && (
          <span className="iai-tag iai-tag-drop">{REASON_LABEL[it.drop_reason] || it.drop_reason}</span>
        )}
      </div>
      {it.title && <h3 className="iai-item-title">{it.title}</h3>}
      {it.text_cleared_at
        ? <p className="dim iai-item-text">Text cleared by retention on {fmtDayUtc(it.text_cleared_at)}; its labels are kept.</p>
        : it.excerpt && <p className="iai-item-text iai-clamp3">{it.excerpt}{it.excerpt_cut && '…'}</p>}
      <MatchedInMedia it={it} />
      <div className="iai-item-foot">
        {it.url && <a href={it.url} target="_blank" rel="noopener noreferrer nofollow">Open the original →</a>}
        {eng.length > 0 && (
          <span className="dim iai-note tnum">{eng.slice(0, 3).map(([k, v]) => `${n(v)} ${ENGAGEMENT_LABEL[k] || k}`).join(' · ')}</span>
        )}
      </div>
      <details className="iai-details">
        <summary>Details</summary>
        <dl className="iai-dl">
          {(it.terms || []).length > 0 && <><dt>Industry words</dt><dd>{it.terms.join(' · ')}</dd></>}
          {it.ai_terms.length > 0 && <><dt>AI terms</dt><dd>{it.ai_terms.join(' · ')}</dd></>}
          {it.groups.length > 0 && <><dt>Group</dt><dd>{it.groups.map((g) => groupNames[g] || g).join(' · ')}</dd></>}
          {it.matched_pattern && <><dt>Type decided by</dt><dd><code>{it.matched_pattern}</code></dd></>}
          {it.verdict === 'dropped' && <><dt>Filtered at</dt><dd>{it.drop_stage}</dd></>}
          {flags.length > 0 && <><dt>Flags</dt><dd>{flags.map(flagLabel).join(' · ')}</dd></>}
          <dt>Found by</dt>
          <dd>{it.queries.map(queryLabel).join(' · ') || '–'}
            {it.domain_hints.length > 1 && ` (searched for under ${it.domain_hints.length} domains)`}</dd>
          {others.length > 0 && <><dt>{domainKey ? 'Also filed under' : 'Names the industries'}</dt><dd>{others.map((x) => domainNames[x] || x.replace(/_/g, ' ')).join(', ')}</dd></>}
          {eng.length > 3 && <><dt>Engagement</dt><dd className="tnum">{eng.map(([k, v]) => `${n(v)} ${ENGAGEMENT_LABEL[k] || k}`).join(' · ')}</dd></>}
          {it.share_count > 0 && <><dt>Shares & copies</dt><dd>{n(it.share_count)}</dd></>}
          {it.duplicate_of && <><dt>A copy of</dt><dd>{it.duplicate_of}</dd></>}
          {it.link && <><dt>Linked article</dt><dd><a href={it.link} target="_blank" rel="noopener noreferrer nofollow">{shorten(it.link, 80)}</a></dd></>}
          {it.canonical_url && it.canonical_url !== it.link && <><dt>Article, deduplicated</dt><dd>{shorten(it.canonical_url, 80)}</dd></>}
          {it.lang && <><dt>Language</dt><dd>{it.lang}</dd></>}
          {it.first_seen_at && <><dt>First seen</dt><dd>{fmtDayUtc(it.first_seen_at)}</dd></>}
        </dl>
      </details>
    </li>
  )
}
