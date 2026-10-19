import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { refIssues, refIssuesFor } from '../api'
import NotFound from '../components/NotFound'
import { useHead } from '../seo/head'
import { issuesHead, issuesForHead } from '../seo/pages'
import { day, engineers, glossaryPath, issuesPath, modelHref, shortName, wallPath } from './live'

/**
 * KNOWN ISSUES (2026-10-15): per model, the problems at least N engineers
 * report, as a tracker - scanned, filtered, returned to - not a story.
 *
 * THERE IS NO "FIXED" COLUMN. Each issue shows when it was first and LAST
 * reported. We cannot know a fix happened, and a silence after a date reads
 * as nothing more than that (rule 4).
 */

export function IssuesIndex() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [q, setQ] = useState('')
  useHead(issuesHead())
  useEffect(() => { refIssues().then(setData).catch((e) => setErr(e.message)) }, [])
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (data?.models || []).filter((r) => !needle || r.model.name.toLowerCase().includes(needle))
  }, [data, q])

  return (
    <div className="shell lv-page">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><span>Known issues</span></div>
      <header className="lv-head">
        <span className="lv-kicker">Reference · tracker</span>
        <h1>Known issues</h1>
        <p className="lv-sub">
          Problems engineers report with each model - only those reported by at least{' '}
          {data ? engineers(data.min_engineers) : 'two engineers'}, each with the quotes behind it.
        </p>
      </header>
      {err && <p className="lv-note">The tracker could not be read: {err}</p>}
      {!data && !err && <div className="skel" style={{ height: 240 }} />}
      {data && (
        <>
          <div className="lv-bar">
            <input className="lv-search" type="search" placeholder="Find a model" value={q}
                   onChange={(e) => setQ(e.target.value)} aria-label="Find a model" />
          </div>
          <p className="lv-note">Ordered by number of known issues, then by name. More issues can mean more use as much as more problems.</p>
          {rows.length === 0 ? <p className="lv-empty">No model matches.</p> : (
            <ol className="lv-list">
              {rows.map((r) => (
                <li key={r.model.id}>
                  <Link className="lv-row" to={issuesPath(r.model.id)}>
                    <span className="lv-row-main"><b>{shortName(r.model.name)}</b></span>
                    <span className="lv-meta">{r.issues} {r.issues === 1 ? 'issue' : 'issues'}{r.latest ? ` · latest report ${day(r.latest)}` : ''}</span>
                  </Link>
                </li>
              ))}
            </ol>
          )}
          <footer className="lv-foot">
            <p>Built in code from the board's public reports. An issue is a capability at least {engineers(data.min_engineers)} report problems with. Nothing here says an issue is fixed - only when it was last reported.</p>
          </footer>
        </>
      )}
    </div>
  )
}

export function IssuesFor({ rest }) {
  const id = rest.split('/').slice(1).map(decodeURIComponent).join('/')
  const [state, setState] = useState({ d: null, err: null, notFound: false })
  useHead(state.notFound ? false : issuesForHead(state.d, `/blogs/${rest}`))

  useEffect(() => {
    setState({ d: null, err: null, notFound: false })
    refIssuesFor(id)
      .then((d) => setState({ d, err: null, notFound: false }))
      .catch((e) => setState({ d: null, err: e.message, notFound: e.status === 404 }))
  }, [id])

  if (state.notFound) return <NotFound what="model" back={{ to: '/blogs/issues', label: 'Known issues' }} />
  const d = state.d
  const name = d ? shortName(d.model.name) : ''
  return (
    <div className="shell lv-page">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><Link to="/blogs/issues">Known issues</Link><span>/</span><span>{name || '…'}</span></div>
      {state.err && <p className="lv-note">This page could not be read: {state.err}</p>}
      {!d && !state.err && <div className="skel" style={{ height: 240 }} />}
      {d && (
        <>
          <header className="lv-head">
            <span className="lv-kicker">Known issues</span>
            <h1>{name}: known issues</h1>
            <p className="lv-sub">
              {d.issues.length
                ? `${d.issues.length} ${d.issues.length === 1 ? 'problem' : 'problems'} reported by at least ${engineers(d.min_engineers)} each.`
                : `No problem has been reported by ${engineers(d.min_engineers)} or more yet.`}
            </p>
            <p className="lv-links"><Link to={modelHref(d.model)}>{name}'s page →</Link></p>
          </header>
          {d.issues.length > 0 && (
            <div className="is-table" role="table" aria-label={`Known issues for ${name}`}>
              <div className="is-tr is-th" role="row">
                <span role="columnheader">Issue</span>
                <span role="columnheader">Report problems</span>
                <span role="columnheader">Report it working</span>
                <span role="columnheader">First reported</span>
                <span role="columnheader">Last reported</span>
              </div>
              {d.issues.map((i) => (
                <details key={i.slug} className="is-row">
                  <summary className="is-tr" role="row">
                    <span role="cell"><b>{i.name}</b></span>
                    <span role="cell" className="lv-neg">{engineers(i.problems)}</span>
                    <span role="cell" className={i.working ? 'lv-pos' : 'dim'}>{i.working ? engineers(i.working) : 'none'}</span>
                    <span role="cell">{i.first ? day(i.first) : '-'}</span>
                    <span role="cell">{i.latest ? day(i.latest) : '-'}</span>
                  </summary>
                  <div className="is-body">
                    {i.quotes.length === 0 && (
                      <p className="lv-none">These reports are counted here, from posts that are not quoted on public pages.</p>
                    )}
                    {i.quotes.map((q, k) => (
                      <blockquote key={k} className="lv-quote">
                        <p>{q.quote}</p>
                        <footer>
                          <span>{q.source}</span>{q.written && <span>{day(q.written)}</span>}
                          {q.url && <a href={q.url} target="_blank" rel="noopener noreferrer">Read the original ↗</a>}
                        </footer>
                      </blockquote>
                    ))}
                    <p className="lv-links">
                      <Link to={wallPath('capability', i.slug, d.model.id)}>Both sides on {i.name.toLowerCase()} →</Link>
                      <Link to={glossaryPath('capability', i.slug)}>What is {i.name.toLowerCase()}? →</Link>
                    </p>
                  </div>
                </details>
              ))}
            </div>
          )}
          <footer className="lv-foot">
            <p>
              Ordered by how many engineers report the problem. There is no "fixed" column: we cannot know a fix
              happened, so each issue says only when it was last reported. Open a row for the quotes.
            </p>
          </footer>
        </>
      )}
    </div>
  )
}
