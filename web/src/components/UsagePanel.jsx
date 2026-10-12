import { useCallback, useEffect, useState } from 'react'
import { adminUsage } from '../api'
import { prettyModel } from '../modelNames'
import { Badge, Notice, Stat } from './ui'
import { IconAlert, IconHeart } from './Icons'
import BilledCostPanel from './BilledCostPanel'

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

// ⚠ LONGER THAN THE REQUEST TAKES, WHICH 15s WAS NOT. Measured 2026-09-17:
// `/admin/usage` answers in about 10s - it reads the whole spend ledger twice,
// each read opening its own connection to a remote database. A 15s poll against
// a 10s request leaves the panel loading two thirds of the time, which is most
// of what "the admin page is laggy" was.
//
// The number to fix is the 10s, not this; until then a poll that overlaps its
// own previous request is just a slower page and a busier database.
const POLL_MS = 45000
const usd = (n, dp = 4) => (n == null ? '—' : `$${Number(n).toFixed(dp)}`)

// MOVED TO src/modelNames.js, because Settings names the same model and was
// printing the raw id - so one page called the extractor two different things.

// ── A CLOSED FIGURE, NOT A LIVE ONE ───────────────────────────────────────────
//
// Gemini 2.5 Flash stopped being the extractor on 2026-09-01, so its total is
// history and cannot move. The ledger holds only $0.0975 of it, because E5 was
// not writing to the shared ledger for most of the period Gemini ran; the real
// figure is the key total on the day of the switch, when Gemini was the only
// thing spending from it.
//
// ⚠ IT IS A MEASUREMENT WITH A DATE, AND THE PAGE MUST SAY SO (rule 11). It
//   read as though the ledger had produced it, which is the one thing it did
//   not: a constant typed into a component, indistinguishable on screen from
//   the live row beside it. `SPEND_BEFORE_THE_LEDGER` is named for what it is,
//   the row is marked, and the date travels with the number.
//
// ⚠ AND IT IS A CEILING FOR GEMINI, NOT A TOTAL. 207 Gemini calls are in the
//   ledger AFTER the switch, running to 2026-09-18 — machines with
//   EXTRACTOR_MODEL still set to Gemini, which `judge/extract/client.py`
//   describes as having happened before. Those are inside the key total and
//   are not inside this figure.
const SPEND_BEFORE_THE_LEDGER = {
  'google/gemini-2.5-flash': { usd: 2.478, asof: '2026-09-01' },
}

