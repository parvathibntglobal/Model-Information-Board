/**
 * The Articles registry — models and the platforms we collect from.
 *
 * This is the seam the workflow pivots on: the board tagged forum evidence
 * against a capability vocabulary; the Articles view collects what each PLATFORM
 * publishes ABOUT a model. Every platform below is wired for DeepSeek V4 Pro
 * (static, from scrapes). A platform left `null` for a future model renders a
 * "not collected yet" notice rather than an empty list, so its absence is
 * visible rather than read as "nothing exists."
 */
import deepseekArxiv from './deepseek-v4-pro-arxiv.json'
import deepseekX from './deepseek-v4-pro-x.json'
import deepseekReddit from './deepseek-v4-pro-reddit.json'
import deepseekHN from './deepseek-v4-pro-hn.json'
import deepseekDevto from './deepseek-v4-pro-devto.json'
import deepseekTikTok from './deepseek-v4-pro-tiktok.json'
import deepseekInstagram from './deepseek-v4-pro-instagram.json'
import deepseekHF from './deepseek-v4-pro-hf.json'
import deepseekHashnode from './deepseek-v4-pro-hashnode.json'

export const PLATFORMS = [
  { id: 'arxiv', label: 'arXiv' },
  { id: 'x', label: 'X' },
  { id: 'reddit', label: 'Reddit' },
  { id: 'hn', label: 'Hacker News' },
  { id: 'devto', label: 'dev.to' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'hf', label: 'Hugging Face' },
  { id: 'hashnode', label: 'Hashnode' },
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
      hn: deepseekHN,
      devto: deepseekDevto,
      tiktok: deepseekTikTok,
      instagram: deepseekInstagram,
      hf: deepseekHF,
      hashnode: deepseekHashnode,
    },
  },
]

export const modelById = (id) => MODELS.find((m) => m.id === id) || MODELS[0]
