import { Badge } from '../components/ui'
import { fmtTokens } from '../api'
import { fmtUsd } from './cost'
import { ENCODING } from './tokenizer'

/** One cost cell. ≈ marks an estimate; "…" means not counted yet, never $0. */
export function Cost({ row, value, label, strong }) {
  const est = row.exactness !== 'exact'
  const shown = value == null ? '…' : `${est ? '≈ ' : ''}${fmtUsd(value)}`
  return (
    <span role="cell" data-label={label}
          className={`tnum${strong ? ' tc-strong' : ''}`}
          title={est ? 'Estimate: this model uses a different tokenizer' : `Exact: this model uses ${ENCODING}`}>
      {shown}
      {!est && value != null && <Badge tone="pass" style={{ marginLeft: 6 }}>exact</Badge>}
    </span>
  )
}

/**
 * Will it fit. Three states and a fourth for "not counted yet"; a model with
 * no published limit says so rather than reading as either answer (rule 6).
 * `fit` is fitOf()'s object, or a bare state string from the workload table.
 */
export function Fit({ fit, what = 'context window' }) {
  const state = typeof fit === 'string' ? fit : fit?.state
  let body
  let title
  if (!state) body = '…'
  else if (state === 'unknown') {
    body = <span className="dim">limit not published</span>
    title = `This model publishes no ${what}, so whether it fits is unknown`
  } else if (state === 'over') {
    body = <span className="tc-over">{fit.by != null ? `over by ${fmtTokens(fit.by)}` : 'too long'}</span>
    title = fit.limit != null ? `Its ${what} is ${fit.limit.toLocaleString('en-US')} tokens` : undefined
  } else {
    body = <span className="tc-fits">{fit.room != null ? `fits · ${fmtTokens(fit.room)} left` : 'fits'}</span>
    title = fit.limit != null ? `Its ${what} is ${fit.limit.toLocaleString('en-US')} tokens` : undefined
  }
  return <span role="cell" data-label="Fits?" title={title}>{body}</span>
}
