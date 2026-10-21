/**
 * The platform a quote's link goes to, named from the link itself.
 *
 * "open the source" after every quote said nothing about WHERE the source was.
 * The host of the URL does, and it is read off the URL rather than looked up
 * or guessed: a host this map does not know is shown as itself
 * ("example.com"), never as a platform it might be.
 */
const HOSTS = {
  'reddit.com': 'Reddit',
  'news.ycombinator.com': 'Hacker News',
  'github.com': 'GitHub',
  'dev.to': 'dev.to',
  'arxiv.org': 'arXiv',
  'x.com': 'X',
  'twitter.com': 'X',
  'huggingface.co': 'Hugging Face',
  'redd.it': 'Reddit',          // Reddit's own short and media host (i.redd.it)
}

export function sourceName(href) {
  let host
  try {
    host = new URL(href).hostname.toLowerCase()
  } catch {
    return 'source'
  }
  // A subdomain of a known host is that host (i.redd.it, old.reddit.com,
  // gist.github.com); anything else is shown as itself.
  for (const [known, name] of Object.entries(HOSTS)) {
    if (host === known || host.endsWith(`.${known}`)) return name
  }
  return host.replace(/^www\./, '')
}
