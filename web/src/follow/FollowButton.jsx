import { useFollowed } from './follow'

/** Follow / Following, for one model id. The list is this browser's (follow.js). */
export default function FollowButton({ id, name }) {
  const [, toggle, isFollowed] = useFollowed()
  const on = isFollowed(id)
  return (
    <button type="button" className={`btn ${on ? 'btn-ghost fl-on' : 'btn-ghost'}`} aria-pressed={on}
            onClick={() => toggle(id)}
            title={on ? `Stop following ${name || id}` : `Follow ${name || id}: it comes first on AI updates and the evidence feed, and this page tells you what is new since your last look`}>
      {on ? '✓ Following' : '+ Follow'}
    </button>
  )
}
