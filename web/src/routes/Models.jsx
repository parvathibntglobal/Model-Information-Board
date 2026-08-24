import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { listModels, listCapabilities, capabilityPage, fetchAll, capLabel, fmtPrice, fmtTokens, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Stat, Unreadable } from '../components/ui'
import { IconAlert, IconArrow, IconSearch } from '../components/Icons'

/**
 * The registry: what each provider advertises, and what engineers have found.
 *
 * TWO KINDS OF FACT ON ONE PAGE, and they are not interchangeable.
 *
 *   advertised  price, context, feature flags — the vendor's claim about
 *               itself, from GET /models. True, and evidence of nothing.
 *   reported    voices and phrases — from the capability pages, gated.
 *
 * The roster arrives in one call. The twelve capability pages then load in the
 * background and fold in evidence, so the page is useful immediately and gets
 * more complete rather than blocking on twelve round trips.
 *
 * Sorting defaults to name. Cost is offered as a sort, never as the default —
 * ordering 342 unevidenced models by price and putting the cheapest on top is
 * a recommendation, and this board does not make one without evidence.
 */
/**
 * The evidence filter, and it is three-valued rather than a checkbox.
 *
 * "Has evidence" sounds binary and is not. 3 of 342 models have a cell and NONE
 * has a published one — every cell is `insufficient`, n_eff 0.012 against a
 * gate of 3.0. A checkbox has to pick: "has evidence = has a cell" shows three
 * models that did not clear the gate to someone who asked for evidence, and
 * "has evidence = published" shows an empty list that reads as a broken filter.
 *
 * So all three states are offered, with counts, and the empty one is legible
 * because the populated ones sit beside it. Rule 4 as a control.
 */
const EVIDENCE = {
  all:          { label: 'All models',     match: () => true },
  published:    { label: 'Published',      match: (m) => m.evidence?.state === 'published' },
  insufficient: { label: 'Below the gate', match: (m) => m.evidence?.state === 'insufficient' },
  unreported:   { label: 'Undiscussed',    match: (m) => (m.evidence?.state || 'unreported') === 'unreported' },
}

const SORTS = {
  name:     { label: 'Name',            fn: (a, b) => (a.display_name || '').localeCompare(b.display_name || '') },
  cheapest: { label: 'Cheapest input',  fn: (a, b) => nullsLast(a.price_in, b.price_in) },
  dearest:  { label: 'Dearest input',   fn: (a, b) => nullsLast(b.price_in, a.price_in) },
  context:  { label: 'Largest context', fn: (a, b) => (b.advertised_context || 0) - (a.advertised_context || 0) },
}

/** A model with no published rate sorts to the end rather than to £0. */
function nullsLast(x, y) {
  if (x == null && y == null) return 0
  if (x == null) return 1
  if (y == null) return -1
  return x - y
}

/* ------------------------------------------------------------------ search */

/**
 * Strip every separator, so `gpt-5`, `gpt 5` and `gpt5` are one string.
 *
 * This is the same normalisation the resolver applies to model mentions, and
 * for the same reason: a version number is written three ways by three people
 * and they all mean one model. The labelling pool has a whole stratum for it —
 * "spacing-variant: gpt-5 against gpt 5 against gpt5. Same model, three
 * surfaces, and the normaliser is what makes them one."
 *
 * A plain substring match got this wrong in the obvious direction. Measured
 * over the 342 models on staging: `gpt-5` found 29 and `gpt 5` found NONE,
 * which reads as "we do not have it" rather than "you typed a space".
 */
const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '')

const haystack = (m) =>
  [norm(m.display_name), norm(m.provider), norm(m.canonical_id)].join('')

/**
 * Squash first, tokens second.
 *
 * Squashing the whole query is exact about adjacency — `gpt 5` returns the same
 * 29 rows as `gpt-5`, no more. Falling back to per-token AND only when that
 * finds nothing buys word-order tolerance ("opus claude" → 8) without loosening
 * the common case, where it would have turned `o1 pro` from 1 hit into 2.
 */
function matches(models, query) {
  const q = query.trim()
  if (!q) return models

  // an id typed or pasted in full still finds its model, though the column is gone
  const raw = q.toLowerCase()
  if (raw.startsWith('mv')) {
    const byId = models.filter((m) => (m.model_version_id || '').toLowerCase().includes(raw))
    if (byId.length) return byId
  }

  const squashed = norm(q)
  if (squashed) {
    const hit = models.filter((m) => haystack(m).includes(squashed))
    if (hit.length) return hit
  }

  const terms = q.split(/\s+/).map(norm).filter(Boolean)
  if (!terms.length) return models
  return models.filter((m) => {
    const h = haystack(m)
    return terms.every((t) => h.includes(t))
  })
}

