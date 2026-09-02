import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MODELS, PLATFORMS, modelById } from '../data/articles'
import { Badge, Notice, Reveal, Stat } from '../components/ui'
import { IconExternal, IconQuote, IconSearch, IconAlert, IconArrow } from '../components/Icons'

/**
 * Articles — what each platform publishes about a model.
 *
 * Two levels: a list of models, and — on clicking one — that model's arXiv / X /
 * Reddit / Hacker News view. arXiv is wired first from a static scrape; the other two
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
          arXiv, X, Reddit and Hacker News. Open a model to see its collected articles.
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
                    const n = data?.articles?.length ?? data?.posts?.length
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
          const count = data?.articles?.length ?? data?.posts?.length
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

      {!platformData
        ? <NotCollected model={model.name} platform={PLATFORMS.find((p) => p.id === platformId)?.label} />
        : platformData.platform === 'x'
          ? <XPanel data={platformData} />
          : platformData.platform === 'reddit'
            ? <RedditPanel data={platformData} />
            : platformData.platform === 'hn'
              ? <HNPanel data={platformData} />
              : platformData.platform === 'devto'
                ? <DevtoPanel data={platformData} />
                : platformData.platform === 'tiktok' || platformData.platform === 'instagram'
                  ? <SocialPanel data={platformData} />
                  : platformData.platform === 'hf'
                    ? <HFPanel data={platformData} />
                    : platformData.platform === 'hashnode'
                      ? <HashnodePanel data={platformData} />
                      : platformData.platform === 'wordpress'
                        ? <WordPressPanel data={platformData} />
                        : <ArxivPanel data={platformData} />}
    </div>
  )
}

/* ── arXiv ─────────────────────────────────────────────────────────────── */

