/**
 * PER-PAGE <head> TEXT: what each route says its title and description are.
 *
 * Pure functions, no DOM - `useHead` (./head.js) applies what these return.
 * Item 1 of the SEO plan (2026-10-08): the whole site shared one <title> and
 * one description, so every model, job, capability and metric page looked the
 * same to a search engine and to a browser tab. Nothing here makes the site
 * indexable - `index.html`'s `noindex, nofollow` still governs every page, and
 * a page can only make robots STRICTER (see head.js).
 *
 * WHAT A DESCRIPTION MAY SAY. Names and the section's own definition, never a
 * count: a number in a description is cached by whoever reads it and goes
 * stale with nothing on the page to correct it (rule 11). And never a
 * platform name - descriptions are for the public view, which withholds some
 * sources entirely (`contract/publication.yaml`); a definition that names one
 * is dropped for the template sentence rather than published.
 */

export const SITE = 'Model Information Board'
/** Search engines show about 60 characters of a title, ~155 of a description. */
export const TITLE_MAX = 60
export const DESCRIPTION_MAX = 155

const PLATFORM = /\b(reddit|subreddit|twitter|tweets?|x\.com|arxiv|hacker ?news|hn|dev\.to|hugging ?face|github)\b/i

/** `Name | Model Information Board`; the name alone when both would not fit;
 *  the name clipped when even it is too long. */
export function fullTitle(name) {
  if (!name) return null
  const clean = squash(name)
  const both = `${clean} | ${SITE}`
  return both.length <= TITLE_MAX ? both : clip(clean, TITLE_MAX)
}

/** One line, whitespace collapsed, cut at a word boundary with an ellipsis. */
export function clip(text, max = DESCRIPTION_MAX) {
  const t = squash(text)
  if (t.length <= max) return t
  const cut = t.slice(0, max - 1)
  const at = cut.lastIndexOf(' ')
  return `${(at > max * 0.6 ? cut.slice(0, at) : cut).replace(/[,;:\s]+$/, '')}…`
}

function squash(s) {
  return String(s ?? '').replace(/\s+/g, ' ').trim()
}

/** A definition sentence, unless it is empty or names a platform. */
function usable(definition) {
  const d = squash(definition)
  return d && !PLATFORM.test(d) ? d : ''
}

function withDefinition(lead, definition) {
  const d = usable(definition)
  return clip(d ? `${lead} ${d.endsWith('.') ? d : `${d}.`}` : lead)
}

/* ── the pages ─────────────────────────────────────────────────────────── */

const BOARD_TABS = {
  best: ['AI models by job', 'Which AI models engineers report working for each job, from coding agents to code review, in their own words.'],
  cap: ['AI models by capability', 'How AI models behave on each capability, as engineers report it in production, in their own words.'],
  met: ['AI model metrics', 'Figures engineers report for AI models, such as cost per token and latency, each with the quote it came from.'],
}

/** `/board?tab=` */
export function boardHub(tab) {
  const [title, description] = BOARD_TABS[tab] || BOARD_TABS.best
  return { title: fullTitle(title), description, canonical: tab && tab !== 'best' ? `/board?tab=${tab}` : '/board' }
}

// Breadcrumbs (SEO item 6): the board, then the tab a section lives on.
const BOARD_CRUMB = { name: 'Board', path: '/board' }

const SECTION = {
  jobs: { path: 'jobs', tab: { name: 'Jobs', path: '/board' }, title: (n) => `Best AI models for ${n}`, lead: (n) => `Which AI models engineers report working for ${n}.` },
  capabilities: { path: 'capabilities', tab: { name: 'Capabilities', path: '/board?tab=cap' }, title: (n) => `${n}: how AI models compare`, lead: (n) => `How AI models handle ${n}, as engineers report it.` },
  metrics: { path: 'metrics', tab: { name: 'Metrics', path: '/board?tab=met' }, title: (n) => `${n} by AI model`, lead: (n) => `${n} figures engineers report for AI models, each with its quote.` },
}

/** `/board/{jobs|capabilities|metrics}/:slug`, from the section's own row. */
export function boardSection(seg, item) {
  const s = SECTION[seg]
  if (!s || !item) return null
  const canonical = `/board/${s.path}/${item.slug}`
  return {
    title: fullTitle(s.title(item.name)),
    description: withDefinition(s.lead(item.name), item.card),
    canonical,
    modified: item.freshUpdated || null,
    breadcrumbs: [BOARD_CRUMB, s.tab, { name: squash(item.name), path: canonical }],
  }
}

