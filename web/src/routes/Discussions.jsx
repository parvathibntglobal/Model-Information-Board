import { Link } from 'react-router-dom'
import { useHead } from '../seo/head'
import { discussionsIndex } from '../seo/pages'

/**
 * DISCUSSIONS (2026-10-14): readers' own experiences with AI models, jobs,
 * capabilities and metrics - shown beside the reports and NEVER added to the
 * counts. THE PAGE IS A PLACEHOLDER: there is no comment store yet, so it
 * offers no form that would lose what someone typed. It asks not to be
 * indexed until it has content.
 */
export default function Discussions() {
  useHead(discussionsIndex())
  return (
    <div className="shell section-tight stack stack-4">
      <div className="stack stack-1">
        <span className="go-badge go-blogs page-tag" style={{ alignSelf: 'flex-start' }}>Discussions</span>
        <h1 style={{ fontSize: 'var(--fs-display)' }}>From readers</h1>
        <p className="muted" style={{ maxWidth: '72ch', margin: 0 }}>
          Readers' own experiences with AI models, jobs, capabilities and metrics. Shown beside the
          reports and never added to the counts.
        </p>
      </div>
      <div className="card stack stack-2">
        <p style={{ margin: 0 }}><strong>This page is being built.</strong></p>
        <p style={{ fontSize: 'var(--fs-sm)', margin: 0, lineHeight: 1.6 }}>
          Comments are not open yet. Until they are, what engineers reported is on the{' '}
          <Link to="/reports">Reports</Link> page.
        </p>
      </div>
    </div>
  )
}
