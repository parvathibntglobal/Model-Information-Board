import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fmtPrice, localModels } from '../api'
import { modelPagePath } from '../catalog/format'
import { Notice } from '../components/ui'
import { IconAlert } from '../components/Icons'
import { useHead } from '../seo/head'
import { localVram } from '../seo/pages'
import { estimate, fmtGiB } from '../vram/estimate'

/**
 * "CAN I RUN IT?" (2026-10-23, docs/proposals/can-i-run-it.md): which open
 * models fit the reader's hardware, at 4-bit or 8-bit.
 *
 * ONE FIGURE PER ROW, AND IT IS MEASURED (rule 3): the size of the exact GGUF
 * file, read from Hugging Face. Whether it fits is a GROUP - a word - worked out
 * from that size plus the memory the chosen context needs and an allowance for
 * the runtime. Neither of those is shown as a number; the page says in words
 * what the group adds. Revised after review on #559, which found the first
 * draft's "≈ 6.58 GiB estimate" was a computed figure rule 3 does not allow.
 *
 * THE CHOICES LIVE IN THE ADDRESS (?hw=&n=&q=&ctx=&kv=), so a reader can
 * bookmark their own machine and a shared link opens on the same answer.
 */

const QUANT_WORDS = { Q4_K_M: '4-bit', Q8_0: '8-bit' }
const CACHE_WORDS = { f16: 'Standard (16-bit)', q8_0: '8-bit (smaller)' }
const GROUPS = [
  ['fits', 'Fits', 'Room to spare after the file, the context and the runtime.'],
  ['tight', 'Tight', 'Fits, with little or no room left. Close other GPU apps, or pick a shorter context.'],
  ['unknown', "Can't tell", "The file and the runtime fit, but the context's memory is either unknown for this model, or known only as an upper bound that does not fit - so it may or may not. Never counted as nothing."],
  ['wont', "Won't fit", 'Needs more memory than this hardware has. Most can still run partly on the CPU, much more slowly.'],
]
const DEFAULT_HW = 'rtx-4060'
const fmtTokens = (n) => (n >= 1024 ? `${Math.round(n / 1024)}K` : String(n))
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`
const NEW_TAB = <span className="sr-only"> (opens in a new tab)</span>

/**
 * A row of choices that behaves as a radio group: one tab stop, arrow keys move
 * the choice (WAI-ARIA radio group pattern; #559 review).
 */
function Seg({ label, options, value, onChange }) {
  const refs = useRef([])
  const at = Math.max(0, options.findIndex((o) => o.value === value))
  const onKeyDown = (e) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key]
    if (!step) return
    e.preventDefault()
    const next = (at + step + options.length) % options.length
    onChange(options[next].value)
    refs.current[next] && refs.current[next].focus()
  }
  return (
    <div className="vr-field">
      <span className="label" id={`seg-${label}`}>{label}</span>
      <div className="vr-seg" role="radiogroup" aria-labelledby={`seg-${label}`} onKeyDown={onKeyDown}>
        {options.map((o, i) => (
          <button key={String(o.value)} type="button" role="radio" aria-checked={value === o.value}
                  tabIndex={i === at ? 0 : -1} ref={(el) => { refs.current[i] = el }}
                  className={value === o.value ? 'on' : ''} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function VramCalculator() {
  useHead(localVram())
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [sp, setSp] = useSearchParams()
  const [q, setQ] = useState('')

  useEffect(() => {
    let alive = true
    localModels()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setErr(e.message || 'The measured sizes could not be read.'))
    return () => { alive = false }
  }, [])

  const c = data && data.constants
  const devices = (data && data.hardware) || []
  const device = devices.find((d) => d.id === sp.get('hw')) || devices.find((d) => d.id === DEFAULT_HW) || devices[0]
  const cards = device && device.kind === 'discrete' ? Math.min(4, Math.max(1, Number(sp.get('n')) || 1)) : 1
  const quant = c && c.quants.includes(sp.get('q')) ? sp.get('q') : c && c.quants[0]
  const tokens = c && c.contexts.includes(Number(sp.get('ctx'))) ? Number(sp.get('ctx')) : c && c.contexts[1]
  const cacheType = c && sp.get('kv') in (c.kv_cache_bytes || {}) ? sp.get('kv') : 'f16'

  const set = (patch) => {
    const next = new URLSearchParams(sp)
    for (const [k, v] of Object.entries(patch)) next.set(k, String(v))
    setSp(next, { replace: true })
  }

  const rows = useMemo(() => {
    if (!data || !device) return null
    const ql = q.trim().toLowerCase()
    return data.models
      .filter((m) => !ql || `${m.name} ${m.family}`.toLowerCase().includes(ql))
      .map((m) => ({ m, e: estimate(m, { quant, tokens, cacheType, device, cards }, c) }))
  }, [data, device, cards, quant, tokens, cacheType, q, c])

  const grouped = useMemo(() => {
    const out = { fits: [], tight: [], unknown: [], wont: [], unmeasured: [] }
    for (const r of rows || []) (r.e ? out[r.e.group] : out.unmeasured).push(r)
    // Largest file first - the measured figure each row shows, so the order can
    // be checked against it: the biggest model that fits is usually the one wanted.
    for (const k of ['fits', 'tight', 'unknown', 'wont']) out[k].sort((a, b) => b.e.fileBytes - a.e.fileBytes)
    return out
  }, [rows])

  // Not shown, in words: a listed file gone from its repo is not "not measured yet".
  const notShown = data ? [
    ...grouped.unmeasured.map(({ m }) => ((m.quants[quant] && m.quants[quant].missing_files.length)
      ? `${m.name} (its ${quant} file is no longer in its repository)`
      : `${m.name} (not measured yet)`)),
    ...data.not_measured.map((m) => `${m.name} (not measured yet)`),
  ] : []

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <nav className="tc-trail label" aria-label="Breadcrumb">
          <Link to="/tools">Tools</Link> <span aria-hidden="true">/</span> Can I run it?
        </nav>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Can I run it? Local LLM VRAM calculator</h1>
        <p className="tc-lead">
          Pick your graphics card or Mac and see which open models fit in its memory at 4-bit or 8-bit.
          Every size shown is the measured size of the actual model file; whether it fits also counts the
          memory your context length needs.
        </p>
      </div>

      {err && <Notice icon={<IconAlert />}>The measured sizes could not be read ({err}). Nothing is shown rather than a guess.</Notice>}
      {!data && !err && <div className="skel" style={{ height: 320 }} />}

      {data && device && (
        <>
          <section className="card vr-controls" aria-label="Your hardware">
            <label className="vr-field">
              <span className="label">Hardware</span>
              <select value={device.id} onChange={(e) => set({ hw: e.target.value, n: 1 })}>
                {[...new Set(devices.map((d) => d.group))].map((g) => (
                  <optgroup key={g} label={g}>
                    {devices.filter((d) => d.group === g).map((d) => (
                      <option key={d.id} value={d.id}>{d.name} · {d.memory_gib} GiB{d.checked ? '' : ' (not yet checked)'}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            {device.kind === 'discrete' && (
              <Seg label="How many" value={cards} onChange={(n) => set({ n })}
                   options={[1, 2, 3, 4].map((n) => ({ value: n, label: `${n}×` }))} />
            )}
            <Seg label="Quantization" value={quant} onChange={(k) => set({ q: k })}
                 options={c.quants.map((k) => ({ value: k, label: <>{QUANT_WORDS[k] || k} <span>{k}</span></> }))} />
            <Seg label="Context length" value={tokens} onChange={(t) => set({ ctx: t })}
                 options={c.contexts.map((t) => ({ value: t, label: fmtTokens(t) }))} />
            <Seg label="KV cache" value={cacheType} onChange={(k) => set({ kv: k })}
                 options={Object.keys(c.kv_cache_bytes).map((k) => ({ value: k, label: CACHE_WORDS[k] || k }))} />
            <p className="dim vr-budget">
              {device.kind === 'unified'
                ? <>macOS lets the GPU use only part of a Mac&apos;s unified memory, and a smaller part on smaller Macs. The groups below count only that part.</>
                : <>{cards > 1 ? `${cards} × ${device.memory_gib} GiB, split by layer across the cards.` : `${device.memory_gib} GiB of graphics memory.`}</>}
              {!device.checked && (
                <> This card&apos;s memory is the size it is sold with, not yet checked against <a href={device.source} target="_blank" rel="noopener noreferrer">the maker&apos;s page{NEW_TAB}</a>.</>
              )}
            </p>
          </section>

          <input className="vr-search" type="search" value={q} onChange={(e) => setQ(e.target.value)}
                 placeholder="Search models (Llama, Qwen, Gemma...)" aria-label="Search models" />

          <p className="sr-only" aria-live="polite">
            {GROUPS.map(([key, title]) => `${title}: ${plural(grouped[key].length, 'model')}`).join('. ')}.
          </p>

          {GROUPS.map(([key, title, note]) => (key === 'unknown' && !grouped.unknown.length ? null : (
            <section key={key} className="stack stack-2" aria-label={title}>
              <div className={`vr-group-head vr-${key}`}>
                <h2>{title} <span className="dim">{plural(grouped[key].length, 'model')}</span></h2>
                <p className="dim">{note}</p>
              </div>
              {grouped[key].length
                ? <ul className="vr-list">{grouped[key].map(({ m, e }) => <Row key={m.id} m={m} e={e} quant={quant} />)}</ul>
                : <p className="dim">None of the models{q ? ` matching "${q}"` : ''}.</p>}
            </section>
          )))}

          {notShown.length > 0 && (
            <Notice icon={<IconAlert />}>
              Not shown, because their {quant} size is not known: {notShown.join(', ')}.
              A missing size is never estimated.
            </Notice>
          )}

          <section className="card stack stack-2 vr-method">
            <h2 style={{ fontSize: 'var(--fs-h3)', margin: 0 }}>How this is worked out</h2>
            <p>
              <strong>The size shown is measured:</strong> the size of the model&apos;s actual {quant} GGUF file
              on Hugging Face, summed over its parts, in GiB (a graphics card&apos;s &quot;8 GB&quot; is 8 GiB).
              Each row links the repository and the commit it was measured at.
            </p>
            <p>
              <strong>The group adds what the file does not hold:</strong> the memory your context length needs,
              worked out from the layers and attention heads stated in the file&apos;s own header, and an
              allowance for the runtime{c.overhead_per_card ? ' on each card' : ''}. A model fits when all of that
              leaves room to spare, and is tight when it only just fits. Where the header does not say exactly
              which layers keep the context, the context is counted as if every layer did - enough to show a
              model fits, never to show it does not, so such a model that does not fit at its most is
              &quot;can&apos;t tell&quot;. Where the context cannot be worked out at all, the model is
              &quot;can&apos;t tell&quot; too, rather than counted as needing nothing.
            </p>
            {data.measured_at && <p className="dim">Sizes measured {String(data.measured_at).slice(0, 10)}; re-measured weekly.</p>}
          </section>
        </>
      )}
    </div>
  )
}

function Row({ m, e, quant }) {
  const f = m.quants[quant]
  const tree = `https://huggingface.co/${m.gguf_repo}/tree/${f.repo_sha || 'main'}`
  const boundOver = e.group === 'unknown' && e.cacheKnown && e.upperBound
  return (
    <li className="card vr-row">
      <div className="vr-name">
        <strong>{m.name}</strong>
        <span className="dim">{m.family}</span>
      </div>
      <div className="vr-size">
        <span className="tnum vr-file">{fmtGiB(e.fileBytes)}</span>
        <span className="dim">{quant} file, measured · <a href={tree} target="_blank" rel="noopener noreferrer">{m.gguf_repo}{NEW_TAB}</a></span>
      </div>
      <div className="vr-est">
        <span className="dim">
          {e.cacheKnown
            ? `Plus the memory a ${e.context.capped ? '' : fmtTokens(e.context.tokens) + ' '}context needs, and the runtime.`
            : "How much memory this model's context needs is unknown."}
        </span>
        {boundOver && <span className="dim">Counted at its most, the context does not fit; this model&apos;s real need is smaller, so it may.</span>}
        {e.upperBound && <span className="dim">Context counted at its most: {m.cache.why}.</span>}
        {!e.cacheKnown && m.cache.why && <span className="dim">{m.cache.why}.</span>}
        {e.context.capped && <span className="dim">This model takes at most {fmtTokens(e.context.tokens)} tokens, so that is what is counted.</span>}
      </div>
      <div className="vr-links">
        {m.on_catalog && <Link to={modelPagePath(m.openrouter)}>Model page →</Link>}
        {m.on_catalog && (m.price_in != null || m.price_out != null) && (
          <span className="dim">Via API: {fmtPrice(m.price_in)} in / {fmtPrice(m.price_out)} out per 1M tokens</span>
        )}
      </div>
    </li>
  )
}