function ArxivPanel({ data }) {
  const s = data.summary
  // Filter by primary category — matches the by_primary_category counts on the
  // chips. Single-select: null means "all"; clicking a chip shows only it, and
  // clicking it again clears back to all.
  const [active, setActive] = useState(null)
  const toggle = (cat) => setActive((prev) => (prev === cat ? null : cat))

  const filtering = active != null
  const filtered = filtering
    ? data.articles.filter((a) => a.primary_category === active)
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
                className={`chip${active === cat ? ' chip-on' : ''}`}
                onClick={() => toggle(cat)}
                aria-pressed={active === cat}
              >
                {cat}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button
                type="button"
                className="chip"
                onClick={() => setActive(null)}
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

/* ── X / Twitter ───────────────────────────────────────────────────────── */

const TYPE_LABEL = {
  deep_analysis: 'Deep analysis',
  benchmark: 'Benchmark',
  usage_demo: 'Usage demo',
  workflow: 'Workflow',
  comparison: 'Comparison',
  opinion: 'Opinion',
  announcement: 'Announcement',
  news_roundup: 'News roundup',
  promo: 'Promo',
  tutorial: 'Tutorial',
  question: 'Question',
  cost: 'Cost & economics',
  hardware: 'Local & hardware',
  production: 'Production & dissent',
  first_hand: 'First-hand analysis',
  news_summary: 'News summary',
  repo: 'Model repo',
  discussion: 'Discussion',
  paper: 'Paper',
  core: 'Core',
  adjacent: 'Adjacent',
  passing: 'Passing mention',
  out_of_window: 'Out of window',
  listicle: 'Listicle',
}

const fmt = (n) =>
  n == null ? '—'
    : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M`
      : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K`
        : String(n)

function XPanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  // Single-select content-type filter — null is "all"; clicking a chip shows only it.
  const [active, setActive] = useState(null)
  const toggle = (t) => setActive((prev) => (prev === t ? null : t))
  const filtering = active != null
  const posts = filtering ? data.posts.filter((p) => p.content_type === active) : data.posts

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${posts.length} of ${s.count} shown` : `${s.count} labelled posts`}
            {' · '}{sweep.date_from} → {sweep.date_to}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.keyword_posts)} l="keyword posts" />
            <Stat n={fmt(sweep.distinct_authors)} l="authors" />
            <Stat n={fmt(sweep.total_engagements)} l="engagements" />
            <Stat n={fmt(sweep.total_views)} l="views" />
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_content_type).map(([t, n]) => (
              <button
                key={t}
                type="button"
                className={`chip${active === t ? ' chip-on' : ''}`}
                onClick={() => toggle(t)}
                aria-pressed={active === t}
              >
                {TYPE_LABEL[t] || t}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button type="button" className="chip" style={{ opacity: 0.75 }} onClick={() => setActive(null)}>
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {posts.map((p, i) => (
          <Reveal key={`${p.status_url || p.handle}-${i}`} delay={Math.min(i * 15, 200)}>
            <PostCard p={p} />
          </Reveal>
        ))}
        {posts.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No posts in the selected types.</p>
        )}
      </div>
    </div>
  )
}

function PostCard({ p }) {
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <div className="row" style={{ gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <a href={p.profile_url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 650, fontSize: 'var(--fs-sm)' }}>
              @{p.handle}
            </a>
            <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{p.date}</span>
            {p.followers != null && (
              <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>· {fmt(p.followers)} followers</span>
            )}
            {p.language && <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{p.language}</span>}
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
            <Badge tone="info">{TYPE_LABEL[p.content_type] || p.content_type}</Badge>
            {p.subject && <Badge tone="pass">subject</Badge>}
          </div>
        </div>

        <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))' }}>{p.quote}</p>

        <div className="row" style={{ gap: 12, flexWrap: 'wrap', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          <span className="mono">{fmt(p.engagements)} eng</span>
          <span className="mono">{fmt(p.views)} views</span>
          {p.likes != null && <span className="mono">{fmt(p.likes)} likes</span>}
          {p.rt != null && <span className="mono">{fmt(p.rt)} RT</span>}
          {p.replies != null && <span className="mono">{fmt(p.replies)} replies</span>}
          {p.saves != null && <span className="mono">{fmt(p.saves)} saves</span>}
          {p.status_url && (
            <a href={p.status_url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, marginLeft: 'auto' }}>
              view on X <IconExternal width={11} height={11} />
            </a>
          )}
        </div>
      </div>
    </section>
  )
}

/* ── Reddit ────────────────────────────────────────────────────────────── */

function RedditPanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  const [active, setActive] = useState(null)
  const toggle = (t) => setActive((prev) => (prev === t ? null : t))
  const filtering = active != null
  const posts = filtering ? data.posts.filter((p) => p.content_type === active) : data.posts

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${posts.length} of ${s.count} shown` : `${s.count} labelled posts`}
            {s.date_from ? ` · ${s.date_from} → ${s.date_to}` : ''}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.records)} l="records" />
            <Stat n={fmt(sweep.literal_matches)} l="literal matches" />
            <Stat n={fmt(sweep.subreddits)} l="subreddits" />
            <Stat n={fmt(sweep.authors)} l="authors" />
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_content_type).map(([t, n]) => (
              <button
                key={t}
                type="button"
                className={`chip${active === t ? ' chip-on' : ''}`}
                onClick={() => toggle(t)}
                aria-pressed={active === t}
              >
                {TYPE_LABEL[t] || t}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button type="button" className="chip" style={{ opacity: 0.75 }} onClick={() => setActive(null)}>
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {posts.map((p, i) => (
          <Reveal key={`${p.url || p.rank}-${i}`} delay={Math.min(i * 12, 200)}>
            <RedditPostCard p={p} />
          </Reveal>
        ))}
        {posts.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No posts in the selected types.</p>
        )}
      </div>
    </div>
  )
}

function RedditPostCard({ p }) {
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <a href={p.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 650, fontSize: 'var(--fs-sm)', lineHeight: 1.35 }}>
            {p.title}
          </a>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
            <Badge tone="info">{TYPE_LABEL[p.content_type] || p.content_type}</Badge>
            {p.subject && <Badge tone="pass">subject</Badge>}
          </div>
        </div>

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          <span className="mono">r/{p.subreddit}</span>
          <span className="dim">u/{p.author}</span>
          {p.date && <span className="dim">{p.date}</span>}
          <span className="mono">▲ {fmt(p.score)}</span>
          {p.comments != null && <span className="mono">{fmt(p.comments)} comments</span>}
        </div>

        {p.excerpt && <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))' }}>{p.excerpt}</p>}

        {p.why_label && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', fontStyle: 'italic', borderLeft: '2px solid var(--bg-3, rgba(127,127,127,.25))', paddingLeft: 8 }}>
            Why {TYPE_LABEL[p.content_type] || p.content_type}: {p.why_label}
          </p>
        )}

        <div className="row">
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, fontSize: 'var(--fs-xs)' }}>
            view on Reddit <IconExternal width={11} height={11} />
          </a>
        </div>
      </div>
    </section>
  )
}

/* ── Hacker News ───────────────────────────────────────────────────────── */

function HNPanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  const [active, setActive] = useState(null)
  const toggle = (t) => setActive((prev) => (prev === t ? null : t))
  const filtering = active != null
  const posts = filtering ? data.posts.filter((p) => p.content_type === active) : data.posts

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${posts.length} of ${s.count} shown` : `${s.count} analysis cases`}
            {s.date_from ? ` · ${s.date_from} → ${s.date_to}` : ''}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.subject_threads)} l="subject threads" />
            <Stat n={fmt(sweep.threads_with_discussion)} l="with discussion" />
            <Stat n={fmt(sweep.comments_fetched)} l="comments read" />
            <Stat n={fmt(sweep.cases)} l="analysis cases" />
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_content_type).map(([t, n]) => (
              <button
                key={t}
                type="button"
                className={`chip${active === t ? ' chip-on' : ''}`}
                onClick={() => toggle(t)}
                aria-pressed={active === t}
              >
                {TYPE_LABEL[t] || t}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button type="button" className="chip" style={{ opacity: 0.75 }} onClick={() => setActive(null)}>
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {posts.map((p) => (
          <Reveal key={p.hn_id} delay={Math.min(p.rank * 12, 200)}>
            <HNPostCard p={p} />
          </Reveal>
        ))}
        {posts.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No cases in the selected type.</p>
        )}
      </div>
    </div>
  )
}

function HNPostCard({ p }) {
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <p style={{ fontWeight: 650, fontSize: 'var(--fs-sm)', lineHeight: 1.4 }}>{p.note}</p>
          <Badge tone="info">{TYPE_LABEL[p.content_type] || p.content_type}</Badge>
        </div>

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          <span className="dim">{p.author}</span>
          <span className="dim">in “{p.thread}”</span>
          <span className="mono">▲ {fmt(p.points)}</span>
          {p.date && <span className="dim">{p.date}</span>}
        </div>

        {p.quote && (
          <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))', fontStyle: 'italic' }}>
            {p.quote}
          </p>
        )}

        <div className="row">
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, fontSize: 'var(--fs-xs)' }}>
            view on Hacker News <IconExternal width={11} height={11} />
          </a>
        </div>
      </div>
    </section>
  )
}

/* ── dev.to ────────────────────────────────────────────────────────────── */

function DevtoPanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  const [active, setActive] = useState(null)
  const toggle = (t) => setActive((prev) => (prev === t ? null : t))
  const filtering = active != null
  const posts = filtering ? data.posts.filter((p) => p.content_type === active) : data.posts

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${posts.length} of ${s.count} shown` : `${s.count} usable articles`}
            {s.date_from ? ` · ${s.date_from} → ${s.date_to}` : ''}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.posts)} l="posts fetched" />
            <Stat n={fmt(sweep.distinct)} l="distinct" />
            <Stat n={fmt(sweep.authors)} l="authors" />
            <Stat n={fmt(sweep.usable)} l="usable" />
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_content_type).map(([t, n]) => (
              <button
                key={t}
                type="button"
                className={`chip${active === t ? ' chip-on' : ''}`}
                onClick={() => toggle(t)}
                aria-pressed={active === t}
              >
                {TYPE_LABEL[t] || t}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button type="button" className="chip" style={{ opacity: 0.75 }} onClick={() => setActive(null)}>
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {posts.map((p) => (
          <Reveal key={p.rank} delay={Math.min(p.rank * 10, 200)}>
            <DevtoPostCard p={p} />
          </Reveal>
        ))}
        {posts.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No articles in the selected type.</p>
        )}
      </div>
    </div>
  )
}

function DevtoPostCard({ p }) {
  const artifacts = p.distinct_artifacts
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <a
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontWeight: 650, fontSize: 'var(--fs-sm)', lineHeight: 1.4 }}
          >
            {p.title}
          </a>
          <Badge tone="info">{TYPE_LABEL[p.content_type] || p.content_type}</Badge>
        </div>

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          <span className="dim">{p.author}</span>
          <span className="dim">{p.stratum}</span>
          {p.date && <span className="dim">{p.date}</span>}
          {p.reactions > 0 && <span className="mono">♥ {fmt(p.reactions)}</span>}
          {artifacts > 0 && <span className="mono">{artifacts} artifact{artifacts === 1 ? '' : 's'}</span>}
        </div>

        {p.excerpt && (
          <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))', fontStyle: 'italic' }}>
            {p.excerpt}
          </p>
        )}

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          <span className="dim">{p.provenance}</span>
          {p.cross_posted && p.cross_posted !== 'no' && <span className="dim">· cross-posted</span>}
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, marginLeft: 'auto' }}>
            view on dev.to <IconExternal width={11} height={11} />
          </a>
        </div>
      </div>
    </section>
  )
}

