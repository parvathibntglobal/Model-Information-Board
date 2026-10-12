import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listRegistry, fetchAll, fmtPrice, BoardUnreadable } from '../api'
import { Notice, Unreadable } from '../components/ui'
import { IconAlert, IconSearch } from '../components/Icons'
import { countLines, countWords, priceRows } from '../tokens/cost'
import { Cost, Fit } from '../tokens/cells'
import Workload from '../tokens/Workload'
import { modelHref } from '../tokens/links'
import { ENCODING, loadTokenizer, pieces } from '../tokens/tokenizer'

/**
 * THE TOKEN COUNTER (2026-10-12). Paste text, count its tokens in the browser,
 * see what it costs to send or generate on each model at its advertised rate.
 *
 * NOT EVIDENCE. Like the models list, a rate is what a provider says about
 * itself; nothing here says which model is better, and the table is in name
 * order until the reader asks for cost order.
 *
 * NOTHING YOU TYPE LEAVES THE PAGE. The only request is the model roster; the
 * text is counted by a tokenizer running here.
 */

//: How many rows the table shows before "Show all". A reading cap, not a filter:
//: the count of the rest is always on the button.
const FIRST_ROWS = 25
//: How many tokens the "show tokens" view colours. Past this the view would
//: re-render thousands of spans on every keystroke; the count above is never capped.
const PIECE_LIMIT = 2000

const SAMPLE =
  'You are a code reviewer. Read the diff below and list every bug, with the line it is on and why it is wrong. ' +
  'If the diff looks correct, say so in one sentence.\n\n' +
  '- if (user.age > 18) {\n+ if (user.age >= 18) {'

const fmtInt = (n) => (n == null ? '—' : n.toLocaleString('en-US'))

