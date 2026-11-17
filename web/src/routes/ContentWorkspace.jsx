import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  contentDraftCheck, contentDraftCreate, contentDraftUpdate, contentNoteCreate, contentNoteHistory,
  contentNoteUpdate, contentPlatform, contentPlatforms, contentSuggestions,
} from '../api'
import { IconAlert } from '../components/Icons'
import { Notice } from '../components/ui'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import '../styles/content-workspace.css'

/**
 * Content workspace (Admin -> Content workspace, 2026-11-17).
 *
 * One place per platform to write posts that bring people to the site:
 * the platform's philosophy, research, rules and recommendations (all
 * editable, every edit kept), coded topic suggestions read from the board,
 * and drafts a PERSON writes, each checked against the platform's rules.
 *
 * Nothing here posts anywhere, and nothing here calls a model (phase 1). The
 * fit check blocks nothing: its word lists and patterns are unmeasured
 * (rule 8), so it reports counts of rules met, never a score (rule 3).
 * Backend: judge/content_workspace/, in its own database.
 */

const TABS = [
  ['philosophy', 'Philosophy'],
  ['research', 'Research'],
  ['rule', 'Rules'],
  ['recommendation', 'Recommendations'],
  ['topics', 'Topics'],
  ['drafts', 'Drafts'],
]
const NOTE_TABS = new Set(['philosophy', 'research', 'rule', 'recommendation'])
const NOTE_INTRO = {
  philosophy: 'What the platform is for and what its people value. From anooj’s framework, our studies and the external research.',
  research: 'Findings with their source, population and date. Where the two research files disagree, the note says so.',
  rule: 'What every post here is checked against. A rule names a coded check, or "manual" for a person to tick. Rules marked "All platforms" apply everywhere; a platform’s own rule on the same check replaces them.',
  recommendation: 'What to do on this platform, and in what order.',
}
const OUTCOME_LABEL = { pass: 'Met', warn: 'Warning', fail: 'Missed', manual: 'By hand', unchecked: 'Not checked' }
const TITLED = new Set(['text_post', 'link_submission', 'show_hn', 'newsletter_issue', 'article',
  'video_metadata', 'shorts_metadata', 'readme', 'discussion_post', 'release_notes'])

const pretty = (s) => String(s || '').replace(/_/g, ' ')
const when = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '')

export default function ContentWorkspace() {
  useHead(PRIVATE.contentWorkspace)
  const [params, setParams] = useSearchParams()
  const [meta, setMeta] = useState(null)
  const [err, setErr] = useState(null)

  const loadMeta = useCallback(() => contentPlatforms()
    .then((d) => { setMeta(d); setErr(null) })
    .catch((e) => setErr(e.message)), [])
  useEffect(() => { loadMeta() }, [loadMeta])

  const key = params.get('p') || meta?.platforms?.[0]?.key
  const tab = TABS.some(([t]) => t === params.get('t')) ? params.get('t') : 'philosophy'
  const go = (next) => setParams({ p: key, t: tab, ...next }, { replace: true })

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <Link to="/admin" className="mb-link" style={{ fontSize: 'var(--fs-xs)' }}>← Back to Admin</Link>
        <span className="eyebrow">Admin · Content</span>
        <h1 style={{ fontSize: 'var(--fs-h2)' }}>Content workspace</h1>
        <p className="muted" style={{ maxWidth: '75ch' }}>
          Write posts for each platform, guided by what it values and what the board can show. People
          write every post; the topic suggestions are coded from the board’s data, and each draft is
          checked against the platform’s rules. Nothing here posts anywhere.
        </p>
      </div>
      {err && !meta && <Notice icon={<IconAlert />}>The workspace could not be read: {err}</Notice>}
      {!meta && !err && <div className="skel" style={{ height: 240 }} />}
      {meta && (
        <div className="cw-grid">
          <PlatformList platforms={meta.platforms} active={key} onPick={(p) => setParams({ p, t: tab }, { replace: true })} />
          {key && (
            <PlatformPanel
              key={key}
              platformKey={key}
              meta={meta}
              tab={tab}
              draftId={params.get('d')}
              go={go}
              onDraftsChanged={loadMeta}
            />
          )}
        </div>
      )}
    </div>
  )
}

