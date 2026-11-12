import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { assistantsPage, assistantDetail, modelPath, BoardUnreadable } from '../api'
import { Badge, Notice, Unreadable } from '../components/ui'
import { useHead } from '../seo/head'
import { assistantsPage as assistantsHead } from '../seo/pages'
import { fmtDayUtc } from '../dates'
import NotFound from '../components/NotFound'
import { Posted, PolarityChip, SourceLine } from '../evidence/parts'
import '../styles/evidence.css'

/**
 * AI ASSISTANTS (/ai-assistants, 2026-11-12, PROPOSED): the registry's personal
 * assistants, workspaces and coding builders, grouped by
 * contract/assistant_groups.yaml, with what engineers report about each one.
 *
 * THE LIST IS COUNTS ONLY: people and reports, no quote, link, handle or
 * platform name. NOTHING IS A SCORE OR A RANK: a card is two counts, the order
 * of a group is the contract file's, a comparison cell is three counts.
 *
 * AN ASSISTANT'S OWN PAGE ALSO SHOWS THE REPORTS BEHIND ITS JOBS AND PROBLEMS,
 * as judge/assistants.py sends them under the publication rules: a verified
 * quote with its platform and a link for most sources; Reddit and X ONLY as the
 * platform's own embed, loaded when the reader clicks (evidence/parts.jsx
 * SourceLine, the evidence feed's); a withheld source is not shown and is
 * counted ("N reports from sources we don't show publicly"). No paraphrase yet.
 *
 * SILENCE IS NOT CRITICISM (rule 4): an assistant nobody has reported on is
 * listed as "No reports yet", an absence and not a verdict, and never as a
 * card of zeros. A member of the grouping the registry does not hold yet is
 * COUNTED, never dropped (rule 6).
 */

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`
const idPath = (canonical) => `/ai-assistants/${modelPath(canonical)}`
const SHOWN = 3

function Tags({ tags }) {
  if (!tags || !tags.length) return null
  return <>{tags.map((t) => <Badge key={t.key} tone="info">{t.label}</Badge>)}</>
}

function NoReports() {
  return <p className="dim as-empty">No reports yet. An absence, not a verdict: nobody has been reported discussing it, which says nothing about how it works.</p>
}

function Card({ a }) {
  return (
    <Link to={idPath(a.canonical_id)} className="card card-hover as-card">
      <div className="as-card-head">
        <strong>{a.name}</strong>
        {a.provider && <span className="dim">{a.provider}</span>}
      </div>
      <div className="as-tags"><Tags tags={a.tags} /></div>
      <p className="tnum as-counts">
        <b>{plural(a.people, 'person', 'people')}</b>, <b>{plural(a.reports, 'report')}</b>
        {a.newest && <span className="dim"> · newest {fmtDayUtc(a.newest)}</span>}
      </p>
      {a.top_jobs.length > 0 && (
        <p className="dim as-jobs">Most discussed jobs: {a.top_jobs.map((j) => `${j.name} (${plural(j.people, 'person', 'people')})`).join(', ')}</p>
      )}
    </Link>
  )
}

function cell(c) {
  if (!c || !c.reports) return <span className="dim">No reports</span>
  return <span className="tnum">{c.working} working, {c.neutral} neutral, {c.problems} problems</span>
}

function Compare({ group, reported }) {
  if (!reported.length) return null
  return (
    <div className="tablewrap as-compare">
      <table>
        <caption className="dim as-caption">Reports per job or capability, counted, not ranked. Only assistants with reports are listed.</caption>
        <thead>
          <tr>
            <th scope="col">Assistant</th>
            {group.compare.map((r) => <th scope="col" key={`${r.kind}-${r.slug}`}>{r.name} <span className="dim">({r.kind})</span></th>)}
          </tr>
        </thead>
        <tbody>
          {reported.map((a) => (
            <tr key={a.canonical_id}>
              <th scope="row"><Link to={idPath(a.canonical_id)}>{a.name}</Link></th>
              {group.compare.map((r) => (
                <td key={`${r.kind}-${r.slug}`}>{cell(r.cells.find((c) => c.canonical_id === a.canonical_id))}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Group({ g }) {
  const reported = g.assistants.filter((a) => a.state === 'reports')
  const silent = g.assistants.filter((a) => a.state !== 'reports')
  return (
    <div className="stack stack-3">
      <p className="muted">{g.what}</p>
      {reported.length > 0 && <div className="as-grid">{reported.map((a) => <Card key={a.canonical_id} a={a} />)}</div>}
      {silent.length > 0 && (
        <p className="as-silent">
          <b>No reports yet ({silent.length}):</b>{' '}
          {silent.map((a, i) => (
            <span key={a.canonical_id}>{i > 0 && ', '}<Link to={idPath(a.canonical_id)}>{a.name}</Link></span>
          ))}
          . <span className="dim">An absence of reports, not a verdict: nobody has been reported discussing them, which says nothing about how they work.</span>
        </p>
      )}
      <p className="dim tnum">
        {g.not_in_registry > 0
          ? `Not yet in the registry: ${g.not_in_registry} of ${g.members} in this group. They are not shown because there is nothing to count yet.`
          : `All ${g.members} in this group are in the registry.`}
      </p>
      <Compare group={g} reported={reported} />
    </div>
  )
}

/** One choice of three: `tablist` and `tab`, arrow keys move, the choice is the address. */
function GroupTabs({ groups, active, onPick }) {
  const move = (e, i) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key]
    const to = e.key === 'Home' ? 0 : e.key === 'End' ? groups.length - 1
      : step ? (i + step + groups.length) % groups.length : null
    if (to === null) return
    e.preventDefault()
    onPick(groups[to].key)
    document.getElementById(`as-tab-${groups[to].key}`)?.focus()
  }
  return (
    <div className="tabstrip" role="tablist" aria-label="Kind of assistant">
      {groups.map((g, i) => (
        <button key={g.key} type="button" role="tab" id={`as-tab-${g.key}`}
                aria-selected={g.key === active} aria-controls="as-panel"
                tabIndex={g.key === active ? 0 : -1}
                onClick={() => onPick(g.key)} onKeyDown={(e) => move(e, i)}>
          {g.title} <span className="x">{g.assistants.filter((a) => a.state === 'reports').length}</span>
        </button>
      ))}
    </div>
  )
}

function List() {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  const [params, setParams] = useSearchParams()
  useHead(assistantsHead())
  useEffect(() => {
    let alive = true
    assistantsPage()
      .then((d) => alive && setState({ data: d, err: null, unreadable: null }))
      .catch((e) => alive && setState({
        data: null,
        err: e instanceof BoardUnreadable ? null : e.message,
        unreadable: e instanceof BoardUnreadable ? e.message : null,
      }))
    return () => { alive = false }
  }, [])
  const { data, err, unreadable } = state
  // An unknown ?group= opens the first group rather than an empty panel.
  const groups = data ? data.groups : []
  const asked = params.get('group')
  const active = (groups.find((g) => g.key === asked) || groups[0] || {}).key
  const shown = groups.find((g) => g.key === active)
  const pick = (key) => setParams(key === groups[0].key ? {} : { group: key }, { replace: true })
  return (
    <div className="shell section-tight stack stack-4">
      <header className="stack stack-2">
        <h1>AI assistants: what engineers report</h1>
        <p className="muted">Assistants that work for you, with you, or code with you. The list is counted from our evidence collection; an assistant&apos;s own page shows the reports behind its counts.</p>
      </header>
      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice>{err}</Notice>}
      {!data && !err && !unreadable && <p className="dim">Loading.</p>}
      {data && (
        <>
          <p className="dim">{data.unit_note}</p>
          <GroupTabs groups={groups} active={active} onPick={pick} />
          <div id="as-panel" role="tabpanel" aria-labelledby={`as-tab-${active}`} key={active} className="stack stack-3">
            <h2>{shown.title}</h2>
            <Group g={shown} />
          </div>
          {data.unclassified.length > 0 && (
            <section className="stack stack-2" aria-labelledby="as-unclassified">
              <h2 id="as-unclassified">Not yet classified</h2>
              <p className="muted">In the registry as an agent, but in none of the groups above. Not guessed into one.</p>
              <ul>
                {data.unclassified.map((u) => <li key={u.canonical_id}>{u.name}{u.provider && <span className="dim"> ({u.provider})</span>}</li>)}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}

/** The reports behind one job's or problem's counts: 3 at first, the rest on request. */
function Support({ ev }) {
  const [all, setAll] = useState(false)
  if (!ev) return null
  const list = all ? ev.items : ev.items.slice(0, SHOWN)
  return (
    <div className="stack stack-2 as-support">
      {list.map((it, i) => (
        <article className="ev-item" key={i}>
          <div className="ev-meta">
            <Posted at={it.posted_at} />
            <PolarityChip polarity={it.polarity} />
          </div>
          {it.text && <blockquote className="ev-text as-quote">{it.text}</blockquote>}
          <SourceLine source={it.source} />
        </article>
      ))}
      {ev.items.length > SHOWN && (
        <button type="button" className="btn btn-ghost" aria-expanded={all} onClick={() => setAll(!all)}>
          {all ? 'Show fewer' : `Show ${ev.items.length - SHOWN} more`}
        </button>
      )}
      {ev.omitted > 0 && (
        <p className="dim as-omitted">{plural(ev.omitted, 'report')} from sources we don&apos;t show publicly: counted above, not shown.</p>
      )}
    </div>
  )
}

function Rows({ rows, empty }) {
  if (!rows.length) return <p className="dim">{empty}</p>
  return (
    <div className="tablewrap">
      <table>
        <thead><tr><th scope="col">Name</th><th scope="col">People</th><th scope="col">Reports</th><th scope="col">Working</th><th scope="col">Neutral</th><th scope="col">Problems</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.slug}>
              <th scope="row">{r.name}</th>
              <td className="tnum">{r.people}</td>
              <td className="tnum">{r.reports}</td>
              <td className="tnum">{r.working}</td>
              <td className="tnum">{r.neutral}</td>
              <td className="tnum">{r.problems}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Detail({ id }) {
  const [state, setState] = useState({ data: null, err: null, unreadable: null, notFound: false })
  useHead(assistantsHead(state.data?.assistant?.name || null, id))
  useEffect(() => {
    let alive = true
    setState({ data: null, err: null, unreadable: null, notFound: false })
    assistantDetail(id)
      .then((d) => alive && setState({ data: d, err: null, unreadable: null, notFound: false }))
      .catch((e) => alive && setState({
        data: null,
        notFound: e.status === 404,
        err: e.status === 404 || e instanceof BoardUnreadable ? null : e.message,
        unreadable: e instanceof BoardUnreadable ? e.message : null,
      }))
    return () => { alive = false }
  }, [id])
  const { data, err, unreadable, notFound } = state
  if (notFound) return <NotFound />
  if (!data) {
    return (
      <div className="shell section-tight stack stack-4">
        {unreadable && <Unreadable detail={unreadable} />}
        {err && <Notice>{err}</Notice>}
        {!unreadable && !err && <p className="dim">Loading.</p>}
      </div>
    )
  }
  const a = data.assistant
  const e = data.evidence
  return (
    <div className="shell section-tight stack stack-4">
      <nav aria-label="Breadcrumb" className="dim"><Link to="/ai-assistants">AI assistants</Link> / {a.name}</nav>
      <header className="stack stack-2">
        <h1>{a.name}</h1>
        <p className="muted">{a.provider && <>{a.provider} · </>}{data.group.title}: {data.group.what}</p>
        <div className="as-tags"><Tags tags={data.tags} /></div>
        {data.freshness.updated_at || data.freshness.newest_report_at ? (
          <p className="dim">
            {data.freshness.updated_at && <>Updated {fmtDayUtc(data.freshness.updated_at)}. </>}
            {data.freshness.newest_report_at && <>Newest report written {fmtDayUtc(data.freshness.newest_report_at)}.</>}
          </p>
        ) : null}
      </header>

      {data.state === 'no_reports' ? <NoReports /> : (
        <section className="stack stack-2">
          <h2>What was reported</h2>
          <p className="tnum">
            <b>{plural(e.people, 'person', 'people')}</b>, <b>{plural(e.reports, 'report')}</b>, from <b>{plural(e.platforms, 'platform')}</b>
            {e.newest && <span className="dim"> · newest report {fmtDayUtc(e.newest)}</span>}
          </p>
          <p className="dim">People are distinct authors; reports are distinct documents. The platform count leaves out sources the board never names publicly.</p>
          <p className="dim">{data.quotes_note} {data.paraphrases_note}</p>
        </section>
      )}

      {data.state !== 'no_reports' && (
        <>
          <section className="stack stack-3">
            <h2>Best tasks</h2>
            <p className="dim">Jobs people used it for, most people first. Working, neutral and problems count reports; the reports themselves are beneath.</p>
            {data.best_for.length === 0 && <p className="dim">No job has been reported for this assistant yet. An absence, not a verdict.</p>}
            {data.best_for.map((r) => (
              <article key={r.slug} className="card card-body stack stack-2">
                <h3>{r.name}</h3>
                <p className="tnum">
                  <b>{plural(r.people, 'person', 'people')}</b>, <b>{plural(r.reports, 'report')}</b>: {r.working} working, {r.neutral} neutral, {r.problems} problems
                </p>
                <Support ev={r.evidence} />
              </article>
            ))}
          </section>

          <section className="stack stack-3">
            <h2>Problems reported</h2>
            {data.problems.length > 0 ? (
              <>
                <p className="dim">Capabilities where at least {data.problems_min_people} different people reported problems.</p>
                {data.problems.map((p) => (
                  <article key={p.slug} className="card card-body stack stack-2">
                    <h3>{p.name}</h3>
                    <p className="tnum">
                      <b>{plural(p.people_with_problems, 'person', 'people')}</b> reported problems
                      {' '}({plural(p.people_it_works_for, 'person', 'people')} reported it working){p.latest && <span className="dim">, latest {fmtDayUtc(p.latest)}</span>}
                    </p>
                    <Support ev={p.evidence} />
                  </article>
                ))}
              </>
            ) : (
              <p className="dim">No capability has problems reported by {data.problems_min_people ?? 'enough'} or more people. That is a count against a threshold, not a clean bill of health.</p>
            )}
          </section>

          <section className="stack stack-2">
            <h2>Capabilities</h2>
            <Rows rows={data.capabilities} empty="No capability has been reported for this assistant yet. An absence, not a verdict." />
          </section>
        </>
      )}

      <section className="stack stack-2">
        <h2>How-to guides</h2>
        {data.guides.length > 0
          ? <ul>{data.guides.map((g) => <li key={g.path}><Link to={g.path}>{g.title}</Link></li>)}</ul>
          : <p className="dim">{data.guides_note}</p>}
      </section>

      <section className="stack stack-2">
        <h2>The full evidence</h2>
        <p className="dim">Every quoted report for this assistant, with the engineers&apos; own words, is behind the sign-in.</p>
        <p><Link to={`/models/${modelPath(a.canonical_id)}`} rel="nofollow">See the quoted evidence (sign-in required)</Link></p>
      </section>
    </div>
  )
}

export default function Assistants() {
  const rest = useParams()['*'] || ''
  const id = rest.split('/').filter(Boolean).map(decodeURIComponent).join('/')
  return id ? <Detail id={id} /> : <List />
}