// ── STAGES THAT READ ZERO BECAUSE NOTHING CALLS THEM YET ─────────────────────
//
// A stage in here is stated as "(not built yet)". A stage NOT in here that has
// never recorded keeps the warning, because the two look identical in the
// ledger and only one of them is harmless.
//
// ⚠ MEMBERSHIP IS A CLAIM ABOUT THE FRONTEND, NOT THE BACKEND, and it is the
//   claim that rots. `ask` is here because no component calls `askUnderstand`
//   and there is no /ask route in the app — the Ask box is a plan, not a
//   surface. Its backend half is wired and correct: `/ask/understand` is the
//   only route in that flow that calls a model, and it records STAGE_ASK ahead
//   of the budget branch.
//
//   `tests/test_the_unwired_stage_notice_cannot_rot.py` fails the day a caller
//   appears, which is the day "(not built yet)" stops being true and starts being
//   the reassuring reading of a real fault.
const NOT_BUILT_YET = new Set(['ask'])

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
        <span className="eyebrow"><IconHeart width={14} height={14} /> API usage — our cap</span>
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
              blogs={data.blogs}
              monthly={data.monthly || null}
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
function OpenRouterTab({ everyone, today, byModel, byTokens, unpriced, basis, ledger, byStage, blogs, monthly }) {
  const rows = Object.entries(byModel)
    .map(([model, spent]) => {
      const closed = SPEND_BEFORE_THE_LEDGER[model]
      return closed
        ? [model, closed.usd, closed.asof]   // third slot: the date, rendered
        : [model, spent, null]
    })
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
  // BLOG SPEND IS LEDGER-KNOWN TOO since 2026-10-07 (stage 'blog'), reported
  // under `blogs` rather than in these rows - so it is added here, or every blog
  // dollar would fall into the remainder below and read as unattributed
  // extractor spend.
  const ledgerKnown = rows.reduce((sum, [, spent]) => sum + spent, 0) + (blogs?.total_usd || 0)
  const remainder = everyone.available ? (everyone.total_usd ?? 0) - ledgerKnown : null
  const todayOnKey = everyone.today_usd ?? null
  const CENT = 0.005 // half a cent: below this the two figures are the same number
  const corroborated =
    remainder != null && todayOnKey != null && Math.abs(remainder - todayOnKey) < CENT
  // Only shown when there IS unledgered spend. A zero row would imply we had
  // checked and DeepSeek had cost nothing, which is a different claim.
  const currentSpend = remainder != null && remainder > 0.00005 ? remainder : null

  // ⚠ THE LEDGER CAN EXCEED THE KEY, AND SAYING NOTHING IS THE WRONG ANSWER.
  //   `remainder` goes NEGATIVE when the rows below add up to more than the
  //   provider has ever charged, and every use of it above tests `> 0` — so
  //   the page fell silent on the one arithmetic it is here to check.
  //
  //   Measured 2026-09-28: the rows read $9.5690 against a key that had spent
  //   $4.1570. Two causes, both real and neither visible from this component:
  //   every extraction call was written to the ledger twice (fixed — one
  //   writer, `judge/extract/client.py`), and every dollar in the ledger is
  //   tokens x a constant, with the two constants for DeepSeek disagreeing by
  //   2.11x (#381, open).
  //
  //   So this is a LIVE CHECK, not a note about a past defect: the moment the
  //   rows outrun the key again, the page says so instead of quietly dropping
  //   the difference.
  const overstated = remainder != null && remainder < -CENT ? -remainder : null
  const alreadyListed = rows.some(([m]) => m === CURRENT_EXTRACTOR)

  // ── THE THREE QUALIFIERS ON TODAY'S FIGURE ────────────────────────────────
  //
  // Each is sent by /admin/usage and each was unread until 2026-09-14. They are
  // separate conditions and the page must not merge them: a floor because the
  // ledger started late is a different fact from a stage that has never
  // recorded, and both are different from a call whose tokens never arrived.
  const isFloor = today.is_a_floor_not_a_total === true
  // A stage in NOT_BUILT_YET is not listed at all now (the Ask box was
  // deprioritised 2026-10-06); any OTHER unwired stage still warns.
  const unwired = ((ledger?.unwired_stages) || []).filter((s) => !NOT_BUILT_YET.has(s))
  const unmetered = today.unmetered_calls || 0
  // The key total is a provider figure and is whole regardless; only the
  // LEDGER's own figure inherits the floor. So the qualifier attaches to the
  // label only when the ledger's number is the one being shown.
  const showingLedgerToday = !everyone.available
  const totalLabel =
    isFloor && showingLedgerToday
      ? 'recorded on this key today — a floor, not a total'
      : 'total spent on this key'

  // ONE ROW SHAPE for every list below: a name on the left, the figure and its
  // small caption on the right.
  const Line = ({ name, value, caption }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline',
      padding: '8px 0', borderTop: '1px solid var(--border-soft)' }}>
      <span>{name}</span>
      <span className="stack" style={{ gap: 1, alignItems: 'flex-end' }}>
        <span className="tnum">{value}</span>
        {caption && <span className="dim" style={{ fontSize: 10 }}>{caption}</span>}
      </span>
    </div>
  )
  const Block = ({ title, children }) => (
    <div className="stack" style={{ gap: 0 }}>
      <span className="label" style={{ marginBottom: 6 }}>{title}</span>
      {children}
    </div>
  )

  return (
    <div className="stack stack-3">
      {/* 1 · THE THREE HEADLINE FIGURES */}
      <div className="grid g3">
        <Stat
          n={everyone.available ? usd(everyone.total_usd) : usd(today.spent_usd)}
          l={totalLabel}
          title={
            basis?.complete && basis.machine_count
              ? `Ledger totals cover ${basis.machine_count} host${basis.machine_count === 1 ? '' : 's'}`
              : undefined
          }
        />
        <Stat n={usd(today.remaining_usd)} l="left before today's cap" />
        <Stat n={today.calls} l={unmetered > 0 ? `calls today — ${unmetered} unmetered` : 'calls today'} />
      </div>

      {/* 2 · WARNINGS, only when one applies. Each is a real caveat on the
          figures above (a floor, an unwired stage, rows above the key total),
          so they stay; the always-on explanatory prose is gone. */}
      {isFloor && (
        <Notice icon={<IconAlert />}>
          The ledger began recording at{' '}
          <strong>{ledger?.counting_since ? new Date(ledger.counting_since).toLocaleString() : 'an unrecorded time'}</strong>,
          after today started, so today&rsquo;s figure is a floor.
        </Notice>
      )}
      {unwired.length > 0 && (
        <Notice icon={<IconAlert />}>
          <strong>
            {unwired.length === 1 ? 'One stage has' : `${unwired.length} stages have`} never
            recorded a call: {unwired.join(', ')}.
          </strong>
          {unwired.some((s) => !NOT_BUILT_YET.has(s)) && (
            <>
              {' '}Either nothing has reached it, or it is not wired to the
              ledger — the second would mean anything it spends is missing from every number here.
            </>
          )}
        </Notice>
      )}
      {overstated != null && (
        <Notice icon={<IconAlert />}>
          <strong style={{ color: 'var(--text)' }}>The rows below exceed the key total by {usd(overstated)}.</strong>{' '}
          They are tokens × a held rate, which overstates cached calls (#381). Trust the total above;
          read the rows as <strong>which model, not how much</strong>.
        </Notice>
      )}
      {(!everyone.available || (basis && !basis.complete)) && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          <strong>This machine only</strong> — the shared ledger could not be read, so these figures are floors.
        </span>
      )}
      {/* #393: rows this machine recorded that never reached the shared table.
          Said only when non-zero (a permanent "0 unmirrored" is furniture). Not
          a floor HERE - this page reads the file too - but every other
          machine's cap is short by exactly these rows. */}
      {basis?.unmirrored_rows > 0 && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          <strong>
            {basis.unmirrored_rows} of {basis.local_rows} call
            {basis.local_rows === 1 ? '' : 's'} recorded on this machine
          </strong>{' '}
          never reached the shared ledger, so other machines&rsquo; daily cap cannot
          see that spend. <code>python scripts/backfill_telemetry.py --apply</code>{' '}
          sends them.
        </span>
      )}

      {/* 3 · TODAY, BY STAGE: the capped stage and the uncapped blog drafts together */}
      <Block title="Today (UTC)">
        {byStage.filter((s) => !NOT_BUILT_YET.has(s.stage)).map((s) => (
          <Line key={s.stage} name={s.label || s.stage}
                value={s.ever_recorded ? usd(s.spent_usd) : 'never recorded'}
                caption={s.ever_recorded ? `${s.calls} call${s.calls === 1 ? '' : 's'} · inside the cap` : null} />
        ))}
        {blogs && (
          <Line name="Blog drafts" value={usd(blogs.spent_today_usd)}
                caption={`${blogs.calls_today} call${blogs.calls_today === 1 ? '' : 's'} · outside the cap${blogs.unpriced_today ? ' · a floor' : ''}`} />
        )}
        {unmetered > 0 && (
          <span className="dim" style={{ fontSize: 'var(--fs-xs)', paddingTop: 6 }}>
            {unmetered} call{unmetered === 1 ? '' : 's'} today reported no token usage, so {unmetered === 1 ? 'it is' : 'they are'} not in the dollar figure.
          </span>
        )}
      </Block>

      {/* 4 · ALL-TIME, BY MODEL: extraction models, then the blog generator */}
      <Block title="All-time spend by model">
        {rows.length === 0 && !(blogs?.models || []).length ? (
          <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>No model calls recorded yet.</span>
        ) : rows.map(([model, spent, asof]) => (
          <Line key={model}
                name={String(model ?? '').trim() === ''
                  ? <span className="dim" style={{ fontStyle: 'italic' }}>{prettyModel(model)}</span>
                  : <><strong style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(model)}</strong>{' '}
                      <Badge tone="mute">extraction</Badge>
                      {model === CURRENT_EXTRACTOR && <> <Badge tone="info">current</Badge></>}
                      {asof && <> <Badge tone="mute">closed {asof}</Badge></>}</>}
                value={(unpriced || []).includes(model) ? 'no published rate' : usd(spent)}
                caption={byTokens?.[model] > 0 ? `${byTokens[model].toLocaleString()} tokens` : null} />
        ))}
        {currentSpend != null && !alreadyListed && (
          <Line name={<><strong style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(CURRENT_EXTRACTOR)}</strong>{' '}
                  <Badge tone={corroborated ? 'mute' : 'warn'}>{corroborated ? 'from the provider' : 'unattributed'}</Badge></>}
                value={usd(currentSpend)} />
        )}
        {(blogs?.models || []).map((m) => (
          <Line key={`blog-${m.model}`}
                name={<><strong style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(m.model)}</strong>{' '}
                  <Badge tone="mute">blog drafts</Badge>
                  {m.model === blogs.model && <> <Badge tone="info">current</Badge></>}</>}
                value={usd(m.spent_usd)}
                caption={`${m.calls} call${m.calls === 1 ? '' : 's'}${m.unpriced_calls ? ' · a floor' : ''}`} />
        ))}
        {blogs && !(blogs.models || []).length && blogs.model && (
          <Line name={<><strong style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(blogs.model)}</strong>{' '}
                  <Badge tone="mute">blog drafts</Badge></>}
                value={<span className="dim">no recorded calls</span>} />
        )}
        {(unpriced || []).length > 0 && (
          <span className="dim" style={{ fontSize: 'var(--fs-xs)', paddingTop: 6 }}>
            No published rate for {(unpriced || []).join(', ')}: tokens counted, dollars not.
          </span>
        )}
      </Block>

      {/* 5 · BY MONTH */}
      <MonthlyLedger monthly={monthly} />

      {/* 6 · BILLED PER RUN (added 2026-10-12) */}
      <BilledCostPanel />
    </div>
  )
}

