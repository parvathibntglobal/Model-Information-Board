import { useCallback, useEffect, useState } from 'react'
import { outreachCheck, outreachPosted, outreachReopen, outreachSkip, outreachThreads } from '../../api'
import '../../styles/blog-live.css'
import '../../styles/discussions.css'
import './admin.css'

/**
 * ADMIN -> KITE PULSE -> OUTREACH (2026-11-09): the phase-1 review queue.
 *
 * Threads the outreach Finders saved (web/src/kitepulse/outreach/), read from
 * outreach's own database. A person reads each one on the forum, and either
 * SKIPS it with a reason, or ANSWERS IT THERE FROM THEIR OWN ACCOUNT and pastes
 * the reply's link here. Nothing on this page posts anywhere: the backend holds
 * no forum credential (ARCHITECTURE.md section 1).
 *
 * The chips are what the Finder recorded: the phrases that matched and its
 * flags. They are not a judgement of the thread.
 *
 * ORDER (phase 2, 2026-11-09): To review is grouped by the Shortlister's row
 * (outreach/shortlist.py), the groups named in words on the page, newest
 * first within each. The model's problem, relevance and reason are shown
 * labelled as its SUGGESTION. Nothing is hidden because of it: the low, none
 * and set-aside groups are collapsed, one click away (CLAUDE.md rule 8).
 */

const TABS = [['found', 'To review'], ['posted', 'Posted'], ['skipped', 'Skipped'], ['dropped', 'Dropped']]
const SOURCE_NAMES = { hackernews: 'Hacker News', discourse: 'Discourse', devto: 'dev.to', github: 'GitHub', reddit: 'Reddit' }

// What each Finder flag means to a reviewer. An unknown flag shows as itself.
const FLAGS = {
  community_pending_review: ['Community rules not checked yet: read them before replying', true],
  team_check_partial: ['Only part of a long thread was checked for a team reply', true],
  answered: ['The asker marked an answer', false],
  posted_by_repo_owner: ['Started by the repo owner (often an announcement)', false],
}
const DROP_REASONS = {
  too_old: 'Older than the week the Finder keeps',
  closed: 'Closed, locked or archived: nobody can reply',
  no_text: 'No text to read',
  community_not_allowed: 'The community does not allow vendor replies',
  already_answered: 'A team account has already replied',
}

const SET_ASIDE = {
  too_old: 'older than the week a reply is useful in',
  hiring_thread: 'a comment in a hiring thread',
  words_far_apart: 'the matched words are far apart in the text, so it is probably not about the problem',
}
// Groups 4-6 start collapsed. A thread in them is one click away, never hidden.
const COLLAPSED_GROUPS = new Set([4, 5, 6])

const when = (iso) => (iso ? new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '')
function age(iso) {
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3600000)
  return h < 48 ? `${Math.max(h, 0)}h ago` : `${Math.floor(h / 24)}d ago`
}

function Body({ text }) {
  if (!text) return <p className="dim qb-why">No text beyond the title.</p>
  if (text.length <= 600) return <p className="qb-why kp-body">{text}</p>
  return (
    <details className="kp-more-text">
      <summary className="qb-why kp-body">{text.slice(0, 600)}… <span className="kp-link">show all</span></summary>
      <p className="qb-why kp-body">{text.slice(600)}</p>
    </details>
  )
}

