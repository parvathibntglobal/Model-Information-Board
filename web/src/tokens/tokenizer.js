/**
 * The tokenizer, loaded only when the token counter opens. Its rank table is
 * large, so it is a dynamic import and its own chunk: no other page downloads
 * it (SEO item 10's first-download budget).
 *
 * o200k_base is OpenAI's published encoding and runs here in the browser; the
 * text is never sent anywhere. Other providers publish no tokenizer this page
 * can run, so their rows apply this count as an estimate (see cost.js).
 */
let loading = null

export const ENCODING = 'o200k_base'

export function loadTokenizer() {
  if (!loading) {
    loading = Promise.all([
      import('js-tiktoken/lite'),
      import('js-tiktoken/ranks/o200k_base'),
    ]).then(([lite, ranks]) => {
      const enc = new lite.Tiktoken(ranks.default)
      return {
        encode: (text) => enc.encode(text),
        decode: (ids) => enc.decode(ids),
        // The library throws "Unknown model" for a name it does not list. That
        // is an answer - "not known to use this encoding" - so it becomes null
        // and the row stays an estimate. It never becomes "exact".
        encodingNameFor: (model) => {
          try { return lite.getEncodingNameForModel(model) } catch { return null }
        },
      }
    }).catch((err) => {
      loading = null   // let a later visit retry; this one shows the error
      throw err
    })
  }
  return loading
}

/**
 * The text cut where the tokenizer cuts it, for the "show tokens" view. A
 * character spread over two tokens (an emoji, most non-Latin scripts) decodes
 * to U+FFFD alone, so tokens are joined until the piece decodes cleanly; `n`
 * says how many tokens a piece holds.
 */
export function pieces(tok, ids, limit) {
  const out = []
  let buf = []
  for (const id of ids.slice(0, limit)) {
    buf.push(id)
    const text = tok.decode(buf)
    if (!text.includes('�') || buf.length >= 4) {
      out.push({ text, n: buf.length })
      buf = []
    }
  }
  if (buf.length) out.push({ text: tok.decode(buf), n: buf.length })
  return out
}