/** `/board/{seg}/:slug/:model` - one model's reports in one section. */
export function boardModelInSection(seg, item, modelKey, modelName, modified = null) {
  const s = SECTION[seg]
  if (!s || !item || !modelKey) return null
  const m = squash(modelName || modelKey)
  const title = seg === 'jobs' ? `${m} for ${item.name}` : `${m}: ${item.name}`
  const section = `/board/${s.path}/${item.slug}`
  const canonical = `${section}/${modelKey}`
  return {
    title: fullTitle(title),
    description: clip(`What engineers report about ${m} on ${item.name}, quoted exactly as they wrote it.`),
    canonical,
    modified,
    breadcrumbs: [BOARD_CRUMB, s.tab, { name: squash(item.name), path: section }, { name: m, path: canonical }],
  }
}

export function modelsIndex() {
  return {
    title: fullTitle('AI models compared'),
    description: 'Every AI model the board tracks, with what engineers report about each one in production and its list price per token.',
    canonical: '/models',
  }
}

/** `/models/*`. `id` is the route key as the URL carries it. */
export function modelPage(id, name, modified = null) {
  const m = squash(name || id)
  return {
    title: fullTitle(`${m}: what engineers report`),
    description: clip(`What engineers report about ${m} in production: the jobs it works for, its capabilities and the figures they measured, in their own words.`),
    canonical: `/models/${id}`,
    modified,
    breadcrumbs: [{ name: 'Models', path: '/models' }, { name: m, path: `/models/${id}` }],
  }
}

/** `/compare?ids=`. The canonical sorts the ids, so A-vs-B and B-vs-A are one page. */
export function comparePage(ids, names) {
  const list = (names && names.length ? names : ids).map(squash).filter(Boolean)
  if (list.length < 2) {
    return { title: fullTitle('Compare AI models'), description: 'Put two or three AI models side by side on what engineers report about each.', canonical: '/compare' }
  }
  return {
    title: fullTitle(list.join(' vs ')),
    description: clip(`${list.join(' vs ')}: what engineers report about each, side by side, by the jobs, capabilities and metrics they share.`),
    canonical: `/compare?ids=${[...ids].sort().join(',')}`,
  }
}

/**
 * `/token-counter` and `/model-finder` (#520). Neither is on
 * contract/indexing.yaml's `always` list, so both are noindex like every
 * unlisted page until somebody adds them there. A HEAD OF THEIR OWN MATTERS
 * EVEN SO: a page with no head keeps index.html's robots, which the open build
 * flips to `index, follow`, so a headless page would be the one route the
 * indexing rule could not reach.
 */
export function tokenCounter() {
  return {
    title: fullTitle('LLM token counter and cost calculator'),
    description: 'Count the tokens in a prompt or an answer in your browser, then see what that text costs to send or generate on each AI model at its list price.',
    canonical: '/token-counter',
    breadcrumbs: [{ name: 'Models', path: '/models' }, { name: 'Token counter', path: '/token-counter' }],
  }
}

export function modelFinder() {
  return {
    title: fullTitle('Find an AI model by spec'),
    description: 'Filter AI models by what each provider advertises: tool calling, vision, structured output, prompt caching, context window and price per token.',
    canonical: '/model-finder',
    breadcrumbs: [{ name: 'Models', path: '/models' }, { name: 'Spec finder', path: '/model-finder' }],
  }
}

/**
 * THE DEMO'S SECTIONS (2026-10-14). Tools gathers pages that already exist.
 * Reports and Discussions are being built: until they hold content they ask
 * not to be indexed, so an empty page never reaches a search result.
 */
/** `/model-picker`: the best model for a job, and cheaper alternatives (2026-10-14). */
export function modelPicker() {
  return {
    title: fullTitle('Best AI model picker: the best model for the job, or a cheaper alternative'),
    description: 'Find the best AI model for your job, or a cheaper alternative to the one you use, from what engineers reported working - beside what each model costs.',
    canonical: '/model-picker',
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'Best AI model picker', path: '/model-picker' }],
  }
}

/** `/catalog` and `/catalog/new`: every model OpenRouter lists. `type` is a
 *  model type key (`image`), `'new'` for New releases, or null for All models. */
const CATALOG_TYPE_NAMES = { text: 'Text', image: 'Image', video: 'Video', speech: 'Speech', audio: 'Audio', transcription: 'Transcription', decisions: 'Decision' }
export function catalogIndex(type = null) {
  if (type === 'new') {
    return { title: fullTitle('New AI model releases'), description: 'The AI models listed most recently, newest first, with their prices, context and type.', canonical: '/catalog/new' }
  }
  if (type && CATALOG_TYPE_NAMES[type]) {
    const n = CATALOG_TYPE_NAMES[type]
    return { title: fullTitle(`${n} AI models by provider`), description: `Every ${n.toLowerCase()} AI model, by provider, with list prices and context.`, canonical: `/catalog?type=${type}` }
  }
  return { title: fullTitle('All AI models by provider and type'), description: 'Every AI model, from every provider: text, image, video, speech, audio, transcription and decision models.', canonical: '/catalog' }
}

