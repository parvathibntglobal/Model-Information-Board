import { useEffect, useMemo, useState } from 'react'
import { adminSchedules, industryAiInfo } from '../api'
// One set of platform labels for every AI in industries view (#668 review).
import { PLATFORM_LABEL } from '../industry-ai/parts'
import { scheduleWords, when } from '../scheduleWords'

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
 *
 * ONE AGENT PER PAGE (2026-11-25): `agent="industry"` (AI in industries) shows the
 * keyword agent - its industries, keywords and caps; `agent="watch"` (AI Watch,
 * routes/AIWatch.jsx) shows the observer agent - its watch lists and people. The
 * rules both share (AI terms, filters, retention, patterns) are on both.
 */

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

/**
 * WHEN IT RUNS (2026-11-25, Parvathi): the harvest's schedule, switch, last and
 * next run, read from the workflow file and GitHub (GET /admin/schedules, the
 * `industry-ai` feed) - the same source as Admin -> Scheduler, so no time is
 * written here. A run list GitHub did not give is said, never "no run yet".
 */
function WhenItRuns({ watchOn, isWatch }) {
  const [state, setState] = useState({ data: null, err: null })
  useEffect(() => {
    let alive = true
    adminSchedules()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])
  const f = state.data?.feeds.find((x) => x.key === 'industry-ai')
  const s = f?.setup || {}
  const gh = f?.github || {}
  const last = (gh.runs || [])[0]
  const sw = f?.switch?.state
  return (
    <section className="card iai-card">
      <h2>When it runs</h2>
      {state.err && <p className="dim">The schedule could not be read: {state.err}</p>}
      {!state.data && !state.err && <p className="dim">Reading the schedule…</p>}
      {state.data && !f && <p className="dim">This backend does not report the Industry AI schedule.</p>}
      {f && (
        <>
          <p className="iai-def">
            {s.unreadable ? <b>On a schedule that can’t be read here.</b> : (s.starts_after || []).length > 0 ? (
              <>
                <b>Daily, when {s.starts_after.join(' or ')} finishes</b>
                {s.waits_for && !s.starts_after.includes(s.waits_for) && <>, never while {s.waits_for} is still running</>}
                {(s.crons || []).length > 0 && <>; a backup run is due {scheduleWords(s.crons)}, for a day that one does not start it</>}.
              </>
            ) : <b>{scheduleWords(s.crons)}.</b>}{' '}
            {isWatch
              ? <>Each day two runs go one after the other: the keyword run, then the observer&apos;s own run
                {watchOn === false && ' (the observer is off in the contract, so only a run started by hand reads the watch lists)'}.</>
              : <>Each day two runs go one after the other: the keyword run, for one group of industries, then the
                observer agent&apos;s own run.</>}
            {' '}A scheduled run harvests only while its on/off switch is on; it can also be started by hand.
          </p>
          <dl className="iai-settings">
            <div><dt>On/off switch</dt><dd title={f.variable ? `Repository variable ${f.variable}` : undefined}>
              {sw === 'on' ? 'on' : sw === 'off' ? 'off' : 'can’t be read here'}
            </dd></div>
            <div><dt>Last run</dt><dd>
              {gh.unreadable ? 'can’t be read here'
                : last ? <>{when(last.started_at)}<span className="dim iai-dd-note">{' '}
                  {(last.conclusion || last.status).replace('_', ' ')}</span></> : 'no run yet'}
            </dd></div>
            <div><dt>Next due</dt><dd>
              {f.next_run ? when(f.next_run) : '–'}
              {sw === 'off' && <span className="dim iai-dd-note"> (does nothing while the switch is off)</span>}
            </dd></div>
          </dl>
          <p className="dim iai-note">GitHub often starts a scheduled job late, so &quot;next due&quot; is when a
            run is due, not when it finishes. Admin → Scheduler shows every run.</p>
        </>
      )}
    </section>
  )
}

/** The words for each reason a post is dropped, as the counts view names them
 *  (IndustryAI.jsx REASON_LABEL), with what each one means. Settings come from
 *  the payload, so no number is written here (rule 11). */
