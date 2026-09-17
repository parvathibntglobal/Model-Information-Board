import { useEffect, useState } from 'react'
import { adminDatabase } from '../api'
import { Badge, Notice, Stat } from './ui'
import { IconAlert, IconLayers } from './Icons'

/**
 * Which database this board is talking to, what is in it, and whether its
 * schema matches the migration files in this checkout.
 *
 * ⚠ NO CREDENTIAL AND NO ADDRESS IS SHOWN, and neither is in the payload. The
 *   database NAME is here because it is what answers "is this the one I meant";
 *   the host and port are not, because they are a reachable address and this
 *   page is served over a network. Local or remote is the whole of what is said
 *   about where it lives.
 *
 * WHY MIGRATIONS ARE ON AN ADMIN PAGE AT ALL. The database is shared and hosted
 * and the host auto-deploys, so code can arrive before its schema does. The
 * failure shape is a column that does not exist, raised at request time, on
 * somebody else's machine.
 */

// The ratios are the reading, not the counts. Two pairs carry most of it: how
// much harvested context has actually been read, and how much of what was read
// reached a page.
const RATIOS = [
  {
    label: 'read by the model',
    of: 'thread_extraction',
    per: 'thread_context',
    why: 'Harvested context that a model has actually read. The gap is backlog.',
  },
  {
    label: 'reached the board',
    of: 'board_entry',
    per: 'claim',
    why: 'Claims that became a board entry. The gap is claims still unruled.',
  },
]

