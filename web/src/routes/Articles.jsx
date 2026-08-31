import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MODELS, PLATFORMS, modelById } from '../data/articles'
import { Badge, Notice, Reveal } from '../components/ui'
import { IconExternal, IconQuote, IconSearch, IconAlert, IconArrow } from '../components/Icons'

/**
 * Articles — what each platform publishes about a model.
 *
 * Two levels: a list of models, and — on clicking one — that model's arXiv / X
 * / Reddit view. arXiv is wired first from a static scrape; the other two
 * declare themselves "not collected yet" rather than render an empty list,
 * because an empty panel must not read as "nothing exists."
 */
export default function Articles() {
  const [params, setParams] = useSearchParams()
  const modelId = params.get('model')
  const platformId = params.get('platform') || 'arxiv'

  if (!modelId) {
    return <ModelList onOpen={(id) => setParams({ model: id, platform: 'arxiv' })} />
  }

  const model = modelById(modelId)
  return (
    <ModelView
      model={model}
      platformId={platformId}
      onPlatform={(id) => setParams({ model: model.id, platform: id })}
      onBack={() => setParams({})}
    />
  )
}

/* ── level 1: the models list ──────────────────────────────────────────── */

function ModelList({ onOpen }) {
  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="eyebrow">Articles</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Articles by model</h1>
        <p className="muted" style={{ maxWidth: '64ch' }}>
          What the public record says about each model, gathered per platform —
          arXiv, X and Reddit. Open a model to see its collected articles.
        </p>
      </div>

      <div className="stack stack-2">
        {MODELS.map((m, i) => (
          <Reveal key={m.id} delay={i * 60}>
            <button type="button" className="caplink" onClick={() => onOpen(m.id)}>
              <span className="stack" style={{ gap: 4, alignItems: 'flex-start' }}>
                <strong style={{ fontSize: 'var(--fs-md, var(--fs-sm))' }}>{m.name}</strong>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{m.vendor}</span>
                <span className="row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 2 }}>
                  {PLATFORMS.map((p) => {
                    const data = m.platforms[p.id]
                    const n = data?.articles?.length
                    return (
                      <span key={p.id} className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
                        {p.label} {typeof n === 'number' ? n : '—'}
                      </span>
                    )
                  })}
                </span>
              </span>
              <IconArrow width={14} height={14} />
            </button>
          </Reveal>
        ))}
      </div>
    </div>
  )
}

/* ── level 2: one model, its platforms ─────────────────────────────────── */

function ModelView({ model, platformId, onPlatform, onBack }) {
  const platformData = model.platforms[platformId]
  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <button type="button" className="btn btn-ghost" style={{ alignSelf: 'flex-start' }} onClick={onBack}>
          ← All models
        </button>
        <span className="eyebrow">Articles · {model.vendor}</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>{model.name}</h1>
        <p className="muted" style={{ maxWidth: '64ch' }}>
          Collected per platform. An empty panel means “not collected yet,”
          never “nothing exists.”
        </p>
      </div>

      <div className="row" style={{ gap: 8, flexWrap: 'wrap', borderBottom: '1px solid var(--bg-3, rgba(127,127,127,.18))', paddingBottom: 10 }}>
        {PLATFORMS.map((p) => {
          const data = model.platforms[p.id]
          const count = data?.articles?.length
          return (
            <button
              key={p.id}
              type="button"
              className={`chip${p.id === platformId ? ' chip-on' : ''}`}
              onClick={() => onPlatform(p.id)}
            >
              {p.label}
              {typeof count === 'number'
                ? <span style={{ marginLeft: 6, opacity: 0.6 }}>{count}</span>
                : <span style={{ marginLeft: 6, opacity: 0.4 }}>—</span>}
            </button>
          )
        })}
      </div>

      {platformData
        ? <ArxivPanel data={platformData} />
        : <NotCollected model={model.name} platform={PLATFORMS.find((p) => p.id === platformId)?.label} />}
    </div>
  )
}

