import { useCallback, useEffect, useRef, useState } from 'react'
import { blogTopics, startTopicHarvest } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert } from './Icons'
import '../styles/blog-live.css'

/**
 * ADMIN -> BLOGS: WHAT THE FIELD IS WRITING ABOUT (2026-10-16).
 *
 * The blog's own harvest - arXiv and the reviewed feeds - grouped by the
 * topics blog_topics.yaml lists (judge/topics.py). Every figure is a count of
 * harvested items; the week against the weeks before is shown as two counts,
 * never a ratio. Emerging phrases are proposals for a person to adopt as
 * topics; code adopts nothing.
 */
export function BlogTopics() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const timer = useRef(null)

  const load = useCallback(() => {
    clearTimeout(timer.current)
    blogTopics()
      .then((d) => {
        setData(d)
        setErr(null)
        if (d.harvest?.running) timer.current = setTimeout(load, 4000)
      })
      .catch((e) => setErr(e.message))
  }, [])
  useEffect(() => { load(); return () => clearTimeout(timer.current) }, [load])

  const harvest = () => {
    setErr(null)
    startTopicHarvest().then(() => { timer.current = setTimeout(load, 2000) }).catch((e) => setErr(e.message))
  }

  const ov = data?.overview
  const running = data?.harvest?.running
  const plan = Object.fromEntries((data?.plan || []).map((p) => [p.key, p]))

  return (
    <details className="fold">
      <summary>
        <span className="label">Topics</span>
        <span className="dim" style={{ fontSize: 11 }}>
          {ov ? `${ov.items} papers and posts harvested · last ${ov.last_harvest ? ov.last_harvest.slice(0, 10) : 'never'}` : 'loading…'}
        </span>
      </summary>
      <div className="stack stack-3" style={{ paddingTop: 'var(--s2)' }}>
        <div className="row-between" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="dim" style={{ fontSize: 11, maxWidth: 560 }}>
            Newest arXiv papers (cs.AI, cs.CL, cs.LG, cs.MA) and every reviewed blog feed, matched to the topics in
            blog_topics.yaml. Several items on one topic make a combined article; one makes an explainer with a quiz.
            No model is called.
          </span>
          <button type="button" className="btn btn-primary blog-gen-btn" disabled={running} onClick={harvest}>
            {running ? 'Harvesting…' : 'Harvest now'}
          </button>
        </div>
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {data?.harvest?.log_tail?.length > 0 && (running || data.harvest.exit_code) && (
          <pre className="mono prompt-text capped">{data.harvest.log_tail.join('\n')}</pre>
        )}
        {ov && ov.items === 0 && <p className="dim" style={{ fontSize: 11, margin: 0 }}>Nothing harvested yet.</p>}
        {ov && ov.items > 0 && (
          <>
            <p className="dim" style={{ fontSize: 11, margin: 0 }}>
              Counted over the last {ov.window_days} days by publication date. Collecting since {ov.collecting_since}:
              the first harvest takes only the newest papers, so this week against the three before means something
              from {ov.trend_meaningful_from}.
            </p>
            <div className="tablewrap"><table>
              <thead><tr>
                <th>Topic</th><th>Items</th><th>This week</th><th>The 3 weeks before</th><th>Can become</th>
              </tr></thead>
              <tbody>
                {ov.topics.filter((t) => t.in_window > 0).map((t) => (
                  <tr key={t.key}>
                    <td>
                      <details>
                        <summary>{t.name}</summary>
                        <ul className="bm-topic-items">
                          {t.items.map((i) => (
                            <li key={i.url}>
                              <a href={i.url} target="_blank" rel="noreferrer">{i.title}</a>{' '}
                              <span className="mono dim">{i.source} · {i.published || 'undated'}</span>
                            </li>
                          ))}
                        </ul>
                      </details>
                    </td>
                    <td className="tnum">{t.in_window}</td>
                    <td className="tnum">{t.this_week}</td>
                    <td className="tnum">{t.prior_three_weeks}</td>
                    <td>
                      {/* RULE 4: a topic that cannot be written yet says why. */}
                      {plan[t.key]?.shape
                        ? <Badge tone={plan[t.key].shape === 'combined article' ? 'pass' : 'mute'}>{plan[t.key].shape}</Badge>
                        : <span className="dim" style={{ fontSize: 11 }}>{plan[t.key]?.why_not || 'not planned'}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            {/* RULE 4: a topic with nothing in the window is named, not dropped. */}
            {ov.silent.length > 0 && (
              <p className="dim" style={{ fontSize: 11, margin: 0 }}>
                <b>Nothing in the window:</b> {ov.silent.join(', ')}.
              </p>
            )}
            <p className="dim" style={{ fontSize: 11, margin: 0 }}>
              {ov.unmatched_in_window} item(s) in the window match no topic.
            </p>
            <div className="stack stack-2">
              <span className="label">Emerging phrases</span>
              <span className="dim" style={{ fontSize: 11 }}>
                Recurring in recent titles and covered by no topic. Adopting one is a person's call: add it to
                blog_topics.yaml.
              </span>
              {data.emerging.length === 0
                ? <p className="dim" style={{ fontSize: 11, margin: 0 }}>None recur often enough yet.</p>
                : (
                  <ul className="bm-emerging">
                    {data.emerging.map((e) => <li key={e.phrase}><b>{e.phrase}</b> <span className="dim">{e.titles} titles</span></li>)}
                  </ul>
                )}
            </div>
          </>
        )}
      </div>
    </details>
  )
}
