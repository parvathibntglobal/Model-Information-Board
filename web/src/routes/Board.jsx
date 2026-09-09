import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { boardPage, BoardUnreadable } from '../api'
import { setBoardData } from '../board/db'
import { vBoard, vJob, vCap, vMet } from '../board/views'
import BoardView from '../board/BoardView'

/**
 * The board: three ways into the same evidence — Best for, Capabilities,
 * Metrics — plus a page per discovered section.
 *
 * THE SECTIONS ARE DISCOVERED, NOT CONFIGURED. `GET /board` returns whatever the
 * classifier found in the evidence: it reads what engineers wrote and names the
 * job, capability or metric they discussed. There is no list of eight jobs
 * anywhere, and a section nobody has discussed simply is not here — which is
 * why an empty board is a real state rather than a loading bug.
 *
 * NO PUBLICATION GATE ON THIS PAGE. `cell` publishes a verdict and clears a
 * gate first; these three sections are observations, so they render as soon as
 * one report exists and the count is shown rather than the row being hidden.
 * The count is a FLOOR and the page says so — an open vocabulary can name one
 * section two ways until somebody merges them.
 *
 * Routes handled (via the /board/* splat):
 *   /board            → hub, tab from ?tab (best|cap|met)
 *   /board/jobs/:slug
 *   /board/capabilities/:slug
 *   /board/metrics/:slug
 */
export default function Board() {
  const rest = useParams()['*'] || ''
  const [sp] = useSearchParams()
  const [seg, slug] = rest.split('/')
  const [state, setState] = useState({ ready: false, err: null, unreadable: null })

  useEffect(() => {
    let alive = true
    boardPage()
      .then((d) => {
        if (!alive) return
        setBoardData(d)
        setState({ ready: true, err: null, unreadable: null })
      })
      .catch((e) => {
        if (!alive) return
        // An unreadable database is its own state, not an error to shout about:
        // the board legitimately has nothing to show before the first fetch run.
        setState({
          ready: true,
          err: e instanceof BoardUnreadable ? null : e.message,
          unreadable: e instanceof BoardUnreadable ? e.message : null,
        })
      })
    return () => { alive = false }
  }, [])

  if (!state.ready) {
    return (
      <div className="shell section-tight">
        <div className="skel" style={{ height: 220 }} />
      </div>
    )
  }

  let html
  if (seg === 'jobs') html = vJob(slug)
  else if (seg === 'capabilities') html = vCap(slug)
  else if (seg === 'metrics') html = vMet(slug)
  else html = vBoard(sp.get('tab') || 'best')

  return (
    <>
      {state.err && (
        <div className="shell section-tight">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            The board could not be read: {state.err}
          </p>
        </div>
      )}
      <BoardView html={html} key={rest + '?' + (sp.get('tab') || '')} />
    </>
  )
}
