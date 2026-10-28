import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '../components/ui'

/**
 * WHAT THE NEWS LIST AND A STORY'S PAGE SHARE (2026-10-28): the picture, the
 * time, the meta line and the two kinds of link. One copy, so the two pages
 * cannot drift apart.
 */

export const GROUPS = [['all', 'All'], ['selected', 'News'], ['lab', 'AI labs'], ['writer', 'Writers'], ['release', 'Releases']]
export const groupLabel = (group) => GROUPS.find(([k]) => k === group)?.[1]

export function ago(iso) {
  if (!iso) return ''
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 60) return `${Math.max(mins, 1)} min ago`
  if (mins < 24 * 60) return `${Math.round(mins / 60)} h ago`
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

/** "3 h ago", or "on 26 Oct" - for use inside a sentence. */
export function when(iso) {
  if (!iso) return null
  const a = ago(iso)
  return a.endsWith('ago') ? a : `on ${a}`
}

export const full = (iso) => (iso ? new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '')

/** The site a link goes to, as a reader knows it: "techcrunch.com". */
export function siteOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

/** A stable colour per source, so its drawn cards are recognisable at a glance. */
function hueOf(key) {
  let h = 0
  for (const ch of key) h = (h * 31 + ch.charCodeAt(0)) % 360
  return h
}

/** The picture: the feed's own, the article's link-preview picture, or a card
 *  drawn naming the source. A picture that fails to load becomes the card. */
export function Picture({ it, source, lead = false }) {
  const [broken, setBroken] = useState(false)
  if (it.image_url && !broken) {
    return (
      <div className={`nw-pic${lead ? ' nw-pic-lead' : ''}`}>
        <img src={it.image_url} alt="" loading={lead ? 'eager' : 'lazy'} referrerPolicy="no-referrer"
             title={it.image_source === 'link_preview' ? "The article's own link-preview picture" : "The feed's picture"}
             onError={() => setBroken(true)} />
      </div>
    )
  }
  // THE DRAWN CARD names the source, not the story: the headline is printed
  // right under it, and saying it twice reads as a mistake.
  const h = hueOf(it.source_key)
  const group = groupLabel(source?.group)
  return (
    <div className={`nw-pic nw-drawn${lead ? ' nw-pic-lead' : ''}`} aria-hidden="true"
         style={{ background: `radial-gradient(120% 90% at 85% 10%, hsl(${(h + 40) % 360} 60% 28%), transparent 60%),`
                  + ` linear-gradient(135deg, hsl(${h} 45% 20%), hsl(${(h + 20) % 360} 50% 10%))` }}>
      {group && <span className="nw-drawn-group">{group}</span>}
      <span className="nw-drawn-name" style={{ color: `hsl(${h} 85% 85%)` }}>{source?.label || it.source_key}</span>
    </div>
  )
}

/** To the story's page on this site. */
export const StoryLink = ({ it, children, className }) => (
  <Link className={className} to={`/news/${encodeURIComponent(it.id)}`}>{children}</Link>
)

/** Straight to the source, for a reader who wants the article and not our page. */
export const SourceLink = ({ it, children, className, title }) => (
  <a className={className} href={it.url} target="_blank" rel="noopener noreferrer nofollow" title={title}>{children}</a>
)

export function Meta({ it, source }) {
  return (
    <div className="nw-meta">
      <span className="nw-source">{source?.label || it.source_key}</span>
      {it.published_at
        ? <time dateTime={it.published_at} title={full(it.published_at)}>{ago(it.published_at)}</time>
        : <span title={`First seen ${full(it.first_seen_at)}`}>date not given</span>}
      {(it.llm_keywords || []).length > 0 && <Badge tone="pass" title={`Matched: ${it.llm_keywords.join(', ')}`}>LLM</Badge>}
      <SourceLink it={it} className="nw-out" title={`Open on ${siteOf(it.url)}`}>↗</SourceLink>
    </div>
  )
}