// The REPLY CHECK (outreach/reply_check.py). Advisory: it does not gate Mark
// posted, and what it cannot check is listed under every result.
function CheckReply({ th }) {
  const [text, setText] = useState('')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const run = async () => {
    setBusy(true); setErr(null)
    try { setRes(await outreachCheck(th.id, text)) } catch (e) { setErr(e.message); setRes(null) }
    setBusy(false)
  }
  return (
    <details className="kp-more-text">
      <summary className="kp-link">Check my reply before posting</summary>
      <div className="stack stack-2" style={{ marginTop: 8 }}>
        <div className="dc-reply-box">
          <textarea value={text} onChange={(e) => { setText(e.target.value); setRes(null) }}
                    placeholder="Paste the reply you are about to post, disclosure line included"
                    aria-label="Reply to check" />
        </div>
        <div className="qb-actions">
          <button type="button" className="btn btn-ghost" disabled={busy || !text.trim()} onClick={run}>
            Check
          </button>
        </div>
        {err && <p className="kp-error" role="alert">{err}</p>}
        {res && (
          <div className={`kp-check ${res.passed ? 'kp-check-pass' : 'kp-check-fail'}`} role="status">
            <b>{res.passed
              ? 'Keeps the posting rules.'
              : `Breaks ${res.failures.length} posting rule${res.failures.length === 1 ? '' : 's'}:`}</b>
            {res.failures.length > 0 && (
              <ul>{res.failures.map((f, i) => <li key={i}><code>{f.code}</code> {f.detail}</li>)}</ul>
            )}
            <span className="dim">
              {res.chars} of {res.max_chars} characters
              {res.claims_used.length > 0 && <>; approved sentence used: {res.claims_used.join(', ')}</>}
            </span>
            {res.warnings.map((w, i) => <span key={i} className="dim">⚠ {w}</span>)}
            <span className="dim">
              Not checked, so still yours to judge: {res.not_checked.join('; ')}.
            </span>
          </div>
        )}
      </div>
    </details>
  )
}

