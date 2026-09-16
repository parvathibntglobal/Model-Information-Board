import { useEffect, useState } from 'react'
import { adminKeywords } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconLayers } from './Icons'

/**
 * The search terms each platform is actually sent, per tracked model.
 *
 * COMPOSED, NOT DESCRIBED. The backend reads `model_alias` through the same
 * `_variants_for` the harvest calls, and slices by each arm's real budget — so
 * these are the terms that would go out on the next fetch.
 *
 * ⚠ THE ARMS DO NOT SEARCH ALIKE, and that asymmetry is the reason this page
 *   exists. X gets ONE clubbed query because its quota is a tenth of Reddit's;
 *   Hugging Face gets a single term because it walks repos, then discussions,
 *   then comments. A reader who assumes "the model is searched for" cannot tell
 *   why one platform found nothing.
 *
 * ⚠ AND GITHUB IS NOT A CROSS PRODUCT, which this file claimed until somebody
 *   asked to see the crossed queries. Measured: 1 variant makes 6 requests,
 *   2 makes 6, 3 makes 12 — spellings that normalise together share a request,
 *   and the rest ride along in it to filter the RESULTS rather than being
 *   searched. So GitHub renders its composed queries and every other arm
 *   renders its terms, because for them the term IS the query.
 */

const chip = { fontSize: 11 }

function Terms({ terms }) {
  if (!terms || terms.length === 0) {
    return <span className="dim" style={chip}>— nothing sent to this arm</span>
  }
  return (
    <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
      {terms.map((t, i) => (
        <span key={i} className="mono" style={{
          ...chip, color: 'var(--text-1)', background: 'var(--surface)',
          border: '1px solid var(--border)', borderRadius: 'var(--r2)',
          padding: '2px 7px', wordBreak: 'break-word', maxWidth: '100%',
        }}>{t}</span>
      ))}
    </div>
  )
}

