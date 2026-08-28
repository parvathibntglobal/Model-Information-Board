# Ruling: `content_hash` identifies the fetched artifact, `text_ref` locates it, and extraction happens at assembly

**Decided, once, for all three platforms. And my Reddit answer was wrong — it is
being repaired alongside GitHub's rather than defended.**

Asked for after the GitHub JSON finding, because I had already taken one answer
for Reddit under time pressure and a second per-platform decision would leave one
field meaning two things.

*Engineer 1 · 2026-08-28. Extends ruling 4 in `docs/engineer-1/rulings.md`, which
settled that the two columns are separate and did not settle what each names.*

---

## 0 · The ruling in four lines

```
content_hash    the hash of the BYTES THE PLATFORM GAVE US, unmodified.
text_ref        the location of those same bytes. One artifact, two columns:
                identity and location, which is ruling 4 unchanged.
prose           DERIVED AT ASSEMBLY, never stored in place of the payload.
the invariant   content_hash(resolve(text_ref)) == content_hash, always.
```

That last line is the part worth having. It is checkable by a test, it is what
makes the two columns describe one thing rather than two, and **it is false for
1,507 reddit rows today.**

## 1 · What I got wrong on Reddit, precisely

`scripts/repoint_reddit_text_refs.py` re-pointed `text_ref` at extracted prose
**and overwrote `content_hash` with the prose's hash**:

```sql
UPDATE document SET text_ref = %(text_ref)s, content_hash = %(content_hash)s
```

I was fixing a real and serious defect — the sweeps had stored
`json.dumps(post.raw)` and `assemble_reddit` was about to flatten JSON envelopes
for 1,512 threads. The fix worked: reddit `text_ref` now resolves to
`'**TL;DR of the discussion generated automatically after 640 comments.**\n…'`,
actual prose, and the 1,512 contexts hold text rather than envelopes.

**And it broke two things that no test covers, because `document` has exactly one
ref column.** I checked the schema rather than remembering it:

```
id, source, external_id, url, author_id, thread_root_id, parent_id, created_at,
fetched_at, lang, text_ref, content_hash, minhash, simhash, engagement, ...
```

There is no `raw_ref`. So pointing `text_ref` at derived prose **leaves the
fetched payload unreferenced from the row**, and overwriting `content_hash`
leaves it **unidentified as well**.

### 1a · NFR-6 breaks

> *"tombstone a document; its quotes vanish next run, **only the content hash
> remains**."*

The hash that remains has to be a fingerprint of **what the author published**,
because a takedown is about published bytes. After my change it is a fingerprint
of a string *we assembled* from two JSON fields. Two consequences:

- Nobody can check it against anything. Reddit cannot confirm the hash of our
  concatenation of their `title` and `selftext`.
- **It moves when our extractor changes.** Add a separator, strip a trailing
  newline, and every tombstone's hash changes. A tombstone whose hash is a
  function of our current code is not a tombstone.

### 1b · NFR-4 breaks

> *"Raw payloads are immutable and content-hash addressed. **Reprocess from there
> rather than re-fetching.**"* — `CLAUDE.md`, Conventions

Reprocessing from raw requires the row to say which raw artifact it came from.
With `text_ref` on prose and `content_hash` on prose, **the row says neither**.
Changing what counts as prose then requires a re-fetch, which is the exact thing
that convention exists to prevent — and on Reddit a re-fetch is not available,
because the listing endpoint returns *recent* posts and those posts are no longer
recent.

**Recoverable, and that is the good news and also the argument.** The discovery
pages are in `harvest_run.discovery_refs`; the store is content-addressed; so
`json.dumps(post.raw)` recomputed from a stored page hashes to the same value and
lands at the same location. The repair needs **no network call**. That property
is precisely what (b) below preserves and what my fix spent.

## 2 · Blog already had the right answer, and it is the only platform with claims on the board

I checked all three rather than reasoning from the code:

```
blog     text_ref -> '<!DOCTYPE html><html lang="en"><head><meta charSet="utf-8"…'
                     RAW HTML. content_hash is that HTML's hash.
                     `assemble_article` uses `article.text`, which is what
                     `extract_article_text` (trafilatura) returned.

github   text_ref -> '{"url":"https://api.github.com/repos/anthropics/claude-code/…'
                     RAW JSON, flattened VERBATIM. No extraction step at all.

reddit   text_ref -> '**TL;DR of the discussion generated automatically after 640…'
                     PROSE. Correct for the extractor, and the payload is now
                     unreferenced.
```

**Blog is the pattern.** Container in the store, hash of the container in the row,
prose derived at assembly by a named extractor. It has produced the only verified,
rendered claims this project has, and it survives an extractor change as a re-run.

So the repo already contained both answers, and the one I picked for Reddit is the
one blog rejected.

## 3 · Why extraction belongs at assembly rather than in the writer

This is the reason that is not in any existing doc, and it decides the question
independently of NFR-4 and NFR-6.

**The writer runs before anyone knows how the document will be assembled.** A
GitHub issue is assembled as `issue_body_only`; a reddit post as
`post_body_only`; a reddit thread as `specificity_x_log_engagement@observed`. The
prose each shape needs is different — a thread wants each comment's `body`
separately so the offset map can attribute spans, a post wants `title` plus
`selftext` joined. If the writer picks the prose, it is picking for a shape that
has not been chosen yet, and the four `selection_method` values become four
things the fetcher has to anticipate.

**And it puts the platform knowledge where it already is.** `assemble_issue` knows
it is holding an issue. `assemble_reddit_post` knows it is holding a post. That is
one JSON parse each, in the function whose whole subject is that platform's shape.

## 4 · The repair, both platforms, one change

```
github   assemble_issue extracts title + body from the payload before flatten.
         text_ref and content_hash unchanged — they were already right, and
         github.py:61's docstring was right for the reason it gave.

reddit   assemble_reddit / assemble_reddit_post extract title + selftext (post)
         or body (comment) before flatten.
         text_ref and content_hash restored to the payload, recomputed from
         harvest_run.discovery_refs. No re-fetch, no network.
         The 1,512 thread_contexts REBUILD — their text is unchanged in content,
         so the extraction just run stays valid; what changes is that the row
         once again names where its text came from.

both     a test asserting the invariant, on all three assembly paths:
             content_hash(resolve(text_ref)) == document.content_hash
         and a second asserting the flattened text is not a container:
             does not parse as JSON, does not start with '<'
```

**The second test is the one that would have caught all of this a week ago** and
is two lines. I only thought to write it after finding the bug in my own code,
which is the honest order of events, and it is now the cheapest thing on this
list.

## 5 · The alternative I rejected, and it was close

**`text_ref` on prose, `content_hash` on the payload.** Tempting, because the
store is content-addressed — `raw/sha256/ab/cd/abcd…` — so `content_hash` *alone*
locates the payload. NFR-6 and NFR-4 both survive, and `text_ref` gets to mean
"the text" on every platform, which is what its name says.

Rejected because it makes the two columns describe **different artifacts**, and
the trap that follows is silent: anyone who computes
`content_hash(resolve(text_ref))` and compares it to `content_hash` gets a
mismatch and has no way to tell a bug from the design. Ruling 4's framing —
*"`text_ref` is a location, `content_hash` is identity"* — reads naturally as one
thing described two ways, and it should stay true rather than become a coincidence
that held on one platform.

The invariant in §0 is worth more than `text_ref` matching its name.

## 6 · What would revise this

An object store where reading the container is expensive enough that per-assembly
extraction shows up in the nightly batch's wall clock. Then a **derived** prose
namespace beside `flattened/` is the answer — a third ref column, cached and
regenerable, with `text_ref` and `content_hash` still on the payload. That is an
addition to this ruling rather than a reversal of it, and nothing today needs it:
2,757 documents.

## 7 · One thing this changes about how I work

I took the Reddit answer in the same hour I found the defect, with 1,512 contexts
waiting on it, and it was the wrong one — while a correct implementation of the
same decision was sitting in `collect/assemble/article.py` the whole time.

The check that would have caught it is not more care. It is **asking what the
other platforms do before fixing one**, and the repo makes that a one-line grep.
I did that today only because the GitHub finding forced a second look at the same
field.