/** One model's page in the catalogue (`/catalog/model/<id>`). */
export function catalogModelHead(m) {
  const who = m.provider_name ? `${m.provider_name} ${m.name}` : m.name
  return {
    title: fullTitle(`${who}: price, specs and what engineers report`),
    description: `${who}: list price per million tokens, what a workload would cost, context and features, and what engineers report about it.`,
    canonical: `/catalog/model/${m.id}`,
  }
}

export function toolsIndex() {
  return {
    title: fullTitle('AI model tools: model picker, specs and token counter'),
    description: 'Find which AI models engineers reported working for your job, what each model advertises, and what your prompt would cost on each one.',
    canonical: '/tools',
  }
}

/**
 * `/reports` and each of its pages: the hub, a section (`/reports/jobs`) or one
 * item in it (`/reports/jobs/coding-agent`). `item.name` is null until the data
 * has loaded, and the title then names the section alone.
 */
export function reportsIndex(section = null, item = null) {
  if (!section) {
    return {
      title: fullTitle('Models: what engineers report about each AI model'),
      description: 'What engineers report about each AI model, by job, capability and metric: counted, and shown only where at least five different people reported.',
      canonical: '/reports',
    }
  }
  const base = `/reports/${section.key}`
  if (item && item.name) {
    return {
      title: fullTitle(`${item.name}: what engineers report`),
      description: clip(`What engineers report about ${item.name}, counted by positive, negative and neutral reports, never quoted.`),
      canonical: `${base}/${item.path}`,
      breadcrumbs: [{ name: 'AI models', path: '/reports' }, { name: item.name, path: `${base}/${item.path}` }],
    }
  }
  return {
    title: fullTitle(section.key === 'models' ? 'Models: what engineers report about each AI model' : `${section.title}: what engineers report`),
    description: clip(section.lede),
    // /reports/models IS /reports - the hub opens on the Models section - so both
    // name one canonical and search engines see one page, not two (2026-10-20).
    canonical: section.key === 'models' ? '/reports' : base,
    breadcrumbs: [{ name: 'AI models', path: '/reports' }, ...(section.key === 'models' ? [] : [{ name: section.title, path: base }])],
  }
}

/**
 * `/discussions` (2026-10-20): readers' own experience with AI models, by
 * topic. INDEXABLE NOW - the page carries its topics and their copy whether or
 * not any post has been approved yet, so it is never an empty result. Measured
 * keywords only (contract/discussions.yaml names them per topic).
 */
export function discussionsIndex() {
  return {
    title: fullTitle('AI model discussions: LLM comparison from real work'),
    description: 'Discuss AI models with engineers: the best LLM for coding, AI agents, RAG, local and open source LLMs, API pricing and Claude vs Gemini - from real work.',
    canonical: '/discussions',
    breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Discussions', path: '/discussions' }],
  }
}

export function blogIndex() {
  return {
    title: fullTitle('Notes on AI models'),
    description: 'Long-form notes on AI models, written from what engineers report in production.',
    canonical: '/blogs',
  }
}

/** The blog's live pages (2026-10-15), built in code from public reports. */
export function liveDisagree() {
  return {
    title: fullTitle('Where engineers disagree about AI models'),
    description: 'Every model and topic where some engineers report it working and others report problems, with both counts and every quote.',
    canonical: '/blogs/disagree',
  }
}

export function liveWall(w, path) {
  if (!w) return liveDisagree()
  const name = String(w.model.name || '').split(':').slice(-1)[0].trim()
  return {
    title: fullTitle(`${name} on ${w.topic}: what engineers report`),
    description: `${w.working} engineers report ${name} working on ${w.topic.toLowerCase()} and ${w.problems} report problems. Every quote, linked to its source.`,
    canonical: path,
  }
}

export function liveWeek(start) {
  return {
    title: fullTitle(start ? `This week in AI models: week of ${start}` : 'This week in AI models'),
    description: 'New models listed, what engineers wrote, price changes and retirement dates, week by week.',
    canonical: start ? `/blogs/this-week/${start}` : '/blogs/this-week',
  }
}

export function liveQuiz() {
  return {
    title: fullTitle('Daily LLM quiz'),
    description: 'Five questions a day on how large language models work - tokens, attention, fine-tuning, retrieval and cost.',
    canonical: '/blogs/quiz',
  }
}

/**
 * THE AI GLOSSARY (2026-10-20): `/glossary` and `/glossary/<slug>`. A term's
 * title is the keyword plan's definition shape (seo/keyword_plan.yaml,
 * `definition`): "What is {concept}? Meaning and example".
 */