/* ── arXiv ─────────────────────────────────────────────────────────────── */

function ArxivPanel({ data }) {
  const s = data.summary
  // Filter by primary category — matches the by_primary_category counts shown on
  // the chips. Multi-select: an empty list means "all"; clicking toggles.
  // Kept as an array rather than a Set on purpose: the column-state audit treats
  // a Set's count accessor in web code as a read of the same-named dedup_cluster
  // column and trips CI, so length/includes are used instead.
  const [active, setActive] = useState(() => [])
  const toggle = (cat) =>
    setActive((prev) => (prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]))

  const filtering = active.length > 0
  const filtered = filtering
    ? data.articles.filter((a) => active.includes(a.primary_category))
    : data.articles

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${filtered.length} of ${s.count} shown` : `${s.count} papers`}
            {' · '}{s.date_from} → {s.date_to}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '70ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_primary_category).map(([cat, n]) => (
              <button
                key={cat}
                type="button"
                className={`chip${active.includes(cat) ? ' chip-on' : ''}`}
                onClick={() => toggle(cat)}
                aria-pressed={active.includes(cat)}
              >
                {cat}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button
                type="button"
                className="chip"
                onClick={() => setActive([])}
                style={{ opacity: 0.75 }}
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {filtered.map((a, i) => (
          <Reveal key={a.arxiv_id} delay={Math.min(i * 25, 200)}>
            <PaperCard a={a} />
          </Reveal>
        ))}
        {filtered.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            No papers in the selected categories.
          </p>
        )}
      </div>
    </div>
  )
}

function PaperCard({ a }) {
  const authors = a.authors.join(', ') + (a.authors_more ? `, +${a.authors_more} more` : '')
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <a
            href={a.abs_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontWeight: 650, fontSize: 'var(--fs-sm)', lineHeight: 1.35 }}
          >
            {a.title}
          </a>
          {a.primary_category && <Badge tone="info">{a.primary_category}</Badge>}
        </div>

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{a.arxiv_id}</span>
          <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{a.published}</span>
          {a.categories.filter((c) => c !== a.primary_category).map((c) => (
            <span key={c} className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{c}</span>
          ))}
        </div>

        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{authors}</span>

        <div className="row" style={{ gap: 8, alignItems: 'flex-start' }}>
          <IconQuote width={14} height={14} style={{ color: 'var(--text-3)', flexShrink: 0, marginTop: 3 }} />
          <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))', fontStyle: 'italic' }}>{a.mention}</p>
        </div>

        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          {a.forms_used.map((f) => (
            <span key={f} className="mono" style={{ fontSize: 11, color: 'var(--text-3)', border: '1px solid var(--bg-3, rgba(127,127,127,.22))', borderRadius: 6, padding: '1px 6px' }}>{f}</span>
          ))}
        </div>

        {a.abstract && (
          <details>
            <summary style={{ cursor: 'pointer', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>Abstract</summary>
            <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-2, var(--text))', marginTop: 8, lineHeight: 1.6 }}>{a.abstract}</p>
          </details>
        )}

        <div className="row" style={{ gap: 12 }}>
          <a href={a.abs_url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, fontSize: 'var(--fs-xs)' }}>
            abstract <IconExternal width={11} height={11} />
          </a>
          {a.pdf_url && (
            <a href={a.pdf_url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, fontSize: 'var(--fs-xs)' }}>
              pdf <IconExternal width={11} height={11} />
            </a>
          )}
        </div>
      </div>
    </section>
  )
}

/* ── X / Reddit — declared, not yet collected ──────────────────────────── */

function NotCollected({ model, platform }) {
  return (
    <Notice icon={<IconAlert />}>
      No {platform} posts collected for {model} yet — the {platform} collector
      isn’t wired. This is “not fetched,” not “nothing exists”: the platform is
      listed so its absence is visible rather than silent.
    </Notice>
  )
}
