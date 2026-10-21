import { useEffect, useRef, useState } from 'react'
import { loadEmbeds } from '../board/embeds'

/**
 * THE EVIDENCE FEED'S PARTS (2026-10-21, PROPOSED): when a report was posted,
 * how it was filed, and where it came from. Shared by the feed page and
 * Admin -> Feed summaries, so a reviewer sees each cited report exactly as a
 * reader will.
 *
 * NO QUOTE IS EVER RENDERED HERE. The payload carries none (judge/feed/items.py)
 * and nothing in this file would show one if it did: a report is our
 * paraphrase, and its source is a link or the platform's own embed.
 */

const UNITS = [
  ['y', 365 * 24 * 3600],
  ['mo', 30 * 24 * 3600],
  ['w', 7 * 24 * 3600],
  ['d', 24 * 3600],
  ['h', 3600],
  ['m', 60],
]

/** "5h ago", "1d ago", "3w ago". A future time (clock skew) reads "just now". */
export function relTime(iso, now = Date.now()) {
  const s = Math.floor((now - new Date(iso).getTime()) / 1000)
  if (!Number.isFinite(s) || s < 60) return 'just now'
  for (const [u, n] of UNITS) if (s >= n) return `${Math.floor(s / n)}${u} ago`
  return 'just now'
}

const exact = (iso) => new Date(iso).toLocaleString('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC', timeZoneName: 'short',
})

/**
 * WHEN IT WAS POSTED - by its author, not when we collected it. A report with
 * no recorded date says so; it never borrows one (rule 6).
 */
export function Posted({ at }) {
  if (!at) return <span className="ev-when ev-dim">date not recorded</span>
  return <time className="ev-when" dateTime={at} title={`Posted ${exact(at)}`}>{relTime(at)}</time>
}

// THE WORD, NOT JUST THE COLOUR: red/green is the pair most readers lose.
// `both` is a report that said it worked and that it failed: "mixed".
const POL = {
  positive: ['positive', 'pass'],
  negative: ['negative', 'fail'],
  both: ['mixed', 'warn'],
  neutral: ['neutral', 'mute'],
}

export function PolarityChip({ polarity }) {
  const [word, tone] = POL[polarity] || ['unlabelled', 'mute']
  return <span className={`badge badge-${tone}`}>{word}</span>
}

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

/**
 * The platform's own markup, rebuilt from the fields we stored and only for a
 * URL of the expected shape - anything else draws nothing. The same rules as
 * the blog's `embedBlock` (web/src/board/views.js); its script turns the
 * blockquote into the post, with its author and date.
 */
function embedMarkup(s) {
  if (s.platform === 'reddit') {
    const u = String(s.url || '')
    const m = u.match(/^https:\/\/www\.reddit\.com\/r\/(\w+)\/comments\/\w+/)
    if (!m) return ''
    const author = /^[\w-]{1,40}$/.test(s.author || '') ? s.author : ''
    return `<blockquote class="reddit-embed-bq" style="height:316px"><a href="${esc(u)}">${esc(s.title || 'View this post on Reddit')}</a><br> by `
      + (author ? `<a href="https://www.reddit.com/user/${esc(author)}/">u/${esc(author)}</a>` : 'a Reddit user')
      + ` in <a href="https://www.reddit.com/r/${esc(m[1])}/">${esc(m[1])}</a></blockquote>`
  }
  if (s.platform === 'x') {
    const m = String(s.url || '').match(/^https:\/\/(?:x|twitter)\.com\/(\w+)\/status\/(\d+)/)
    if (!m) return ''
    return `<blockquote class="twitter-tweet" data-theme="dark" data-dnt="true"><a href="https://twitter.com/${esc(m[1])}/status/${esc(m[2])}">View this post on X</a></blockquote>`
  }
  return ''
}

/** Loaded only when asked: an embed fetches the platform's script and the post. */
function Embed({ source }) {
  const ref = useRef(null)
  const markup = embedMarkup(source)
  useEffect(() => { if (ref.current && markup) loadEmbeds(ref.current) }, [markup])
  if (!markup) return <span className="ev-dim">The original post can&apos;t be embedded.</span>
  // eslint-disable-next-line react/no-danger -- built above from validated fields, every value escaped
  return <div ref={ref} className="ev-embed" dangerouslySetInnerHTML={{ __html: markup }} />
}

const PLATFORM_NAME = { reddit: 'Reddit', x: 'X' }

/** Where the report came from, below its text. */
export function SourceLine({ source }) {
  const [open, setOpen] = useState(false)
  if (!source) return null
  if (source.kind === 'link') {
    return (
      <div className="ev-source">
        <a href={source.url} target="_blank" rel="noopener noreferrer">{source.platform} ↗</a>
        {source.acknowledgement && <span className="ev-ack">{source.acknowledgement}</span>}
      </div>
    )
  }
  if (source.kind === 'embed') {
    const name = PLATFORM_NAME[source.platform] || source.platform
    return (
      <div className="ev-source">
        {open
          ? <Embed source={source} />
          : <button type="button" className="btn btn-ghost ev-show" onClick={() => setOpen(true)}>Show the original post on {name}</button>}
      </div>
    )
  }
  if (source.kind === 'pending') {
    return <div className="ev-source ev-dim">{source.platform}: original post not resolved yet</div>
  }
  if (source.kind === 'unavailable') {
    return (
      <div className="ev-source ev-dim">
        {source.platform}: {source.reason === 'no_link'
          ? 'no link recorded'
          : "the original post can't be embedded (deleted, removed or a link post)"}
      </div>
    )
  }
  if (source.kind === 'withheld') return <div className="ev-source ev-dim">From a source this feed does not show</div>
  return null
}

/** One report: when, how it was filed, our paraphrase, its source. */
export function Report({ item, id }) {
  return (
    <article className="ev-item" id={id}>
      <div className="ev-meta">
        <Posted at={item.posted_at} />
        <PolarityChip polarity={item.polarity} />
        {(item.tags || []).map((t) => (
          <span key={`${t.section}:${t.slug}`} className="ev-tag">{t.name || t.slug}</span>
        ))}
      </div>
      {item.paraphrase
        ? <p className="ev-text">{item.paraphrase}</p>
        : <p className="ev-text ev-dim">Not paraphrased yet. The source is below.</p>}
      <SourceLine source={item.source} />
    </article>
  )
}