export default function Models() {
  const [roster, setRoster] = useState(null)
  const [evidence, setEvidence] = useState({})   // model id -> [{capability, voices, phrases}]
  const [checked, setChecked] = useState(0)
  const [failed, setFailed] = useState(0)
  const [total, setTotal] = useState(0)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('name')
  const [freeOnly, setFreeOnly] = useState(false)
  const [evidenceFilter, setEvidenceFilter] = useState('all')
  const [meta, setMeta] = useState(null)      // summary + priced_at, straight from the API
  const searchRef = useRef(null)

  // "/" jumps to the search box, the convention on any page that is mostly a
  // list. Guarded so it does not steal the key from someone typing in a field.
  useEffect(() => {
    function onKey(e) {
      if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return
      const t = e.target
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      e.preventDefault()
      searchRef.current?.focus()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    let alive = true

    ;(async () => {
      // the roster, in one call, with everything the provider advertises
      try {
        const list = await fetchAll((l, o) => listModels(l, o))
        if (!alive) return
        setRoster(list.models)
        setMeta({ summary: list.summary, priced_at: list.priced_at })
      } catch (e) {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message)
        return
      }

      // then the evidence, which is a separate kind of fact and a separate
      // set of calls. A capability page failing must not blank the roster.
      let caps
      try {
        caps = await listCapabilities()
      } catch { return }
      if (!alive) return
      setTotal(caps.length)

      for (const key of caps.map((c) => c.key)) {
        if (!alive) return
        try {
          const page = await fetchAll((l, o) => capabilityPage(key, l, o))
          if (!alive) return
          fold(page)
          setChecked((n) => n + 1)
        } catch {
          // A capability that could not be READ is not a capability with
          // nothing in it, and counting it as checked would let the page
          // conclude "no model has a single report" from requests that never
          // returned. One failure must not blank the roster, and it must not
          // quietly join the tally either.
          if (alive) setFailed((n) => n + 1)
        }
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
    let out = matches(roster, query)
    // `=== 0` and not falsy: null is "no published rate", not free.
    if (freeOnly) out = out.filter((m) => m.price_in === 0 && m.price_out === 0)
    out = out.filter(EVIDENCE[evidenceFilter].match)
    return [...out].sort(SORTS[sort].fn)
  }, [roster, query, sort, freeOnly, evidenceFilter])

  // Counted off the roster, not the filtered view — a tab that says how many
  // it holds must not change when another tab is selected.
  const evidenceCounts = useMemo(() => {
    if (!roster) return {}
    return Object.fromEntries(
      Object.entries(EVIDENCE).map(([k, v]) => [k, roster.filter(v.match).length])
    )
  }, [roster])

  const withEvidence = Object.keys(evidence).length
  const priced = roster ? roster.filter((m) => m.price_in != null).length : 0

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
              <div className="grid g4">
                <Stat n={roster.length} l="models in the registry" />
                <Stat n={priced} l="with a published price" />
                <Stat n={withEvidence} l="with any evidence" />
                <Stat n={`${checked}/${total}`} l="capabilities checked" />
              </div>
              {meta?.summary && (
                <p className="dim" style={{ fontSize: 'var(--fs-xs)', marginTop: 'var(--s3)' }}>
                  {meta.summary}
                  {meta.priced_at && ` Prices as advertised on ${new Date(meta.priced_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}.`}
                </p>
              )}
              {checked + failed < total && (
                <p className="dim" style={{ fontSize: 'var(--fs-xs)', marginTop: 'var(--s3)' }}>
                  Still reading capability pages — the evidence column fills in as they land.
                </p>
              )}
              {failed > 0 && (
                <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--warn)', marginTop: 'var(--s3)' }}>
                  {failed} of {total} capability {failed === 1 ? 'page' : 'pages'} could not
                  be read, so the evidence column below is incomplete. A model showing
                  “no reports” here may have reports under a capability that failed to
                  load — that is a gap in this page, not a fact about the model.
                </p>
              )}
              {checked === total && failed === 0 && withEvidence === 0 && (
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
              ref={searchRef}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Escape') setQuery('') }}
              placeholder={`Search ${roster.length} models — name, provider, or id`}
              aria-label="Search models by name"
              autoComplete="off"
              spellCheck="false"
            />
            {query && <button className="x" onClick={() => setQuery('')}>clear</button>}
          </label>

          {query && shown.length === 0 && (
            <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
              Spacing and punctuation are ignored, so “gpt 5”, “gpt-5” and “gpt5”
              all find the same models — if this is empty, the registry genuinely
              has nothing by that name.
            </p>
          )}

          {/* EVIDENCE, on its own row and above the sorts. It answers a
              different question from "how should these be ordered" — it says
              which of them the board can speak about at all — and every option
              carries its count so an empty one reads as a finding rather than
              as a filter that broke. */}
          <div className="stack stack-1">
            <span className="label">What the board knows about them</span>
            <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
              {Object.entries(EVIDENCE).map(([k, e]) => (
                <button
                  key={k}
                  className={`chip${evidenceFilter === k ? ' chip-on' : ''}`}
                  aria-pressed={evidenceFilter === k}
                  onClick={() => setEvidenceFilter(k)}
                >
                  {e.label}
                  <span className="tnum" style={{ opacity: .6, marginLeft: 6 }}>
                    {evidenceCounts[k] ?? '—'}
                  </span>
                </button>
              ))}
            </div>

            {evidenceFilter === 'published' && evidenceCounts.published === 0 && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '70ch' }}>
                Nothing has cleared the gate yet, and that is the honest answer
                rather than a broken filter. Publishing needs about three
                independent voices across two platforms;{' '}
                {evidenceCounts.insufficient > 0
                  ? <>the {evidenceCounts.insufficient} under <em>Below the gate</em> have someone
                     talking about them and not yet enough of them.</>
                  : <>no model has any reports at all yet.</>}
              </p>
            )}

            {evidenceFilter === 'insufficient' && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '70ch' }}>
                Somebody has reported on these and it is <strong>not yet enough to
                publish a finding</strong>. Below the gate is not a verdict — neither
                “good” nor “bad”, just not enough voices to say either.
              </p>
            )}

            {evidenceFilter === 'unreported' && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '70ch' }}>
                Nobody has discussed these. That is an absence of evidence, not
                evidence of a problem — a model here may be excellent and simply
                unwritten-about.
              </p>
            )}
          </div>

          <div className="row" style={{ gap: 'var(--s3)', flexWrap: 'wrap', justifyContent: 'space-between' }}>
            <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
              {Object.entries(SORTS).map(([k, s]) => (
                <button
                  key={k}
                  className={`chip${sort === k ? ' chip-on' : ''}`}
                  aria-pressed={sort === k}
                  onClick={() => setSort(k)}
                >
                  {s.label}
                </button>
              ))}
              <button
                className={`chip${freeOnly ? ' chip-on' : ''}`}
                aria-pressed={freeOnly}
                onClick={() => setFreeOnly((v) => !v)}
              >
                Free only
              </button>
            </div>

            <span className="label">
              {shown.length === roster.length
                ? `${roster.length} models`
                : `${shown.length} of ${roster.length} models`}
            </span>
          </div>

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
  const unpriced = m.price_in == null

  return (
    <Link
      to={`/models/${m.model_version_id}`}
      state={{ from: '/models', name: m.display_name }}
      className="mrow"
    >
      <span className="stack" style={{ gap: 3, minWidth: 0 }}>
        <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.display_name || m.model_version_id}</strong>
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          {m.provider}
          {m.advertised_context ? ` · ${fmtTokens(m.advertised_context)} context` : ''}
        </span>
        {rows && (
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            {rows.map((r) => `${capLabel(r.capability)} · ${r.voices} ${r.voices === 1 ? 'voice' : 'voices'}`).join('  ·  ')}
          </span>
        )}
      </span>

      <span className="row" style={{ gap: 'var(--s3)', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
        {/* Advertised, not measured — the price block is deliberately quiet
            next to the evidence badge, which is the figure that decides
            anything. A router shows "no rate", never a zero. */}
        <span className="stack" style={{ gap: 1, alignItems: 'flex-end' }}>
          <span
            className="mono"
            style={{ fontSize: 'var(--fs-sm)', color: unpriced ? 'var(--text-3)' : 'var(--text-1)' }}
            title={unpriced ? 'This model routes to others and publishes no rate of its own' : 'USD per million tokens, in / out'}
          >
            {unpriced ? 'no rate' : `${fmtPrice(m.price_in)} / ${fmtPrice(m.price_out)}`}
          </span>
          {!unpriced && (
            <span className="dim" style={{ fontSize: 10, letterSpacing: '.04em' }}>PER MTOK · IN / OUT</span>
          )}
        </span>

        {/* From the roster's own `evidence`, not from the capability sweep.
            The sweep takes 26 seconds and can fail per-page; this arrives with
            the row. `rows` still supplies WHICH capability once it lands. */}
        <EvidenceBadge e={m.evidence} rows={rows} />
        <IconArrow width={13} height={13} style={{ opacity: .5 }} />
      </span>
    </Link>
  )
}


/**
 * One badge, three states, never collapsed into two.
 *
 * `insufficient` is the one that must not be rounded off. Rounding it up to
 * "reported" tells a reader a claim was proven; rounding it down to "no
 * reports" hides that somebody looked. Both are wrong in a way the reader
 * cannot see, which is what rule 4 is about.
 */
function EvidenceBadge({ e, rows }) {
  const state = e?.state || 'unreported'

  if (state === 'published') {
    return <Badge tone="pass">published{rows ? ` · ${rows.length}` : ''}</Badge>
  }
  if (state === 'insufficient') {
    return (
      <Badge tone="warn" title="Someone has reported on this and it has not cleared the gate">
        below the gate{e.cells ? ` · ${e.cells}` : ''}
      </Badge>
    )
  }
  return <Badge tone="mute">nobody has discussed this</Badge>
}
