import { useEffect, useMemo, useRef, useState } from 'react'
import { discussionsPage, modelCatalog, postDiscussion } from '../api'
import { useHead } from '../seo/head'
import { discussionsIndex } from '../seo/pages'
import '../styles/discussions.css'

/**
 * DISCUSSIONS (2026-10-20, Parvathi): readers' own experience with AI models,
 * by topic. A reader posts here; the post is stored PENDING and shown only once
 * a person approves it in Admin -> Discussions (judge/discussions.py). Nothing
 * typed is lost and nothing appears unreviewed. Discussions are shown beside
 * the reports and NEVER added to the counts.
 *
 * THE TOPICS AND THEIR COPY ARE THE CONTRACT'S (contract/discussions.yaml),
 * served by `/discussions`, so the page is the same keywords the file names -
 * measured ones only - and a topic with no posts yet still has its section.
 *
 * NEWEST FIRST, WITH REPLIES (2026-10-20): the server sends each topic's posts
 * newest first by when they were written, each with its approved replies
 * oldest first. Replies are typed in a box under the post and held for review
 * like a post.
 *
 * BODIES ARE PRINTED AS TEXT. React escapes them, and a link in a post is not
 * made clickable: a reader's post carries no link equity for whoever wrote it.
 */

const STEPS = [
  ['1', 'Pick a topic', 'Coding agents, AI agents, RAG, a model comparison, local LLMs, pricing, prompting or model drift.'],
  ['2', 'Say what you ran', 'The job, the model, and what happened - worked, failed, or somewhere in between.'],
  ['3', 'A person reviews it', 'Every post is read before it appears. It sits beside the reports and is never added to the counts.'],
]

const GUIDE = [
  'Write about your own use: what you ran, on which model, and what happened.',
  'Name the job - "a 40-file refactor", "RAG over contracts" - not just "it is good".',
  'No personal data, no one else\'s private messages, no advertising.',
  'Plain text. At most two links.',
]

const fmtDay = (iso) => (iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '')

/**
 * REPLYING (2026-10-20): a box under a post, opened by its Reply button. A
 * reply is held for review like a post, so the box says so once it is sent
 * rather than showing the reply straight away.
 */
