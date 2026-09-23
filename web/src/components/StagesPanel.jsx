import { Fragment, useEffect, useState } from 'react'
import { adminStages } from '../api'
import { Badge, Notice } from './ui'
import { IconAlert, IconLayers } from './Icons'

/**
 * What happens at each stage of a fetch, in words.
 *
 * ⚠ NO COUNTS HERE, AND THAT IS THE POINT. The fetch log already carries the
 *   numbers, beside each stage, attached to the run they belong to. What it
 *   cannot carry is what a stage is FOR — "E4b · 1 thread(s) held back" is a
 *   figure and not an explanation, and a reader meeting the pipeline for the
 *   first time needs the second one.
 *
 * TWO SOURCES, KEPT APART. The LIST is parsed from `scripts/fetch_model.py`,
 * which is what emits the stages, so a new stage appears here the moment it is
 * added. The WORDS come from `contract/pipeline_stages.yaml`, reviewable in a
 * diff. A stage with no description renders as undescribed rather than being
 * dropped — the gap is the useful thing to show.
 */

// The E2* arms are one phase wearing seven ids. Grouped so the shape of a run
// reads as harvest → assemble → judge → extract → publish, rather than as a
// flat list of twenty-two in which the seven harvests dominate by count.
const PHASE = (id) => {
  if (id === '?' || id === 'DB' || id === 'STOP') return 'Around the run'
  if (id === 'E1') return 'Before anything is fetched'
  if (id.startsWith('E2')) return 'Harvest — one arm per platform'
  if (id.startsWith('E3')) return 'Assemble — turn documents into threads'
  if (id.startsWith('E4')) return 'Judge — before a token is spent'
  if (id.startsWith('E5')) return 'Extract — the only stage that costs money'
  return 'Publish — what the board renders'
}

/**
 * The gates a stage runs, named — never counted.
 *
 * ⚠ A GATE CAUSES AN ABSENCE, WHICH IS THE WHOLE REASON TO SHOW IT. Rule 4:
 *   a board that is thin because a gate fired and one that is thin because
 *   nobody reported anything render identically, and they are opposite
 *   statements. Naming the gates does not fix that by itself, but a reader who
 *   cannot find out a gate exists has no way to ask whether it fired.
 *
 * ⚠ A FLAG IS NOT A GATE, and it is drawn differently on purpose. `known-bot-
 *   counted` and `near-miss-not-registered` are recorded on documents that are
 *   KEPT — rule 8's one-way direction, a judgement measured on a population we
 *   chose ourselves, so it ships as a record and not as a drop. Showing the
 *   two in one list would say the pipeline throws away twice what it does.
 */
function Gates({ rows, note, source, sameAs }) {
  if (sameAs) {
    return (
      <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: '6px 0 0', lineHeight: 1.6 }}>
        {note} <span className="mono">({sameAs}</span>&#39;<span className="mono">s gates, run again)</span>
      </p>
    )
  }
  if (!rows?.length) return null
  const gates = rows.filter((g) => g.kind === 'gate')
  const flags = rows.filter((g) => g.kind === 'flag')
  return (
    <div className="stack stack-2" style={{ margin: '8px 0 0' }}>
      {note && (
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0, lineHeight: 1.6 }}>
          {note}
        </p>
      )}
      <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
        <span className="label">Gates here</span>
        <span className="dim" style={{ fontSize: 11 }}>
          {gates.length} refuse{gates.length === 1 ? 's' : ''} a row
          {flags.length > 0 && ` · ${flags.length} record only`}
        </span>
      </div>
      <ul className="stack stack-1" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {[...gates, ...flags].map((g) => (
          <li key={g.name} style={{
            borderLeft: `2px solid ${g.kind === 'flag' ? 'var(--border-soft)' : 'var(--text-3)'}`,
            paddingLeft: 10,
          }}>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
              <span className="mono" style={{ fontSize: 'var(--fs-xs)', color: 'var(--text)' }}>
                {g.name}
              </span>
              {g.kind === 'flag' && <Badge>recorded, not dropped</Badge>}
              {g.undescribed && <Badge tone="fail">not described</Badge>}
            </div>
            {g.drops && (
              <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '74ch', margin: '2px 0 0', lineHeight: 1.6 }}>
                {g.drops}
              </p>
            )}
          </li>
        ))}
      </ul>
      {source && (
        <span className="dim mono" style={{ fontSize: 11 }}>read from {source}</span>
      )}
    </div>
  )
}

