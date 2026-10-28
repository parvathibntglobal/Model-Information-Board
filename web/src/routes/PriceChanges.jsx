import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { BoardUnreadable, adminPriceChanges } from '../api'
import { modelPagePath } from '../catalog/format'
import { Badge, Stat, Unreadable } from '../components/ui'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import '../styles/price-changes.css'

/**
 * PRICE CHANGELOG (2026-10-27, Parvathi): signed in. Every OpenRouter list-price
 * change the registry poll has seen (judge/price_changes.py), newest first, with
 * fixed flags and a `newsworthy` mark - a short list to check before writing a
 * headline, never the headline itself.
 *
 * ONE SOURCE, UNCONFIRMED. Every price is OpenRouter's list price; OpenRouter can
 * move it without the provider changing anything. So a row says "seen on
 * OpenRouter", and the date is when the poll saw it, not when it changed.
 * Confirm on the provider's own page before using a change anywhere public.
 *
 * THE VIEW (`show`) works like Benchmarks' changelog: a News-worthy menu for the
 * kinds of news (cuts, rises, now free), and pills for every change and the
 * kinds that are never news on their own (settling, no longer polled, bounced,
 * provider waves). Counts follow the provider and size filters, so a count is
 * what clicking it shows.
 *
 * A PROVIDER WAVE IS A LABEL (review on #579, 2026-10-28): it mostly measures
 * OpenRouter repricing a provider's models in bulk, so it adds context ("wave
 * of 5") and never makes a change news-worthy.
 *
 * Filters live in the address (`?show=cut&provider=qwen&min=20&days=30`),
 * so a view can be sent to somebody.
 */

const WINDOWS = [7, 30, 90, 365]
// Badge tone, text and hover definition; the numbers are the server's (contract).
const UNPOLLED = (r) => `The poll stopped seeing this model: its last poll is over ${r.unpolled_hours} hours older than the newest poll, so this change can never settle. It may have left OpenRouter's list.`
const FLAG = {
  cut: ['pass', () => 'Cut', (r) => `Input or output price fell at least ${r.big_change_pct}%`],
  rise: ['fail', () => 'Rise', (r) => `Input or output price rose at least ${r.big_change_pct}%`],
  free: ['info', () => 'Now free', () => 'Both prices went to 0 from a paid price'],
  wave: ['mute', (c) => `Wave of ${c.wave_size}`,
    (r, c) => `Part of ${c.wave_size} ${c.provider} price changes the same day (UTC). Context only, never news on its own.`],
  settling: ['warn', () => 'Settling', (r) => `Not yet held ${r.hold_hours} hours without another change: it may still revert`],
  unpolled: ['warn', () => 'No longer polled', UNPOLLED],
  bounced: ['mute', () => 'Bounced', (r) => `Back to the previous price within ${r.bounce_days} days: likely a host switch or an ended promotion`],
}

// NEWS-WORTHY KINDS: each is a newsworthy change carrying that flag. The numbers
// in the hints are the server's (contract/price_changes.yaml), never a copy here.
const NEWS_RULE = (r) => `Settled, not bounced, still polled, and a cut or rise of at least ${r.big_change_pct}%, or now free`
const NEWS = [
  { key: 'news', label: 'All news-worthy', hint: NEWS_RULE },
  { key: 'cut', label: 'Cuts', hint: (r) => `Input or output price down at least ${r.big_change_pct}%` },
  { key: 'rise', label: 'Rises', hint: (r) => `Input or output price up at least ${r.big_change_pct}%` },
  { key: 'free', label: 'Now free', hint: () => 'Both prices went to 0 from a paid price' },
]
// EVERY CHANGE, and the kinds that are never news on their own.
const PILLS = [
  { key: 'all', label: 'All changes', hint: () => 'Every price change seen in the window, news-worthy or not' },
  { key: 'settling', label: 'Settling', hint: (r) => `Not yet held ${r.hold_hours} hours without another change: it may still revert` },
  { key: 'unpolled', label: 'No longer polled', hint: UNPOLLED },
  { key: 'bounced', label: 'Bounced', hint: (r) => `Back to the previous price within ${r.bounce_days} days: likely a host switch or an ended promotion` },
  { key: 'wave', label: 'Provider waves', hint: (r) => `${r.wave_min_models} or more of one provider's models changed the same day (UTC). Context only, never news on its own.` },
]
const PILL_KEYS = new Set(PILLS.map((f) => f.key))
const SHOWS = new Set([...NEWS, ...PILLS].map((f) => f.key))
const matches = (c, show) => (
  show === 'all' ? true
    : PILL_KEYS.has(show) ? c.flags.includes(show)
      : c.newsworthy && (show === 'news' || c.flags.includes(show)))

