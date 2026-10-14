import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { boardPage, freshness, BoardUnreadable } from '../api'
import { DB, modelKeyFor, setBoardData } from '../board/db'
import { useHead } from '../seo/head'
import { boardHub, boardModelInSection, boardSection } from '../seo/pages'
import { vBoard, vJob, vCap, vMet, vJobModel, vCapModel, vMetModel } from '../board/views'
import BoardView from '../board/BoardView'
import NotFound from '../components/NotFound'

/**
 * The board: three ways into the same evidence — Jobs (key `best_for`), Capabilities,
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
 *   /board?tab=cap&group=<heading>  → one heading's capabilities (a box opened)
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
  // THE ADDRESS NAMES THE MODEL READABLY (`anthropic/claude-opus-4.6`); the
  // views look rows up by their grouping key, so it is translated here. An
  // old `mv_…` link is its own key and still works.
  const modelParam = parts.length > 2 ? parts.slice(2).join('/') : null
  const [state, setState] = useState({ ready: false, err: null, unreadable: null })
  const modelKey = state.ready ? modelKeyFor(modelParam) : modelParam

  useEffect(() => {
    let alive = true
    // THE FRESHNESS DATES ride along; if they cannot be read the line is left
    // out, and the board still renders.
    Promise.all([boardPage(), freshness().catch(() => null)])
      .then(([d, f]) => {
        if (!alive) return
        setBoardData(d)
        DB.freshness = f
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

  // PER-PAGE <head> (seo/pages.js), from the section the board actually
  // loaded - null while loading, so the site defaults stand until it has.
  // A slug the board does not hold gets the hub's head, which is also what
  // the views render for it.
  // A SECTION THAT IS NOT ON THE BOARD IS NOT FOUND (SEO item 7), where the
  // views used to render the hub at its address. `/board/jobs` with no slug is
  // still the tab: a list page links use. NotFound owns the head then (`false`).
  const missing = state.ready && sectionMissing(seg, slug)
  useHead(!state.ready ? null : missing ? false : headFor(seg, slug, modelKey, sp.get('tab')))

  if (!state.ready) {
    return (
      <div className="shell section-tight">
        <div className="skel" style={{ height: 220 }} />
      </div>
    )
  }

  if (missing) {
    const what = { jobs: 'job', capabilities: 'capability', metrics: 'metric' }[seg]
    return <NotFound what={what} back={{ to: '/board', label: 'Browse the board' }} />
  }

  let html
  if (seg === 'jobs') html = modelKey ? vJobModel(slug, modelKey) : vJob(slug)
  else if (seg === 'capabilities') html = modelKey ? vCapModel(slug, modelKey) : vCap(slug)
  else if (seg === 'metrics') html = modelKey ? vMetModel(slug, modelKey) : vMet(slug)
  else html = vBoard(sp.get('tab') || 'best', sp.get('group'))

  return (
    <>
      {state.err && (
        <div className="shell section-tight">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            The board could not be read: {state.err}
          </p>
        </div>
      )}
      <BoardView html={html} key={rest + '?' + (sp.get('tab') || '') + '&' + (sp.get('group') || '')} />
    </>
  )
}

const SECTION_LIST = { jobs: 'jobs', capabilities: 'caps', metrics: 'mets' }

/** An unknown segment (`/board/foo`), or a slug the board does not hold. */
function sectionMissing(seg, slug) {
  if (!seg) return false
  const list = DB[SECTION_LIST[seg]]
  if (!list) return true
  return Boolean(slug) && !list.some((x) => x.slug === slug)
}

function headFor(seg, slug, modelKey, tab) {
  const list = DB[SECTION_LIST[seg]]
  const item = list ? list.find((x) => x.slug === slug) : null
  if (!item) return boardHub(seg ? 'best' : tab || 'best')
  if (!modelKey) return boardSection(seg, item)
  const row = (item.rows || []).find((r) => r.key === modelKey)
  return row ? boardModelInSection(seg, item, row.slug || modelKey, row.m, row.freshUpdated) : boardSection(seg, item)
}