const STAGE_SHORT = { extract: 'Extraction', ask: 'Ask box', blog: 'Blog drafts' }

/**
 * SPEND BY MONTH — every model call in the ledger, by calendar month (UTC),
 * stage and model, GPT-6 Luna's blog drafts included (`monthly` in
 * /admin/usage, judge/spend_ledger.py `monthly`).
 *
 * TWO KINDS OF DOLLAR, SAID ON THE PAGE (rule 7): extraction and Ask rows are
 * tokens x a rate held in `judge/extract/budget.py` (see the note above on how
 * far that rate is off), blog rows are OpenRouter's reported cost per call. A
 * month before a stage's first recorded call has no row for it because nothing
 * was recording, not because nothing was spent — so each stage's start is shown.
 */
function MonthlyLedger({ monthly }) {
  if (!monthly) return null
  const rows = monthly.rows || []
  const since = Object.entries(monthly.counting_since || {})
  return (
    <>
      <span className="label">By month — every model call in the ledger (UTC months)</span>
      {monthly.complete === false && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          The shared ledger could not be read, so these are this machine&apos;s calls only — every row is a floor.
        </span>
      )}
      {rows.length === 0 ? (
        <span className="dim" style={{ fontSize: 'var(--fs-sm)' }}>No model calls recorded yet.</span>
      ) : (
        <div className="tablewrap"><table>
          <thead>
            <tr><th>Month</th><th>Stage</th><th>Model</th><th>Calls</th><th>Tokens in / out</th><th>Spent</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.month}|${r.stage}|${r.model}`}>
                <td className="mono">{r.month}</td>
                <td>
                  {STAGE_SHORT[r.stage] || r.stage}
                  {r.stage === 'blog' && <> <Badge tone="mute">outside cap</Badge></>}
                </td>
                <td>
                  <strong style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(r.model)}</strong>
                  <span className="mono" style={{ display: 'block', fontSize: 10, color: 'var(--text-3)' }}>{r.model}</span>
                </td>
                <td className="tnum">{r.calls.toLocaleString()}</td>
                <td className="tnum">{r.tokens_in.toLocaleString()} / {r.tokens_out.toLocaleString()}</td>
                <td className="tnum">
                  {usd(r.usd)}
                  {(r.unpriced_calls > 0 || r.unmetered_calls > 0) && (
                    <span className="dim" style={{ display: 'block', fontSize: 10 }}>
                      a floor: {[r.unpriced_calls ? `${r.unpriced_calls} unpriced` : null,
                        r.unmetered_calls ? `${r.unmetered_calls} with no tokens reported` : null]
                        .filter(Boolean).join(', ')}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Recording since {since.length
          ? since.map(([st, at]) => `${STAGE_SHORT[st] || st} ${new Date(at).toLocaleDateString()}`).join(' · ')
          : 'nothing recorded'}.
      </span>
    </>
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
/** A count, or an em dash. — rather than 0, because rule 6: a reading nobody
 *  took and a reading of zero are different facts.
 *
 *  ⚠ HOISTED, AND RENAMED FROM `n`. It lived inside `RapidApiTab`, and
 *    `QuotaSeries` — a sibling, not a child — called `n(s.consumed)` anyway.
 *    That threw `ReferenceError` and React unmounted the whole page: a dark
 *    empty screen with nothing to read.
 *
 *    It survived review because it is UNREACHABLE until an arm has two quota
 *    readings. Reddit had none, so its tab returned early and rendered fine;
 *    X reached its second reading and the tab stopped working. Not an X bug —
 *    Reddit was one reading away from the same crash.
 *
 *    `count`, not `n`, because `<Stat n={...}>` takes a prop of that name, so
 *    `n={n(x)}` reads as correct at a glance. Two things one letter apart in
 *    one expression is how this got written in the first place.
 */
const count = (v) => (typeof v === 'number' ? v.toLocaleString() : '—')

function RapidApiTab({ rapid, which }) {
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
                {count(orphan.quota_remaining)} requests remaining
              </strong>
              {typeof orphan.quota_limit === 'number'
                ? ` of ${count(orphan.quota_limit)}`
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
          <Stat n={count(used)} l="requests spent" />
          <Stat n={share == null ? '—' : `${share.toFixed(2)}%`} l="of the quota" />
          <Stat n={count(remaining)} l="left" />
        </div>
      ) : (
        <div className="grid g2">
          <Stat n={count(remaining)} l="requests remaining — measured" />
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
          ? `${count(used)} of ${count(limit)} requests is the spend.`
          : `${count(remaining)} requests remaining is what the gateway last reported.`}
      </span>
      {/* ⚠ THE COUNTER BELONGS TO A SUBSCRIPTION, NOT TO A MACHINE, AND THIS
          CAPTION USED TO LEAD WITH THE MACHINE.

          It opened "Showing the shared table reading, taken on machine-A…", which
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

      {/* ── THE WINDOW. BOTH ENDS DATED, OR VISIBLY NOT. ──────────────────
          Replaces a sentence that said "23.9 days, not a month (measured
          2026-08-18)". That figure was never a window LENGTH — it was TIME
          REMAINING on one reading, presented as a period, and it made every
          costing on this page a third wrong in the direction nobody checks.

          Reddit's period is measured at exactly 30.000 days and both boundaries
          are dated. X's is NOT, and the bar says so rather than borrowing
          Reddit's: same gateway, different upstream. */}
      <WindowBar w={rapid.window} which={which} />

      {/* ── THE SERIES. ABSENT BY CONSTRUCTION IS NOT ABSENT BECAUSE NOTHING
             HAPPENED, and this is the whole reason for writing it. ─────────── */}
      <QuotaSeries s={rapid.series} which={which} />

      {/* ── PROVENANCE, DEMOTED TO ONE LINE. ──────────────────────────────
          This was three overlapping sentences: "Reading taken from the shared
          table, read by <host> at <time>", then "As of <time> (recorded by a
          harvest), read on the Reddit fetch", then "This tab's own path took
          the reading." The first two say the same thing twice and the third is
          the second's own subject restated. One line, once. */}
      <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
        Read {rapid.as_of || 'at an unrecorded time'}
        {readBy ? ` during a ${readBy}` : ''}, from{' '}
        {rapid.reading_source === 'shared table' ? 'the shared table' : "this machine's cache"}
        , on {rapid.reading_host || 'an unrecorded host'}
        {rapid.key_fingerprint ? (
          <> · key <span className="mono">{rapid.key_fingerprint}</span></>
        ) : null}
        .{' '}
        <Staleness asOf={rapid.as_of} />
        {!mine && (
          <>
            {' '}⚠ Taken on {readOn ? (readOn === 'x' ? 'an X' : 'a Reddit') : 'a different'}{' '}
            fetch, and the arms are metered separately — so this is NOT this
            tab's quota.
          </>
        )}
      </span>

      {/* THE READING THIS ONE BEAT — a footnote, which is what its own API
          comment always said it was for: "here to show the other side has also
          fetched, not as a second figure to compare". It led the caption until
          now, which presented one counter as two and explained a gap that is
          usually not there. */}
      {rapid.also_held && !rapid.subscriptions_differ && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs))', opacity: 0.75 }}
              title={`${count(rapid.also_held.quota_remaining)} remaining, read by ${rapid.also_held.host || 'an unrecorded host'} at ${rapid.also_held.as_of || 'an unrecorded time'}`}>
          An older reading of this same meter is also held — hover for it. It is
          not a second figure: the counter only falls, so the newest reading is
          the truest one.
        </span>
      )}

      <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
        {/* ⚠ 500,000 IS THE REDDIT PLAN'S FIGURE AND WAS BEING ASSERTED OF BOTH
            ARMS. It comes from docs/measurements/reddit-rate-and-quota.md, which
            is about the Reddit subscription; nobody has read X's plan page. The
            two arms are separate subscriptions — that is the premise this panel
            got wrong once already, when one key was believed to meter both — so
            the discrepancy is stated for the arm it was measured on and NOT for
            the other (rule 7: a figure travels with the population it came
            from). */}
        {which === 'Reddit' ? (
          knownLimit
            ? `The billed tier remains unverified: the gateway header says ${count(limit)} and the plan page says 500,000. Only the RapidAPI subscription page settles it.`
            : 'The billed tier has never been verified either — the plan page said 500,000, an older header said 1,000,000, and this reading fits neither. One look at the RapidAPI subscription page settles it, and no request can.'
        ) : (
          knownLimit
            ? `The billed tier is unverified for this arm: the gateway header says ${count(limit)}, and nobody has read X's plan page. Reddit's 500,000/1,000,000 discrepancy is NOT quoted here — that figure was measured on the Reddit subscription and these are separate accounts. Only the RapidAPI subscription page settles it.`
            : "The billed tier is unverified for this arm, and no plan figure has ever been read for it. Reddit's discrepancy is not this arm's — they are separate subscriptions."
        )}
      </span>
    </div>
  )
}

/** How old the reading is, and WHY that matters — not just the age.
 *
 * A number of hours means nothing on its own. What a reader acts on is that
 * this counter is shared and moves only when a fetch runs: a fetch on another
 * machine draws it down and nothing here learns about it until someone reads
 * the header again. So the caution names the mechanism, not the duration.
 *
 * Thresholds are judgement, not measurement, and are deliberately coarse.
 */
function Staleness({ asOf }) {
  if (!asOf) return null
  const t = Date.parse(asOf)
  if (Number.isNaN(t)) return null
  const hours = (Date.now() - t) / 3_600_000
  if (hours < 1) return null
  if (hours < 3) {
    return (
      <span>
        It moves only when a fetch runs, so it is current as of that time rather
        than now.
      </span>
    )
  }
  const age = hours < 24
    ? `${Math.round(hours)} hours old`
    : `${Math.round(hours / 24)} days old`
  return (
    <strong style={{ color: hours >= 24 ? 'var(--warn)' : 'var(--text)' }}>
      This reading is {age} and may be stale — the counter is shared, it moves
      only when a fetch runs, and a fetch on another machine moves it invisibly
      to this page.
    </strong>
  )
}

/** The window, with both ends dated — or one end visibly undated.
 *
 * ⚠ THE ASYMMETRY BETWEEN THE ARMS IS THE POINT AND MUST SURVIVE REDESIGN.
 *   Reddit's period is MEASURED at 30.000 days, so both boundaries are
 *   arithmetic. X has ONE dated boundary and no period, so its left end is
 *   unknown and is drawn as unknown. Filling it in with Reddit's 30 days would
 *   be inventing a measurement — same gateway, different upstream (rule 6).
 */
function WindowBar({ w, which }) {
  if (!w) return null
  const fmt = (iso) => {
    if (!iso) return null
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return null
    return d.toISOString().replace('T', ' ').slice(0, 16) + ' UTC'
  }
  const prev = fmt(w.previous_boundary)
  const next = fmt(w.next_boundary)
  // Where we are in the window — only computable with both ends.
  let pct = null, elapsedDays = null, leftDays = null
  if (w.previous_boundary && w.next_boundary) {
    const a = Date.parse(w.previous_boundary), b = Date.parse(w.next_boundary)
    const now = Date.now()
    if (b > a) {
      pct = Math.min(100, Math.max(0, ((now - a) / (b - a)) * 100))
      elapsedDays = (now - a) / 86_400_000
      leftDays = (b - now) / 86_400_000
    }
  }
  return (
    <div className="stack stack-1">
      <span className="label">
        {w.period_measured
          ? `Window — ${w.period_days.toFixed(3)} days, measured`
          : 'Window — length not measured'}
      </span>
      {pct != null ? (
        <>
          <div style={{
            position: 'relative', height: 6, borderRadius: 3,
            background: 'var(--surface-2, rgba(128,128,128,0.2))',
          }}>
            <div style={{
              position: 'absolute', left: 0, top: 0, bottom: 0,
              width: `${pct}%`, borderRadius: 3, background: 'var(--accent, #6b8afd)',
            }} />
          </div>
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            {prev} → {next} · {elapsedDays.toFixed(1)}d in, {leftDays.toFixed(1)}d left
          </span>
        </>
      ) : (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
          {next ? (
            <>
              Next boundary <strong style={{ color: 'var(--text)' }}>{next}</strong>.{' '}
              <strong>The start of this window is not known</strong> — only one
              boundary has been dated, and one boundary is not a period. Reddit's
              30 days is deliberately not assumed here: same gateway, different
              upstream. One {which} reading after that date dates a second
              boundary and settles it, for one request.
            </>
          ) : w.boundary_passed ? (
            <>
              <strong>The only dated boundary ({fmt(w.boundary_passed)}) has
              passed</strong>, and no period is known, so this arm has nothing
              current to say about its window. One reading re-dates it.
            </>
          ) : (
            <>No boundary has been dated for this arm.</>
          )}
        </span>
      )}
      {w.source && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs))', opacity: 0.75 }}>
          {w.source}
          {w.boundary_from ? ` · boundary from ${w.boundary_from}` : ''}
        </span>
      )}
    </div>
  )
}

/** Consumption over time — or an honest account of why there is none yet.
 *
 * ⚠ EMPTY BY CONSTRUCTION IS NOT EMPTY BECAUSE NOTHING HAPPENED, and saying so
 *   is the only reason to render anything here at all. `rapidapi_quota_reading`
 *   was created on 2026-09-16 and every reading before that was written to a
 *   table that OVERWRITES, so the history is absent because we did not keep it
 *   — not because the quota sat still. Rendering a flat line or an empty chart
 *   would assert the second (rule 4).
 *
 * A RATE CARRIES ITS SPAN. This harvest is bursty — 1,103 documents on one run
 * and 2 on the next — so "30.6/day" without the window it was measured over is
 * a figure answering a question nobody asked (rule 7).
 */
function QuotaSeries({ s, which }) {
  if (s == null) {
    return (
      <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
        <strong style={{ color: 'var(--warn)' }}>
          The reading history could not be read.
        </strong>{' '}
        That is a fact about the database connection, not about consumption —
        there may be readings and this page cannot see them.
      </span>
    )
  }
  if (!s.readings || s.readings < 2 || s.per_day == null) {
    return (
      <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
        <strong style={{ color: 'var(--text)' }}>
          No reading history yet — this fills from the next metered call.
        </strong>{' '}
        {s.readings === 1
          ? 'One reading is recorded, and a rate needs two. '
          : 'The series is empty BY CONSTRUCTION, not because nothing has happened: '
            + 'every reading before 2026-09-16 was written to a table that keeps '
            + 'only the latest row per meter, so the past was overwritten rather '
            + 'than lost. '}
        A consumption rate appears here once two {which} readings exist.
      </span>
    )
  }
  return (
    <div className="stack stack-1">
      <span className="label">Consumption — measured over the recorded series</span>
      <div className="grid g2">
        <Stat n={`${s.consumed_is_a_floor ? '≥ ' : ''}${s.per_day.toFixed(1)}/day`}
              l={`over ${s.span_days.toFixed(1)} days`} />
        <Stat n={`${s.consumed_is_a_floor ? '≥ ' : ''}${count(s.consumed)}`}
              l={`requests across ${s.readings} readings`} />
      </div>
      <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
        Measured between {s.first_at} and {s.last_at}. The span is stated because
        this harvest is bursty — a rate without the window it was taken over is a
        figure answering a question nobody asked.
      </span>
      {/* A RESET IS NOT NEGATIVE CONSUMPTION. Until 2026-10-07 this read first
          minus last, and X's two resets turned it into -1,018 requests. Summed
          reading to reading now (judge/app.py _quota_consumption); the part a
          reset hides is said, not guessed. */}
      {s.resets > 0 && (
        <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch' }}>
          <strong style={{ color: 'var(--text)' }}>
            The quota reset {s.resets} time{s.resets === 1 ? '' : 's'} in this span, so these are floors.
          </strong>{' '}
          Requests in each new window are counted from the limit; requests made between the last reading
          and a reset were never read.
        </span>
      )}
    </div>
  )
}
