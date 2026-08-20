import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCapabilities, capabilityPage, capLabel, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Stat, Unreadable } from '../components/ui'
import { IconAlert, IconArrow, IconSearch } from '../components/Icons'

/**
 * The registry, and what evidence exists per model.
 *
 * There is no `GET /models` endpoint — only `GET /models/{id}` — so the roster
 * is taken from a capability page, which is explicit that it lists *every*
 * model in the registry and not only the ones people post about:
 *
 *   "The other 340 are listed unreported rather than omitted: a comparison
 *    over only the models people post about ranks popularity, not capability."
 *
 * The first capability gives the roster immediately. The remaining eleven load
 * in the background and fold in per-model evidence, so the page is useful at
 * once and gets more complete rather than blocking on twelve round trips.
 */
export default function Models() {
  const [roster, setRoster] = useState(null)
  const [evidence, setEvidence] = useState({})   // model id -> [{capability, voices, phrases}]
  const [checked, setChecked] = useState(0)
  const [total, setTotal] = useState(0)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    let alive = true

    ;(async () => {
      let caps
      try {
        caps = await listCapabilities()
      } catch (e) { if (alive) setErr(e.message); return }
      if (!alive) return
      setTotal(caps.length)

      const keys = caps.map((c) => c.key)

      // roster first, from one call
      try {
        const first = await capabilityPage(keys[0])
        if (!alive) return
        setRoster(first.models)
        setChecked(1)
        fold(first)
      } catch (e) {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message)
        return
      }

      // then enrich, one capability at a time so a slow database does not
      // open twelve connections at once
      for (const key of keys.slice(1)) {
        if (!alive) return
        try {
          const page = await capabilityPage(key)
          if (!alive) return
          fold(page)
        } catch { /* one capability failing should not blank the page */ }
        if (alive) setChecked((n) => n + 1)
      }
    })()

    function fold(page) {
      setEvidence((prev) => {
        const next = { ...prev }
        for (const m of page.models) {
          if (m.state === 'unreported') continue
          const rows = next[m.model_version_id] ? [...next[m.model_version_id]] : []
          rows.push({ capability: page.key, voices: m.voices, phrases: m.phrases, conditional: m.conditional })
          next[m.model_version_id] = rows
        }
        return next
      })
    }

    return () => { alive = false }
  }, [])

  const shown = useMemo(() => {
    if (!roster) return []
    const q = query.trim().toLowerCase()
    if (!q) return roster
    return roster.filter(
      (m) =>
        (m.display_name || '').toLowerCase().includes(q) ||
        (m.model_version_id || '').toLowerCase().includes(q)
    )
  }, [roster, query])

  const withEvidence = Object.keys(evidence).length

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="eyebrow">Models</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>The registry</h1>
        <p className="muted" style={{ maxWidth: '66ch' }}>
          Every model the board tracks, not only the ones people post about —
          a list of only the discussed ones would rank popularity, not capability.
        </p>
      </div>

      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!roster && !err && !unreadable && <div className="skel" style={{ height: 260 }} />}

      {roster && (
        <>
          <Reveal>
            <div className="card">
              <div className="grid g3">
                <Stat n={roster.length} l="models in the registry" />
                <Stat n={withEvidence} l="with any evidence" />
                <Stat n={`${checked}/${total}`} l="capabilities checked" />
              </div>
              {checked < total && (
                <p className="dim" style={{ fontSize: 'var(--fs-xs)', marginTop: 'var(--s3)' }}>
                  Still reading capability pages — the evidence column fills in as they land.
                </p>
              )}
              {checked === total && withEvidence === 0 && (
                <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--warn)', marginTop: 'var(--s3)' }}>
                  All {total} capabilities checked. No model has a single published
                  report — nobody has looked, which is not the same as nobody having
                  complained.
                </p>
              )}
            </div>
          </Reveal>

          <label className="searchbar">
            <IconSearch width={15} height={15} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Filter ${roster.length} models by name or id`}
              aria-label="Filter models"
            />
            {query && <button className="x" onClick={() => setQuery('')}>clear</button>}
          </label>

          <span className="label">
            {shown.length === roster.length
              ? `${roster.length} models`
              : `${shown.length} of ${roster.length} models`}
          </span>

          <div className="stack stack-1">
            {shown.slice(0, 200).map((m) => (
              <ModelRow key={m.model_version_id} m={m} rows={evidence[m.model_version_id]} />
            ))}
            {shown.length > 200 && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', padding: '10px 2px' }}>
                Showing the first 200. Narrow the filter to see the rest — the API does
                not paginate, so this cap is the client being polite, and it is saying so.
              </p>
            )}
            {shown.length === 0 && (
              <p className="dim" style={{ fontSize: 'var(--fs-sm)' }}>Nothing matches “{query}”.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function ModelRow({ m, rows }) {
  const vendor = (m.model_version_id || '').includes('/')
    ? m.model_version_id.split('/')[0]
    : null

  return (
    <Link to={`/models/${m.model_version_id}`} className="mrow">
      <span className="stack" style={{ gap: 3, minWidth: 0 }}>
        <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.display_name || m.model_version_id}</strong>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
          {m.model_version_id}
        </span>
        {rows && (
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            {rows.map((r) => `${capLabel(r.capability)} · ${r.voices} ${r.voices === 1 ? 'voice' : 'voices'}`).join('  ·  ')}
          </span>
        )}
      </span>

      <span className="row" style={{ gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
        {vendor && <Badge tone="mute">{vendor}</Badge>}
        {rows
          ? <Badge tone="pass">{rows.length} {rows.length === 1 ? 'report' : 'reports'}</Badge>
          : <Badge tone="mute">no reports</Badge>}
        <IconArrow width={13} height={13} style={{ opacity: .5 }} />
      </span>
    </Link>
  )
}
