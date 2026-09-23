import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { comparePage, capLabel, fmtPrice, fmtTokens, BoardUnreadable } from '../api'
import { Badge, Notice, Unreadable } from '../components/ui'
import { IconAlert } from '../components/Icons'

/**
 * Two or three models side by side — `/compare?ids=a,b[,c]`.
 *
 * THE DEMO'S TABLE HAD NINE ROWS AND THIS ONE CANNOT. Verdict, best-for, cost,
 * context and report counts all have a source in the database. Licence,
 * benchmark standing, the one-line blurb and the "core differentiation" line do
 * not — they were written by hand for the mock-up. So they are listed at the
 * bottom with the reason, rather than dropped: a shorter table with no
 * explanation reads as "the board compared everything it could", which is a
 * different and false claim.
 *
 * ADVERTISED AND REPORTED ARE NEVER IN THE SAME BLOCK. A price is the vendor's
 * claim about itself; a report count is what somebody found. The demo put
 * "Cost / M tokens" and "First-hand reports" in one column of one table, which
 * is exactly the mistake that makes a spec look like evidence. Here the two
 * halves are separated with a heading each, and the reported half says plainly
 * when it is empty.
 *
 * NO WINNER IS COMPUTED. There is no highlight on the cheapest cell, no "best
 * value" ribbon, no total. Picking a winner from a spec sheet is the
 * recommendation this board refuses to make without evidence — and with 0
 * reports on every model, a comparison IS a spec sheet and says so.
 */