function PlatformList({ platforms, active, onPick }) {
  return (
    <nav className="cw-platforms" aria-label="Platforms">
      {platforms.map((p) => {
        const open = p.drafts.draft + p.drafts.ready
        return (
          <button key={p.key} type="button" className={`cw-platform${p.key === active ? ' is-on' : ''}`} onClick={() => onPick(p.key)}>
            <span className="cw-platform-name">{p.name}</span>
            <span className="cw-platform-tags">
              {p.ai_writer_allowed && <span className="cw-tag">AI writer allowed</span>}
              {!p.video_creation && ['youtube', 'instagram'].includes(p.key) && <span className="cw-tag">metadata & comments</span>}
              {!p.researched && <span className="cw-tag cw-tag-warn">not researched</span>}
              {open > 0 && <span className="cw-tag">{open} open</span>}
              {p.drafts.posted > 0 && <span className="cw-tag">{p.drafts.posted} posted</span>}
            </span>
          </button>
        )
      })}
    </nav>
  )
}

function PlatformPanel({ platformKey, meta, tab, draftId, go, onDraftsChanged }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [archived, setArchived] = useState(false)

  const load = useCallback(() => contentPlatform(platformKey, archived)
    .then((d) => { setData(d); setErr(null) })
    .catch((e) => setErr(e.message)), [platformKey, archived])
  useEffect(() => { load() }, [load])

  if (err && !data) return <Notice icon={<IconAlert />}>This platform could not be read: {err}</Notice>
  if (!data) return <div className="skel" style={{ height: 320 }} />
  const p = data.platform

  return (
    <section className="cw-panel stack stack-3">
      <div className="cw-panel-head">
        <h2 style={{ fontSize: 'var(--fs-h3)' }}>{p.name}</h2>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          Formats: {p.formats.map(pretty).join(', ')}
          {' · '}{p.ai_writer_allowed ? 'an AI writer may draft here; a person edits and posts' : 'written by a person'}
          {!p.video_creation && ['youtube', 'instagram'].includes(p.key) && ' · no video yet: metadata and comments only'}
        </p>
        {!p.researched && (
          <Notice icon={<IconAlert />}>Neither research file studied {p.name}. Its notes are a placeholder until it is researched.</Notice>
        )}
      </div>
      <div className="cw-tabs" role="tablist">
        {TABS.map(([t, label]) => {
          const n = NOTE_TABS.has(t) ? data.notes[t].filter((x) => !x.archived).length : t === 'drafts' ? data.drafts.length : null
          return (
            <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? 'on' : ''} onClick={() => go({ t, d: '' })}>
              {label}{n != null && <span className="dim"> {n}</span>}
            </button>
          )
        })}
      </div>
      {NOTE_TABS.has(tab) && (
        <NotesTab
          section={tab}
          platform={p}
          notes={data.notes[tab]}
          meta={meta}
          archived={archived}
          setArchived={setArchived}
          reload={load}
        />
      )}
      {tab === 'topics' && (
        <TopicsTab
          platform={p}
          onStart={async (kind, item) => {
            const d = await contentDraftCreate({
              platform_key: p.key, format: p.formats[0], topic_kind: kind, body: '', suggestion: item,
            })
            await load(); onDraftsChanged()
            go({ t: 'drafts', d: String(d.id) })
          }}
        />
      )}
      {tab === 'drafts' && (
        <DraftsTab
          platform={p}
          drafts={data.drafts}
          meta={meta}
          draftId={draftId}
          open={(id) => go({ t: 'drafts', d: id ? String(id) : '' })}
          reload={async () => { await load(); onDraftsChanged() }}
        />
      )}
    </section>
  )
}