export default function StagesPanel() {
  const [state, setState] = useState({ data: null, err: null })

  useEffect(() => {
    let alive = true
    adminStages()
      .then((d) => alive && setState({ data: d, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])

  const { data, err } = state
  const stages = data?.stages || []

  // Grouped in the order the backend returned, which is the order they run.
  // Not sorted: `E3d` runs before `E3b` and `E5c` before `E5b`, so any sort on
  // the id would show a sequence that never happens.
  const phases = []
  for (const s of stages) {
    const name = PHASE(s.id)
    const last = phases[phases.length - 1]
    if (last && last.name === name) last.items.push(s)
    else phases.push({ name, items: [s] })
  }

  return (
    <section className="card card-flush">
      <div className="card-head">
        <div className="row" style={{ gap: 8 }}>
          <IconLayers width={14} height={14} style={{ color: 'var(--text-3)' }} />
          <span className="label">Evidence stages — what each one does</span>
        </div>
        {data && <span className="label">{data.count} stage(s)</span>}
      </div>

      <div style={{ padding: '0 var(--s4)' }}>
        <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
          Every stage a fetch emits, in the order it runs them.{' '}
          <strong style={{ color: 'var(--text)' }}>No counts here on purpose</strong> —
          those are on the fetch log beside each stage, attached to the run they belong
          to. The list is read from the file that emits the stages, so a new one shows
          up here the moment it exists. Where a stage <strong style={{ color: 'var(--text)' }}>refuses
          something</strong>, the gates it runs are named under it — read from the
          modules that enforce them, not written out here.
        </p>
      </div>

      <div className="card-body stack stack-4">
        {err && <Notice icon={<IconAlert />}>{err}</Notice>}
        {!data && !err && <div className="skel" style={{ height: 220 }} />}

        {data?.contract_unreadable && (
          <Notice icon={<IconAlert />}>
            The stage descriptions could not be read, so every stage below shows as
            undescribed: {data.contract_unreadable}
          </Notice>
        )}

        {/* DRAWN AS A RAIL, because a pipeline is what this is. The previous
            shape was a stack of left-bordered blocks, which is the same markup
            the Sources and Keywords panels use for a SET - and a set is exactly
            what these are not. E2R runs after E2 and before E2A; the order is
            the content, so the page draws it.

            `what` reads at full strength and `why` beneath it dimmed: one is
            the stage and the other is the argument for it, and flattening them
            into two identical paragraphs is what made this hard to skim. */}
        {phases.map((phase) => (
          <div key={phase.name} className="stack stack-2">
            <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
              <span className="label">{phase.name}</span>
              <span className="dim" style={{ fontSize: 11 }}>
                {phase.items.length} stage{phase.items.length === 1 ? '' : 's'}
              </span>
            </div>
            <div className="rail">
              {phase.items.map((s, i) => (
                <Fragment key={s.id}>
                  <span className="rail-id">{s.id}</span>
                  <div className={`rail-body${i === phase.items.length - 1 ? ' last' : ''}`}>
                    <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                      <strong style={{ fontSize: 'var(--fs-sm)' }}>{s.name}</strong>
                      {s.undescribed && <Badge tone="fail">not described</Badge>}
                    </div>

                    {s.what && (
                      <p style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: '4px 0 0',
                                  color: 'var(--text)', lineHeight: 1.6 }}>
                        {s.what}
                      </p>
                    )}
                    {s.why && (
                      <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch',
                                                  margin: '4px 0 0', lineHeight: 1.6 }}>
                        {s.why}
                      </p>
                    )}

                    {/* A stage the code emits and the contract does not explain.
                        Shown as a gap rather than omitted: a reader who cannot
                        see it has no way to know the page is incomplete. */}
                    {s.undescribed && (
                      <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch',
                                                  margin: '4px 0 0' }}>
                        This stage runs and nobody has written down what it is for.
                        Add it to <span className="mono">contract/pipeline_stages.yaml</span>.
                      </p>
                    )}

                    <Gates
                      rows={s.gates}
                      note={s.gates_note}
                      source={s.gates_source}
                      sameAs={s.gates_same_as}
                    />
                  </div>
                </Fragment>
              ))}
            </div>
          </div>
        ))}

        {/* NOT A FETCH STAGE, so not in the rail. These run when somebody
            opens a page, over rows that are already stored — putting them in
            the sequence would say a run applies them, and a reader chasing a
            missing figure would look in the wrong place. */}
        {data?.after_the_run?.length > 0 && (
          <div className="stack stack-2">
            <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
              <span className="label">After the run — checked when a page is read</span>
              <span className="dim" style={{ fontSize: 11 }}>
                {data.after_the_run.length} gate(s)
              </span>
            </div>
            <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '78ch', margin: 0, lineHeight: 1.6 }}>
              These do not run during a fetch. They are asked of a stored row every
              time a page renders it, so a figure held back here is{' '}
              <strong style={{ color: 'var(--text)' }}>untouched in the database</strong>{' '}
              and comes back the moment its unit or its axis is corrected.
            </p>
            <Gates rows={data.after_the_run} source="judge/store/board_entries.py:metric_withholding" />
          </div>
        )}

        {data?.gates_unreadable?.length > 0 && (
          <Notice icon={<IconAlert />}>
            These gate lists could not be read, so the stages above understate what
            the pipeline refuses: {data.gates_unreadable.join(' · ')}
          </Notice>
        )}

        {/* DRIFT THE OTHER WAY. A description for a stage nothing emits would
            otherwise read as part of the pipeline. */}
        {data?.described_but_not_emitted?.length > 0 && (
          <Notice icon={<IconAlert />}>
            Described but never emitted, so nothing runs them:{' '}
            {data.described_but_not_emitted.join(', ')}
          </Notice>
        )}

        {data && (
          <span className="dim mono" style={{ fontSize: 11 }}>
            list: {data.source_of_list} · words: {data.source_of_words}
          </span>
        )}
      </div>
    </section>
  )
}
