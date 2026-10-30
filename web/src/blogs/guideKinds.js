/**
 * WHICH POSTS ARE GUIDES (2026-10-30, anooj). A guide is listed under Blogs ->
 * Guides ONLY: the blog index and the directory leave it out ("only under
 * Guides"), and its address stays /blogs/<slug>, so every link keeps working.
 *
 * One definition, read by the index (board/views.js vBlogs), the directory, the
 * Guides hub and the verified-facts box, so the four cannot disagree. Decided by
 * the post's plan key, which names its format: `migration-guide:<a>+<b>`.
 *
 * THREE MORE (Guides phase B, 2026-10-30): developer guides, tutorials and
 * error fixes, written from the providers' official sources
 * (generate_sample_blogs.py --guide-pack). Their code is copied from an
 * official source, not illustrative - views.js words the footer by it.
 */
export const OFFICIAL_GUIDE_FORMATS = ['developer-guide', 'tutorial', 'error-fix']

export const GUIDE_FORMATS = ['migration-guide', ...OFFICIAL_GUIDE_FORMATS]

/** The hub's tabs, by format. An error fix is listed with the developer guides, labelled. */
export const GUIDE_TABS = [
  { key: 'migration', label: 'Migration guides', formats: ['migration-guide'] },
  { key: 'developer', label: 'Developer guides', formats: ['developer-guide', 'error-fix'] },
  { key: 'tutorials', label: 'Tutorials', formats: ['tutorial'] },
]

/** What a card calls a post of each format. */
export const GUIDE_LABEL = {
  'migration-guide': 'Migration guide', 'developer-guide': 'Developer guide',
  'error-fix': 'Error fix', tutorial: 'Tutorial',
}

export const formatOf = (p) => String(p?.provenance?.plan_key || '').split(':')[0]

export const isGuide = (p) => GUIDE_FORMATS.includes(formatOf(p))

export const isMigrationGuide = (p) => formatOf(p) === 'migration-guide'

export const isOfficialGuide = (p) => OFFICIAL_GUIDE_FORMATS.includes(formatOf(p))

/** The tab a post is listed under, or null when it is not a guide. */
export const tabOf = (p) => (GUIDE_TABS.find((t) => t.formats.includes(formatOf(p))) || {}).key || null
