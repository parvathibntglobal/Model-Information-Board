# The 30 blog documents, characterised before anything reads them

**The corpus is contaminated in a way that guarantees over-extraction, and the
contamination is ours. 27 of 30 flattened documents carry a "Recent articles"
block from the site template, every one of those blocks names models, and 13
documents mention a model ONLY there.**

*Engineer 1 · 2026-08-20 ·
`postgresql://example_user@203.0.113.5:5432/Model-information-Board`, read-only ·
surfaces resolved with `entity.resolve` against the live 1,224-surface population*

---

## 0 · Two methodological notes, because the first pass was wrong

**Read the flattened text, not `document.text_ref`.** The stored blog payload is
the **raw HTML page** — every one opens `<!DOCTYPE html>`, 13–19k characters. My
first pass resolved surfaces over it and got 9 identical surfaces on posts about
`sqlite-utils` and CORS alike, because it was reading the site's navigation. The
string the extractor is shown is `thread_context.flattened_text_ref`, written by
`assemble_article`, and everything below reads that.

**Anything else resolving surfaces from `document.text_ref` is counting
navigation as mentions.** Worth checking before triage or the entity gate runs
over stored blog rows.

## 1 · The contamination, measured

```
blog documents                        30
carrying "## Recent articles"         27
  surfaces resolve inside that block  27  of 27
surfaces resolve in the article body  14  of 30
block share of all flattened text     7,182 / 63,879 = 11%
```

**So 13 documents appear to mention a model only because of the template.** The
clearest case, in full — `blog:…/2026/Aug/13/alchemy-utils/`, 367 characters:

```
13th August 2026

Performance boost for DuckDB exports and CSV imports, see here.

## Recent articles

- Qwen 3.8 27B is excellent, but it defaults to wildly overthinking things - 16th August 2026
- Now we have a timeline of the OpenAI accidental attack against Hugging Face - 7th August 2026
- One-shotting a Raccoon Heist game using Claude Fable 5 - 5th August 2026
```

The article is one sentence about DuckDB. The model names, **and a complete
capability-shaped claim**, come from another post's headline:

> *"Qwen 3.8 27B is excellent, but it defaults to wildly overthinking things"*

Subject, polarity both ways, and a condition. An extractor shown this document
would produce a well-formed claim about Qwen 3.8 27B from a post about CSV
imports — **and the quote would verify**, because the sentence really is in the
text it was given. Rule 1 holds and the claim is still wrong about which document
supports it.

**This is a `collect/` defect and it is mine.** `assemble_article` flattens what
`extract_article_text` returns, and trafilatura under `DEFAULT_EXTRACTION` is
keeping the recent-articles list. The fix is in the blog extraction, not in
`judge/`.

## 2 · The 30, by kind

Classified from the flattened text. `relay` counts model-card / benchmark /
announcement language; `first-hand` counts `I ran|tried|tested|found|noticed`
constructions.

| kind | count | what it is |
|---|---|---|
| **link-blog stub** — a sentence or two plus a link | **17** | *"Performance boost for DuckDB exports, see here."* No capability content of its own |
| **link-blog with commentary on someone else's claim** | **6** | quotes or paraphrases an announcement, a paper, a benchmark. `stealing-reasoning-traces` (24 surfaces, relay 4), `deepseek-v4-pro-0813` (21 surfaces, relay 2) |
| **first-hand observation** | **4** | `introducing-muse-glimmer` (first-hand 3), `openclaw`, `alchemy-utils`, `deepseek-v4-pro-0813` each carry one or more `I ran/tried/found` constructions |
| **names no model at all** | **3** | including `sighting-391300422`, 484 characters, 0 surfaces even with the template block |

**Median flattened length is about 1,300 characters** — 367 at the shortest, 3,598
at the longest. These are link-blog entries, not articles: the format is a
sentence of commentary plus a pointer.

## 3 · The column Engineer 2 asked for: whose claim is it

**Documents where a surface resolves but the only capability-shaped content is
somebody else's claim rather than the author's experience.**

| | count of 30 |
|---|---|
| surface resolves, capability content is the **author's own** experience | **4** |
| surface resolves, capability content is **relayed** — announcement, model card, benchmark, or another post's headline | **23** |
| no surface resolves anywhere | **3** |

**The 23 is the row that matters, and it is the same shape as the vendor
announcement in the seven** — the most informative-looking row precisely because
it reads like evidence. A Willison post quoting a model card is structurally
identical to `ClaudeOfficial` posting benchmark copy: a real quote, a real
subject, and an evidentiary weight belonging to the vendor rather than to the
byline above it.

**And 13 of the 23 are relayed from our own template**, which is the worst
version: not even a claim the author chose to repeat.

## 4 · Authors: a gap, with the reason recorded and one question left open

`author` holds **0 rows** and `author_id` is NULL on all 57 documents, blog and
GitHub alike. Not a decision against storing authors:

- **`write_authors` has no caller.** The `assemble-authors` chain stage is
  `run=None`, and its `starves=` text records why: *"`from_github` and
  `from_reddit` read the adapter's in-memory hits, not stored documents, so this
  belongs INSIDE the sweep rather than after it — a chain stage over stored rows
  cannot produce it without re-parsing the raw payloads."* So the reason exists
  and it is about **where** the work belongs, not whether.
- **GitHub**: `from_github` exists and my sweep never called it. That is mine, and
  it is a one-line omission in `ops/sweep.py` beside `write_documents`.
- **Blog**: there is **no `from_blog` at all.** Deeper gap, and it needs a
  decision rather than a call.

**The open question is the one raised, and the Reddit ruling does not settle it.**
`handle_hash` stores a digest and discards the handle, because obligation attaches
at publication and recovery is a raw-store read. A blog byline is public and
attributed by the author's choice, and a GitHub user has a stable numeric id — so
"store a digest and throw the handle away" may be the wrong shape for both. That
is a `contract/` question about `author`, not a bug.

## 5 · What is not comparable to the seven

Different population, and the numbers must not be placed in a sequence:

```
the seven      1 Reddit thread (6 comments) + 1 blog post, mixed authorship
these thirty   30 link-blog entries from ONE author on ONE site
```

The seven produced *zero-expected* for reasons of content — billing, vendor copy,
a relayed benchmark. These thirty produce a different prediction for a different
reason, and one of them is a defect in our own flattening. **The zero does not
carry over and the rates are not comparable.**
