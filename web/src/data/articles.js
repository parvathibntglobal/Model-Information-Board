/**
 * The Articles registry — models and the three platforms we collect from.
 *
 * This is the seam the workflow pivots on: the board tagged forum evidence
 * against a capability vocabulary; the Articles view collects what each PLATFORM
 * publishes ABOUT a model. arXiv is wired first (static, from a scrape); X and
 * Reddit are declared but not yet collected, and the UI says so rather than
 * rendering an empty list as if nothing exists.
 */
import deepseekArxiv from './deepseek-v4-pro-arxiv.json'

export const PLATFORMS = [
  { id: 'arxiv', label: 'arXiv' },
  { id: 'x', label: 'X' },
  { id: 'reddit', label: 'Reddit' },
]

export const MODELS = [
  {
    id: 'deepseek-v4-pro',
    name: 'DeepSeek V4 Pro',
    vendor: 'DeepSeek',
    // A platform value of `null` means "collector not wired yet" — distinct from
    // a value with `articles: []`, which would mean "collected, found nothing".
    platforms: {
      arxiv: deepseekArxiv,
      x: null,
      reddit: null,
    },
  },
]

export const modelById = (id) => MODELS.find((m) => m.id === id) || MODELS[0]
