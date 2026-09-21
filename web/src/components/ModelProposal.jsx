import { useCallback, useEffect, useRef, useState } from 'react'
import { proposeModel } from '../api'
import { Badge, Notice, Stat } from './ui'
import { IconAlert } from './Icons'

/**
 * Change what the board tracks — add a model, stop tracking one, or bring back
 * one that was dropped.
 *
 * ⚠ NOTHING HERE WRITES. Not the contract, not a row, not an alias. The board's
 *   model list lives in `contract/tracked_models.yaml` — versioned config, rule
 *   5 — so the change ends in a commit somebody reviews. What this does is the
 *   tedious, checkable half: derive every spelling a person might type, count
 *   what the corpus already attests, find collisions with aliases that are
 *   already live, and compose the exact YAML.
 *
 *   A button that wrote the list from here would put it in two places that can
 *   disagree — and on the deployment the filesystem is ephemeral, so the edit
 *   would die at the next deploy while any rows it caused survived.
 *
 * ⚠ "DELETE" IS THE WRONG WORD, SO NO CONTROL USES IT. `model_alias` is
 *   append-only under FR-4 with no undo, and every claim, entry and document
 *   stays. What changes is one list. The panel counts what survives rather than
 *   asserting it — which is also what makes bringing a model back cheap.
 */

//: ⚠ "ADD A MODEL" WAS BUILT AND REMOVED, AND THE REASON IS NOT A DEFECT.
//:
//:   It only ever worked for a model the registry already held - anything newer
//:   needs a `model_version` row first, which the OpenRouter poll brings or a
//:   seed contract seats, and neither is a button. And even for a model that IS
//:   in the registry, the entry lands in `contract/tracked_models.yaml`, so it
//:   took a commit and a redeploy before the board showed it. Long enough that
//:   the control read as broken: it said "Add this model" and the models page
//:   still said 13.
//:
//:   Tracked membership probably belongs in the database rather than in YAML -
//:   then add and remove are instant and a delete is honest, because a tracked
//:   row is list membership rather than evidence. That is a migration to a
//:   shared database and a change to who can alter the board, so it is its own
//:   decision. See the issue.
//:
//:   The two that remain need the same commit, but neither pretends otherwise.
const TABS = [
  { id: 'untrack', label: 'Stop tracking' },
  { id: 'recall', label: 'Bring one back' },
]

