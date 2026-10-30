import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { blogPosts } from '../api'
import { useHead } from '../seo/head'
import { guidesHead } from '../seo/pages'
import '../styles/guides.css'
import { formatOf } from './guideKinds'

/**
 * GUIDES (2026-10-30, anooj): Blogs -> Guides, `/blogs/guides`.
 *
 * Three kinds of guide, one hub:
 *   Migration guides  written posts on moving between two models, each with a
 *                     verified-facts box built from the registry (GuideFacts)
 *   Developer guides  } written once the providers' official SDK release notes
 *   Tutorials         } are collected - a guide is instructions, and an
 *                       engineer's opinion is not one. Until then each tab
 *                       says so, rather than showing an empty grid (rule 4).
 *
 * THE SERVER DECIDES WHAT IS LISTED: approved posts only, as the blog index.
 */
const TABS = [
  { key: 'migration', label: 'Migration guides', format: 'migration-guide' },
  { key: 'developer', label: 'Developer guides', format: null },
  { key: 'tutorials', label: 'Tutorials', format: null },
]

const dateOf = (p) => (p.published_at || '').slice(0, 10) || (p.meta || [])[0] || ''
const modelsOf = (p) => (p.tags || []).filter((t) => t && t !== p.kicker && t !== p.tag)

function Cover({ p, big }) {
  const src = p.cover?.src
  if (src) return <img className="gh-cover" src={src} alt={p.cover.alt || ''} loading={big ? 'eager' : 'lazy'} />
  const [a, b] = modelsOf(p)
  return (
    <div className="gh-cover gh-cover-text" aria-hidden="true">
      <span>{a}</span><span className="gh-arrow">→</span><span>{b}</span>
    </div>
  )
}

function Card({ p, big }) {
  const [a, b] = modelsOf(p)
  return (
    <Link to={`/blogs/${p.slug}`} className={`gh-card${big ? ' gh-card-big' : ''}`}>
      <Cover p={p} big={big} />
      <div className="gh-body">
        <span className="gh-kicker">{p.kicker || 'Guide'}{a && b ? ` · ${a} · ${b}` : ''}</span>
        <b className="gh-title">{p.title}</b>
        {p.dek && <span className="gh-dek">{p.dek}</span>}
        <span className="gh-meta mono">{[dateOf(p), p.read ? `${p.read} min read` : null].filter(Boolean).join(' · ')}</span>
      </div>
    </Link>
  )
}

export default function Guides() {
  useHead(guidesHead())
  const [sp, setSp] = useSearchParams()
  const tab = TABS.find((t) => t.key === sp.get('tab')) || TABS[0]
  const model = sp.get('model') || ''
  const [posts, setPosts] = useState(null)
  const [err, setErr] = useState(null)
  const [q, setQ] = useState('')

  useEffect(() => { blogPosts().then((d) => setPosts(d.posts || [])).catch((e) => setErr(e.message)) }, [])

  const byTab = useMemo(() => {
    const out = {}
    for (const t of TABS) out[t.key] = t.format ? (posts || []).filter((p) => formatOf(p) === t.format) : []
    return out
  }, [posts])
  const models = useMemo(() => [...new Set(byTab[tab.key].flatMap(modelsOf))].sort(), [byTab, tab])
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return byTab[tab.key]
      .filter((p) => !model || modelsOf(p).includes(model))
      .filter((p) => !needle || [p.title, p.dek, ...modelsOf(p)].join(' ').toLowerCase().includes(needle))
      .sort((x, y) => dateOf(y).localeCompare(dateOf(x)))
  }, [byTab, tab, model, q])

  const go = (patch) => {
    const next = new URLSearchParams(sp)
    for (const [k, v] of Object.entries(patch)) { if (v) next.set(k, v); else next.delete(k) }
    setSp(next, { replace: true })
  }

  return (
    <div className="shell section-tight gh-page">
      <header className="gh-hero">
        <span className="page-tag">Blogs · Guides</span>
        <h1>Guides</h1>
        <p>
          Written guides for engineers moving between AI models: why teams switch, what changes, what broke for the
          people who did it, and what to check first. Every migration guide carries a box of verified facts - each
          model&apos;s listed price, context window, output limit and features - read from our model registry when you
          open it.
        </p>
      </header>

      <div className="gh-tabs" role="tablist" aria-label="Kinds of guide">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={t.key === tab.key}
            className={`gh-tab${t.key === tab.key ? ' on' : ''}`} onClick={() => go({ tab: t.key === 'migration' ? '' : t.key, model: '' })}>
            {t.label} <span className="gh-n">{posts ? byTab[t.key].length : '…'}</span>
          </button>
        ))}
      </div>

      {err && <p className="gh-empty">The guides could not be read: {err}</p>}
      {!posts && !err && <div className="skel" style={{ height: 320 }} />}

      {posts && !tab.format && (
        <section className="gh-empty-box">
          <b>No {tab.label.toLowerCase()} yet.</b>
          <p>
            A {tab.key === 'developer' ? 'developer guide' : 'tutorial'} gives steps you can follow, so it has to rest on
            each provider&apos;s official SDK and API documentation, not on what one engineer reported. We are adding the
            providers&apos; official SDK release notes next; these guides are written from them once they are in.
          </p>
          <p><button type="button" className="btn" onClick={() => go({ tab: '', model: '' })}>Read the migration guides</button></p>
        </section>
      )}

      {posts && tab.format && (
        <>
          <div className="gh-tools">
            <input type="search" className="gh-search" placeholder="Find a guide or a model…" value={q}
              onChange={(e) => setQ(e.target.value)} aria-label="Find a guide" />
            <label className="gh-filter">Model
              <select value={model} onChange={(e) => go({ model: e.target.value })}>
                <option value="">All models</option>
                {models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </label>
            <span className="gh-count mono">{shown.length} of {byTab[tab.key].length} guides</span>
          </div>
          {shown.length === 0 && <p className="gh-empty">No guide matches. <button type="button" className="gh-link" onClick={() => { setQ(''); go({ model: '' }) }}>Show all</button></p>}
          {shown.length > 0 && (
            <div className="gh-grid">
              {shown.map((p, i) => <Card key={p.slug} p={p} big={i === 0 && !q && !model} />)}
            </div>
          )}
        </>
      )}
    </div>
  )
}
