import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { boardPage, blogPosts } from '../api'
import Hero from '../components/Hero'
import SiteSearch from '../components/SiteSearch'
import Faq from '../components/Faq'
import BlogShowcase from '../components/BlogShowcase'
import { Reveal, Badge } from '../components/ui'

// Three questions a visitor arrives with, each answered by board pages.
// NAMES AND A COUNT, NOTHING ELSE. A bar sized by report count reads as a
// score, and a short one as a bad result when it only means few people have
// written about it yet; a plain "94 reports" pill is neither. The count is
// read live from `/board` (the board's own floor), never typed in here. Every
// slug was checked against the live board on 2026-09-29, and none repeats a
// hero chip.
const BROWSE = [
  {
    q: 'Which model for my job?', k: 'Best for', noun: 'jobs', key: 'jobs', route: 'jobs', tint: 'var(--info)',
    more: { label: 'All jobs', to: '/board?tab=best' },
    rows: [['coding-agent', 'Coding agents'], ['code-review', 'Code review'], ['extraction', 'Data extraction'],
      ['translation', 'Translation'], ['creative-writing', 'Creative writing'], ['terminal-agent', 'Terminal agents'],
      ['general-purpose', 'General purpose']],
  },
  {
    q: 'Can it do this well?', k: 'Capabilities', noun: '', key: 'caps', route: 'capabilities', tint: 'var(--pass)',
    more: { label: 'All capabilities', to: '/board?tab=cap' },
    rows: [['reasoning', 'Reasoning'], ['code-generation', 'Code generation'], ['long-context', 'Long context'],
      ['function-calling', 'Function calling'], ['structured-output', 'Structured output'], ['vision', 'Vision'],
      ['multimodal', 'Multimodal']],
  },
  {
    q: 'How does it measure up?', k: 'Metrics', noun: '', key: 'mets', route: 'metrics', tint: 'var(--warn)',
    more: { label: 'All metrics', to: '/board?tab=met' },
    rows: [['cost-per-token', 'Cost per million tokens'], ['cost-per-task', 'Cost per task'],
      ['tokens-per-second', 'Tokens per second'], ['time-to-first-token', 'Time to first token'],
      ['swe-bench-verified', 'SWE-bench Verified'], ['gpqa-diamond', 'GPQA Diamond'], ['arc-agi-3', 'ARC-AGI-3']],
  },
]

// "The models" and "AI model comparison": two boxes, and no model appears in
// both, so between them the section names eighteen models people search for.
// Every one has a page on the board (checked 2026-09-29). Links use the
// registry id, the readable form the compare page prefers in a shared URL.
// The entry count beside a model is read live from `/board`, by its label.
const MODELS = [
  { name: 'Claude Opus 5', provider: 'Anthropic', id: 'anthropic/claude-opus-5', label: 'Anthropic: Claude Opus 5' },
  { name: 'GPT-6 Astra', provider: 'OpenAI', id: 'openai/gpt-6-astra', label: 'OpenAI: GPT-6 Astra' },
  { name: 'DeepSeek V4 Flash', provider: 'DeepSeek', id: 'deepseek/deepseek-v4-flash', label: 'DeepSeek: DeepSeek V4 Flash 0423' },
  { name: 'Gemini 3.8 Flash', provider: 'Google', id: 'google/gemini-3.8-flash', label: 'Google: Gemini 3.8 Flash' },
  { name: 'Kimi K2.5', provider: 'Moonshot AI', id: 'moonshotai/kimi-k2.5', label: 'MoonshotAI: Kimi K2.5' },
  { name: 'Qwen3.8 27B', provider: 'Qwen', id: 'qwen/qwen3.8-27b', label: 'Qwen: Qwen3.8 27B' },
]
const PAIRS = [
  [{ name: 'Claude Sonnet 5', id: 'anthropic/claude-sonnet-5' }, { name: 'Claude Opus 4.8', id: 'anthropic/claude-opus-4.8' }],
  [{ name: 'Claude Haiku 4.5', id: 'anthropic/claude-haiku-4.5' }, { name: 'Gemini 3.7 Flash', id: 'google/gemini-3.7-flash' }],
  [{ name: 'GPT-5.6 Sol', id: 'openai/gpt-5.6-sol' }, { name: 'DeepSeek V4 Pro', id: 'deepseek/deepseek-v4-pro' }],
  [{ name: 'Kimi K3', id: 'moonshotai/kimi-k3' }, { name: 'Qwen3.6 27B', id: 'qwen/qwen3.6-27b' }],
  [{ name: 'Grok 4.7', id: 'x-ai/grok-4.7' }, { name: 'GPT-5.6 Luna', id: 'openai/gpt-5.6-luna' }],
  [{ name: 'GLM 5', id: 'z-ai/glm-5' }, { name: 'MiniMax M3', id: 'minimax/minimax-m3' }],
]

