import { useEffect, useMemo, useState } from 'react'
import { industryAiInfo } from '../api'

/**
 * AI IN INDUSTRIES -> INFO (2026-11-24, Parvathi): what the page's two agents -
 * the Industry AI agent (by keyword) and the observer agent (watch lists) -
 * search for and how they decide, read from contract/industry_ai.yaml as it
 * stands (judge/industry_ai/view.py industry_ai_info). Every domain's keywords,
 * ambiguous terms, exclusions and queries; the AI terms; the run and watch
 * settings; the filter patterns.
 *
 * NO NUMBER IS WRITTEN IN THIS FILE (rule 11): windows, caps and switches all
 * come from the payload, so the page cannot disagree with the contract. Every
 * figure here is a SETTING or a count of configured terms, never a count of
 * collected posts - those live on the counts view.
 */

const PLATFORM_LABEL = {
  reddit: 'Reddit', x: 'X', github: 'GitHub', hackernews: 'Hacker News', devto: 'dev.to',
  bluesky: 'Bluesky', feeds: 'Blogs & feeds',
}
const TYPE_LABEL = {
  use_case: 'Use case', how_to: 'How-to & tips', tool_or_product: 'Tool or product',
  research: 'Research', news: 'News', discussion: 'Discussion',
}
const PATTERN_LABEL = {
  spam_patterns: 'Spam and scams', ad_patterns: 'Sign-up ads', hiring_patterns: 'Hiring and job ads',
  promo_patterns: 'Sponsored or affiliate', teach_patterns: 'Teaching (how-to) phrasing',
}
const HN_LIST_LABEL = { show_hn: 'Show HN', ask_hn: 'Ask HN', front_page: 'Front page' }

const onOff = (v) => (v === true ? 'on' : v === false ? 'off' : 'not set')
const plat = (p) => PLATFORM_LABEL[p] || p
// `watch.people` keys are snake_case names (simon_willison -> Simon Willison).
const personName = (k) => k.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
const handle = (p, h) => (p === 'x' ? `@${h}` : h)

/** A list folded under its heading, closed until clicked (Parvathi, 2026-11-24).
 *  `heading` keeps the look it had as a plain heading; `open` is true when the
 *  keyword search hits something inside, so a match is never hidden. */
function Collapse({ heading, open, className = 'iai-sub', children }) {
  return (
    <details className="iai-collapse" open={open || undefined}>
      <summary className={className}>{heading}</summary>
      <div className="iai-collapse-body">{children}</div>
    </details>
  )
}

const hits = (list, q) => Boolean(q) && (list || []).some((t) => String(t || '').toLowerCase().includes(q))

function Chips({ items, mono }) {
  if (!items?.length) return <p className="dim iai-none">None.</p>
  return (
    <ul className={`iai-chips${mono ? ' iai-chips-mono' : ''}`}>
      {items.map((t, i) => <li key={`${t}-${i}`} className="iai-chip">{t}</li>)}
    </ul>
  )
}

function Queries({ queries, q }) {
  const rows = Object.entries(queries || {}).flatMap(([p, q]) => [
    ...(q.subreddits?.length ? [[`${plat(p)} communities`, q.subreddits.map((s) => `r/${s}`)]] : []),
    ...(q.search?.length ? [[`${plat(p)} searches`, q.search]] : []),
  ])
  if (!rows.length) return <p className="dim iai-none">No queries listed.</p>
  return (
    <div className="iai-queries">
      {rows.map(([label, list]) => (
        <Collapse key={label} className="iai-q-label" open={hits(list, q)}
                  heading={<>{label} <span className="dim tnum">({list.length})</span></>}>
          <Chips items={list} mono />
        </Collapse>
      ))}
    </div>
  )
}

/** One domain's or group's terms: the same shape at both levels. */
function TermBlock({ b, q }) {
  return (
    <>
      <Collapse open={hits(b.terms, q)}
                heading={<>Keywords <span className="tnum">({b.terms.length})</span></>}>
        <Chips items={b.terms} />
      </Collapse>
      {b.ambiguous.length > 0 && (
        <Collapse open={hits(b.ambiguous.map((a) => a.term), q)}
                  heading={<>Ambiguous keywords <span className="tnum">({b.ambiguous.length})</span></>}>
          <p className="dim iai-def">Counted only when one of the context words appears nearby.</p>
          <ul className="iai-ambig">
            {b.ambiguous.map((a) => (
              <li key={a.term}><b>{a.term}</b> <span className="dim">needs</span> {a.context.join(', ')}</li>
            ))}
          </ul>
        </Collapse>
      )}
      {b.exclude_phrases.length > 0 && (
        <Collapse heading={<>Excluded phrases <span className="tnum">({b.exclude_phrases.length})</span></>}>
          <Chips items={b.exclude_phrases} mono />
        </Collapse>
      )}
      <h4 className="iai-sub">Queries</h4>
      <Queries queries={b.queries} q={q} />
    </>
  )
}

