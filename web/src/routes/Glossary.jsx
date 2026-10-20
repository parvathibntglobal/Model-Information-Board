import { useEffect, useMemo, useState } from 'react'
import { Link, Route, Routes, useParams } from 'react-router-dom'
import { glossaryTerm, glossaryTerms } from '../api'
import NotFound from '../components/NotFound'
import { useHead } from '../seo/head'
import { aiGlossaryHead, aiGlossaryTermHead } from '../seo/pages'
import '../styles/glossary.css'

/**
 * THE AI GLOSSARY (2026-10-20): what each concept IS, in one short paragraph.
 *
 *   /glossary         every term, A to Z, with a search and the categories
 *   /glossary/<slug>  one term: the paragraph, its related terms, A-Z neighbours
 *
 * The layout follows sanity.io/glossary - a numbered letter index over letter
 * sections of term cards - with the definition kept to one paragraph rather
 * than an article. The words come from glossary.yaml through
 * /glossary-terms (judge/glossary.py); nothing is written here.
 */

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

function letterOf(term) {
  const c = (term || '').trim()[0]?.toUpperCase() || '#'
  return /[A-Z]/.test(c) ? c : '#'
}

export default function Glossary() {
  return (
    <Routes>
      <Route index element={<GlossaryIndex />} />
      <Route path=":slug" element={<GlossaryTerm />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

function GlossaryIndex() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('all')
  useHead(aiGlossaryHead())
  useEffect(() => { glossaryTerms().then(setData).catch((e) => setErr(e.message)) }, [])

  const groups = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const rows = (data?.terms || []).filter((t) => (cat === 'all' || t.category === cat)
      && (!needle || [t.term, ...(t.aka || []), t.teaser].join(' ').toLowerCase().includes(needle)))
    const by = {}
    for (const t of rows) (by[letterOf(t.term)] ||= []).push(t)
    return Object.entries(by).sort(([a], [b]) => a.localeCompare(b))
  }, [data, q, cat])

  const present = new Set(groups.map(([l]) => l))
  const shown = groups.reduce((n, [, ts]) => n + ts.length, 0)
  const catName = Object.fromEntries((data?.categories || []).map((c) => [c.key, c.name]))

  return (
    <div className="shell section-tight gl-page">
      <header className="gl-hero">
        <span className="go-badge go-models page-tag">Glossary</span>
        <h1>Glossary</h1>
        <p className="muted">
          Plain definitions of the terms you meet when choosing, prompting and running AI models.
          One short paragraph each: enough to get the idea, with the related terms beside it.
        </p>
      </header>

      {err && <p className="gl-note">The glossary could not be loaded: {err}</p>}
      {!data && !err && <p className="gl-note">Loading the glossary…</p>}

      {data && (
        <>
          <div className="gl-tools">
            <input
              className="gl-search"
              type="search"
              placeholder={`Search ${data.terms.length} terms`}
              aria-label="Search the glossary"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="gl-chips" role="group" aria-label="Filter by category">
              <button type="button" className={`gl-chip${cat === 'all' ? ' on' : ''}`} onClick={() => setCat('all')}>All</button>
              {data.categories.map((c) => (
                <button key={c.key} type="button" className={`gl-chip${cat === c.key ? ' on' : ''}`} onClick={() => setCat(c.key)}>
                  {c.name}
                </button>
              ))}
            </div>
          </div>

          <nav className="gl-az" aria-label="Jump to a letter">
            {LETTERS.map((l) => present.has(l)
              ? <a key={l} href={`#gl-${l}`}>{l}</a>
              : <span key={l} aria-hidden="true">{l}</span>)}
          </nav>

          {shown === 0 && <p className="gl-note">No term matches that search.</p>}

          {groups.map(([letter, terms]) => (
            <section key={letter} id={`gl-${letter}`} className="gl-letter">
              <h2>{letter}</h2>
              <ol className="gl-grid">
                {terms.map((t, i) => (
                  <li key={t.slug}>
                    <Link to={`/glossary/${t.slug}`} className="gl-card">
                      <span className="gl-num">{String(i + 1).padStart(2, '0')}</span>
                      <h3>{t.term}</h3>
                      {t.aka?.length > 0 && <span className="gl-aka">{t.aka.join(' · ')}</span>}
                      <p>{t.teaser}</p>
                      <span className="gl-cat">{catName[t.category]}</span>
                    </Link>
                  </li>
                ))}
              </ol>
            </section>
          ))}
        </>
      )}
    </div>
  )
}

function GlossaryTerm() {
  const { slug } = useParams()
  const [t, setT] = useState(null)
  const [missing, setMissing] = useState(false)
  const [err, setErr] = useState(null)
  useHead(t ? aiGlossaryTermHead(t) : null)
  useEffect(() => {
    setT(null); setMissing(false); setErr(null)
    glossaryTerm(slug).then(setT).catch((e) => (e.status === 404 ? setMissing(true) : setErr(e.message)))
  }, [slug])

  if (missing) return <NotFound />
  return (
    <div className="shell section-tight gl-page">
      <div className="gl-crumb"><Link to="/glossary">Glossary</Link><span>/</span><span>{t?.term || slug}</span></div>
      {err && <p className="gl-note">This term could not be loaded: {err}</p>}
      {!t && !err && <p className="gl-note">Loading…</p>}
      {t && (
        <article className="gl-term">
          <span className="eyebrow">{t.category_name}</span>
          <h1>What is {t.term}?</h1>
          {t.aka?.length > 0 && <p className="gl-aka">Also called {t.aka.join(', ')}</p>}
          <p className="gl-def">{t.definition}</p>

          <section className="gl-related">
            <h2>Related terms</h2>
            <ul>
              {t.related.map((r) => (
                <li key={r.slug}>
                  <Link to={`/glossary/${r.slug}`} className="gl-card gl-card-sm">
                    <h3>{r.term}</h3>
                    <p>{r.teaser}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <nav className="gl-pager" aria-label="Previous and next term">
            {t.previous ? <Link to={`/glossary/${t.previous.slug}`}>← {t.previous.term}</Link> : <span />}
            <Link to="/glossary">All terms</Link>
            {t.next ? <Link to={`/glossary/${t.next.slug}`}>{t.next.term} →</Link> : <span />}
          </nav>
        </article>
      )}
    </div>
  )
}
