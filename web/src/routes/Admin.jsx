import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { health, coveragePage, listModels, BoardUnreadable } from '../api'
import { Badge, Notice, Reveal, Stat } from '../components/ui'
import UsagePanel from '../components/UsagePanel'
import BoardReview from '../components/BoardReview'
import KeywordsPanel from '../components/KeywordsPanel'
import PromptsPanel from '../components/PromptsPanel'
import SourcesPanel from '../components/SourcesPanel'
import StagesPanel from '../components/StagesPanel'
import RunsPanel from '../components/RunsPanel'
import DatabasePanel from '../components/DatabasePanel'
import SettingsPanel from '../components/SettingsPanel'
import FetchPanel from '../components/FetchPanel'
import ModelProposal from '../components/ModelProposal'
import { IconAlert, IconGauge } from '../components/Icons'

/**
 * Operations. `/health` needs nothing; the database-backed surfaces are each
 * allowed to be unreadable on their own, so one missing page does not blank the
 * others.
 */
function useSurface(fn, deps = []) {
  const [state, setState] = useState({ data: null, err: null, unreadable: null })
  useEffect(() => {
    let alive = true
    fn()
      .then((d) => alive && setState({ data: d, err: null, unreadable: null }))
      .catch((e) => alive && setState({
        data: null,
        err: e instanceof BoardUnreadable ? null : e.message,
        unreadable: e instanceof BoardUnreadable ? e.message : null,
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

  return (
    <div className="stack stack-3">
      <div className="stack stack-1">
        <span className="label">Collect evidence — sweep a model on demand</span>
        <span className="dim" style={{ fontSize: 'var(--fs-xs)' }}>
          Each fetch runs a fresh harvest through the evidence pipeline and appends new rows.
          The fetch log and every past run are kept per model.
        </span>
      </div>
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
        <details key={m.model_version_id} className="disc">
          <summary>
            {m.display_name || m.model_version_id}
            <span className="n">{m.model_version_id}</span>
            {m.provider && <Badge tone="mute">{m.provider}</Badge>}
          </summary>
          <div className="disc-body">
            <FetchPanel modelVersionId={m.model_version_id} />
          </div>
        </details>
      ))}

    </div>
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
  {
    id: 'service',
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
    id: 'models',
    title: 'Models',
    blurb: 'Sweep a model on demand, add one, or stop tracking one',
    render: () => <CollectEvidence />,
  },
  {
    id: 'board',
    title: 'Board sections',
    blurb: 'Discovered by the classifier, and already live',
    render: () => <BoardReview />,
  },
  {
    id: 'pipeline',
    title: 'Evidence stages',
    blurb: 'What each stage of a fetch actually does',
    render: () => <StagesPanel />,
  },
  {
    id: 'prompts',
    title: 'Prompts',
    blurb: 'Every prompt we send a model, composed not copied',
    render: () => <PromptsPanel />,
  },
  // APPENDED RATHER THAN SLOTTED IN BESIDE `models`, WHERE `runs` BELONGS BY
  // SUBJECT. Keywords was asked for in fourth place and Evidence stages in
  // seventh, and both are counted from the top of this list — so inserting a
  // section above them would quietly move the two that were positioned on
  // purpose.
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
          <IconGauge width={14} height={14} style={{ color: 'var(--text-3)' }} />
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
          <Stat n={cov.data ? 'yes' : 'no'} l="database readable" />
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

  return (
    <div className="shell section-tight stack stack-4 adm-page">
      <div className="stack stack-1">
        <span className="eyebrow">Operations</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>Pipeline health</h1>
        <p className="muted">Read straight off the backend. Nothing on this page is synthesised.</p>
      </div>

      <div className="adm">
        {/* A real <nav> with real <button>s: each is tabbable and reachable by
            a screen reader, and `aria-current` is what announces which one you
            are on. A div with an onClick would look identical and be none of
            those things. */}
        <nav className="adm-nav" aria-label="Operations sections">
          {SECTIONS.map((sec) => (
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
              <span className="t">{sec.title}</span>
              <span className="d">{sec.blurb}</span>
            </button>
          ))}
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