export default function TokenCounter() {
  const [text, setText] = useState('')
  const deferred = useDeferredValue(text)
  const [tok, setTok] = useState(null)
  const [tokErr, setTokErr] = useState(null)

  const [models, setModels] = useState(null)
  const [pricedAt, setPricedAt] = useState(null)
  const [err, setErr] = useState(null)
  const [unreadable, setUnreadable] = useState(null)

  const [direction, setDirection] = useState('input')
  const [calls, setCalls] = useState(1000)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('name')
  const [showAll, setShowAll] = useState(false)
  const [showPieces, setShowPieces] = useState(false)
  const [mode, setMode] = useState('text')
  const [fitsOnly, setFitsOnly] = useState(false)

  useEffect(() => {
    let alive = true
    loadTokenizer().then((t) => { if (alive) setTok(t) }, (e) => { if (alive) setTokErr(e.message) })
    ;(async () => {
      try {
        const list = await fetchAll((l, o) => listRegistry(l, o))
        if (!alive) return
        setModels(list.models)
        setPricedAt(list.priced_at)
      } catch (e) {
        if (!alive) return
        if (e instanceof BoardUnreadable) setUnreadable(e.message)
        else setErr(e.message)
      }
    })()
    return () => { alive = false }
  }, [])

  // NULL UNTIL THE TOKENIZER IS HERE, never 0: "not counted yet" and "no
  // tokens" are different, and every cost below inherits whichever this is.
  const ids = useMemo(() => (tok ? tok.encode(deferred) : null), [tok, deferred])
  const tokens = ids ? ids.length : null
  const chars = [...deferred].length

  const rows = useMemo(
    () => priceRows(models, { tokens, direction, calls, query, sort, encodingNameFor: tok?.encodingNameFor }),
    [models, tokens, direction, calls, query, sort, tok],
  )
  const exactCount = rows.priced.filter((r) => r.exactness === 'exact').length
  // "ONLY WHERE IT FITS" HIDES ROWS, AND SAYS HOW MANY AND WHY: a model with no
  // published limit is hidden as unknown, never counted as too short (rule 6).
  const hidden = { over: 0, unknown: 0 }
  for (const r of rows.priced) if (r.fit && r.fit.state !== 'fits') hidden[r.fit.state] += 1
  const visible = fitsOnly && tokens > 0 ? rows.priced.filter((r) => r.fit?.state === 'fits') : rows.priced
  const shown = showAll ? visible : visible.slice(0, FIRST_ROWS)

  const split = useMemo(
    () => (showPieces && tok && ids ? pieces(tok, ids, PIECE_LIMIT) : null),
    [showPieces, tok, ids],
  )

  const priceDay = pricedAt ? String(pricedAt).slice(0, 10) : null
  const verb = direction === 'output' ? 'generate' : 'send'

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <nav className="tc-trail label" aria-label="Breadcrumb">
          <Link to="/models">Models</Link> <span aria-hidden="true">/</span> Token counter
        </nav>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>LLM token counter</h1>
        <p className="tc-lead">
          Paste a prompt, a document or a model's answer. The count runs in your browser,
          and the table prices that text on every model that publishes a per-token rate.
        </p>
      </div>

      {tokErr && (
        <Notice icon={<IconAlert />}>
          The tokenizer did not load ({tokErr}), so nothing is counted and no cost is shown.
          Reload the page to try again.
        </Notice>
      )}

      <div className="tc-work">
        <section className="card tc-editor" aria-label="Your text">
          <div className="tc-editor-head">
            <span className="label">Your text</span>
            <span className="tc-private">Counted on this page. Nothing you type is sent.</span>
          </div>
          <textarea
            className="tc-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste or type here…"
            spellCheck="false"
            aria-label="Text to count"
          />
          <div className="tc-editor-foot">
            <button type="button" className={`chip${showPieces ? ' chip-on' : ''}`}
                    aria-pressed={showPieces} onClick={() => setShowPieces((v) => !v)}
                    disabled={!text}>
              Show how it splits
            </button>
            {!text && (
              <button type="button" className="chip" onClick={() => setText(SAMPLE)}>Try a sample</button>
            )}
            {text && (
              <button type="button" className="chip" onClick={() => setText('')}>Clear</button>
            )}
          </div>
          {split && (
            <div className="tc-pieces" aria-label="The text, one colour per token">
              {split.map((p, i) => (
                <span key={i} className={`tc-piece tc-piece-${i % 4}`}
                      title={p.n > 1 ? `${p.n} tokens (one character spread over several)` : undefined}>
                  {p.text.replace(/\n/g, '↵\n')}
                </span>
              ))}
              {ids.length > PIECE_LIMIT && (
                <p className="dim tc-note">
                  Colouring the first {fmtInt(PIECE_LIMIT)} of {fmtInt(ids.length)} tokens. The count covers all of them.
                </p>
              )}
            </div>
          )}
        </section>

        <aside className="card tc-meter" aria-label="Count">
          <div className="tc-big">
            <span className="tc-big-n tnum">{tok ? fmtInt(tokens) : '…'}</span>
            <span className="label">tokens · {ENCODING}</span>
          </div>
          <dl className="tc-facts">
            <div><dt>Characters</dt><dd className="tnum">{fmtInt(chars)}</dd></div>
            <div><dt>Words</dt><dd className="tnum">{fmtInt(countWords(deferred))}</dd></div>
            <div><dt>Lines</dt><dd className="tnum">{fmtInt(countLines(deferred))}</dd></div>
            <div><dt>Characters per token</dt>
              <dd className="tnum">{tokens ? (chars / tokens).toFixed(1) : '—'}</dd></div>
          </dl>

          <div className="tc-controls">
            <span className="label">Price this text as</span>
            <div className="tc-seg" role="radiogroup" aria-label="Price this text as">
              {[['input', 'Input', 'a prompt you send'], ['output', 'Output', 'an answer it writes']].map(([k, l, sub]) => (
                <button key={k} type="button" role="radio" aria-checked={direction === k}
                        className={direction === k ? 'on' : ''} onClick={() => setDirection(k)}>
                  <strong>{l}</strong><span>{sub}</span>
                </button>
              ))}
            </div>
            <label className="tc-calls">
              <span className="label">Calls</span>
              <input type="number" min="1" step="1" value={calls}
                     onChange={(e) => setCalls(Math.max(1, Math.floor(Number(e.target.value) || 1)))} />
            </label>
          </div>
        </aside>
      </div>

      <section className="stack stack-2" aria-labelledby="tc-costs">
        <div className="tabstrip tc-tabs" role="tablist" aria-label="What to price">
          <button type="button" role="tab" aria-selected={mode === 'text'} onClick={() => setMode('text')}>
            This text
          </button>
          <button type="button" role="tab" aria-selected={mode === 'workload'} onClick={() => setMode('workload')}>
            A workload, per month
          </button>
        </div>
        <div className="row-between" style={{ flexWrap: 'wrap', alignItems: 'baseline' }}>
          <h2 id="tc-costs">{mode === 'text' ? `What this text costs to ${verb}` : 'What a workload costs'}</h2>
          {/* `priced_at` is the newest pricing_history row, and a row is written
              only when a price CHANGES - so it dates the last change seen, not
              the last poll. Labelled as what it is. */}
          {priceDay && <span className="label">List prices · latest change recorded {priceDay}</span>}
        </div>
        <p className="dim tc-note">
          {models && tok && exactCount === 0
            ? <>The count uses OpenAI's published {ENCODING} encoding, and the tokenizer library
                lists none of the models below as using it - newer models included - so every
                cost and fit here is an estimate (≈).</>
            : <>The count is exact for models the tokenizer library lists as {ENCODING}
                {models && tok ? ` (${exactCount} of the ${rows.priced.length} below)` : ''}.
                Every other row, marked ≈, applies the same count as an estimate.</>}
          {' '}Models split text with their own tokenizers, and how far their counts differ from
          this one has not been measured here. The count is of the text alone; a chat API adds a
          few tokens per message.
        </p>

        {unreadable && <Unreadable detail={unreadable} />}
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!models && !err && !unreadable && <div className="skel" style={{ height: 220 }} />}

        {models && (
          <>
            <div className="tc-tablebar">
              <label className="searchbar" style={{ flex: 1 }}>
                <IconSearch width={15} height={15} />
                <input type="search" value={query} onChange={(e) => setQuery(e.target.value)}
                       placeholder="Search models" aria-label="Search models" autoComplete="off" spellCheck="false" />
                {query && <button className="x" onClick={() => setQuery('')}>clear</button>}
              </label>
              <div className="row" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-label="Order and filter">
                <button type="button" className={`chip${sort === 'name' ? ' chip-on' : ''}`}
                        aria-pressed={sort === 'name'} onClick={() => setSort('name')}>A–Z</button>
                <button type="button" className={`chip${sort === 'cost' ? ' chip-on' : ''}`}
                        aria-pressed={sort === 'cost'} onClick={() => setSort('cost')}>
                  {mode === 'text' ? `Lowest ${direction} rate` : 'Lowest monthly cost'}
                </button>
                {mode === 'text' && (
                  <button type="button" className={`chip${fitsOnly ? ' chip-on' : ''}`} disabled={!tokens}
                          aria-pressed={fitsOnly} onClick={() => setFitsOnly((v) => !v)}>
                    Only where it fits
                  </button>
                )}
              </div>
            </div>

            {mode === 'workload' ? (
              <Workload models={models} tokens={tokens} encodingNameFor={tok?.encodingNameFor}
                        query={query} sort={sort} />
            ) : (
              <>
                {fitsOnly && tokens > 0 && (hidden.over + hidden.unknown) > 0 && (
                  <p className="dim tc-note">
                    Hiding {hidden.over + hidden.unknown}: {hidden.over} this text is too long for
                    {hidden.unknown ? `, and ${hidden.unknown} that publish no ${direction === 'output' ? 'output limit' : 'context window'}, so whether it fits is unknown` : ''}.
                  </p>
                )}
                <div className="tc-table" role="table" aria-label="Cost per model">
                  <div className="tc-tr tc-th" role="row">
                    <span role="columnheader">Model</span>
                    <span role="columnheader">Fits?</span>
                    <span role="columnheader">{direction === 'output' ? 'Output' : 'Input'} rate / 1M</span>
                    <span role="columnheader">1 call</span>
                    <span role="columnheader">{fmtInt(calls)} {calls === 1 ? 'call' : 'calls'}</span>
                  </div>
                  {shown.map((r) => (
                    <div key={r.id} className="tc-tr" role="row">
                      <span role="cell" className="tc-model">
                        <Link to={modelHref(r.mvId)}>{r.name}</Link>
                        <span className="dim">{r.provider || 'provider not recorded'}</span>
                      </span>
                      <Fit fit={r.fit} what={direction === 'output' ? 'output limit' : 'context window'} />
                      <span role="cell" className="tnum" data-label="Rate / 1M">{fmtPrice(r.rate)}</span>
                      <Cost row={r} value={r.one} label="1 call" />
                      <Cost row={r} value={r.many} label={`${fmtInt(calls)} calls`} strong />
                    </div>
                  ))}
                  {visible.length === 0 && (
                    <p className="dim tc-note" style={{ padding: 'var(--s2)' }}>
                      {query ? `No priced model matches “${query}”.`
                        : fitsOnly ? 'This text fits no priced model.' : 'No model in the registry publishes a rate.'}
                    </p>
                  )}
                </div>

                {visible.length > FIRST_ROWS && (
                  <button type="button" className="btn btn-quiet" style={{ alignSelf: 'flex-start' }}
                          onClick={() => setShowAll((v) => !v)}>
                    {showAll ? `Show the first ${FIRST_ROWS}` : `Show all ${fmtInt(visible.length)} models`}
                  </button>
                )}

                {rows.unpriced.length > 0 && (
                  <details className="tc-unpriced">
                    <summary>
                      {rows.unpriced.length} {rows.unpriced.length === 1 ? 'model publishes' : 'models publish'} no {direction} rate
                    </summary>
                    <p className="dim tc-note">
                      Not free, and not left out: these have no per-token {direction} rate in the registry,
                      so this text cannot be priced on them. A router bills at the rate of whichever
                      model it picks; an image, video or speech model is priced per image, second or character.
                    </p>
                    <p className="tc-unpriced-list">
                      {rows.unpriced.map((r, i) => (
                        <span key={r.id}>{i ? ', ' : ''}<Link to={modelHref(r.mvId)}>{r.name}</Link></span>
                      ))}
                    </p>
                  </details>
                )}
              </>
            )}
          </>
        )}
      </section>
    </div>
  )
}
