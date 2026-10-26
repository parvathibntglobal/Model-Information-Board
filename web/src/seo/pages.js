import { canonicalComparePath } from '../compare/path.js'
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

/**
 * A comparison. The canonical is the readable path, `/compare/<a>-vs-<b>`, with
 * the names sorted so A-vs-B and B-vs-A are one page (compare/path.js); ids with
 * no readable name keep `/compare?ids=`, sorted the same way.
 */
export function comparePage(ids, names) {
  const list = (names && names.length ? names : ids).map(squash).filter(Boolean)
  if (list.length < 2) {
    return { title: fullTitle('AI Model Comparison'), description: 'Put two or three AI models side by side on what engineers report about each.', canonical: '/compare',
      app: { name: 'AI model comparison' }, breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'AI model comparison', path: '/compare' }] }
  }
  return {
    title: fullTitle(list.join(' vs ')),
    description: clip(`${list.join(' vs ')}: what engineers report about each, side by side, by the jobs, capabilities and metrics they share.`),
    canonical: canonicalComparePath(ids),
  }
}

/**
 * `/token-counter` and `/ai-model-pricing` (#520). Neither is on
 * contract/indexing.yaml's `always` list, so both are noindex like every
 * unlisted page until somebody adds them there. A HEAD OF THEIR OWN MATTERS
 * EVEN SO: a page with no head keeps index.html's robots, which the open build
 * flips to `index, follow`, so a headless page would be the one route the
 * indexing rule could not reach.
 */
export function tokenCounter() {
  return {
    title: fullTitle('LLM Cost Calculator & Token Counter'),
    description: 'Count the tokens in a prompt or an answer in your browser, then see what that text costs to send or generate on each AI model at its list price.',
    canonical: '/token-counter',
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'LLM cost calculator', path: '/token-counter' }],
    app: { name: 'LLM cost calculator & token counter' },
  }
}

/**
 * "Can I run it?" (2026-10-23, docs/proposals/can-i-run-it.md): which open
 * models fit a reader's graphics card or Mac. A tool, so `app` gives it the
 * WebApplication JSON-LD like the token counter.
 */
export function localVram() {
  return {
    title: fullTitle('Can I Run It? Local LLM VRAM Calculator'),
    description: 'Pick your GPU or Mac and see which open models fit in its memory at 4-bit or 8-bit, from the measured size of each model file. Free, no sign-in.',
    canonical: '/local-llm-vram-calculator',
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'Can I run it?', path: '/local-llm-vram-calculator' }],
    app: { name: 'Can I run it? Local LLM VRAM calculator' },
  }
}

export function modelFinder() {
  return {
    title: fullTitle('AI Model Pricing & Specs Table'),
    description: "Every AI model's price per token, context window and features in one table: filter by tool calling, vision, structured output and prompt caching.",
    canonical: '/ai-model-pricing',
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'AI model pricing & specs table', path: '/ai-model-pricing' }],
    app: { name: 'AI model pricing & specs table' },
  }
}

/**
 * THE DEMO'S SECTIONS (2026-10-14). Tools gathers pages that already exist.
 * Reports and Discussions are being built: until they hold content they ask
 * not to be indexed, so an empty page never reaches a search result.
 */
/** `/best-ai-model`: the best model for a job, and cheaper alternatives (2026-10-14). */
export function modelPicker() {
  return {
    title: fullTitle('Best AI model picker: the best model for the job, or a cheaper alternative'),
    description: 'Find the best AI model for your job, or a cheaper alternative to the one you use, from what engineers reported working - beside what each model costs.',
    canonical: '/best-ai-model',
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'Best AI model picker', path: '/best-ai-model' }],
    app: { name: 'Best AI model picker' },
  }
}

/** One job in the picker (`/best-ai-model/<job>`, 2026-10-21): the models engineers reported working for it. */
/** "Coding agents" -> "coding agents" inside a sentence; "RAG" stays "RAG". */
export const inSentence = (s) => (/^[A-Z0-9]{2,}\b/.test(s) ? s : s.charAt(0).toLowerCase() + s.slice(1))