export default function ModelProposal({ models }) {
  const [tab, setTab] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState(null)
  const [recall, setRecall] = useState(null)
  // What a confirmation is currently ASKING about. `null` means no dialog.
  const [pending, setPending] = useState(null)

  const run = useCallback((payload) => {
    setBusy(true); setErr(null); setResult(null)
    return proposeModel(payload)
      .then((d) => setResult(d))
      .catch((e) => setErr(e.message))
      .finally(() => setBusy(false))
  }, [])

  // The recall list is a read with no inputs, so it loads when its tab opens
  // rather than making you press a button to see a list.
  useEffect(() => {
    if (tab !== 'recall' || recall) return
    proposeModel({ action: 'recallable' })
      .then(setRecall)
      .catch((e) => setErr(e.message))
  }, [tab, recall])

  const open = (next) => {
    setTab(tab === next ? null : next)
    setResult(null); setErr(null)
  }

  return (
    <div className="stack stack-3">
      <div className="stack stack-1">
        <span className="label">Change what the board tracks</span>
        <span className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', lineHeight: 1.6 }}>
          Both <strong style={{ color: 'var(--text)' }}>write nothing</strong>.
          They work out what the change would mean and hand you the exact contract
          edit — the commit and a deploy are what make it real, so the board does
          not change while you are looking at it.
        </span>
      </div>

      {/* THE SAME CHIP VOCABULARY AS EVERY OTHER CONTROL ON THIS SITE, and at
          the TOP of the section: these are what you came here to do that is not
          "run a fetch", and they were previously below thirteen model folds. */}
      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }} role="tablist"
           aria-label="Change what the board tracks">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
                  className={`chip${tab === t.id ? ' chip-on' : ''}`}
                  onClick={() => open(t.id)}>
            {t.label}
            {t.id === 'recall' && recall?.count > 0 && (
              <span className="x">{recall.count}</span>
            )}
          </button>
        ))}
      </div>

      {tab === 'untrack' && (
        <div className="stack stack-2" role="tabpanel">
          <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
            {(models || []).map((m) => (
              <button key={m.model_version_id} type="button" className="chip" disabled={busy}
                      onClick={() => setPending({
                        action: 'untrack',
                        registry: m.canonical_id || m.model_version_id,
                        name: m.display_name || m.model_version_id,
                        verb: 'Stop tracking',
                      })}>
                {m.display_name || m.model_version_id}
              </button>
            ))}
          </div>
          <span className="dim" style={{ fontSize: 11, maxWidth: '78ch', lineHeight: 1.6 }}>
            Stop tracking, not delete. Nothing is removed from the database — the
            registry row, the aliases and every piece of evidence stay, because
            <span className="mono"> model_alias</span> is append-only and has no
            undo. What changes is which models the board lists.
          </span>
        </div>
      )}

      {tab === 'recall' && (
        <div className="stack stack-2" role="tabpanel">
          {!recall && <div className="skel" style={{ height: 70 }} />}

          {/* ⚠ RULE 4. No git checkout is not an empty list, and rendering it as
              one would say "nothing was ever dropped" — the opposite of what is
              known. The deployment's image excludes `.git/`, so this is the
              expected answer there rather than a fault. */}
          {recall && !recall.readable && (
            <Notice icon={<IconAlert />}>{recall.why}</Notice>
          )}

          {recall?.readable && recall.count === 0 && (
            <p className="dim" style={{ fontSize: 'var(--fs-sm)', margin: 0 }}>
              Nothing has been dropped: all {recall.ever_tracked} models the list
              has ever held are still on it.
            </p>
          )}

          {recall?.readable && recall.count > 0 && (
            <>
              <div className="stack stack-1">
                {recall.models.map((m) => (
                  <div key={m.registry} className="row-between"
                       style={{ gap: 12, alignItems: 'baseline', flexWrap: 'wrap' }}>
                    <span className="stack stack-1" style={{ gap: 0 }}>
                      <span className="row" style={{ gap: 8, alignItems: 'baseline' }}>
                        <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.name}</strong>
                        <span className="mono dim" style={{ fontSize: 11 }}>{m.registry}</span>
                      </span>
                      {/* WHAT COMES BACK WITH IT. A recall does not re-harvest:
                          the evidence never left, so this says whether bringing
                          it back lands on a page with something on it. */}
                      <span className="dim" style={{ fontSize: 10 }}>
                        {m.survives.board_entry} board entr
                        {m.survives.board_entry === 1 ? 'y' : 'ies'} ·{' '}
                        {m.survives.model_alias} alias(es) ·{' '}
                        {m.survives.runs} run(s) still here
                        {m.in_registry ? '' : ' · no registry row'}
                      </span>
                    </span>
                    <button type="button" className="chip" disabled={busy}
                            onClick={() => setPending({
                              action: 'add', registry: m.registry, name: m.name,
                              kind: m.kind, verb: 'Bring back', recalled: true,
                            })}>
                      Bring back
                    </button>
                  </div>
                ))}
              </div>
              <span className="dim" style={{ fontSize: 11, maxWidth: '78ch', lineHeight: 1.6 }}>
                {/* ⚠ RULE 7. Six of how many, read from how much history. */}
                {recall.count} dropped of {recall.ever_tracked} the list has ever
                held, across {recall.commits_read} commits; {recall.currently_tracked}{' '}
                tracked now. {recall.note}
              </span>
            </>
          )}
        </div>
      )}

      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {result && <Proposal p={result} />}

      <Confirm
        pending={pending}
        onCancel={() => setPending(null)}
        onConfirm={() => {
          const { verb, recalled, ...payload } = pending  // eslint-disable-line no-unused-vars
          setPending(null)
          run(payload)
        }}
      />
    </div>
  )
}

/**
 * The second press. Never a single click, for either direction.
 *
 * ⚠ AND IT SAYS WHAT IT WILL NOT DO, which is the unusual part. Nothing here
 *   writes, so this is not guarding a change — it is guarding against a misclick
 *   producing a confident-looking proposal for the wrong model, and it is the
 *   place to state plainly that the commit is still yours to make. A dialog that
 *   only said "Are you sure?" would imply something irreversible was about to
 *   happen, which would be its own small lie.
 *
 * Native `<dialog>` + `showModal()`: focus trapping, Escape, an inert page
 * behind it and a real backdrop, none of which a div with a z-index gets for
 * free — and it announces itself as a dialog with no aria plumbing.
 */
