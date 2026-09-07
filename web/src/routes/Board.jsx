import { useParams, useSearchParams } from 'react-router-dom'
import { vBoard, vJob, vCap, vMet } from '../board/views'
import BoardView from '../board/BoardView'

/**
 * The board, ported from the SEO demo: three ways into the evidence
 * (Best for / Capabilities / Metrics) plus a page per job, capability and
 * metric. Data is illustrative (see board/db.js); the shape matches what a
 * query against the claim/thread_context tables would fill.
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

  let html
  if (seg === 'jobs') html = vJob(slug)
  else if (seg === 'capabilities') html = vCap(slug)
  else if (seg === 'metrics') html = vMet(slug)
  else html = vBoard(sp.get('tab') || 'best')

  return <BoardView html={html} key={rest + '?' + (sp.get('tab') || '')} />
}