function Domain({ d, open, q }) {
  const total = d.terms.length + d.groups.reduce((s, g) => s + g.terms.length, 0)
  return (
    <details className="card iai-domain" open={open}>
      <summary>
        <span className="iai-domain-name">{d.name}</span>
        <span className={`iai-tag${d.active ? ' iai-tag-on' : ''}`}>{d.active ? 'active' : 'off'}</span>
        {d.kind && <span className="dim iai-kind">{d.kind}</span>}
        <span className="dim tnum iai-domain-n">{total} keyword{total === 1 ? '' : 's'}</span>
      </summary>
      <div className="iai-domain-body">
        {d.definition && <p className="dim iai-def">{d.definition}</p>}
        <TermBlock b={d} q={q} />
        {d.groups.map((g) => (
          <section key={g.key} className="iai-group">
            <h3 className="iai-group-name">{g.name}</h3>
            {g.definition && <p className="dim iai-def">{g.definition}</p>}
            <TermBlock b={g} q={q} />
          </section>
        ))}
      </div>
    </details>
  )
}

/** Does a domain (or one of its groups) mention `q` in a name, keyword or query? */
function matches(d, q) {
  if (!q) return true
  const hay = (b) => [b.name, ...(b.terms || []), ...(b.ambiguous || []).map((a) => a.term),
    ...Object.values(b.queries || {}).flatMap((x) => [...(x.search || []), ...(x.subreddits || [])])]
  return [d, ...d.groups].some((b) => hay(b).some((s) => String(s || '').toLowerCase().includes(q)))
}

