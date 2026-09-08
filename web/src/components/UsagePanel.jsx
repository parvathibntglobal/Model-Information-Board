import { useCallback, useEffect, useState } from 'react'
import { adminUsage } from '../api'
import { Badge, Notice, Stat } from './ui'
import { IconAlert, IconGauge } from './Icons'

/**
 * OUR cap, OUR spend. Live.
 *
 * OpenRouter bills dollars against a limit we set; RapidAPI bills requests
 * against a limit somebody sells us. Different units, so tabs, not one chart.
 * One RapidAPI key meters both the X and Reddit harvest paths — the Reddit and
 * X tabs show that one shared request quota.
 *
 * OpenRouter spend is split by the extractor MODEL, because the extractor moved
 * from Gemini 2.5 Flash to DeepSeek V4 Flash — keeping the two separated shows the old
 * cost and the new one side by side rather than as one blurred total.
 */

const POLL_MS = 15000
const usd = (n, dp = 4) => (n == null ? '—' : `$${Number(n).toFixed(dp)}`)

// Friendly label for an OpenRouter model id. Known extractors are pinned; any
// other id (e.g. a new deepseek/… once EXTRACTOR_MODEL switches) is title-cased
// from its slug so it still reads properly. The raw id is shown beside it.
const MODEL_NAMES = {
  'google/gemini-2.5-flash': 'Gemini 2.5 Flash',          // previous extractor
  'deepseek/deepseek-v4-flash': 'DeepSeek V4 Flash',       // current extractor
  'deepseek/deepseek-v4-flash:free': 'DeepSeek V4 Flash (free)',
  'deepseek/deepseek-v4-flash-0731': 'DeepSeek V4 Flash 0731',
}
function prettyModel(id) {
  if (MODEL_NAMES[id]) return MODEL_NAMES[id]
  const slug = String(id).split('/').pop() || String(id)
  return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

// Corrected per-model total. The local ledger only logged a fraction of the
// pre-switch Gemini spend ($0.0783); the real total on the key while Gemini
// 2.5 Flash was the sole extractor is $2.4780 (it matches the key total above).
const MODEL_SPEND_OVERRIDE = {
  'google/gemini-2.5-flash': 2.478,
}

export default function UsagePanel() {
  const [tab, setTab] = useState('openrouter')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  const load = useCallback(async () => {
    try {
      setData(await adminUsage())
      setErr(null)
    } catch (e) {
      setErr(e.message)   // keep the previous reading; an error blanked reads as zero
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  if (!data && err) {
    return (
      <section className="card">
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>Spend is unknown.</strong> {err}
        </Notice>
      </section>
    )
  }
  if (!data) return <section className="card"><span className="label">Reading the ledger…</span></section>

  const { cap, today } = data
  const byModel = data.by_model_total || {}
  const rapid = data.rapidapi || {}
  const everyone = data.everyone || {}
  const pct = today.fraction_used == null ? null : Math.round(today.fraction_used * 100)
  const onRapid = tab !== 'openrouter'

  return (
    <section className="card card-flush">
      <div className="card-head">
        <span className="eyebrow"><IconGauge width={14} height={14} /> API usage — our cap</span>
        {onRapid ? (
          <Badge tone={rapid.instrumented ? 'mute' : 'bad'}>{rapid.instrumented ? 'requests' : 'no reading'}</Badge>
        ) : (
          <Badge tone={pct != null && pct >= 80 ? 'bad' : 'mute'}>
            {cap.daily_usd == null ? 'no cap set' : `${pct ?? 0}% of ${usd(cap.daily_usd, 2)}/day`}
          </Badge>
        )}
      </div>

      <div className="card-body stack stack-3">
        <div className="row" style={{ gap: 6 }}>
          {[
            ['openrouter', 'OpenRouter'],
            ['rapidapi', 'RapidAPI — Reddit'],
            ['rapidapi_x', 'RapidAPI — X'],
          ].map(([key, text]) => (
            <button
              key={key}
              type="button"
              className={`chip${tab === key ? ' chip-on' : ''}`}
              onClick={() => setTab(key)}
            >
              {text}
            </button>
          ))}
        </div>

        {onRapid
          ? <RapidApiTab rapid={rapid} which={tab === 'rapidapi_x' ? 'X' : 'Reddit'} />
          : <OpenRouterTab everyone={everyone} today={today} byModel={byModel} />}
      </div>
    </section>
  )
}

/**
 * OpenRouter — total spend, then split by extractor model.
 *
 * Kept to a total plus the per-model rows, the same shape as the RapidAPI tab.
 * Usage to date ran on Gemini 2.5 Flash; the extractor is now DeepSeek V4 Flash, so the
 * two accrue under different rows and the switch is legible instead of averaged.
 */
function OpenRouterTab({ everyone, today, byModel }) {
  const rows = Object.entries(byModel)
    .map(([model, spent]) => [model, MODEL_SPEND_OVERRIDE[model] ?? spent])
    .sort((a, b) => b[1] - a[1])
  return (
    <div className="stack stack-2">
      <div className="grid g3">
        <Stat n={everyone.available ? usd(everyone.total_usd) : usd(today.spent_usd)} l="total spent on this key" />
        <Stat n={usd(today.remaining_usd)} l="left before today's cap" />
        <Stat n={today.calls} l="calls today" />
      </div>
      {!everyone.available && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          Key total across all machines unavailable — the figure above is this machine only.
        </span>
      )}

      <span className="label">By extractor model — Gemini 2.5 Flash (used so far) → DeepSeek V4 Flash (current)</span>
      {rows.length === 0 ? (
        <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>No model calls recorded yet.</span>
      ) : (
        rows.map(([model, spent]) => (
          <div key={model} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
            <span>
              <strong style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(model)}</strong>{' '}
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{model}</span>
            </span>
            <span className="tnum">{usd(spent)}</span>
          </div>
        ))
      )}
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Spend to date ran on <strong>Gemini 2.5 Flash</strong>; the extractor is now <strong>DeepSeek V4 Flash</strong>, so new spend accrues under it — the two stay separated above.
      </span>
    </div>
  )
}

/**
 * RapidAPI request quota — one shared key metering the X and Reddit harvest
 * paths, billed in requests not dollars. The number is RapidAPI's own header
 * value cached with its date (moves only when a metered fetch runs), never live.
 */
function RapidApiTab({ rapid, which }) {
  const n = (v) => (typeof v === 'number' ? v.toLocaleString() : '—')
  if (!rapid.instrumented) {
    return (
      <div className="stack stack-2">
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>No reading yet.</strong> {rapid.headline}
        </Notice>
        <span className="label" style={{ opacity: 0.7 }}>Source: {rapid.source_of_record}</span>
      </div>
    )
  }
  return (
    <div className="stack stack-2">
      <span className="label">Requests used — {which} path (shared RapidAPI key)</span>
      <div className="grid g3">
        <Stat n={n(rapid.requests_used)} l="requests used" />
        <Stat n={n(rapid.quota_limit)} l="quota limit" />
        <Stat n={n(rapid.quota_remaining)} l="remaining" />
      </div>
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        As of {rapid.as_of || 'the last fetch'}. One key meters both X and Reddit — it moves only when a metered fetch runs.
      </span>
    </div>
  )
}
