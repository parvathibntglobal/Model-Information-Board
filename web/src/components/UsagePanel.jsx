import { useCallback, useEffect, useState } from 'react'
import { adminUsage } from '../api'
import { Badge, Notice, Stat } from './ui'
import { IconAlert, IconGauge } from './Icons'

/**
 * OUR cap, OUR spend. Live.
 *
 * Deliberately not OpenRouter's numbers. The provider has its own ceilings —
 * account credit and a per-key cap — on a different schedule, and neither is
 * the figure a person can act on. `EXTRACTION_DAILY_BUDGET_USD` is.
 *
 * ONE CAP, TWO STAGES. The limit is a single daily dollar shared by extraction
 * and the ask box, so the cap is rendered once and every usage figure is split
 * by stage. Two bars under one ceiling, never two ceilings.
 */

const STAGE_TONE = { extract: 'var(--accent)', ask: 'var(--warn, #d08770)' }
const POLL_MS = 15000

const usd = (n, dp = 4) => (n == null ? '—' : `$${Number(n).toFixed(dp)}`)

export default function UsagePanel() {
  // TWO PAID APIS, TWO UNITS, so they are tabs rather than two halves of one
  // chart. OpenRouter bills dollars per day against a limit WE set; RapidAPI
  // bills requests per 23.9 days against a limit somebody sells us. Putting
  // both on one axis would be a rule-7 failure with a unit change.
  const [tab, setTab] = useState('openrouter')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [at, setAt] = useState(null)

  const load = useCallback(async () => {
    try {
      const next = await adminUsage()
      setData(next)
      setErr(null)
      setAt(new Date())
    } catch (e) {
      // The PREVIOUS reading is kept on screen rather than blanked. A spend
      // figure replaced by an error is a figure a reader will assume is zero.
      setErr(e.message)
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
          <strong style={{ color: 'var(--text)' }}>Spend is unknown.</strong> {err}{' '}
          Unknown is not zero — treat this as “we cannot see the meter”, not as “nothing
          has been spent”.
        </Notice>
      </section>
    )
  }
  if (!data) return <section className="card"><span className="label">Reading the ledger…</span></section>

  const { cap, today, by_stage: stages, rates, hourly, daily, ledger } = data
  const byModel = data.by_model_total || {}
  const rapid = data.rapidapi || {}
  const everyone = data.everyone || {}
  const pct = today.fraction_used == null ? null : Math.round(today.fraction_used * 100)
  const unwired = ledger.unwired_stages || []

  return (
    <section className="card card-flush">
      <div className="card-head">
        <span className="eyebrow"><IconGauge width={14} height={14} /> API usage — our cap</span>
        {tab === 'openrouter' ? (
          <Badge tone={pct != null && pct >= 80 ? 'bad' : 'mute'}>
            {cap.daily_usd == null ? 'no cap set' : `${pct ?? 0}% of ${usd(cap.daily_usd, 2)}/day`}
          </Badge>
        ) : (
          <Badge tone={rapid.instrumented ? 'mute' : 'bad'}>
            {rapid.instrumented ? 'requests' : 'not instrumented'}
          </Badge>
        )}
      </div>

      <div className="card-body stack stack-3">
        <div className="row" style={{ gap: 6 }}>
          {[
            ['openrouter', 'OpenRouter — extractor + ask'],
            ['rapidapi', 'RapidAPI — Reddit'],
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

        {tab === 'rapidapi' ? <RapidApiTab rapid={rapid} /> : (
        <>
        {/* INSIDE THE OPENROUTER TAB, not above both. It is this key's total,
            and RapidAPI is a different key entirely - above the tabs it read as
            a figure covering both, which is a bigger claim than the number
            supports. First thing in the tab, though, because everything below
            it is one machine's share of the same key. */}
        <div className="stack stack-1">
          <span className="label">Total spent by everyone on this key</span>
          {everyone.available ? (
            <>
              <span className="stat-n tnum" style={{ fontSize: 'var(--fs-xl, 1.5rem)' }}>
                {usd(everyone.total_usd)}
              </span>
              <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
                Reported by OpenRouter, so it counts calls from every machine using
                this key — {usd(data.today?.spent_usd)} of it recorded here. Everything
                below is this machine only, which is why the two differ.
              </span>
            </>
          ) : (
            <Notice icon={<IconAlert />}>
              <strong style={{ color: 'var(--text)' }}>
                Spend across all machines is unknown.
              </strong>{' '}
              {everyone.why} Unknown is not zero — everything below is this machine only.
            </Notice>
          )}
        </div>
        {/* THE CAVEATS COME FIRST. Both of these change what every number below
            MEANS, so putting them after the figures would let a reader finish
            with the reassuring half. */}
        {unwired.length > 0 && ledger.rows > 0 && (
          <Notice icon={<IconAlert />}>
            <strong style={{ color: 'var(--text)' }}>
              {unwired.join(' and ')} {unwired.length > 1 ? 'have' : 'has'} never recorded a call.
            </strong>{' '}
            That is a wiring gap, not a quiet day — every total here is spend from the
            other stage only, and a flat line for {unwired.join(' / ')} means the chart
            cannot see it rather than that it is free.
          </Notice>
        )}
        {/* `counting_since` is null on an EMPTY ledger, and the floor flag is
            true there because no rows cannot mean full coverage - so both were
            true at once and this printed "the ledger began at  UTC" with a hole
            where the time goes. The empty case is already stated by the summary
            below; this notice is for the real one, a ledger that started partway
            through today. */}
        {today.is_a_floor_not_a_total && ledger.counting_since && (
          <Notice icon={<IconAlert />}>
            <strong style={{ color: 'var(--text)' }}>Today’s figure is a floor.</strong>{' '}
            The ledger began at {ledger.counting_since?.slice(11, 16)} UTC, after today
            started, so spend before that is not counted here.
          </Notice>
        )}

        <p className="muted" style={{ margin: 0 }}>
          {data.summary}
        </p>

        {/* ONE CEILING. The bar is the shared cap; the fills are the two stages
            stacked inside it, so the split can never read as two budgets. */}
        <div className="stack stack-1">
          <span className="label">
            Today, both stages together — resets at 00:00 UTC ({cap.resets_at?.slice(0, 10)})
          </span>
          <div
            style={{
              display: 'flex', height: 14, borderRadius: 7, overflow: 'hidden',
              background: 'var(--bg-3, rgba(127,127,127,.18))',
            }}
            role="img"
            aria-label={`${usd(today.spent_usd)} of ${usd(cap.daily_usd, 2)} used`}
          >
            {stages.map((s) => {
              const frac = cap.daily_usd ? (s.spent_usd / cap.daily_usd) * 100 : 0
              return (
                <div key={s.stage} title={`${s.stage}: ${usd(s.spent_usd)}`}
                     style={{ width: `${Math.min(100, frac)}%`, background: STAGE_TONE[s.stage] }} />
              )
            })}
          </div>
        </div>

        <div className="grid g2">
          <Stat n={usd(today.spent_usd)} l="spent today, both stages" />
          <Stat n={usd(today.remaining_usd)} l="left before the cap binds" />
          <Stat n={today.calls} l="calls today" />
          <Stat n={today.calls_remaining ?? '—'} l="more calls the rest affords" />
        </div>

        {/* WHERE THE SHARED DOLLAR WENT */}
        <div className="stack stack-2">
          <span className="label">Which stage spent it — one cap, two spenders</span>
          {stages.map((s) => (
            <div key={s.stage} className="stack stack-1">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <span>
                  <span style={{
                    display: 'inline-block', width: 9, height: 9, borderRadius: 2,
                    background: STAGE_TONE[s.stage], marginRight: 7,
                  }} />
                  {s.label}
                </span>
                <span className="tnum">
                  {s.ever_recorded
                    ? <>{usd(s.spent_usd)} · {s.calls} calls</>
                    : <Badge tone="bad">not recording</Badge>}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* PER-MODEL TOTAL — OUR recorded spend, all-time, split by the model
            that ran. All-time on purpose: the by-stage figures above are today
            only (they share the cap window), so a per-model total is the figure
            that actually compares Gemini vs DeepSeek. Separate from "everyone"
            above, which is the whole key's total from OpenRouter, not just ours. */}
        <div className="stack stack-2">
          <span className="label">Total recorded per model — all-time, our spend</span>
          {Object.keys(byModel).length === 0 ? (
            <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>
              No model calls recorded yet.
            </span>
          ) : (
            Object.entries(byModel)
              .sort((a, b) => b[1] - a[1])
              .map(([model, spent]) => (
                <div key={model} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <span className="mono" style={{ fontSize: 'var(--fs-sm)' }}>{model}</span>
                  <span className="tnum">{usd(spent)}</span>
                </div>
              ))
          )}
        </div>

        <Chart title="Spend per hour, last 24h — stacked by stage" points={hourly} stages={stages} />
        <Chart title="Spend per day, last 14d — stacked by stage" points={daily} stages={stages}
               cap={cap.daily_usd} />

        <div className="grid g2">
          <Stat n={usd(rates.usd_last_hour, 5)} l="spent in the last hour" />
          <Stat
            n={rates.hours_to_cap == null ? 'not at this rate' : `${rates.hours_to_cap}h`}
            l="until the cap binds, at that rate"
          />
          <Stat n={usd(rates.measured_cost_per_call_usd, 5)} l="measured cost per call" />
          <Stat
            n={`$${rates.price_in_per_million_usd} / $${rates.price_out_per_million_usd}`}
            l="price per 1M tokens, in / out"
          />
        </div>

        <span className="label" style={{ opacity: 0.7 }}>
          {ledger.rows} calls recorded since {ledger.counting_since?.replace('T', ' ').slice(0, 16)} UTC
          {at && ` · refreshed ${at.toLocaleTimeString()}`}
          {err && ` · last refresh failed: ${err}`}
        </span>
        </>
        )}
      </div>
    </section>
  )
}

/**
 * A stacked column chart, built from plain divs.
 *
 * No charting library: the page must stay dependency-free, and a two-series bar
 * chart is less code than the import. Every bar carries a title attribute, so
 * the numbers are readable without a tooltip layer.
 *
 * The y-axis is scaled to the largest bucket, NOT to the cap, unless the cap is
 * the larger of the two — a chart scaled to a $1 ceiling renders a real $0.006
 * hour as nothing at all, which is how a spend spike goes unseen.
 */
function Chart({ title, points, stages, cap }) {
  const peak = Math.max(...points.map((p) => p.usd), 0)
  const top = cap && cap > peak ? cap : peak
  const nothing = top <= 0

  return (
    <div className="stack stack-1">
      <span className="label">{title}</span>
      {nothing ? (
        <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
          No recorded spend in this window. That is the ledger reporting nothing, not
          a guarantee nothing was spent — see the caveats above.
        </span>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <div style={{
            display: 'flex', alignItems: 'flex-end', gap: 3, height: 92, minWidth: 260,
          }}>
            {points.map((p) => (
              <div key={p.starts_at} style={{ flex: '1 0 8px', textAlign: 'center' }}
                   title={`${p.label} — $${p.usd.toFixed(5)}, ${p.calls} call(s)`}>
                <div style={{
                  display: 'flex', flexDirection: 'column-reverse', justifyContent: 'flex-start',
                  height: 72, alignItems: 'stretch',
                }}>
                  {stages.map((s) => {
                    const value = p.by_stage?.[s.stage] || 0
                    return value > 0 ? (
                      <div key={s.stage} style={{
                        height: `${(value / top) * 100}%`,
                        background: STAGE_TONE[s.stage],
                        minHeight: 1,
                      }} />
                    ) : null
                  })}
                </div>
                <span style={{
                  fontSize: 9, color: 'var(--text-3)', display: 'block', marginTop: 3,
                }}>{p.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


/**
 * RapidAPI — Reddit, billed in requests rather than dollars, so it cannot share
 * an axis with the LLM cap.
 *
 * When a Reddit fetch has recorded a quota reading, this shows the requests USED
 * (limit − remaining) — the spend on the key — labelled AS OF the time it was
 * read, never as live. It is RapidAPI's own header value cached with its date,
 * not a figure recomputed here, and it is requests not dollars because the
 * plan's per-request price is not configured (a dollar figure would be invented,
 * rule 6). Before the first fetch there is nothing to show, and it says so.
 */
function RapidApiTab({ rapid }) {
  if (!rapid.instrumented) {
    return (
      <div className="stack stack-3">
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>Nothing recorded yet.</strong>{' '}
          {rapid.headline}
        </Notice>
        <div className="stack stack-1">
          <span className="label">How it fills in</span>
          <p className="muted" style={{ margin: 0 }}>{rapid.limits_status}</p>
        </div>
        <span className="label" style={{ opacity: 0.7 }}>
          Source of record: {rapid.source_of_record}
        </span>
      </div>
    )
  }

  const n = (v) => (typeof v === 'number' ? v.toLocaleString() : '—')
  return (
    <div className="stack stack-3">
      <div className="stack stack-1">
        <span className="label">Requests used this month on this key</span>
        <span className="stat-n tnum" style={{ fontSize: 'var(--fs-xl, 1.5rem)' }}>
          {n(rapid.requests_used)}
          {rapid.quota_limit != null && (
            <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
              {' '}of {n(rapid.quota_limit)}
            </span>
          )}
        </span>
        <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
          {rapid.quota_remaining != null
            ? `${n(rapid.quota_remaining)} remaining. `
            : ''}
          RapidAPI's own quota header, <strong>as of {rapid.as_of || 'the last fetch'}</strong> —
          it moves only when a Reddit fetch runs, so it is not live.
        </span>
      </div>

      <div className="stack stack-1">
        <span className="label">Billed in</span>
        <p className="muted" style={{ margin: 0 }}>
          {rapid.unit} — not dollars (the plan's per-request price isn't
          configured, so a dollar figure would be invented), which is why this is
          a separate tab rather than another line on the chart.
        </p>
      </div>

      <span className="label" style={{ opacity: 0.7 }}>
        Source of record: {rapid.source_of_record}
      </span>
    </div>
  )
}
