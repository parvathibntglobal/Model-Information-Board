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

  const { models, missing, unsourced, summary } = state.data
  const anyReports = models.some((m) => (m.reported?.reports || 0) > 0)

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

      {/* ── REPORTED ─ what people found. First, because it is the only half
             that can settle anything. ─────────────────────────────────────── */}
      <div className="stack stack-2">
        <span className="label">Reported — what engineers said, counted</span>
        {!anyReports && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch' }}>
            <strong style={{ color: 'var(--text)' }}>Nobody has reported on any of these yet.</strong>{' '}
            So this comparison is a specification sheet, not a recommendation. That is an absence
            we found, not a judgement we made — a model here may be excellent and simply
            unwritten-about.
          </p>
        )}
        <Table
          models={models}
          rows={[
            ['Reports', (m) => {
              const n = m.reported?.reports || 0
              return n === 0
                ? <span className="dim">nobody has discussed this</span>
                : <span className="tnum">{n} {n === 1 ? 'report' : 'reports'}</span>
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

      {/* ── ADVERTISED ─ what is on the tin. Evidence of nothing. ─────────── */}
      <div className="stack stack-2">
        <span className="label">Advertised — the provider's claim about itself</span>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch' }}>
          Measured figures, published by the vendor, and evidence of nothing about whether the
          model does your job. A blank rate is a router with no price of its own — never a zero.
        </p>
        <Table
          models={models}
          rows={[
            ['Provider', (m) => m.provider || <span className="dim">—</span>],
            ['Cost per Mtok — in / out', (m) => {
              const a = m.advertised || {}
              return a.price_in == null
                ? <span className="dim">no rate published</span>
                : <span className="mono">{fmtPrice(a.price_in)} / {fmtPrice(a.price_out)}</span>
            }],
            ['Cached read', (m) => m.advertised?.price_cached_read == null
              ? <span className="dim">—</span>
              : <span className="mono">{fmtPrice(m.advertised.price_cached_read)}</span>],
            ['Context window', (m) => m.advertised?.context
              ? <span className="mono">{fmtTokens(m.advertised.context)}</span>
              : <span className="dim">not published</span>],
            ['Max output', (m) => m.advertised?.max_output_tokens
              ? <span className="mono">{fmtTokens(m.advertised.max_output_tokens)}</span>
              : <span className="dim">not published</span>],
            ['Tools · vision · JSON · caching', (m) => {
              const a = m.advertised || {}
              // `null` is not `false`. A flag the provider never stated stays a
              // dash, because "does not support tools" and "did not say" are
              // different claims (rule 6).
              const mark = (v) => v === true ? '✓' : v === false ? '✗' : '–'
              return (
                <span className="mono" title="✓ stated · ✗ stated as unsupported · – not stated">
                  {mark(a.tools)} {mark(a.vision)} {mark(a.structured_output)} {mark(a.caching)}
                </span>
              )
            }],
            ['Lifecycle', (m) => m.advertised?.lifecycle || <span className="dim">—</span>],
          ]}
        />
      </div>

      {/* ── WHAT IS NOT HERE, and why. ───────────────────────────────────── */}
      {unsourced?.length > 0 && (
        <div className="stack stack-2">
          <span className="label">Rows the landing demo had that this cannot</span>
          <div className="stack stack-1">
            {unsourced.map((u) => (
              <p key={u.row} className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '80ch' }}>
                <strong style={{ color: 'var(--text)' }}>
                  {u.row.replace(/_/g, ' ')}
                </strong>{' '}
                — {u.why}.
              </p>
            ))}
          </div>
        </div>
      )}

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
                <span className="mono" style={{
                  display: 'block', fontSize: 10, color: 'var(--text-3)', fontWeight: 400,
                }}>
                  {m.model_version_id}
                </span>
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