// ── notes ────────────────────────────────────────────────────────────────────

function NotesTab({ section, platform, notes, meta, archived, setArchived, reload }) {
  const [adding, setAdding] = useState(false)
  const groups = useMemo(() => {
    if (section !== 'research') return [[null, notes]]
    const by = new Map()
    for (const n of notes) {
      const k = n.topic || 'other'
      if (!by.has(k)) by.set(k, [])
      by.get(k).push(n)
    }
    return [...by.entries()]
  }, [section, notes])

  return (
    <div className="stack stack-3">
      <p className="muted cw-intro">{NOTE_INTRO[section]}</p>
      {notes.length === 0 && <p className="dim">No notes here yet.</p>}
      {groups.map(([topic, list]) => (
        <div key={topic || 'all'} className="stack stack-2">
          {topic && <h3 className="eyebrow">{pretty(topic)}</h3>}
          {list.map((n) => <NoteCard key={n.id} note={n} platform={platform} meta={meta} reload={reload} />)}
        </div>
      ))}
      <div className="cw-row">
        {!adding && <button type="button" className="btn btn-ghost" onClick={() => setAdding(true)}>Add a note</button>}
        <label className="cw-check dim">
          <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Show archived
        </label>
      </div>
      {adding && (
        <NoteEditor
          section={section}
          platform={platform}
          meta={meta}
          note={{ body: '', source: 'anooj', source_type: '', topic: '', check_id: 'manual', severity: 'manual', params: {}, formats: null }}
          onCancel={() => setAdding(false)}
          onSave={async (fields, forAll) => {
            await contentNoteCreate({ ...fields, section, platform_key: forAll ? null : platform.key })
            setAdding(false); await reload()
          }}
          allowForAll
        />
      )}
    </div>
  )
}

