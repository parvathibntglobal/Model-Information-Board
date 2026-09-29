/**
 * A readable name for an OpenRouter model id.
 *
 * SHARED BECAUSE TWO PANELS NAME THE SAME MODEL. This lived inside
 * `UsagePanel`, and Settings printed the raw id instead — so the same extractor
 * read as `DeepSeek V4 Flash` in one place and `deepseek/deepseek-v4-flash` in
 * another, on the same page.
 *
 * ⚠ THE BUILD NUMBER IS PART OF THE NAME. `deepseek/deepseek-v4-flash` is an
 *   undated alias (`judge/extract/client.py:38`), and the build it resolved to
 *   as of 2026-09-18 is 0423 — so the id alone does not say which model read the
 *   evidence, while `-0731` sitting in this same list does. Writing the number
 *   is what makes the two distinguishable on a page.
 *
 *   This is a LABEL, not a target. Nothing here changes which model is called:
 *   `EXTRACTOR_MODEL` is still `deepseek/deepseek-v4-flash`, and it has to be —
 *   there is no `-0423` id in the registry to point at, so the alias is the only
 *   route to that build.
 *
 * The raw id is always shown beside the label, so an unmapped id is readable
 * rather than hidden: anything unknown is title-cased from its slug.
 */
export const MODEL_NAMES = {
  'google/gemini-2.5-flash': 'Gemini 2.5 Flash',                 // previous extractor
  'deepseek/deepseek-v4-flash': 'DeepSeek V4 Flash 0423',        // current extractor
  'deepseek/deepseek-v4-flash:free': 'DeepSeek V4 Flash 0423 (free)',
  'deepseek/deepseek-v4-flash-0731': 'DeepSeek V4 Flash 0731',
}

export function prettyModel(id) {
  // ⚠ AN EMPTY ID IS A READING, NOT A MISSING LABEL. The ledger records the
  //   model the PROVIDER named, and records nothing when it named nobody —
  //   `judge/extract/client.py` used to copy the id we asked for into that
  //   gap, which made one column mean two things (#481 → #381).
  //
  //   So this arrives here, and it must not render as an empty cell beside
  //   real names: a blank reads as a layout fault and invites somebody to
  //   "fix" it by restoring the fallback.
  if (id == null || String(id).trim() === '') return 'provider named none'
  if (MODEL_NAMES[id]) return MODEL_NAMES[id]
  const slug = String(id).split('/').pop() || String(id)
  return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