function Decide({ th, reasons, onDone }) {
  const [reason, setReason] = useState('not_relevant')
  const [note, setNote] = useState('')
  const [url, setUrl] = useState('')
  const [account, setAccount] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const run = async (call) => {
    setBusy(true); setErr(null)
    try { await call(); onDone() } catch (e) { setErr(e.message) }
    setBusy(false)
  }
  return (
    <div className="stack stack-2">
      <div className="qb-actions">
        <select className="kp-pick" value={reason} onChange={(e) => setReason(e.target.value)}
                aria-label="Why skip">
          {Object.entries(reasons).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
        <input className="lv-search qb-note" value={note} onChange={(e) => setNote(e.target.value)}
               placeholder={reason === 'other' ? 'Why? (required)' : 'Note (optional)'} maxLength={500} />
        <button type="button" className="btn btn-ghost" disabled={busy}
                onClick={() => run(() => outreachSkip(th.id, reason, note))}>Skip</button>
      </div>
      <CheckReply th={th} />
      <div className="qb-actions">
        <input className="lv-search kp-url" value={url} onChange={(e) => setUrl(e.target.value)}
               placeholder="Link to YOUR reply, after posting it" />
        <input className="lv-search qb-note" value={account} onChange={(e) => setAccount(e.target.value)}
               placeholder="Account you posted from" maxLength={100} />
        <button type="button" className="btn" disabled={busy || !url.trim() || !account.trim()}
                onClick={() => run(() => outreachPosted(th.id, url, account))}>Mark posted</button>
      </div>
      {err && <p className="kp-error" role="alert">{err}</p>}
    </div>
  )
}

function Decided({ th, reasons, onDone }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const reopen = async () => {
    setBusy(true); setErr(null)
    try { await outreachReopen(th.id); onDone() } catch (e) { setErr(e.message) }
    setBusy(false)
  }
  const by = th.decided_by || 'someone (no signed-in identity was recorded)'
  return (
    <div className="stack stack-2">
      {th.status === 'posted' ? (
        <p className="qb-why">
          Posted by <b>{th.posted_by_account}</b>:{' '}
          <a href={th.posted_url} target="_blank" rel="noreferrer">{th.posted_url}</a>
          <br /><span className="dim">Link checked against the thread: {th.url_check}</span>
        </p>
      ) : (
        <p className="qb-why">
          Skipped: <b>{reasons[th.skip_reason] || th.skip_reason}</b>{th.skip_note ? `. ${th.skip_note}` : ''}
        </p>
      )}
      <p className="dim qb-why">{when(th.decided_at)}, by {by}</p>
      <div className="qb-actions">
        <button type="button" className="btn btn-ghost" disabled={busy} onClick={reopen}>Back to review</button>
      </div>
      {err && <p className="kp-error" role="alert">{err}</p>}
    </div>
  )
}

// What the Shortlister recorded for this thread. A model's answer is labelled
// as a suggestion; code's set-aside says it was code.
function Suggestion({ sl }) {
  if (!sl) return <p className="dim qb-why">Not sorted yet: the Shortlister has not read this thread.</p>
  if (sl.outcome === 'set_aside') {
    return <p className="dim qb-why">Set aside by code, not sent to the model: {SET_ASIDE[sl.set_aside_reason] || sl.set_aside_reason}.</p>
  }
  if (sl.outcome === 'invalid') {
    return <p className="dim qb-why">The model&apos;s answer failed the checks ({sl.invalid_why}), so it is not used to sort.</p>
  }
  return (
    <div className="qb-why kp-suggest">
      <span className="dim">Model&apos;s suggestion ({sl.model}):</span>{' '}
      <b>{sl.problem === 'none' ? 'none of our problems' : `${sl.problem}, ${sl.relevance} relevance`}</b>
      <br /><span className="dim">Why:</span> {sl.reason}
      {sl.article_slug && <span className="dim"> Article: {sl.article_slug}{sl.slug_verified ? '' : ' (not in the article index, not used)'}.</span>}
      <CallCost sl={sl} />
    </div>
  )
}

// What the call behind this suggestion used. A figure the provider did not
// report says so; it is never shown as 0.
const num = (n) => (n == null ? 'not reported' : Number(n).toLocaleString('en-GB'))
const usd = (v) => (v == null ? 'cost not reported' : `$${Number(v).toFixed(6)}`)
function CallCost({ sl }) {
  return (
    <>
      <br />
      <span className="dim kp-tokens">
        This call: {num(sl.input_tokens)} tokens in, {num(sl.output_tokens)} out, {usd(sl.usd)}
      </span>
    </>
  )
}

// Every outreach model call, from kp_outreach_spend. All sources and steps,
// including calls repeated after a prompt change, so it can be more than the
// per-thread figures add up to.
function UsageRow({ label, u }) {
  if (!u.calls) return <div className="kp-summary-row"><span>{label}: no model calls</span></div>
  const floor = u.unpriced_calls > 0 || u.unmetered_calls > 0
  return (
    <div className="kp-summary-row">
      <span>{label}:</span>
      <span><b>{u.calls}</b> call{u.calls === 1 ? '' : 's'}</span>
      <span><b>{num(u.input_tokens)}</b> tokens in</span>
      <span><b>{num(u.output_tokens)}</b> tokens out</span>
      <span><b>{u.usd == null ? 'no cost reported' : `$${Number(u.usd).toFixed(4)}`}</b></span>
      {floor && (
        <span className="dp-warn">
          ⚠ at least: {u.unpriced_calls > 0 && `${u.unpriced_calls} call(s) reported no cost`}
          {u.unpriced_calls > 0 && u.unmetered_calls > 0 && ', '}
          {u.unmetered_calls > 0 && `${u.unmetered_calls} reported no tokens`}
        </span>
      )}
    </div>
  )
}

function Usage({ u }) {
  const today = u.today
  return (
    <div className="kp-summary" aria-label="Model usage">
      <b>Model usage (tokens and cost, as OpenRouter reported them)</b>
      <UsageRow label="Today (UTC)" u={today} />
      <UsageRow label="All time" u={u.all_time} />
      <span className="dim">
        {u.daily_budget_usd
          ? `Daily cap $${Number(u.daily_budget_usd).toFixed(2)}${today.usd != null
            ? `: $${Math.max(Number(u.daily_budget_usd) - Number(today.usd), 0).toFixed(4)} left today` : ''}. `
          : `Daily cap not readable here: ${u.budget_problem} `}
        Counts every outreach model call, including repeats after a prompt change.
      </span>
    </div>
  )
}

const VIEWS = [
  ['all', 'All threads'],
  ['sent', 'Sent to the model'],
  ['selected', 'Selected by the model'],
]
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

// What the Shortlister did with To review, as counts. Computed by the backend
// over the source and problem filters, the same whichever view is open.
function ShortlistSummary({ s }) {
  const g = Object.fromEntries(s.groups.map((x) => [x.group, x.count]))
  const reasons = Object.entries(s.set_aside_by_reason)
    .map(([k, n]) => `${n} ${k.replaceAll('_', ' ')}`).join(', ')
  return (
    <div className="kp-summary" aria-label="What the Shortlister did">
      <div className="kp-summary-row">
        <span><b>{s.total}</b> in To review</span>
        <span><b>{s.sent_to_model}</b> sent to the model</span>
        <span><b>{s.set_aside}</b> set aside by code{reasons && <span className="dim"> ({reasons})</span>}</span>
        <span><b>{s.not_sorted}</b> not sorted yet</span>
      </div>
      {s.sent_to_model > 0 && (
        <div className="kp-summary-row dim">
          <span>Of the {s.sent_to_model} sent, the model suggested:</span>
          <span><b>{g[1] || 0}</b> high</span>
          <span><b>{g[2] || 0}</b> medium</span>
          <span><b>{g[4] || 0}</b> low</span>
          <span><b>{g[5] || 0}</b> none of our problems</span>
          {s.model_answer_failed_checks > 0 && (
            <span><b>{s.model_answer_failed_checks}</b> answers failed the checks</span>
          )}
        </div>
      )}
    </div>
  )
}

function Thread({ th, reasons, onDone }) {
  return (
    <div className="qb-item">
      <div className="qb-meta">
        <span>{SOURCE_NAMES[th.source] || th.source}</span>
        <span className="mono">{th.community}</span>
        <span>{th.kind}</span>
        <span title={when(th.created_at)}>{age(th.created_at)}</span>
        {th.author && <span>by {th.author}</span>}
        <span>{th.matched_problems.join(', ')}</span>
      </div>
      <p className="qb-q">
        <a href={th.url} target="_blank" rel="noreferrer"><b>{th.title || '(no title)'}</b> ↗</a>
      </p>
      <Body text={th.body} />
      <div className="dp-checks" aria-label="What the Finder recorded">
        {th.matched_phrases.map((p) => <span key={`p-${p}`}>“{p}”</span>)}
        {th.flags.map((f) => {
          const [label, warn] = FLAGS[f] || [f, false]
          return <span key={`f-${f}`} className={warn ? 'dp-warn' : ''}>{warn ? '⚠ ' : ''}{label}</span>
        })}
      </div>
      {th.status === 'found' && <Suggestion sl={th.shortlist} />}
      {th.status === 'dropped' && (
        <p className="dim qb-why">Dropped by the Finder: {DROP_REASONS[th.drop_reason] || th.drop_reason}</p>
      )}
      {th.status === 'found' && <Decide th={th} reasons={reasons} onDone={onDone} />}
      {(th.status === 'posted' || th.status === 'skipped') && <Decided th={th} reasons={reasons} onDone={onDone} />}
    </div>
  )
}

export default function OutreachPanel() {
  const [tab, setTab] = useState('found')
  const [source, setSource] = useState('')
  const [problem, setProblem] = useState('')
  const [view, setView] = useState('all')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    outreachThreads({ tab, source, problem, view: tab === 'found' ? view : '' })
      .then((d) => { setData(d); setErr(null) }).catch((e) => setErr(e.message))
  }, [tab, source, problem, view])
  useEffect(() => { load() }, [load])

  if (err && !data) return <p className="dim">The outreach threads could not be read: {err}</p>
  if (!data) return <div className="skel" style={{ height: 160 }} />
  const c = data.counts
  return (
    <div className="stack stack-3">
      <p className="dim qb-intro">
        Threads the outreach Finders saved. Open a thread, and if you can genuinely help,
        answer it <b>on the forum, from your own account</b>, with a disclosure line such as
        “Disclosure: I work on Kite Pulse”. Then paste your reply&apos;s link here. This page never posts
        anything. Skip a thread with a reason: the reasons are how we learn which threads are worth reading.
      </p>
      <div className="qb-stats">
        <span><b>{c.found}</b> to review</span>
        <span><b>{c.posted}</b> posted</span>
        <span><b>{c.skipped}</b> skipped</span>
        <span><b>{c.dropped}</b> dropped by the Finder</span>
        <span className="dim">database {data.database}</span>
      </div>
      <div className="qb-actions">
        <div className="lv-seg" role="group" aria-label="Which threads">
          {TABS.map(([k, label]) => (
            <button key={k} type="button" className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>
          ))}
        </div>
        <select className="kp-pick" value={source} onChange={(e) => setSource(e.target.value)}
                aria-label="Source">
          <option value="">Every source</option>
          {data.sources.map((s) => <option key={s} value={s}>{SOURCE_NAMES[s] || s}</option>)}
        </select>
        <select className="kp-pick" value={problem} onChange={(e) => setProblem(e.target.value)}
                aria-label="Problem">
          <option value="">Every problem</option>
          {data.problems.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>
      {tab === 'found' && data.shortlist && (
        <>
          <ShortlistSummary s={data.shortlist} />
          {data.usage && <Usage u={data.usage} />}
          <div className="lv-seg" role="group" aria-label="Which threads in To review">
            {VIEWS.map(([k, label]) => (
              <button key={k} type="button" className={view === k ? 'on' : ''} onClick={() => setView(k)}>{label}</button>
            ))}
          </div>
          {view !== 'all' && (
            <p className="dim qb-why">
              {view === 'sent'
                ? `${plural(data.matching, 'thread')} the Shortlister sent to the model, with the model's reason for each. `
                : `${plural(data.matching, 'thread')} the model suggested as high or medium relevance, with its reason. `}
              Threads not shown here are still in To review: switch to All threads to see them.
            </p>
          )}
        </>
      )}
      {err && <p className="kp-error" role="alert">{err}</p>}
      {data.matching > data.items.length && (
        <p className="dim qb-why">
          Showing the newest {data.items.length} of {data.matching}. Filter by source or problem to see the rest.
        </p>
      )}
      {data.items.length === 0
        ? <p className="lv-empty">{tab !== 'found'
          ? 'No threads here yet.'
          : view === 'sent'
            ? 'No thread has been sent to the model yet. Run shortlist.py to sort To review.'
            : view === 'selected'
              ? 'The model has not suggested any thread as high or medium relevance yet.'
              : 'Nothing to review. Run a Finder to look for new threads.'}</p>
        : tab === 'found' && view === 'all' && data.shortlist
          ? <Grouped data={data} onDone={load} />
          : data.items.map((th) => <Thread key={th.id} th={th} reasons={data.skip_reasons} onDone={load} />)}
    </div>
  )
}

