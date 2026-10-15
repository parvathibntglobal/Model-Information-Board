// Shared by the blog's live pages (judge/blog_live.py): addresses and words.
// Plain ESM, no JSX.

import { modelPagePath } from '../catalog/format'

/** Board section -> the word in a wall's address, and back. */
export const SECTION_PATH = { best_for: 'jobs', capability: 'capabilities' }
export const SECTION_OF = { jobs: 'best_for', capabilities: 'capability' }

const seg = (id) => String(id).split('/').map(encodeURIComponent).join('/')

/** One claim wall: one model on one job or capability. */
export const wallPath = (section, slug, modelId) =>
  `/blogs/disagree/${SECTION_PATH[section]}/${encodeURIComponent(slug)}/${seg(modelId)}`

/** A model's page: the catalogue's where it lists the model, the registry's otherwise. */
export const modelHref = (m) => (m.page === 'catalog' ? modelPagePath(m.id) : `/models/${seg(m.id)}`)

/** A job or capability on the board. */
export const topicHref = (section, slug) =>
  `/board/${section === 'best_for' ? 'jobs' : 'capabilities'}/${encodeURIComponent(slug)}`

/** "Anthropic: Claude Opus 5" -> "Claude Opus 5". */
export const shortName = (n) => String(n || '').split(':').slice(-1)[0].trim()

export const engineers = (n) => `${n} ${n === 1 ? 'engineer' : 'engineers'}`

/** "12 Oct 2026" from an ISO date. */
export const day = (iso) => (iso
  ? new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
  : '')
