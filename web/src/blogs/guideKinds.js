/**
 * WHICH POSTS ARE GUIDES (2026-10-30, anooj). A guide is listed under Blogs ->
 * Guides ONLY: the blog index and the directory leave it out ("only under
 * Guides"), and its address stays /blogs/<slug>, so every link keeps working.
 *
 * One definition, read by the index (board/views.js vBlogs), the directory, the
 * Guides hub and the verified-facts box, so the four cannot disagree. Decided by
 * the post's plan key, which names its format: `migration-guide:<a>+<b>`.
 */
export const GUIDE_FORMATS = ['migration-guide']

export const formatOf = (p) => String(p?.provenance?.plan_key || '').split(':')[0]

export const isGuide = (p) => GUIDE_FORMATS.includes(formatOf(p))

export const isMigrationGuide = (p) => formatOf(p) === 'migration-guide'