function NewsMenu({ show, counts, rules, onPick }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const away = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    const esc = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
  }, [open])
  const current = NEWS.find((f) => f.key === show)
  return (
    <div className="pc-news-wrap" ref={ref}>
      <button type="button" className={`pc-chip pc-news-btn${current ? ' on' : ''}`} aria-haspopup="menu"
              aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {current ? current.label : 'News-worthy'} <span className="pc-chip-n">{counts[current?.key || 'news'] ?? 0}</span> ▾
      </button>
      {open && (
        <div className="pc-news-menu" role="menu">
          {NEWS.map((f) => (
            <button key={f.key} type="button" role="menuitemradio" aria-checked={show === f.key}
                    title={rules ? f.hint(rules) : undefined}
                    className={`pc-news-item${show === f.key ? ' on' : ''}`} disabled={!counts[f.key]}
                    onClick={() => { onPick(f.key); setOpen(false) }}>
              <span className="pc-news-label">{f.label} <span className="pc-chip-n">{counts[f.key] ?? 0}</span></span>
              {rules && <span className="dim pc-small">{f.hint(rules)}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// Per million tokens, as OpenRouter lists it. A price not stated stays "—".
const fmtPrice = (v) => (v == null ? '—' : `$${v < 0.01 && v > 0 ? v.toPrecision(2) : +v.toFixed(4)}`)
const fmtPct = (p) => (p == null ? '' : `${p > 0 ? '+' : ''}${p}%`)
const fmtSeen = (iso) => new Date(iso).toLocaleString('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
}) + ' UTC'
const fmtDay = (iso) => new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })

function Move({ label, before, after, pct }) {
  const same = before === after
  return (
    <div className={`pc-move${same ? ' pc-same' : ''}`}>
      <span className="pc-k">{label}</span>
      <span className="tnum">{fmtPrice(before)} → {fmtPrice(after)}</span>
      {!same && pct != null && <span className={`pc-pct tnum ${pct < 0 ? 'pc-down' : 'pc-up'}`}>{fmtPct(pct)}</span>}
    </div>
  )
}

export default function PriceChanges() {
  useHead(PRIVATE.priceChanges)
  const [sp, setSp] = useSearchParams()
  const days = Number(sp.get('days')) || null
  const show = SHOWS.has(sp.get('show')) ? sp.get('show') : 'news'
  const provider = sp.get('provider') || ''
  const min = Number(sp.get('min')) || 0
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    setData(null)
    setErr(null)
    adminPriceChanges(days).then(setData).catch(setErr)
  }, [days])

  const set = (k, v) => {
    const next = new URLSearchParams(sp)
    if (v === '' || v == null || v === false) next.delete(k)
    else next.set(k, v === true ? '1' : String(v))
    setSp(next, { replace: true })
  }

  const providers = useMemo(
    () => [...new Set((data?.changes || []).map((c) => c.provider).filter(Boolean))].sort(),
    [data])
  const scoped = useMemo(() => (data?.changes || []).filter((c) => (
    (!provider || c.provider === provider)
    && (!min || (c.largest_pct != null && Math.abs(c.largest_pct) >= min))
  )), [data, provider, min])
  const counts = useMemo(() => Object.fromEntries(
    [...SHOWS].map((k) => [k, scoped.filter((c) => matches(c, k)).length])), [scoped])
  const rows = useMemo(() => scoped.filter((c) => matches(c, show)), [scoped, show])

  if (err) {
    return (
      <div className="shell section-tight stack stack-3 pc-page">
        <h1>Price changelog</h1>
        {err instanceof BoardUnreadable
          ? <Unreadable detail={err.message} compact />
          : <p className="pc-error">{err.message}</p>}
      </div>
    )
  }

  return (
    <div className="shell section-tight stack stack-3 pc-page">
      <header className="stack stack-2">
        <h1>Price changelog</h1>
        <p className="dim">
          Every change to a tracked model's <strong>OpenRouter list price</strong>, as the registry poll saw it.
          Prices are per million tokens. A date is the poll that <em>saw</em> the change; it happened some time
          after the poll before, and the poll can start hours late, so there is no fixed bound. A percentage is the plain change between the two listed prices; a
          price that was 0 or not stated has none. Hover a pill, a menu option or a badge for its rule.
        </p>
        <div className="pc-caveat" role="note">
          <strong>One source, not confirmed.</strong> OpenRouter can change its listed price without the provider
          changing theirs (a different host, a promotion, a re-listing). Check the provider's own pricing page
          before using a change in anything public. Only input, output and cached-read prices are tracked:
          long-context tiers, image, audio and per-request prices are not, so a change to only those does not
          appear here.
        </div>
      </header>

      {!data ? <p className="dim">Loading…</p> : (
        <>
          <div className="pc-stats">
            <Stat n={data.counts.changes} l={`changes in ${data.window_days} days`} />
            <Stat n={data.counts.newsworthy} l="newsworthy" title={NEWS_RULE(data.rules)} />
            <Stat n={data.counts.models} l="models changed" />
            {data.newest_seen_at && <Stat n={fmtDay(data.newest_seen_at)} l="newest seen" />}
          </div>
          {/* Rule 7: what these counts are counted over. */}
          <p className="dim pc-small">
            Counted over the registry's {data.population.models_with_history} models with price history
            (of {data.population.registry_models} registry models). The rest of the catalogue keeps only
            current prices, so its changes are not here.
            {data.newest_poll_at && <> Newest poll: {fmtSeen(data.newest_poll_at)}.</>}
          </p>

          <div className="pc-filters">
            <div className="pc-chips" role="group" aria-label="Show changes of one kind">
              {PILLS.map((f) => (
                <button key={f.key} type="button" className={`pc-chip${show === f.key ? ' on' : ''}`}
                        aria-pressed={show === f.key} onClick={() => set('show', f.key)} disabled={!counts[f.key]}
                        title={f.hint(data.rules)}>
                  {f.label} <span className="pc-chip-n">{counts[f.key]}</span>
                </button>
              ))}
            </div>
            <NewsMenu show={show} counts={counts} rules={data.rules}
                      onPick={(k) => set('show', k === 'news' ? '' : k)} />
            <label className="pc-sel">Provider
              <select value={provider} onChange={(e) => set('provider', e.target.value)}>
                <option value="">All</option>
                {providers.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </label>
            <label className="pc-sel">At least
              <select value={min} onChange={(e) => set('min', Number(e.target.value))}>
                {[0, 10, 20, 50].map((n) => <option key={n} value={n}>{n ? `${n}%` : 'any size'}</option>)}
              </select>
            </label>
            <label className="pc-sel">Window
              <select value={data.window_days} onChange={(e) => set('days', Number(e.target.value))}>
                {WINDOWS.map((n) => <option key={n} value={n}>{n} days</option>)}
              </select>
            </label>
          </div>

          {rows.length === 0 ? (
            <p className="dim">No change matches these filters in the last {data.window_days} days.</p>
          ) : (
            <ul className="pc-list">
              {rows.map((c) => (
                <li key={`${c.model_version_id}-${c.seen_at}`} className={`pc-row card${c.newsworthy ? ' pc-news' : ''}`}>
                  <div className="pc-head">
                    <div className="stack stack-1">
                      {c.canonical_id
                        ? <Link to={modelPagePath(c.canonical_id)} className="pc-name">{c.name}</Link>
                        : <span className="pc-name">{c.name}</span>}
                      <span className="dim pc-small">
                        {c.provider || 'provider not stated'} · seen on OpenRouter at the poll at {fmtSeen(c.seen_at)}
                      </span>
                    </div>
                    <div className="pc-flags">
                      {c.newsworthy && <Badge tone="pass" title={`${NEWS_RULE(data.rules)}. Still unconfirmed.`}>Newsworthy</Badge>}
                      {c.flags.map((f) => FLAG[f] && (
                        <Badge key={f} tone={FLAG[f][0]} title={FLAG[f][2](data.rules, c)}>{FLAG[f][1](c)}</Badge>
                      ))}
                      <Badge tone="mute" title="Not checked against the provider's own pricing page.">Unconfirmed</Badge>
                    </div>
                  </div>
                  <div className="pc-moves">
                    <Move label="Input" before={c.before.price_in} after={c.after.price_in} pct={c.change_pct.price_in} />
                    <Move label="Output" before={c.before.price_out} after={c.after.price_out} pct={c.change_pct.price_out} />
                    {(c.before.price_cached_read != null || c.after.price_cached_read != null) && (
                      <Move label="Cached read" before={c.before.price_cached_read} after={c.after.price_cached_read}
                            pct={c.change_pct.price_cached_read} />
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

        </>
      )}
    </div>
  )
}
