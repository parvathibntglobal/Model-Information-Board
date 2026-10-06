import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { blogPosts, listModels } from '../api'
import { DB } from '../board/db'
import { vBlogs, vPost } from '../board/views'
import BoardView from '../board/BoardView'

/**
 * Blogs: posts the team examines before anything is published.
 *
 *   /blogs         → the index
 *   /blogs/:slug   → one post
 *
 * THE POSTS COME FROM `GET /blog-posts`, NOT FROM `/board`. Drafts are files
 * written by `generate_sample_blogs.py`; see `judge/blog_posts.py`.
 *
 * GENERATING MOVED TO THE ADMIN PAGE (2026-10-06). Posts are generated and
 * approved from Admin → Blogs, so the "Generate 3 more posts" strip that sat
 * above this index is gone; this page only reads the drafts.
 */
export default function Blogs() {
  const rest = useParams()['*'] || ''
  // OPENED FROM ADMIN -> BLOGS' PREVIEW: the reviewer must see a post that is
  // still awaiting review (hidden from the public index), and needs a way back
  // to where the review happens.
  const fromAdmin = useLocation().state?.from === 'admin'
  const [state, setState] = useState({ ready: false, err: null })

  const loadPosts = useCallback(() => blogPosts()
    .then((d) => {
      // A POST A RECORDED RUN WROTE IS SHOWN ONCE APPROVED in Admin -> Blogs
      // (`review` is pending | approved | rejected). Posts with no `review`
      // predate the run history and show as they always did.
      DB.posts = fromAdmin ? (d.posts || []) : (d.posts || []).filter((p) => !p.review || p.review === 'approved')
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
    }), [fromAdmin])

  useEffect(() => {
    loadPosts()
  }, [loadPosts])

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
      {fromAdmin && (
        <div className="shell" style={{ paddingTop: 'var(--s3)' }}>
          <Link to="/admin?s=blogs" className="mb-link" style={{ fontSize: 'var(--fs-xs)' }}>
            ← Back to Admin · Blogs
          </Link>
        </div>
      )}
      <BoardView html={html} key={rest} />
    </>
  )
}