function FilterWords({ info, isWatch }) {
  const { run, watch } = info
  const all = [
    ['No AI term', 'It names none of the AI terms below.'],
    !isWatch && ['No industry term', <>It names none of the industry&apos;s keywords, or only an ambiguous keyword without
      one of its context words within <span className="tnum">{run.context_window_words ?? '–'}</span> words.</>],
    !isWatch && ['Older than the run window', <>Posted more than <span className="tnum">{run.window_days ?? '–'}</span> days
      before the run.</>],
    isWatch && ['Watched post older than the watch window', <>A watch-list post first seen more than{' '}
      <span className="tnum">{watch.lookback_days ?? '–'}</span> days after it was posted.</>],
    ['Same article shared elsewhere', 'The same article linked from several posts: kept once, the copies counted as shares.'],
    ['Same author, same post again', 'One person posting the same thing twice.'],
    ['Near-duplicate text', 'Almost the same words as a post already kept.'],
    ['Too short', <>Fewer than <span className="tnum">{run.min_text_chars ?? '–'}</span> characters of text.</>],
    ['Bot account', 'Posted by an account on the bot list.'],
    ['Not English', 'Written in another language.'],
    ['Spam or scam', 'Matches a spam pattern: engagement bait, trading-signal groups, “guaranteed returns” and the like.'],
    ['Sponsored or affiliate', 'Labelled as sponsored, a paid partnership, or carrying an affiliate tag.'],
    ['Hiring or job ad', 'An employer advertising a job. A job seeker writing about one is kept.'],
    ['Sign-up ad', 'Mainly a call to register, enrol or use a promo code, unless it also teaches something: then it is kept as How-to & tips.'],
  ]
  const rows = all.filter(Boolean)
  return (
    <section className="card iai-card">
      <h2>What the filters and labels mean</h2>
      <p className="dim iai-def">
        The reasons a post is dropped, as the counts view names them, and how a kept post is labelled. The exact
        patterns are under &quot;Filter and labelling patterns&quot; below.
      </p>
      <Collapse heading={<>Why a post is dropped <span className="tnum">({rows.length})</span></>}>
        <dl className="iai-words">
          {rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
        </dl>
      </Collapse>
      <Collapse heading="How a kept post is labelled">
        <dl className="iai-words">
          {isWatch ? (
            <>
              <div><dt>General AI</dt><dd>A watched post that names an AI term but no industry: general AI news and
                opinion. Most of what the observer keeps.</dd></div>
              <div><dt>Mentions an industry</dt><dd>A watched post that names an industry&apos;s keywords is filed under
                every industry it names, and shown under Mentions.</dd></div>
            </>
          ) : (
            <div><dt>Industry</dt><dd>Every industry whose keywords the post names. A post found by one
              industry&apos;s search but naming none of its keywords is counted as <b>Domain unconfirmed</b>, apart
              from every industry.</dd></div>
          )}
          <div><dt>Content type</dt><dd>The first type whose pattern matches, in this order:{' '}
            {info.types.map((t) => TYPE_LABEL[t] || t).join(', ')}. A post that matches none is a Discussion.</dd></div>
          <div><dt>Use case</dt><dd>Someone describing what they or their team use AI for. It counts only when the
            sentence names an AI tool or term: &quot;I use it for my notes&quot; is not a use case, &quot;I used
            Claude to&quot; is.</dd></div>
          <div><dt>Use-case stage</dt><dd>For a use case only: deployed, pilot or first-hand, from the first stage
            pattern that matches; none when no pattern does.</dd></div>
          <div><dt>Low engagement</dt><dd>A post with engagement at or below{' '}
            <span className="tnum">{run.low_engagement_max ?? '–'}</span> is flagged, never dropped.</dd></div>
        </dl>
      </Collapse>
    </section>
  )
}

/** TEXT RETENTION (contract `retention:`): when a post's words are emptied. */
function Retention({ info }) {
  const r = info.retention || {}
  if (r.clear_text_after_days == null) return null
  const name = (k) => info.domains.find((d) => d.key === k)?.name || k
  const kept = (r.kept_domains || []).map(name)
  const which = [r.dropped && 'every dropped post', kept.length > 0 && `every kept post in ${kept.join(', ')}`]
    .filter(Boolean).join(' and ')
  return (
    <section className="card iai-card">
      <h2>How long a post&apos;s text is kept</h2>
      <p className="iai-def">
        <span className="tnum">{r.clear_text_after_days}</span> days after a post is first stored, its title and text
        are emptied for {which || 'no post (nothing is set to be cleared)'}. The row stays, with its dates, labels
        and reasons, so every count on the page is unchanged, and a cleared post is never labelled again.
      </p>
      {kept.length > 0 && (
        <p className="dim iai-note">{kept.join(', ')} {kept.length === 1 ? 'holds' : 'hold'} posts about people&apos;s
          own lives, so even a kept one loses its words. Anything drafted from those posts has to quote them within
          that time.</p>
      )}
    </section>
  )
}

export default function IndustryAIInfo({ agent = 'industry' }) {
  const isWatch = agent === 'watch'
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
        <h2>How it works</h2>
        <p className="iai-def">
          It is <b>code only</b>: no language model reads, labels or scores a post.{' '}
          {isWatch
            ? 'It has its own daily run, after the keyword run (see "When it runs"), and its posts go through the same steps.'
            : 'It has its own daily run, one group of industries a day (see "When it runs"); the observer agent runs separately, after it.'}
        </p>
        <div className="iai-agents">
          {isWatch ? (
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
                A watched post that names an industry&apos;s keywords is listed under Mentions; one that names
                none is General AI. It reads
                back <span className="tnum">{watch.lookback_days ?? '–'}</span> days from when it first sees a post,
                with its own request caps.
              </p>
            </div>
          ) : (
            <div className="iai-agent">
              <div className="iai-agent-head">
                <h3>Industry AI agent</h3>
                <span className={`iai-tag${run.enabled ? ' iai-tag-on' : ''}`}>
                  {run.enabled === true ? 'harvests allowed' : run.enabled === false ? 'harvests refused' : 'not set'}
                </span>
              </div>
              <p className="dim iai-def">
                Finds posts <b>by keyword</b>. Each industry has its own keywords and its own searches on{' '}
                {Object.keys(run.max_requests || {}).map(plat).join(', ')}. A post is kept only if it names an AI term{' '}
                <i>and</i> one of the industry&apos;s keywords, and was posted within the last{' '}
                <span className="tnum">{run.window_days ?? '–'}</span> days.
              </p>
              <p className="dim iai-note">
                Searches <span className="tnum">{active.length}</span> of <span className="tnum">{info.domains.length}</span>{' '}
                industries and roles now: the active ones under &quot;Industries and keywords&quot; below.
              </p>
            </div>
          )}
        </div>

        <h3 className="iai-sub">What happens to every post</h3>
        <ol className="iai-steps">
          <li><b>Harvest</b>: the agent&apos;s queries, within each platform&apos;s request cap.</li>
          <li><b>Sieve</b>: the AI term, keyword and date tests above.</li>
          <li><b>Dedupe</b>: the same article shared on several platforms, the same author repeating a post, or
            near-identical text count once.</li>
          <li><b>Filter</b>: too short, bots, not English, spam, sponsored posts, hiring and sign-up ads are
            dropped, and counted by reason on the counts view.</li>
          <li><b>Label</b>: the industry or industries its keywords confirm, and a content type (
            {info.types.map((t) => TYPE_LABEL[t] || t).join(', ')}).</li>
          <li><b>Store</b>: this summary shows counts only. An industry&apos;s own page lists its posts, each
            with its text up to its first <span className="tnum">{info.excerpt_chars ?? '–'}</span> characters (most
            posts are shorter, so are shown whole) and a link to the original.</li>
        </ol>
        <dl className="iai-settings">
          <div><dt>Shortest post kept</dt><dd className="tnum">{run.min_text_chars ?? '–'} characters</dd></div>
          <div><dt>Context distance</dt><dd className="tnum">{run.context_window_words ?? '–'} words</dd></div>
          <div><dt>Rules version</dt><dd><span className="mono">{info.rules_version || '–'}</span>
            {info.versions?.[info.rules_version] && (
              <span className="dim iai-dd-note"> {info.versions[info.rules_version]}</span>)}</dd></div>
        </dl>
        {run.pages_per_query?.x_clubbed != null && run.x_clubbed_min_keywords != null && (
          <p className="dim iai-note">An X search that groups at least{' '}
            <span className="tnum">{run.x_clubbed_min_keywords}</span> keywords reads{' '}
            <span className="tnum">{run.pages_per_query.x_clubbed}</span> pages of results; any other search reads{' '}
            {Object.entries(run.pages_per_query).filter(([k]) => k !== 'x_clubbed')
              .map(([k, n]) => `${n} ${n === 1 ? 'page' : 'pages'} on ${plat(k)}`).join(' and ')}.</p>
        )}
        {!isWatch && caps.length > 0 && (
          <>
            <h3 className="iai-sub">Industry AI agent: request cap per platform, per run</h3>
            <ul className="iai-caps">
              {caps.map(([p, n]) => <li key={p}><span>{plat(p)}</span><b className="tnum">{n}</b></li>)}
            </ul>
            <p className="dim iai-note">Reddit and X requests are metered and share their monthly quota with
              the model fetches.</p>
          </>
        )}
      </section>

      <WhenItRuns watchOn={watch.enabled} isWatch={isWatch} />

      {!isWatch && (
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
      )}

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

      {isWatch && (
        <section className="card iai-card">
          <h2>Watch lists (observer agent)</h2>
          <p className="dim iai-def">
            What the observer agent reads on each run: the newest posts of these communities, accounts and lists.
          </p>
          <dl className="iai-settings">
            <div><dt>Switch</dt><dd>{onOff(watch.enabled)}</dd></div>
            <div><dt>Looks back</dt><dd className="tnum">{watch.lookback_days ?? '–'} days</dd></div>
          </dl>
          {watch.x_club_max != null && (
            <p className="dim iai-note">X accounts are read up to <span className="tnum">{watch.x_club_max}</span> per
              search{watch.x_pages != null && <>, <span className="tnum">{watch.x_pages}</span> pages each</>}
              {watch.x_suffix && <>, with <code>{watch.x_suffix}</code> added</>}.</p>
          )}
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
          {src.instagram && (
            <Collapse heading={<>Instagram accounts ({src.instagram.length}){watchCaps.instagram != null && ` · cap ${watchCaps.instagram}`}</>}>
              <Chips items={src.instagram.map((s) => `@${s}`)} mono />
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
      )}

      <Retention info={info} />

      <FilterWords info={info} isWatch={isWatch} />

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