/* ── TikTok & Instagram (social) ───────────────────────────────────────── */

// One panel for both: ranked by engagement, no per-post category to filter on.
// The sweep line names the count and what it was ranked by; each card leads with
// the metrics that platform exposes (TikTok has views/shares, Instagram does not).
function SocialPanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  const isTikTok = data.platform === 'tiktok'
  const rankedBy = isTikTok ? 'views' : 'likes + comments'

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {`top ${s.count} by ${rankedBy}`}
            {s.date_from ? ` · ${s.date_from} → ${s.date_to}` : ''}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.posts)} l="on-target posts" />
            {isTikTok && <Stat n={fmt(sweep.views)} l="views" />}
            <Stat n={fmt(sweep.likes)} l={isTikTok ? 'likes' : 'likes (floor)'} />
            <Stat n={fmt(sweep.comments)} l="comments" />
            {isTikTok && <Stat n={fmt(sweep.shares)} l="shares" />}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {data.posts.map((p) => (
          <Reveal key={p.rank} delay={Math.min(p.rank * 10, 200)}>
            <SocialPostCard p={p} tiktok={isTikTok} />
          </Reveal>
        ))}
      </div>
    </div>
  )
}

function SocialPostCard({ p, tiktok }) {
  const label = tiktok ? 'view on TikTok' : 'view on Instagram'
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
            <span className="mono" style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>#{p.rank}</span>
            <span style={{ fontWeight: 650, fontSize: 'var(--fs-sm)' }}>{p.creator}</span>
          </div>
          {p.date && <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>{p.date}</span>}
        </div>

        <div className="row" style={{ gap: 12, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          {tiktok && p.views != null && <span className="mono">▶ {fmt(p.views)} views</span>}
          {p.likes != null && <span className="mono">♥ {fmt(p.likes)}</span>}
          {p.comments != null && <span className="mono">💬 {fmt(p.comments)}</span>}
          {tiktok && p.shares != null && <span className="mono">↗ {fmt(p.shares)}</span>}
          {tiktok && p.engagement_rate && <span className="dim">ER {p.engagement_rate}</span>}
        </div>

        {p.caption && (
          <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))' }}>
            {p.caption}
          </p>
        )}

        <div className="row">
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, fontSize: 'var(--fs-xs)' }}>
            {label} <IconExternal width={11} height={11} />
          </a>
        </div>
      </div>
    </section>
  )
}

/* ── Hugging Face ──────────────────────────────────────────────────────── */

