import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  contentDraftCheck, contentDraftCreate, contentDraftUpdate, contentNoteCreate, contentNoteHistory,
  contentModels, contentNoteUpdate, contentPlatform, contentPlatforms, contentPropose,
  contentProposals, contentSuggestions, contentTrajectory, contentUseProposal, contentWriterStatus,
  contentAddResult, contentResults, contentTemplate, contentTick, contentPlatformResults,
  contentMedia, contentMediaBlob, contentCapabilitySplit,
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
  ['results', 'Results'],
]
const NOTE_TABS = new Set(['philosophy', 'research', 'rule', 'recommendation'])
const NOTE_INTRO = {
  philosophy: 'What the platform is for and what its people value. From anooj’s framework, our studies and the external research.',
  research: 'Findings with their source, population and date. Where the two research files disagree, the note says so.',
  rule: 'What every post here is checked against. A rule names a coded check, or "manual" for a person to tick. Rules marked "All platforms" apply everywhere; a platform’s own rule on the same check replaces them.',
  recommendation: 'What to do on this platform, and in what order.',
}
const OUTCOME_LABEL = { pass: 'Met', warn: 'Warning', fail: 'Missed', manual: 'By hand', unchecked: 'Not checked' }
const TITLED = new Set(['text_post', 'image_post', 'link_submission', 'show_hn', 'newsletter_issue', 'article',
  'video_metadata', 'shorts_metadata', 'readme', 'discussion_post', 'release_notes', 'document_carousel_text'])
const TITLE_LABEL = { newsletter_issue: 'Subject line', document_carousel_text: 'Post text that goes with the carousel' }
const MEDIA_LABEL = { carousel_pdf: 'carousel PDF', card_png: 'card image', chart_png: 'chart image',
  cover_png: 'cover image', other: 'other file' }

// The topic kind's look and this platform's recipe (workspace.yaml topic_recipes).
function Recipe({ recipe }) {
  if (!recipe) return null
  if (recipe.missing) return <p className="dim cw-small">{recipe.note}</p>
  const media = recipe.media.length
    ? recipe.media.map((m) => MEDIA_LABEL[m] || m).join(' + ')
    : 'text only'
  return (
    <p className="cw-small">
      <span className="muted">Look:</span> {recipe.look.label}
      {' · '}<span className="muted">Format:</span> {recipe.format.replaceAll('_', ' ')}
      {' · '}<span className="muted">Media:</span> {media}
      {recipe.look.suits && <span className="dim"> — {recipe.look.suits}</span>}
    </p>
  )
}
// Where the link to the model page goes, when the rules keep it out of the post.
const FIRST_COMMENT_LABEL = {
  linkedin: 'First comment (the model page link goes here)',
  x: 'First reply (the link-in-reply test)',
}

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
      {tab === 'results' && <ResultsTab platform={p} open={(id) => go({ t: 'drafts', d: String(id) })} />}
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

// The extractor's polarity label, as the board files it; not our judgement.
const SIDE = { positive: 'Positive report', negative: 'Negative report' }

function Links({ links }) {
  return (links || []).map((l) => (l.url
    ? <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer" className="mb-link cw-small">{l.label} ↗</a>
    : <Link key={l.path} to={l.path} className="mb-link cw-small">{l.label}</Link>))
}