export function pickerJob(job, items = []) {
  const name = inSentence(job.label)
  return {
    title: fullTitle(`Best AI model for ${name}: what engineers report working`),
    description: `The AI models engineers reported working for ${name}, counted from their public posts, beside what each one costs.`,
    canonical: `/best-ai-model/${job.id}`,
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'Best AI model picker', path: '/best-ai-model' },
      { name: job.label, path: `/best-ai-model/${job.id}` }],
    list: { name: `AI models reported working for ${name}`, items },
  }
}

/**
 * One model's alternatives in the picker (`/alternatives/<model>`, 2026-10-21):
 * models engineers reported working on the same jobs and capabilities. `model`
 * is { id, label, slug }.
 */
export function pickerAlternatives(model, items = []) {
  return {
    title: fullTitle(`${model.label} alternatives: what engineers report working`),
    description: clip(`AI models engineers reported working on the same jobs and capabilities as ${model.label}, counted from their public posts, beside what each one costs.`),
    canonical: `/alternatives/${model.slug}`,
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'Best AI model picker', path: '/best-ai-model' },
      { name: `${model.label} alternatives`, path: `/alternatives/${model.slug}` }],
    list: { name: `Alternatives to ${model.label}`, items },
  }
}

/**
 * One provider's alternatives (`/alternatives/<provider>`, 2026-10-22): the
 * other providers' models engineers reported on the same jobs and
 * capabilities. `provider` is { id, label }.
 */
export function pickerProviderAlternatives(provider, items = []) {
  return {
    title: fullTitle(`${provider.label} alternatives: AI models engineers report working`),
    description: clip(`The AI models from other providers that engineers reported working on the same jobs and capabilities as ${provider.label}'s models, counted from their public posts.`),
    canonical: `/alternatives/${provider.id}`,
    breadcrumbs: [{ name: 'Tools', path: '/tools' }, { name: 'Best AI model picker', path: '/best-ai-model' },
      { name: `${provider.label} alternatives`, path: `/alternatives/${provider.id}` }],
    list: { name: `Alternatives to ${provider.label}`, items },
  }
}

/** `/ai-models` and `/ai-models/latest`: every model OpenRouter lists. `type` is a
 *  model type key (`image`), `'new'` for the latest releases, or null for All models. */
const CATALOG_TYPE_NAMES = { text: 'Text', image: 'Image', video: 'Video', speech: 'Speech', audio: 'Audio', transcription: 'Transcription', decisions: 'Decision' }
const MODELS_CRUMB = { name: 'AI models', path: '/ai-models' }
/** `items`: the models the page lists, in its order, as [{ name, path }] (structured data). */
export function catalogIndex(type = null, items = []) {
  if (type === 'new') {
    return { title: fullTitle('Latest AI Models: New Releases'), description: 'The latest AI models, listed most recently first, with their prices, context and type.', canonical: '/ai-models/latest',
      breadcrumbs: [MODELS_CRUMB, { name: 'Latest AI model releases', path: '/ai-models/latest' }],
      list: { name: 'Latest AI model releases', items } }
  }
  if (type && CATALOG_TYPE_NAMES[type]) {
    const n = CATALOG_TYPE_NAMES[type]
    return { title: fullTitle(`${n} AI models by provider`), description: `Every ${n.toLowerCase()} AI model, by provider, with list prices and context.`, canonical: `/ai-models/${type}`,
      breadcrumbs: [MODELS_CRUMB, { name: `${n} models`, path: `/ai-models/${type}` }],
      list: { name: `${n} AI models engineers reported on`, items } }
  }
  return { title: fullTitle('All AI models by provider and type'), description: 'Every AI model, from every provider: text, image, video, speech, audio, transcription and decision models.', canonical: '/ai-models',
    list: { name: 'AI models engineers reported on', items } }
}

/** One model's page in the catalogue (`/ai-models/<id>`). */
export function catalogModelHead(m) {
  const who = m.provider_name ? `${m.provider_name} ${m.name}` : m.name
  return {
    title: fullTitle(`${who}: price, specs and what engineers report`),
    description: `${who}: list price per million tokens, what a workload would cost, context and features, and what engineers report about it.`,
    canonical: `/ai-models/${m.id}`,
    breadcrumbs: [MODELS_CRUMB, { name: squash(m.name), path: `/ai-models/${m.id}` }],
  }
}

