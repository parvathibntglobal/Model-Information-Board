import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { DAYS_PER_MONTH, fmtUsd } from './cost'
import { modelHref } from './links'

/**
 * PROMPT-CACHE SAVINGS (2026-10-15): what reading a repeated prompt prefix from
 * the cache saves, per model, per month - opened from the token counter.
 *
 * ARITHMETIC ON PUBLISHED RATES ONLY. Saving = cached tokens x calls x
 * (input rate - cached-read rate). A model publishing no cached-read rate is
 * listed apart and named - not given a saving of zero, which would read as
 * "caching does nothing here" when the truth is "nobody published the rate"
 * (rule 6).
 *
 * AN UPPER BOUND, AND SAID SO. Some providers charge to WRITE a prefix into the
 * cache and expire it after minutes; the registry holds no write rate and no
 * lifetime, so neither is subtracted. The real saving is this or less.
 */
const int = (v, min = 0) => Math.max(min, Math.floor(Number(v) || 0))
const SHOWN = 20

export default function CacheSavings({ models, tokens, onClose }) {
  const [prompt, setPrompt] = useState(tokens > 0 ? tokens : 4000)
  const [share, setShare] = useState(60)
  const [perDay, setPerDay] = useState(1000)
  const [all, setAll] = useState(false)

  useEffect(() => {
    const esc = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  const rows = useMemo(() => {
    const cached = prompt * (share / 100)
    const calls = perDay * DAYS_PER_MONTH
    const priced = []
    const noRate = []
    for (const m of models || []) {
      if (m.price_in == null) continue
      const name = m.display_name || m.canonical_id
      if (m.price_cached_read == null) { noRate.push({ m, name }); continue }
      const without = (prompt * m.price_in * calls) / 1e6
      const withCache = (((prompt - cached) * m.price_in + cached * m.price_cached_read) * calls) / 1e6
      priced.push({ m, name, without, withCache, saved: without - withCache,
                    pct: without > 0 ? (without - withCache) / without : 0 })
    }
    priced.sort((a, b) => b.saved - a.saved || a.name.localeCompare(b.name))
    noRate.sort((a, b) => a.name.localeCompare(b.name))
    return { priced, noRate }
  }, [models, prompt, share, perDay])

  const shown = all ? rows.priced : rows.priced.slice(0, SHOWN)
  return (
    <div className="cs-scrim" onClick={onClose} role="presentation">
      <aside className="cs-drawer" role="dialog" aria-label="Prompt-cache savings" onClick={(e) => e.stopPropagation()}>
        <div className="row-between" style={{ alignItems: 'baseline' }}>
          <h2 style={{ margin: 0, fontSize: 'var(--fs-h3)' }}>Prompt-cache savings</h2>
          <button type="button" className="btn btn-quiet" onClick={onClose} aria-label="Close">Close ✕</button>
        </div>
        <p className="dim tc-note">
          When every call starts with the same system prompt, tools or documents, that prefix can be read
          from a cache at a lower rate. This is what that saves on each model's published rates.
        </p>
        <div className="cs-form">
          <label><span className="label">Prompt tokens per call</span>
            <input type="number" min="0" value={prompt} onChange={(e) => setPrompt(int(e.target.value))} /></label>
          <label><span className="label">Calls per day</span>
            <input type="number" min="1" value={perDay} onChange={(e) => setPerDay(int(e.target.value, 1))} /></label>
          <label className="cs-wide"><span className="label">Repeated prefix: {share}% of the prompt</span>
            <input type="range" min="0" max="100" step="5" value={share} onChange={(e) => setShare(int(e.target.value))}
                   aria-label="Share of the prompt that repeats" /></label>
        </div>
        {tokens > 0 && tokens !== prompt && (
          <button type="button" className="chip" style={{ alignSelf: 'flex-start' }} onClick={() => setPrompt(tokens)}>
            Use my text ({tokens.toLocaleString('en-US')} tokens)
          </button>
        )}

        <div className="cs-table" role="table" aria-label="Monthly input cost with and without caching">
          <div className="cs-tr cs-th" role="row">
            <span role="columnheader">Model</span><span role="columnheader">Without</span>
            <span role="columnheader">With cache</span><span role="columnheader">Saved / month</span>
          </div>
          {shown.map((r) => (
            <div key={r.m.model_version_id} className="cs-tr" role="row">
              <span role="cell"><Link to={modelHref(r.m.model_version_id)}>{r.name}</Link></span>
              <span role="cell" className="tnum">{fmtUsd(r.without)}</span>
              <span role="cell" className="tnum">{fmtUsd(r.withCache)}</span>
              <span role="cell" className="tnum"><b>{fmtUsd(r.saved)}</b> <span className="dim">{Math.round(r.pct * 100)}%</span></span>
            </div>
          ))}
        </div>
        {rows.priced.length > SHOWN && (
          <button type="button" className="btn btn-quiet" style={{ alignSelf: 'flex-start' }} onClick={() => setAll((v) => !v)}>
            {all ? `Show the first ${SHOWN}` : `Show all ${rows.priced.length}`}
          </button>
        )}
        {rows.noRate.length > 0 && (
          <details className="tc-unpriced">
            <summary>{rows.noRate.length} models publish no cached-read rate</summary>
            <p className="dim tc-note">Not "no saving": nobody published the rate, so there is nothing to compute.</p>
            <p className="tc-unpriced-list">{rows.noRate.map((r, i) => <span key={r.m.model_version_id}>{i ? ', ' : ''}{r.name}</span>)}</p>
          </details>
        )}
        <p className="dim tc-note">
          Input only, over {DAYS_PER_MONTH} days. An upper bound: cache WRITES, which some providers charge
          extra for, and a cache's expiry are not in the registry, so neither is subtracted.
        </p>
      </aside>
    </div>
  )
}
