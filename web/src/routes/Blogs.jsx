import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { blogPosts, startBlogGeneration, blogGenerationStatus, listModels } from '../api'
import { DB } from '../board/db'
import { vBlogs, vPost } from '../board/views'
import BoardView from '../board/BoardView'

/**
 * Blogs: posts the team examines before anything is published.
 *
 *   /blogs         → the index, with "Generate 3 more posts"
 *   /blogs/:slug   → one post
 *
 * THE POSTS COME FROM `GET /blog-posts`, NOT FROM `/board`. Drafts are files
 * written by `generate_sample_blogs.py`; see `judge/blog_posts.py`.
 *
 * THE BUTTON STARTS A BACKGROUND RUN (`POST /blog-posts/generate`) and this page
 * polls its status. What gets written is decided by the planner in code, from
 * `blog_formats.yaml` and the board's evidence — not by the model.
 *
 * THE CONTROL IS A STRIP ABOVE THE INDEX, NOT PART OF ITS HTML. BoardView
 * scrolls to the top whenever its HTML changes, so progress inside it would jump
 * the page every poll; and a portal into that HTML was tried and lost its target
 * when BoardView rewrote the markup (2026-10-01).
 */
const RUNNING = new Set(['starting', 'running'])
const COUNT = 3

// States that need the reader's attention. A finished run says nothing - its
// posts are on the page - but a failure must never disappear quietly.
const PROBLEM = new Set(['failed', 'partial', 'stalled'])

function GenBar({ gen, onStart }) {
  const running = gen && RUNNING.has(gen.state)
  const items = (gen && gen.items) || []
  const done = items.filter((i) => i.state === 'done').length
  const current = items.find((i) => i.state !== 'done' && i.state !== 'failed' && i.state !== 'queued')
  let note = null
  if (running) {
    note = current ? `Writing: ${current.format} · ${current.subject}` : 'Planning the next posts…'
  } else if (gen && PROBLEM.has(gen.state)) {
    const failed = items.filter((i) => i.state === 'failed').length
    note = gen.state === 'stalled' ? 'The last run stopped reporting.'
      : failed ? `${failed} of ${items.length} posts could not be written.` : 'The last run failed.'
  }
  return (
    <div className="es-gen">
      <div className="es-gen-row">
        {note && <span className={`es-gen-note${running ? '' : ' warn'}`}>{note}</span>}
        <button type="button" className="es-gen-btn" disabled={running} onClick={onStart}>
          {running ? `Generating… ${done} of ${items.length || COUNT}` : `Generate ${COUNT} more posts`}
        </button>
      </div>
    </div>
  )
}

export default function Blogs() {
  const rest = useParams()['*'] || ''
  const [state, setState] = useState({ ready: false, err: null })
  const [gen, setGen] = useState(null)
  const timer = useRef(null)

  const loadPosts = useCallback(() => blogPosts()
    .then((d) => {
      DB.posts = d.posts || []
      DB.postsMeta = { reason: d.reason || null, skipped: d.skipped || [] }
      setState((s) => ({ ready: true, err: null, n: (s.n || 0) + 1 }))
      // INTERACTIVE POSTS read today's model figures (docs/proposals/
      // interactive-blogs.md). Loaded beside the posts, never ahead of them:
      // a failure here leaves posts readable, just without links and cards.
      // ONE RETRY after 3 s: a single dropped database connection left the
      // example post without its cards on 2026-10-06.
      const loadModels = (left) => listModels(200)
        .then((m) => {
          DB.blogModels = m.models || []
          setState((s) => ({ ...s, n: (s.n || 0) + 1 }))
        })
        .catch((e) => {
          if (left > 0) { setTimeout(() => loadModels(left - 1), 3000); return }
          console.warn('interactive posts: models not loaded:', e.message)
        })
      loadModels(1)
    })
    .catch((e) => {
      DB.posts = []
      DB.postsMeta = { reason: null, skipped: [] }
      setState((s) => ({ ready: true, err: e.message, n: (s.n || 0) + 1 }))
    }), [])

  const poll = useCallback(() => {
    clearTimeout(timer.current)
    blogGenerationStatus()
      .then((s) => {
        setGen((prev) => {
          // A run that just finished brings its new posts onto the page.
          if (prev && RUNNING.has(prev.state) && !RUNNING.has(s.state)) loadPosts()
          return s
        })
        if (RUNNING.has(s.state)) timer.current = setTimeout(poll, 4000)
      })
      .catch((e) => setGen({ state: 'failed', message: e.message, items: [] }))
  }, [loadPosts])

  useEffect(() => {
    loadPosts()
    poll() // a run started before this page opened is picked up, not missed
    return () => clearTimeout(timer.current)
  }, [loadPosts, poll])

  const onStart = () => {
    setGen({ state: 'starting', items: [] })
    startBlogGeneration(COUNT)
      .then((s) => { setGen(s); timer.current = setTimeout(poll, 2000) })
      .catch((err) => setGen({ state: 'failed', message: err.message, items: [] }))
  }

  const html = !state.ready ? '' : rest ? vPost(rest) : vBlogs()

  if (!state.ready) {
    return (
      <div className="shell section-tight">
        <div className="skel" style={{ height: 220 }} />
      </div>
    )
  }

  return (
    <>
      {state.err && (
        <div className="shell section-tight">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            The blog drafts could not be read: {state.err}
          </p>
        </div>
      )}
      {!rest && (
        <div className="essay es-strip">
          <div className="es-strip-in"><GenBar gen={gen} onStart={onStart} /></div>
        </div>
      )}
      <BoardView html={html} key={rest} />
    </>
  )
}
