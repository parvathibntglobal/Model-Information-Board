import { useEffect, useState } from 'react'
import { discussedModels, BoardUnreadable } from '../api'
import { Notice, Unreadable } from '../components/ui'
import { IconAlert } from './Icons'

/**
 * Models the board holds evidence about that the models page does not show.
 *
 * ⚠ 1,076 ENTRIES ABOUT 66 MODELS WERE ON NO SURFACE AT ALL. The models page
 *   renders `contract/tracked_models.yaml` — what we chose to watch.
 *   `board_entry` records what engineers actually wrote about. Nothing
 *   compared the two, so evidence collected about a model nobody had picked
 *   had nowhere to appear:
 *
 *       models with board entries        78
 *         on the models page             12
 *         DISCUSSED but not tracked      66
 *       board entries on those        1,076
 *
 * ⚠ IT IS NOT A QUEUE, and it must not read as one. Nothing here waits for
 *   approval. A model is listed because somebody wrote about it and the
 *   extractor resolved the mention — the pipeline working, not a backlog
 *   forming. The panel that used to sit in this position WAS a queue
 *   (capability candidates, removed #434), so the distinction is worth making
 *   in words rather than trusting the layout to carry it.
 *
 * ⚠ RENDERED IN TWO SECTIONS ON PURPOSE. It answers a question that Models
 *   and Board sections each raise and neither owns — "what did we learn about
 *   things we were not watching" — and a reader arriving at either one has
 *   that question. One component, one endpoint, so the two cannot disagree.
 */
export default function DiscussedModels({ heading }) {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  const [all, setAll] = useState(false)

  useEffect(() => {
    let alive = true
    discussedModels()
      .then((d) => alive && setState({ data: d, err: null, unreadable: null }))
      .catch((e) => alive && setState({
        data: null,
        err: e instanceof BoardUnreadable ? null : e.message,
        unreadable: e instanceof BoardUnreadable ? e.message : null,
      }))
    return () => { alive = false }
  }, [])

  const { data, err, unreadable } = state
  if (unreadable) return <Unreadable detail={unreadable} />

  const models = data?.models || []
  const shown = all ? models : models.slice(0, 12)

  return (
    <div className="stack stack-2">
      <div className="row" style={{ gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span className="label">{heading || 'Discussed, and not on the models page'}</span>
        {data && (
          <span className="dim tnum" style={{ fontSize: 11 }}>
            {/* RULE 7: the denominator travels. "66 models" alone says
                nothing about whether that is most of the board or a corner
                of it. */}
            {data.count} of {data.with_entries} models with evidence ·{' '}
            {data.entries} entries
          </span>
        )}
      </div>

      <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '80ch',
                                  margin: 0, lineHeight: 1.6 }}>
        Engineers wrote about these and the board kept it, but{' '}
        <strong style={{ color: 'var(--text)' }}>they are not on the models page</strong>,
        which lists the models we chose to track. Nothing here is waiting to be
        approved — it is what the corpus turned out to contain. It is also the list
        to pick from when deciding what to track next.
        {/* THE OTHER SIDE OF THE SAME GAP, and the one the models page cannot
            show you: a tracked model with no entries is a row that is there and
            empty, which reads as "nothing found" rather than "nobody wrote
            about it". Both halves are stated so neither count is a bare
            numerator (RULE 7). */}
        {data && (
          <>
            {' '}The models page lists{' '}
            <span className="tnum">{data.tracked_total}</span> models, of which{' '}
            <span className="tnum">{data.tracked_with_entries}</span> have evidence
            on the board.
          </>
        )}
      </p>

      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!data && !err && <div className="skel" style={{ height: 160 }} />}

      {data && models.length === 0 && (
        <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          Every model the board holds evidence about is on the models page. That is a
          measurement, not an empty list — {data.with_entries} models have entries and
          all of them are tracked.
        </p>
      )}

      {data && models.length > 0 && (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table className="cmp-table" style={{ fontSize: 'var(--fs-xs)' }}>
              <thead>
                <tr>
                  <th>Model</th>
                  <th style={{ textAlign: 'right' }}>Entries</th>
                  <th style={{ textAlign: 'right' }}>Documents</th>
                  <th style={{ textAlign: 'right' }}>Sections</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((m) => (
                  <tr key={m.canonical_id}>
                    <th scope="row" style={{ fontWeight: 500 }}>
                      {m.display_name}
                      {/* THE PROVIDER'S ID, not ours. A reader who wants to
                          look this model up needs the name its provider uses,
                          and `mv_…` is not lookup-able anywhere. */}
                      <span className="dim mono" style={{ display: 'block', fontSize: 10 }}>
                        {m.canonical_id}
                      </span>
                    </th>
                    <td className="tnum" style={{ textAlign: 'right' }}>{m.entries}</td>
                    {/* ENTRIES AND DOCUMENTS ARE NOT THE SAME COUNT, and the
                        gap is the point: one document can carry several
                        entries, so 110 entries from 20 documents is a
                        different kind of evidence from 110 from 90. */}
                    <td className="tnum" style={{ textAlign: 'right' }}>{m.documents}</td>
                    <td className="tnum" style={{ textAlign: 'right' }}>{m.sections}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {models.length > shown.length && (
            <button type="button" className="chip" onClick={() => setAll(true)}>
              show the other {models.length - shown.length}
            </button>
          )}
        </>
      )}
    </div>
  )
}
