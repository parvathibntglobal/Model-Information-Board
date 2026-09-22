import { Fragment, useEffect, useState } from 'react'
import { adminSources } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconCaret, IconLayers } from './Icons'

/**
 * Every platform the harvest reaches, and how it reaches it.
 *
 * THE LIST COMES FROM THE CONTRACT. `/admin/sources` reads
 * `contract/sources.yaml` — the same file the harvest reads — so a platform
 * added there appears here without an edit to this component.
 *
 * ⚠ NO CREDENTIAL IS SHOWN. Not the key, not a fingerprint, not a prefix. The
 *   page says "uses a key" or "no key" and nothing else, because a page that
 *   shows even part of a credential has published it.
 *
 * WHY "PAID" IS RENDERED AS "METERED". What is measurable is that an arm draws
 * down a RapidAPI quota, which `collect/usage.py` records. The price per
 * request is not in our config, so a dollar figure here would be invented.
 */

// A method is a claim about money or about somebody's terms, so each gets a
// tone rather than all rendering alike: paid access and a robots-gated fetch
// are the two a reader should look at twice.
const METHOD_TONE = (m) => {
  if (!m) return 'fail'
  if (m.startsWith('paid')) return 'warn'
  if (m.startsWith('free')) return 'pass'
  return 'mute'
}