// Board entries naming a model, across every section; null while loading.
function entriesFor(board, label) {
  if (!board) return null
  let n = 0
  for (const key of ['jobs', 'caps', 'mets']) {
    for (const s of board[key] || []) for (const q of s.quotes || []) if (q.model_label === label) n += 1
  }
  return n
}

// "LLM leaderboard alternative": one panel holding what the board gives (a slim
// list) and one real entry laid out field by field, split by a rule; the
// heading and paragraph on the right. The entry is
// FIXED, like the hero's quotes - a verified quote in Best for · Coding
// agents, checked against the shared board on 2026-09-29 - so the first
// entry a visitor reads is never an unreviewed one.
const GIVES = [
  "The engineer's exact words",
  'Real production work, filed by job',
  'Split by job, capability and metric',
  'A link to every post it came from',
  'People, each counted once',
]
const ENTRY = {
  section: 'Best for · Coding agents',
  sectionTo: '/board/jobs/coding-agent',
  polarity: 'positive',
  quote: 'DeepSeek V4 Flash for 70% of traffic. Best cost-to-quality ratio in this group, period.',
  model: 'DeepSeek V4 Flash 0423',
  source: 'dev.to',
  url: 'https://dev.to/rileykim/i-benchmarked-chinas-top-4-llms-the-numbers-dont-lie-40d2',
}

// The closing call to action: a line that swipes through what the board is
// for, then three buttons - the board, the models, and the blogs written from
// the evidence. JS drives the swap rather than a CSS loop, so
// reduced motion can stop it outright - the global rule would only shorten a
// looping animation, which flickers instead of stopping. Screen readers get
// every line once, as text; the moving copy is hidden from them.
const CLOSING_LINES = ['Find the best AI model for the job.', 'Read real user experiences with AI models.', 'Go deeper with evidence-based AI blogs.']

function ClosingCta() {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    const t = setInterval(() => setI((n) => (n + 1) % CLOSING_LINES.length), 2600)
    return () => clearInterval(t)
  }, [])
  return (
    <div className="closing">
      <span className="eyebrow">Model Information Board</span>
      <h2 className="closing-h">
        <span className="sr-only">{CLOSING_LINES.join(' ')}</span>
        <span className="closing-swipe" aria-hidden="true">
          {CLOSING_LINES.map((line, n) => (
            <span key={line} className={`closing-line l${n}${n === i ? ' on' : ''}${n === (i + CLOSING_LINES.length - 1) % CLOSING_LINES.length ? ' out' : ''}`}>
              {line}
            </span>
          ))}
        </span>
      </h2>
      <p className="muted">Every AI model, every job, in the words of the engineers who ran it.</p>
      <div className="closing-actions">
        <Link to="/board" className="btn btn-primary btn-lg">Browse the board</Link>
        <Link to="/models" className="btn btn-primary btn-lg">See the models</Link>
        <Link to="/blogs" className="btn btn-primary btn-lg">Read the blogs</Link>
      </div>
    </div>
  )
}

// A pill: "94 reports" when the board has the section, "none yet" when it
// was read and does not, nothing while it loads or if it cannot be read.
function reportsPill(board, key, slug) {
  if (!board) return null
  const s = (board[key] || []).find((x) => x.slug === slug)
  if (!s || !s.reports) return <span className="browse-pill none">none yet</span>
  return <span className="browse-pill tnum">{s.reports} {s.reports === 1 ? 'report' : 'reports'}</span>
}

// The three Browse cards as a showcase: one in front, the other two standing
// behind it on either side. It turns one place every few seconds; hovering or
// focusing pauses it, a click or a tab onto a side card brings that card to
// the front (the click does not follow the card's links until it is in
// front), and the dots pick one directly. Reduced motion: it never turns by
// itself. Under 760px the cards simply stack.
const SHOWCASE_MS = 5200

