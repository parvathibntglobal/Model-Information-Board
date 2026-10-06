import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { blogPosts, startBlogGeneration, blogGenerationStatus, blogGenerationLog, blogRuns, reviewBlogPost, storeBlogDrafts } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconGrid } from './Icons'

/**
 * Blogs: the drafts the generator wrote, and the control that writes more.
 *
 * WIRED TO THE TEAM'S BLOG BACKEND (2026-10-06), and nothing of its own:
 *   GET  /blog-posts           the drafts - files in BLOG_POSTS_DIR, read by
 *                              `judge/blog_posts.py`
 *   POST /blog-posts/generate  starts `generate_sample_blogs.py --plan 3` in the
 *                              background; refused (403) unless the backend is
 *                              local development, and one run at a time (409)
 *   GET  /blog-posts/generate  that run's progress and its provider-reported cost
 *   GET  /blog-posts/generate/log  the run's console log, keys masked
 * Generating lives HERE ONLY: the Blogs page's button was moved to this panel
 * (2026-10-06), since posts are approved from the admin page.
 *
 * RUN HISTORY AND REVIEW LIVE IN THE SHARED DATABASE (`judge/blog_runs.py`,
 *   migration 20261006T1200): every generation run is a row with its cost,
 *   tokens and log, and every decision is a row.
 *
 * THE POSTS LIVE THERE TOO (`judge/blog_store.py`, migration 20261006T1500),
 *   so every machine and the hosted platform review the same posts:
 *     pending    a run's drafts are stored when it finishes; anything else on
 *                this machine is stored with "Store them as drafts"
 *     approved   shown on the Blogs page (filtered on the server)
 *     rejected   CONTENT DELETED - only the slug, plan key and decision stay, so
 *                the planner never writes it again. Cannot be moved back.
 *
 * ⚠ GENERATING SPENDS MONEY, so the button asks first.
 */

const COUNT = 3
export const RUNNING = new Set(['starting', 'running'])
const PROBLEM = new Set(['failed', 'partial', 'stalled'])
const ITEM_TONE = { done: 'pass', failed: 'fail', queued: 'mute' }