function ReplyBox({ post, limits, onClose }) {
  const [f, setF] = useState({ body: '', author_name: '', website: '' })
  const [state, setState] = useState({ sending: false, sent: false, err: null })
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const L = limits || { reply_min: 10, body_max: 4000, name_min: 2, name_max: 40 }
  const ready = f.body.trim().length >= (L.reply_min || 10) && f.author_name.trim().length >= (L.name_min || 2)

  const send = async (e) => {
    e.preventDefault()
    setState({ sending: true, sent: false, err: null })
    try {
      await postDiscussion({ parent_id: post.id, ...f })
      setState({ sending: false, sent: true, err: null })
      setF({ body: '', author_name: '', website: '' })
    } catch (err) {
      setState({ sending: false, sent: false, err: err.message })
    }
  }

  if (state.sent) {
    return (
      <div className="dc-reply-box">
        <p className="dc-ok" role="status">Thank you - your reply is waiting for review. It appears under this post once a person has read it.</p>
        <button type="button" className="dc-link" onClick={onClose}>Close</button>
      </div>
    )
  }
  return (
    <form className="dc-reply-box" onSubmit={send} aria-label={`Reply to ${post.title}`}>
      <textarea value={f.body} onChange={set('body')} maxLength={L.body_max} rows={3} required autoFocus
                placeholder="Write a reply - what did you find on the same job?" />
      <div className="dc-reply-row">
        <input value={f.author_name} onChange={set('author_name')} maxLength={L.name_max} required
               placeholder="Your name" aria-label="Your name" />
        {/* the honeypot, as on the post form */}
        <label className="dc-trap" aria-hidden="true">
          Website <input tabIndex={-1} autoComplete="off" value={f.website} onChange={set('website')} />
        </label>
        <button type="submit" className="btn btn-primary" disabled={!ready || state.sending}>
          {state.sending ? 'Sending…' : 'Reply for review'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
      </div>
      {state.err && <p className="dc-err" role="alert">{state.err}</p>}
    </form>
  )
}

function Post({ p, modelName, limits, topicName }) {
  const [replying, setReplying] = useState(false)
  const replies = p.replies || []
  return (
    <article className="dc-post">
      {topicName && <span className="dc-topic-tag">{topicName}</span>}
      <h3>{p.title}</h3>
      <p className="dc-body">{p.body}</p>
      <div className="dc-meta">
        <span>{p.author_name || 'A reader'}</span>
        {p.model_id && <span className="dc-model">{modelName(p.model_id)}</span>}
        {p.created_at && <span>{fmtDay(p.created_at)}</span>}
        <span>{replies.length ? `${replies.length} ${replies.length === 1 ? 'reply' : 'replies'}` : 'No replies yet'}</span>
        {!replying && <button type="button" className="dc-link dc-reply-btn" onClick={() => setReplying(true)}>Reply</button>}
      </div>
      {replies.length > 0 && (
        <ol className="dc-replies" aria-label="Replies">
          {replies.map((r) => (
            <li key={r.id} className="dc-reply">
              <p className="dc-body">{r.body}</p>
              <div className="dc-meta">
                <span>{r.author_name || 'A reader'}</span>
                {r.created_at && <span>{fmtDay(r.created_at)}</span>}
              </div>
            </li>
          ))}
        </ol>
      )}
      {replying && <ReplyBox post={p} limits={limits} onClose={() => setReplying(false)} />}
    </article>
  )
}

function Compose({ topics, models, topic, setTopic, limits, formRef }) {
  const [f, setF] = useState({ title: '', body: '', author_name: '', model_id: '', website: '' })
  const [state, setState] = useState({ sending: false, sent: false, err: null })
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const L = limits || { title_min: 8, title_max: 120, body_min: 30, body_max: 4000, name_min: 2, name_max: 40, links_max: 2 }
  // the name is required (2026-10-20): every post is signed
  const ready = topic && f.title.trim().length >= L.title_min && f.body.trim().length >= L.body_min
    && f.author_name.trim().length >= (L.name_min || 2)

  const submit = async (e) => {
    e.preventDefault()
    setState({ sending: true, sent: false, err: null })
    try {
      await postDiscussion({ topic, ...f, model_id: f.model_id || null })
      setState({ sending: false, sent: true, err: null })
      setF({ title: '', body: '', author_name: '', model_id: '', website: '' })
    } catch (err) {
      setState({ sending: false, sent: false, err: err.message })
    }
  }

  return (
    <form className="dc-form" onSubmit={submit} ref={formRef} id="start" aria-labelledby="dc-form-h">
      <h2 id="dc-form-h">Start a discussion</h2>
      <p className="dc-dim">Share what you found with an AI model in real work. A person reads every post before it appears.</p>

      <label className="dc-field">
        <span>Topic</span>
        <select value={topic} onChange={(e) => setTopic(e.target.value)} required>
          <option value="" disabled>Choose a topic</option>
          {topics.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
        </select>
      </label>

      <label className="dc-field">
        <span>Model <em>optional</em></span>
        <select value={f.model_id} onChange={set('model_id')}>
          <option value="">Not about one model</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
      </label>

      <label className="dc-field">
        <span>Title</span>
        <input value={f.title} onChange={set('title')} maxLength={L.title_max} required
               placeholder="e.g. Opus 5 held the plan across a 40-file refactor" />
        <small>{f.title.trim().length}/{L.title_max}</small>
      </label>

      <label className="dc-field">
        <span>Your experience</span>
        <textarea value={f.body} onChange={set('body')} maxLength={L.body_max} rows={7} required
                  placeholder="What was the job, which model did you use, and what happened? What would you tell someone choosing a model for the same work?" />
        <small>{f.body.trim().length < L.body_min ? `at least ${L.body_min} characters` : `${f.body.trim().length}/${L.body_max}`}</small>
      </label>

      <label className="dc-field">
        <span>Name</span>
        <input value={f.author_name} onChange={set('author_name')} maxLength={L.name_max} required
               placeholder="Shown with your post - a first name or a handle is enough" />
      </label>

      {/* THE HONEYPOT: hidden from people and from screen readers; a bot that
          fills every field fills this one, and the server refuses the post. */}
      <label className="dc-trap" aria-hidden="true">
        Website <input tabIndex={-1} autoComplete="off" value={f.website} onChange={set('website')} />
      </label>

      <div className="dc-actions">
        <button type="submit" className="btn btn-primary" disabled={!ready || state.sending}>
          {state.sending ? 'Sending…' : 'Post for review'}
        </button>
        <span className="dc-dim">No account needed. We store no email and no address.</span>
      </div>
      {state.sent && (
        <p className="dc-ok" role="status">Thank you - your post is waiting for review. It appears here once a person has read it.</p>
      )}
      {state.err && <p className="dc-err" role="alert">{state.err}</p>}
    </form>
  )
}

export default function Discussions() {
  useHead(discussionsIndex())
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [models, setModels] = useState([])
  const [topic, setTopic] = useState('')
  const formRef = useRef(null)

  useEffect(() => {
    let alive = true
    discussionsPage().then((d) => alive && setData(d)).catch((e) => alive && setErr(e.message))
    // the most-reported models first, so the list starts with what people use
    modelCatalog().then((c) => {
      if (!alive || c?.reason) return
      setModels((c.models || []).filter((m) => m.voices > 0)
        .sort((a, b) => b.voices - a.voices || a.name.localeCompare(b.name)).slice(0, 120))
    }).catch(() => {})
    return () => { alive = false }
  }, [])

  const names = useMemo(() => Object.fromEntries(models.map((m) => [m.id, m.name])), [models])
  const modelName = (id) => names[id] || id
  const startOn = (slug) => {
    if (slug) setTopic(slug)
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const topics = data?.topics || []
  const [filter, setFilter] = useState('')
  // EVERY TOPIC'S POSTS IN ONE LIST, NEWEST FIRST by when they were written,
  // each knowing its topic's name for the label on the card.
  const feed = useMemo(() => topics
    .flatMap((t) => t.posts.map((p) => ({ ...p, topic: t.slug, topicName: t.name })))
    .sort((x, y) => String(y.created_at).localeCompare(String(x.created_at))), [topics])
  const current = topics.find((t) => t.slug === filter) || null
  const shown = filter ? feed.filter((p) => p.topic === filter) : feed
  return (
    <div className="shell section-tight stack stack-4 dc">
      <header className="dc-hero">
        <span className="go-badge go-blogs page-tag">Discussions</span>
        <h1>AI model discussions from real work</h1>
        <p className="dc-lead">
          Talk to other engineers about the AI models you actually use. Which is the best LLM for coding on your
          codebase, which AI agents held up, how RAG behaved on your documents, whether a local LLM or an open
          source LLM was enough, and what the API really cost. An LLM comparison from your own runs - Claude vs
          Gemini, Opus vs Sonnet - helps the next person more than any ranking.
        </p>
        <div className="dc-hero-cta">
          <a href="#start" className="btn btn-primary" onClick={(e) => { e.preventDefault(); startOn(topic) }}>Start a discussion</a>
        </div>
      </header>

      <section className="dc-steps" aria-label="How discussions work">
        {STEPS.map(([n, t, d]) => (
          <div key={n} className="dc-step"><b>{n}</b><div><h2>{t}</h2><p>{d}</p></div></div>
        ))}
      </section>

      {err && <p className="dc-err">The discussions could not be read: {err}</p>}
      {!data && !err && <div className="skel" style={{ height: 220 }} />}

      {data && (
        <>
          {/* THE CHIPS ARE THE FILTER (2026-10-20): "All" and one per topic, each
              with its count. Below them ONE list, newest first across every
              topic - a topic with no posts adds no empty card. */}
          <nav className="dc-topics" aria-label="Discussion topics">
            <button type="button" className={`dc-topic${filter ? '' : ' dc-on'}`} aria-pressed={!filter}
                    onClick={() => setFilter('')}>
              <b>All discussions</b>
              <span>{feed.length ? `${feed.length} ${feed.length === 1 ? 'discussion' : 'discussions'}` : 'None yet'}</span>
            </button>
            {topics.map((t) => (
              <button key={t.slug} type="button" className={`dc-topic${filter === t.slug ? ' dc-on' : ''}`}
                      aria-pressed={filter === t.slug} onClick={() => setFilter(filter === t.slug ? '' : t.slug)}>
                <b>{t.name}</b>
                <span>{t.posts.length ? `${t.posts.length} ${t.posts.length === 1 ? 'discussion' : 'discussions'}` : 'Be the first to post'}</span>
              </button>
            ))}
          </nav>

          <div className="dc-grid">
            <div className="dc-main">
              {current && (
                <div className="dc-intro">
                  <p className="dc-blurb">{current.blurb}</p>
                  <button type="button" className="btn btn-ghost dc-new" onClick={() => startOn(current.slug)}>Post on this topic</button>
                </div>
              )}
              {shown.length
                ? <div className="dc-posts">{shown.map((p) => <Post key={p.id} p={p} modelName={modelName} limits={data.limits} topicName={filter ? null : p.topicName} />)}</div>
                : (
                  <p className="dc-empty">
                    {current ? `No discussions on ${current.name.toLowerCase()} yet.` : 'No discussions yet.'}{' '}
                    <button type="button" className="dc-link" onClick={() => startOn(current ? current.slug : '')}>Start the first one.</button>
                  </p>
                )}
            </div>

            <aside className="dc-side">
              <Compose topics={topics} models={models} topic={topic} setTopic={setTopic} limits={data.limits} formRef={formRef} />
              <div className="dc-guide">
                <h2>Posting guidelines</h2>
                <ul>{GUIDE.map((g) => <li key={g}>{g}</li>)}</ul>
                <p className="dc-dim">Discussions sit beside the counted reports and are never added to them.</p>
              </div>
            </aside>
          </div>
        </>
      )}
    </div>
  )
}
