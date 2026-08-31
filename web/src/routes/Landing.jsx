import { Link } from 'react-router-dom'
import FluidCanvas from '../components/FluidCanvas'
import { Reveal, Stat, Badge } from '../components/ui'
import { IconQuote, IconPeople, IconSplit, IconSilence, IconArrow } from '../components/Icons'

const ADVANTAGES = [
  {
    icon: IconQuote,
    title: 'Evidence',
    body: 'Every claim carries a verbatim quote, verified in code against its source. No quote, no claim — and no scores, only what people actually said.',
  },
  {
    icon: IconPeople,
    title: 'Independence',
    body: 'Four hundred reshares of one post count once. We count people, not posts, because corroboration is the only thing that separates noise from signal.',
  },
  {
    icon: IconSplit,
    title: 'Conditions',
    body: 'Fine under five tools, fails above ten. Most disagreements are condition mismatches, and separating them is the answer rather than the problem.',
  },
  {
    icon: IconSilence,
    title: 'Silence',
    body: 'When nobody has tested something, the board says so. Absence of evidence must never read as evidence of capability.',
  },
]

const STEPS = [
  { n: '01', t: 'Describe the work', b: 'A task, a product brief, or a pasted agent config. You never need to know a model name to start.' },
  { n: '02', t: 'We split it into roles', b: 'A research assistant is five sub-agents. The one that runs ten times per request is where the money is.' },
  { n: '03', t: 'Answers, with the words', b: 'Ranked by cost, each with the quotes that earned its place and the criticisms that did not disqualify it.' },
]

export default function Landing() {
  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <section className="hero shell">
        <div className="hero-frame">
          <span className="hero-corner tl" /><span className="hero-corner tr" />
          <span className="hero-corner bl" /><span className="hero-corner br" />

          <div className="hero-stage">
            <FluidCanvas />
            <div className="hero-copy">
              <Reveal as="h1">Model Information Board</Reveal>
              <Reveal delay={120}>
                <p className="hero-sub">
                  You describe the work. The board names the models engineers have actually
                  made that work with — cheapest first, and shows you their exact words.
                </p>
              </Reveal>
            </div>

            {/* outside .hero-copy so the difference blend never touches the controls */}
            <Reveal delay={240} className="hero-cta">
              <Link to="/ask" className="btn btn-primary btn-lg">
                Describe a task <IconArrow width={15} height={15} />
              </Link>
              <Link to="/articles" className="btn btn-ghost btn-lg">Browse articles</Link>
            </Reveal>

            <span className="hero-hint">move the cursor · double-click to break the surface</span>
          </div>
        </div>

        {/* --------------------------------------------------- advantages */}
        <div className="grid g4" style={{ marginTop: 'var(--gap)' }}>
          {ADVANTAGES.map((a, i) => (
            <Reveal key={a.title} delay={i * 90}>
              <article className="card card-hover adv-cell" style={{ height: '100%' }}>
                <div className="adv-head">
                  <a.icon className="adv-ico" />
                  <span className="adv-title">{a.title}</span>
                </div>
                <p>{a.body}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------- the problem */}
      <section className="section shell">
        <div className="section-head">
          <span className="eyebrow">The problem</span>
          <h2>Your coding agent picks its own models. It picks the expensive one.</h2>
          <p>
            A sub-agent that summarises a page, classifies an intent or extracts four fields
            does not need a frontier model. Something far cheaper often does it at parity —
            and across thousands of requests a day, that difference is the operating cost.
            The hard part is knowing where cheaper is <em>safe</em>.
          </p>
        </div>

        <div className="grid g2">
          <Reveal>
            <div className="card" style={{ height: '100%' }}>
              <span className="label">A leaderboard says</span>
              <p style={{ marginTop: 12, fontSize: '1.25rem', letterSpacing: '-.02em' }}>
                Summarization score 87.3 · rank 4
              </p>
              <p className="muted" style={{ marginTop: 12, fontSize: 'var(--fs-sm)' }}>
                Curated tasks, leaked into training data, optimised for, and averaged across
                exactly the distinctions that matter.
              </p>
            </div>
          </Reveal>
          <Reveal delay={110}>
            <div className="card" style={{ height: '100%', borderColor: 'var(--border-strong)' }}>
              <span className="label">An engineer says</span>
              <p style={{ marginTop: 12, fontSize: '1.0625rem', lineHeight: 1.55, fontStyle: 'italic' }}>
                “Fine under about 50k tokens. Past that we started silently missing things in
                the middle. Took us two weeks to notice.”
              </p>
              <p className="muted" style={{ marginTop: 12, fontSize: 'var(--fs-sm)' }}>
                A failure mode, a threshold, and how long it took to detect. No benchmark
                produces that, because no benchmark has been embarrassed in production.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ------------------------------------------------------------ steps */}
      <section className="section-tight shell">
        <div className="grid g3">
          {STEPS.map((s, i) => (
            <Reveal key={s.n} delay={i * 90}>
              <div className="stack stack-2">
                <span className="label">{s.n}</span>
                <h3>{s.t}</h3>
                <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{s.b}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------- numbers */}
      <section className="section shell">
        <Reveal>
          <div className="card">
            <div className="row-between" style={{ marginBottom: 'var(--s4)' }}>
              <div className="stack stack-1">
                <span className="eyebrow">One nightly run</span>
                <p className="muted" style={{ fontSize: 'var(--fs-sm)' }}>
                  Filters run cheapest first. Only what survives all of them is ever published.
                </p>
              </div>
              <Badge tone="info">illustrative</Badge>
            </div>
            <div className="grid g4">
              <Stat n="10,000" l="posts harvested" />
              <Stat n="1,200" l="reach the reader" />
              <Stat n="1,700" l="claims kept" />
              <Stat n="96" l="cells published" />
            </div>
          </div>
        </Reveal>
      </section>

      {/* -------------------------------------------------------------- cta */}
      <section className="section-tight shell">
        <Reveal>
          <div className="card" style={{ textAlign: 'center', padding: 'var(--s7) var(--s3)' }}>
            <h2 style={{ fontSize: 'var(--fs-display)' }}>Find out where cheaper is safe.</h2>
            <p className="muted" style={{ maxWidth: '48ch', margin: '14px auto 0' }}>
              Describe one sub-agent, or paste your whole fleet config.
            </p>
            <div className="hero-cta">
              <Link to="/ask" className="btn btn-primary btn-lg">
                Describe a task <IconArrow width={15} height={15} />
              </Link>
            </div>
          </div>
        </Reveal>
      </section>
    </>
  )
}