// One panel over three surfaces (repo / discussion / paper), filtered by the
// same single-select chips as the other platforms. The chip counts are what's
// shown per surface; the sweep stats above carry the full totals.
function HFPanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  const [active, setActive] = useState(null)
  const toggle = (t) => setActive((prev) => (prev === t ? null : t))
  const filtering = active != null
  const posts = filtering ? data.posts.filter((p) => p.content_type === active) : data.posts

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${posts.length} of ${s.count} shown` : `${s.count} items across 3 surfaces`}
            {s.date_from ? ` · ${s.date_from} → ${s.date_to}` : ''}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.repos_found)} l="model repos" />
            <Stat n={fmt(sweep.downloads_total)} l="downloads" />
            <Stat n={fmt(sweep.discussions)} l="discussions" />
            <Stat n={fmt(sweep.papers)} l="papers" />
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_content_type).map(([t, n]) => (
              <button
                key={t}
                type="button"
                className={`chip${active === t ? ' chip-on' : ''}`}
                onClick={() => toggle(t)}
                aria-pressed={active === t}
              >
                {TYPE_LABEL[t] || t}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button type="button" className="chip" style={{ opacity: 0.75 }} onClick={() => setActive(null)}>
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {posts.map((p, i) => (
          <Reveal key={p.url || `${p.content_type}-${p.rank}`} delay={Math.min(i * 8, 200)}>
            <HFPostCard p={p} />
          </Reveal>
        ))}
        {posts.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No items on the selected surface.</p>
        )}
      </div>
    </div>
  )
}

function HFPostCard({ p }) {
  const isRepo = p.content_type === 'repo'
  const isPaper = p.content_type === 'paper'
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <a
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mono"
            style={{ fontWeight: 650, fontSize: 'var(--fs-sm)', lineHeight: 1.4, wordBreak: 'break-word' }}
          >
            {p.title}
          </a>
          <Badge tone={isRepo ? 'mute' : 'info'}>
            {p.official ? 'Official repo' : (TYPE_LABEL[p.content_type] || p.content_type)}
          </Badge>
        </div>

        {isRepo ? (
          <div className="row" style={{ gap: 12, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
            <span className="mono">↓ {fmt(p.downloads)}</span>
            {p.likes != null && <span className="mono">♥ {fmt(p.likes)}</span>}
            {p.licence && <span className="dim">{p.licence}</span>}
            {p.discussions != null && <span className="dim">{fmt(p.discussions)} discussions</span>}
            {p.modified && <span className="dim">updated {p.modified}</span>}
          </div>
        ) : (
          <div className="row" style={{ gap: 10, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
            {isPaper ? (
              <>
                <span className="mono">▲ {fmt(p.upvotes)}</span>
                {p.authors != null && <span className="dim">{fmt(p.authors)} authors</span>}
                {p.names_v4pro && <span className="dim">names V4 Pro</span>}
              </>
            ) : (
              <>
                <span className="dim">{p.author}</span>
                <span className="dim">in {p.repo}</span>
                <span className="dim">{p.disc_type}</span>
                {p.comments != null && <span className="mono">💬 {fmt(p.comments)}</span>}
                {p.vendor_reply && <span className="dim">vendor replied</span>}
              </>
            )}
            {p.date && <span className="dim">{p.date}</span>}
            {p.artifacts != null && <span className="mono">{p.artifacts} artifact{p.artifacts === 1 ? '' : 's'}</span>}
          </div>
        )}

        {p.excerpt && (
          <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))', fontStyle: 'italic' }}>
            {p.excerpt}
          </p>
        )}

        <div className="row">
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, fontSize: 'var(--fs-xs)' }}>
            view on Hugging Face <IconExternal width={11} height={11} />
          </a>
        </div>
      </div>
    </section>
  )
}

/* ── Hashnode ──────────────────────────────────────────────────────────── */

// A thin surface, filtered by relevance (core / adjacent / passing / out of
// window). Each card carries the sweep's own provenance read and evidence note
// rather than a body excerpt, because that read is the point on this platform.
function HashnodePanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  const [active, setActive] = useState(null)
  const toggle = (t) => setActive((prev) => (prev === t ? null : t))
  const filtering = active != null
  const posts = filtering ? data.posts.filter((p) => p.content_type === active) : data.posts

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${posts.length} of ${s.count} shown` : `${s.count} posts returned`}
            {s.date_from ? ` · ${s.date_from} → ${s.date_to}` : ''}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.posts)} l="in-window" />
            <Stat n={fmt(sweep.core)} l="core" />
            <Stat n={fmt(sweep.first_hand)} l="first-hand" />
            <Stat n={fmt(sweep.authors)} l="authors" />
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_content_type).map(([t, n]) => (
              <button
                key={t}
                type="button"
                className={`chip${active === t ? ' chip-on' : ''}`}
                onClick={() => toggle(t)}
                aria-pressed={active === t}
              >
                {TYPE_LABEL[t] || t}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button type="button" className="chip" style={{ opacity: 0.75 }} onClick={() => setActive(null)}>
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {posts.map((p, i) => (
          <Reveal key={p.url || p.rank} delay={Math.min(i * 12, 200)}>
            <HashnodePostCard p={p} />
          </Reveal>
        ))}
        {posts.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No posts at the selected relevance.</p>
        )}
      </div>
    </div>
  )
}

function HashnodePostCard({ p }) {
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <a
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontWeight: 650, fontSize: 'var(--fs-sm)', lineHeight: 1.4 }}
          >
            {p.title}
          </a>
          <Badge tone="info">{TYPE_LABEL[p.content_type] || p.content_type}</Badge>
        </div>

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          {p.author && <span className="dim">{p.author}</span>}
          {p.publication && <span className="mono">{p.publication}</span>}
          {p.date && <span className="dim">{p.date}</span>}
          {p.read_time && <span className="dim">{p.read_time} read</span>}
          {p.views != null && <span className="mono">{fmt(p.views)} views</span>}
          {p.post_type && <span className="dim">· {p.post_type}</span>}
        </div>

        {p.whose_result && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            Whose result: {p.whose_result}
          </p>
        )}

        {p.excerpt && (
          <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))', fontStyle: 'italic' }}>
            {p.excerpt}
          </p>
        )}

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          {p.strong_artifacts != null && <span className="mono">{p.strong_artifacts} strong artifact{p.strong_artifacts === 1 ? '' : 's'}</span>}
          {p.cross_posted && <span className="dim">· cross-posted from {p.cross_posted}</span>}
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, marginLeft: 'auto' }}>
            view on Hashnode <IconExternal width={11} height={11} />
          </a>
        </div>
      </div>
    </section>
  )
}