// The board's paraphrased reports carried as proof. The source post's link is
// not here on purpose: posts link to the model page, never to somebody's post.
function Proof({ proof }) {
  if (!proof?.length) return null
  return (
    <div className="cw-proof">
      <p className="dim cw-small">
        Proof: the board’s paraphrases of single reports (restate them; never quote them or link the post)
      </p>
      <ul className="cw-evidence">
        {proof.map((p) => (
          <li key={`${p.period}:${p.side}:${p.text}`}>
            <span className={`cw-sev ${p.side === 'negative' ? 'cw-sev-fail' : 'cw-sev-manual'}`}>{SIDE[p.side]}</span>
            {' '}<span className="dim">{[p.period, p.date, p.platform].filter(Boolean).join(' · ')}</span>
            {' '}{p.text}
            {p.on?.length > 0 && <span className="dim"> ({p.on.join(', ')})</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Suggestion({ item: it, busy, onStart }) {
  return (
    <article className="cw-suggestion">
      <p className="cw-suggestion-head">
        {it.date && <span className="dim">{it.date} · </span>}
        <strong>{it.headline}</strong>
      </p>
      {it.detail && <p className="cw-small">{it.detail}</p>}
      {it.price && <p className="cw-small dim">{it.price}.</p>}
      {it.sample?.small && <p className="cw-small cw-warn-text"><span className="cw-tag cw-tag-warn">small sample</span> {it.sample.note}</p>}
      {it.no_reports && <p className="cw-small cw-warn-text"><span className="cw-tag cw-tag-warn">no reports</span> {it.no_reports}</p>}
      <ul className="cw-evidence">
        {it.evidence.map((e) => <li key={e}>{e}</li>)}
      </ul>
      <Proof proof={it.proof} />
      {!it.ready && <p className="cw-small cw-warn-text">{it.why_not_ready}</p>}
      <div className="cw-row">
        <Links links={it.links} />
        <button type="button" className="btn btn-ghost" disabled={busy} onClick={onStart}>Start a draft</button>
      </div>
    </article>
  )
}

// A model's reports by capability and job: people on each side, with the label in
// words beside its counts. The order and what the labels mean are stated, never a score.
function CapabilitySplit({ split }) {
  return (
    <div className="stack stack-2">
      <p className="cw-small">
        <strong>{split.name}</strong>, {split.start} to {split.end}{split.still_running ? ' (still running)' : ''}:{' '}
        {split.people} people in {split.posts} posts.
      </p>
      {split.empty ? <p className="dim cw-small">{split.empty}</p> : (
        <table className="cw-table cw-small">
          <thead><tr><th>Capability or job</th><th>People</th><th>For</th><th>Against</th><th>Neutral</th><th>In words</th></tr></thead>
          <tbody>
            {split.capabilities.map((c) => (
              <tr key={`${c.section}:${c.name}`}>
                <td>{c.name}{c.section === 'best_for' ? ' (job)' : ''}</td>
                <td>{c.people}</td><td>{c.for}</td><td>{c.against}</td><td>{c.neutral}</td><td>{c.label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {split.more > 0 && <p className="dim cw-small">{split.more} more capabilities and jobs not shown.</p>}
      <p className="dim cw-small">{split.order}</p>
      {split.pain_angles && (
        <>
          <p className="cw-small"><strong>Angles from the pain research</strong></p>
          <table className="cw-table cw-small">
            <thead><tr><th>Pain</th><th>Fit</th><th>People</th><th>For</th><th>Against</th><th>In words</th></tr></thead>
            <tbody>
              {split.pain_angles.map((a) => (
                <tr key={a.key}>
                  <td title={a.says}>{a.label}</td><td>{a.fit}</td>
                  <td>{a.people}</td><td>{a.for}</td><td>{a.against}</td><td>{a.in_words}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="dim cw-small">{split.pain_note}</p>
          <p className="dim cw-small">Not counted on the board: {split.pain_not_counted.join(', ')}.</p>
        </>
      )}
    </div>
  )
}

function TrajectoryPicker({ kind, busy, start }) {
  const [q, setQ] = useState('')
  const [found, setFound] = useState(null)
  const [model, setModel] = useState(null)
  const [from, setFrom] = useState('')
  const [weeks, setWeeks] = useState('')
  const [item, setItem] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)

  const search = async () => {
    setErr(null); setItem(null)
    try { setFound((await contentModels(q)).models) } catch (e) { setErr(e.message) }
  }
  const [split, setSplit] = useState(null)
  const build = async () => {
    setErr(null); setLoading(true)
    try { setItem(await contentTrajectory(model.id, { start: from, weeks })) } catch (e) { setErr(e.message) }
    setLoading(false)
  }
  const bySplit = async () => {
    setErr(null); setLoading(true)
    const days = weeks ? Number(weeks) * 7 : ''
    try { setSplit(await contentCapabilitySplit(model.id, { start: from, days })) } catch (e) { setErr(e.message) }
    setLoading(false)
  }

  return (
    <div className="stack stack-2">
      <div className="cw-row">
        <input className="cw-input" style={{ maxWidth: 320 }} value={q} placeholder="Find a model, e.g. opus 5.5"
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') search() }} />
        <button type="button" className="btn btn-ghost" disabled={q.trim().length < 2} onClick={search}>Find</button>
      </div>
      {found && found.length === 0 && <p className="dim cw-small">No model on the board matches.</p>}
      {found && found.length > 0 && !model && (
        <div className="cw-row">
          {found.map((m) => (
            <button key={m.id} type="button" className="btn btn-quiet cw-small" onClick={() => { setModel(m); setFound(null) }}>
              {m.name}{m.release_date ? ` · ${m.release_date}` : ''}
            </button>
          ))}
        </div>
      )}
      {model && (
        <div className="cw-fields">
          <p className="cw-field">Model<strong>{model.name}</strong>
            <button type="button" className="btn btn-quiet cw-small" onClick={() => { setModel(null); setItem(null) }}>change</button>
          </p>
          <label className="cw-field">Start (blank: its release date{model.release_date ? `, ${model.release_date}` : ''})
            <input className="cw-input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="cw-field">Weeks (blank: 4)
            <input className="cw-input" type="number" min="1" max="8" value={weeks} onChange={(e) => setWeeks(e.target.value)} />
          </label>
          <div className="cw-field"><span>&nbsp;</span>
            <button type="button" className="btn btn-ghost" disabled={loading} onClick={build}>{loading ? 'Reading…' : 'Build the trajectory'}</button>
          </div>
          <div className="cw-field"><span>&nbsp;</span>
            <button type="button" className="btn btn-ghost" disabled={loading} onClick={bySplit}>By capability</button>
          </div>
        </div>
      )}
      {err && <p className="cw-err">{err}</p>}
      {split && <CapabilitySplit split={split} />}
      {item && <Suggestion item={item} busy={busy} onStart={() => start(kind, item)} />}
    </div>
  )
}

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

  const start = async (kind, it) => {
    setBusy(true)
    try { await onStart(kind, it) } catch (e) { setErr(e.message) }
    setBusy(false)
  }

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
            <Recipe recipe={k.recipe} />
          </div>
          {k.unreadable && <Notice icon={<IconAlert />}>{k.note}</Notice>}
          {!k.unreadable && k.items.length === 0 && k.signal !== 'trajectory' && <p className="dim cw-small">{k.note}</p>}
          {k.signal === 'trajectory' && !k.unreadable && <TrajectoryPicker kind={k.kind} busy={busy} start={start} />}
          {k.items.map((it) => (
            <Suggestion key={it.id} item={it} busy={busy} onStart={() => start(k.kind, it)} />
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
        // Keyed by the saved version too, so text a proposal put in the draft
        // (or a save) re-seeds the editor from the server.
        ? <DraftEditor key={`${current.id}:${current.updated_at}`} draft={current} platform={platform} meta={meta} reload={reload} />
        : <p className="dim">Pick a draft, or start one.</p>}
    </div>
  )
}

function DraftEditor({ draft, platform, meta, reload }) {
  const [f, setF] = useState({
    format: draft.format, topic_kind: draft.topic_kind || '', title: draft.title || '', body: draft.body,
    first_comment: draft.first_comment || '', tags: (draft.tags || []).join(', '), ai_assisted: draft.ai_assisted, status: draft.status, posted_url: draft.posted_url || '',
  })
  const [report, setReport] = useState(draft.last_check)
  const [saved, setSaved] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [ticks, setTicks] = useState(draft.ticks || {})
  const tick = async (noteId, on) => {
    setErr(null)
    const before = ticks
    // Show the tick at once; the server's answer replaces it, and a failed
    // save puts the previous state back (and says so).
    setTicks((t) => ({ ...t, [noteId]: { ...t[noteId], ticked: on, content_sha: draft.content_sha, at: new Date().toISOString() } }))
    try { setTicks((await contentTick(draft.id, noteId, on)).ticks) } catch (e) { setTicks(before); setErr(`The tick was not saved: ${e.message}`) }
  }
  const set = (k, v) => { setF((x) => ({ ...x, [k]: v })); setSaved(false) }

  const payload = () => ({
    format: f.format, topic_kind: f.topic_kind || null, title: f.title.trim() || null, body: f.body,
    first_comment: f.first_comment.trim() || null, tags: f.tags.split(',').map((t) => t.trim()).filter(Boolean), ai_assisted: f.ai_assisted,
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

  const [filled, setFilled] = useState(null)
  const hasTemplate = (meta.templates?.[platform.key] || []).includes(draft.format)
  const startFromTemplate = async () => {
    if ((f.body.trim() || f.title.trim()) && !window.confirm('Replace the title, text and first comment with the template?')) return
    setErr(null)
    try {
      const t = await contentTemplate(draft.id)
      setF((x) => ({ ...x, title: t.title || '', body: t.body || '', first_comment: t.first_comment || '' }))
      setSaved(false)
      setFilled(t)
    } catch (e) { setErr(e.message) }
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
          {s.price && <p className="cw-small dim">{s.price}.</p>}
          {s.sample?.small && <p className="cw-small cw-warn-text"><span className="cw-tag cw-tag-warn">small sample</span> {s.sample.note}</p>}
          <ul className="cw-evidence">{(s.evidence || []).map((e) => <li key={e}>{e}</li>)}</ul>
          <Proof proof={s.proof} />
          <div className="cw-row"><Links links={s.links} /></div>
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
      {hasTemplate && (
        <div className="cw-row">
          <button type="button" className="btn btn-ghost" disabled={busy || f.format !== draft.format} onClick={startFromTemplate}>
            Start from the template
          </button>
          <span className="dim cw-small">
            {f.format !== draft.format
              ? 'Save the new format first.'
              : 'Fills the fields from this draft’s suggestion; every figure comes from the board. You write the rest.'}
          </span>
        </div>
      )}
      {filled && (
        <p className="cw-small cw-warn-text">
          Template filled, not saved. {filled.to_write} place{filled.to_write === 1 ? '' : 's'} marked [like this] for you to write
          {filled.unfilled.length > 0 && `; this suggestion has no ${filled.unfilled.join(', ')}`}.
        </p>
      )}
      {(TITLED.has(f.format) || f.title) && (
        <label className="cw-field">{TITLE_LABEL[f.format] || 'Title'}
          {f.format === 'document_carousel_text'
            ? <textarea className="cw-input" rows={3} value={f.title} onChange={(e) => set('title', e.target.value)} />
            : <input className="cw-input" value={f.title} onChange={(e) => set('title', e.target.value)} />}
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
      <label className="cw-field">{FIRST_COMMENT_LABEL[platform.key] || 'First comment or reply (optional)'}
        <textarea className="cw-input" rows={2} value={f.first_comment} onChange={(e) => set('first_comment', e.target.value)} />
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
      <FitReport report={report} stale={stale} ticks={ticks} onTick={tick} sha={draft.content_sha} saved={saved} />
      <MediaPanel draft={draft} />
      <ResultsPanel draft={draft} />
      {platform.ai_writer_allowed && <WriterPanel draft={draft} saved={saved} reload={reload} />}
    </div>
  )
}

// ── media made for a draft ───────────────────────────────────────────────────

const MEDIA_KIND = { carousel_pdf: 'Carousel (PDF)', card_png: 'Card', chart_png: 'Chart', cover_png: 'Cover', other: 'File' }

function MediaFile({ m }) {
  const [url, setUrl] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    let live = true
    let made = null
    contentMediaBlob(m.id)
      .then((b) => { made = URL.createObjectURL(b); if (live) setUrl(made) })
      .catch((e) => live && setErr(e.message))
    return () => { live = false; if (made) URL.revokeObjectURL(made) }
  }, [m.id])
  return (
    <article className="cw-suggestion">
      <p className="cw-small">
        <strong>{MEDIA_KIND[m.kind] || m.kind}</strong>
        <span className="dim"> · {m.filename} · {m.pages ? `${m.pages} page${m.pages === 1 ? '' : 's'}` : `${m.width}×${m.height}`} · {(m.size_bytes / 1024).toFixed(0)} KB · {when(m.created_at)}</span>
      </p>
      {m.out_of_date && <p className="cw-small cw-warn-text">Made from an earlier version of the text: check it still matches.</p>}
      <p className="dim cw-small">Made with {m.made_with}{m.note ? `. ${m.note}` : ''}</p>
      {err && <p className="cw-err">{err}</p>}
      {url && m.content_type === 'image/png' && <img src={url} alt={`${MEDIA_KIND[m.kind] || 'Media'} for this draft`} className="cw-media-img" />}
      {url && (
        <div className="cw-row">
          <a className="btn btn-ghost" href={url} target="_blank" rel="noopener noreferrer">Open</a>
          <a className="btn btn-quiet" href={url} download={m.filename}>Download</a>
        </div>
      )}
    </article>
  )
}

function MediaPanel({ draft }) {
  const [list, setList] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => { contentMedia(draft.id).then((d) => setList(d.media)).catch((e) => setErr(e.message)) }, [draft.id])
  return (
    <div className="cw-report stack stack-2">
      <div>
        <p className="eyebrow">Media</p>
        <p className="cw-small muted">
          Carousel PDFs, cards and charts for this draft are made in Claude Code with the media skills, in the
          board’s theme, from this draft’s text and the board’s counts. Ask Claude: <strong>“make media for
          content workspace draft {draft.id}”</strong> (a carousel, a card or a chart). Look at every file before
          posting: code checks the file, not what the picture says.
        </p>
      </div>
      {err && <p className="cw-err">{err}</p>}
      {list && list.length === 0 && <p className="dim cw-small">No media yet.</p>}
      {list && list.map((m) => <MediaFile key={m.id} m={m} />)}
    </div>
  )
}

// ── results overview per platform ────────────────────────────────────────────

function ResultsTab({ platform, open }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => { contentPlatformResults(platform.key).then(setData).catch((e) => setErr(e.message)) }, [platform.key])
  if (err) return <Notice icon={<IconAlert />}>Results could not be read: {err}</Notice>
  if (!data) return <div className="skel" style={{ height: 200 }} />
  return (
    <div className="stack stack-3">
      <p className="muted cw-intro">
        What each posted {platform.name} draft did, as its analytics showed it. {data.order} {data.counts.posted} posted,
        {' '}{data.counts.with_any_reading} with at least one reading.
      </p>
      <p className="dim cw-small">Visits to our site from these posts: not measured. {data.site_visits.why}.</p>
      {data.posts.length === 0 && <p className="dim">Nothing posted on {platform.name} yet. Mark a draft posted (with its link) to record its results.</p>}
      {data.posts.length > 0 && (
        <div className="cw-table-wrap">
          <table className="cw-table">
            <thead>
              <tr>
                <th>Post</th>
                {data.metrics.map((m) => <th key={m.key}>{m.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.posts.map((p) => (
                <tr key={p.draft_id}>
                  <td>
                    <button type="button" className="btn btn-quiet cw-small" onClick={() => open(p.draft_id)}>{p.headline || `Draft ${p.draft_id}`}</button>
                    <div className="dim cw-small">{p.posted_at ? `posted ${when(p.posted_at)}` : ''}{p.ai_assisted ? ' · AI-assisted' : ''}</div>
                  </td>
                  {data.metrics.map((m) => {
                    const r = p.latest[m.key]
                    return (
                      <td key={m.key} className="tnum">
                        {r ? <>{r.value.toLocaleString()}<div className="dim cw-small">as of {when(r.observed_at)}</div></> : <span className="dim">not recorded</span>}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── phase 3: tracked link and results ────────────────────────────────────────

function ResultsPanel({ draft }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [form, setForm] = useState({ metric: '', value: '', source: '', observed_at: '', note: '' })
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = useCallback(() => contentResults(draft.id).then(setData).catch((e) => setErr(e.message)), [draft.id])
  useEffect(() => { load() }, [load])

  const copy = async () => {
    try { await navigator.clipboard.writeText(data.link.url); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { setCopied(false) }
  }
  const add = async () => {
    setBusy(true); setErr(null)
    try {
      await contentAddResult(draft.id, {
        metric: form.metric, value: Number(form.value), source: form.source,
        observed_at: form.observed_at ? new Date(form.observed_at).toISOString() : null, note: form.note || null,
      })
      setForm((x) => ({ ...x, value: '', note: '' }))
      await load()
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  if (!data) return err ? <p className="cw-err">{err}</p> : null
  const posted = draft.status === 'posted'
  const valid = form.metric && form.source.trim() && /^\d+$/.test(form.value)

  return (
    <div className="cw-report stack stack-2">
      <div>
        <p className="eyebrow">Tracked link and results</p>
        <div className="cw-row">
          <code className="cw-mono cw-small" style={{ overflowWrap: 'anywhere' }}>{data.link.url}</code>
          <button type="button" className="btn btn-quiet cw-small" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
        </div>
        <p className="dim cw-small">
          Use this link wherever this post links to the board (first comment, bio, description).
          {data.link.note && ` Note: ${data.link.note}.`}
        </p>
      </div>
      {!posted && <p className="dim cw-small">Results are recorded once the draft is marked posted, with where it was posted.</p>}
      {posted && (
        <>
          <ul className="cw-results">
            {data.metrics.map((m) => (
              <li key={m.key} className="cw-result">
                <span className="cw-outcome">{m.latest ? m.latest.value.toLocaleString() : '—'}</span>
                <span>{m.label}
                  <span className="dim cw-small"> — {m.latest ? `as of ${when(m.latest.observed_at)}, from ${m.latest.source}` : 'not recorded'}</span>
                </span>
              </li>
            ))}
            <li className="cw-result">
              <span className="cw-outcome">n/a</span>
              <span>Visits to our site from the tracked link
                <span className="dim cw-small"> — not measured: {data.site_visits.why}</span>
              </span>
            </li>
          </ul>
          <div className="cw-fields">
            <label className="cw-field">Metric
              <select className="cw-input" value={form.metric} onChange={(e) => setForm({ ...form, metric: e.target.value })}>
                <option value="">(choose)</option>
                {data.metrics.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
              </select>
            </label>
            <label className="cw-field">Count
              <input className="cw-input" inputMode="numeric" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value.trim() })} />
            </label>
            <label className="cw-field">Read from
              <input className="cw-input" value={form.source} placeholder="e.g. LinkedIn post analytics" onChange={(e) => setForm({ ...form, source: e.target.value })} />
            </label>
            <label className="cw-field">When it showed this (blank: now)
              <input className="cw-input" type="datetime-local" value={form.observed_at} onChange={(e) => setForm({ ...form, observed_at: e.target.value })} />
            </label>
          </div>
          <div className="cw-row">
            <button type="button" className="btn btn-ghost" disabled={busy || !valid} onClick={add}>Record reading</button>
            <span className="dim cw-small">Each reading is kept with its date; a later one does not replace it.</span>
          </div>
          {data.readings.length > 0 && (
            <details className="cw-small">
              <summary className="dim">All {data.readings.length} reading{data.readings.length === 1 ? '' : 's'}</summary>
              <ul className="cw-evidence">
                {data.readings.map((r) => (
                  <li key={r.id}>{when(r.observed_at)} · {r.metric} {r.value.toLocaleString()} · {r.source}{r.note ? ` · ${r.note}` : ''}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
      {err && <p className="cw-err">{err}</p>}
    </div>
  )
}

// ── the AI writer (phase 2) ──────────────────────────────────────────────────

const RUN_STATE = { proposed: 'Proposed', refused: 'Refused by the checks', failed: 'No usable answer' }

function WriterPanel({ draft, saved, reload }) {
  const [runs, setRuns] = useState(null)
  const [status, setStatus] = useState(null)
  const [instructions, setInstructions] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    contentProposals(draft.id).then((d) => setRuns(d.proposals)).catch((e) => setErr(e.message))
    contentWriterStatus().then(setStatus).catch(() => {})
  }, [draft.id])
  useEffect(() => { load() }, [load])

  const propose = async () => {
    setBusy(true); setErr(null)
    try { await contentPropose(draft.id, instructions); load() } catch (e) { setErr(e.message) }
    setBusy(false)
  }
  const use = async (id) => {
    setBusy(true); setErr(null)
    try { await contentUseProposal(id); await reload() } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  return (
    <div className="cw-report stack stack-2">
      <div>
        <p className="eyebrow">AI writer</p>
        <p className="cw-small muted">
          A model proposes text from this draft’s suggestion, your text and your instructions, following
          the platform’s philosophy and rules as they are now. Code refuses a proposal with a number that
          is not in that material, a link it was not given, or a handle. You decide whether to use it,
          then edit it; using one marks the draft AI-assisted.
        </p>
        {status && status.api_enabled && (
          <p className="dim cw-small">
            {status.model} · today ${status.today.usd.toFixed(4)} of ${status.daily_budget_usd.toFixed(2)} over {status.today.calls} call{status.today.calls === 1 ? '' : 's'}
            {status.today.unreported_cost_calls > 0 && ` (${status.today.unreported_cost_calls} with no cost reported, not counted)`}
          </p>
        )}
      </div>
      {status && !status.api_enabled && (
        <p className="cw-small">
          For now proposals are written in Claude Code, not by an API model (the team picks that model
          later). Save the draft, then ask Claude: <strong>“draft content workspace draft {draft.id}”</strong>,
          with any instructions. Its proposal goes through the same checks and appears below.
        </p>
      )}
      {status && status.api_enabled && (
        <>
          <textarea className="cw-input" rows={2} value={instructions} onChange={(e) => setInstructions(e.target.value)}
            placeholder="Instructions (optional): the angle, what to lead with, what to leave out" />
          <div className="cw-row">
            <button type="button" className="btn btn-ghost" disabled={busy || !saved} onClick={propose}>{busy ? 'Working…' : 'Propose text'}</button>
            {!saved && <span className="cw-small cw-warn-text">Save first: the writer reads the saved draft.</span>}
          </div>
        </>
      )}
      {err && <p className="cw-err">{err}</p>}
      {runs && runs.length === 0 && <p className="dim cw-small">No proposals yet.</p>}
      {runs && runs.map((r) => (
        <article key={r.id} className="cw-suggestion">
          <p className="cw-small">
            <strong className={r.state === 'proposed' ? '' : 'cw-warn-text'}>{RUN_STATE[r.state]}</strong>
            <span className="dim"> · {when(r.created_at)} · {r.model_served || r.model_asked}
              {(r.model_asked || '').startsWith('claude-code/')
                ? ' · written in Claude Code (not metered per proposal)'
                : r.cost_usd != null ? ` · $${r.cost_usd.toFixed(5)}` : ' · cost not reported'}
              {r.used_at ? ` · used ${when(r.used_at)}` : ''}</span>
          </p>
          {r.instructions && <p className="dim cw-small">Instructions: {r.instructions}</p>}
          {r.reasons.length > 0 && <ul className="cw-evidence">{r.reasons.map((x) => <li key={x}>{x}</li>)}</ul>}
          {r.proposal && (
            <>
              {r.proposal.title && <p><strong>{r.proposal.title}</strong></p>}
              <p className="cw-note-body">{r.proposal.text}</p>
              {r.proposal.first_comment && (
                <p className="cw-small"><span className="dim">First comment / reply: </span>{r.proposal.first_comment}</p>
              )}
              {r.proposal.editor_note && <p className="dim cw-small">Note from the writer: {r.proposal.editor_note}</p>}
            </>
          )}
          {r.fit && <p className="cw-small">Fit check on this text: {r.fit.summary}</p>}
          {r.state === 'proposed' && (
            <div className="cw-row">
              <button type="button" className="btn btn-ghost" disabled={busy || !saved} onClick={() => use(r.id)}>
                Use this text
              </button>
              <span className="dim cw-small">Replaces the draft’s text; the old text is kept on this proposal.</span>
            </div>
          )}
        </article>
      ))}
    </div>
  )
}

function FitReport({ report, stale, ticks, onTick, sha, saved }) {
  if (!report) return <p className="dim cw-small">Not checked yet. Save and check to see how it fits the platform’s rules.</p>
  const order = { fail: 0, warn: 1, unchecked: 2, manual: 3, pass: 4 }
  const rows = [...report.results].sort((a, b) => order[a.outcome] - order[b.outcome])
  const manual = rows.filter((r) => r.outcome === 'manual')
  const done = manual.filter((r) => ticks[r.note_id]?.ticked && ticks[r.note_id].content_sha === sha).length
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
                ? (
                  <label className="cw-check">
                    <input type="checkbox" disabled={!saved} checked={!!ticks[r.note_id]?.ticked}
                      onChange={(e) => onTick(r.note_id, e.target.checked)} /> {OUTCOME_LABEL.manual}
                  </label>
                )
                : OUTCOME_LABEL[r.outcome]}
            </span>
            <span>
              {r.rule}
              <span className="dim cw-small"> — {r.detail}{r.for_all_platforms ? ' (all platforms)' : ''}</span>
              {ticks[r.note_id]?.ticked && (
                <span className={`cw-small ${ticks[r.note_id].content_sha === sha ? 'dim' : 'cw-warn-text'}`}>
                  {' '}· ticked {when(ticks[r.note_id].at)}{ticks[r.note_id].by ? ` by ${ticks[r.note_id].by}` : ''}
                  {ticks[r.note_id].content_sha !== sha && ', before the last edit: look again'}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
      {manual.length > 0 && (
        <p className="dim cw-small">
          {done} of {manual.length} checked by hand against the saved text. Ticks are saved with who and when{saved ? '' : '; save the draft to tick'}.
        </p>
      )}
    </div>
  )
}
