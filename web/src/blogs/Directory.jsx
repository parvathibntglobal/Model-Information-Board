import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { blogPosts } from '../api'
import { useHead } from '../seo/head'
import { directoryHead } from '../seo/pages'

/**
 * THE POST DIRECTORY (2026-10-18, anooj: "as the posts are increasing the user
 * needs a directory so he can find the exact post rather than moving around
 * pages"). The blog index pages ten posts at a time, newest first, which is a
 * way to browse and not a way to find one. This lists every post the reader may
 * see on one page - by model, by topic, A-Z or newest - with a search over the
 * title, summary, tags and format.
 *
 * NOT THE GLOSSARY. /blogs/glossary defines capabilities and jobs; this indexes
 * posts. Same page furniture (blog-live.css), different thing.
 *
 * THE SERVER DECIDES WHAT IS LISTED (judge/blog_store.py): the public list is
 * approved posts only, exactly as on the index.
 */

const KINDS = {
  model: 'Model',
  pair: 'Comparison',
  capability: 'Capability or job',
  concept: 'Concept',
  other: 'Other',
}

// THE THREE POSTS WRITTEN BEFORE PLAN KEYS EXISTED, named by format. Anything
// else without a plan key is filed under Other rather than guessed (rule 12).
const LEGACY = { 'Model deep dive': 'model', 'Routing guide': 'pair', 'Capability analysis': 'capability' }

function kindOf(p) {
  const subj = String(p.provenance?.plan_key || '').split(':')[1] || ''
  if (subj.startsWith('concept/')) return 'concept'
  if (subj.startsWith('capability/') || subj.startsWith('best_for/')) return 'capability'
  if (subj.includes('+')) return 'pair'
  if (subj) return 'model'
  return LEGACY[p.kicker] || 'other'
}

/** The post's subjects: its tags without its own format name. A model post
 *  names one model, a comparison two; a topic post names its topic first. */
function subjectsOf(p, kind) {
  const tags = (p.tags || []).filter((t) => t && t !== p.kicker && t !== p.tag)
  if (kind === 'pair') return tags.slice(0, 2)
  return tags.slice(0, 1)
}

const dateOf = (p) => String(p.provenance?.generated_at || '').slice(0, 10)
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s)
const letterOf = (s) => (/[a-z]/i.test(s[0] || '') ? s[0].toUpperCase() : '#')

const VIEWS = [['model', 'By model'], ['topic', 'By topic'], ['az', 'A–Z'], ['new', 'Newest']]