function NoteCard({ note, platform, meta, reload }) {
  const [editing, setEditing] = useState(false)
  const [history, setHistory] = useState(null)
  const [err, setErr] = useState(null)
  const common = note.platform_key === null

  const archive = async () => {
    try { await contentNoteUpdate(note.id, { archived: !note.archived }); await reload() } catch (e) { setErr(e.message) }
  }
  const showHistory = async () => {
    if (history) { setHistory(null); return }
    try { setHistory((await contentNoteHistory(note.id)).edits) } catch (e) { setErr(e.message) }
  }

  if (editing) {
    return (
      <NoteEditor
        section={note.section}
        platform={platform}
        meta={meta}
        note={note}
        onCancel={() => setEditing(false)}
        onSave={async (fields) => { await contentNoteUpdate(note.id, fields); setEditing(false); await reload() }}
      />
    )
  }
  return (
    <article className={`cw-note${note.archived ? ' is-archived' : ''}`}>
      <p className="cw-note-body">{note.body}</p>
      {note.section === 'rule' && (
        <p className="cw-note-rule">
          <span className={`cw-sev cw-sev-${note.severity}`}>{note.severity === 'manual' ? 'by hand' : note.severity}</span>
          {' '}check: <code>{note.check_id}</code>
          {Object.keys(note.params || {}).length > 0 && <> · <code>{JSON.stringify(note.params)}</code></>}
          {note.formats?.length > 0 && <> · formats: {note.formats.map(pretty).join(', ')}</>}
        </p>
      )}
      <p className="cw-note-meta dim">
        {common && <span className="cw-tag">All platforms</span>}
        {' '}{note.source}{note.source_type ? ` · ${note.source_type}` : ''}
        {note.updated_by && note.updated_by !== 'seed' ? ` · edited by ${note.updated_by}, ${when(note.updated_at)}` : ''}
        {note.archived && ' · archived'}
      </p>
      <div className="cw-row">
        <button type="button" className="btn btn-quiet" onClick={() => setEditing(true)}>Edit{common ? ' (all platforms)' : ''}</button>
        <button type="button" className="btn btn-quiet" onClick={archive}>{note.archived ? 'Restore' : 'Archive'}</button>
        <button type="button" className="btn btn-quiet" onClick={showHistory}>{history ? 'Hide history' : 'History'}</button>
      </div>
      {err && <p className="cw-err">{err}</p>}
      {history && (
        <ul className="cw-history">
          {history.length === 0 && <li className="dim">Not edited since it was seeded or written.</li>}
          {history.map((h) => (
            <li key={h.edited_at + JSON.stringify(h.after)}>
              <span className="dim">{when(h.edited_at)}{h.edited_by ? ` · ${h.edited_by}` : ''}</span>
              {Object.keys(h.after).map((k) => (
                <div key={k} className="cw-diff">
                  <code>{k}</code> <del>{typeof h.before[k] === 'string' ? h.before[k] : JSON.stringify(h.before[k])}</del>
                  {' → '}<ins>{typeof h.after[k] === 'string' ? h.after[k] : JSON.stringify(h.after[k])}</ins>
                </div>
              ))}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

function NoteEditor({ section, platform, meta, note, onCancel, onSave, allowForAll = false }) {
  const [body, setBody] = useState(note.body)
  const [source, setSource] = useState(note.source || '')
  const [sourceType, setSourceType] = useState(note.source_type || '')
  const [topic, setTopic] = useState(note.topic || '')
  const [checkId, setCheckId] = useState(note.check_id || 'manual')
  const [severity, setSeverity] = useState(note.severity || 'manual')
  const [paramsText, setParamsText] = useState(JSON.stringify(note.params || {}))
  const [formats, setFormats] = useState(note.formats || [])
  const [forAll, setForAll] = useState(false)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const save = async () => {
    const fields = { body, source, source_type: sourceType || null, topic: topic || null }
    if (section === 'rule') {
      let params
      try { params = JSON.parse(paramsText || '{}') } catch { setErr('Parameters must be JSON, e.g. {"max_chars": 280}'); return }
      Object.assign(fields, { check_id: checkId, severity, params, formats: formats.length ? formats : null })
    }
    setBusy(true)
    try { await onSave(fields, forAll) } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  return (
    <div className="cw-note cw-editing stack stack-2">
      <textarea className="cw-input" rows={5} value={body} onChange={(e) => setBody(e.target.value)} placeholder="The note" />
      <div className="cw-fields">
        <label className="cw-field">Source<input className="cw-input" value={source} onChange={(e) => setSource(e.target.value)} placeholder="who or what it comes from" /></label>
        <label className="cw-field">Source type<input className="cw-input" value={sourceType} onChange={(e) => setSourceType(e.target.value)} placeholder="official, code, study, press, marketing-blog, inference" /></label>
        {section === 'research' && (
          <label className="cw-field">Topic<input className="cw-input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="algorithm, audience, conversion…" /></label>
        )}
      </div>
      {section === 'rule' && (
        <div className="cw-fields">
          <label className="cw-field">Check
            <select className="cw-input" value={checkId} onChange={(e) => setCheckId(e.target.value)}>
              {meta.checks.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label className="cw-field">A miss shows as
            <select className="cw-input" value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {meta.severities.map((s) => <option key={s} value={s}>{s === 'manual' ? 'by hand' : s}</option>)}
            </select>
          </label>
          <label className="cw-field">Parameters (JSON)
            <input className="cw-input cw-mono" value={paramsText} onChange={(e) => setParamsText(e.target.value)} placeholder='{"max_chars": 280}' />
          </label>
          <fieldset className="cw-field">
            <span>Formats (none ticked: all)</span>
            <span className="cw-row">
              {platform.formats.map((f) => (
                <label key={f} className="cw-check">
                  <input type="checkbox" checked={formats.includes(f)} onChange={(e) => setFormats(e.target.checked ? [...formats, f] : formats.filter((x) => x !== f))} /> {pretty(f)}
                </label>
              ))}
            </span>
          </fieldset>
        </div>
      )}
      {allowForAll && (
        <label className="cw-check dim">
          <input type="checkbox" checked={forAll} onChange={(e) => setForAll(e.target.checked)} /> For all platforms, not only {platform.name}
        </label>
      )}
      {err && <p className="cw-err">{err}</p>}
      <div className="cw-row">
        <button type="button" className="btn btn-primary" disabled={busy || !body.trim() || !source.trim()} onClick={save}>Save</button>
        <button type="button" className="btn btn-quiet" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

// ── topics ───────────────────────────────────────────────────────────────────

function TopicsTab({ platform, onStart }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    setData(null)
    contentSuggestions(platform.key).then((d) => { setData(d); setErr(null) }).catch((e) => setErr(e.message))
  }, [platform.key])
  useEffect(() => { load() }, [load])

  if (err) return <Notice icon={<IconAlert />}>Suggestions could not be read: {err}</Notice>
  if (!data) return <div className="skel" style={{ height: 240 }} />

  return (
    <div className="stack stack-3">
      <div className="cw-row">
        <p className="muted cw-intro">
          Coded from the board’s data, one block per topic kind {platform.name} uses. {data.order}
        </p>
        <button type="button" className="btn btn-ghost" onClick={load}>Refresh</button>
      </div>
      {data.kinds.map((k) => (
        <div key={k.kind} className="cw-kind stack stack-2">
          <div>
            <h3 style={{ fontSize: 'var(--fs-body)' }}>{k.label}</h3>
            {k.angle && <p className="dim cw-small">{k.angle}</p>}
          </div>
          {k.unreadable && <Notice icon={<IconAlert />}>{k.note}</Notice>}
          {!k.unreadable && k.items.length === 0 && <p className="dim cw-small">{k.note}</p>}
          {k.items.map((it) => (
            <article key={it.id} className="cw-suggestion">
              <p className="cw-suggestion-head">
                {it.date && <span className="dim">{it.date} · </span>}
                <strong>{it.headline}</strong>
              </p>
              {it.detail && <p className="cw-small">{it.detail}</p>}
              <ul className="cw-evidence">
                {it.evidence.map((e) => <li key={e}>{e}</li>)}
              </ul>
              {!it.ready && <p className="cw-small cw-warn-text">{it.why_not_ready}</p>}
              <div className="cw-row">
                {it.links.map((l) => (l.url
                  ? <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer" className="mb-link cw-small">{l.label} ↗</a>
                  : <Link key={l.path} to={l.path} className="mb-link cw-small">{l.label}</Link>))}
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={busy}
                  onClick={async () => { setBusy(true); try { await onStart(k.kind, it) } catch (e) { setErr(e.message) } setBusy(false) }}
                >
                  Start a draft
                </button>
              </div>
            </article>
          ))}
          {k.more > 0 && <p className="dim cw-small">{k.more} more not shown.</p>}
        </div>
      ))}
    </div>
  )
}

// ── drafts ───────────────────────────────────────────────────────────────────

function DraftsTab({ platform, drafts, meta, draftId, open, reload }) {
  const current = drafts.find((d) => String(d.id) === String(draftId))
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const create = async () => {
    setBusy(true)
    try { const d = await contentDraftCreate({ platform_key: platform.key, format: platform.formats[0], body: '' }); await reload(); open(d.id) } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  return (
    <div className="cw-drafts">
      <div className="stack stack-1">
        <button type="button" className="btn btn-ghost" disabled={busy} onClick={create}>New draft</button>
        {err && <p className="cw-err">{err}</p>}
        {drafts.length === 0 && <p className="dim cw-small">No drafts yet. Start one here or from Topics.</p>}
        {drafts.map((d) => (
          <button key={d.id} type="button" className={`cw-draft-item${current?.id === d.id ? ' is-on' : ''}`} onClick={() => open(d.id)}>
            <span className="cw-draft-title">{d.title || (d.body || '').split('\n')[0] || d.suggestion?.headline || `Draft ${d.id}`}</span>
            <span className="dim cw-small">
              {d.status} · {pretty(d.format)}
              {d.last_check && ` · ${d.last_check.counts.fail} missed, ${d.last_check.counts.warn} warnings`}
            </span>
          </button>
        ))}
      </div>
      {current
        ? <DraftEditor key={current.id} draft={current} platform={platform} meta={meta} reload={reload} />
        : <p className="dim">Pick a draft, or start one.</p>}
    </div>
  )
}

function DraftEditor({ draft, platform, meta, reload }) {
  const [f, setF] = useState({
    format: draft.format, topic_kind: draft.topic_kind || '', title: draft.title || '', body: draft.body,
    tags: (draft.tags || []).join(', '), ai_assisted: draft.ai_assisted, status: draft.status, posted_url: draft.posted_url || '',
  })
  const [report, setReport] = useState(draft.last_check)
  const [saved, setSaved] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [ticked, setTicked] = useState({})
  const set = (k, v) => { setF((x) => ({ ...x, [k]: v })); setSaved(false) }

  const payload = () => ({
    format: f.format, topic_kind: f.topic_kind || null, title: f.title.trim() || null, body: f.body,
    tags: f.tags.split(',').map((t) => t.trim()).filter(Boolean), ai_assisted: f.ai_assisted,
    status: f.status, posted_url: f.posted_url.trim() || null,
  })
  const save = async (andCheck) => {
    setBusy(true); setErr(null)
    try {
      await contentDraftUpdate(draft.id, payload())
      setSaved(true)
      if (andCheck) setReport(await contentDraftCheck(draft.id))
      await reload()
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  const parts = f.body.split(/^\s*---\s*$/m).filter((x) => x.trim()).length
  const stale = report && !saved
  const s = draft.suggestion

  return (
    <div className="cw-editor stack stack-3">
      {s && (
        <aside className="cw-from">
          <p className="eyebrow">Started from</p>
          <p><strong>{s.headline}</strong>{s.date ? <span className="dim"> · {s.date}</span> : null}</p>
          {s.detail && <p className="cw-small">{s.detail}</p>}
          <ul className="cw-evidence">{(s.evidence || []).map((e) => <li key={e}>{e}</li>)}</ul>
          <div className="cw-row">
            {(s.links || []).map((l) => (l.url
              ? <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer" className="mb-link cw-small">{l.label} ↗</a>
              : <Link key={l.path} to={l.path} className="mb-link cw-small">{l.label}</Link>))}
          </div>
        </aside>
      )}
      <div className="cw-fields">
        <label className="cw-field">Format
          <select className="cw-input" value={f.format} onChange={(e) => set('format', e.target.value)}>
            {platform.formats.map((x) => <option key={x} value={x}>{pretty(x)}</option>)}
          </select>
        </label>
        <label className="cw-field">Topic
          <select className="cw-input" value={f.topic_kind} onChange={(e) => set('topic_kind', e.target.value)}>
            <option value="">(none)</option>
            {platform.topic_kinds.map((k) => <option key={k} value={k}>{meta.topic_kinds[k]?.label || k}</option>)}
          </select>
        </label>
        <label className="cw-field">Status
          <select className="cw-input" value={f.status} onChange={(e) => set('status', e.target.value)}>
            {meta.statuses.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
        </label>
      </div>
      {(TITLED.has(f.format) || f.title) && (
        <label className="cw-field">Title{f.format === 'newsletter_issue' ? ' (subject line)' : ''}
          <input className="cw-input" value={f.title} onChange={(e) => set('title', e.target.value)} />
          <span className="dim cw-small">{f.title.length} characters</span>
        </label>
      )}
      <label className="cw-field">
        {f.format.includes('metadata') ? 'Description' : 'Text'}
        <textarea className="cw-input cw-body" rows={12} value={f.body} onChange={(e) => set('body', e.target.value)}
          placeholder={['thread', 'carousel_text', 'document_carousel_text'].includes(f.format) ? 'One part per block; put --- on a line by itself between parts.' : 'Written by a person.'} />
        <span className="dim cw-small">
          {f.body.length.toLocaleString()} characters
          {['thread', 'carousel_text', 'document_carousel_text'].includes(f.format) && ` · ${parts} part${parts === 1 ? '' : 's'}`}
        </span>
      </label>
      {f.format.includes('metadata') && (
        <label className="cw-field">Tags (comma-separated)
          <input className="cw-input" value={f.tags} onChange={(e) => set('tags', e.target.value)} />
        </label>
      )}
      <label className="cw-check">
        <input type="checkbox" checked={f.ai_assisted} onChange={(e) => set('ai_assisted', e.target.checked)} />
        {' '}An AI drafted some of this text
        {!platform.ai_writer_allowed && <span className="cw-warn-text cw-small"> ({platform.name} expects text written by a person; the rules check this)</span>}
      </label>
      {f.status === 'posted' && (
        <label className="cw-field">Where it was posted (URL)
          <input className="cw-input" value={f.posted_url} onChange={(e) => set('posted_url', e.target.value)} />
        </label>
      )}
      {err && <p className="cw-err">{err}</p>}
      <div className="cw-row">
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => save(true)}>Save and check</button>
        <button type="button" className="btn btn-ghost" disabled={busy || saved} onClick={() => save(false)}>Save</button>
        <span className="dim cw-small">{saved ? `Saved ${when(draft.updated_at)}` : 'Not saved'}</span>
      </div>
      <FitReport report={report} stale={stale} ticked={ticked} setTicked={setTicked} />
    </div>
  )
}

function FitReport({ report, stale, ticked, setTicked }) {
  if (!report) return <p className="dim cw-small">Not checked yet. Save and check to see how it fits the platform’s rules.</p>
  const order = { fail: 0, warn: 1, unchecked: 2, manual: 3, pass: 4 }
  const rows = [...report.results].sort((a, b) => order[a.outcome] - order[b.outcome])
  return (
    <div className="cw-report stack stack-2">
      <div>
        <p className="eyebrow">Platform fit check</p>
        <p><strong>{report.summary}</strong></p>
        <p className="dim cw-small">
          Checked {when(report.ran_at)}{stale ? ' · the text has changed since: check again' : ''}.
          Advisory: it blocks nothing, and its word lists and patterns have not been measured.
          {report.counts.replaced_by_platform_rule > 0 && ` ${report.counts.replaced_by_platform_rule} all-platform rule(s) replaced by this platform’s own.`}
          {report.counts.not_for_this_format > 0 && ` ${report.counts.not_for_this_format} rule(s) do not apply to this format.`}
        </p>
      </div>
      <ul className="cw-results">
        {rows.map((r) => (
          <li key={r.note_id} className={`cw-result cw-out-${r.outcome}`}>
            <span className="cw-outcome">
              {r.outcome === 'manual'
                ? <label className="cw-check"><input type="checkbox" checked={!!ticked[r.note_id]} onChange={(e) => setTicked((t) => ({ ...t, [r.note_id]: e.target.checked }))} /> {OUTCOME_LABEL.manual}</label>
                : OUTCOME_LABEL[r.outcome]}
            </span>
            <span>
              {r.rule}
              <span className="dim cw-small"> — {r.detail}{r.for_all_platforms ? ' (all platforms)' : ''}</span>
            </span>
          </li>
        ))}
      </ul>
      {rows.some((r) => r.outcome === 'manual') && <p className="dim cw-small">Ticks are for you while writing; they are not saved.</p>}
    </div>
  )
}
