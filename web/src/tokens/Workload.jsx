import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '../components/ui'
import { DAYS_PER_MONTH, workloadRows } from './cost'
import { Cost, Fit } from './cells'
import { modelHref } from './links'
import PersonaPicker from './PersonaPicker'

/**
 * PRICE A WORKLOAD (2026-10-12): tokens in and out per call, calls per day,
 * and the share of the input read from a prompt cache - priced per call, per
 * day and per month on every model with the rates the workload needs.
 *
 * WHAT IS NOT IN THE FIGURE, said on the page: cache WRITES (some providers
 * charge extra to store a prompt; the registry holds no write rate), batch
 * discounts (`batch_discount` holds values above 1 whose meaning is unsettled),
 * and per-message chat overhead.
 */

const FIRST_ROWS = 25

const int = (v, min = 0) => Math.max(min, Math.floor(Number(v) || 0))
const fmtInt = (n) => (n == null ? '—' : n.toLocaleString('en-US'))

export default function Workload({ models, tokens, encodingNameFor, query, sort }) {
  const [inTok, setInTok] = useState(2000)
  const [outTok, setOutTok] = useState(500)
  const [perDay, setPerDay] = useState(1000)
  const [cachedPct, setCachedPct] = useState(0)
  const [showAll, setShowAll] = useState(false)

  const rows = useMemo(
    () => workloadRows(models, { inTok, outTok, callsPerDay: perDay, cachedShare: cachedPct / 100, query, sort, encodingNameFor }),
    [models, inTok, outTok, perDay, cachedPct, query, sort, encodingNameFor],
  )
  const shown = showAll ? rows.priced : rows.priced.slice(0, FIRST_ROWS)
  const noCache = rows.priced.filter((r) => r.cache === 'none').length

  // A PERSONA FILLS THE FOUR FIELDS (2026-10-14); editing any of them after
  // makes the numbers the reader's own. See tokens/personas.js.
  const pick = (v) => { setInTok(v.inTok); setOutTok(v.outTok); setPerDay(v.perDay); setCachedPct(v.cached) }

  return (
    <>
      <PersonaPicker value={{ inTok, outTok, perDay, cached: cachedPct }} onPick={pick} />
      <div className="card tc-form">
        <label>
          <span className="label">Input tokens per call</span>
          <input type="number" min="0" value={inTok} onChange={(e) => setInTok(int(e.target.value))} />
          {tokens > 0 && tokens !== inTok && (
            <button type="button" className="chip" onClick={() => setInTok(tokens)}>
              Use my text ({fmtInt(tokens)})
            </button>
          )}
        </label>
        <label>
          <span className="label">Output tokens per call</span>
          <input type="number" min="0" value={outTok} onChange={(e) => setOutTok(int(e.target.value))} />
        </label>
        <label>
          <span className="label">Calls per day</span>
          <input type="number" min="1" value={perDay} onChange={(e) => setPerDay(int(e.target.value, 1))} />
        </label>
        <label>
          <span className="label">Input read from cache</span>
          <span className="tc-pct">
            <input type="range" min="0" max="100" step="5" value={cachedPct}
                   onChange={(e) => setCachedPct(int(e.target.value))} aria-label="Share of input read from cache" />
            <span className="tnum">{cachedPct}%</span>
          </span>
        </label>
      </div>

      <p className="dim tc-note">
        A month is {DAYS_PER_MONTH} days. The cached share is priced at the model's cached-read rate
        where one is published; cache writes, which some providers charge extra for, are not included,
        and neither are batch discounts.
        {cachedPct > 0 && noCache > 0 && ` ${noCache} of these models publish no cached-read rate, so their rows are priced without caching and marked.`}
      </p>

      <div className="tc-table" role="table" aria-label="Monthly cost per model">
        <div className="tc-tr tc-th" role="row">
          <span role="columnheader">Model</span>
          <span role="columnheader">Fits?</span>
          <span role="columnheader">Per call</span>
          <span role="columnheader">Per day</span>
          <span role="columnheader">Per month</span>
        </div>
        {shown.map((r) => (
          <div key={r.id} className="tc-tr" role="row">
            <span role="cell" className="tc-model">
              <Link to={modelHref(r.mvId)}>{r.name}</Link>
              <span className="dim">
                {r.provider || 'provider not recorded'}
                {r.cache === 'none' && (
                  <Badge tone="warn" style={{ marginLeft: 6 }}
                         title="No cached-read rate is published, so this row is priced without caching">
                    no cache rate
                  </Badge>
                )}
              </span>
            </span>
            <Fit fit={r.fit} what="context window or output limit" />
            <Cost row={r} value={r.perCall} label="Per call" />
            <Cost row={r} value={r.perDay} label="Per day" />
            <Cost row={r} value={r.perMonth} label="Per month" strong />
          </div>
        ))}
        {rows.priced.length === 0 && (
          <p className="dim tc-note" style={{ padding: 'var(--s2)' }}>
            {query ? `No priced model matches “${query}”.` : 'No model publishes the rates this workload needs.'}
          </p>
        )}
      </div>

      {rows.priced.length > FIRST_ROWS && (
        <button type="button" className="btn btn-quiet" style={{ alignSelf: 'flex-start' }}
                onClick={() => setShowAll((v) => !v)}>
          {showAll ? `Show the first ${FIRST_ROWS}` : `Show all ${fmtInt(rows.priced.length)} priced models`}
        </button>
      )}

      {rows.unpriced.length > 0 && (
        <details className="tc-unpriced">
          <summary>
            {rows.unpriced.length} {rows.unpriced.length === 1 ? 'model is' : 'models are'} missing a rate this workload needs
          </summary>
          <p className="dim tc-note">
            Not free, and not left out: each lacks a per-token input or output rate in the registry,
            so this workload cannot be priced on it.
          </p>
          <p className="tc-unpriced-list">
            {rows.unpriced.map((r, i) => (
              <span key={r.id}>{i ? ', ' : ''}<Link to={modelHref(r.mvId)}>{r.name}</Link></span>
            ))}
          </p>
        </details>
      )}
    </>
  )
}