export default function Directory() {
  const [posts, setPosts] = useState(null)
  const [err, setErr] = useState(null)
  const [view, setView] = useState('model')
  const [fmt, setFmt] = useState('')
  const [q, setQ] = useState('')
  useHead(directoryHead())
  useEffect(() => { blogPosts().then((d) => setPosts(d.posts || [])).catch((e) => setErr(e.message)) }, [])

  const rows = useMemo(() => (posts || []).map((p) => {
    const kind = kindOf(p)
    return { p, kind, subjects: subjectsOf(p, kind), date: dateOf(p) }
  }), [posts])

  const formats = useMemo(() => [...new Set(rows.map((r) => r.p.kicker).filter(Boolean))].sort(), [rows])

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return rows.filter((r) => (!fmt || r.p.kicker === fmt) && (!needle || [
      r.p.title, r.p.dek, r.p.kicker, ...(r.p.tags || []), ...(r.p.keywords || []),
    ].join(' ').toLowerCase().includes(needle)))
  }, [rows, fmt, q])

  // GROUPS FOR THE CHOSEN VIEW. A comparison is listed under BOTH of its
  // models, so "everything on Claude Opus 5" includes the posts that weigh it
  // against another model.
  const groups = useMemo(() => {
    // ONE GROUP PER NAME, WHATEVER ITS CASE: writers tag "Code review" and
    // "Code Review", "long context" and "Long context" (4 such pairs on
    // 2026-10-18). Grouped case-blind, shown as first written, capitalised.
    const by = new Map()
    const label = new Map()
    const add = (name, r) => {
      const key = name.toLowerCase()
      if (!by.has(key)) { by.set(key, []); label.set(key, cap(name)) }
      by.get(key).push(r)
    }
    if (view === 'model') {
      for (const r of shown) {
        if (r.kind === 'model' || r.kind === 'pair') r.subjects.forEach((s) => add(s, r))
      }
    } else if (view === 'topic') {
      for (const r of shown) {
        if (r.kind === 'concept' || r.kind === 'capability' || r.kind === 'other') add(r.subjects[0] || 'Other', r)
      }
    } else if (view === 'az') {
      for (const r of shown) add(letterOf(r.p.title), r)
    } else {
      for (const r of shown) add(r.date.slice(0, 7) || 'Undated', r)
    }
    const order = view === 'new'
      ? (a, b) => b[0].localeCompare(a[0])
      : (a, b) => a[0].localeCompare(b[0], undefined, { sensitivity: 'base' })
    const within = view === 'new'
      ? (a, b) => b.date.localeCompare(a.date) || a.p.title.localeCompare(b.p.title)
      : (a, b) => a.p.title.localeCompare(b.p.title)
    return [...by.entries()].map(([k, list]) => [label.get(k), list]).sort(order)
      .map(([k, list]) => [k, [...list].sort(within)])
  }, [shown, view])

  const outOfView = view === 'model' || view === 'topic'
    ? shown.length - new Set(groups.flatMap(([, list]) => list.map((r) => r.p.slug))).size : 0
  const jump = view === 'az' || view === 'model' || view === 'topic'
    ? [...new Set(groups.map(([k]) => letterOf(k)))] : []
  const month = (ym) => {
    const [y, m] = ym.split('-')
    return m ? new Date(Number(y), Number(m) - 1, 1).toLocaleString('en-GB', { month: 'long', year: 'numeric' }) : ym
  }

  return (
    <div className="shell lv-page">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><span>Directory</span></div>
      <header className="lv-head">
        <span className="lv-kicker">Directory</span>
        <h1>Every post, in one place</h1>
        <p className="lv-sub">
          Find a post by the model it covers, the topic it explains, its title or its date - or search for it.
        </p>
      </header>
      {err && <p className="lv-note">The posts could not be read: {err}</p>}
      {!posts && !err && <div className="skel" style={{ height: 240 }} />}
      {posts && (
        <>
          <div className="lv-bar">
            <div className="lv-seg" role="group" aria-label="Arrange by">
              {VIEWS.map(([k, label]) => (
                <button key={k} type="button" className={view === k ? 'on' : ''} onClick={() => setView(k)}>{label}</button>
              ))}
            </div>
            <select className="dir-format" value={fmt} onChange={(e) => setFmt(e.target.value)} aria-label="Format">
              <option value="">All formats</option>
              {formats.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
            <input className="lv-search" type="search" placeholder="Search posts" value={q}
                   onChange={(e) => setQ(e.target.value)} aria-label="Search posts" />
          </div>
          <p className="lv-note dir-count">
            {shown.length === rows.length
              ? `${rows.length} ${rows.length === 1 ? 'post' : 'posts'}.`
              : `${shown.length} of ${rows.length} posts match.`}
            {outOfView > 0 && ` ${outOfView} of them ${outOfView === 1 ? 'is' : 'are'} listed under ${
              view === 'model' ? 'By topic' : 'By model'}, not here.`}
          </p>
          {jump.length > 1 && (
            <nav className="dir-jump" aria-label="Jump to letter">
              {jump.map((l) => <a key={l} href={`#dir-${l}`}>{l}</a>)}
            </nav>
          )}
          {groups.length === 0 && <p className="lv-empty">{rows.length ? 'No post matches that search.' : 'No posts yet.'}</p>}
          {groups.map(([key, list], i) => {
            const first = i === 0 || letterOf(groups[i - 1][0]) !== letterOf(key)
            return (
              <section key={key} className="dir-group" id={first && jump.length ? `dir-${letterOf(key)}` : undefined}>
                <h2 className="lv-group">{view === 'new' ? month(key) : key}<span>{list.length} {list.length === 1 ? 'post' : 'posts'}</span></h2>
                <ul className="lv-list">
                  {list.map((r) => (
                    <li key={r.p.slug}>
                      <Link to={`/blogs/${r.p.slug}`} className="lv-row dir-row">
                        <span className="lv-row-main">
                          <b>{r.p.title}</b>
                          {r.p.dek && <span className="dir-dek">{r.p.dek}</span>}
                        </span>
                        <span className="dir-meta">
                          <span className="dir-fmt">{r.p.kicker || KINDS[r.kind]}</span>
                          {r.kind === 'pair' && view === 'model' && <span>vs {r.subjects.find((s) => s !== key)}</span>}
                          {r.date && <span>{r.date}</span>}
                          {r.p.read && <span>{r.p.read} min</span>}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            )
          })}
        </>
      )}
    </div>
  )
}
