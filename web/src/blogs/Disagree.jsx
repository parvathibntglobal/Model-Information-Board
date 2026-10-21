import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { liveDisagree, liveWall } from '../api'
import NotFound from '../components/NotFound'
import { useHead } from '../seo/head'
import { liveDisagree as disagreeHead, liveWall as wallHead } from '../seo/pages'
import { SECTION_OF, day, engineers, glossaryPath, modelHref, shortName, topicHref, wallPath, problems as problemsOf, reports } from './live'
import { evidencePath } from '../catalog/format'

/**
 * WHERE ENGINEERS DISAGREE, AND ONE CLAIM WALL (2026-10-15).
 *
 * Built in code from the board's public reports (judge/blog_live.py). Nothing
 * here is written by a model and nothing is a score: every figure is a count
 * of engineers, and the order is said in words above the list (rule 3).
 */

function Counts({ working, problems, neutral }) {
  return (
    <span className="lv-counts">
      <span className="lv-pos">{working} working</span>
      <span className="lv-neg">{problemsOf(problems)}</span>
      {neutral > 0 && <span className="lv-neu">{neutral} neutral</span>}
    </span>
  )
}

function Crumb({ children }) {
  return (
    <div className="lv-crumb">
      <Link to="/blogs">Blogs</Link><span>/</span>{children}
    </div>
  )
}

export function DisagreeIndex() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [section, setSection] = useState('all')
  const [q, setQ] = useState('')
  useHead(disagreeHead())
  useEffect(() => { liveDisagree().then(setData).catch((e) => setErr(e.message)) }, [])

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (data?.pairs || []).filter((r) => (section === 'all' || r.section === section)
      && (!needle || `${r.topic} ${r.model.name}`.toLowerCase().includes(needle)))
  }, [data, section, q])

  const strong = rows.filter((r) => Math.min(r.working, r.problems) >= 2)
  const thin = rows.filter((r) => Math.min(r.working, r.problems) < 2)
  return (
    <div className="shell lv-page">
      <Crumb><span>Where engineers disagree</span></Crumb>
      <header className="lv-head">
        <span className="lv-kicker">Live · updated with every fetch</span>
        <h1>Where engineers disagree</h1>
        <p className="lv-sub">
          Every model and topic where at least one engineer reports it working and at least one reports
          problems. Open a row to read both sides, quoted and linked.
        </p>
      </header>
      {err && <p className="lv-note">The list could not be read: {err}</p>}
      {!data && !err && <div className="skel" style={{ height: 240 }} />}
      {data && (
        <>
          <div className="lv-bar">
            <div className="lv-seg" role="group" aria-label="Section">
              {[['all', 'All'], ['best_for', 'Jobs'], ['capability', 'Capabilities']].map(([k, label]) => (
                <button key={k} type="button" className={section === k ? 'on' : ''} onClick={() => setSection(k)}>{label}</button>
              ))}
            </div>
            <input className="lv-search" type="search" placeholder="Filter by model or topic"
                   value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter" />
          </div>
          <p className="lv-note">
            {data.pairs.length} pairs, {data.two_or_more_each_side} of them with two or more engineers on each
            side. <b>Ordered by the number of engineers on the smaller side, then on the larger side</b> - both
            counts are on every row. An engineer is counted once per side, however many times they wrote.
          </p>
          {rows.length === 0 ? (
            <p className="lv-empty">No pair matches that filter.</p>
          ) : (
            <>
              {/* TWO GROUPS, BY A STATED RULE (rule 3): two or more engineers on
                  each side, then the rest - folded, because one voice against
                  is thin and the first group is what a reader came for. */}
              <h2 className="lv-group">Two or more engineers on each side <span>{strong.length}</span></h2>
              {strong.length ? <PairList rows={strong} /> : <p className="lv-empty">None matches that filter.</p>}
              {thin.length > 0 && (
                <details className="lv-fold">
                  <summary>One engineer on at least one side <span>{thin.length}</span></summary>
                  <PairList rows={thin} />
                </details>
              )}
            </>
          )}
          <Footer withheld={data.withheld_entries} />
        </>
      )}
    </div>
  )
}

function PairList({ rows }) {
  return (
    <ol className="lv-list">
      {rows.map((r) => (
        <li key={`${r.section}:${r.slug}:${r.model.id}`}>
          <Link className="lv-row" to={wallPath(r.section, r.slug, r.model.id)}>
            <span className="lv-row-main">
              <b>{shortName(r.model.name)}</b>
              <span className="lv-on"> on </span>
              <span>{r.topic}</span>
              <span className="lv-sec">{r.section === 'best_for' ? 'Job' : 'Capability'}</span>
            </span>
            <Counts {...r} />
          </Link>
        </li>
      ))}
    </ol>
  )
}

function Footer({ withheld }) {
  return (
    <footer className="lv-foot">
      <p>
        Built in code from the board's reports. Counts include every source we read; quotes and links
        come only from sources we show publicly. Which side a quote is on is the
        extractor's reading of it; every quote is shown exactly as written and links to where it was
        posted. Nothing on this page is written by a model, and no model is scored or ranked.
      </p>
      {withheld > 0 && (
        <p>{withheld} of the reports behind these counts come from sources whose posts are not quoted on public
          pages, so a count can be larger than the quotes shown for it.</p>
      )}
    </footer>
  )
}

function QuoteCard({ q }) {
  return (
    <blockquote className="lv-quote">
      <p>{q.quote}</p>
      <footer>
        <span>{q.source}</span>
        {q.written && <span>{day(q.written)}</span>}
        {q.url && <a href={q.url} target="_blank" rel="noopener noreferrer">Read the original ↗</a>}
      </footer>
    </blockquote>
  )
}

