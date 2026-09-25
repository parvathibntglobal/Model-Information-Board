import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listModels, listCapabilities, capabilityPage, fetchAll, capLabel, fmtTokens, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Stat, Unreadable } from '../components/ui'
import { IconAlert, IconArrow, IconSearch } from '../components/Icons'

/**
 * The registry: what each provider advertises, and what engineers have found.
 *
 * TWO KINDS OF FACT ON ONE PAGE, and they are not interchangeable.
 *
 *   advertised  context and feature flags — the vendor's claim about itself,
 *               from GET /models?tracked=1. True, and evidence of nothing.
 *   reported    voices and phrases — from the capability pages, gated.
 *
 * The roster arrives in one call. The twelve capability pages then load in the
 * background and fold in evidence, so the page is useful immediately and gets
 * more complete rather than blocking on twelve round trips.
 *
 * Sorting defaults to name, and cost is no longer a sort at all. It was offered
 * but never defaulted, on the grounds that putting the cheapest model on top is
 * a recommendation and this board does not make one without evidence. The price
 * COLUMN then went too: seventeen of the thirty tracked models are image, video
 * and speech models, priced per image, per second and per character, and a
 * column headed PER MTOK cannot hold any of them. More than half the page was a
 * unit that did not apply wearing the label of the half that did.
 *
 * WHICH thirty is config — contract/tracked_models.yaml — not a constant in
 * this bundle. `model_version` holds 344 because a router carries 344; that is
 * what the registry HOLDS, not what this page is for.
 */

//: How many models may be compared at once. Three, matching the backend's own
//: cap, and the reason is presentational rather than arbitrary: a fourth column
//: makes the table scroll sideways, which is where a comparison stops being
//: read. The backend refuses a fourth independently - this is not the only
//: guard, it is the one that explains itself before the request.
const COMPARE_MAX = 3

