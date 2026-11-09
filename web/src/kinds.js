/**
 * The tracked kinds (contract/tracked_models.yaml `kind`), named once for every
 * page that shows them - the Models page's Type filter and badges, and Admin.
 *
 * BUILT FROM THE KINDS PRESENT, NOT A FIXED LIST (#612 review, point 12). A
 * fixed list gave a kind it did not know - `agent`, when the agents are seated -
 * no label, no chip and no filter, and "All N" stopped being the sum of the
 * chips. A known kind keeps its place and name; any other kind follows, named
 * from itself.
 */
const ORDER = ['text', 'image', 'video', 'speech', 'transcription', 'decision']
const NAMES = {
  text: 'Text', image: 'Image', video: 'Video', speech: 'Speech',
  transcription: 'Transcription', decision: 'Decision',
}

const nameOf = (kind) => NAMES[kind] || (kind.charAt(0).toUpperCase() + kind.slice(1))

/** `[[kind, chip label], ...]` for every kind with at least one model. */
export function kindChips(counts) {
  const present = Object.keys(counts || {}).filter((k) => k && k !== 'undefined' && counts[k])
  const known = ORDER.filter((k) => present.includes(k))
  const other = present.filter((k) => !ORDER.includes(k)).sort()
  return [...known, ...other].map((k) => [k, nameOf(k)])
}

/** "Image model" for a non-text kind; '' for text, which needs no badge. */
export function kindLabel(kind) {
  return kind && kind !== 'text' ? `${nameOf(kind)} model` : ''
}
