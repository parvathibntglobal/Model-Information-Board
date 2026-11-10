import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BoardUnreadable, approveAllUpdates, reviewUpdate, undoUpdate, updatesList } from '../api'
import { Badge, Unreadable } from '../components/ui'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import '../styles/updates.css'

/**
 * UPDATES (2026-10-29, Parvathi): signed in. Short headlines about what changed
 * - launches, price cuts and rises, retirements, benchmark results - each with
 * a one-line detail, built by judge/updates.py from data the board holds.
 *
 * TWO SECTIONS. News headlines shows every update nobody has declined, as soon
 * as it is built. Manage lists the same updates to approve, decline, restyle
 * (contract/updates.yaml templates) or edit; Undo takes back the last change.
 *
 * The words are templates filled from facts, never written by a model. An edit
 * that brings in a number the facts do not hold asks to be confirmed.
 *
 * Filters live in the address (`?section=manage&kind=price_cut&tracked=1`), so
 * a view can be sent to somebody.
 */

const KINDS = ['launch', 'price_cut', 'price_rise', 'price_change', 'retiring', 'benchmark', 'roundup']
// The filter's words; each card's own label is the contract's (`u.label`).
const KIND_CHIPS = { launch: 'Launches', price_cut: 'Price cuts', price_rise: 'Price rises', price_change: 'Price changes', retiring: 'Retiring', benchmark: 'Benchmarks', roundup: 'Round-ups' }
const KIND_TONE = { launch: 'info', price_cut: 'pass', price_rise: 'fail', price_change: 'warn', retiring: 'warn', benchmark: 'mute', roundup: 'info' }
const STATUSES = [
  { key: 'pending', label: 'Not reviewed', hint: 'Shown on News headlines; nobody has approved or declined it yet' },
  { key: 'approved', label: 'Approved', hint: 'Shown on News headlines, checked by a person' },
  { key: 'published', label: 'Published', hint: 'On the home page now' },
  { key: 'removed', label: 'Removed from home', hint: 'Published, then taken off the home page by itself: older than the home page keeps, or no longer in the data' },
  { key: 'declined', label: 'Declined', hint: 'Hidden from News headlines' },
  { key: 'all', label: 'All', hint: 'Every update in the window' },
]
const WINDOWS = [7, 30, 90]
const PAGE = 40
/** Whether an update belongs under a review filter; Published is the home page's. */
const inStatus = (u, key) => (
  key === 'all' ? true
    : key === 'published' ? !!u.home?.on_home
      : key === 'removed' ? !!u.home && !u.home.on_home
        : u.status === key)

/** Why a published update is no longer on the home page, in words. */
const removedWhy = (home, days) => ({
  expired: `published more than ${days} days ago`,
  not_in_data: 'no longer in the data',
  not_approved: 'no longer approved',
}[home.removed] || '')

const fmtDay = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', {
  weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
})
const fmtWhen = (iso) => new Date(iso).toLocaleString('en-GB', {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
}) + ' UTC'

function KindTag({ u }) {
  return <Badge tone={KIND_TONE[u.kind]}>{u.label}</Badge>
}

/**
 * EVERY PRICE UPDATE ASKS TO BE VERIFIED. A listed price can be the provider's
 * own change or only the router's, so the words do not say which; this mark
 * does, and a move past `second_check_pct` says it more firmly.
 */
function Verify({ u, pct }) {
  if (!u.kind.startsWith('price')) return null
  return u.second_check ? (
    <Badge tone="warn" title={`A move of ${pct}% or more. Large moves on a router's list are often a host switch: confirm on the provider's own pricing page before sharing it.`}>
      Big move: verify first
    </Badge>
  ) : (
    <Badge tone="mute" title="Seen in OpenRouter's listed price. Confirm on the provider's own pricing page before relying on it.">
      Verify with the provider
    </Badge>
  )
}

