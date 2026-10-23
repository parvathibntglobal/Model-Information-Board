import { Link } from 'react-router-dom'
import { useHead } from '../seo/head'
import { toolsIndex } from '../seo/pages'

/**
 * TOOLS (2026-10-14): the demo's Tools section as a page. It gathers the three
 * tools that already exist rather than rebuilding them: the best AI model picker, the
 * model specs finder and the token counter. Comparing models starts from Reports → AI models (2026-10-14). The wording follows model-information-board-home-demo.html.
 *
 * ADVERTISED IS NOT REPORTED. Specs and prices are what providers publish;
 * the page says so, as the demo does, so nobody reads them as evidence.
 */
const TOOLS = [
  {
    to: '/best-ai-model',
    name: 'Best AI model picker',
    title: 'The best model for the job, or a cheaper alternative',
    body: "Start from a job to see the models engineers reported working for it, or from a model you use to find alternatives that worked as well and cost less.",
    cta: 'Open the model picker',
  },
  {
    to: '/ai-model-pricing',
    name: 'AI model pricing & specs table',
    title: "Every model's advertised specs",
    body: 'Context window, output limit, prices and features for every model on our registry. Advertised by providers: not evidence, and never part of the counts.',
    cta: 'Open the pricing & specs table',
  },
  {
    to: '/token-counter',
    name: 'LLM cost calculator & token counter',
    title: 'Price your own prompt',
    body: "Counted with OpenAI's o200k tokenizer, in your browser. See the cost as input or output on each model, and whether it fits each model's context. Your text never leaves the page.",
    cta: 'Open token counter',
  },
]

export default function Tools() {
  useHead(toolsIndex())
  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="go-badge go-models page-tag" style={{ alignSelf: 'flex-start' }}>Tools</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Free AI model tools</h1>
        <p className="muted" style={{ maxWidth: '72ch', margin: 0 }}>
          Free AI model tools: a picker for the best model for your job, a pricing and specs table, and an LLM cost calculator. No sign-in.
        </p>
      </div>
      <div style={{ display: 'grid', gap: 'var(--s3)', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
        {TOOLS.map((t) => (
          <div key={t.to} className="card stack stack-2">
            <span className="eyebrow">{t.name}</span>
            <h2 style={{ fontSize: 'var(--fs-h3)', margin: 0 }}>{t.title}</h2>
            <p style={{ fontSize: 'var(--fs-sm)', margin: 0, lineHeight: 1.6 }}>{t.body}</p>
            <Link to={t.to} className="btn btn-ghost" style={{ alignSelf: 'flex-start', marginTop: 'auto' }}>{t.cta} →</Link>
          </div>
        ))}
      </div>
    </div>
  )
}
