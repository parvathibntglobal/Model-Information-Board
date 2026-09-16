import { useCallback, useEffect, useState } from 'react'
import { adminUsage } from '../api'
import { Badge, Notice, Stat } from './ui'
import { IconAlert, IconGauge } from './Icons'

/**
 * OUR cap, OUR spend. Live.
 *
 * OpenRouter bills dollars against a limit we set; RapidAPI bills requests
 * against a limit somebody sells us. Different units, so tabs, not one chart.
 * THE REDDIT AND X ARMS ARE METERED SEPARATELY. This said "one RapidAPI key
 * meters both the X and Reddit harvest paths — the Reddit and X tabs show that
 * one shared request quota", and both tabs were fed the same object. Measured
 * 2026-09-10: they are two RapidAPI subscriptions with two limits (1,000,000
 * and 100,000), each returning 403 on the other's provider. Each tab now reads
 * its own meter, and an arm with no reading says so instead of borrowing the
 * other's number.
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
  // ONE OBJECT PER METER. Both tabs used to read `data.rapidapi`, so the X
  // tab rendered Reddit's reading under an X heading — the arms are separate
  // RapidAPI subscriptions with different limits (measured 2026-09-10:
  // 1,000,000 and 100,000), so a borrowed figure is the wrong meter.
  const rapidReddit = data.rapidapi || {}
  const rapidX = data.rapidapi_x || {}
  const everyone = data.everyone || {}
  const pct = today.fraction_used == null ? null : Math.round(today.fraction_used * 100)
  const onRapid = tab !== 'openrouter'
  const rapid = tab === 'rapidapi_x' ? rapidX : rapidReddit

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
          : <OpenRouterTab
              everyone={everyone}
              today={today}
              byModel={byModel}
              byTokens={data.by_model_tokens || {}}
              unpriced={data.unpriced_models || []}
              basis={data.basis || null}
              ledger={data.ledger || null}
              byStage={data.by_stage || []}
            />}
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
 *
 * `ledger` AND `byStage` ARE READ HERE BECAUSE THE FIGURE ABOVE IS NOT ALWAYS A
 * TOTAL. /admin/usage has always sent three qualifiers on it and this panel read
 * none of them, so the word "total" was unconditional while the backend knew
 * when it was not one. judge/app.py:1805 states the rule this violated:
 *
 *   "`covers_whole_window` is false when the ledger began after today did, in
 *    which case today's total is a floor rather than a total; `unwired_stages`
 *    names any stage that has never recorded at all, which is a wiring failure
 *    and not a quiet day. A page rendering either of those as a plain zero
 *    would be stating the most reassuring of two readings."
 *
 * The producer did its half. This is the consumer's.
 */
