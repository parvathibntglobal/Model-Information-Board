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
  const rapid = data.rapidapi || {}
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
            ['openrouter', 'OpenRouter — Gemini 2.5 Flash'],
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
        {today.is_a_floor_not_a_total && (
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
 * RapidAPI — requests, not dollars, and not live.
 *
 * The quota arrives in `x-ratelimit-requests-*` response headers read in
 * `collect/adapters/reddit.py`, which is the other lane, and nothing persists
 * them. So there is no row for this page to read.
 *
 * The last dated reading is deliberately NOT copied here. It lives in
 * `contract/sources.yaml` beside the date it was read on; on a live dashboard
 * the same number would read as current, which is the one thing this product
 * exists not to do. An empty tab that says why beats a stale number that
 * looks fine.
 */
function RapidApiTab({ rapid }) {
  return (
    <div className="stack stack-3">
      <Notice icon={<IconAlert />}>
        <strong style={{ color: 'var(--text)' }}>Not instrumented here.</strong>{' '}
        {rapid.headline}
      </Notice>

      <div className="stack stack-1">
        <span className="label">Billing window</span>
        <p className="muted" style={{ margin: 0 }}>{rapid.window}</p>
      </div>

      {/* THE OPEN QUESTIONS ARE THE CONTENT. Both change what a usage bar would
          mean, so they are the tab rather than a footnote under one. */}
      <div className="stack stack-2">
        <span className="label">Open questions — both change what a usage bar would mean</span>
        {(rapid.open_questions || []).map((q) => (
          <div key={q.question} className="stack stack-1">
            <strong style={{ color: 'var(--text)' }}>{q.question}</strong>
            <span className="muted">{q.detail}</span>
          </div>
        ))}
      </div>

      <div className="stack stack-1">
        <span className="label">What would make this live</span>
        <p className="muted" style={{ margin: 0 }}>{rapid.what_would_make_it_live}</p>
      </div>

      <span className="label" style={{ opacity: 0.7 }}>
        Source of record: {rapid.source_of_record}
      </span>
    </div>
  )
}
