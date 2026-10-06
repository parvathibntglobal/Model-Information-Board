import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { blogGenerationStatus, blogRuns } from '../api'
import { Notice } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { RunHistory, RunLog, RunStatus, RUNNING } from '../components/BlogsPanel'

/**
 * Blog generation logs: the current run's live log and every recorded run.
 *
 * ITS OWN PAGE (2026-10-06), opened from the Logs button in Admin -> Blogs, so
 * reading a long log does not push the drafts table around. Same sources as the
 * panel: GET /blog-posts/generate (status), /generate/log (console, keys
 * masked) and /blog-posts/runs (history in the shared database).
 */
export default function BlogLogs() {
  const [gen, setGen] = useState(null)
  const [tick, setTick] = useState(0)
  const [hist, setHist] = useState({ data: null, err: null })
  const timer = useRef(null)

  const loadHist = useCallback(() => blogRuns()
    .then((d) => setHist({ data: d, err: null }))
    .catch((e) => setHist({ data: null, err: e.message })), [])

  const poll = useCallback(() => {
    clearTimeout(timer.current)
    blogGenerationStatus()
      .then((s) => {
        setTick((t) => t + 1)
        setGen((prev) => {
          if (prev && RUNNING.has(prev.state) && !RUNNING.has(s.state)) loadHist()
          return s
        })
        if (RUNNING.has(s.state)) timer.current = setTimeout(poll, 4000)
      })
      .catch(() => {})
  }, [loadHist])

  useEffect(() => {
    loadHist()
    poll()
    return () => clearTimeout(timer.current)
  }, [loadHist, poll])

  const running = gen && RUNNING.has(gen.state)

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <Link to="/admin?s=blogs" className="mb-link" style={{ fontSize: 'var(--fs-xs)' }}>← Back to Admin · Blogs</Link>
        <span className="eyebrow">Admin · Blogs</span>
        <h1 style={{ fontSize: 'var(--fs-h2)' }}>Generation logs</h1>
        <p className="muted" style={{ maxWidth: '70ch' }}>
          What each run did, as it happened: the live log of the current run, and every recorded run with
          its cost, tokens, the posts it wrote and its saved log.
        </p>
      </div>

      <section className="card stack stack-3">
        <span className="label">Current run</span>
        <RunStatus gen={gen} />
        <RunLog running={running} tick={tick} />
      </section>

      <section className="card stack stack-3">
        <span className="label">Run history — every generation, stored in the database</span>
        {hist.err
          ? <Notice icon={<IconAlert />}>The run history could not be read: {hist.err}</Notice>
          : hist.data ? <RunHistory runs={hist.data.runs || []} /> : <div className="skel" style={{ height: 120 }} />}
      </section>
    </div>
  )
}
