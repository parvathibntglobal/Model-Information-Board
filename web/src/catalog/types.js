// The model types the Models menu and pages offer, in their order.
//
// THE KEYS ARE OPENROUTER'S OWN OUTPUT MODALITIES (judge/catalog.py: TYPES),
// so "Image models" means exactly what https://openrouter.ai/models?output_modalities=image
// lists. The board invents no taxonomy; the labels and notes are ours, the
// sorting is theirs. One list for both the menu and the page, so the two can
// never offer different types.
export const MODEL_TYPES = [
  { key: 'text', label: 'Text', note: 'Chat, code, reasoning' },
  { key: 'image', label: 'Image', note: 'Generate and edit images' },
  { key: 'video', label: 'Video', note: 'Generate and edit video' },
  { key: 'speech', label: 'Speech', note: 'Text to a spoken voice' },
  { key: 'audio', label: 'Audio', note: 'Sound and music out' },
  { key: 'transcription', label: 'Transcription', note: 'Speech to text' },
  { key: 'decisions', label: 'Decision', note: 'Classify, route, decide' },
]

export const typeLabel = (key) => (MODEL_TYPES.find((t) => t.key === key) || {}).label || key
