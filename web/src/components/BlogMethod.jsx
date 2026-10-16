import { useCallback, useEffect, useRef, useState } from 'react'
import { blogPacks, startBlogPacks } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert } from './Icons'
import '../styles/blog-live.css'

/**
 * ADMIN -> BLOGS: HOW A POST IS MADE, AND THE WRITING PACKS (2026-10-16).
 *
 * The method sits beside the drafts it produced, so a reviewer reads the
 * prompt and the rules where they decide. Everything here comes from the
 * backend (judge/blog_method.py and the same prompt the Prompts panel shows);
 * nothing is restated in this file.
 */

const WHO = { code: ['code', 'mute'], writer: ['writer', 'warn'], person: ['person', 'pass'] }

export function BlogMethod({ method }) {
  if (!method) return null
  const p = method.prompt || {}
  return (
    <details className="fold">
      <summary>
        <span className="label">How a post is made</span>
        <span className="dim" style={{ fontSize: 11 }}>{method.writer_label}</span>
      </summary>
      <div className="stack stack-3" style={{ paddingTop: 'var(--s2)' }}>
        <ol className="bm-steps">
          {method.stages.map((s) => {
            const [label, tone] = WHO[s.who] || [s.who, 'mute']
            return (
              <li key={s.step}>
                <div className="bm-step-head"><b>{s.step}</b> <Badge tone={tone}>{label}</Badge></div>
                <p>{s.what}</p>
                <span className="mono dim bm-where">{s.where}</span>
              </li>
            )
          })}
        </ol>

        <details className="fold">
          <summary><span className="label">The prompt</span>
            <span className="dim" style={{ fontSize: 11 }}>{p.model || ''}{p.format ? ` · shown for the ${p.format} format` : ''}</span>
          </summary>
          {p.unreadable
            ? <p className="dim">The prompt could not be read: {p.unreadable}</p>
            : (
              <div className="stack stack-2" style={{ paddingTop: 'var(--s2)' }}>
                <p className="dim" style={{ fontSize: 11, margin: 0 }}>
                  The STRUCTURE section changes with each format ({(p.formats || []).join(', ')}); the rest is the same for every post.
                </p>
                <span className="label">System</span>
                <pre className="mono prompt-text capped">{p.system}</pre>
                <span className="label">Brief and sources (shape)</span>
                <pre className="mono prompt-text capped">{p.user}</pre>
              </div>
            )}
        </details>

        <details className="fold">
          <summary><span className="label">The rules code checks</span>
            <span className="dim" style={{ fontSize: 11 }}>a draft that breaks one is refused</span>
          </summary>
          <div className="stack stack-2" style={{ paddingTop: 'var(--s2)' }}>
            {method.rules.map((g) => (
              <div key={g.group} className="bm-rules">
                <b>{g.group}</b>
                <ul>{g.items.map((r) => <li key={r}>{r}</li>)}</ul>
                <span className="mono dim bm-where">{g.where}</span>
              </div>
            ))}
          </div>
        </details>
      </div>
    </details>
  )
}

/** The packs Claude Code writes from, and a button to prepare more. */
export function WritingPacks() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const timer = useRef(null)

  const load = useCallback(() => {
    clearTimeout(timer.current)
    blogPacks()
      .then((d) => {
        setData(d)
        setErr(null)
        if (d.run?.running) timer.current = setTimeout(load, 3000)
      })
      .catch((e) => setErr(e.message))
  }, [])
  useEffect(() => { load(); return () => clearTimeout(timer.current) }, [load])

  const prepare = () => {
    setErr(null)
    startBlogPacks(3).then(() => { timer.current = setTimeout(load, 1500) }).catch((e) => setErr(e.message))
  }

  const running = data?.run?.running
  return (
    <div className="stack stack-2 bm-packs">
      <div className="row-between" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="stack" style={{ gap: 2 }}>
          <span className="label">Writing packs</span>
          <span className="dim" style={{ fontSize: 11 }}>
            Code picks the subject and documents and writes each pack; Claude Code writes the post from it; the
            checks run and a passing post appears under Drafts. No model is called here.
          </span>
        </div>
        <button type="button" className="btn btn-primary blog-gen-btn" disabled={running} onClick={prepare}>
          {running ? 'Preparing…' : 'Prepare 3 writing packs'}
        </button>
      </div>
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {data?.run?.log_tail?.length > 0 && (running || data.run.exit_code) && (
        <pre className="mono prompt-text capped">{data.run.log_tail.join('\n')}</pre>
      )}
      {data && data.packs.length === 0 && <p className="dim" style={{ fontSize: 11, margin: 0 }}>No packs yet.</p>}
      {data && data.packs.length > 0 && (
        <div className="tablewrap"><table>
          <thead><tr><th>Subject</th><th>Format</th><th>Documents</th><th>State</th></tr></thead>
          <tbody>
            {data.packs.map((k) => (
              <tr key={k.key}>
                <td>{k.subject}<div className="mono dim" style={{ fontSize: 10 }}>{k.key}</div></td>
                <td className="dim">{k.format}</td>
                <td className="tnum">{k.documents}</td>
                <td>
                  {!k.essay_written ? <Badge tone="mute">waiting for the writer</Badge>
                    : !k.checks ? <Badge tone="warn">written, not checked</Badge>
                    : k.checks.startsWith('0 blocking') ? <Badge tone="pass">passed · {k.checks}</Badge>
                    : <Badge tone="fail">{k.checks}</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </div>
  )
}
