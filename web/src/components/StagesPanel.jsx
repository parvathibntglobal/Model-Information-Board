import { useEffect, useState } from 'react'
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
          <strong style={{ color: 'var(--text-1)' }}>No counts here on purpose</strong> —
          those are on the fetch log beside each stage, attached to the run they belong
          to. The list is read from the file that emits the stages, so a new one shows
          up here the moment it exists.
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

        {phases.map((phase) => (
          <div key={phase.name} className="stack stack-2">
            <span className="label">{phase.name}</span>
            {phase.items.map((s) => (
              <div key={s.id} className="stack stack-1"
                   style={{ borderLeft: '2px solid var(--line)', paddingLeft: 12 }}>
                <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                  <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{s.id}</span>
                  <strong style={{ fontSize: 'var(--fs-sm)' }}>{s.name}</strong>
                  {s.undescribed && <Badge tone="fail">not described</Badge>}
                </div>

                {s.what && (
                  <p style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0,
                              color: 'var(--text-1)', lineHeight: 1.6 }}>
                    {s.what}
                  </p>
                )}
                {s.why && (
                  <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch',
                                              margin: 0, lineHeight: 1.6 }}>
                    {s.why}
                  </p>
                )}

                {/* A stage the code emits and the contract does not explain.
                    Shown as a gap rather than omitted: a reader who cannot see
                    it has no way to know the page is incomplete. */}
                {s.undescribed && (
                  <p className="dim" style={{ fontSize: 'var(--fs-xs)', maxWidth: '76ch', margin: 0 }}>
                    This stage runs and nobody has written down what it is for.
                    Add it to <span className="mono">contract/pipeline_stages.yaml</span>.
                  </p>
                )}
              </div>
            ))}
          </div>
        ))}

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
