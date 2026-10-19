import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { blogPosts, listModels } from '../api'
import { DB } from '../board/db'
import { vBlogs, vPost } from '../board/views'
import BoardView from '../board/BoardView'
import { loadEmbeds } from '../board/embeds'
import NotFound from '../components/NotFound'
import { useHead } from '../seo/head'
import { blogIndex, blogPost } from '../seo/pages'
import Directory from '../blogs/Directory'
import '../styles/blog-live.css'

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
/**
 * ONE PAGE UNDER /blogs THAT IS NOT A POST: the directory.
 *
 *   /blogs/directory    every post, by model/topic/title/date (2026-10-18)
 *
 * THE LIVE AND REFERENCE PAGES ARE UNROUTED (2026-10-19, anooj): where
 * engineers disagree and its claim walls, this week in models, the daily quiz,
 * the glossary, known issues and answers. Their URLs now fall through to the
 * post lookup and show "not found". The components stay in web/src/blogs/
 * (Disagree, ThisWeek, Quiz, Glossary, Issues, Answers) and the endpoints in
 * judge/blog_live.py and judge/blog_reference.py, so restoring one is an import
 * and a line here plus its tile in views.js `LIVE`.
 *
 * NOR IS THE READ-NEXT BLOCK UNDER A POST (2026-10-19): `ReadNext`
 * (blogs/Explore.jsx) offered tiles to three of those pages - disagree, this
 * week, the quiz - and links into claim walls, all of which now open "not
 * found"; it also asked /blog-live/disagree, which a signed-out visitor is
 * refused. Restoring it is the import and the line under <BoardView> again.
 */
export default function Blogs() {
  const rest = useParams()['*'] || ''
  if (rest === 'directory') return <Directory />
  return <BlogPosts rest={rest} />
}

function BlogPosts({ rest }) {
  // OPENED FROM ADMIN -> BLOGS' PREVIEW: the reviewer must see a post that is
  // still awaiting review (hidden from the public index), and needs a way back
  // to where the review happens.
  const fromAdmin = useLocation().state?.from === 'admin'
  const [state, setState] = useState({ ready: false, err: null })

  // THE SERVER DECIDES WHAT IS SHOWN (judge/blog_store.py): the public list is
  // approved posts only, and a store that cannot be read returns none with a
  // reason - never every draft. Admin's preview asks for pending posts too.
  const loadPosts = useCallback(() => blogPosts(fromAdmin ? 'all' : undefined)
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
    }), [fromAdmin])

  useEffect(() => {
    loadPosts()
  }, [loadPosts])

  const html = !state.ready ? '' : rest ? vPost(rest) : vBlogs()

  // PER-PAGE <head> (seo/pages.js). A preview opened from Admin may be a post
  // still awaiting review, so it is never indexable, whatever index.html says.
  // A POST THAT IS NOT HERE IS NOT FOUND (SEO item 7) - unknown, or not
  // approved for this reader - where vPost used to render the index at its
  // address. NotFound owns the head then (`false`).
  const post = rest ? (DB.posts || []).find((p) => p.slug === rest) : null
  const missing = state.ready && !state.err && Boolean(rest) && !post
  const head = !state.ready ? null : missing ? false : rest ? blogPost(post) : blogIndex()
  useHead(head && fromAdmin ? { ...head, noindex: true } : head)
  // OFFICIAL EMBEDS draw after the post is in the page (board/embeds.js).
  useEffect(() => { if (rest && html) loadEmbeds() }, [rest, html])

  if (!state.ready) {
    return (
      <div className="shell section-tight">
        <div className="skel" style={{ height: 220 }} />
      </div>
    )
  }

  if (missing) return <NotFound what="post" back={{ to: '/blogs', label: 'All posts' }} />

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