function OpenRouterTab({ everyone, today, byModel, byTokens, unpriced, basis, ledger, byStage }) {
  const rows = Object.entries(byModel)
    .map(([model, spent]) => [model, MODEL_SPEND_OVERRIDE[model] ?? spent])
    .sort((a, b) => b[1] - a[1])

  // ── THE CURRENT EXTRACTOR'S SPEND, which the ledger does not have ─────────
  //
  // `by_model_total` is the SHARED ledger since 2026-09-11 (every machine
  // that has recorded), and it holds one row so far: Gemini.
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

  // ── THE THREE QUALIFIERS ON TODAY'S FIGURE ────────────────────────────────
  //
  // Each is sent by /admin/usage and each was unread until 2026-09-14. They are
  // separate conditions and the page must not merge them: a floor because the
  // ledger started late is a different fact from a stage that has never
  // recorded, and both are different from a call whose tokens never arrived.
  const isFloor = today.is_a_floor_not_a_total === true
  const unwired = (ledger?.unwired_stages) || []
  const unmetered = today.unmetered_calls || 0
  // The key total is a provider figure and is whole regardless; only the
  // LEDGER's own figure inherits the floor. So the qualifier attaches to the
  // label only when the ledger's number is the one being shown.
  const showingLedgerToday = !everyone.available
  const totalLabel =
    isFloor && showingLedgerToday
      ? 'recorded on this key today — a floor, not a total'
      : 'total spent on this key'

  return (
    <div className="stack stack-2">
      <div className="grid g3">
        <Stat
          n={everyone.available ? usd(everyone.total_usd) : usd(today.spent_usd)}
          l={totalLabel}
          // The population this figure was drawn from, on hover rather than in
          // prose. It was a sentence under the panel saying "nothing is
          // missing" on every healthy render.
          title={
            basis?.complete && basis.machines?.length
              ? `Ledger totals cover ${basis.machines.length} machine${
                  basis.machines.length === 1 ? '' : 's'}: ${basis.machines.join(', ')}`
              : undefined
          }
        />
        <Stat n={usd(today.remaining_usd)} l="left before today's cap" />
        <Stat
          n={today.calls}
          l={unmetered > 0 ? `calls today — ${unmetered} unmetered` : 'calls today'}
        />
      </div>

      {/* A FLOOR SAYS WHY IT IS ONE. `counting_since` is the whole explanation:
          the ledger began after today did, so calls made before it started are
          missing from the figure rather than absent from the day. */}
      {isFloor && (
        <Notice icon={<IconAlert />}>
          The ledger began recording at{' '}
          <strong>{ledger?.counting_since ? new Date(ledger.counting_since).toLocaleString() : 'an unrecorded time'}</strong>
          , which is after today started. Spend before that is missing from
          today&rsquo;s figure, not absent from the day — so the number above is
          a floor.
        </Notice>
      )}

      {/* A STAGE THAT HAS NEVER RECORDED IS A WIRING FAULT, NOT A QUIET DAY.
          Without this the stage simply reads $0.00, which is the more
          reassuring of the two available readings. */}
      {unwired.length > 0 && (
        <Notice icon={<IconAlert />}>
          <strong>
            {unwired.length === 1 ? 'One stage has' : `${unwired.length} stages have`} never
            recorded a call: {unwired.join(', ')}.
          </strong>{' '}
          That is a stage not wired to the ledger, not a stage that has cost
          nothing — anything it spends is missing from every figure here.
        </Notice>
      )}

      {/* UNMETERED IS NOT UNPRICED, AND THE PAGE MUST SAY WHICH.
          `spend_ledger.py:124-127` keeps them apart deliberately — "Both make a
          dollar total a floor, and for different reasons a reader would want to
          tell apart" — and the panel already shows `unpriced_calls_today` in
          the basis line below. Two dim sentences each saying "n calls were not
          counted" would be true of both and tell a reader neither, so this one
          names the contrast rather than restating the shape:

            unpriced    tokens known, RATE missing        -> publish the rate
            unmetered   the provider reported NO tokens   -> ask the provider

          They want different repairs, which is the test of whether the
          distinction survived into the UI rather than living only in the code. */}
      {unmetered > 0 && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch' }}>
          <strong style={{ color: 'var(--text)' }}>
            {unmetered} call{unmetered === 1 ? '' : 's'} today reported no token usage at all.
          </strong>{' '}
          Not a missing price — a missing measurement. An unpriced call has known
          tokens and no published rate; {unmetered === 1 ? 'this one has' : 'these have'}{' '}
          neither, so {unmetered === 1 ? 'it is' : 'they are'} counted in the call
          figure and absent from the dollar one.
        </span>
      )}
      {!everyone.available && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          Key total across all machines unavailable — the figure above is this machine only.
        </span>
      )}

      {/* WHOSE SPEND THIS IS. A dollar total means nothing without the
          population it covers, and that population is variable: every machine
          that has recorded when the shared table is readable, one laptop when
          it is not. An incomplete total is named a FLOOR rather than shown in
          the same type as a whole one — the same reason report counts on the
          board say so. */}
      {/* THE POPULATION IS NAMED ONLY WHEN IT QUALIFIES SOMETHING.
      
          This printed "Ledger totals cover all 2 machines (ANOOJ, LenovoPB)."
          on every render of a healthy panel - a sentence whose entire content
          is "nothing is missing", which is what a reader already assumes. A
          caveat that is always on screen stops being read, and then the one
          time it says something different it is in the same grey as the
          hundred times it did not.
      
          RULE 7 IS NOT WAIVED, IT IS RELOCATED. The figure still travels with
          its population - the machine list moved to the `title` of the stat
          above, so it is one hover away and nothing is unknowable. What went
          is the prose, not the fact.
      
          The INCOMPLETE branch stays exactly as it was, because that one is a
          real caveat: a floor reported as a total is the error this whole
          panel is built to avoid. */}
      {basis && !basis.complete && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          <strong>This machine only ({basis.this_machine}).</strong> The shared
          ledger could not be read, so every figure here is a floor &mdash; other
          machines&rsquo; spend is missing from it, not absent.
        </span>
      )}
      {basis?.unpriced_calls_today > 0 && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          {basis.unpriced_calls_today} call
          {basis.unpriced_calls_today === 1 ? '' : 's'} today used a model with no
          published rate, so its tokens are counted and its dollars are not.
        </span>
      )}

      {/* WHERE THE ONE CAP WENT. The backend splits every figure by stage
          precisely so a reader can see which of the two consumed the day
          "without the split implying two budgets" (judge/app.py:1800), and
          nothing rendered it. A stage that has never recorded is shown as such
          rather than as $0.00 — those are different claims, and only one of
          them is reassuring. */}
      {byStage.length > 0 && (
        <>
          <span className="label">Where today&rsquo;s spend went — one cap, split by stage</span>
          {byStage.map((s) => (
            <div key={s.stage} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
              <span style={{ fontSize: 'var(--fs-sm)' }}>{s.label || s.stage}</span>
              <span className="stack" style={{ gap: 1, alignItems: 'flex-end' }}>
                <span className="tnum">
                  {s.ever_recorded ? usd(s.spent_usd) : 'never recorded'}
                </span>
                {s.ever_recorded && (
                  <span className="dim" style={{ fontSize: 10 }}>
                    {s.calls} call{s.calls === 1 ? '' : 's'} today
                  </span>
                )}
              </span>
            </div>
          ))}
        </>
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
            <span className="stack" style={{ gap: 1, alignItems: 'flex-end' }}>
              <span className="tnum">
                {(unpriced || []).includes(model) ? 'no published rate' : usd(spent)}
              </span>
              {/* TOKENS ARE THE MEASUREMENT. Shown beside the dollars because a
                  model with no rate records $0.00, and money alone would read
                  as free — the one wrong conclusion available here. */}
              {byTokens?.[model] > 0 && (
                <span className="dim" style={{ fontSize: 10 }}>
                  {byTokens[model].toLocaleString()} tokens
                </span>
              )}
            </span>
          </div>
        ))
      )}

      {(unpriced || []).length > 0 && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch' }}>
          <strong style={{ color: 'var(--text)' }}>
            {(unpriced || []).length} model{(unpriced || []).length === 1 ? '' : 's'} recorded
            tokens with no published rate
          </strong>{' '}
          — {(unpriced || []).join(', ')}. Their tokens are measured; the price is not held in{' '}
          <span className="mono">judge/extract/budget.py</span>, so no dollar figure is computed
          for them rather than one being computed at another model's rate.
        </span>
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
 * RapidAPI spend for ONE arm — Reddit and X are metered separately.
 *
 * THE SPEND ON THIS KEY IS REQUESTS, NOT DOLLARS, and that is not a gap in the
 * panel: the plan's per-request price is in nobody's config, so a dollar figure
 * here would be one this code invented (rule 3). Requests used IS the spend —
 * `limit − remaining`, both the gateway's own header values.
 *
 * The number is RapidAPI's own reading cached with its date; it moves only when
 * a metered fetch runs, never live.
 *
 * ⚠ THIS DOCSTRING SAID "one shared key metering the X and Reddit harvest
 *   paths" and that `read_on` exists "because one key cannot be split by
 *   endpoint". The module docstring above was corrected in #243 and this one
 *   was missed, which is the third copy of the same false premise in this
 *   repository. Measured 2026-09-10: two RapidAPI subscriptions, limits of
 *   1,000,000 and 100,000, each returning 403 on the other's provider.
 *   `read_on` identifies WHICH METER a reading belongs to.
 */
function RapidApiTab({ rapid, which }) {
  const n = (v) => (typeof v === 'number' ? v.toLocaleString() : '—')
  if (!rapid.instrumented) {
    // AN UNATTRIBUTED READING IS RENDERED, NOT JUST CARRIED. `_rapidapi_quota`
    // publishes `unattributed_reading` when the store holds a record written
    // before `read_on` existed: it belongs to no arm, so it cannot be shown AS
    // this arm's figure - and saying only "no reading yet" hides a measurement
    // we actually hold. #243 added the field and never displayed it, so the
    // payload told the truth and the page understated it.
    const orphan = rapid.unattributed_reading
    return (
      <div className="stack stack-2">
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>
            {orphan ? `No reading for the ${which} arm.` : 'No reading yet.'}
          </strong>{' '}
          {rapid.headline}
        </Notice>
        {orphan && (
          <div className="stack stack-1">
            <span className="label">
              One older reading exists and cannot be attributed to either arm
            </span>
            {/* NOT a <Stat>. A Stat is how this panel renders a figure it is
                standing behind, and standing behind this one is exactly what
                cannot be done - it is shown so it is not lost, captioned so it
                is not mistaken for this tab's quota. */}
            <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
              <strong style={{ color: 'var(--text)' }}>
                {n(orphan.quota_remaining)} requests remaining
              </strong>
              {typeof orphan.quota_limit === 'number'
                ? ` of ${n(orphan.quota_limit)}`
                : ', against a limit this reading did not carry'}
              , read {orphan.as_of || 'at an unrecorded time'}.
            </span>
            <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
              <strong style={{ color: 'var(--text)' }}>Why it is not shown above:</strong>{' '}
              {orphan.why_not_shown}
            </span>
            <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
              It resolves itself: the next metered fetch on either arm records a
              reading that names its own path, and this one stops being the most
              recent thing we know. <strong style={{ color: 'var(--text)' }}>Do not
              delete <code>var/rapidapi-quota.json</code> to clear this</strong> — it
              is a real header reading, and deleting it discards a measurement to
              make the page look tidy.
            </span>
          </div>
        )}
        <span className="label" style={{ opacity: 0.7 }}>Source: {rapid.source_of_record}</span>
      </div>
    )
  }
  const used = rapid.requests_used
  const limit = rapid.quota_limit
  const remaining = rapid.quota_remaining
  const knownLimit = typeof limit === 'number' && limit > 0
  const share = knownLimit && typeof used === 'number' ? (used / limit) * 100 : null
  // Whose fetch took the reading. `null` is a record written before the field
  // existed — unrecorded, which is not the same as "this tab's path".
  const readOn = rapid.read_on || null
  const readBy = rapid.read_by || null
  const mine = readOn === (which === 'X' ? 'x' : 'reddit')

  return (
    <div className="stack stack-2">
      <span className="label">
        Spend on this key — {which} path, billed in requests
      </span>
      {/* WHICHEVER HALF WE ACTUALLY HAVE LEADS. With both, spent-of-limit is
          the natural frame. With only `remaining` — which is the current
          reading — a "spent" figure cannot be derived at all, so showing it as
          a dash three times would bury the one measured number on the tab. */}
      {knownLimit ? (
        <div className="grid g3">
          <Stat n={n(used)} l="requests spent" />
          <Stat n={share == null ? '—' : `${share.toFixed(2)}%`} l="of the quota" />
          <Stat n={n(remaining)} l="left" />
        </div>
      ) : (
        <div className="grid g2">
          <Stat n={n(remaining)} l="requests remaining — measured" />
          <Stat n="not established" l="monthly limit" />
        </div>
      )}

      {!knownLimit && rapid.limit_unknown_why && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
          <strong style={{ color: 'var(--text)' }}>
            The limit is not known, so neither is the percentage.
          </strong>{' '}
          {rapid.limit_unknown_why}
        </span>
      )}

      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        <strong style={{ color: 'var(--text)' }}>No dollar amount, deliberately.</strong>{' '}
        RapidAPI sells this as a request quota and the per-request price is not in
        our config, so a dollar figure would be invented rather than measured.{' '}
        {knownLimit
          ? `${n(used)} of ${n(limit)} requests is the spend.`
          : `${n(remaining)} requests remaining is what the gateway last reported.`}
      </span>
      {/* ⚠ THE COUNTER BELONGS TO A SUBSCRIPTION, NOT TO A MACHINE, AND THIS
          CAPTION USED TO LEAD WITH THE MACHINE.

          It opened "Showing the shared table reading, taken on ANOOJ…", which
          reads as though a laptop owned the quota. It does not. The board is
          hosted: anybody signed in can start a fetch, and it draws down one
          RapidAPI subscription whoever clicked. Parvathi, 2026-09-16 — "anybody
          logged in can do the fetch run so rely on api key usage and not
          machines".

          So the subject is the meter and its subscription; the machine is
          demoted to what it always was — who happened to observe the number.
          `key_fingerprint` is sha256(key)[:12], never the key, and it is the
          only thing on this row that identifies the counter. */}
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        This is one{' '}
        <strong style={{ color: 'var(--text)' }}>
          shared {readOn === 'x' ? 'X' : 'Reddit'} subscription
        </strong>
        {rapid.key_fingerprint ? (
          <> (<span className="mono">{rapid.key_fingerprint}</span>)</>
        ) : null}
        , drawn down by everyone who runs a fetch — the board is hosted, so the
        machine below is who <em>read</em> the number, not who spent it.
      </span>

      {/* A DISAGREEMENT IS SHOWN, NOT RESOLVED. Two readings of two different
          subscriptions are not a stale-versus-fresh pair, and picking the newer
          would assert that one of two real counters is the real one. */}
      {rapid.subscriptions_differ && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)', color: 'var(--warn)' }}>
          <strong>These two readings are of different subscriptions.</strong>{' '}
          Their key fingerprints do not match, so the figure above is one
          account's and the one below is another's. They are not a stale reading
          beside a fresh one and must not be read as a single counter — check
          which <span className="mono">RAPIDAPI_KEY</span> each host is using.
        </span>
      )}

      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Reading taken from the{' '}
        <strong style={{ color: 'var(--text)' }}>
          {rapid.reading_source === 'shared table'
            ? 'shared table'
            : "this machine's cache"}
        </strong>
        , observed by {rapid.reading_machine || 'an unrecorded machine'} at{' '}
        {rapid.as_of || 'an unrecorded time'}.
        {rapid.also_held ? (
          <>
            {' '}The other store holds {n(rapid.also_held.quota_remaining)}{' '}
            remaining, observed by{' '}
            {rapid.also_held.machine || 'an unrecorded machine'} at{' '}
            {rapid.also_held.as_of || 'an unrecorded time'}
            {rapid.subscriptions_differ
              ? ' — a different subscription, see above.'
              : ' — older, and shown because a stale cached reading beside a'
                + ' fresher shared one is the normal case on one shared'
                + ' counter, not a disagreement to resolve.'}
          </>
        ) : rapid.reading_source === 'shared table' ? (
          <> This machine has no cached reading of its own for this meter.</>
        ) : (
          <> Nothing has recorded this meter to the shared table yet.</>
        )}
      </span>
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        As of {rapid.as_of || 'the last fetch'}
        {readBy ? ` (recorded by a ${readBy})` : ''}, read on{' '}
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
          : `⚠ This reading was taken on a ${readOn ? (readOn === 'x' ? 'X' : 'Reddit') : 'different'} fetch, and the two arms are metered separately — so it is NOT this tab's quota. Read it as the other arm's figure, filed here only because no ${which} reading has been recorded.`}
      </span>
      <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
        {which === 'Reddit' ? (
          <>
            And the window is <strong>23.9 days, not a month</strong> (measured
            2026-08-18), so anything costed as a share of a month against this
            quota is a third too low.{' '}
          </>
        ) : (
          <>
            The window is <strong>not a month</strong> either: this arm's
            <code> x-ratelimit-requests-reset</code> read ~19 days on 2026-09-10.
            The 23.9-day figure belongs to the Reddit arm and is not this one's.{' '}
          </>
        )}
        {knownLimit
          ? `The billed tier remains unverified: the gateway header says ${n(limit)} and the plan page says 500,000. Only the RapidAPI subscription page settles it.`
          : 'The billed tier has never been verified either — the plan page said 500,000, an older header said 1,000,000, and this reading fits neither. One look at the RapidAPI subscription page settles it, and no request can.'}
      </span>
    </div>
  )
}