export default function Compare() {
  const [sp] = useSearchParams()
  const ids = (sp.get('ids') || '').split(',').map((s) => s.trim()).filter(Boolean)
  const [state, setState] = useState({ data: null, err: null, unreadable: null })

  useEffect(() => {
    if (ids.length < 2) { setState({ data: null, err: null, unreadable: null }); return }
    let alive = true
    comparePage(ids)
      .then((d) => { if (alive) setState({ data: d, err: null, unreadable: null }) })
      .catch((e) => {
        if (!alive) return
        setState({
          data: null,
          err: e instanceof BoardUnreadable ? null : e.message,
          unreadable: e instanceof BoardUnreadable ? e.message : null,
        })
      })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp.get('ids')])

  if (ids.length < 2) {
    return (
      <div className="shell section-tight stack stack-3">
        <span className="eyebrow">AI model comparison</span>
        <h1>Compare models side by side</h1>
        <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '70ch' }}>
          Tick two or three models on the{' '}
          <Link to="/models" className="mb-link">models list</Link> to compare what their
          providers advertise against what engineers have actually reported — in one view,
          with no synthesised score and no winner picked for you.
        </p>
      </div>
    )
  }

  if (state.unreadable) return <Unreadable detail={state.unreadable} />
  if (state.err) {
    return (
      <div className="shell section-tight">
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>That comparison could not be built.</strong>{' '}
          {state.err}
        </Notice>
        <p style={{ marginTop: 'var(--s3)' }}>
          <Link to="/models" className="mb-link">← All models</Link>
        </p>
      </div>
    )
  }
  if (!state.data) {
    return <div className="shell section-tight"><div className="skel" style={{ height: 260 }} /></div>
  }

  // `unsourced` is deliberately not destructured — the payload still carries
  // it and nothing on this page reads it. See the note further down.
  const { models, missing, summary } = state.data
  // ⚠ NOT `reported.reports`, AND GATING ON IT BLANKED THE PAGE. That counter
  //   comes from the legacy `cell` table and is **0 on all 348 models in the
  //   registry** (#194: `cell.status` is `insufficient` on 311 of 311), while
  //   79 models carry real board entries. It used to only add a paragraph
  //   above a table that rendered anyway, so its being permanently zero was
  //   invisible; the moment the table was gated on it, every comparison
  //   rendered empty.
  //
  //   The question this page is asking is "did anybody write about these",
  //   and the answer is in the evidence itself - entries, discovered sections
  //   - not in a score nothing has ever populated.
  const hasEvidence = (m) => {
    const r = m.reported || {}
    return (r.polarity?.entries || 0) > 0
      || (r.best_for || []).length > 0
      || (r.capabilities || []).length > 0
      || (r.discovered?.metrics || []).length > 0
  }
  const anyReports = models.some(hasEvidence)

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-2">
        <Link to="/models" className="mb-link" style={{ fontSize: 'var(--fs-xs)' }}>← All models</Link>
        <span className="eyebrow">AI model comparison</span>
        <h1>{models.map((m) => m.display_name).join('  vs  ')}</h1>
        <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '76ch' }}>{summary}</p>
      </div>

      {missing?.length > 0 && (
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>
            {missing.length} of the models asked for {missing.length === 1 ? 'is' : 'are'} not in
            the registry
          </strong>{' '}
          — <span className="mono">{missing.join(', ')}</span>. Named rather than dropped: a
          comparison quietly missing a column is a different comparison.
        </Notice>
      )}

      {/* ── WHAT ENGINEERS SAID. The whole page. ───────────────────────── */}

      {/* ⚠ NOBODY HAS WRITTEN ABOUT THESE: SAY IT ONCE AND STOP. This used to
             render as a table row reading "nobody has discussed this" in every
             column - the same sentence three times, under a heading, in a grid
             built for differences. A row where every cell is identical is a row
             carrying no comparison, and three of them is not three facts. */}
      {!anyReports ? (
        <p className="dim" style={{ fontSize: 'var(--fs-sm)', maxWidth: '76ch', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--text)' }}>
            Nobody has written about {models.length === 2 ? 'either' : 'any'} of these yet.
          </strong>{' '}
          So there is nothing to compare. That is an absence we found rather than a judgement
          we made — a model here may be excellent and simply unwritten-about — and it is why
          this page shows nothing instead of showing a specification and calling it a
          comparison.
        </p>
      ) : (
      <div className="stack stack-2">
        <span className="label">What engineers said, counted</span>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch' }}>
          Every number below is counted, never scored. How a report was PHRASED is counted
          separately from how many there were, because twelve complaints and twelve
          recommendations are both "12 reports" and are not the same finding.
        </p>
        <Table
          models={models}
          rows={[
            ['Documents', (m) => {
              const p = m.reported?.polarity || {}
              const n = p.documents || 0
              return n === 0
                ? <span className="dim">none yet</span>
                : <span className="tnum">{n} {n === 1 ? 'document' : 'documents'}</span>
            }],
            // ⚠ THREE NUMBERS AND NEVER A RATIO. A net score, a percentage
            //   positive or a "sentiment" figure would be the 0-100 capability
            //   score this board refuses to compute (rule 3) - and it would
            //   pick a winner from a count of sentences.
            ['How it was phrased', (m) => {
              const p = m.reported?.polarity || {}
              if (!p.entries) return <span className="dim">nothing recorded</span>
              return (
                <span className="tnum" style={{ display: 'inline-flex', gap: 10, flexWrap: 'wrap' }}>
                  <span title="entries phrased as a problem">
                    <strong>{p.negative}</strong> negative
                  </span>
                  <span title="entries phrased as praise or a recommendation">
                    <strong>{p.positive}</strong> positive
                  </span>
                  <span className="dim" title="entries stating something without praise or complaint">
                    {p.neutral} neutral
                  </span>
                </span>
              )
            }],
            // RULE 7: the figures above are ENTRIES, and entries are not
            // people. One document can produce several, so the denominator
            // travels with them or "74 negative" means nothing.
            ['— out of', (m) => {
              const p = m.reported?.polarity || {}
              return p.entries
                ? <span className="dim tnum">{p.entries} entries, from {p.documents} documents</span>
                : <span className="dim">—</span>
            }],
            ['Best for — discovered', (m) => {
              const bf = m.reported?.best_for || []
              if (!bf.length) return <span className="dim">no job named yet</span>
              return bf.map((b) => `${b.name} (${b.reports})`).join(', ')
            }],
            ['Discussed under', (m) => {
              const caps = m.reported?.capabilities || []
              return caps.length ? caps.map(capLabel).join(', ')
                                 : <span className="dim">nothing yet</span>
            }],
            ['Metrics reported', (m) => {
              const mets = m.reported?.discovered?.metrics || []
              if (!mets.length) return <span className="dim">none</span>
              // A FIGURE TRAVELS WITH ITS BASIS (rule 7). `stated` is what the
              // vendor advertised, `reported` is what somebody measured, and
              // they are never merged into one number.
              return mets.slice(0, 3).map((x) => {
                const f = (x.figures || [])[0]
                return `${x.name}${f ? `: ${f.value} (${f.basis})` : ''}`
              }).join('; ')
            }],
          ]}
        />
      </div>
      )}

      {/* ⚠ THE PROVIDER'S SPECIFICATION IS NOT ON THIS PAGE, 2026-09-23.

             It was the larger half: price in and out, cached read, context,
             max output, tools/vision/JSON/caching, lifecycle. All of it real
             and all of it published.

             It went because of what this board IS. The evidence here comes
             from engineers writing about models they used; a provider's spec
             sheet is the one thing on the page nobody reported, and putting it
             beside counted reports invites exactly the comparison the board
             exists to refuse - a published number read as a measured one. The
             old heading tried to hold that line in words ("the provider's
             claim about itself") and the line does not hold: a table is a
             table, and the two halves looked equally like findings.

             Price and context are still on every MODEL PAGE, where they are
             described rather than ranked, and still in `/compare`'s payload
             under `advertised` for anything that wants them.

             ⚠ WHAT THIS COSTS, SAID PLAINLY: two models nobody has written
             about now compare to almost nothing. That is the honest result -
             the board has no evidence about them - and it is better than a
             spec sheet standing in for evidence that does not exist. */}

      {/* ⚠ THE "WHAT IS NOT HERE" LIST IS GONE, 2026-09-23, and the reason is
             worth keeping because rule 4 nearly justified keeping it.

             It listed `licence`, `benchmark_standing` and `one_line` with an
             explanation each, under the argument that a shorter table with no
             explanation reads as "everything comparable has been compared".

             That argument is rule 4's and it does not reach this far. Rule 4 is
             about an absence WE CAUSED - a figure withheld by a gate, a thread
             we could not read - which a reader would otherwise take for an
             absence in the world. These three were never collected at all, so
             there is no caused absence to disclose, and the section was the
             board explaining its own history to somebody who came to compare
             two models.

             `unsourced` is still in the payload and still carries its reasons.
             If a row here ever becomes an absence we cause rather than one we
             never filled, this is where it goes back. */}

      <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Change the selection on the <Link to="/models" className="mb-link">models list</Link>.
      </p>
    </div>
  )
}