// THE REPORTS BEHIND A SIDE (2026-10-21): the evidence feed for this model on
// this job or capability, one side. These counts are ENGINEERS; the feed lists
// the reports those engineers wrote on that side - the same people, counted as
// reports there. Neutral is not linked: here it is any neutral mention, in the
// feed a report that took no side, and those are different populations.
function SideCount({ to, n }) {
  return n > 0 && to
    ? <Link to={to} className="ev-open" title={`Open the reports these ${engineers(n)} wrote`}>{engineers(n)}</Link>
    : <>{engineers(n)}</>
}

function Side({ title, tone, quotes, count, empty, to }) {
  // A COUNT WITH NO QUOTE IS NOT "NOBODY". Totals count every source; quotes
  // come only from sources shown publicly, so a side can have reports and no
  // quote - and must say that, not "nobody" (rule 4).
  return (
    <section className={`lv-side lv-side-${tone}`}>
      <h2>{title} <span><SideCount to={to} n={count} /></span></h2>
      {quotes.length === 0
        ? <p className="lv-none">{count > 0
          ? `${engineers(count)} counted here, from posts that are not quoted on public pages.`
          : empty}</p>
        : quotes.map((q, i) => <QuoteCard key={i} q={q} />)}
    </section>
  )
}

export function Wall({ rest }) {
  // rest = disagree/<jobs|capabilities>/<slug>/<model id, may contain a slash>
  const parts = rest.split('/')
  const section = SECTION_OF[parts[1]]
  const slug = decodeURIComponent(parts[2] || '')
  const modelId = parts.slice(3).map(decodeURIComponent).join('/')
  const [state, setState] = useState({ w: null, err: null, notFound: false })
  const path = `/blogs/${rest}`
  useHead(state.notFound ? false : wallHead(state.w, path))

  useEffect(() => {
    setState({ w: null, err: null, notFound: false })
    if (!section || !slug || !modelId) { setState({ w: null, err: null, notFound: true }); return }
    liveWall(section, slug, modelId)
      .then((w) => setState({ w, err: null, notFound: false }))
      .catch((e) => setState({ w: null, err: e.message, notFound: e.status === 404 }))
  }, [section, slug, modelId])

  if (state.notFound) return <NotFound what="page" back={{ to: '/blogs/disagree', label: 'Where engineers disagree' }} />
  const w = state.w
  const name = w ? shortName(w.model.name) : ''
  const feed = (polarity) => (w ? evidencePath(w.model.id, { section: w.section, slug: w.slug, polarity }) : null)
  return (
    <div className="shell lv-page">
      <Crumb><Link to="/blogs/disagree">Where engineers disagree</Link><span>/</span><span>{name || '…'}</span></Crumb>
      {state.err && <p className="lv-note">This page could not be read: {state.err}</p>}
      {!w && !state.err && <div className="skel" style={{ height: 320 }} />}
      {w && (
        <>
          <header className="lv-head">
            <span className="lv-kicker">{w.section === 'best_for' ? 'Job' : 'Capability'} · claim and counter-claim</span>
            <h1>{name} on {w.topic}</h1>
            <p className="lv-sub">
              <b className="lv-pos"><SideCount to={feed('positive')} n={w.working} /></b> {reports(w.working)} it working ·{' '}
              <b className="lv-neg"><SideCount to={feed('negative')} n={w.problems} /></b> {reports(w.problems)} problems
              {w.neutral > 0 && <> · {engineers(w.neutral)} neutral</>}
            </p>
            {w.about && <p className="lv-about">{w.about}</p>}
            <p className="lv-links">
              <Link to={modelHref(w.model)}>{name}'s page →</Link>
              <Link to={topicHref(w.section, w.slug)}>{w.topic} on the board →</Link>
              {w.about && <Link to={glossaryPath(w.section, w.slug)}>What is {w.topic.toLowerCase()}? →</Link>}
            </p>
          </header>
          <div className="lv-wall">
            <Side title="Reports of it working" tone="pos" quotes={w.quotes.positive} count={w.working}
                  empty="Nobody has reported it working on this." to={feed('positive')} />
            <Side title="Reports of problems" tone="neg" quotes={w.quotes.negative} count={w.problems}
                  empty="Nobody has reported problems with this." to={feed('negative')} />
          </div>
          {w.quotes.neutral.length > 0 && (
            <section className="lv-side lv-side-neu">
              <h2>Neutral mentions <span>{engineers(w.neutral)}</span></h2>
              {w.quotes.neutral.map((q, i) => <QuoteCard key={i} q={q} />)}
            </section>
          )}
          <p className="lv-note">
            The two sides are not paired: no quote here answers another. Counts are engineers, once per side.
            {w.quotes_without_author > 0 && ` ${w.quotes_without_author} quote(s) have no known author and add no count.`}
          </p>
          <div className="lv-rails">
            {w.same_topic.length > 0 && (
              <section>
                <h3>{w.topic}: other models</h3>
                {w.same_topic.map((r) => (
                  <Link key={r.model.id} className="lv-rail" to={wallPath(w.section, w.slug, r.model.id)}>
                    <span>{shortName(r.model.name)}</span><Counts {...r} />
                  </Link>
                ))}
              </section>
            )}
            {w.other_topics.length > 0 && (
              <section>
                <h3>{name}: other topics engineers disagree on</h3>
                {w.other_topics.map((r) => (
                  <Link key={`${r.section}:${r.slug}`} className="lv-rail" to={wallPath(r.section, r.slug, w.model.id)}>
                    <span>{r.topic}</span><Counts working={r.working} problems={r.problems} neutral={0} />
                  </Link>
                ))}
              </section>
            )}
          </div>
          <Footer withheld={w.withheld_entries} />
        </>
      )}
    </div>
  )
}