function day(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null
    : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

/** The run in progress, or the last one if it needs attention. */
export function RunStatus({ gen }) {
  if (!gen || gen.state === 'idle') return null
  const running = RUNNING.has(gen.state)
  const items = gen.items || []
  if (!running && !PROBLEM.has(gen.state) && !items.length) return null
  const done = items.filter((i) => i.state === 'done').length
  return (
    <div className="stack stack-2">
      <div className="row" style={{ gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span className="label">{running ? 'Generating now' : 'Last run'}</span>
        <Badge tone={running ? 'info' : PROBLEM.has(gen.state) ? 'fail' : 'mute'}>{gen.state}</Badge>
        {items.length > 0 && <span className="dim tnum" style={{ fontSize: 11 }}>{done} of {items.length} written</span>}
        {/* The provider's own figure, as the run recorded it - not an estimate. */}
        {gen.cost_usd != null && (
          <span className="dim tnum" style={{ fontSize: 11 }}>· ${Number(gen.cost_usd).toFixed(4)} so far, provider-reported</span>
        )}
        {gen.model && <span className="dim mono" style={{ fontSize: 11 }}>· {gen.model}</span>}
      </div>
      {gen.message && PROBLEM.has(gen.state) && (
        <Notice icon={<IconAlert />}>{gen.message}</Notice>
      )}
      {items.length > 0 && (
        <div className="tablewrap"><table>
          <thead><tr><th>Format</th><th>Subject</th><th>State</th></tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.key}>
                <td>{i.format}</td>
                <td className="dim">{i.subject}</td>
                <td><Badge tone={ITEM_TONE[i.state] || 'info'}>{i.state}{i.attempt ? ` · try ${i.attempt}` : ''}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </div>
  )
}

/**
 * THE RUN'S OWN LOG, live while it runs and kept afterwards: each planned post,
 * each post written with its calls, cost and tokens, and every failure - the
 * generator's console, read through GET /blog-posts/generate/log. Pinned to
 * the newest line while running.
 */
export function RunLog({ running, tick }) {
  const [log, setLog] = useState(null)
  const box = useRef(null)
  useEffect(() => {
    let alive = true
    blogGenerationLog()
      .then((d) => alive && setLog(d))
      .catch((e) => alive && setLog({ lines: [], err: e.message }))
    return () => { alive = false }
  }, [tick])
  useEffect(() => {
    if (running && box.current) box.current.scrollTop = box.current.scrollHeight
  }, [log, running])
  if (!log) return null
  if (log.err) return <p className="dim" style={{ fontSize: 11, margin: 0 }}>The run log could not be read: {log.err}</p>
  if (!log.exists) return <p className="dim" style={{ fontSize: 11, margin: 0 }}>No generation run has written a log on this backend yet.</p>
  if (log.unreadable) return <p className="dim" style={{ fontSize: 11, margin: 0 }}>The run log exists but could not be read ({log.unreadable}).</p>
  return (
    <details className="fold" open={running || undefined}>
      <summary>
        <span className="label">Run log</span>
        <span className="dim" style={{ fontSize: 11 }}>{log.lines.length} line{log.lines.length === 1 ? '' : 's'}{running ? ' · live' : ' · last run'}</span>
      </summary>
      <pre ref={box} className="mono prompt-text capped blog-log" tabIndex={0}>
        {log.lines.length ? log.lines.join('\n') : 'The log is empty so far.'}
      </pre>
    </details>
  )
}

/** Every recorded run, newest first; each opens onto the log it stored. */
export function RunHistory({ runs }) {
  if (!runs.length) {
    return <p className="dim" style={{ fontSize: 11, margin: 0 }}>No generation run recorded yet. Runs started from here are recorded from now on.</p>
  }
  return (
    <div>
      {runs.map((r) => (
        <details key={r.id} className="disc disc-row">
          <summary>
            <span>{when(r.started_at)}</span>
            <Badge tone={r.state === 'done' ? 'mute' : RUNNING.has(r.state) || !r.finished_at ? 'info' : 'fail'}>
              {r.finished_at ? r.state : 'in progress'}
            </Badge>
            <span className="n">
              {(r.posts_written || []).length} written · {(r.posts_failed || []).length} failed
            </span>
            <span className="disc-when">
              {r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : 'cost not reported'}
              {r.tokens_in != null && ` · ${r.tokens_in.toLocaleString()} in / ${r.tokens_out.toLocaleString()} out tokens`}
            </span>
          </summary>
          <div className="disc-body stack stack-2">
            <span className="dim" style={{ fontSize: 11 }}>
              Asked for {r.requested_count}{r.model ? ` · ${r.model}` : ''}{r.message ? ` · ${r.message}` : ''}
              {r.finished_at ? ` · finished ${when(r.finished_at)}` : ''}
            </span>
            {(r.posts_written || []).length > 0 && (
              <span className="dim" style={{ fontSize: 11 }}>Wrote: {r.posts_written.join(', ')}</span>
            )}
            <pre className="mono prompt-text capped blog-log" tabIndex={0}>
              {r.log || 'No log was stored for this run.'}
            </pre>
          </div>
        </details>
      ))}
    </div>
  )
}

function when(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso
    : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

const TABS = [
  ['drafts', 'Drafts'],
  ['approved', 'Approved'],
  ['rejected', 'Rejected'],
]

export default function BlogsPanel() {
  const [posts, setPosts] = useState({ data: null, err: null })
  const [hist, setHist] = useState({ data: null, err: null })
  const [gen, setGen] = useState(null)
  const [startErr, setStartErr] = useState(null)
  const [tab, setTab] = useState('drafts')
  const [busy, setBusy] = useState(null)
  const [reviewErr, setReviewErr] = useState(null)
  const [storeMsg, setStoreMsg] = useState(null)
  const timer = useRef(null)

  const load = useCallback(() => blogPosts({ review: true })
    .then((d) => setPosts({ data: d, err: null }))
    .catch((e) => setPosts({ data: null, err: e.message })), [])

  const loadHist = useCallback(() => blogRuns()
    .then((d) => setHist({ data: d, err: null }))
    .catch((e) => setHist({ data: null, err: e.message })), [])

  const poll = useCallback(() => {
    clearTimeout(timer.current)
    blogGenerationStatus()
      .then((s) => {
        setGen((prev) => {
          // A run that just finished brings its new drafts and its history row in.
          if (prev && RUNNING.has(prev.state) && !RUNNING.has(s.state)) { load(); loadHist() }
          return s
        })
        if (RUNNING.has(s.state)) timer.current = setTimeout(poll, 4000)
      })
      .catch(() => {}) // the drafts still list; the status line simply does not show
  }, [load, loadHist])

  useEffect(() => {
    load()
    loadHist()
    poll() // a run already going is picked up, not missed
    return () => clearTimeout(timer.current)
  }, [load, loadHist, poll])

  const running = gen && RUNNING.has(gen.state)
  const onGenerate = () => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Generate ${COUNT} more posts? This calls a paid model; the drafts are stored for review when the run finishes.`)) return
    setStartErr(null)
    setGen({ state: 'starting', items: [] })
    startBlogGeneration(COUNT)
      .then((s) => {
        setGen(s)
        if (s.history_unrecorded) setStartErr(`started, but this run is not being recorded: ${s.history_unrecorded}`)
        loadHist()
        timer.current = setTimeout(poll, 2000)
      })
      .catch((e) => { setStartErr(e.message); poll() })
  }

  const decide = (slug, decision) => {
    let reason = null
    if (decision === 'rejected') {
      // eslint-disable-next-line no-alert
      if (!window.confirm('Reject this post? Its content is DELETED. Only the decision and its reason are kept, and it cannot be moved back.')) return
      // eslint-disable-next-line no-alert
      reason = window.prompt('Why is it rejected? (optional, kept with the decision)', '')
      if (reason === null) return
    }
    setBusy(slug)
    setReviewErr(null)
    reviewBlogPost(slug, decision, reason)
      .then(() => { loadHist(); load() })
      .catch((e) => setReviewErr(`${slug}: ${e.message}`))
      .finally(() => setBusy(null))
  }

  const onStore = () => {
    setStoreMsg(null)
    setBusy('store')
    storeBlogDrafts()
      .then((r) => {
        const parts = [`${r.stored.length} stored`]
        if (r.already.length) parts.push(`${r.already.length} already stored, left as they were`)
        if (r.refused.length) parts.push(`${r.refused.length} refused: ${r.refused.map((x) => `${x.slug} (${x.why})`).join('; ')}`)
        setStoreMsg(parts.join(' · '))
        load()
      })
      .catch((e) => setStoreMsg(`Could not store the drafts: ${e.message}`))
      .finally(() => setBusy(null))
  }

  const data = posts.data
  const live = data?.posts || []
  const tombstones = data?.rejected || []
  const unstored = data?.unstored || []
  const stateOf = (p) => (p.review === 'approved' ? 'approved' : 'drafts')
  // Built from TABS, so the tab keys and their counts cannot drift apart.
  const counts = Object.fromEntries(TABS.map(([k]) => [k, 0]))
  for (const p of live) counts[stateOf(p)] += 1
  counts[TABS[2][0]] = tombstones.length
  const list = live.filter((p) => stateOf(p) === tab)
  const ok = data && !data.reason

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconGrid width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Blogs — drafts from the evidence, for approval</span>
        </div>
        {ok && <span className="label">{live.length} post{live.length === 1 ? '' : 's'}</span>}
      </div>

      <div className="card-intro">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Written by a language model from engineers&apos; public reports and checked in code. Generating plans
          the next posts from the board&apos;s evidence;{' '}
          <strong style={{ color: 'var(--text)' }}>it calls a paid model</strong> and runs only on a local
          development backend, one run at a time. Posts are kept in the shared database, so everyone reviews
          the same ones, and a post reaches the Blogs page only once approved here.
        </p>
      </div>

      <div className="card-body stack stack-3">
        <div className="row-between" style={{ gap: 'var(--s3)', flexWrap: 'wrap', alignItems: 'center' }}>
          <div className="row" style={{ gap: 6 }} role="tablist" aria-label="Post status">
            {TABS.map(([key, label]) => (
              <button key={key} type="button" role="tab" aria-selected={tab === key}
                      className={`chip${tab === key ? ' chip-on' : ''}`} onClick={() => setTab(key)}>
                {label} <span className="x">{counts[key]}</span>
              </button>
            ))}
          </div>
          {/* LOGS BESIDE GENERATE: the record of what runs did sits next to the
              control that starts one. Logs opens its own page, so it is a
              link styled as a button, with an arrow that says "goes somewhere". */}
          <div className="row" style={{ gap: 8, alignItems: 'center' }}>
            <Link to="/admin/blog-logs" className="btn btn-ghost blog-logs-btn">
              Logs <span className="x tnum">{(hist.data?.runs || []).length}</span>
              <span aria-hidden="true">→</span>
            </Link>
            {/* THE PANEL'S MAIN ACTION, so it is the one filled button on it. */}
            <button type="button" className="btn btn-primary blog-gen-btn" disabled={running} onClick={onGenerate}>
              {running ? 'Generating…' : `Generate ${COUNT} more posts`}
            </button>
          </div>
        </div>

        {startErr && <Notice icon={<IconAlert />}>{startErr}</Notice>}
        <RunStatus gen={gen} />

        {posts.err && <Notice icon={<IconAlert />}>The posts could not be read: {posts.err}</Notice>}
        {reviewErr && <Notice icon={<IconAlert />}>Could not record the decision for {reviewErr}</Notice>}
        {!data && !posts.err && <div className="skel" style={{ height: 160 }} />}

        {/* RULE 4: "the store could not be read" and "nothing stored yet" are different facts. */}
        {data?.reason && <Notice icon={<IconAlert />}>{data.reason}</Notice>}

        {/* DRAFT FILES THIS BACKEND'S MACHINE HAS AND THE STORE DOES NOT: older
            drafts, and runs started from a terminal. Named, never dropped. */}
        {ok && unstored.length > 0 && (
          <Notice icon={<IconAlert />}>
            <span>
              {unstored.length} draft{unstored.length === 1 ? '' : 's'} on this machine {unstored.length === 1 ? 'is' : 'are'} not
              stored yet, so nobody else can review {unstored.length === 1 ? 'it' : 'them'}: {unstored.map((u) => u.title || u.slug).join(' · ')}.{' '}
              <button type="button" className="btn btn-ghost prompt-btn" disabled={busy === 'store'} onClick={onStore}>
                {busy === 'store' ? 'Storing…' : 'Store them as drafts'}
              </button>
            </span>
          </Notice>
        )}
        {storeMsg && <p className="dim" style={{ fontSize: 11, margin: 0 }}>{storeMsg}</p>}
        {/* WHY THIS BACKEND HAS NO DRAFT FILES TO OFFER (BLOG_POSTS_DIR unset or
            missing) - the hosted platform, typically. Said, not left as an
            empty list that reads as "everything is stored". */}
        {ok && data.files_reason && (
          <p className="dim" style={{ fontSize: 11, margin: 0 }}>
            No draft files are read on this backend, so nothing can be stored from here: {data.files_reason}
          </p>
        )}

        {ok && tab !== 'rejected' && (
          <div className="tablewrap"><table>
            <thead>
              <tr><th>Title</th><th>Format</th><th>Written</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {list.length === 0 ? (
                <tr><td colSpan={5} className="dim">
                  {tab === 'drafts' ? 'No drafts awaiting review. Generate some above.' : 'Nothing approved yet.'}
                </td></tr>
              ) : list.map((p) => {
                const st = stateOf(p)
                return (
                  <tr key={p.slug}>
                    <td>
                      <strong style={{ fontSize: 'var(--fs-sm)' }}>{p.title}</strong>
                      {p.feat && <> <Badge tone="mute">featured</Badge></>}
                      {p.review_reason && <span className="dim" style={{ display: 'block', fontSize: 11 }}>Reason: {p.review_reason}</span>}
                    </td>
                    <td className="dim">{p.kicker || p.tag}</td>
                    <td className="dim" style={{ whiteSpace: 'nowrap' }}>
                      {day(p.provenance?.generated_at) || '—'}
                      {p.provenance?.model && (
                        <span className="mono" style={{ display: 'block', fontSize: 10 }}>{p.provenance.model}</span>
                      )}
                    </td>
                    <td>
                      <Badge tone={st === 'approved' ? 'pass' : 'mute'}>{st === 'approved' ? 'approved' : 'awaiting review'}</Badge>
                    </td>
                    <td>
                      <span className="row" style={{ gap: 6, flexWrap: 'nowrap' }}>
                        <Link to={`/blogs/${encodeURIComponent(p.slug)}`} state={{ from: 'admin' }}
                              className="btn btn-ghost prompt-btn">Preview</Link>
                        {st === 'drafts' ? (
                          <button type="button" className="btn btn-ghost prompt-btn" disabled={busy === p.slug}
                                  onClick={() => decide(p.slug, 'approved')}>Approve</button>
                        ) : (
                          <button type="button" className="btn btn-quiet prompt-btn" disabled={busy === p.slug}
                                  onClick={() => decide(p.slug, 'reopened')}>Move back to drafts</button>
                        )}
                        <button type="button" className="btn btn-quiet prompt-btn" disabled={busy === p.slug}
                                onClick={() => decide(p.slug, 'rejected')}>Reject</button>
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table></div>
        )}

        {/* REJECTED POSTS ARE TOMBSTONES: the content is gone, so there is no
            title, no preview and no way back - only what was decided and why. */}
        {ok && tab === 'rejected' && (
          <div className="tablewrap"><table>
            <thead><tr><th>Post</th><th>Rejected</th><th>Reason</th></tr></thead>
            <tbody>
              {tombstones.length === 0 ? (
                <tr><td colSpan={3} className="dim">Nothing rejected.</td></tr>
              ) : tombstones.map((t) => (
                <tr key={t.slug}>
                  <td><span className="mono" style={{ fontSize: 11 }}>{t.slug}</span>
                    {t.plan_key && <span className="dim" style={{ display: 'block', fontSize: 10 }}>{t.plan_key}</span>}</td>
                  <td className="dim" style={{ whiteSpace: 'nowrap' }}>{day(t.decided_at) || '—'}</td>
                  <td className="dim">{t.review_reason || 'No reason given'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}

        {/* A file that could not be read is named, never dropped. */}
        {data?.skipped?.length > 0 && (
          <Notice icon={<IconAlert />}>
            Could not be read: {data.skipped.map((x) => `${x.file} (${x.why})`).join('; ')}
          </Notice>
        )}

        <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
          Approval rule: a post reaches the Blogs page only after it is approved here, and Move back to drafts
          takes it off again. Rejecting deletes the post&apos;s content and keeps only the decision and its
          reason, so a rejected post cannot come back and the planner will not write it again.
        </p>
      </div>
    </section>
  )
}