function SourceNote({ u }) {
  return (
    <span className="up-src" tabIndex={0} title={u.source} aria-label={`Source: ${u.source}`}>
      Source
    </span>
  )
}

/**
 * PUBLISH TO THE HOME PAGE (2026-10-29): stores the decision and the words,
 * fixed, for the home page's updates strip (components/UpdatesStrip.jsx). ONLY ON
 * APPROVED UPDATES: approving happens in Manage, and an update nobody approved
 * never gets the button. A card whose words changed after publishing offers
 * Republish; one taken off the home page by itself (after `home_days`) says
 * so and can be published again.
 */
function PublishButton({ u, act, busy, saving, days }) {
  const off = busy || !saving
  if (!u.home && u.status !== 'approved') return null
  if (!u.home) {
    return (
      <button type="button" className="btn btn-ghost up-btn" disabled={off}
              onClick={() => act({ key: u.key, action: 'publish' })}
              title="Show this headline on the home page, in these exact words.">
        Publish
      </button>
    )
  }
  return (
    <span className="up-pub">
      {u.home.on_home
        ? <Badge tone="pass" title={`Published by ${u.home.by}, ${fmtWhen(u.home.at)}`}>On home page</Badge>
        : <Badge tone="mute" title={`Published by ${u.home.by}, ${fmtWhen(u.home.at)}`}>Removed from home: {removedWhy(u.home, days)}</Badge>}
      {(!u.home.current || !u.home.on_home) && (
        <button type="button" className="btn btn-ghost up-btn" disabled={off}
                onClick={() => act({ key: u.key, action: 'publish' })}
                title={u.home.on_home
                  ? 'The words changed after publishing. Republish to show the new words on the home page.'
                  : `Put it back on the home page, in these words, for another ${days} days.`}>
          Republish
        </button>
      )}
      <button type="button" className="btn btn-ghost up-btn" disabled={off}
              onClick={() => act({ key: u.key, action: 'unpublish' })}
              title="Take it off the home page. It stays on News headlines.">
        Unpublish
      </button>
    </span>
  )
}

/** One headline card on News headlines. */
function Headline({ u, pct, act, busy, saving, days }) {
  return (
    <article className={`up-card card${u.home ? ' up-on-home' : ''}`}>
      <div className="up-meta">
        <KindTag u={u} />
        <Verify u={u} pct={pct} />
      </div>
      <h3 className="up-head">{u.headline}</h3>
      <p className="up-detail">{u.detail}</p>
      <div className="up-foot">
        <span className="up-why">{u.why}</span>
        <SourceNote u={u} />
      </div>
      {(u.home || u.status === 'approved') && (
        <div className="up-card-actions">
          <PublishButton u={u} act={act} busy={busy} saving={saving} days={days} />
        </div>
      )}
    </article>
  )
}

/** Updates by day, newest first; upcoming retirements first, as "Coming up". */
function byDay(items) {
  const groups = []
  for (const u of items) {
    const label = u.upcoming ? 'Coming up' : fmtDay(u.date)
    const last = groups[groups.length - 1]
    if (last && last.label === label) last.items.push(u)
    else groups.push({ label, items: [u] })
  }
  return groups
}

function Chips({ value, options, counts, onPick, label }) {
  return (
    <div className="pc-chips" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.key} type="button" className={`pc-chip${value === o.key ? ' on' : ''}`}
                aria-pressed={value === o.key} onClick={() => onPick(o.key)} title={o.hint}>
          {o.label} {counts && <span className="pc-chip-n">{counts[o.key] ?? 0}</span>}
        </button>
      ))}
    </div>
  )
}