function Confirm({ pending, onCancel, onConfirm }) {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (pending && !el.open) el.showModal()
    if (!pending && el.open) el.close()
  }, [pending])

  const untrack = pending?.action === 'untrack'

  return (
    <dialog
      ref={ref}
      className="confirm"
      aria-labelledby="confirm-title"
      // Escape fires `cancel`, and the backdrop click fires nothing — so the
      // close path has to be wired or the dialog can be dismissed with React
      // still believing it is open.
      onCancel={(e) => { e.preventDefault(); onCancel() }}
      onClose={onCancel}
    >
      {pending && (
        <>
          <div className="confirm-body">
            <strong id="confirm-title" style={{ fontSize: 'var(--fs-sm)' }}>
              {pending.verb} {pending.name || pending.registry}?
            </strong>
            <span className="mono dim" style={{ fontSize: 11 }}>{pending.registry}</span>

            <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, lineHeight: 1.6 }}>
              {untrack
                ? 'This works out what dropping it would remove from the board '
                  + 'and what would stay in the database. Nothing is deleted and '
                  + 'nothing is written — you get the exact contract edit, and '
                  + 'the commit is what makes it real.'
                : 'This works out the search spellings, checks them against '
                  + 'aliases that are already live, and composes the contract '
                  + 'entry. Nothing is written — the commit is what makes it '
                  + 'real.'}
            </p>

            {pending.recalled && (
              <p className="dim" style={{ fontSize: 11, margin: 0, lineHeight: 1.6 }}>
                Its evidence never left, so bringing it back does not re-harvest
                anything.
              </p>
            )}

            {/* ⚠ THE SURPRISE THAT REMOVED THE ADD TAB, SAID HERE SO IT CANNOT
                HAPPEN AGAIN. A control called "Add this model" produced a
                proposal and the models page still said 13 - because the entry
                lands in a contract file and the board reads it through an
                lru_cache. Both remaining controls need the same commit, and
                both now say so before you press anything. */}
            <p style={{ fontSize: 11, margin: 0, lineHeight: 1.6, color: 'var(--warn)' }}>
              The board will not change until the contract edit is committed and
              deployed. This composes the edit; it does not apply it.
            </p>
          </div>
          <div className="confirm-actions">
            <button type="button" className="chip" onClick={onCancel}>Cancel</button>
            <button type="button" className="chip chip-on" onClick={onConfirm}>
              {pending.verb}
            </button>
          </div>
        </>
      )}
    </dialog>
  )
}

const INPUT = {
  height: 32, padding: '0 10px', borderRadius: 'var(--r-sm)',
  border: '1px solid var(--border)', background: 'var(--surface)',
  fontSize: 'var(--fs-xs)', minWidth: 190,
}

