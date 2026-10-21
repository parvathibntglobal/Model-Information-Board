import { useCallback, useEffect, useState } from 'react'
import { deleteDiscussion, discussionsReview, reviewDiscussion } from '../api'
import '../styles/blog-live.css'
import '../styles/discussions.css'

/**
 * ADMIN -> DISCUSSIONS (2026-10-20): readers' posts, held for review.
 *
 * A reader posts on /discussions; the post is stored pending
 * (judge/discussions.py) and appears on the public page only once it is
 * approved here. Code has already refused posts that break a limit (length,
 * links, the honeypot); whether a post is genuine and fit to show is the
 * reviewer's call. Deciding again is allowed - a misclick is undone by
 * deciding again.
 *
 * DELETE (2026-10-20) removes a post for good - for what must not be kept at
 * all: personal data, abuse, spam. Rejecting hides a post and keeps it with
 * its reason. Delete asks first, because it cannot be undone.
 *
 * THE CHECKS LINE is a reviewer's aid, worked out here from the text: links,
 * length, and anything that looks like an email address or a phone number.
 * It flags; it decides nothing.
 */

const TABS = [['pending', 'Waiting'], ['approved', 'Approved'], ['rejected', 'Rejected']]
const LINK = /https?:\/\/|www\./gi
const EMAIL = /[\w.+-]+@[\w-]+\.[\w.]+/
const PHONE = /(?:\+?\d[\d\s().-]{8,}\d)/

/** What a reviewer should look at before approving, from the text alone. */
function checks(p) {
  const text = `${p.title || ''} ${p.body}`
  const words = p.body.trim().split(/\s+/).filter(Boolean).length
  const links = (text.match(LINK) || []).length
  const out = [
    { t: `${words} words`, warn: words < 12 },
    { t: links ? `${links} ${links === 1 ? 'link' : 'links'}` : 'no links', warn: links > 0 },
    { t: p.model_id ? 'names a model' : 'no model named', warn: false },
    { t: p.author_name ? 'named author' : 'no name', warn: false },
  ]
  if (EMAIL.test(text)) out.push({ t: 'looks like an email address', warn: true })
  if (PHONE.test(text)) out.push({ t: 'looks like a phone number', warn: true })
  return out
}

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '')

function Item({ p, onDecide, onDelete, busy }) {
  const [note, setNote] = useState('')
  return (
    <div className="qb-item">
      <div className="qb-meta">
        <span>{p.topic}</span>
        {p.model_id && <span className="mono">{p.model_id}</span>}
        <span>{p.author_name || 'A reader'}</span>
        <span className="dim">{fmt(p.created_at)}</span>
      </div>
      {p.parent_id
        ? <p className="qb-q"><span className="dim">Reply to:</span> <b>{p.parent_title || p.parent_id}</b></p>
        : <p className="qb-q"><b>{p.title}</b></p>}
      <p className="qb-why" style={{ whiteSpace: 'pre-wrap' }}>{p.body}</p>
      <div className="dp-checks" aria-label="Checks">
        {checks(p).map((c) => <span key={c.t} className={c.warn ? 'dp-warn' : ''}>{c.warn ? '⚠ ' : ''}{c.t}</span>)}
      </div>
      {p.review_note && <p className="dim qb-why">Review note: {p.review_note}</p>}
      <div className="qb-actions">
        {p.state !== 'approved' && (
          <button type="button" className="btn" disabled={busy} onClick={() => onDecide(p.id, 'approved', note)}>Approve</button>
        )}
        {p.state !== 'rejected' && (
          <>
            <input className="lv-search qb-note" placeholder="Why reject? (optional)" value={note}
                   onChange={(e) => setNote(e.target.value)} />
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => onDecide(p.id, 'rejected', note)}>Reject</button>
          </>
        )}
        {p.state !== 'pending' && (
          <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => onDecide(p.id, 'pending', '')}>Back to waiting</button>
        )}
        <button type="button" className="btn btn-ghost dp-delete" disabled={busy} onClick={() => onDelete(p)}>Delete</button>
      </div>
    </div>
  )
}

export default function DiscussionsPanel() {
  const [tab, setTab] = useState('pending')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    discussionsReview(tab).then((d) => { setData(d); setErr(null) }).catch((e) => setErr(e.message))
  }, [tab])
  useEffect(() => { load() }, [load])

  const decide = async (id, decision, note) => {
    setBusy(true)
    try { await reviewDiscussion(id, decision, note); load() } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  const remove = async (p) => {
    // it cannot be undone, so it asks - naming the post, not just "are you sure"
    const what = p.parent_id ? 'this reply' : `"${p.title}" and its replies`
    if (!window.confirm(`Delete ${what} for good? This cannot be undone. To hide it but keep it, reject it instead.`)) return
    setBusy(true)
    try { await deleteDiscussion(p.id); load() } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  if (err && !data) return <p className="dim">The discussions could not be read: {err}</p>
  if (!data) return <div className="skel" style={{ height: 160 }} />
  const c = data.counts
  return (
    <div className="stack stack-3">
      <p className="dim qb-intro">
        Readers&apos; posts from the Discussions page. Each is shown publicly only once approved here.
        Code has refused posts that break a limit; check that each one is a genuine experience, carries
        no personal data and is not advertising before approving. Reject hides a post and keeps it;
        Delete removes it for good.
      </p>
      <div className="qb-stats">
        <span><b>{c.approved}</b> approved</span>
        <span><b>{c.pending}</b> waiting</span>
        <span><b>{c.rejected}</b> rejected</span>
      </div>
      <div className="lv-seg" role="group" aria-label="Which posts">
        {TABS.map(([k, label]) => (
          <button key={k} type="button" className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      {data.items.length === 0
        ? <p className="lv-empty">{tab === 'pending' ? 'Nothing is waiting for review.' : `No ${tab} posts yet.`}</p>
        : data.items.map((p) => <Item key={p.id} p={p} onDecide={decide} onDelete={remove} busy={busy} />)}
    </div>
  )
}