/**
 * One comparison table. Models are columns, facts are rows.
 *
 * Models across the top rather than down the side because a reader compares one
 * fact at a time — they scan a row, not a column — and because two or three
 * columns fit where two or three of these tables stacked would not.
 */
function Table({ models, rows }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="cmp-table">
        <thead>
          <tr>
            <th />
            {models.map((m) => (
              <th key={m.model_version_id}>
                <Link
                  to={`/models/${m.model_version_id}`}
                  state={{ from: '/compare', name: m.display_name }}
                  className="mb-link"
                  style={{ color: 'inherit' }}
                >
                  {m.display_name}
                </Link>
                {/* ⚠ THE PROVIDER'S NAME, NOT OURS. This printed
                    `mv_de3e701e07b8bfa9` under every column - an internal key
                    shown to a reader, who cannot look it up, check it, or use
                    it anywhere. `canonical_id` is the same model in the form
                    the provider writes it. Omitted entirely where there is
                    none, rather than falling back to the database id. */}
                {m.canonical_id && (
                  <span className="mono" style={{
                    display: 'block', fontSize: 10, color: 'var(--text-3)', fontWeight: 400,
                  }}>
                    {m.canonical_id}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, cell]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              {models.map((m) => <td key={m.model_version_id}>{cell(m)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
