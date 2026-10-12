/**
 * Where a model's page is. The models list links `/models/{model_version_id}`,
 * so the counter and the spec finder do the same rather than a second form.
 */
export const modelHref = (mvId) => `/models/${encodeURIComponent(mvId)}`