function Proposal({ p }) {
  return (
    <section className="card" style={{ padding: 'var(--s3)' }}>
      <div className="stack stack-3">
        <div className="row" style={{ gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
          <Badge tone="mute">
            {p.action === 'add' ? 'would add' : 'would stop tracking'}
          </Badge>
          <strong style={{ fontSize: 'var(--fs-sm)' }}>{p.name || p.registry}</strong>
          <span className="mono dim" style={{ fontSize: 11 }}>{p.registry}</span>
          {p.wrote_nothing && <Badge tone="pass">nothing was written</Badge>}
        </div>

        {p.action === 'add' && <AddProposal p={p} />}
        {p.action === 'untrack' && <UntrackProposal p={p} />}
      </div>
    </section>
  )
}

function AddProposal({ p }) {
  const missing = Object.entries(p.renderings || {}).filter(([, v]) => !v)
  const attested = (p.attestation?.counts || []).reduce((n, c) => n + c.quotes, 0)

  return (
    <>
      {/* ⚠ THE BLOCKING FACT FIRST. A model with no registry row cannot be
          fetched at all — a run is filed under a model_version_id — so this is
          said here rather than left for the first empty fetch to reveal. It is
          exactly why Gemini 3.8 Flash showed no runs. */}
      {p.blocking && <Notice icon={<IconAlert />}>{p.blocking}</Notice>}

      {/* ⚠ THE ONE HARD FAILURE. An alias that already resolves to a different
          model does not add evidence, it MISFILES it — and model_alias is
          append-only, so there is no undo. */}
      {(p.collisions || []).length > 0 && (
        <Notice icon={<IconAlert />}>
          {p.collisions.length} spelling(s) are already live for a different model:{' '}
          {p.collisions.map((c) => `${c.variant} → ${c.held_by}`).join(', ')}.
          Adding these would misfile evidence, and aliases cannot be withdrawn.
        </Notice>
      )}

      <div className="grid g2">
        <Stat n={p.already_tracked ? 'yes' : 'no'} l="already on the board" />
        <Stat n={p.in_registry ? 'yes' : 'no'} l="has a registry row" />
      </div>

      <div className="stack stack-1">
        <span className="label">Search spellings — derived, not invented</span>
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          {(p.variants || []).map((v) => (
            <span key={v} className="mono" style={CHIP}>{v}</span>
          ))}
        </div>
        {missing.length > 0 && (
          <span style={{ fontSize: 11, color: 'var(--warn)' }}>
            No {missing.map(([k]) => k).join(' or ')} rendering. The loader
            refuses a model that cannot be found by all three, so this name would
            not seat as written.
          </span>
        )}
      </div>

      <div className="stack stack-1">
        <span className="label">Already attested — {attested} quote(s)</span>
        {/* ⚠ RULE 4 AND RULE 7 TOGETHER. Zero means "not in the extracted
            quotes", NOT "nobody writes this" — the raw document text is in a
            per-machine store this backend cannot read. Opposite claims, and
            only one of them is about the world. */}
        <span className="dim" style={{ fontSize: 11, maxWidth: '78ch', lineHeight: 1.6 }}>
          {p.attestation?.note}
        </span>
      </div>

      <Paste
        label="Add this to contract/tracked_models.yaml, then commit"
        text={p.contract_entry}
      />
    </>
  )
}

function UntrackProposal({ p }) {
  const stays = Object.entries(p.stays || {}).filter(([, n]) => n > 0)
  return (
    <>
      {!p.tracked && (
        <Notice icon={<IconAlert />}>
          This id is not in the tracked list, so there is nothing to remove.
        </Notice>
      )}

      <div className="stack stack-1">
        <span className="label">What stays — none of this is deleted</span>
        <div className="grid g2" style={{ gap: 'var(--s2)' }}>
          {stays.map(([table, n]) => (
            <div key={table} className="row-between" style={{ gap: 8 }}>
              <span className="mono" style={{ fontSize: 11 }}>{table}</span>
              <span style={{ fontSize: 'var(--fs-sm)' }}>{n.toLocaleString()}</span>
            </div>
          ))}
        </div>
        <span className="dim" style={{ fontSize: 11, maxWidth: '78ch', lineHeight: 1.6 }}>
          {p.stays_note} You can put it back from “Bring one back”.
        </span>
      </div>

      {p.remove_lines && (
        <Paste
          label="Remove these lines from contract/tracked_models.yaml, then commit"
          text={p.remove_lines}
        />
      )}
    </>
  )
}

/**
 * The exact text to paste, and a button to copy it.
 *
 * Shown as well as copyable: a control that only copies asks a reader to trust
 * what went to the clipboard, and the whole point of this panel is that the
 * change is reviewable before it is made.
 */
function Paste({ label, text }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="stack stack-1">
      <div className="row-between">
        <span className="label">{label}</span>
        <button
          type="button"
          className="chip"
          onClick={() => {
            // `navigator.clipboard` is absent over plain http on some browsers
            // and rejects without a user gesture on others. Failing silently
            // would leave a reader believing they had copied something.
            Promise.resolve(navigator.clipboard?.writeText(text))
              .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
              .catch(() => setCopied(false))
          }}
        >
          {copied ? 'copied' : 'copy'}
        </button>
      </div>
      <pre className="mono" style={{
        margin: 0, padding: 'var(--s2)', borderRadius: 'var(--r-sm)',
        background: 'var(--surface-2)', border: '1px solid var(--border)',
        fontSize: 11, overflowX: 'auto', whiteSpace: 'pre',
      }}>{text}</pre>
    </div>
  )
}

const CHIP = {
  fontSize: 11, padding: '3px 8px', borderRadius: 'var(--r-pill)',
  border: '1px solid var(--border)', background: 'var(--surface-2)',
  color: 'var(--text-2)',
}
