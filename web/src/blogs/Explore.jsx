import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { liveDisagree } from '../api'
import { shortName, wallPath } from './live'

/**
 * THE LIVE PAGES, OFFERED WHERE A READER ALREADY IS (2026-10-15).
 *
 * `ReadNext` sits under a post (the index offers the same three pages from
 * `views.js` `vBlogs`). Plain links. ReadNext's walls are a JOIN: the post's model tags matched to
 * models that have a claim wall, never a recommendation.
 */

const CARDS = [
  ['/blogs/disagree', 'Where engineers disagree', 'Models and topics with reports on both sides, every quote linked.'],
  ['/blogs/this-week', 'This week in models', 'New listings, what engineers wrote, prices and retirements.'],
  ['/blogs/quiz', 'Which model was this?', 'Five real quotes a day. Guess the model.'],
]

export function ReadNext({ post }) {
  const [pairs, setPairs] = useState(null)
  useEffect(() => { liveDisagree().then((d) => setPairs(d.pairs || [])).catch(() => setPairs([])) }, [])
  const tags = new Set((post?.tags || []).filter((t) => t !== post?.tag).map((t) => t.toLowerCase()))
  const walls = (pairs || []).filter((r) => tags.has(shortName(r.model.name).toLowerCase())).slice(0, 4)
  return (
    <div className="shell lv-next">
      {walls.length > 0 && (
        <section>
          <h3>Where engineers disagree about the models in this post</h3>
          {walls.map((r) => (
            <Link key={`${r.section}:${r.slug}:${r.model.id}`} className="lv-rail" to={wallPath(r.section, r.slug, r.model.id)}>
              <span>{shortName(r.model.name)} on {r.topic}</span>
              <span className="lv-counts"><span className="lv-pos">{r.working} working</span><span className="lv-neg">{r.problems} problems</span></span>
            </Link>
          ))}
        </section>
      )}
      <section className="lv-explore lv-explore-tight">
        {CARDS.map(([to, title, text]) => (
          <Link key={to} to={to} className="lv-tile"><b>{title}</b><span>{text}</span></Link>
        ))}
      </section>
    </div>
  )
}
