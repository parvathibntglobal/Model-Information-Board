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

// The extractor running now. Kept beside the names above so a switch is one
// edit in one file — and it must match `EXTRACTOR_MODEL` in the backend, which
// is what actually spends the money.
const CURRENT_EXTRACTOR = 'deepseek/deepseek-v4-flash'

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
          <Badge tone={rapid.instrumented ? 'mute' : 'fail'}>{rapid.instrumented ? 'requests' : 'no reading'}</Badge>
        ) : (
          <Badge tone={pct != null && pct >= 80 ? 'fail' : 'mute'}>
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

  // ── THE CURRENT EXTRACTOR'S SPEND, which the ledger does not have ─────────
  //
  // `by_model_total` is THIS MACHINE'S ledger, and it holds one row: Gemini.
  // DeepSeek has spent real money on the key — the provider reports
  // $2.48266 total against Gemini's corrected $2.4780 — and none of it reached
  // the ledger, because the runs that spent it errored before the write.
  //
  // So the figure comes from the PROVIDER instead, two ways that must agree:
  //   today_usd   what the provider says was spent today
  //   remainder   key total minus every model the ledger does know about
  // Both are arithmetic on measured figures, never an estimate. They are shown
  // as one row only when they CORROBORATE each other; if they diverge, the
  // attribution is not safe and the row says so rather than picking one.
  const ledgerKnown = rows.reduce((sum, [, spent]) => sum + spent, 0)
  const remainder = everyone.available ? (everyone.total_usd ?? 0) - ledgerKnown : null
  const todayOnKey = everyone.today_usd ?? null
  const CENT = 0.005 // half a cent: below this the two figures are the same number
  const corroborated =
    remainder != null && todayOnKey != null && Math.abs(remainder - todayOnKey) < CENT
  // Only shown when there IS unledgered spend. A zero row would imply we had
  // checked and DeepSeek had cost nothing, which is a different claim.
  const currentSpend = remainder != null && remainder > 0.00005 ? remainder : null
  const alreadyListed = rows.some(([m]) => m === CURRENT_EXTRACTOR)

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

      {/* The current extractor, listed BELOW the previous one so the switch
          reads in order. Its figure is the provider's, not the ledger's, and
          the row says which — a number whose source is not stated is not
          evidence (rule 7). */}
      {currentSpend != null && !alreadyListed && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
          <span>
            <strong style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(CURRENT_EXTRACTOR)}</strong>{' '}
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{CURRENT_EXTRACTOR}</span>{' '}
            <Badge tone={corroborated ? 'mute' : 'warn'}>
              {corroborated ? 'from the provider' : 'unattributed'}
            </Badge>
          </span>
          <span className="tnum">{usd(currentSpend)}</span>
        </div>
      )}

      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Spend to date ran on <strong>Gemini 2.5 Flash</strong>; the extractor is now{' '}
        <strong>DeepSeek V4 Flash</strong>, so new spend accrues under it — the two stay
        separated above.
      </span>
      {currentSpend != null && !alreadyListed && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          {corroborated ? (
            <>
              The DeepSeek figure is <strong>the provider&apos;s</strong>, not this machine&apos;s
              ledger — the runs that spent it errored before the ledger write. It is the key
              total minus every model the ledger knows, and it matches what the provider
              reports for today ({usd(todayOnKey)}), which is why it is attributed rather
              than left as a gap.
            </>
          ) : (
            <>
              <strong style={{ color: 'var(--text)' }}>Unattributed.</strong> {usd(currentSpend)}{' '}
              is on the key and not in this machine&apos;s ledger, but it does not match what
              the provider reports for today ({usd(todayOnKey)}) — so it may not all be
              DeepSeek. Shown rather than hidden, and not assigned.
            </>
          )}
        </span>
      )}
    </div>
  )
}

/**
 * RapidAPI spend — one shared key metering the X and Reddit harvest paths.
 *
 * THE SPEND ON THIS KEY IS REQUESTS, NOT DOLLARS, and that is not a gap in the
 * panel: the plan's per-request price is in nobody's config, so a dollar figure
 * here would be one this code invented (rule 3). Requests used IS the spend —
 * `limit − remaining`, both the gateway's own header values.
 *
 * The number is RapidAPI's own reading cached with its date; it moves only when
 * a metered fetch runs, never live. `read_on` names the path whose fetch took
 * it, because one key cannot be split by endpoint — the gateway meters the key.
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
  const used = rapid.requests_used
  const limit = rapid.quota_limit
  const share =
    typeof used === 'number' && typeof limit === 'number' && limit > 0
      ? (used / limit) * 100
      : null
  // Whose fetch took the reading. `null` is a record written before the field
  // existed — unrecorded, which is not the same as "this tab's path".
  const readOn = rapid.read_on || null
  const mine = readOn === (which === 'X' ? 'x' : 'reddit')

  return (
    <div className="stack stack-2">
      <span className="label">
        Spend on this key — {which} path, billed in requests
      </span>
      <div className="grid g3">
        <Stat n={n(used)} l="requests spent" />
        <Stat n={share == null ? '—' : `${share.toFixed(2)}%`} l="of the quota" />
        <Stat n={n(rapid.quota_remaining)} l="left" />
      </div>
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        <strong style={{ color: 'var(--text)' }}>No dollar amount, deliberately.</strong>{' '}
        RapidAPI sells this as a request quota and the per-request price is not in
        our config, so a dollar figure would be invented rather than measured.{' '}
        {n(used)} of {n(limit)} requests is the spend.
      </span>
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        As of {rapid.as_of || 'the last fetch'}, read on{' '}
        {readOn ? (
          <strong style={{ color: 'var(--text)' }}>
            the {readOn === 'x' ? 'X' : 'Reddit'} fetch
          </strong>
        ) : (
          'a fetch that did not record which path'
        )}
        .{' '}
        {mine
          ? `This tab's own path took the reading.`
          : `One key meters both paths, so the figure is the ${which} spend too — but it was last read on a ${readOn ? (readOn === 'x' ? 'X' : 'Reddit') : 'different'} fetch, so any ${which} requests since then are already spent and not yet in it.`}
      </span>
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Two things the denominator does not say: the window is{' '}
        <strong>23.9 days, not a month</strong>, and the billed tier is{' '}
        <strong>unverified</strong> — the gateway header says {n(limit)} while the
        plan page says 500,000, and only opening the RapidAPI subscription page
        settles it. On the smaller tier the cut-off arrives at half the figure above.
      </span>
    </div>
  )
}
