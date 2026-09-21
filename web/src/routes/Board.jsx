import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { boardPage, BoardUnreadable } from '../api'
import { setBoardData } from '../board/db'
import { vBoard, vJob, vCap, vMet, vJobModel, vCapModel, vMetModel } from '../board/views'
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
 *   /board                          → hub, tab from ?tab (best|cap|met)
 *   /board/jobs/:slug               → the models reported for that job
 *   /board/jobs/:slug/*             → one model's reports on that job
 *   /board/capabilities/:slug       → the models reported on that capability
 *   /board/capabilities/:slug/*     → one model's reports on that capability
 *   /board/metrics/:slug            → the models with figures on that axis
 *   /board/metrics/:slug/*          → one model's figures on that axis
 *
 * THE MODEL KEY IS THE REST OF THE PATH, not the third segment.
 * `model_version.id` holds a canonical id for 166 of 1,249 board rows, and
 * `anthropic/claude-fable-5-1` is one key to us and two segments to a router.
 * Splitting into three and reading `[2]` would truncate it to `anthropic` and
 * find no model - and `vModelIn` would then send the visitor back to the
 * category page, which looks like a model that has nothing said about it
 * rather than a link this file broke.
 */
export default function Board() {
  const rest = useParams()['*'] || ''
  const [sp] = useSearchParams()
  const parts = rest.split('/')
  const [seg, slug] = parts
  const modelKey = parts.length > 2 ? parts.slice(2).join('/') : null
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
  if (seg === 'jobs') html = modelKey ? vJobModel(slug, modelKey) : vJob(slug)
  else if (seg === 'capabilities') html = modelKey ? vCapModel(slug, modelKey) : vCap(slug)
  else if (seg === 'metrics') html = modelKey ? vMetModel(slug, modelKey) : vMet(slug)
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
