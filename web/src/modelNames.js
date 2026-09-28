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
  if (MODEL_NAMES[id]) return MODEL_NAMES[id]
  const slug = String(id).split('/').pop() || String(id)
  return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
