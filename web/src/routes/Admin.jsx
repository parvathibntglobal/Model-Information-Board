import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { health, coveragePage, listModels, adminRuns, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Stat } from '../components/ui'
import UsagePanel from '../components/UsagePanel'
import BoardReview from '../components/BoardReview'
import DiscussedModels from '../components/DiscussedModels'
import KeywordsPanel from '../components/KeywordsPanel'
import PromptsPanel from '../components/PromptsPanel'
import SourcesPanel from '../components/SourcesPanel'
import StagesPanel from '../components/StagesPanel'
import RunsPanel from '../components/RunsPanel'
import DatabasePanel from '../components/DatabasePanel'
import SettingsPanel from '../components/SettingsPanel'
import FetchPanel from '../components/FetchPanel'
import ModelProposal from '../components/ModelProposal'
import SchedulerPanel from '../components/SchedulerPanel'
import BlogsPanel from '../components/BlogsPanel'
import { IconAlert, IconGrid, IconHeart } from '../components/Icons'

/**
 * Operations. `/health` needs nothing; the database-backed surfaces are each
 * allowed to be unreadable on their own, so one missing page does not blank the
 * others.
 */
function useSurface(fn, deps = []) {
  // `done` and `status` so a reader can tell "still asking" and "not signed
  // in" (401/403) apart from "the database did not answer".
  const [state, setState] = useState({ data: null, err: null, unreadable: null, done: false, status: null })
  useEffect(() => {
    let alive = true
    fn()
      .then((d) => alive && setState({ data: d, err: null, unreadable: null, done: true, status: 200 }))
      .catch((e) => alive && setState({
        data: null,
        err: e instanceof BoardUnreadable ? null : e.message,
        unreadable: e instanceof BoardUnreadable ? e.message : null,
        done: true,
        status: e?.status ?? null,
      }))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

/**
 * Collect evidence — the tracked models, each with a Fetch button and its
 * fetch-log history. Sweeping a model runs its evidence pipeline on demand and
 * appends new rows; the per-model history is served from the stored run logs.
 */
/** "today", "1 day ago", "12 days ago" - the full time is on hover. */
function agoShort(iso) {
  const at = Date.parse(iso)
  if (Number.isNaN(at)) return ''
  const days = Math.floor((Date.now() - at) / 86400000)
  return days <= 0 ? 'today' : days === 1 ? '1 day ago' : `${days} days ago`
}

function CollectEvidence() {
  const [models, setModels] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    listModels()
      .then((d) => alive && setModels(d.models || []))
      .catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [])

  // LAST FETCHED, PER ROW, from the shared fetch log's latest 300 runs - one
  // request, not one per model. A model with no completed run IN THAT WINDOW
  // shows no date at all rather than "never" (rule 4): an older fetch may
  // exist past the window. Failing to read the runs shows no dates either.
  const [lastOk, setLastOk] = useState({})
  useEffect(() => {
    let alive = true
    adminRuns(300)
      .then((d) => {
        const by = {}
        for (const r of d.runs || []) {
          if (r.status !== 'ok' || !r.model) continue
          const at = r.last_at || r.started_at
          if (at && (!by[r.model] || at > by[r.model])) by[r.model] = at
        }
        if (alive) setLastOk(by)
      })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  return (
    // A CARD LIKE EVERY OTHER SECTION. It was bare text on the page
    // background, the one section with no frame and no header strip.
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconGrid width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Collect evidence — sweep a model on demand</span>
        </div>
        {models && <span className="label">{models.length} tracked</span>}
      </div>
      <div className="card-intro">
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Each fetch runs a fresh harvest through the evidence pipeline and appends new rows.
          The fetch log and every past run are kept per model.
        </p>
      </div>
      <div className="card-body stack stack-3">
      {err && <Notice icon={<IconAlert />}>{err}</Notice>}
      {!models && !err && <div className="skel" style={{ height: 120 }} />}

      {/* AT THE TOP, AS CHIPS, because these are what you come to this section
          to do that is not "run a fetch" - and below thirteen model folds they
          were somewhere you had to scroll to find. Each opens in place; neither
          add nor stop-tracking acts on one click. */}
      {models && (
        <div style={{ borderBottom: '1px solid var(--border-soft)',
                      paddingBottom: 'var(--s3)' }}>
          <ModelProposal models={models} />
        </div>
      )}
      {models && models.length === 0 && (
        <p className="dim" style={{ fontSize: 'var(--fs-sm)' }}>No models tracked yet.</p>
      )}
      {/* ONE FOLD PER MODEL. Each row carries a whole FetchPanel - the button,
          the live stage list and the run history - so with more than a couple
          of models the page becomes a column of panels and the one you came to
          run is somewhere in it. Folded, the list is a list again.

          NOT folded into a single "Models" panel: the thing a reader is
          choosing between IS the models, so each needs to stay individually
          visible and individually clickable.

          Native <details>, same as the FAQ and the other folds: the panels
          stay in the DOM whether or not they are open. */}
      {models && models.map((m) => (
        <details key={m.model_version_id} className="disc disc-row">
          <summary>
            {/* ⚠ THE PROVIDER'S ID ON THE LINE, NOT OURS. This printed
                `mv_b3508133423993d7` beside every name - an internal database
                key, shown to a reader who cannot look it up, check it against
                the provider, or use it anywhere. The compare page already
                carries this rule and a test enforces it there; the admin list
                was the surface still doing it.

                `canonical_id` is the same model in the form the provider
                writes it, and the roster has returned it all along. */}
            {m.display_name || m.canonical_id || m.model_version_id}
            {m.canonical_id && <span className="n">{m.canonical_id}</span>}
            {/* The provider tag is gone: the name already starts with it
                ("Anthropic: Claude Fable 5.1"), so it said the same thing twice. */}
            {lastOk[m.display_name] && (
              <span className="disc-when" title={lastOk[m.display_name]}>
                fetched {agoShort(lastOk[m.display_name])}
              </span>
            )}
          </summary>
          <div className="disc-body stack stack-2">
            {/* ⚠ KEPT, AND MOVED INSIDE THE FOLD. Somebody debugging a run
                does need the internal key - it is what `board_entry` and
                `claim` are joined on. What it does not need is a place on the
                scan line, where it competes with the name for the eye and
                cannot be acted on. Open the row and it is here. */}
            <span className="dim mono" style={{ fontSize: 10 }}>
              {m.model_version_id}
            </span>
            <FetchPanel modelVersionId={m.model_version_id} />
          </div>
        </details>
      ))}
      </div>
    </section>
  )
}

/**
 * THE SECTIONS, AND THE NAV IS BUILT FROM THIS RATHER THAN BESIDE IT.
 *
 * One list, so a section cannot appear in the nav and not render, or render
 * with a heading that disagrees with the one you clicked. Adding a fifth panel
 * is one entry here.
 *
 * `id` GOES IN THE URL and is therefore permanent: `?s=board` is a link
 * somebody can send. Renaming one silently breaks saved links, which is why
 * these are short slugs and not the titles.
 */
const SECTIONS = [
  // THE ORDER IS THE ONE ASKED FOR, top to bottom, ruled 2026-10-05 by
  // @parvathibntglobal. `group` labels the run of sections that starts there;
  // `wired: false` marks a section that is layout only. None is, since Blogs
  // and Scheduler were wired on 2026-10-06.
  {
    id: 'service',
    group: 'Health',
    title: 'Service',
    blurb: 'Is the board up, and can it read the database',
    render: (ctx) => <ServicePanel hp={ctx.hp} cov={ctx.cov} />,
  },
  {
    id: 'usage',
    title: 'API usage — our cap',
    blurb: 'What we are spending, against the limits we set',
    render: () => <UsagePanel />,
  },
  {
    id: 'sources',
    group: 'Evidence',
    title: 'Sources',
    blurb: 'Where evidence comes from, and how each is reached',
    render: () => <SourcesPanel />,
  },
  {
    id: 'keywords',
    title: 'Keywords',
    blurb: 'What each platform is actually sent, per model',
    render: () => <KeywordsPanel />,
  },
  {
    id: 'pipeline',
    title: 'Evidence stages',
    blurb: 'What each stage of a fetch actually does',
    render: () => <StagesPanel />,
  },
  {
    id: 'models',
    group: 'Board & content',
    title: 'Models',
    blurb: 'Sweep a model on demand, add one, or stop tracking one',
    render: () => (
      <div className="stack stack-4">
        <CollectEvidence />
        {/* ⚠ BELOW THE TRACKED LIST, AND THE ORDER IS THE POINT. (Two cards
            now, so the rule that separated them went.) This
            section is "the models we watch"; the panel underneath is
            everything the board learned about models we did not. A reader
            who has just scrolled thirteen folds is exactly the reader who
            should see that 66 more have evidence. */}
        <DiscussedModels />
      </div>
    ),
  },
  {
    id: 'board',
    title: 'Board sections',
    blurb: 'Discovered by the classifier, and already live',
    render: () => (
      <div className="stack stack-4">
        <BoardReview />
        {/* ⚠ `DiscussedModels` WAS MOUNTED HERE TOO AND IS NOT ANY MORE.
            The argument for both was that the question belongs to neither
            section — the review shows which AXES the board discovered, that
            panel shows which MODELS it discovered them about.

            What that argument left out is that they are the SAME LIST under
            two headings, one screen apart, with the same counts. A reader who
            meets `64 of 78 models with evidence` twice does not think "two
            views of one fact"; they think one of the two is stale, and then
            they check. Saying it once in the section that owns the models is
            the cheaper answer, and the review still links out to it. */}
      </div>
    ),
  },
  // ⚠ THERE IS NO 'Capability candidates' SECTION, AND ITS ABSENCE IS A
  //   DECISION RATHER THAN THE OVERSIGHT IT LOOKS LIKE. `capability_key` is
  //   the CLOSED twelve from the first plan, where discovering capabilities
  //   was its own surface. The board replaced that: discovery now happens in
  //   `board_entries`, whose vocabulary is open and needs no ruling, and
  //   `schema.py` itself calls the closed path "an older scoring path and is
  //   NOT what the board displays".
  //
  //   So capabilities get no privilege the other two sections lack. Board
  //   sections above is the whole review surface. Ruled 2026-09-24 by
  //   @parvathibntglobal, after measuring that 24 of the 53 keys e5.5
  //   proposed ALREADY EXIST as a board slug — one observation, written
  //   into two vocabularies, only one of which anybody reads.
  //
  //   What still writes to `capability_candidate` is upstream of this file:
  //   the `proposed_capabilities` prompt field and the endpoint behind it.
  //   Both are shared code mid-batch, so they are raised on #434 rather
  //   than deleted from this side.
  {
    id: 'blogs',
    title: 'Blogs',
    blurb: 'Drafts from the evidence, waiting for approval',
    render: () => <BlogsPanel />,
  },
  {
    id: 'prompts',
    title: 'Prompts',
    blurb: 'Every prompt we send a model, composed not copied',
    render: () => <PromptsPanel />,
  },
  {
    id: 'scheduler',
    group: 'Operations',
    title: 'Scheduler',
    blurb: 'Scheduled fetches: schedule, queue, controls and log',
    render: () => <SchedulerPanel />,
  },
  {
    id: 'runs',
    title: 'Runs',
    blurb: 'Every fetch, across machines — and whether it finished',
    render: () => <RunsPanel />,
  },
  {
    id: 'database',
    title: 'Database',
    blurb: 'Which database, what is in it, and whether the schema matches',
    render: () => <DatabasePanel />,
  },
  {
    id: 'settings',
    title: 'Settings',
    blurb: 'Account, stack, running commit and every operational cap',
    render: () => <SettingsPanel />,
  },
]

/** `/health` plus whether the database answered. Needs no database itself. */
function ServicePanel({ hp, cov }) {
  return (
    <section className="card">
      <div className="row-between" style={{ marginBottom: 'var(--s3)' }}>
        <div className="row" style={{ gap: 8 }}>
          <IconHeart width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Service</span>
        </div>
        {hp.data
          ? <Badge tone="pass">{hp.data.status}</Badge>
          : <Badge tone="fail">unreachable</Badge>}
      </div>
      {hp.err && <Notice icon={<IconAlert />}>{hp.err}</Notice>}
      {hp.data && (
        <div className="grid g2">
          {/* `capabilities_loaded` REMOVED — and the comment lives INSIDE
              the div because `{cond && ( ... )}` takes ONE child, so a
              comment beside the element is a second one and the build
              refuses it.

              It counted the ratified twelve: the closed vocabulary feeding
              the legacy cell score, not the board's sections, which are
              discovered from the evidence and unbounded. On a health panel
              it read as "the board tracks 12 things", which is the one
              thing it does not mean. `/health` still returns the figure;
              nothing renders it as health. */}
          <Stat n={hp.data.environment} l="environment" />
          {/* ⚠ "no" ONLY WHEN THE DATABASE FAILED. A 401 is the sign-in
              expiring, and it read as "database readable: no" while the
              database answered fine (seen 2026-10-05). Loading is not "no"
              either. */}
          <Stat
            n={cov.data ? 'yes' : !cov.done ? '…' : (cov.status === 401 || cov.status === 403) ? 'not checked' : 'no'}
            l={cov.done && (cov.status === 401 || cov.status === 403)
              ? 'database — sign in again to check'
              : 'database readable'}
          />
        </div>
      )}
    </section>
  )
}

export default function Admin() {
  const hp = useSurface(health)
  const cov = useSurface(coveragePage)

  // THE SELECTION LIVES IN THE URL, not in useState. An operations page is
  // something people link each other to — "the board review is showing 40
  // unruled" is worth sending — and a refresh mid-incident should not drop you
  // back to the first tab. An unknown or absent `s` falls back to the first
  // section rather than rendering nothing.
  const [params, setParams] = useSearchParams()
  const wanted = params.get('s')
  const active = SECTIONS.find((x) => x.id === wanted) || SECTIONS[0]

  // A LINK TO A LOW SECTION OPENS WITH ITS NAV ITEM IN VIEW. The nav scrolls
  // inside its own pane, so `?s=settings` would otherwise select an item the
  // reader cannot see. `nearest` moves nothing when it is already visible.
  const nav = useRef(null)
  useEffect(() => {
    nav.current?.querySelector('[aria-current="page"]')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [active.id])

  return (
    <div className="shell section-tight stack stack-4 adm-page">
      <div className="stack stack-1">
        <span className="eyebrow">Operations</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Admin</h1>
        <p className="muted">Read straight off the backend. Nothing on this page is synthesised.</p>
      </div>

      <div className="adm">
        {/* A real <nav> with real <button>s: each is tabbable and reachable by
            a screen reader, and `aria-current` is what announces which one you
            are on. A div with an onClick would look identical and be none of
            those things. */}
        <nav className="adm-nav" aria-label="Operations sections" ref={nav}>
          {SECTIONS.map((sec) => [
            // A GROUP LABEL OPENS EACH RUN OF SECTIONS. It only names the
            // order above - it never moves a section.
            sec.group && <span key={`g-${sec.group}`} className="adm-nav-group" aria-hidden="true">{sec.group}</span>,
            <button
              key={sec.id}
              type="button"
              aria-current={sec.id === active.id ? 'page' : undefined}
              onClick={() => setParams(
                sec.id === SECTIONS[0].id ? {} : { s: sec.id },
                // REPLACE, NOT PUSH. Switching panels is not navigation a
                // reader wants to walk back through — Back should leave the
                // admin page, not step through four tabs they clicked.
                { replace: true },
              )}
            >
              <span className="t">
                {sec.title}
                {sec.wired === false && <span className="adm-nav-tag">not wired</span>}
              </span>
              <span className="d">{sec.blurb}</span>
            </button>,
          ])}
        </nav>

        {/* ONE SECTION MOUNTED AT A TIME, which is the point and also the cost.
            Each panel polls or fetches on mount, so switching away and back
            re-fetches — that is correct for an ops page (a stale reading is
            worse than a spinner) and it is why `UsagePanel`'s 15s poll no
            longer runs while you are reading the board review.

            `key` on the wrapper so React remounts rather than reconciling two
            different panels into one another's state. */}
        <div className="adm-body" key={active.id}>
          <Reveal>{active.render({ hp, cov })}</Reveal>
        </div>
      </div>
    </div>
  )
}
