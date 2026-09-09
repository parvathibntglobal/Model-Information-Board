import { useEffect, useState } from 'react'
import { faqPage } from '../api'
import { Badge } from './ui'

/**
 * The landing page's FAQ — eleven questions, from `contract/faq.yaml`.
 *
 * WHY IT FETCHES INSTEAD OF HOLDING THE COPY. The answers are editorial text
 * that changes without a deploy and is reviewed by people who do not read JSX,
 * so they live in a versioned contract file (rule 5). It also means the copy
 * cannot drift from what the board can actually support: three of the eleven
 * ask something about MODELS rather than about the board, and the endpoint
 * decides whether the evidence supports an answer yet.
 *
 * THE DEMO'S ANSWERS ARE NOT RENDERED WHERE THEY WERE CLAIMS. The landing
 * mock-up answered "which is cheapest per token" with "DeepSeek V4 Flash at
 * $0.14 in and $0.28 out" and "best for coding" with Claude Opus 5. Those came
 * from demo data. Here they arrive `established: false` with an answer that
 * says what the board cannot yet support, and a quiet marker so a reader can
 * see WHICH kind of answer they are reading. Rendering the demo's figures would
 * be rule 3 with no way for a reader to notice.
 *
 * IT SURVIVES THE BOARD BEING UNREADABLE. `/faq` touches no database, so this
 * section still renders when everything below it cannot. That is the right way
 * round: half of what the FAQ explains is why an empty board is a real state.
 *
 * The JSON-LD is injected as a real `<script type="application/ld+json">`, and
 * ONLY from the answers actually served. Giving an answer engine the demo's
 * figures while showing the reader a caveat is cloaking.
 */
export default function Faq() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    faqPage()
      .then((d) => { if (alive) setData(d) })
      .catch((e) => { if (alive) setErr(e.message) })
    return () => { alive = false }
  }, [])

  // FAQPage structured data, from the served answers only.
  useEffect(() => {
    if (!data?.questions?.length) return
    const el = document.createElement('script')
    el.type = 'application/ld+json'
    el.dataset.faq = 'modelboard'
    el.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': data.schema_type || 'FAQPage',
      mainEntity: data.questions.map((q) => ({
        '@type': 'Question',
        name: q.question,
        acceptedAnswer: { '@type': 'Answer', text: q.answer },
      })),
    })
    document.head.appendChild(el)
    return () => { el.remove() }
  }, [data])

  // THE HASH JUMP HAS TO WAIT FOR THE FETCH. `/#faq` from the nav fires the
  // browser's own jump immediately, before this section is in the DOM, so it
  // lands nowhere. Once the answers render, honour the hash ourselves.
  useEffect(() => {
    if (!data || window.location.hash !== '#faq') return
    document.getElementById('faq')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [data])

  if (err) {
    return (
      <section id="faq" className="section-tight shell">
        <div className="section-head">
          <span className="eyebrow">FAQ</span>
          <h2>Frequently asked questions</h2>
        </div>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          The FAQ could not be read: {err}
        </p>
      </section>
    )
  }
  if (!data) {
    return (
      <section id="faq" className="section-tight shell">
        <div className="skel" style={{ height: 160 }} />
      </section>
    )
  }

  const unestablished = data.questions.filter((q) => !q.established).length

  return (
    <section id="faq" className="section-tight shell">
      <div className="section-head">
        <span className="eyebrow">FAQ page</span>
        <h2>Frequently asked questions</h2>
      </div>

      <div className="stack stack-2">
        {data.questions.map((q) => (
          <details key={q.id} open={q.open} className="faq-item">
            <summary>
              {q.question}
              {!q.established && (
                <>
                  {' '}
                  <Badge tone="mute" title="This asks about models, not about how the board works. The board answers it from evidence, and does not have enough yet.">
                    not yet established
                  </Badge>
                </>
              )}
            </summary>
            <p className="muted" style={{ fontSize: 'var(--fs-sm)', maxWidth: '74ch' }}>
              {q.answer}
            </p>
          </details>
        ))}
      </div>

      {unestablished > 0 && (
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', marginTop: 'var(--s3)' }}>
          <strong style={{ color: 'var(--text)' }}>
            {unestablished} of these {unestablished === 1 ? 'asks' : 'ask'} about models rather
            than about the board
          </strong>{' '}
          — which is cheapest, which is best for coding, whether a benchmark is saturated. Those
          are answered from evidence or not at all, and the board has not collected enough to name
          a model yet. It says so rather than filling the gap with a plausible sentence, and the
          answer changes on its own once the reports exist. Evidence comes from{' '}
          {(data.platforms || []).join(', ')}.
        </p>
      )}
    </section>
  )
}