export default function IndustryAIInfo() {
  const [info, setInfo] = useState(null)
  const [err, setErr] = useState(null)
  const [scope, setScope] = useState('active')
  const [q, setQ] = useState('')

  useEffect(() => {
    let alive = true
    industryAiInfo().then((d) => alive && setInfo(d)).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  const needle = q.trim().toLowerCase()
  const shown = useMemo(() => (info?.domains || [])
    .filter((d) => scope === 'all' || d.active)
    .filter((d) => matches(d, needle)), [info, scope, needle])

  if (err) return <p className="iai-error">Could not load: {err}</p>
  if (!info) return <p className="dim">Loading…</p>

  const { run, watch } = info
  const active = info.domains.filter((d) => d.active)
  const caps = Object.entries(run.max_requests || {})
  const watchCaps = watch.max_requests || {}
  const src = watch.sources || {}
  const people = watch.people || []
  const hn = src.hackernews
    ? [...(src.hackernews.lists || []).map((l) => HN_LIST_LABEL[l] || l),
       ...(src.hackernews.authors || []).map((a) => `by ${a}`)]
    : []

  return (
    <div className="stack stack-4">
      <section className="card iai-card">
        <h2>Two agents fill this page</h2>
        <p className="iai-def">
          Both are <b>code only</b>: no language model reads, labels or scores a post. They run in the same weekly
          run, through the same steps, into the same counts, and a post both of them find is counted once.
        </p>
        <div className="iai-agents">
          <div className="iai-agent">
            <div className="iai-agent-head">
              <h3>Industry AI agent</h3>
              <span className={`iai-tag${run.enabled ? ' iai-tag-on' : ''}`}>
                {run.enabled === true ? 'harvests allowed' : run.enabled === false ? 'harvests refused' : 'not set'}
              </span>
            </div>
            <p className="dim iai-def">
              Finds posts <b>by keyword</b>. Each industry has its own keywords and its own searches on{' '}
              {Object.keys(PLATFORM_LABEL).map(plat).join(', ')}. A post is kept only if it names an AI term{' '}
              <i>and</i> one of the industry&apos;s keywords, and was posted within the last{' '}
              <span className="tnum">{run.window_days ?? '–'}</span> days.
            </p>
            <p className="dim iai-note">
              Searches <span className="tnum">{active.length}</span> of <span className="tnum">{info.domains.length}</span>{' '}
              industries now: the active ones under &quot;Industries and keywords&quot; below.
            </p>
          </div>
          <div className="iai-agent">
            <div className="iai-agent-head">
              <h3>Observer agent</h3>
              <span className={`iai-tag${watch.enabled ? ' iai-tag-on' : ''}`}>{watch.enabled ? 'on' : 'off'}</span>
            </div>
            <p className="dim iai-def">
              Finds posts <b>by who or where</b>, with no keyword: the newest posts of chosen communities, accounts
              and lists (&quot;Watch lists&quot; below). It catches new tools, workflows and opinions the keywords
              would not have guessed. A watched post needs an AI term; an industry keyword is optional.
            </p>
            <p className="dim iai-note">
              A watched post that names an industry&apos;s keywords is shown on that industry&apos;s card, counted
              apart from what the Industry AI agent found; one that names none is counted as General AI. It reads
              back <span className="tnum">{watch.lookback_days ?? '–'}</span> days from when it first sees a post,
              with its own request caps.
            </p>
          </div>
        </div>

        <h3 className="iai-sub">What happens to every post, from either agent</h3>
        <ol className="iai-steps">
          <li><b>Harvest</b>: the agent&apos;s queries, within each platform&apos;s request cap.</li>
          <li><b>Sieve</b>: the AI term, keyword and date tests above.</li>
          <li><b>Dedupe</b>: the same article shared on several platforms, the same author repeating a post, or
            near-identical text count once.</li>
          <li><b>Filter</b>: too short, bots, not English, spam, sponsored posts, hiring and sign-up ads are
            dropped, and counted by reason on the counts view.</li>
          <li><b>Label</b>: the industry or industries its keywords confirm, and a content type (
            {info.types.map((t) => TYPE_LABEL[t] || t).join(', ')}).</li>
          <li><b>Store</b>: only counts reach the page; no post text, link or author is shown.</li>
        </ol>
        <dl className="iai-settings">
          {/* run.enabled only allows or refuses a harvest; whether the weekly
              schedule fires is the INDUSTRY_AI_ENABLED repository variable,
              which this page cannot read - so neither label says "running". */}
          <div><dt>Schedule</dt><dd>{run.cadence || 'not set'}<span className="dim iai-dd-note"> when
            INDUSTRY_AI_ENABLED is set</span></dd></div>
          <div><dt>Shortest post kept</dt><dd className="tnum">{run.min_text_chars ?? '–'} characters</dd></div>
          <div><dt>Context distance</dt><dd className="tnum">{run.context_window_words ?? '–'} words</dd></div>
          <div><dt>Rules version</dt><dd className="mono">{info.pipeline_version || '–'}</dd></div>
        </dl>
        {caps.length > 0 && (
          <>
            <h3 className="iai-sub">Industry AI agent: request cap per platform, per run</h3>
            <ul className="iai-caps">
              {caps.map(([p, n]) => <li key={p}><span>{plat(p)}</span><b className="tnum">{n}</b></li>)}
            </ul>
            <p className="dim iai-note">Reddit and X requests are metered and share their monthly quota with
              the model fetches. The observer has its own caps, shown with its watch lists.</p>
          </>
        )}
      </section>

      <section className="stack stack-2">
        <div className="iai-domains-head">
          <h2 className="iai-h2">Industries and keywords</h2>
          <div className="iai-domains-tools">
            <button type="button" className={`chip${scope === 'active' ? ' chip-on' : ''}`}
                    onClick={() => setScope('active')}>Active <span className="x">{active.length}</span></button>
            <button type="button" className={`chip${scope === 'all' ? ' chip-on' : ''}`}
                    onClick={() => setScope('all')}>All <span className="x">{info.domains.length}</span></button>
            <input className="iai-search" type="search" value={q} placeholder="Find a keyword or query…"
                   aria-label="Find a keyword or query" onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>
        {shown.length === 0 && (
          <p className="dim">No {scope === 'active' ? 'active ' : ''}industry mentions &quot;{q}&quot;.
            {scope === 'active' && ' Try All.'}</p>
        )}
        {shown.map((d) => <Domain key={d.key} d={d} q={needle} open={Boolean(needle) || shown.length === 1} />)}
      </section>

      <section className="card iai-card">
        <h2>AI terms</h2>
        <p className="dim iai-def">
          A post must name at least one of these, whichever agent found it and in every industry. The word &quot;AI&quot; also counts on its
          own when written in capitals; lower-case &quot;ai&quot; and &quot;.ai&quot; do not. Names of models on
          the board are added at run time.
        </p>
        <Collapse heading={<>AI terms <span className="tnum">({info.ai_terms.length})</span></>}>
          <Chips items={info.ai_terms} />
        </Collapse>
        {info.global_exclude_phrases.length > 0 && (
          <Collapse heading={<>Removed before matching, in every industry{' '}
            <span className="tnum">({info.global_exclude_phrases.length})</span></>}>
            <Chips items={info.global_exclude_phrases} mono />
          </Collapse>
        )}
        {Object.keys(info.query_suffix || {}).length > 0 && (
          <Collapse heading="Added to every query">
            <ul className="iai-ambig">
              {Object.entries(info.query_suffix).map(([p, s]) => (
                <li key={p}><b>{plat(p)}</b> <code>{s}</code></li>
              ))}
            </ul>
          </Collapse>
        )}
      </section>

      <section className="card iai-card">
        <h2>Watch lists (observer agent)</h2>
        <p className="dim iai-def">
          What the observer agent reads on each run: the newest posts of these communities, accounts and lists.
        </p>
        <dl className="iai-settings">
          <div><dt>Switch</dt><dd>{onOff(watch.enabled)}</dd></div>
          <div><dt>Looks back</dt><dd className="tnum">{watch.lookback_days ?? '–'} days</dd></div>
        </dl>
        {src.reddit && (
          <Collapse heading={<>Reddit communities ({src.reddit.length}){watchCaps.reddit != null && ` · cap ${watchCaps.reddit}`}</>}>
            <Chips items={src.reddit.map((s) => `r/${s}`)} mono />
          </Collapse>)}
        {src.x && (
          <Collapse heading={<>X accounts ({src.x.length}){watchCaps.x != null && ` · cap ${watchCaps.x}`}</>}>
            <Chips items={src.x.map((s) => `@${s}`)} mono />
          </Collapse>)}
        {src.bluesky && (
          <Collapse heading={<>Bluesky accounts ({src.bluesky.length}){watchCaps.bluesky != null && ` · cap ${watchCaps.bluesky}`}</>}>
            <Chips items={src.bluesky} mono />
          </Collapse>)}
        {hn.length > 0 && (
          <Collapse heading={<>Hacker News ({hn.length}){watchCaps.hackernews != null && ` · cap ${watchCaps.hackernews}`}</>}>
            <Chips items={hn} mono />
          </Collapse>)}
        {people.length > 0 && (
          <Collapse heading={<>People on several platforms ({people.length})</>}>
            <p className="dim iai-def">
              Each person is counted as one author, not one per platform. Their same post on two platforms
              {watch.cross_post_hours != null && <> within <span className="tnum">{watch.cross_post_hours}</span> hours</>}
              {' '}is counted once, as a share.
            </p>
            <ul className="iai-ambig">
              {people.map((p) => (
                <li key={p.key}>
                  <b>{personName(p.key)}</b>{' '}
                  <span className="dim">{Object.entries(p.handles).map(([pl, h]) => `${plat(pl)} ${handle(pl, h)}`).join(' · ')}</span>
                </li>
              ))}
            </ul>
          </Collapse>)}
      </section>

      <details className="card iai-card iai-patterns">
        <summary><h2>Filter and labelling patterns</h2></summary>
        <p className="dim iai-def">The patterns the code matches, exactly as the contract writes them.</p>
        {Object.entries(info.patterns).map(([k, list]) => (
          <Collapse key={k} heading={<>{PATTERN_LABEL[k] || k} <span className="tnum">({list.length})</span></>}>
            <Chips items={list} mono />
          </Collapse>
        ))}
        {Object.entries(info.type_patterns).map(([t, list]) => (
          <Collapse key={t} heading={<>Type: {TYPE_LABEL[t] || t} <span className="tnum">({list.length})</span></>}>
            <Chips items={list} mono />
          </Collapse>
        ))}
        {Object.entries(info.stage_patterns).map(([s, list]) => (
          <Collapse key={s} heading={<>Use-case stage: {s.replace('_', '-')} <span className="tnum">({list.length})</span></>}>
            <Chips items={list} mono />
          </Collapse>
        ))}
      </details>
    </div>
  )
}
