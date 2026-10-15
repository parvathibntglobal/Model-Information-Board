// Shared formatting for the Models pages (catalogue list and model page).

/** A list price per 1M tokens. A published zero is "$0", never "$0.000". */
export const fmtUsd = (n) => (n === 0 ? '$0' : n >= 100 ? `$${n.toFixed(0)}` : n >= 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(3)}`)
export const fmtCtx = (n) => (n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}K` : String(n))
export const fmtDate = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

/** The address of one model's page. Each id segment is encoded; the slash between them is kept. */
export const modelPagePath = (id) => `/catalog/model/${id.split('/').map(encodeURIComponent).join('/')}`
/** Her reports page for a model (judge/reports.py): every job, capability and metric, counted. */
export const reportsPath = (id) => `/reports/models/${id.split('/').map(encodeURIComponent).join('/')}`