function BrowseShowcase({ board }) {
  const [front, setFront] = useState(0)
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (paused || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    const t = setInterval(() => setFront((n) => (n + 1) % BROWSE.length), SHOWCASE_MS)
    return () => clearInterval(t)
  }, [paused])

  const place = (i) => {
    const d = (i - front + BROWSE.length) % BROWSE.length
    return d === 0 ? 'front' : d === 1 ? 'right' : 'left'
  }

  return (
    <div
      className="showcase"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className="showcase-stage">
        {BROWSE.map((c, i) => {
          const at = place(i)
          return (
            <div
              key={c.k}
              className={`showcase-item at-${at}`}
              onClickCapture={(e) => { if (at !== 'front') { e.preventDefault(); setFront(i) } }}
              onFocusCapture={() => at !== 'front' && setFront(i)}
            >
              <div className="browse-card" style={{ '--tint': c.tint }}>
                <span className="browse-q">{c.q}</span>
                <span className="browse-k">
                  {c.k}
                  {board?.counts?.[c.key] != null && <> · {board.counts[c.key]}{c.noun ? ` ${c.noun}` : ''}</>}
                </span>
                <ul className="browse-list">
                  {c.rows.map(([slug, name]) => (
                    <li key={slug}>
                      <Link to={`/board/${c.route}/${slug}`}>{name}</Link>
                      {reportsPill(board, c.key, slug)}
                    </li>
                  ))}
                </ul>
                <Link className="browse-more" to={c.more.to}>{c.more.label} →</Link>
              </div>
            </div>
          )
        })}
      </div>
      <div className="showcase-dots" role="group" aria-label="Choose a card">
        {BROWSE.map((c, i) => (
          <button
            key={c.k}
            type="button"
            className={i === front ? 'on' : ''}
            style={{ '--tint': c.tint }}
            aria-label={c.q}
            aria-pressed={i === front}
            onClick={() => setFront(i)}
          />
        ))}
      </div>
    </div>
  )
}

// The counts row under the hero. Every figure is read live from `/board`:
// models are the distinct models engineers reported on (not the registry,
// most of which nobody has written about), entries are the board's quotes.
// The board's payload carries no posts yet, so Blogs says so rather than
// showing a zero beside real figures. Nothing renders until the board is read.
function boardCounts(board) {
  if (!board) return null
  const sections = [...(board.jobs || []), ...(board.caps || []), ...(board.mets || [])]
  const models = new Set()
  let entries = 0
  for (const s of sections) {
    entries += s.quote_count || 0
    for (const m of s.models || []) models.add(m.model_label)
  }
  return { models: models.size, entries, blogs: (board.posts || []).length }
}

const fmtN = (n) => Number(n).toLocaleString('en-US')

