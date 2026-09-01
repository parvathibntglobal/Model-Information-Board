/**
 * The Articles registry — models and the three platforms we collect from.
 *
 * This is the seam the workflow pivots on: the board tagged forum evidence
 * against a capability vocabulary; the Articles view collects what each PLATFORM
 * publishes ABOUT a model. All three platforms are wired for DeepSeek V4 Pro
 * (static, from scrapes). A platform left `null` for a future model renders a
 * "not collected yet" notice rather than an empty list, so its absence is
 * visible rather than read as "nothing exists."
 */
import deepseekArxiv from './deepseek-v4-pro-arxiv.json'
import deepseekX from './deepseek-v4-pro-x.json'
import deepseekReddit from './deepseek-v4-pro-reddit.json'

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
      x: deepseekX,
      reddit: deepseekReddit,
    },
  },
]

export const modelById = (id) => MODELS.find((m) => m.id === id) || MODELS[0]
