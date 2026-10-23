import { useEffect, useMemo, useState } from 'react'
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
 * THE FIGURE IS MEASURED, THE GROUP IS ESTIMATED (rule 3). Each row shows the
 * size of the exact GGUF file, read from Hugging Face. The total that decides
 * fits / tight / won't fit adds the KV cache for the chosen context and a
 * runtime allowance, and is labelled "estimate" wherever it appears.
 *
 * THE CHOICES LIVE IN THE ADDRESS (?hw=&n=&q=&ctx=&kv=), so a reader can
 * bookmark their own machine and a shared link opens on the same answer.
 */

const QUANT_WORDS = { Q4_K_M: '4-bit', Q8_0: '8-bit' }
const CACHE_WORDS = { f16: 'Standard (16-bit)', q8_0: '8-bit (smaller)' }
const GROUPS = [
  ['fits', 'Fits', 'Room to spare after the file, the context and the runtime.'],
  ['tight', 'Tight', 'Fits by the estimate, with little or no room left. Close other GPU apps, or shorten the context.'],
  ['wont', "Won't fit", 'Needs more memory than this hardware has, by the estimate. Most can still run partly on the CPU, much more slowly.'],
]
const DEFAULT_HW = 'rtx-4060'
const fmtTokens = (n) => (n >= 1024 ? `${Math.round(n / 1024)}K` : String(n))
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

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
    const out = { fits: [], tight: [], wont: [], unmeasured: [] }
    for (const r of rows || []) (r.e ? out[r.e.group] : out.unmeasured).push(r)
    // Largest file first: the biggest model that fits is usually the one a reader wants.
    for (const k of ['fits', 'tight', 'wont']) out[k].sort((a, b) => b.e.fileBytes - a.e.fileBytes)
    return out
  }, [rows])

  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <nav className="tc-trail label" aria-label="Breadcrumb">
          <Link to="/tools">Tools</Link> <span aria-hidden="true">/</span> Can I run it?
        </nav>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Can I run it? Local LLM VRAM calculator</h1>
        <p className="tc-lead">
          Pick your graphics card or Mac and see which open models fit in its memory at 4-bit or 8-bit.
          Every size is the measured size of the actual model file; whether it fits is an estimate that
          adds the memory your context length needs.
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
                      <option key={d.id} value={d.id}>{d.name} · {d.memory_gib} GiB</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            {device.kind === 'discrete' && (
              <div className="vr-field">
                <span className="label">How many</span>
                <div className="vr-seg" role="radiogroup" aria-label="How many cards">
                  {[1, 2, 3, 4].map((n) => (
                    <button key={n} type="button" role="radio" aria-checked={cards === n}
                            className={cards === n ? 'on' : ''} onClick={() => set({ n })}>{n}×</button>
                  ))}
                </div>
              </div>
            )}
            <div className="vr-field">
              <span className="label">Quantization</span>
              <div className="vr-seg" role="radiogroup" aria-label="Quantization">
                {c.quants.map((k) => (
                  <button key={k} type="button" role="radio" aria-checked={quant === k}
                          className={quant === k ? 'on' : ''} onClick={() => set({ q: k })}>
                    {QUANT_WORDS[k] || k} <span>{k}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="vr-field">
              <span className="label">Context length</span>
              <div className="vr-seg" role="radiogroup" aria-label="Context length">
                {c.contexts.map((t) => (
                  <button key={t} type="button" role="radio" aria-checked={tokens === t}
                          className={tokens === t ? 'on' : ''} onClick={() => set({ ctx: t })}>{fmtTokens(t)}</button>
                ))}
              </div>
            </div>
            <div className="vr-field">
              <span className="label">KV cache</span>
              <div className="vr-seg" role="radiogroup" aria-label="KV cache type">
                {Object.keys(c.kv_cache_bytes).map((k) => (
                  <button key={k} type="button" role="radio" aria-checked={cacheType === k}
                          className={cacheType === k ? 'on' : ''} onClick={() => set({ kv: k })}>{CACHE_WORDS[k] || k}</button>
                ))}
              </div>
            </div>
            <p className="dim vr-budget">
              {device.kind === 'unified'
                ? <>A Mac lets its GPU use about {Math.round(c.apple_gpu_share * 100)}% of unified memory by default: {fmtGiB(device.memory_gib * c.apple_gpu_share * 2 ** 30)} of {device.memory_gib} GiB.</>
                : <>{cards > 1 ? `${cards} cards, ${cards * device.memory_gib} GiB together, split by layer.` : `${device.memory_gib} GiB of graphics memory.`}</>}
            </p>
          </section>

          <input className="vr-search" type="search" value={q} onChange={(e) => setQ(e.target.value)}
                 placeholder="Search models (Llama, Qwen, Gemma...)" aria-label="Search models" />

          {GROUPS.map(([key, title, note]) => (
            <section key={key} className="stack stack-2" aria-label={title}>
              <div className={`vr-group-head vr-${key}`}>
                <h2>{title} <span className="dim">{plural(grouped[key].length, 'model')}</span></h2>
                <p className="dim">{note}</p>
              </div>
              {grouped[key].length
                ? <ul className="vr-list">{grouped[key].map(({ m, e }) => <Row key={m.id} m={m} e={e} quant={quant} />)}</ul>
                : <p className="dim">None of the models{q ? ` matching "${q}"` : ''}.</p>}
            </section>
          ))}

          {(grouped.unmeasured.length > 0 || data.not_measured.length > 0) && (
            <Notice icon={<IconAlert />}>
              Not shown, because their {quant} file has not been measured yet:{' '}
              {[...grouped.unmeasured.map((r) => r.m.name), ...data.not_measured].join(', ')}.
              A missing size is never estimated.
            </Notice>
          )}

          <section className="card stack stack-2 vr-method">
            <h2 style={{ fontSize: 'var(--fs-h3)', margin: 0 }}>How this is worked out</h2>
            <p>
              <strong>The size shown is measured:</strong> the size of the model&apos;s actual {quant} GGUF file
              on Hugging Face, summed over its parts, in GiB (a graphics card&apos;s &quot;8 GB&quot; is 8 GiB).
              Each row links the repository it was measured in.
            </p>
            <p>
              <strong>Whether it fits is an estimate:</strong> the file, plus the memory the context needs
              (worked out from the layers and attention heads stated in the file&apos;s own header), plus
              about {c.runtime_overhead_gib} GiB for the runtime{c.overhead_per_card ? ', once per card' : ''}.
              It fits when that is at most {Math.round(c.fits_at_most * 100)}% of the memory available, and is
              tight up to 100%. Where the header does not say exactly which layers keep the context, the
              context memory is an upper bound, and the row says so.
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
  return (
    <li className="card vr-row">
      <div className="vr-name">
        <strong>{m.name}</strong>
        <span className="dim">{m.family}</span>
      </div>
      <div className="vr-size">
        <span className="tnum vr-file">{fmtGiB(e.fileBytes)}</span>
        <span className="dim">{quant} file, measured · <a href={tree} target="_blank" rel="noopener noreferrer">{m.gguf_repo}</a></span>
      </div>
      <div className="vr-est">
        <span className="tnum">≈ {fmtGiB(e.total)} <span className="dim">estimate</span></span>
        <span className="dim">
          file + {e.cacheBytes == null ? 'context memory unknown' : `${fmtGiB(e.cacheBytes)} for ${fmtTokens(e.context.tokens)} context`}
          {' '}+ {fmtGiB(e.overheadBytes)} runtime
        </span>
        {e.upperBound && <span className="dim">Context memory is an upper bound: {m.cache.why}.</span>}
        {e.cacheBytes == null && m.cache.why && <span className="dim">{m.cache.why}.</span>}
        {e.context.capped && <span className="dim">This model takes at most {fmtTokens(e.context.tokens)} tokens.</span>}
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
