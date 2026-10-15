import { Fragment, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { modelCatalog, reportsPage } from '../api'
import { MODEL_TYPES } from '../catalog/types'
import { fmtDate, modelPagePath } from '../catalog/format'
import { useInView } from './ui'

/**
 * MODELS AND COMPARISONS AS A SHOWCASE (2026-10-15), the way the Board's
 * "browse" cards used to turn on the landing: one small card in front, its
 * neighbours standing smaller and faded on either side, the rest waiting
 * behind. Six cards - Compare, then the nav's Models menu, entry for entry:
 * All models, New releases, Most reported, Model types, Providers.
 *
 * WHERE EACH READS:
 *   Compare        the landing's comparison box as it was: "Compare up to
 *                  three AI models" and its inverted pyramid of pairs and trios.
 *   Most reported  `/reports`, at the Models pages' floor: a model counts on a
 *                  job, capability or metric only where 5+ people reported.
 *   the rest       `/model-catalog`, the /catalog pages' own data.
 * Every row opens the page the menu would. A card with nothing to show is left
 * out - nothing is invented to fill one.
 *
 * It turns every few seconds while on screen; a click or a tab
 * onto a side card brings it to the front (the click does not follow its links
 * until it is in front), the dots pick one, and a swipe turns it. Reduced
 * motion: it never turns by itself. Under 760px the cards simply stack
 * (styles: the showcase rules in app.css).
 */

const MIN = 5
// four a card: six cards of six rows read heavy (2026-10-15)
const ROWS = 4
const TURN_MS = 3800
const PROVIDERS = { anthropic: 'Anthropic', openai: 'OpenAI', google: 'Google', deepseek: 'DeepSeek', moonshotai: 'Moonshot AI',
  qwen: 'Qwen', 'z-ai': 'Z.ai', minimax: 'MiniMax', 'x-ai': 'xAI', mistralai: 'Mistral', 'meta-llama': 'Meta' }
const shortName = (l) => (l && l.includes(':') ? l.split(':').slice(1).join(':').trim() : l)
const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

// THE COMPARE ROWS: the landing's hand-picked pairs and trios, unchanged
// (2026-10-15, on request). Every id links to a real compare.
const COMPARES = [
  [{ name: 'Claude Sonnet 5', id: 'anthropic/claude-sonnet-5' }, { name: 'Claude Opus 4.8', id: 'anthropic/claude-opus-4.8' }, { name: 'Claude Haiku 4.5', id: 'anthropic/claude-haiku-4.5' }],
  [{ name: 'Gemini 3.7 Flash', id: 'google/gemini-3.7-flash' }, { name: 'DeepSeek V4 Pro', id: 'deepseek/deepseek-v4-pro' }, { name: 'Qwen3.6 27B', id: 'qwen/qwen3.6-27b' }],
  [{ name: 'GPT-5.6 Luna', id: 'openai/gpt-5.6-luna' }, { name: 'MiniMax M3', id: 'minimax/minimax-m3' }, { name: 'GPT-5.6 Sol', id: 'openai/gpt-5.6-sol' }],
  [{ name: 'Claude Opus 5.5', id: 'anthropic/claude-opus-5.5' }, { name: 'Claude Opus 4.6', id: 'anthropic/claude-opus-4.6' }],
  [{ name: 'Grok 4.6', id: 'x-ai/grok-4.6' }, { name: 'GPT-6 Sol', id: 'openai/gpt-6-sol' }],
]

/** Per published model: how many jobs, capabilities and metrics it qualifies on. */
function mostReported(axes) {
  const by = new Map()
  for (const a of axes) {
    for (const m of a.models) {
      if (m.voices < MIN || !m.canonical) continue
      const r = by.get(m.key) || { key: m.key, label: m.label, canonical: m.canonical, total: 0, people: 0 }
      r.total += 1
      r.people = Math.max(r.people, m.voices)
      by.set(m.key, r)
    }
  }
  return [...by.values()].sort((a, b) => b.total - a.total || b.people - a.people || shortName(a.label).localeCompare(shortName(b.label)))
}

/** The cards, each { key, q, k, tint, rows: [{ to, name, pill }], more }. */
function buildCards(cat, reported) {
  // the Compare card is the landing's comparison box as it was: its heading,
  // its line and the inverted pyramid of pairs and trios
  const cards = [{
    key: 'compare', q: 'Compare up to three AI models', k: 'AI model comparison', tint: 'var(--warn)', pyramid: COMPARES,
    note: 'Opus vs Sonnet vs Gemini Flash and more — every job and capability they have reports on, side by side.',
    more: { to: '/compare', label: 'Compare models' },
  }]
  const names = Object.fromEntries((cat?.providers || []).flatMap((p) => p.ids.map((i) => [i, p.name])))
  const list = cat?.models || []
  const voiced = list.filter((m) => m.voices > 0).sort((a, b) => b.voices - a.voices || b.reports - a.reports || a.name.localeCompare(b.name))
  if (voiced.length) {
    cards.push({
      key: 'all', q: 'Which models do engineers use?', k: `All models · ${voiced.length} reported`, tint: 'var(--pass)', grid: true,
      rows: voiced.slice(0, ROWS).map((m) => ({ to: modelPagePath(m.id), top: names[m.provider] || PROVIDERS[m.provider] || m.provider, name: m.name, pill: plural(m.voices, 'voice') })),
      more: { to: '/catalog', label: 'All models' },
    })
  }
  const byId = Object.fromEntries(list.map((m) => [m.id, m]))
  const fresh = (cat?.new_releases || []).map((id) => byId[id]).filter(Boolean).slice(0, ROWS)
  if (fresh.length) {
    cards.push({
      key: 'new', q: 'What just came out?', k: 'New releases', tint: 'var(--info)',
      rows: fresh.map((m) => ({ to: modelPagePath(m.id), name: m.name, by: names[m.provider] || PROVIDERS[m.provider] || m.provider,
        pill: fmtDate(m.listed_at).replace(/ \d{4}$/, '') })),
      more: { to: '/catalog/new', label: 'All new releases' },
    })
  }
  if (reported.length) {
    cards.push({
      key: 'reported', q: 'Where is the evidence deepest?', k: 'Most reported', tint: 'color-mix(in srgb,var(--pass) 50%,var(--info))',
      rows: reported.slice(0, ROWS).map((r) => ({ to: `/reports/models/${r.canonical}`, name: shortName(r.label), pill: plural(r.total, 'topic') })),
      more: { to: '/reports/models', label: 'All reported models' },
    })
  }
  // the six types with the most models; the card's link opens all of them
  const types = MODEL_TYPES.filter((t) => cat?.types?.[t.key])
  if (types.length) {
    cards.push({
      key: 'types', q: 'What kind of model do I need?', k: 'Model types', tint: 'color-mix(in srgb,var(--info) 55%,var(--fail))', grid: true,
      rows: [...types].sort((a, b) => cat.types[b.key] - cat.types[a.key]).slice(0, ROWS)
        .map((t) => ({ to: `/catalog?type=${t.key}`, top: t.note, name: t.label, pill: plural(cat.types[t.key], 'model') })),
      more: { to: '/catalog', label: `All ${types.length} types` },
    })
  }
  const provs = [...(cat?.providers || [])].sort((a, b) => b.voiced - a.voiced || b.models - a.models).slice(0, ROWS)
  if (provs.length) {
    cards.push({
      key: 'providers', q: 'Who makes them?', k: `Providers · ${cat.providers.length}`, tint: 'color-mix(in srgb,var(--warn) 55%,var(--fail))', grid: true,
      rows: provs.map((p) => ({ to: `/catalog?provider=${p.id}`, top: `${p.voiced} with reports`, name: p.name, pill: plural(p.models, 'model') })),
      more: { to: '/catalog', label: 'All providers' },
    })
  }
  return cards
}

export default function ModelsShowcase() {
  const [cards, setCards] = useState(null)
  const [front, setFront] = useState(0)
  const start = useRef(null)
  useEffect(() => {
    let alive = true
    // either read may fail alone; the cards it feeds are then left out
    Promise.allSettled([modelCatalog(), reportsPage()]).then(([c, r]) => {
      if (!alive) return
      const cat = c.status === 'fulfilled' && !c.value.reason ? c.value : null
      setCards(buildCards(cat, r.status === 'fulfilled' ? mostReported(r.value.axes || []) : []))
    })
    return () => { alive = false }
  }, [])
  const n = cards ? cards.length : 0
  // it turns only while on screen (components/ui.jsx: useInView)
  // NO HOVER OR FOCUS PAUSE (2026-10-15): a mouse resting over the section
  // while scrolling, or a tab left focused after a click, held it still
  // indefinitely and it read as broken. A click still picks a card, and the
  // timer starts over from it.
  const [el, setEl] = useState(null)
  const inView = useInView(el)
  useEffect(() => {
    if (!inView || n < 2 || reduced()) return undefined
    const t = setTimeout(() => setFront((i) => (i + 1) % n), TURN_MS)
    return () => clearTimeout(t)
  }, [front, inView, n])

  if (!cards) return <div className="showcase-wait" aria-hidden="true" />
  const place = (i) => {
    const d = (i - front + n) % n
    if (d === 0) return 'front'
    if (d === 1) return 'right'
    if (d === n - 1) return 'left'
    return d <= n / 2 ? 'back-right' : 'back-left'
  }

  return (
    <div className="showcase showcase-models" ref={setEl}
>
      <div className="showcase-stage"
           onPointerDown={(e) => { start.current = e.clientX }}
           onPointerUp={(e) => {
             if (start.current == null) return
             const dx = e.clientX - start.current
             start.current = null
             if (Math.abs(dx) > 40) setFront((i) => (i + (dx < 0 ? 1 : n - 1)) % n)
           }}>
        {cards.map((c, i) => {
          const at = place(i)
          return (
            <div key={c.key} className={`showcase-item at-${at}${c.pyramid ? ' showcase-wide' : ''}`} aria-hidden={at !== 'front'}
                 onClickCapture={(e) => { if (at !== 'front') { e.preventDefault(); setFront(i) } }}
                 onFocusCapture={() => at !== 'front' && setFront(i)}>
              <div className="browse-card" style={{ '--tint': c.tint }}>
                <span className="browse-q">{c.q}</span>
                <span className="browse-k">{c.k}</span>
                {c.pyramid ? (
                  <>
                    <p className="browse-note">{c.note}</p>
                    {/* AN INVERTED PYRAMID: the three-way rows lead, then the
                        pairs, each row a little narrower and centred */}
                    <div className="vs-list vs-pyramid">
                      {c.pyramid.map((ms, k) => (
                        <Link key={ms.map((m) => m.id).join()} to={`/compare?ids=${ms.map((m) => m.id).join(',')}`}
                              className={`vs${ms.length === 3 ? ' vs3' : ''}`} tabIndex={at === 'front' ? 0 : -1}
                              style={{ '--i': k, '--w': `${100 - k * 9}%` }}>
                          {ms.map((m, j) => (
                            <Fragment key={m.id}>
                              {j > 0 && <span className="vs-x">vs</span>}
                              <span className={j === 0 ? 'vs-a' : j === ms.length - 1 ? 'vs-b' : 'vs-m'}>{m.name}</span>
                            </Fragment>
                          ))}
                        </Link>
                      ))}
                    </div>
                  </>
                ) : c.grid ? (
                  <div className="browse-grid">
                    {c.rows.map((r) => (
                      <Link key={r.to} to={r.to} className="browse-tile" tabIndex={at === 'front' ? 0 : -1}>
                        <span className="browse-tile-top">{r.top}</span>
                        <b>{r.name}</b>
                        <span className="browse-tile-n tnum">{r.pill}</span>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <ul className="browse-list">
                    {c.rows.map((r) => (
                      <li key={r.to}>
                        <Link to={r.to} tabIndex={at === 'front' ? 0 : -1}>
                          {r.name}{r.by && <span className="browse-by"> · {r.by}</span>}
                        </Link>
                        <span className="browse-pill tnum">{r.pill}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <Link className="browse-more" to={c.more.to} tabIndex={at === 'front' ? 0 : -1}>{c.more.label} →</Link>
              </div>
            </div>
          )
        })}
      </div>
      <div className="showcase-dots" role="group" aria-label="Choose a card">
        {cards.map((c, i) => (
          <button key={c.key} type="button" className={i === front ? 'on' : ''} style={{ '--tint': c.tint }}
                  aria-label={c.k} aria-pressed={i === front} onClick={() => setFront(i)} />
        ))}
      </div>
    </div>
  )
}