// To review, in the Shortlister's groups. The order is said in words: which
// group a thread is in, then newest first. No score is computed or shown.
function Grouped({ data, onDone }) {
  return (
    <div className="stack stack-3">
      <p className="dim qb-why">
        Sorted into the groups below by the Shortlister: code sets some threads aside, and a model
        suggests a problem and relevance for the rest. Newest first within each group. It only
        decides the order; every thread stays here until you skip or post.
      </p>
      {data.shortlist.groups.filter((g) => g.count > 0).map((g) => {
        const items = data.items.filter((th) => th.shortlist_group === g.group)
        const shown = items.length < g.count ? ` (showing ${items.length} of ${g.count})` : ''
        const list = items.map((th) => <Thread key={th.id} th={th} reasons={data.skip_reasons} onDone={onDone} />)
        return COLLAPSED_GROUPS.has(g.group) ? (
          <details key={g.group} className="kp-group">
            <summary><b>{g.label}</b>: {g.count}{shown}</summary>
            <div className="stack stack-3" style={{ marginTop: 8 }}>{list}</div>
          </details>
        ) : (
          <section key={g.group} className="stack stack-3">
            <h3 className="kp-group-head">{g.label}: {g.count}{shown}</h3>
            {list}
          </section>
        )
      })}
    </div>
  )
}