export default function Landing() {
  const [board, setBoard] = useState(null)
  // THE BLOG COUNT IS THE POSTS A READER CAN OPEN: the Blogs page's own rule -
  // a run-written post once approved, and drafts from before run history.
  // `null` until read, so the row says "Soon" rather than a guessed 0.
  const [blogCount, setBlogCount] = useState(null)
  const stats = { ...boardCounts(board), blogs: blogCount }
  useEffect(() => {
    let alive = true
    boardPage().then((b) => alive && setBoard(b)).catch(() => {})
    blogPosts()
      .then((d) => alive && setBlogCount((d.posts || []).filter((p) => !p.review || p.review === 'approved').length))
      .catch(() => {})
    return () => { alive = false }
  }, [])

  return (
    <div className="landing">
      {/* ------------------------------------------------------------ hero */}
      <section className="hero shell">
        <Hero>
          <SiteSearch board={board} />
        </Hero>

      </section>

      {/* ---------------------------------------------------------- counts */}
      {stats && (
        <section className="shell counts-row" aria-label="The board today">
          <div className="counts">
            <div className="count"><b className="tnum">{fmtN(stats.models)}</b><span>Latest AI models discussed</span></div>
            <div className="count"><b className="tnum">{fmtN(stats.entries)}</b><span>board entries across jobs, capabilities and metrics</span></div>
            <div className="count">{stats.blogs
              ? <><b className="tnum">{fmtN(stats.blogs)}</b><span>blogs written from the evidence</span></>
              : <><b className="count-soon">Soon</b><span>blogs written from the evidence</span></>}</div>
          </div>
          <span className="counts-note">live from the board</span>
        </section>
      )}

      {/* ---------------------------------------------------- why trust it */}
      <section className="section shell" id="not-a-leaderboard">
        {/* the label sits above the row, over the right-hand column */}
        <div className="trust trust-top">
          <span />
          <span className="eyebrow trust-label">LLM leaderboard alternative</span>
        </div>
        <div className="trust">
          <Reveal>
            <div className="trust-panel">
              <div className="gives">
                <span className="gives-h">The Model Information Board gives you</span>
                <ul>
                  {GIVES.map((g) => <li key={g}>{g}</li>)}
                </ul>
              </div>
              <figure className="entry">
                <figcaption className="entry-cap">One real entry, as the board keeps it</figcaption>
                <dl className="entry-fields">
                  <dt>Section</dt>
                  <dd><Link to={ENTRY.sectionTo}>{ENTRY.section}</Link></dd>
                  <dt>Verdict</dt>
                  <dd><Badge tone="pass">{ENTRY.polarity}</Badge> <span className="dim">never a score</span></dd>
                  <dt>Quote</dt>
                  <dd><blockquote>“{ENTRY.quote}”</blockquote><span className="dim">found word for word in the source</span></dd>
                  <dt>Model</dt>
                  <dd>{ENTRY.model} <span className="dim">named in the quote itself</span></dd>
                  <dt>Source</dt>
                  <dd><a href={ENTRY.url} target="_blank" rel="nofollow noopener noreferrer">{ENTRY.source} ↗</a></dd>
                  <dt>Counted</dt>
                  <dd>once for its author, however often it is reshared</dd>
                </dl>
              </figure>
            </div>
          </Reveal>
          <div className="section-head trust-head">
            {/* FOUR LINES, so the claim reads as a statement rather than a caption. */}
            <h2 className="trust-lines">
              <span>Leaderboards give you</span>
              <span>a score.</span>
              <span>This gives you</span>
              <span>the evidence.</span>
            </h2>
            <p>
              An AI leaderboard, a Chatbot Arena vote or a table of LLM rankings gives each model one number,
              averaged across tasks you may never run. The Model Information Board keeps what engineers actually
              wrote, files it by the job they were doing, and links every word to its source.
            </p>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------ browse */}
      <section className="section-tight shell" id="browse">
        <div className="section-head section-head-row">
          <div>
            <span className="eyebrow">Best AI model by use case</span>
            <h2>Browse AI models by job, capability or metric</h2>
          </div>
          <Link to="/board" className="go-badge go-board" aria-label="Open the board">Board <span aria-hidden="true">→</span></Link>
        </div>
        <BrowseShowcase board={board} />
      </section>

      {/* ------------------------------------------------ models + compare */}
      <section className="section-tight shell" id="models-and-compare">
        {/* THE SAME HEAD AS BOARD AND BLOGS: eyebrow, H2, badge on the right. */}
        <div className="section-head section-head-row">
          <div>
            <span className="eyebrow">Models and comparisons</span>
            <h2>AI models and side-by-side comparisons</h2>
          </div>
          <Link to="/models" className="go-badge go-models" aria-label="Open all models">Models <span aria-hidden="true">→</span></Link>
        </div>
        <div className="mc-pair">
          <Reveal>
            <div className="mc-box mc-models">
              <span className="eyebrow">The models</span>
              <h2>One page per AI model</h2>
              <p className="muted">Claude, GPT, Gemini, DeepSeek, Kimi, Qwen and more — everything engineers reported about each one.</p>
              <div className="mt-grid">
                {MODELS.map((m, i) => {
                  const n = entriesFor(board, m.label)
                  return (
                    <Link key={m.id} to={`/models/${m.id}`} className="mt" style={{ '--i': i }}>
                      <span className="mt-p">{m.provider}</span>
                      <span className="mt-n">{m.name}</span>
                      {n != null && <span className="mt-c tnum">{n ? `${n} ${n === 1 ? 'entry' : 'entries'}` : 'none yet'}</span>}
                    </Link>
                  )
                })}
              </div>
            </div>
          </Reveal>

          <Reveal delay={110}>
            <div className="mc-box mc-compare">
              <span className="eyebrow">AI model comparison</span>
              <h2>Compare two AI models</h2>
              <p className="muted">Opus vs Sonnet, Haiku vs Gemini Flash, GPT vs DeepSeek — every job and capability both have reports on, side by side.</p>
              <div className="vs-list">
                {PAIRS.map(([a, b], i) => (
                  <Link key={a.id + b.id} to={`/compare?ids=${a.id},${b.id}`} className="vs" style={{ '--i': i }}>
                    <span className="vs-a">{a.name}</span>
                    <span className="vs-x">vs</span>
                    <span className="vs-b">{b.name}</span>
                  </Link>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ------------------------------------------------------------- blogs */}
      {/* Title only for now: the posts are written later and fill this in. */}
      <section className="section-tight shell" id="blogs">
        <div className="section-head section-head-row">
          <div>
            <span className="eyebrow">From the evidence · blogs</span>
            <h2>AI model insights</h2>
          </div>
          <Link to="/blogs" className="go-badge go-blogs" aria-label="Open the blogs">Blogs <span aria-hidden="true">→</span></Link>
        </div>
        <BlogShowcase />
      </section>

      {/* ---------------------------------------------------- closing cta */}
      <section className="section shell">
        <Reveal><ClosingCta /></Reveal>
      </section>

      {/* FAQ, last on the page as in the landing demo. It is the one section
          that renders when the board cannot be read: `/faq` touches no
          database, and half of what it explains is why an empty board is a
          real state. */}
      <Faq />

    </div>
  )
}