function NewsHeadlines({ data, shownItems, more, onMore, act, busy }) {
  if (!shownItems.length) return <p className="dim">No update matches these filters in the last {data.window_days} days.</p>
  return (
    <>
      {byDay(shownItems).map((g) => (
        <section key={g.label} className="up-day">
          <h2 className="up-day-h">{g.label}</h2>
          <div className="up-grid">
            {g.items.map((u) => (
              <Headline key={u.key} u={u} pct={data.second_check_pct} act={act} busy={busy} saving={data.saving}
                        days={data.home_days} />
            ))}
          </div>
        </section>
      ))}
      {more > 0 && (
        <button type="button" className="btn btn-ghost up-more" onClick={onMore}>Show older ({more} more)</button>
      )}
    </>
  )
}

/** One update in Manage: its words, its review, and what can be done to it. */
function ManageRow({ u, data, act, busy }) {
  const [editing, setEditing] = useState(false)
  const [picking, setPicking] = useState(false)
  const [headline, setHeadline] = useState(u.headline)
  const [detail, setDetail] = useState(u.detail)
  const [unknown, setUnknown] = useState(null)
  const off = !data.saving || busy

  useEffect(() => {
    if (!editing) { setHeadline(u.headline); setDetail(u.detail); setUnknown(null) }
  }, [u.headline, u.detail, editing])

  const save = async (confirm) => {
    const done = await act({ key: u.key, action: 'edit', headline, detail, confirm }, (err) => {
      const numbers = err?.status === 409 ? err.body?.detail?.numbers : null
      if (numbers) { setUnknown(numbers); return true }
      return false
    })
    if (done) { setEditing(false); setUnknown(null) }
  }

  const statusTone = { pending: 'mute', approved: 'pass', declined: 'fail' }[u.status]
  const statusWord = STATUSES.find((s) => s.key === u.status)?.label
  return (
    <li className={`up-row card up-${u.status}`}>
      <div className="up-meta">
        <KindTag u={u} />
        <span className="dim up-small">{u.upcoming ? `Coming up: ${fmtDay(u.date)}` : fmtDay(u.date)}</span>
        <Badge tone={statusTone}>{statusWord}</Badge>
        {u.kind === 'roundup' && !u.published && u.status !== 'declined' && (
          <Badge tone="warn" title="A round-up is a summary, so it goes on News headlines only once someone approves it">
            Publishes once approved
          </Badge>
        )}
        {u.edited && <Badge tone="info" title="A person's own words replace the style's">Edited</Badge>}
        <Verify u={u} pct={data.second_check_pct} />
        {u.tracked && <Badge tone="mute" title="One of the models on the registry page">Tracked</Badge>}
        {u.gone && (
          <Badge tone="warn" title="Its facts changed after it was published (a cut that did not last, a launch that joined a group), so it is no longer built. Shown in its published words so it can be taken off the home page.">
            No longer in the data
          </Badge>
        )}
        {u.home && (u.home.on_home ? (
          <Badge tone="pass" title={`Published by ${u.home.by}, ${fmtWhen(u.home.at)}${u.home.current ? '' : '. The words changed since: republish from News headlines.'}`}>
            {u.home.current ? 'On home page' : 'On home page (old words)'}
          </Badge>
        ) : (
          <Badge tone="mute" title={`Published by ${u.home.by}, ${fmtWhen(u.home.at)}`}>
            Removed from home: {removedWhy(u.home, data.home_days)}
          </Badge>
        ))}
      </div>

      {editing ? (
        <div className="up-edit">
          <label className="up-field">Headline
            <input value={headline} maxLength={data.edit_limits.headline} onChange={(e) => { setHeadline(e.target.value); setUnknown(null) }} />
          </label>
          <label className="up-field">Detail
            <textarea rows={2} value={detail} maxLength={data.edit_limits.detail} onChange={(e) => { setDetail(e.target.value); setUnknown(null) }} />
          </label>
          {unknown && (
            <div className="up-warn" role="alert">
              <strong>Check these numbers:</strong> {unknown.join(', ')} {unknown.length === 1 ? 'is' : 'are'} not in this
              update&apos;s facts. Save anyway only if you have checked {unknown.length === 1 ? 'it' : 'them'}.
            </div>
          )}
          <div className="up-actions">
            {unknown
              ? <button type="button" className="btn btn-primary up-btn" disabled={off} onClick={() => save(true)}>Save anyway</button>
              : <button type="button" className="btn btn-primary up-btn" disabled={off} onClick={() => save(false)}>Save</button>}
            <button type="button" className="btn btn-ghost up-btn" onClick={() => setEditing(false)}>Cancel</button>
            <span className="dim up-small">Leave a field empty to use the style&apos;s words.</span>
          </div>
        </div>
      ) : (
        <div className="stack stack-1">
          <h3 className="up-head">{u.headline}</h3>
          <p className="up-detail">{u.detail}</p>
        </div>
      )}

      {!editing && (
        <div className="up-actions">
          {u.status !== 'approved' && !u.gone && (
            <button type="button" className="btn btn-ghost up-btn up-approve" disabled={off}
                    onClick={() => act({ key: u.key, action: 'approve' })}>Approve</button>
          )}
          {u.gone && u.home?.on_home && (
            <button type="button" className="btn btn-ghost up-btn" disabled={off}
                    onClick={() => act({ key: u.key, action: 'unpublish' })}
                    title="Take it off the home page now">Unpublish</button>
          )}
          {u.status === 'declined' ? (
            <button type="button" className="btn btn-ghost up-btn" disabled={off}
                    onClick={() => act({ key: u.key, action: 'restore' })}
                    title="Show it on News headlines again, not reviewed">Restore</button>
          ) : (
            <button type="button" className="btn btn-ghost up-btn up-decline" disabled={off}
                    onClick={() => act({ key: u.key, action: 'decline' })}
                    title="Hide it from News headlines">Decline</button>
          )}
          {!u.gone && (<>
          <button type="button" className={`btn btn-ghost up-btn${picking ? ' on' : ''}`} disabled={u.styles.length < 2}
                  aria-expanded={picking} onClick={() => setPicking((v) => !v)}
                  title="See every style this update can take, worded in full">
            Style: {u.styles.find((st) => st.id === u.style)?.label} · {u.styles.length} to choose
          </button>
          <button type="button" className="btn btn-ghost up-btn" disabled={off} onClick={() => setEditing(true)}>Edit</button>
          </>)}
          {u.undo && (
            <button type="button" className="btn btn-ghost up-btn" disabled={off} onClick={() => act({ undo: u.key })}
                    title={`Take back: ${u.undo.action} by ${u.undo.by}, ${fmtWhen(u.undo.at)}`}>Undo</button>
          )}
          <span className="dim up-small up-who">
            {u.reviewed_by
              ? <>Last change by {u.reviewed_by}, {fmtWhen(u.reviewed_at)}</>
              : 'Nobody has reviewed this yet'}
            {' · '}<SourceNote u={u} />
          </span>
        </div>
      )}

      {/* THE STYLE PICKER (2026-10-29): every style this update can take,
          worded in full from its facts, so a choice is made on the words. */}
      {picking && !editing && (
        <div className="up-picker" role="radiogroup" aria-label="Styles for this update">
          {u.edited && <p className="dim up-small">Picking a style replaces the edited words.</p>}
          {u.styles.map((st) => {
            const current = st.id === u.style && !u.edited
            return (
              <div key={st.id} className={`up-pick${current ? ' on' : ''}`}>
                <div className="up-pick-text">
                  <span className="up-pick-label">{st.label}{current && ' · in use'}</span>
                  <span className="up-pick-head">{st.headline}</span>
                  <span className="up-pick-detail">{st.detail}</span>
                </div>
                <button type="button" className="btn btn-ghost up-btn" disabled={off || current}
                        role="radio" aria-checked={current}
                        onClick={async () => { if (await act({ key: u.key, action: 'style', style: st.id })) setPicking(false) }}>
                  {current ? 'In use' : 'Use this'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </li>
  )
}

/** A template as written, its {placeholders} marked as the facts they are. */
function Template({ text }) {
  return (
    <>
      {text.split(/(\{[A-Za-z_]+\})/).map((part, i) => (
        /^\{[A-Za-z_]+\}$/.test(part)
          ? <span key={i} className="up-slot" title="Filled from the update's facts">{part.slice(1, -1).replace(/_/g, ' ')}</span>
          : <span key={i}>{part}</span>
      ))}
    </>
  )
}

/**
 * EVERY TEMPLATE STYLE, grouped by kind (contract/updates.yaml, sent by the
 * server). Each style shows its template and, when an update in the current
 * window uses that set, the same style filled from it.
 */
function StyleCatalog({ catalog }) {
  // ALL CLOSED ON LOAD, ONE OPEN AT A TIME (Parvathi, 2026-10-29): opening a
  // kind closes the one that was open.
  const [openKind, setOpenKind] = useState(null)
  return (
    <section className="card up-info-card up-info-wide">
      <h2>Template styles</h2>
      <p>
        Every style a headline can take, by kind. The <span className="up-slot">marked words</span> are filled from
        the update&apos;s facts. The example is the same style filled from an update in the current window; a style
        has none when no update in the window has that shape, or lacks a fact it needs.
      </p>
      {KINDS.map((kind) => {
        const sets = catalog.filter((c) => c.kind === kind)
        if (!sets.length) return null
        const count = sets.reduce((n, c) => n + c.styles.length, 0)
        return (
          <details key={kind} className="up-cat" open={openKind === kind}>
            <summary onClick={(e) => { e.preventDefault(); setOpenKind((o) => (o === kind ? null : kind)) }}
                     aria-expanded={openKind === kind}>
              <span className="up-cat-kind">{KIND_CHIPS[kind]}</span>
              <span className="dim up-small">{sets.length} {sets.length === 1 ? 'shape' : 'shapes'}, {count} styles</span>
            </summary>
            {sets.map((c) => (
              <div key={c.set} className="up-cat-set">
                <h3 className="up-cat-h">{c.label}</h3>
                <div className="up-cat-rows">
                  {c.styles.map((st, i) => (
                    <div key={st.id} className="up-cat-row">
                      <div className="up-cat-name">
                        {st.label}
                        {i === 0 && <span className="dim up-small"> (default)</span>}
                      </div>
                      <div>
                        <div className="up-cat-head"><Template text={st.headline} /></div>
                        <div className="up-cat-detail"><Template text={st.detail} /></div>
                      </div>
                      <div className="up-cat-ex">
                        {st.example ? (
                          <>
                            <div className="up-cat-head">{st.example.headline}</div>
                            <div className="up-cat-detail">{st.example.detail}</div>
                          </>
                        ) : <span className="dim up-small">No example in this window</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </details>
        )
      })}
    </section>
  )
}

/** What this page does and how to use it. Numbers come from the server. */
function Info({ data }) {
  return (
    <div className="up-info">
      <section className="card up-info-card">
        <h2>What this page is for</h2>
        <p>
          Updates turns changes the board already tracks into short news headlines, so a reader can see in a
          minute what moved in AI models: what launched, what got cheaper or pricier, what is retiring and what
          scored well. Approved headlines can be published to the home page as a strip of headlines that keeps readers
          coming back.
        </p>
        <p>
          Nothing here is written by an AI and nothing new is collected. Every update is rebuilt from the
          board&apos;s own data each time the page opens; <strong>Refresh</strong> rebuilds it after new data
          arrives, round-ups included.
        </p>
      </section>

      <section className="card up-info-card">
        <h2>Where updates come from</h2>
        <dl className="up-dl">
          <dt>Launches</dt>
          <dd>A new model in the registry, with its context window and price. Several from one provider on the same day become one update.</dd>
          <dt>Price cuts and rises</dt>
          <dd>A listed price move the Price changelog marks newsworthy, judged from the settled price (what held a week before), never from a price that is flipping or did not last. Shown as prices, never percentages.</dd>
          <dt>Price changes</dt>
          <dd>One price fell while the other rose. It is never called cheaper or pricier, and never grouped.</dd>
          <dt>Retiring</dt>
          <dd>A model with a listed retirement date coming up, or just passed.</dd>
          <dt>Benchmarks</dt>
          <dd>A model&apos;s first scores, a new #1 on a board, or a score that moved. A model a board stops listing is never news: it is often the page changing, not the model.</dd>
          <dt>Round-ups</dt>
          <dd>A summary of each finished week&apos;s launches and price moves. A summary is a judgement, so it shows on News headlines only once someone approves it.</dd>
        </dl>
      </section>

      <section className="card up-info-card">
        <h2>How headlines are written</h2>
        <p>
          Each kind of update has two or three <strong>template styles</strong>, filled from the update&apos;s
          facts: the same numbers, worded differently. A headline says what happened with its key number; the
          line under it explains it. A style is offered only when every fact it needs is known, so a launch with
          no listed price never claims one.
        </p>
        <p>
          The styles live in <code>contract/updates.yaml</code>, so a change to the wording is reviewed like any
          other change to the board. Every style is listed under <strong>Template styles</strong> below.
        </p>
      </section>

      <section className="card up-info-card">
        <h2>Manage: the options</h2>
        <dl className="up-dl">
          <dt>Approve</dt>
          <dd>A person checked it. It stays on News headlines, gets a Publish button there, and a round-up starts showing there.</dd>
          <dt>Decline / Restore</dt>
          <dd>Decline hides it from News headlines and takes it off the home page. Restore brings it back.</dd>
          <dt>Style</dt>
          <dd>Pick another template style. It replaces any edited words.</dd>
          <dt>Edit</dt>
          <dd>Write your own headline or detail. A number that is not in the update&apos;s facts asks you to check it before saving.</dd>
          <dt>Undo</dt>
          <dd>Takes back the last change, one step at a time.</dd>
          <dt>Filters</dt>
          <dd>Not reviewed, Approved, Published (on the home page now), Removed from home, Declined, or All. News headlines has an <strong>Approved only</strong> switch.</dd>
          <dt>Approve all shown</dt>
          <dd>Approves every not-reviewed update in the list below. Declined ones stay declined.</dd>
        </dl>
      </section>

      <section className="card up-info-card">
        <h2>Publishing to the home page</h2>
        <p>
          Approve an update in <strong>Manage</strong> first: only approved updates get a
          <strong> Publish</strong> button on News headlines. Publishing puts it in the home page&apos;s updates strip
          in its words at that moment. Later edits or style changes do not reach the home page until you
          <strong> Republish</strong>; <strong>Unpublish</strong> takes it off.
        </p>
        <p>
          A headline stays on the home page for <strong>{data.home_days} days</strong> from when it was published,
          then comes off by itself and is listed in Manage under <strong>Removed from home</strong>, where it can be
          published again. A headline no longer in the data (a cut that did not last, a retirement date that changed) comes off at once.
        </p>
      </section>

      <section className="card up-info-card">
        <h2>The marks on a card</h2>
        <dl className="up-dl">
          <dt>Verify with the provider</dt>
          <dd>Every price update. The price was seen on OpenRouter&apos;s list, which can be the provider&apos;s change or only the router&apos;s.</dd>
          <dt>Big move: verify first</dt>
          <dd>A price move of {data.second_check_pct}% or more, often a host switch rather than a real price change.</dd>
          <dt>Tracked</dt>
          <dd>About a model on the registry page.</dd>
          <dt>Edited</dt>
          <dd>A person&apos;s own words replace the style&apos;s.</dd>
          <dt>On home page</dt>
          <dd>Published; &ldquo;old words&rdquo; means it changed after publishing.</dd>
        </dl>
      </section>

      <StyleCatalog catalog={data.style_catalog} />
    </div>
  )
}

function Manage({ data, shownItems, status, setStatus, counts, act, busy, more, onMore }) {
  const pending = shownItems.filter((u) => u.status === 'pending')
  return (
    <>
      {!data.saving && (
        <div className="pc-caveat" role="note">
          <strong>Saving is off here.</strong> The table that stores decisions (migration
          20261029T1200_update_review) is not in this database yet, so nothing in Manage can be saved. Every update
          still shows on News headlines.
        </div>
      )}
      <div className="pc-filters">
        <Chips value={status} options={STATUSES} counts={counts} onPick={setStatus} label="Show updates by review" />
        <button type="button" className="btn btn-ghost up-btn" disabled={!data.saving || busy || !pending.length}
                onClick={() => act({ approveAll: pending.map((u) => u.key) })}
                title="Approve every update listed below that nobody has reviewed. Declined ones stay declined.">
          Approve all shown ({pending.length})
        </button>
      </div>
      {!shownItems.length
        ? <p className="dim">No update matches these filters.</p>
        : (
          <ul className="up-list">
            {shownItems.map((u) => <ManageRow key={u.key} u={u} data={data} act={act} busy={busy} />)}
          </ul>
        )}
      {more > 0 && (
        <button type="button" className="btn btn-ghost up-more" onClick={onMore}>Show older ({more} more)</button>
      )}
    </>
  )
}

export default function Updates() {
  useHead(PRIVATE.updates)
  const [sp, setSp] = useSearchParams()
  const section = ['manage', 'info'].includes(sp.get('section')) ? sp.get('section') : 'news'
  const days = Number(sp.get('days')) || null
  const kind = KINDS.includes(sp.get('kind')) ? sp.get('kind') : 'all'
  const tracked = sp.get('tracked') === '1'
  // News headlines only: just the updates a person approved in Manage.
  const approvedOnly = sp.get('approved') === '1'
  const status = STATUSES.some((s) => s.key === sp.get('status')) ? sp.get('status') : 'pending'
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [actErr, setActErr] = useState(null)
  const [limit, setLimit] = useState(PAGE)

  const load = useCallback(() => updatesList(days).then(setData), [days])
  useEffect(() => {
    setData(null)
    setErr(null)
    load().catch(setErr)
  }, [load])
  useEffect(() => { setLimit(PAGE) }, [section, kind, tracked, approvedOnly, status, days])

  const set = (k, v) => {
    const next = new URLSearchParams(sp)
    if (v === '' || v == null || v === false || (v === 'all' && k === 'kind')) next.delete(k)
    else next.set(k, v === true ? '1' : String(v))
    setSp(next, { replace: true })
  }

  /** One change, then the list again. `handled(err)` may claim an error. */
  const act = async (what, handled) => {
    setBusy(true)
    setActErr(null)
    try {
      if (what.undo) await undoUpdate(what.undo)
      else if (what.approveAll) await approveAllUpdates(what.approveAll, days)
      else await reviewUpdate({ ...what, days })
      await load()
      return true
    } catch (e) {
      if (!(handled && handled(e))) setActErr(typeof e.message === 'string' ? e.message : 'That change was not saved.')
      return false
    } finally {
      setBusy(false)
    }
  }

  const scoped = useMemo(() => (data?.updates || []).filter((u) => (
    (kind === 'all' || u.kind === kind) && (!tracked || u.tracked)
  )), [data, kind, tracked])
  const live = useMemo(
    () => scoped.filter((u) => u.published && (!approvedOnly || u.status === 'approved')),
    [scoped, approvedOnly])
  const kindCounts = useMemo(() => {
    const pool = (data?.updates || []).filter((u) => (!tracked || u.tracked)
      && (section === 'manage' || (u.published && (!approvedOnly || u.status === 'approved'))))
    return Object.fromEntries([['all', pool.length], ...KINDS.map((k) => [k, pool.filter((u) => u.kind === k).length])])
  }, [data, tracked, section, approvedOnly])
  const statusCounts = useMemo(() => ({
    ...Object.fromEntries(STATUSES.map((s) => [s.key, scoped.filter((u) => inStatus(u, s.key)).length])),
  }), [scoped])
  const managed = useMemo(() => scoped.filter((u) => inStatus(u, status)), [scoped, status])

  const kindOptions = [{ key: 'all', label: 'All' }, ...KINDS.map((k) => ({ key: k, label: KIND_CHIPS[k] }))]

  if (err) {
    return (
      <div className="shell section-tight stack stack-3 up-page">
        <h1>Updates</h1>
        {err instanceof BoardUnreadable
          ? <Unreadable detail={err.message} compact />
          : <p className="pc-error">{err.message}</p>}
      </div>
    )
  }

  const list = section === 'manage' ? managed : live
  return (
    <div className="shell section-tight stack stack-3 up-page">
      <header className="stack stack-2">
        <h1>Updates</h1>
        <p className="dim">
          What changed for AI models: launches, price cuts and rises, retirements and benchmark results. Each update
          is built from the board&apos;s own data and worded from a fixed template, and shows here as soon as it is
          built. Hover <em>Source</em> for where it came from. A price update is a listed price the board has
          seen change; check it on the provider&apos;s own page before relying on it.
        </p>
      </header>

      <div className="up-tabs" role="tablist" aria-label="Updates sections">
        {[['news', 'News headlines'], ['manage', 'Manage'], ['info', 'Info']].map(([k, l]) => (
          <button key={k} type="button" role="tab" aria-selected={section === k}
                  className={`up-tab${section === k ? ' on' : ''}`} onClick={() => set('section', k === 'news' ? '' : k)}>
            {l}
          </button>
        ))}
      </div>

      {!data ? <p className="dim">Loading…</p> : section === 'info' ? <Info data={data} /> : (
        <>
          <div className="pc-filters">
            <Chips value={kind} options={kindOptions} counts={kindCounts} onPick={(k) => set('kind', k)} label="Show one kind of update" />
            <label className="up-toggle">
              <input type="checkbox" checked={tracked} onChange={(e) => set('tracked', e.target.checked)} />
              Tracked models only
            </label>
            {section === 'news' && (
              <label className="up-toggle" title="Only the updates a person approved in Manage">
                <input type="checkbox" checked={approvedOnly} onChange={(e) => set('approved', e.target.checked)} />
                Approved only
              </label>
            )}
            <label className="pc-sel">Window
              <select value={data.window_days} onChange={(e) => set('days', Number(e.target.value))}>
                {WINDOWS.filter((n) => n <= data.max_window_days).map((n) => <option key={n} value={n}>{n} days</option>)}
              </select>
            </label>
          </div>
          <p className="dim up-small up-built">
            Built {fmtWhen(data.built_at)} from the board&apos;s data.{' '}
            <button type="button" className="btn btn-ghost up-btn" disabled={busy}
                    onClick={() => { setBusy(true); load().catch(setErr).finally(() => setBusy(false)) }}
                    title="Build the list again from the newest data the board holds. Nothing is collected or paid for.">
              Refresh
            </button>
          </p>
          {data.notes.map((n) => <p key={n} className="dim up-small">{n}</p>)}
          {actErr && <p className="pc-error" role="alert">{actErr}</p>}

          {section === 'news'
            ? <NewsHeadlines data={data} shownItems={list.slice(0, limit)} more={list.length - limit}
                             onMore={() => setLimit((n) => n + PAGE)} act={act} busy={busy} />
            : <Manage data={data} shownItems={list.slice(0, limit)} status={status} setStatus={(s) => set('status', s === 'pending' ? '' : s)}
                      counts={statusCounts} act={act} busy={busy} more={list.length - limit}
                      onMore={() => setLimit((n) => n + PAGE)} />}
        </>
      )}
    </div>
  )
}