/** `/methodology` (2026-10-21): how a report is found, checked and counted. */
export function methodologyPage() {
  return {
    title: fullTitle('How We Count Engineer Reports: Methodology'),
    description: 'How AI model reports are found, checked against the post they came from, and counted by person and post, with the fixed rule behind every verdict.',
    canonical: '/methodology',
    breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Methodology', path: '/methodology' }],
  }
}

export function toolsIndex() {
  return {
    title: fullTitle('Free AI Model Tools: picker, specs, cost calculator'),
    description: 'Find which AI models engineers reported working for your job, what each model advertises, and what your prompt would cost on each one.',
    canonical: '/tools',
  }
}

/**
 * `/reviews` and each of its pages: the hub, a section (`/reviews/jobs`) or one
 * item in it (`/reviews/jobs/coding-agent`). `item.name` is null until the data
 * has loaded, and the title then names the section alone.
 */
/** "AI model reviews by job", "... by capability", "... by metric" (2026-10-20). */
const REVIEW_NOUN = { jobs: 'job', capabilities: 'capability', metrics: 'metric' }

const REVIEWS_CRUMB = { name: 'AI model reviews', path: '/reviews' }
/** `items`: what the page ranks, in its order, as [{ name, path }] (structured data). */
export function reportsIndex(section = null, item = null, items = []) {
  if (!section) {
    return {
      title: fullTitle('AI Model Reviews: Ranked by Engineer Reports'),
      description: 'What engineers report about each AI model, by job, capability and metric: counted, and shown only where at least five different people reported.',
      canonical: '/reviews',
      list: { name: 'AI models ranked by engineer reports', items },
    }
  }
  const base = `/reviews/${section.key}`
  if (item && item.name) {
    return {
      title: fullTitle(`${item.name}: AI model reviews from engineers`),
      description: clip(`What engineers report about ${item.name}, counted by positive, negative and neutral reports, never quoted.`),
      canonical: `${base}/${item.path}`,
      breadcrumbs: [REVIEWS_CRUMB, { name: item.name, path: `${base}/${item.path}` }],
    }
  }
  return {
    title: fullTitle(section.key === 'models' ? 'AI Model Reviews: Ranked by Engineer Reports' : `AI model reviews by ${REVIEW_NOUN[section.key] || section.title.toLowerCase()}`),
    description: clip(section.lede),
    // /reviews/models IS /reviews - the hub opens on the Models section - so both
    // name one canonical and search engines see one page, not two (2026-10-20).
    canonical: section.key === 'models' ? '/reviews' : base,
    breadcrumbs: [REVIEWS_CRUMB, ...(section.key === 'models' ? [] : [{ name: section.title, path: base }])],
    list: { name: section.key === 'models' ? 'AI models ranked by engineer reports' : `AI model reviews by ${REVIEW_NOUN[section.key] || section.title.toLowerCase()}`, items },
  }
}

/**
 * `/evidence` and one model's feed (2026-10-21, PROPOSED). NOINDEX while the
 * feed is proposed: its paraphrases are written by a model and its terms are
 * not ratified (contract/publication.yaml `evidence_feed`), so it is not put in
 * front of a search engine before they are.
 */
export function evidenceHead(label = null, id = null) {
  if (!label || !id) {
    return {
      title: fullTitle('Evidence feed: the reports behind every count'),
      description: 'Every report behind the counts on this site, in our own words, newest first, each with a link to its source.',
      canonical: '/evidence',
      noindex: true,
    }
  }
  return {
    title: fullTitle(`${label}: the reports behind the counts`),
    description: clip(`Every report engineers wrote about ${label}, in our own words, newest first, each with its source.`),
    canonical: `/evidence/${id}`,
    noindex: true,
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
    title: fullTitle('AI Glossary: AI and LLM terms defined in a paragraph'),
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
  benchmarks: { title: fullTitle('Benchmarks'), noindex: true },
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