/* ── WordPress ─────────────────────────────────────────────────────────── */

// The usable set (>=2 artifacts, non-injected), filtered by post type. The
// provenance line is prominent because this surface is mostly relayed numbers —
// only 3 of 73 posts are first-hand.
function WordPressPanel({ data }) {
  const s = data.summary
  const sweep = s.sweep || {}
  const [active, setActive] = useState(null)
  const toggle = (t) => setActive((prev) => (prev === t ? null : t))
  const filtering = active != null
  const posts = filtering ? data.posts.filter((p) => p.content_type === active) : data.posts

  return (
    <div className="stack stack-3">
      <section className="card card-flush">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <IconSearch width={14} height={14} style={{ color: 'var(--text-3)' }} />
            <span className="label">{data.source}</span>
          </div>
          <span className="label">
            {filtering ? `${posts.length} of ${s.count} shown` : `${s.count} usable posts`}
            {s.date_from ? ` · ${s.date_from} → ${s.date_to}` : ''}
          </span>
        </div>
        <div className="card-body stack stack-2">
          <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '72ch' }}>{data.note}</p>
          <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
            <Stat n={fmt(sweep.in_window)} l="in-window" />
            <Stat n={fmt(sweep.sites)} l="sites" />
            <Stat n={fmt(sweep.first_hand)} l="first-hand" />
            <Stat n={fmt(sweep.injected)} l="injected (excl.)" />
          </div>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {Object.entries(s.by_content_type).map(([t, n]) => (
              <button
                key={t}
                type="button"
                className={`chip${active === t ? ' chip-on' : ''}`}
                onClick={() => toggle(t)}
                aria-pressed={active === t}
              >
                {TYPE_LABEL[t] || t}<span style={{ marginLeft: 5, opacity: 0.6 }}>{n}</span>
              </button>
            ))}
            {filtering && (
              <button type="button" className="chip" style={{ opacity: 0.75 }} onClick={() => setActive(null)}>
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      <div className="stack stack-2">
        {posts.map((p, i) => (
          <Reveal key={p.url || p.rank} delay={Math.min(i * 10, 200)}>
            <WordPressPostCard p={p} />
          </Reveal>
        ))}
        {posts.length === 0 && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>No posts of the selected type.</p>
        )}
      </div>
    </div>
  )
}

function WordPressPostCard({ p }) {
  return (
    <section className="card card-flush">
      <div className="card-body stack stack-2">
        <div className="row" style={{ gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <a
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontWeight: 650, fontSize: 'var(--fs-sm)', lineHeight: 1.4 }}
          >
            {p.title}
          </a>
          <Badge tone="info">{TYPE_LABEL[p.content_type] || p.content_type}</Badge>
        </div>

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          {p.author && <span className="dim">{p.author}{p.is_person ? '' : ' (unverified byline)'}</span>}
          {p.site && <span className="mono">{p.site}</span>}
          {p.date && <span className="dim">{p.date}</span>}
          {p.words != null && <span className="dim">{fmt(p.words)} words</span>}
          {p.comments > 0 && <span className="mono">💬 {fmt(p.comments)}</span>}
        </div>

        {p.provenance && (
          <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
            Provenance: {p.provenance}
          </p>
        )}

        {p.excerpt && (
          <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2, var(--text))', fontStyle: 'italic' }}>
            {p.excerpt}
          </p>
        )}

        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
          {p.artifacts != null && <span className="mono">{p.artifacts} artifact{p.artifacts === 1 ? '' : 's'}</span>}
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="row" style={{ gap: 4, marginLeft: 'auto' }}>
            view on WordPress <IconExternal width={11} height={11} />
          </a>
        </div>
      </div>
    </section>
  )
}

/* ── platforms with no data yet ────────────────────────────────────────── */

function NotCollected({ model, platform }) {
  return (
    <Notice icon={<IconAlert />}>
      No {platform} posts collected for {model} yet — the {platform} collector
      isn’t wired. This is “not fetched,” not “nothing exists”: the platform is
      listed so its absence is visible rather than silent.
    </Notice>
  )
}
