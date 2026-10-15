import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { refGlossary, refGlossaryEntry } from '../api'
import NotFound from '../components/NotFound'
import { useHead } from '../seo/head'
import { glossaryHead, glossaryEntryHead } from '../seo/pages'
import { SECTION_OF, engineers, glossaryPath, shortName, topicHref, wallPath, problems as problemsOf } from './live'

/**
 * THE GLOSSARY (2026-10-15): what each job and capability IS, from the
 * hand-written descriptions in contract/ - which name no model and state no
 * count - with what engineers report on it beside them (judge/blog_reference.py).
 * A reference, looked up and linked to, not an article read top to bottom.
 */

const KIND = { best_for: 'Job', capability: 'Capability' }

export function GlossaryIndex() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [section, setSection] = useState('all')
  const [q, setQ] = useState('')
  useHead(glossaryHead())
  useEffect(() => { refGlossary().then(setData).catch((e) => setErr(e.message)) }, [])

  const groups = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const rows = (data?.entries || []).filter((e) => (section === 'all' || e.section === section)
      && (!needle || `${e.name} ${e.summary}`.toLowerCase().includes(needle)))
    const by = {}
    for (const e of rows) {
      const letter = /[a-z]/i.test(e.name[0]) ? e.name[0].toUpperCase() : '#'
      ;(by[letter] ||= []).push(e)
    }
    return Object.entries(by).sort(([a], [b]) => a.localeCompare(b))
  }, [data, section, q])

  return (
    <div className="shell lv-page">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><span>Glossary</span></div>
      <header className="lv-head">
        <span className="lv-kicker">Reference</span>
        <h1>Glossary</h1>
        <p className="lv-sub">
          What each job and capability on the board means, in plain words - and how many engineers have
          reported on it, for which models.
        </p>
      </header>
      {err && <p className="lv-note">The glossary could not be read: {err}</p>}
      {!data && !err && <div className="skel" style={{ height: 240 }} />}
      {data && (
        <>
          <div className="lv-bar">
            <div className="lv-seg" role="group" aria-label="Kind">
              {[['all', 'All'], ['capability', 'Capabilities'], ['best_for', 'Jobs']].map(([k, label]) => (
                <button key={k} type="button" className={section === k ? 'on' : ''} onClick={() => setSection(k)}>{label}</button>
              ))}
            </div>
            <input className="lv-search" type="search" placeholder="Search the glossary" value={q}
                   onChange={(e) => setQ(e.target.value)} aria-label="Search" />
          </div>
          {groups.length === 0 && <p className="lv-empty">Nothing matches that search.</p>}
          {groups.map(([letter, rows]) => (
            <section key={letter} className="gl-letter">
              <h2>{letter}</h2>
              <div className="gl-grid">
                {rows.map((e) => (
                  <Link key={`${e.section}:${e.slug}`} to={glossaryPath(e.section, e.slug)} className="gl-card">
                    <b>{e.name}</b>
                    <span className="gl-sum">{e.summary}</span>
                    <span className="lv-meta">
                      {KIND[e.section]}{e.engineers ? ` · ${engineers(e.engineers)} on ${e.models} ${e.models === 1 ? 'model' : 'models'}` : ' · no public reports yet'}
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </>
      )}
    </div>
  )
}

export function GlossaryEntry({ rest }) {
  const [, kind, raw] = rest.split('/')
  const section = SECTION_OF[kind]
  const slug = decodeURIComponent(raw || '')
  const [state, setState] = useState({ e: null, err: null, notFound: false })
  useHead(state.notFound ? false : glossaryEntryHead(state.e, `/blogs/${rest}`))

  useEffect(() => {
    setState({ e: null, err: null, notFound: false })
    if (!section || !slug) { setState({ e: null, err: null, notFound: true }); return }
    refGlossaryEntry(section, slug)
      .then((e) => setState({ e, err: null, notFound: false }))
      .catch((x) => setState({ e: null, err: x.message, notFound: x.status === 404 }))
  }, [section, slug])

  if (state.notFound) return <NotFound what="entry" back={{ to: '/blogs/glossary', label: 'Glossary' }} />
  const e = state.e
  return (
    <div className="shell lv-page lv-narrow">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><Link to="/blogs/glossary">Glossary</Link><span>/</span><span>{e?.name || '…'}</span></div>
      {state.err && <p className="lv-note">This entry could not be read: {state.err}</p>}
      {!e && !state.err && <div className="skel" style={{ height: 240 }} />}
      {e && (
        <>
          <header className="lv-head">
            <span className="lv-kicker">{KIND[e.section]}{e.heading ? ` · ${e.heading}` : ''}</span>
            <h1>What is {e.name.toLowerCase().startsWith('the ') ? e.name : e.name.toLowerCase()}?</h1>
            <p className="gl-about">{e.about}</p>
            <p className="lv-links"><Link to={topicHref(e.section, e.slug)}>{e.name} on the board →</Link></p>
          </header>
          <section className="lv-card">
            <h2>What engineers report <span>{engineers(e.engineers)}</span></h2>
            {e.models.length === 0
              ? <p className="lv-none">Nobody has reported on this yet.</p>
              : (
                <>
                  <p className="lv-note">Per model, the engineers who report it working, report problems, or mention it. Ordered by how many engineers wrote about it.</p>
                  {e.models.map((r) => (
                    <Link key={r.model.id} className="lv-rail" to={wallPath(e.section, e.slug, r.model.id)}>
                      <span>{shortName(r.model.name)}</span>
                      <span className="lv-counts">
                        <span className="lv-pos">{r.working} working</span>
                        <span className="lv-neg">{problemsOf(r.problems)}</span>
                        {r.neutral > 0 && <span className="lv-neu">{r.neutral} neutral</span>}
                      </span>
                    </Link>
                  ))}
                </>
              )}
          </section>
          {e.siblings.length > 0 && (
            <section className="gl-related">
              <h3>Also under {e.heading}</h3>
              <div className="gl-chips">
                {e.siblings.map((s) => <Link key={s.slug} to={glossaryPath(e.section, s.slug)}>{s.name}</Link>)}
              </div>
            </section>
          )}
          <footer className="lv-foot">
            <p>The description is written by the team and names no model. The counts are built in code from the board's reports and include every source we read.</p>
          </footer>
        </>
      )}
    </div>
  )
}