// PRICE IS NOT SHOWN ON THIS PAGE, SO IT DOES NOT SORT IT EITHER.
//
// `Cheapest input` and `Dearest input` went with the price column. A control
// that orders rows by a figure the reader cannot see is worse than no control:
// the list visibly rearranges and nothing on screen says what by. Same reason
// `Free only` went - a filter whose criterion is invisible.
//
// `Largest context` stays, because the context window is still on the row.
// NO SORT CONTROL, AND SO NO SORT.
//
// `Name` and `Largest context` were the last two, after the price sorts went
// with the price column. Removing the control without removing the sort would
// have left the list silently ordered by whichever happened to be the default -
// a choice nobody can see or change.
//
// The rows now arrive in the order `contract/tracked_models.yaml` lists them,
// and that order is deliberate: the models a fetch has actually run against
// lead the page. Re-sorting alphabetically in the browser would have thrown
// that away for no reason a reader asked for.


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

  // ── COMPARE SELECTION ────────────────────────────────────────────────────
  // Held here rather than in a URL param: it is a transient choice being made,
  // not a view worth linking to. The comparison itself IS a URL — /compare
  // carries the ids — so what is shareable is the finished comparison and not
  // a half-made selection.
  const navigate = useNavigate()
  const [picked, setPicked] = useState([])
  const togglePick = (id) =>
    setPicked((cur) => cur.includes(id)
      ? cur.filter((x) => x !== id)
      // The cap is also enforced on the checkbox (disabled past three) and
      // again in the backend. This is the last of the three, and the one that
      // makes a stray click a no-op rather than a silent truncation.
      : cur.length >= COMPARE_MAX ? cur : [...cur, id])
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
      } catch (e) {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message)
        return
      }

      // then the evidence, which is a separate kind of fact and a separate
      // set of calls. A capability page failing must not blank the roster.
      let vocabulary
      try {
        vocabulary = await listCapabilities()
      } catch { return }
      if (!alive) return
      setTotal(vocabulary.length)

      for (const key of vocabulary.map((c) => c.key)) {
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
    return out
  }, [roster, query])


  return (
    <div className="shell section-tight stack stack-4">
      <div className="row-between" style={{ alignItems: 'flex-start', gap: 'var(--s4)' }}>
        <div className="stack stack-1">
          <span className="eyebrow">Models</span>
          <h1 style={{ fontSize: 'var(--fs-display)' }}>The registry</h1>
        </div>

        {/* TOP RIGHT, AND ALWAYS PRESENT. The sticky bar at the foot of the
            list only appears once something is ticked, so until then nothing
            on the page said comparison existed — a column of bare checkboxes
            does not explain itself. Disabled with a reason is the right shape:
            it tells the reader the feature is there and what it needs, which is
            the opposite of the usual objection to a disabled control. */}
        <button
          type="button"
          className="btn btn-primary"
          disabled={picked.length < 2}
          onClick={() => navigate(`/compare?ids=${encodeURIComponent(picked.join(','))}`)}
          title={
            picked.length === 0
              ? `Tick 2–${COMPARE_MAX} models to compare what providers advertise against what engineers reported`
              : picked.length === 1
                ? 'Tick one more — a single model is its own page, not a comparison'
                : `Compare ${picked.length} models side by side`
          }
          style={{ flexShrink: 0, whiteSpace: 'nowrap' }}
        >
          {picked.length === 0 ? 'Compare models' : `Compare (${picked.length}) →`}
        </button>
      </div>

      {unreadable && <Unreadable detail={unreadable} />}
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!roster && !err && !unreadable && <div className="skel" style={{ height: 260 }} />}

      {roster && (
        <>
          {/* ONLY WHEN IT HAS SOMETHING TO SAY. This card used to hold two stats
              and a summary, so it always had content. With those gone it is two
              conditional notices and nothing else, and an unconditional wrapper
              renders an empty box whenever neither fires - which is most of the
              time. */}
          {(checked + failed < total || failed > 0) && (
            <Reveal>
              <div className="card">
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
              </div>
            </Reveal>
          )}

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

          <div className="row" style={{ gap: 'var(--s3)', flexWrap: 'wrap', justifyContent: 'space-between' }}>
            {/* The sort chips were here. With no control the count is the only
                child of this row, and `space-between` puts it where it was. */}

            <span className="label">
              {shown.length === roster.length
                ? `${roster.length} models`
                : `${shown.length} of ${roster.length} models`}
            </span>
          </div>

          <div className="stack stack-1">
            {shown.slice(0, 200).map((m) => (
              <ModelRow
                key={m.model_version_id}
                m={m}
                rows={evidence[m.model_version_id]}
                picked={picked.includes(m.model_version_id)}
                onPick={togglePick}
                atCap={picked.length >= COMPARE_MAX}
              />
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

          {/* THE COMPARE BAR, sticky because the list is 200 rows long and a
              button at the top is unreachable by the time you have picked your
              second model. Absent entirely at zero: an always-visible bar
              reading "Compare (0)" is a disabled control explaining nothing. */}
          {picked.length > 0 && (
            <div className="cmp-bar">
              <span className="stack stack-1" style={{ gap: 2, minWidth: 0 }}>
                <strong style={{ fontSize: 'var(--fs-sm)' }}>
                  {picked.length} selected
                </strong>
                <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                  {picked.length === 1
                    ? 'Tick one more — a single model is its own page, not a comparison.'
                    : `Up to ${COMPARE_MAX}. Advertised specification and counted reports, side by side.`}
                </span>
              </span>
              <span className="row" style={{ gap: 8 }}>
                <button type="button" className="chip" onClick={() => setPicked([])}>
                  Clear
                </button>
                {/* Kept here too, not for symmetry: the list is 200 rows and
                    the header button is off-screen by the time the second
                    model is ticked. Two copies of one action is the cost of a
                    long list, and it is cheaper than scrolling back up. */}
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={picked.length < 2}
                  onClick={() => navigate(`/compare?ids=${encodeURIComponent(picked.join(','))}`)}
                >
                  Compare ({picked.length}) →
                </button>
              </span>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function ModelRow({ m, rows, picked, onPick, atCap }) {

  return (
    <div className={`mrow-wrap${picked ? ' mrow-picked' : ''}`}>
      {/* OUTSIDE THE LINK. A checkbox inside an anchor is invalid HTML and
          unusable — every tick would navigate to the model page. */}
      <label className="mrow-pick" onClick={(e) => e.stopPropagation()}>
        <input
          type="checkbox"
          checked={picked}
          disabled={!picked && atCap}
          onChange={() => onPick(m.model_version_id)}
          aria-label={`Select ${m.display_name || m.model_version_id} to compare`}
          title={!picked && atCap
            ? `${COMPARE_MAX} is the maximum — a fourth column makes the table scroll sideways`
            : 'Compare this model'}
        />
      </label>
    {/* A ROW IS ONLY A LINK IF THERE IS A PAGE BEHIND IT.
    
        `/models/{id}` refuses an id the registry does not hold, and it is
        right to: its own 404 says an unknown id would read "nobody has
        reported on this model", which is indistinguishable from a model
        in the registry nobody has discussed. But four tracked models have
        no registry row at all, so linking them sent a reader to that
        refusal - a dead end reached by clicking something that looked
        live. The row still renders; it just does not pretend to go
        somewhere. */}
    {m.in_registry === false ? (
      <div className="mrow" style={{ cursor: 'default' }}
           title="Not in the registry the board polls, so there is no model page for it yet">
        <span className="stack" style={{ gap: 3, minWidth: 0 }}>
          <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.display_name || m.model_version_id}</strong>
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            {m.provider}
            {m.advertised_context ? ` · ${fmtTokens(m.advertised_context)} context` : ''}
          </span>
          {/* Which capability, from the roster row itself — so it is on screen
              the moment the list is, rather than 26 seconds later when the
              capability sweep lands. `rows` upgrades it with voice counts if and
              when that finishes. */}
          {m.evidence?.capabilities?.length > 0 && (
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
              {rows
                ? rows.map((r) => `${capLabel(r.capability)} · ${r.voices} ${r.voices === 1 ? 'voice' : 'voices'}`).join('  ·  ')
                : m.evidence.capabilities.map(capLabel).join('  ·  ')}
            </span>
          )}
        </span>

        <span className="row" style={{ gap: 'var(--s3)', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {/* THE PRICE BLOCK IS GONE. It read `$1.60 / $3.20 PER MTOK` for the
              thirteen models the OpenRouter poll carries and `no rate` for the
              seventeen it does not - and those seventeen are image, video and
              speech models, which are priced per image, per second and per
              character. A column headed PER MTOK cannot hold any of them, so more
              than half the page was a unit that did not apply, wearing the same
              label as the half that did. Removed rather than half-filled. */}

          {/* From the roster's own `evidence`, not from the capability sweep.
              The sweep takes 26 seconds and can fail per-page; this arrives with
              the row. `rows` still supplies WHICH capability once it lands. */}
          <EvidenceBadge e={m.evidence} rows={rows} />
          {/* BESIDE THE BADGE, NEVER INSTEAD OF IT. A cell has been through the
              gate; a board entry has not. Collapsing them breaks rule 4 in
              whichever direction you collapse - see BoardBadge.

              ON BOTH BRANCHES OF THE ROW, because #299 split it into a linked
              row and an unlinked one for models with no registry entry. A badge
              on one branch only is the same defect in half the rows. */}
          <BoardBadge b={m.board} />
          <IconArrow width={13} height={13} style={{ opacity: .5 }} />
        </span>
      </div>
    ) : (
      <Link
        to={`/models/${m.model_version_id}`}
        // `focus` carries which capability to open the model page on. It used to
        // prefer whichever one the reader had filtered by; the "Discussed under"
        // filter is gone, so the first capability this model has evidence for is
        // the only answer left - and `null` when it has none, rather than a
        // capability picked because it happened to sort first.
        state={{
          from: '/models',
          name: m.display_name,
          focus: m.evidence?.capabilities?.[0] || null,
        }}
        className="mrow"
      >
        <span className="stack" style={{ gap: 3, minWidth: 0 }}>
          <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.display_name || m.model_version_id}</strong>
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            {m.provider}
            {m.advertised_context ? ` · ${fmtTokens(m.advertised_context)} context` : ''}
          </span>
          {/* Which capability, from the roster row itself — so it is on screen
              the moment the list is, rather than 26 seconds later when the
              capability sweep lands. `rows` upgrades it with voice counts if and
              when that finishes. */}
          {m.evidence?.capabilities?.length > 0 && (
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
              {rows
                ? rows.map((r) => `${capLabel(r.capability)} · ${r.voices} ${r.voices === 1 ? 'voice' : 'voices'}`).join('  ·  ')
                : m.evidence.capabilities.map(capLabel).join('  ·  ')}
            </span>
          )}
        </span>

        <span className="row" style={{ gap: 'var(--s3)', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {/* THE PRICE BLOCK IS GONE. It read `$1.60 / $3.20 PER MTOK` for the
              thirteen models the OpenRouter poll carries and `no rate` for the
              seventeen it does not - and those seventeen are image, video and
              speech models, which are priced per image, per second and per
              character. A column headed PER MTOK cannot hold any of them, so more
              than half the page was a unit that did not apply, wearing the same
              label as the half that did. Removed rather than half-filled. */}

          {/* From the roster's own `evidence`, not from the capability sweep.
              The sweep takes 26 seconds and can fail per-page; this arrives with
              the row. `rows` still supplies WHICH capability once it lands. */}
          <EvidenceBadge e={m.evidence} rows={rows} />
          {/* BESIDE THE BADGE, NEVER INSTEAD OF IT. A cell has been through the
              gate; a board entry has not. Collapsing them breaks rule 4 in
              whichever direction you collapse - see BoardBadge.

              ON BOTH BRANCHES OF THE ROW, because #299 split it into a linked
              row and an unlinked one for models with no registry entry. A badge
              on one branch only is the same defect in half the rows. */}
          <BoardBadge b={m.board} />
          <IconArrow width={13} height={13} style={{ opacity: .5 }} />
        </span>
      </Link>
    )}
    </div>
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
/**
 * What the BOARD holds for this model. A second surface on the same evidence,
 * never a second opinion on the gate.
 *
 * ⚠ IT SITS BESIDE `EvidenceBadge` AND MUST NOT MERGE WITH IT. The two count
 *   different things and collapsing them misreads in whichever direction you
 *   collapse. Measured on DeepSeek V4 Pro, 2026-09-15:
 *
 *     entries only   23 reports  → reads as 23 findings, when ZERO cleared
 *                                  the publication bar
 *     cells only      6 cells    → reads as a near-empty model, while 22
 *                                  entries about it sit unread
 *
 *   The second is what this page did until now, which is why a fetch that
 *   produced 50 board entries changed nothing a reader could see.
 *
 * NO STATE WORD HERE, deliberately. `EvidenceBadge` says `few reports` because
 * a cell has a gate verdict behind it. An entry has been through nothing, so
 * this says only how many and where - a count, never a judgement (rule 3).
 */
function BoardBadge({ b }) {
  if (!b || !b.entries) return null
  const where = Object.entries(b.sections || {})
    .map(([section, n]) => `${n} ${section.replace('_', '-')}`)
    .join(', ')
  return (
    <Badge
      tone="mute"
      title={`Ungated. ${b.entries} report${b.entries === 1 ? '' : 's'} on the board for this model${where ? ` (${where})` : ''}. Board entries are what somebody said; they have not been counted against the publication bar the way a capability has.`}
    >
      {b.entries} on the board{where ? ` · ${where}` : ''}
    </Badge>
  )
}


function EvidenceBadge({ e, rows }) {
  // NULL MEANS THE LEGACY CAPABILITY CARDS ARE OFF (LEGACY_CELLS, judge/legacy.py),
  // not "nobody has discussed this". Cells are no longer rebuilt, so rendering the
  // rows still in `cell` would show a frozen verdict as live, and a missing one
  // would contradict the board badge beside it. BoardBadge carries the evidence.
  if (e === null) return null
  const state = e?.state || 'unreported'

  // The board has no publication gate any more, so these badges COUNT reports
  // rather than announcing a gate verdict. A count says how many people spoke;
  // it never says who was right.
  if (state === 'published') {
    return <Badge tone="pass">reported{rows ? ` · ${rows.length}` : ''}</Badge>
  }
  if (state === 'insufficient') {
    return (
      <Badge tone="warn" title="Somebody has reported on this. A low count is not a verdict.">
        few reports{e.reports ? ` · ${e.reports}` : ''}
      </Badge>
    )
  }
  return <Badge tone="mute">nobody has discussed this</Badge>
}
