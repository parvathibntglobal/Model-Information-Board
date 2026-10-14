// WORKLOAD PERSONAS (2026-10-14): typical shapes of a month of model calls,
// for the token counter's monthly workload and a model page's cost estimate.
//
// ILLUSTRATIVE, NOT MEASURED. These numbers are starting points somebody edits
// - nobody counted them from a real system - and every place they appear says
// so. A figure with no population behind it is an estimate (CLAUDE.md, rule 7),
// so they are never shown as what a workload "costs", only as where to start.
//
// `cached` is the share of each call's input read from a prompt cache.
export const PERSONAS = [
  { key: 'helpdesk', name: 'Help-desk bot', scene: 'Short questions, short answers, all day long.',
    inTok: 900, outTok: 250, perDay: 8000, cached: 40 },
  { key: 'docs-qa', name: 'Docs answerer', scene: 'Retrieved passages in, a cited answer out.',
    inTok: 6000, outTok: 450, perDay: 2000, cached: 20 },
  { key: 'code-loop', name: 'Code agent loop', scene: 'A long repository context on every turn.',
    inTok: 30000, outTok: 2500, perDay: 600, cached: 70 },
  { key: 'form-reader', name: 'Form and invoice reader', scene: 'A scanned page in, structured fields out.',
    inTok: 3500, outTok: 600, perDay: 1500, cached: 10 },
  { key: 'tagger', name: 'Overnight tagger', scene: 'Tiny prompts, one-word labels, huge volume.',
    inTok: 400, outTok: 20, perDay: 50000, cached: 60 },
  { key: 'writer', name: 'Long-form writer', scene: 'A brief in, a long draft out.',
    inTok: 2000, outTok: 3000, perDay: 300, cached: 30 },
]

/** The persona whose numbers these are, or null for "your own numbers". */
export function personaOf({ inTok, outTok, perDay, cached }) {
  return PERSONAS.find((p) => p.inTok === inTok && p.outTok === outTok && p.perDay === perDay && p.cached === cached) || null
}