export default function DatabasePanel() {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    adminDatabase()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const counts = data?.counts || {}
  const mig = data?.migrations

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Database</span>
        </div>
        {data && <Badge tone={data.read_only_dsn ? 'warn' : 'pass'}>
          {data.read_only_dsn ? 'read-only' : 'writable'}
        </Badge>}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          The database name, which is what tells you this is the one you meant,
          and whether it lives on this machine or a remote one.{' '}
          <strong style={{ color: 'var(--text-1)' }}>
            No credential and no host address is shown
          </strong>
          , and neither is in the payload behind this page.
        </p>
      </div>

      <div className="card-body stack stack-4">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 240 }} />}

        {data && (
          <div className="stack stack-2">
            <div className="grid g2">
              <Stat n={data.database || 'not configured'} l="database" />
              <Stat n={data.host || '—'} l="where it runs" />
              <Stat n={data.environment} l="environment" />
            </div>
            {/* SAID, NOT SILENTLY OMITTED. A reader who goes looking for the
                host should find out that it was withheld on purpose rather
                than conclude the page forgot it. */}
            {data.host_withheld && (
              <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                {/* WHAT IT MEANS, NOT JUST WHAT IT IS. "a remote host" named a
                    category of server and left a reader none the wiser. The
                    consequence is the part worth reading: every query crosses a
                    network, which is why this page has a connection pool. */}
                {data.host !== 'this machine' && (
                  <>Every query crosses a network — about 250ms per round trip
                  from here, which is why the backend pools its connections. </>
                )}
                {data.host_withheld}
              </p>
            )}
            {/* ⚠ THE CAVEAT TRAVELS WITH THE CLAIM. "writable" here means the
                DSN did not ask for read-only — a server-side default or a role
                setting could still refuse a write, and this cannot see either.
                The hour lost to "cannot execute INSERT in a read-only
                transaction" is the reason the distinction is spelled out rather
                than collapsed into the badge. */}
            {data.read_only_note && (
              <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                {data.read_only_note}
              </p>
            )}
          </div>
        )}

        {/* ── the schema ─────────────────────────────────────────────── */}
        {mig && (
          <div className="stack stack-2">
            <div className="row-between">
              <span className="label">Schema — files against the ledger</span>
              {mig.readable && (
                <Badge tone={mig.in_step ? 'pass' : 'fail'}>
                  {mig.in_step ? 'in step' : 'out of step'}
                </Badge>
              )}
            </div>

            {/* ⚠ RULE 4. A ledger that could not be read is SAID so, not shown
                as zero migrations — which would read as "nothing has ever been
                applied", the one thing it does not mean. */}
            {!mig.readable && (
              <Notice icon={<IconAlert />}>
                The migration state could not be read — {mig.why}. This is not a
                statement that no migration has been applied.
              </Notice>
            )}

            {mig.readable && (
              <>
                <div className="grid g2">
                  <Stat n={mig.files_on_disk} l="migration files here" />
                  <Stat n={mig.applied} l="applied to this database" />
                </div>

                {/* THREE WAYS TO DISAGREE, KEPT APART. A single count could not
                    tell them apart: 18 files against 20 applied is not "2
                    pending", and reading it that way is how you go looking for
                    the wrong problem. */}
                <Disagreement
                  names={mig.pending}
                  tone="fail"
                  title="On disk, not applied"
                  why="The database is behind this checkout. Running code will hit a column that does not exist."
                />
                <Disagreement
                  names={mig.applied_not_on_disk}
                  tone="warn"
                  title="Applied, not on disk"
                  why="Another branch reached this database first. Harmless to read from — the schema is ahead, not behind."
                />
                <Disagreement
                  names={mig.drifted}
                  tone="fail"
                  title="Same name, different content"
                  why="A file was edited after it was applied. The database ran something this repo no longer contains, and nothing can say what."
                />

                {!mig.pending?.length && !mig.applied_not_on_disk?.length && !mig.drifted?.length && (
                  <p className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0 }}>
                    Every file here is applied, with matching content.
                  </p>
                )}
              </>
            )}
          </div>
        )}

        {/* ── what is in it ──────────────────────────────────────────── */}
        {data && (
          <div className="stack stack-2">
            <span className="label">Rows</span>
            {RATIOS.map((r) => {
              const of = counts[r.of]
              const per = counts[r.per]
              if (of == null || !per) return null
              return (
                <p key={r.label} className="dim" style={{ fontSize: 'var(--fs-xs)', margin: 0, lineHeight: 1.6 }}>
                  {/* ⚠ RULE 7. The figure travels with its denominator — a bare
                      percentage here would be the same number with the thing it
                      measures removed. */}
                  <strong style={{ color: 'var(--text-1)' }}>
                    {of.toLocaleString()} of {per.toLocaleString()}
                  </strong>{' '}
                  {r.label} ({Math.round((of / per) * 100)}%). {r.why}
                </p>
              )
            })}

            <div className="grid g2" style={{ gap: 'var(--s2)' }}>
              {Object.entries(counts).map(([table, n]) => (
                <div key={table} className="row-between" style={{ gap: 8 }}>
                  <span className="mono" style={{ fontSize: 11 }}>{table}</span>
                  {/* ⚠ RULE 6. ABSENT, NOT ZERO. A table this database does not
                      have reads as "absent"; rendering it as 0 would turn a
                      missing table into an empty one. */}
                  <span style={{ fontSize: 'var(--fs-sm)' }}>
                    {n == null
                      ? <span className="dim" title="This database does not have this table">absent</span>
                      : n.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
            {data.counts_absent_note && (
              <p className="dim" style={{ fontSize: 11, margin: 0 }}>{data.counts_absent_note}</p>
            )}
          </div>
        )}

        {/* ── the column contract ────────────────────────────────────── */}
        {data && (
          <div className="stack stack-2">
            <div className="row-between">
              <span className="label">Column contract</span>
              {data.columns_unreviewed > 0 && (
                <span className="dim" style={{ fontSize: 11 }}>
                  {/* ⚠ RULE 7. The denominator travels with the figure: 256
                      unreviewed is a different fact at 370 columns than at
                      260. */}
                  {data.columns_unreviewed} of {data.columns_total} not yet reviewed
                </span>
              )}
            </div>

            {data.column_states === null ? (
              /* ⚠ RULE 4. Said, not shown as an empty row of zeroes. */
              <Notice icon={<IconAlert />}>
                <span className="mono">contract/column_states.yaml</span> could not
                be read — {data.column_states_unreadable}. No column is being
                claimed either way.
              </Notice>
            ) : (
              <>
                <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
                  {Object.entries(data.column_states || {}).map(([state, n]) => (
                    <span key={state} className="row" style={{ gap: 6, alignItems: 'baseline' }}>
                      <Badge tone={state === 'read' ? 'pass' : state === 'write_only' ? 'warn' : 'mute'}>
                        {state}
                      </Badge>
                      <span className="dim" style={{ fontSize: 11 }}>{n}</span>
                    </span>
                  ))}
                </div>
                {data.column_states_note && (
                  <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                    {data.column_states_note}
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

/**
 * One of the three ways the files and the ledger can disagree — rendered only
 * when it has happened, and always with the names rather than a count alone.
 * "1 pending" sends you to the shell to find out which; the name does not.
 */
function Disagreement({ names, tone, title, why }) {
  if (!names || names.length === 0) return null
  return (
    <div className="stack stack-1">
      <span className="row" style={{ gap: 6, alignItems: 'baseline' }}>
        <Badge tone={tone}>{title}</Badge>
        <span className="dim" style={{ fontSize: 11 }}>{names.length}</span>
      </span>
      <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>{why}</p>
      <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
        {names.map((n) => (
          <li key={n} className="mono" style={{ fontSize: 11 }}>{n}</li>
        ))}
      </ul>
    </div>
  )
}
