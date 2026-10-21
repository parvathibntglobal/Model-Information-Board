import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { faqPage } from '../api'
import { useHead } from '../seo/head'
import { methodologyPage } from '../seo/pages'

/**
 * METHODOLOGY (2026-10-21): how a report is found, checked and counted - for a
 * reader deciding whether to trust a count, and for a search engine or an AI
 * tool deciding whether to cite one.
 *
 * EVERY SENTENCE IS SOMETHING THE CODE DOES, and names where:
 *   - a model proposes, code checks the quote   judge/extract/runner.py (the
 *     quote must be in the thread text; board_entry CHECKs quote_verified)
 *   - what the code does NOT check              the same file: job and side are
 *     the model's choice, measured against a hand-labelled set
 *   - people and posts                          voices / reports (judge/reports.py)
 *   - 5 people by default, 3 or 10, 2 platforms routes/Reports.jsx (MINS, multi)
 *   - the words                                 routes/Reports.jsx `phrase`
 *   - the order inside a job                    judge/reports.py (groups, then
 *     the Wilson lower bound it never emits)
 *   - totals and withheld platforms             contract/publication.yaml
 *   - prices and specs                          advertised, never counted; a model's page
 *                                               reads OpenRouter's listing (judge/catalog.py)
 * Change one of those and this page changes with it.
 *
 * THE PLATFORMS ARE READ, NOT WRITTEN: from `/faq`, the public list the footer
 * and the FAQ also show, so the three cannot disagree.
 */

const WORDS = [
  ['Reported working, no problems reported', 'At least one person reported it working and nobody reported a problem.'],
  ['Mostly working', 'Working reports are at least three times the problem reports.'],
  ['Mixed reports', 'Neither side is three times the other.'],
  ['Mostly problems', 'Problem reports are at least three times the working reports.'],
  ['Problems reported, none working', 'At least one problem and no working report.'],
  ['No side taken', 'Every report was neutral.'],
]

function Section({ title, children }) {
  return (
    <section className="stack stack-2" style={{ maxWidth: '72ch' }}>
      <h2 style={{ fontSize: 'var(--fs-h3)', margin: 0 }}>{title}</h2>
      {children}
    </section>
  )
}

export default function Methodology() {
  useHead(methodologyPage())
  const [platforms, setPlatforms] = useState(null)
  useEffect(() => {
    let alive = true
    faqPage().then((f) => alive && setPlatforms(f?.platforms || [])).catch(() => alive && setPlatforms([]))
    return () => { alive = false }
  }, [])

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="go-badge go-models page-tag" style={{ alignSelf: 'flex-start' }}>Methodology</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>How we count engineer reports</h1>
        <p className="muted" style={{ maxWidth: '72ch', margin: 0 }}>
          We read what engineers write publicly about the AI models they use, check every quoted line against the
          post it came from, and count how many different people reported each model working, failing or neither
          for each job. We publish those counts, not a score.
        </p>
      </div>

      <Section title="Where the reports come from">
        <p style={{ margin: 0 }}>
          Public posts by engineers about AI models they used in real work
          {platforms && platforms.length > 0 ? <>, on platforms including {platforms.join(', ')}</> : null}.
          Some platforms we read are never named, quoted or linked on this site. Their reports count towards the
          totals, so a model with 20 people behind it shows 20, but nothing on a page says which platform a report
          came from.
        </p>
      </Section>

      <Section title="How a statement is found and checked">
        <p style={{ margin: 0 }}>
          An AI model reads each post and proposes what it says: which model, which job, capability or metric,
          and whether the experience was positive, negative or neutral, with the words that say so. Code then
          checks that those exact words appear in the post. A statement whose quote is not found in the post is
          never counted.
        </p>
        <p style={{ margin: 0 }}>
          What code cannot check is the AI model's judgement: which job a post is about and which side it takes.
          That is measured against a set of posts labelled by hand, rather than taken on trust.
        </p>
      </Section>

      <Section title="What we count">
        <p style={{ margin: 0 }}>
          Two numbers: <b>people</b>, the different engineers who reported on a model, and <b>reports</b>, the
          posts they did it in. A person is counted once for a job however many times they posted about it, so
          one loud voice cannot outweigh several quiet ones.
        </p>
      </Section>

      <Section title="When a model is shown">
        <p style={{ margin: 0 }}>
          A model appears for a job, capability or metric once at least <b>5 different people</b> have reported on
          it. On the <Link to="/reviews">AI model reviews</Link> you can change that to 3 or 10 people, or ask for
          reports from at least two platforms. Fewer reports is not a low score: it means not enough engineers
          have written about that model for that job yet.
        </p>
      </Section>

      <Section title="The words we use">
        <p style={{ margin: 0 }}>
          The words beside a model follow a fixed rule over its working and problem reports. They are never a
          rating.
        </p>
        <div className="tablewrap">
          <table>
            <thead><tr><th scope="col">Words</th><th scope="col">When</th></tr></thead>
            <tbody>{WORDS.map(([w, when]) => <tr key={w}><th scope="row">{w}</th><td>{when}</td></tr>)}</tbody>
          </table>
        </div>
        <p style={{ margin: 0 }}>
          Within a job, models are grouped by what was reported, then ordered by how firmly their counts point
          that way, so a model with many consistent reports sits above one with a few. That ordering number is
          never shown as a score.
        </p>
      </Section>

      <Section title="What is not counted">
        <p style={{ margin: 0 }}>
          Prices, context windows and features are what providers advertise; each model&apos;s page shows{' '}
          <a href="https://openrouter.ai/models" target="_blank" rel="noreferrer">OpenRouter</a>&apos;s listing. They are
          shown beside the reports and never mixed into them. There is no overall score, no paid placement, and
          the site sells no model.
        </p>
      </Section>

      <Section title="Dates">
        <p style={{ margin: 0 }}>
          Every report keeps its date. Newer reports sit beside older ones rather than being folded into a running
          average, so when a model changes, it shows as newer reports saying something different.
        </p>
      </Section>

      <p className="muted" style={{ margin: 0 }}>
        Questions this page does not answer may be in the <Link to="/#faq">FAQ</Link>.
      </p>
    </div>
  )
}
