import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { liveWeek } from '../api'
import { fmtCtx, fmtUsd, modelPagePath } from '../catalog/format'
import NotFound from '../components/NotFound'
import { useHead } from '../seo/head'
import { liveWeek as weekHead } from '../seo/pages'
import { day, engineers, modelHref, shortName, topicHref, problems as problemsOf } from './live'

/**
 * THIS WEEK IN MODELS (2026-10-15). One week, Monday to Sunday (UTC), built
 * in code from the catalogue, the price history and the board's public
 * reports (judge/blog_live.py). Every line is a count, a date or a published
 * price; nothing is written by a model.
 */

const price = (n) => (n == null ? 'not per token' : `${fmtUsd(n)}/M`)

function Was({ was, now }) {
  if (was === now) return <span className="dim">{price(now)}</span>
  return <span>{price(was)} → <b>{price(now)}</b></span>
}

export default function ThisWeek({ start }) {
  const nav = useNavigate()
  const [state, setState] = useState({ w: null, err: null, notFound: false })
  useHead(state.notFound ? false : weekHead(start))

  useEffect(() => {
    setState({ w: null, err: null, notFound: false })
    liveWeek(start)
      .then((w) => setState({ w, err: null, notFound: false }))
      .catch((e) => setState({ w: null, err: e.message, notFound: e.status === 404 }))
  }, [start])

  if (state.notFound) return <NotFound what="week" back={{ to: '/blogs/this-week', label: 'This week' }} />
  const w = state.w
  const ph = w?.price_history
  return (
    <div className="shell lv-page">
      <div className="lv-crumb"><Link to="/blogs">Blogs</Link><span>/</span><span>This week in models</span></div>
      <header className="lv-head">
        <span className="lv-kicker">Weekly · built from data, not written</span>
        <h1>This week in models</h1>
        {w && (
          <div className="lv-bar">
            <label className="lv-week">
              <span>Week of</span>
              <select value={w.week} onChange={(e) => nav(e.target.value === w.weeks[0] ? '/blogs/this-week' : `/blogs/this-week/${e.target.value}`)}>
                {w.weeks.map((x) => <option key={x} value={x}>{day(x)}</option>)}
              </select>
            </label>
            {w.in_progress && <span className="lv-note lv-inline">Week in progress, through {day(w.through)}.</span>}
          </div>
        )}
      </header>
      {state.err && <p className="lv-note">This week could not be read: {state.err}</p>}
      {!w && !state.err && <div className="skel" style={{ height: 320 }} />}
      {w && (
        <div className="lv-week-grid">
          <section className="lv-card">
            <h2>New on OpenRouter <span>{w.listings.length}</span></h2>
            {w.listings.length === 0 ? <p className="lv-none">No model was listed this week.</p> : (
              <ul className="lv-lines">
                {w.listings.map((m) => (
                  <li key={m.id}>
                    <Link to={modelPagePath(m.id)}><b>{shortName(m.name)}</b></Link>
                    <span className="dim"> {m.provider} · writes {m.outputs.join(', ') || 'not published'}</span>
                    <span className="lv-meta">
                      {m.price_in != null || m.price_out != null ? `${price(m.price_in)} in · ${price(m.price_out)} out` : 'price not per token'}
                      {m.context ? ` · ${fmtCtx(m.context)} context` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="lv-card">
            <h2>What engineers wrote <span>{w.reports.entries}</span></h2>
            <p className="lv-note">
              {w.reports.entries} reports from {engineers(w.reports.voices)} about {w.reports.models} models,
              counted by <b>when the post was written</b>, not when we found it. A past week can grow when a
              later fetch finds an older post.
            </p>
            {w.busiest.length > 0 && (
              <>
                <p className="lv-label">Most written about, by engineers that week</p>
                <ul className="lv-lines">
                  {w.busiest.map((r) => (
                    <li key={r.model.id}>
                      <Link to={modelHref(r.model)}><b>{shortName(r.model.name)}</b></Link>
                      <span className="lv-meta">
                        {engineers(r.voices)} · <span className="lv-pos">{r.working} working</span> ·{' '}
                        <span className="lv-neg">{problemsOf(r.problems)}</span>{r.neutral ? ` · ${r.neutral} neutral` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>

          <section className="lv-card">
            <h2>First reports on a topic <span>{w.first_voices.length}</span></h2>
            {w.first_voices.length === 0 ? <p className="lv-none">No job or capability got its first report this week.</p> : (
              <ul className="lv-lines">
                {w.first_voices.slice(0, 12).map((t) => (
                  <li key={`${t.section}:${t.slug}`}>
                    <Link to={topicHref(t.section, t.slug)}><b>{t.topic}</b></Link>
                    <span className="lv-meta">first written {day(t.first)} · {engineers(t.voices)} so far, {t.models} {t.models === 1 ? 'model' : 'models'}</span>
                  </li>
                ))}
                {w.first_voices.length > 12 && <li className="dim">and {w.first_voices.length - 12} more</li>}
              </ul>
            )}
          </section>

          <section className="lv-card">
            <h2>Retiring soon <span>{w.retiring.length}</span></h2>
            <p className="lv-note">Dates in the {w.retiring_within_days} days after this week, as OpenRouter's catalogue reads today.</p>
            {w.retiring.length === 0 ? <p className="lv-none">No retirement date falls in that window.</p> : (
              <ul className="lv-lines">
                {w.retiring.map((m) => (
                  <li key={m.id}>
                    <Link to={modelPagePath(m.id)}><b>{shortName(m.name)}</b></Link>
                    <span className="lv-meta">{day(m.date)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="lv-card lv-wide">
            <h2>Price changes <span>{w.prices.length}</span></h2>
            {w.prices.length === 0 ? <p className="lv-none">No price change is recorded for this week.</p> : (
              <ul className="lv-lines">
                {w.prices.map((r, i) => (
                  <li key={`${r.model.id}:${i}`}>
                    <Link to={modelHref(r.model)}><b>{shortName(r.model.name)}</b></Link>
                    <span className="lv-meta">
                      in <Was was={r.was_in} now={r.now_in} /> · out <Was was={r.was_out} now={r.now_out} /> · {day(r.on)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {ph && (
              <p className={`lv-note${ph.differs_now > 0 ? ' lv-warn' : ''}`}>
                The price history's last recorded change is {ph.last_change ? day(ph.last_change) : 'not recorded'}.{' '}
                {ph.differs_now > 0
                  ? `Today's catalogue (read ${day(ph.catalogue_read)}) shows a different price from that history for ${ph.differs_now} of ${ph.compared} models, so changes after that date are notFound here - not absent.`
                  : `Today's catalogue matches the last recorded price for all ${ph.compared} models compared.`}
              </p>
            )}
          </section>
        </div>
      )}
      {w && (
        <footer className="lv-foot">
          <p>Built in code from OpenRouter's catalogue, the registry's price history and the board's reports, counting every source we read.
            No model writes this page and no model is scored or ranked.</p>
        </footer>
      )}
    </div>
  )
}