export function aiGlossaryHead() {
  return {
    title: fullTitle('Glossary: LLM and AI terms, defined in a paragraph'),
    description: 'Plain definitions of the terms you meet when choosing, prompting and running AI models, from tokens and context windows to agents, RAG and quantization.',
    canonical: '/glossary',
    breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Glossary', path: '/glossary' }],
  }
}
export function aiGlossaryTermHead(t) {
  if (!t) return aiGlossaryHead()
  const path = `/glossary/${t.slug}`
  return {
    title: fullTitle(`What is ${t.term}? Meaning and example`),
    description: clip(t.teaser),
    canonical: path,
    breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Glossary', path: '/glossary' }, { name: t.term, path }],
    definedTerm: { name: t.term, description: t.definition, path, aka: t.aka || [] },
  }
}

/** The blog's reference formats (2026-10-15): glossary, known issues, answers. */
const shortOf = (n) => String(n || '').split(':').slice(-1)[0].trim()
export function glossaryHead() {
  return {
    title: fullTitle('Glossary of AI model capabilities and jobs'),
    description: 'What each AI model capability and job means, in plain words, with how many engineers have reported on it.',
    canonical: '/blogs/glossary',
  }
}
export function directoryHead() {
  return {
    title: fullTitle('Blog directory: every post by model and topic'),
    description: 'Every Model Information Board post in one place, by the model it covers, the topic it explains, its title or its date.',
    canonical: '/blogs/directory',
  }
}
export function glossaryEntryHead(e, path) {
  if (!e) return glossaryHead()
  return {
    title: fullTitle(`What is ${e.name.toLowerCase()}?`),
    description: e.about.length > 155 ? `${e.about.slice(0, 152).trimEnd()}…` : e.about,
    canonical: path,
  }
}
export function issuesHead() {
  return {
    title: fullTitle('Known issues in AI models, as engineers report them'),
    description: 'Problems engineers report with each AI model, each with its quotes and when it was last reported.',
    canonical: '/blogs/issues',
  }
}
export function issuesForHead(d, path) {
  if (!d) return issuesHead()
  const n = shortOf(d.model.name)
  return {
    title: fullTitle(`${n} known issues`),
    description: `${d.issues.length} problems engineers report with ${n}, each with the quotes behind it and when it was last reported.`,
    canonical: path,
  }
}
export function answersHead() {
  return {
    title: fullTitle('What does each AI model support?'),
    description: 'Tool calling, structured output, image input and prompt caching: what each model advertises, beside what engineers report.',
    canonical: '/blogs/answers',
  }
}
export function answersForHead(d, path) {
  if (!d) return answersHead()
  const n = shortOf(d.model.name)
  return {
    title: fullTitle(`Does ${n} support tool calling, structured output and image input?`),
    description: `What ${n} advertises, beside what engineers report: tool calling, structured output, image input, prompt caching.`,
    canonical: path,
  }
}

/** `/blogs/:slug`, from the post itself. A post the reader may not see gets the index's head. */
export function blogPost(post) {
  if (!post) return blogIndex()
  // The post's own meta description first (written for search since
  // 2026-10-13); posts from before that carry none and fall back to the dek.
  const text = usable(post.description) || usable(post.dek) || usable(post.lead) || 'A note on AI models, written from what engineers report in production.'
  const canonical = `/blogs/${post.slug}`
  return {
    title: fullTitle(post.title),
    description: clip(text),
    canonical,
    breadcrumbs: [{ name: 'Blogs', path: '/blogs' }, { name: squash(post.title), path: canonical }],
    // Article markup (SEO item 11): only what the post carries; structured.js
    // leaves out any field that is missing rather than filling it.
    article: {
      slug: post.slug,
      title: post.title,
      dek: usable(post.dek) || null,
      description: usable(post.description) || null,
      keywords: Array.isArray(post.keywords) ? post.keywords.filter((k) => usable(k)) : [],
      published_at: post.published_at || null,
      provenance: { generated_at: (post.provenance && post.provenance.generated_at) || null },
    },
  }
}

/** Never indexed, whatever index.html says later. */
export const PRIVATE = {
  login: { title: fullTitle('Sign in'), noindex: true },
  admin: { title: fullTitle('Admin'), noindex: true },
  blogLogs: { title: fullTitle('Blog run logs'), noindex: true },
  keywords: { title: fullTitle('SEO keywords'), noindex: true },
  notFound: { title: fullTitle('Page not found'), noindex: true },
}

/**
 * Whether a page is `noindex`: it asked to be, or its canonical path is not on
 * the indexable list (SEO item 5, `contract/indexing.yaml`). An unknown list
 * (`null`: loading, or the request failed) counts as "not on it" - a page that
 * cannot ask is never indexed by default. A page with no canonical has nothing
 * to look up and keeps index.html's robots.
 */
export function noindexFor(head, indexable) {
  if (!head) return false
  if (head.noindex) return true
  if (!head.canonical) return false
  return !(indexable && indexable.has(head.canonical))
}