export default function KeywordsPanel() {
  const [state, setState] = useState({ data: null, err: null })
  const [open, setOpen] = useState(null)

  useEffect(() => {
    let alive = true
    adminKeywords()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const arms = data?.arms || []

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Keywords — what each platform is actually sent</span>
        </div>
        {data && <span className="label">{data.count} model(s)</span>}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Read through the same call the harvest makes, so these are the terms that
          would go out on the next fetch.{' '}
          <strong style={{ color: 'var(--text-1)' }}>The arms do not search alike</strong> —
          each takes a different number of terms, for reasons of quota and cost.
        </p>
      </div>

      <div className="card-body stack stack-4">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 220 }} />}

        {arms.length > 0 && (
          <div className="stack stack-2">
            <span className="label">How much each arm gets</span>
            {arms.map((a) => (
              <div key={a.id} className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <span className="mono" style={{ ...chip, color: 'var(--text-3)' }}>{a.stage}</span>
                <strong style={{ fontSize: 'var(--fs-xs)' }}>{a.label}</strong>
                <Badge tone={a.budget === 0 ? 'mute' : 'pass'}>{a.budget_note}</Badge>
                <span className="dim" style={{ fontSize: 11 }}>{a.how}</span>
              </div>
            ))}
            <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
              {data.ordering_note}
            </p>
          </div>
        )}

        {/* THE GITHUB VOCABULARY, which is the one arm that searches for more
            than names. Folded: it is the same for every model, so repeating it
            under each would bury the per-model terms that differ. */}
        {data?.capability_queries?.length > 0 && (
          <details className="disc">
            <summary>
              GitHub also crosses every name with a topic vocabulary
              <span className="n">{data.capability_queries.length} queries · {data.scope.length} repos</span>
            </summary>
            <div className="disc-body stack stack-2">
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch' }}>
                Topic terms say what a post is about; signal terms say what happened.
                Both stances are searched — a capability with only complaints behind
                it is not the same as one nobody has praised.
              </p>
              {data.capability_queries.map((q, i) => (
                <div key={i} className="stack stack-1"
                     style={{ borderLeft: '2px solid var(--line)', paddingLeft: 12 }}>
                  <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
                    <span className="mono" style={chip}>{q.capability}</span>
                    <Badge tone={q.stance === 'positive' ? 'pass' : 'warn'}>{q.stance}</Badge>
                  </div>
                  <span className="dim" style={chip}>topic: {q.topic.join(' · ')}</span>
                  <span className="dim" style={chip}>signal: {q.signal.join(' · ')}</span>
                </div>
              ))}
              <div className="stack stack-1">
                <span className="label">scoped to</span>
                <span className="dim mono" style={chip}>{data.scope.join('  ')}</span>
              </div>
            </div>
          </details>
        )}

        <div className="stack stack-2">
          <span className="label">Per model</span>
          {(data?.models || []).map((m) => (
            <div key={m.name} className="stack stack-1"
                 style={{ borderLeft: '2px solid var(--line)', paddingLeft: 12 }}>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <strong style={{ fontSize: 'var(--fs-sm)' }}>{m.name}</strong>
                {m.searches_nothing
                  ? <Badge tone="fail">searches nothing</Badge>
                  : <span className="label">{m.variants.length} variant(s)</span>}
              </div>

              {/* ⚠ RULE 4. Zero terms is a fetch that searches NOTHING — not a
                  model nobody discusses. Those look identical on a results page
                  and are opposite claims about the world. */}
              {m.searches_nothing && (
                <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', margin: 0 }}>
                  {m.why} A fetch would run and find nothing, and that would be our
                  silence rather than the corpus&rsquo;s.
                </p>
              )}

              {!m.searches_nothing && (
                <>
                  <button type="button" className="chip"
                          onClick={() => setOpen(open === m.name ? null : m.name)}>
                    {open === m.name ? 'Hide the terms' : 'Show what each platform gets'}
                  </button>
                  {open === m.name && (
                    <div className="stack stack-2" style={{ marginTop: 4 }}>
                      {arms.map((a) => (
                        <div key={a.id} className="stack stack-1">
                          <div className="row" style={{ gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                            <span className="mono" style={{ ...chip, color: 'var(--text-3)' }}>{a.stage}</span>
                            <strong style={{ fontSize: 'var(--fs-xs)' }}>{a.label}</strong>
                            {a.id === 'github' && (
                              <span className="label">{m.github_request_count} request(s)</span>
                            )}
                          </div>

                          {/* GITHUB SHOWS THE COMPOSED QUERIES, not the name
                              list. Every other arm searches a bare name, so its
                              terms ARE the query; GitHub crosses each searchable
                              alias with a narrowing token and the repo scope, so
                              the name alone is not what goes out. This was
                              described in prose and the prose was wrong - 3
                              variants make 12 requests, not 18. */}
                          {/* FOLDED, AND ONLY THIS ONE. Every other arm sends
                              a handful of bare names, so its terms fit inline
                              and reading them is the point. GitHub sends a full
                              query per searchable alias per capability entry -
                              twelve for a three-variant model, each carrying
                              five repo scopes - so inline it buries the seven
                              arms under it. Native <details>, so the queries
                              stay in the DOM for ctrl-F whether or not it is
                              open. */}
                          {a.id === 'github' ? (
                            m.github_queries?.length ? (
                              <details className="disc">
                                <summary>
                                  The queries it sends
                                  <span className="n">{m.github_queries.length}</span>
                                </summary>
                                <div className="disc-body stack stack-1">
                                  {m.github_queries.map((q, i) => (
                                    <div key={i} className="stack stack-1"
                                         style={{ borderLeft: '1px solid var(--line)', paddingLeft: 10 }}>
                                      <span className="dim" style={chip}>
                                        {q.entry}
                                        {q.narrowing_token ? ` · narrowed on "${q.narrowing_token}"` : ''}
                                      </span>
                                      <span className="mono" style={{
                                        ...chip, color: 'var(--text-1)', background: 'var(--surface)',
                                        border: '1px solid var(--border)', borderRadius: 'var(--r2)',
                                        padding: '3px 7px', wordBreak: 'break-word',
                                      }}>{q.query}</span>
                                    </div>
                                  ))}
                                </div>
                              </details>
                            ) : (
                              <span className="dim" style={chip}>
                                — no GitHub request could be planned for this model
                              </span>
                            )
                          ) : (
                            <Terms terms={m.per_platform?.[a.id]} />
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