export default function SourcesPanel() {
  const [state, setState] = useState({ data: null, err: null })
  // Which platform's prose is open. One at a time: these are read to answer a
  // question about ONE row, and several open at once rebuilds the wall of
  // paragraphs the table replaced.
  const [open, setOpen] = useState(null)

  useEffect(() => {
    let alive = true
    adminSources()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const sources = data?.sources || []
  const feeds = data?.blog_feeds || []

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Sources — where the evidence comes from</span>
        </div>
        {data && <span className="label">{data.count} platform(s)</span>}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Read from <span className="mono">contract/sources.yaml</span>, the same file
          the harvest reads — so this is what actually runs, not a description of it.
          Each row says how the platform is reached and whether a key is used.{' '}
          <strong style={{ color: 'var(--text)' }}>No key is shown anywhere</strong>,
          and none is in the payload behind this page.
        </p>
      </div>

      <div className="card-body stack stack-3">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 180 }} />}

        {data?.by_method && (
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            {Object.entries(data.by_method).map(([method, ids]) => (
              <span key={method} className="row" style={{ gap: 6, alignItems: 'baseline' }}>
                <Badge tone={METHOD_TONE(method)}>{method}</Badge>
                <span className="dim" style={{ fontSize: 11 }}>{ids.length}</span>
              </span>
            ))}
          </div>
        )}

        {/* A TABLE, BECAUSE THE QUESTION IS A COMPARISON. Every row answers the
            same four questions - how is it reached, does it use a key, is it
            metered, have its terms been read - and the answers were buried in
            four paragraphs each, one platform after another. Twelve platforms
            made a page you had to read rather than scan, to compare things that
            differ in one column.

            The prose is not deleted; it moves behind the caret. The detail, the
            credential note and the ruling are what you read about ONE platform
            after the table has told you which one to look at. */}
        {sources.length > 0 && (
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>How it is reached</th>
                  <th>Key</th>
                  <th>Quota</th>
                  <th>Terms</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <Fragment key={s.id}>
                    <tr>
                      <td>
                        <button type="button" className="rowtoggle"
                                aria-expanded={open === s.id}
                                onClick={() => setOpen(open === s.id ? null : s.id)}>
                          <IconCaret width={13} height={13}
                                     className={`caret${open === s.id ? ' on' : ''}`} />
                          <strong>{s.id}</strong>
                        </button>
                      </td>
                      <td>
                        {s.method
                          ? <Badge tone={METHOD_TONE(s.method)}>{s.method}</Badge>
                          : <Badge tone="fail">not described</Badge>}
                      </td>
                      {/* THE WHOLE OF WHAT IS SAID ABOUT CREDENTIALS. Not the
                          key, not a fingerprint, not a prefix. */}
                      <td className="dim">{s.uses_credential ? 'uses a key' : 'no key'}</td>
                      <td>
                        {s.metered
                          ? <Badge tone="warn">metered</Badge>
                          : <span className="dim">unmetered</span>}
                      </td>
                      {/* ⚠ RULE 4. `terms_document_read: false` means NOBODY HAS
                          READ the platform's terms document - not that it was
                          read and found wanting. Two opposite claims, and only
                          one of them is about the platform, so the cell says
                          "not read by us" rather than anything shorter. */}
                      <td>
                        {s.terms_document_read === false
                          ? <span style={{ color: 'var(--warn)', fontSize: 'var(--fs-xs)' }}>
                              not read by us
                            </span>
                          : s.terms_reviewed_on
                            ? <span className="dim mono" style={{ fontSize: 11 }}>
                                {s.terms_reviewed_on}
                              </span>
                            : <span className="dim">—</span>}
                      </td>
                    </tr>

                    {open === s.id && (
                      <tr>
                        <td colSpan={5} style={{ background: 'var(--surface-2)' }}>
                          <div className="stack stack-1">
                            {s.detail && (
                              <p className="muted" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
                                {s.detail}
                              </p>
                            )}
                            {s.credential_note && (
                              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
                                {s.credential_note}
                              </p>
                            )}
                            {s.terms_document_read === false && (
                              <p style={{ fontSize: 11, color: 'var(--warn)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
                                The platform&rsquo;s terms document has not been read. That is
                                an absence on our side, not a finding about them — what was
                                checked is in the ruling below.
                              </p>
                            )}
                            {s.undescribed && (
                              <Notice icon={<IconAlert />}>
                                This platform is in the contract and this page has not been
                                taught how it is reached. Unknown, which is different from
                                &ldquo;no key&rdquo;.
                              </Notice>
                            )}
                            <span className="dim mono" style={{ fontSize: 11 }}>
                              {s.endpoint || 'no single endpoint — feed-based'}
                            </span>

                            {/* ⚠ THE FEEDS BELONG IN THIS ROW'S OWN DROPDOWN,
                                and the first version put them in a separate
                                table further down the page. A reader looking
                                for "which blogs" opens the blogs row - that is
                                what the caret is for - and finding the answer
                                somewhere else on the page is the same as not
                                finding it.

                                `blogs` is the only platform with feeds under
                                it, so this is keyed on the id rather than on
                                the list being non-empty: if `feeds` ever
                                arrives empty, the row should say so here
                                rather than silently render nothing. */}
                            {s.id === 'blogs' && <BlogFeeds data={data} feeds={feeds} />}
                            <span className="dim mono" style={{ fontSize: 11 }}>
                              ruling {s.terms_ruling || '—'}
                              {s.terms_reviewed_on ? ` · reviewed ${s.terms_reviewed_on}` : ''}
                              {s.evidence ? ` · ${s.evidence}` : ''}
                            </span>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* DRIFT IN THE OTHER DIRECTION. A platform described here but absent
            from the contract would otherwise look live. */}
        {data?.described_but_not_in_contract?.length > 0 && (
          <Notice icon={<IconAlert />}>
            Described but not in the contract, so nothing harvests them:{' '}
            {data.described_but_not_in_contract.join(', ')}
          </Notice>
        )}

        {data && (
          <span className="dim" style={{ fontSize: 11 }}>{data.credentials_note}</span>
        )}
      </div>
    </section>
  )
}

/** The blog feeds seated in the contract, inside the `blogs` row's dropdown.
 *
 * ⚠ WHERE THIS RENDERS IS THE WHOLE POINT, and the first version got it
 *   wrong. The feeds were a separate table below the platform list, so a
 *   reader who opened the blogs row - which is exactly what the caret invites
 *   - saw the platform's endpoint and nothing else, and reported that the
 *   feeds were not there. They were, six hundred pixels down.
 *
 *   An answer in the wrong place is not a smaller version of the right
 *   answer. It is the same as no answer, and the reader is the one who
 *   discovers that.
 *
 * THE COUNT IS WHY IT IS WORTH RENDERING, not the list of names. Two of the
 * eighteen have harvested nothing and `swyx.io` alone is 432 documents,
 * roughly a third of the blog corpus. A list of names says neither.
 */
function BlogFeeds({ data, feeds }) {
  if (!feeds.length) {
    // RULE 4. The contract carrying no feeds is a state worth naming; an
    // empty dropdown would read as a component that failed to load.
    return (
      <p className="dim" style={{ fontSize: 11, margin: 0 }}>
        No feeds are seated in <span className="mono">contract/sources.yaml</span>.
      </p>
    )
  }
  const totalDocs = feeds.reduce((t, f) => t + (f.documents || 0), 0)
  return (
          <div className="stack stack-2">
            <div className="row-between">
              <span className="label">Blog feeds seated in the contract</span>
              <span className="label">
                {feeds.length} feed{feeds.length === 1 ? '' : 's'}
                {data.blog_counts_unreadable ? '' : ` · ${totalDocs.toLocaleString()} documents`}
              </span>
            </div>

            {/* RULE 6. A count we could not take is not a zero, and the page
                must not print one. */}
            {data.blog_counts_unreadable && (
              <Notice icon={<IconAlert />}>
                The per-feed document counts could not be read, so they are shown as
                <strong> unknown</strong> rather than zero: {data.blog_counts_unreadable}
              </Notice>
            )}

            <div className="tblwrap">
              <table>
                <thead>
                  <tr>
                    <th>Feed</th>
                    <th className="r">Documents</th>
                    <th>Byline</th>
                    <th>Terms</th>
                  </tr>
                </thead>
                <tbody>
                  {feeds.map((f) => (
                    <tr key={f.id}>
                      <td>
                        <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
                          {/* The site, not the feed URL: a reader checking a
                              claim wants the blog, and the endpoint is an
                              atom file. Both are public; neither is a key. */}
                          {f.site
                            ? (
                              <a href={f.site} target="_blank" rel="noopener noreferrer"
                                 className="mono" style={{ fontSize: 11 }}>
                                {f.id.replace(/^blog:/, '')}
                              </a>
                            )
                            : <span className="mono" style={{ fontSize: 11 }}>{f.id.replace(/^blog:/, '')}</span>}
                          {f.provenance === 'seed' && <Badge tone="mute">seed</Badge>}
                        </div>
                      </td>
                      <td className="r">
                        {f.documents == null
                          ? <span className="dim">unknown</span>
                          : (
                            <>
                              {f.documents.toLocaleString()}
                              {/* RULE 7. `medium.com/airbnb-engineering` is one
                                  feed on a host the harvester keys by, so this
                                  number is the host's and the row says so
                                  rather than claiming it. */}
                              {f.count_is_for_the_host && (
                                <span className="dim" title="Counted by host, which this feed shares with another">
                                  {' '}· host
                                </span>
                              )}
                            </>
                          )}
                      </td>
                      <td>
                        {/* ⚠ `entry` IS THE ONE WITH A KNOWN DEFECT (#373):
                            several voices in one run, so the author row is
                            written and nothing links a document to it. Marked
                            here so the affected feeds are visible without
                            opening the issue. */}
                        {f.byline_source === 'entry'
                          ? <Badge tone="warn">entry</Badge>
                          : <span className="dim" style={{ fontSize: 11 }}>{f.byline_source || 'not recorded'}</span>}
                      </td>
                      <td>
                        {/* RULE 4, the same as the platform rows above: `false`
                            means nobody has read the terms document, NOT that
                            it was read and found wanting. */}
                        <span className="dim" style={{ fontSize: 11 }}>
                          {f.terms_document_read === true
                            ? 'document read'
                            : f.terms_document_read === false
                              ? 'robots only'
                              : 'not recorded'}
                          {f.terms_reviewed_on ? ` · ${f.terms_reviewed_on}` : ''}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="dim" style={{ fontSize: 11, maxWidth: '78ch', lineHeight: 1.6, margin: 0 }}>
              Read from <span className="mono">contract/sources.yaml</span> when this page
              loaded; the counts are live from <span className="mono">document</span>.
              A feed reading <strong>0</strong> is seated and has harvested nothing — which
              is a measurement, not a gap. <strong>entry</strong> under Byline marks the
              feeds whose author rows are written and linked to nothing (#373).
            </p>
          </div>
  )
}
