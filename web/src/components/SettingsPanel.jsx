import { useEffect, useState } from 'react'
import { adminSettings } from '../api'
import { prettyModel } from '../modelNames'
import { Badge, Notice, Stat } from './ui'
import { IconAlert, IconFilter } from './Icons'

/**
 * Who is signed in, what this board is built on, which commit is running, and
 * every operational cap.
 *
 * ⚠ NO SECRET IS SHOWN AND NONE IS IN THE PAYLOAD. Every credential is a
 *   BOOLEAN by the time it leaves the backend — "set" or "not set", never a
 *   value, a prefix, a length or a hash. `AUTH_PASSWORD_HASH` is included in
 *   that rule: a hash of a guessable password is not a safe thing to publish.
 *
 * WHY THE CAPS ARE HERE. "What is the current reading limit?" has been answered
 * by reading source more than once. Each cap also says whether it is the
 * DEFAULT or an OVERRIDE, which is how you would see that a `FETCH_MAX_THREADS`
 * written into a file never reached the running process.
 */

function when(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
}

export default function SettingsPanel() {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    adminSettings()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const acct = data?.account
  const build = data?.build

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconFilter width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Settings</span>
        </div>
        {acct?.signed_in_as && <span className="label">{acct.signed_in_as}</span>}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Read from the running process — the values this backend is actually
          using, not the ones a config file declares.{' '}
          <strong style={{ color: 'var(--text)' }}>
            No key, token or secret is shown here or carried in the payload
          </strong>
          ; a credential appears only as set or not set.
        </p>
      </div>

      <div className="card-body stack stack-4">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 260 }} />}

        {/* ── who is signed in ───────────────────────────────────────── */}
        {acct && (
          <div className="stack stack-2">
            <span className="label">Account</span>
            <div className="grid g2">
              {/* ⚠ RULE 6. A caller holding the shared API_TOKEN has no identity
                  to report, and this says that rather than falling back to the
                  configured address — which would name someone who is not
                  necessarily the person reading the page. */}
              <Stat n={acct.signed_in_as || 'not a named session'} l="signed in as" />
              <Stat n={acct.session_hours + ' h'} l="session length" />
            </div>
            <p className="dim" style={{ fontSize: 11, margin: 0 }}>
              Via {acct.via}.
              {acct.configured_account && acct.configured_account !== acct.signed_in_as
                ? ` The account this backend is configured with is ${acct.configured_account}.`
                : ''}
            </p>

            {/* THE ONE THAT MATTERS ON ANYTHING REACHABLE. The demo signing
                secret is published in the repo, so any token can be forged — a
                fact that is fine locally and never fine on a host. */}
            {acct.on_demo_credentials && (
              <Notice icon={<IconAlert />}>
                Sign-in is using the credentials published in{' '}
                <span className="mono">.env.example</span>. The signing secret is
                public, so any token can be forged — fine locally, never on
                anything reachable.
              </Notice>
            )}

            {data.auth && (
              <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                <Badge tone={data.auth.required ? 'pass' : 'fail'}>
                  {data.auth.required ? 'auth required' : 'open'}
                </Badge>{' '}
                {data.auth.reason}
              </p>
            )}
          </div>
        )}

        {/* ── what it runs on ────────────────────────────────────────── */}
        {data && (
          <div className="stack stack-2">
            <span className="label">Stack</span>
            <div className="grid g2" style={{ gap: 'var(--s2)' }}>
              {Object.entries(data.runtime || {}).map(([name, v]) => (
                <Pair key={name} k={name} v={v} absent="not reported" />
              ))}
              {Object.entries(data.web || {}).map(([name, v]) => (
                <Pair key={name} k={name} v={v} />
              ))}
            </div>
            {/* ⚠ RULE 6 again. A null is "this process could not be asked", not
                "this package is absent" — the two look identical from here, so
                neither is claimed. */}
            <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
              A blank is a version this process could not report, which is not
              the same as a package that is not installed. {data.web_note}
            </p>
          </div>
        )}

        {/* ── which commit ───────────────────────────────────────────── */}
        {/* ⚠ HIDDEN WHERE IT HAS NO ANSWER, WHICH IS THE HOSTED DEPLOYMENT.
            `.dockerignore:55` excludes `.git/` - correctly, it is large and it
            is a supply-chain surface - so the container has no checkout and all
            three fields come back null. Three rows reading "no git checkout to
            read" are worse than no rows at all: they occupy the space an answer
            would, and say nothing, on the one machine where Railway's own
            dashboard already shows the deployed commit.

            NOT DELETED, because locally it answers something nothing else does
            - which commit this backend is actually running - and local is where
            you debug. If it is ever wanted on the deployment, Railway already
            injects RAILWAY_GIT_COMMIT_SHA and RAILWAY_GIT_BRANCH and nothing
            reads them; that is the fix, not removing the block. */}
        {build && (build.commit || build.branch || build.committed_at) && (
          <div className="stack stack-2">
            <div className="row-between">
              <span className="label">Running code</span>
              {build.uncommitted_changes && <Badge tone="warn">uncommitted changes</Badge>}
            </div>
            <div className="grid g2" style={{ gap: 'var(--s2)' }}>
              <Pair k="commit" v={build.commit} absent="no git checkout to read" />
              <Pair k="branch" v={build.branch} absent="no git checkout to read" />
              <Pair k="committed" v={when(build.committed_at)} absent="no git checkout to read" />
            </div>
            {build.uncommitted_changes && (
              <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                The working tree has changes that are not in the commit above, so
                what is running is not exactly what that commit contains.
              </p>
            )}
            {data.build_note && (
              <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                {data.build_note}
              </p>
            )}
          </div>
        )}

        {/* ── the caps ───────────────────────────────────────────────── */}
        {data?.caps && (
          <div className="stack stack-2">
            <span className="label">Operational caps</span>
            <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
              Each is read from this process. A cap marked{' '}
              <em>overridden</em> is one an environment variable changed; the
              default beside it is what the code falls back to — so a value you
              set that is not marked overridden never reached this process.
            </p>
            <div className="stack stack-1">
              {data.caps.map((c) => (
                <div key={c.name} className="row-between" style={{ gap: 12, alignItems: 'baseline' }}>
                  <span className="stack stack-1" style={{ gap: 0 }}>
                    <span className="mono" style={{ fontSize: 11 }}>{c.name}</span>
                    <span className="dim" style={{ fontSize: 10 }}>{c.why}</span>
                  </span>
                  <span className="row" style={{ gap: 6, alignItems: 'baseline', flexShrink: 0 }}>
                    {/* ⚠ THE MODEL CAP READS AS A NAME, THE REST AS NUMBERS.
                        `EXTRACTOR_MODEL` printed the bare id, so the same model
                        was `DeepSeek V4 Flash` on the usage panel and
                        `deepseek/deepseek-v4-flash` here - and neither said
                        WHICH build, while `-0731` sits in the registry looking
                        almost identical. The id stays beside the name; it is
                        what is actually sent and it has not changed. */}
                    {c.name === 'EXTRACTOR_MODEL' && c.value ? (
                      <span className="row" style={{ gap: 6, alignItems: 'baseline' }}>
                        <span style={{ fontSize: 'var(--fs-sm)' }}>{prettyModel(c.value)}</span>
                        <span className="mono dim" style={{ fontSize: 10 }}>{c.value}</span>
                      </span>
                    ) : (
                      <span className="mono" style={{ fontSize: 'var(--fs-sm)' }}>{c.value}</span>
                    )}
                    {c.overridden
                      ? <Badge tone="warn" title={`default ${c.default}`}>overridden</Badge>
                      : <Badge tone="mute">default</Badge>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── credentials, as booleans ───────────────────────────────── */}
        {data?.credentials && (
          <div className="stack stack-2">
            <span className="label">Credentials</span>
            <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
              {data.credentials.map((c) => (
                <span key={c.name} className="row" style={{ gap: 6, alignItems: 'baseline' }}>
                  <span className="mono" style={{ fontSize: 11 }}>{c.name}</span>
                  <Badge tone={c.set ? 'pass' : 'mute'}>{c.set ? 'set' : 'not set'}</Badge>
                </span>
              ))}
            </div>
            <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
              {data.credentials_note}
            </p>
          </div>
        )}

        {/* ── what the model is asked, and the rules it is asked under ──
            READ FROM SOURCE ON EVERY REQUEST, never transcribed. A prompt
            pasted onto an admin page is true the day it is pasted and
            silently wrong afterwards, and the reader it misleads is the one
            person who came here to find the current wording (rule 11).

            `axis_verbatim` has been rewritten twice in a week - once because
            it said "REQUIRED" and "leave this empty" in one paragraph, and
            once to say where a benchmark name stops. A copy would be
            describing neither version by now. */}
        {data?.contract && (
          <div className="stack stack-2">
            <span className="label">What the extractor is asked</span>
            <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
              These descriptions <em>are</em> the prompt: they are sent to the provider as the
              tool-call schema, so this is the instruction itself and not a summary of it. Read
              from <span className="mono">judge/extract/schema.py</span> when this page loaded.
            </p>
            <div className="stack stack-2">
              {(data.contract.extraction_fields || []).map((f) => (
                <details key={`${f.object}:${f.field}`} className="fold">
                  <summary>
                    <span className="mono" style={{ fontSize: 11 }}>{f.field}</span>
                    <Badge tone={f.required ? 'warn' : 'mute'}>
                      {f.required ? 'required' : 'optional'}
                    </Badge>
                    <span className="dim" style={{ fontSize: 11 }}>{f.object}</span>
                  </summary>
                  <p style={{
                    fontSize: 'var(--fs-xs)', lineHeight: 1.65, maxWidth: '82ch',
                    margin: '8px 0 0', color: 'var(--text-2)', whiteSpace: 'pre-wrap',
                  }}>
                    {f.asks}
                  </p>
                </details>
              ))}
            </div>

            <span className="label" style={{ marginTop: 8 }}>The rules this is built under</span>
            {data.contract.rules_source_readable ? (
              <ol className="stack stack-1" style={{
                margin: 0, paddingLeft: '1.4em', fontSize: 'var(--fs-xs)',
                lineHeight: 1.65, color: 'var(--text-2)', maxWidth: '82ch',
              }}>
                {(data.contract.rules || []).map((r) => (
                  <li key={r.n} value={r.n}>{r.rule}</li>
                ))}
              </ol>
            ) : (
              /* RULE 4: SAY THE ABSENCE WAS CAUSED. A container ships the code
                 without the repository, so the file genuinely is not there -
                 which is a different thing from there being no rules, and a
                 blank list would say the second. */
              <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
                <span className="mono">CLAUDE.md</span> is not readable from this process, so the
                rules cannot be listed here. That is this deployment shipping code without the
                repository around it — not an absence of rules.
              </p>
            )}
            <p className="dim" style={{ fontSize: 11, margin: 0, maxWidth: '78ch', lineHeight: 1.6 }}>
              Headlines only. The argument under each rule is what makes it followable and it is
              long; a second copy of it here is the exact failure the rules are about. Read at{' '}
              <span className="mono">{data.contract.read_from_source_at}</span>.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}

/** A name and its value, or the reason there is no value — never a blank. */
function Pair({ k, v, absent }) {
  return (
    <div className="row-between" style={{ gap: 8 }}>
      <span className="mono" style={{ fontSize: 11 }}>{k}</span>
      <span style={{ fontSize: 'var(--fs-sm)' }}>
        {v == null || v === ''
          ? <span className="dim">{absent || 'not reported'}</span>
          : v}
      </span>
    </div>
  )
}
