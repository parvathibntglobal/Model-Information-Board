# Proposal: a feed entry may be stored as its own raw payload

**Proposed 2026-09-17 by anooj + Claude. Reviewer question, not a taken
decision — it settles a contract reading that three files currently disagree
about, and it is the thing the Substack question sits behind.**

**No Substack ruling is proposed here, deliberately.** Whichever pattern this
establishes is the one a sixth ruling should follow, and deciding it alongside
the ruling would let the ruling decide it.

---

## The question

**Can a feed entry be stored as its own raw payload?**

Not "should we" in general — the narrow, answerable form: when a feed's
`content:encoded` carries a whole post, may we write that entry's bytes into
`raw/` under their own hash, so the entry becomes a document with its own
`text_ref` and its own `content_hash`?

## Three readings of one namespace, all live today

**1 · `collect/adapters/x.py` carves per item and re-serialises.**

```python
def store_posts(self, run: XRun, posts) -> XRun:
    """Write each post's own payload. No request - the bytes are in hand."""
    for post in posts:
        put = self._store.put(post.payload, namespace=RAW)
```

`XPost.payload` is documented as *"The tweet result object, re-serialised
deterministically"* — `json.dumps(result, sort_keys=True, ensure_ascii=False)`.
One search response becomes many raw blobs, each with its own hash.

**2 · `collect/adapters/huggingface.py` does the same**, and names it: its
`payload` field carries *"see the module docstring for why this is the one
re-serialised payload here."*

**3 · `collect/adapters/blog/fetch.py:11-15` holds that this is forbidden:**

> `document.text_ref` points at the **article** bytes … It cannot point at the
> feed payload: one feed covers many entries, so `content_hash` would stop
> identifying one document — which breaks dedupe, and breaks NFR-6, where a
> takedown for one post would land a tombstone on a blob holding forty.

and, on the alternative:

> a discovered entry we could not fetch is a gap, not a document with a
> feed-shaped body — including for full-content feeds, where the alternative is
> storing bytes we serialised ourselves into **the one namespace that forbids
> derived content**.

**4 · `collect/rawstore.py`, the namespace's own contract, says neither.** It
frames `raw/` as *durability*, not as provenance of serialisation:

```
raw/         fetched payloads. Irreplaceable. Never evictable.
flattened/   derived thread text. A cache: regenerable from raw/.
```

The stated reason is NFR-4 — a full rebuild from raw must always be possible —
so `raw/` can never be cleaned up and `flattened/` always can. **There is no
rule in `rawstore.py` about who serialised the bytes.** The phrase "the one
namespace that forbids derived content" appears in the blog adapter's docstring
and nowhere in the store it describes.

## The takedown argument is the right way round, and the objection has it backwards

This is the part worth reading, because the objection's strongest sentence is
the one that reverses.

`RawStore.tombstone(ref, ...)` takes **a ref** and removes **that blob's
bytes**, keeping a marker. So the question is only ever: *how many documents
share the blob a takedown lands on?*

```
ONE BLOB PER FEED          takedown for one post   ->  40 posts' bytes destroyed
ONE BLOB PER ENTRY         takedown for one post   ->  1 post's bytes destroyed
```

**Carving per item is what PREVENTS a single takedown destroying thirty-nine
unrelated posts.** The arrangement the objection defends — a feed blob holding
forty entries — is the arrangement with that problem. The objection reads as
though carving creates the hazard; it removes it.

The same inversion applies to the `content_hash` half. *"`content_hash` would
stop identifying one document"* is true **of pointing many documents at one feed
blob**, and it is the reason to carve rather than a reason not to: a per-entry
blob has a per-entry hash, which is exactly what `content_hash` is for. Dedupe
gets better, not worse.

So the docstring's two technical objections are both arguments **for** the thing
it refuses. What survives of it is one real concern, stated next.

## What does survive: NFR-4, and it is answerable

The reading worth defending is not about takedowns. It is:

> **can the corpus be rebuilt from `raw/`?**

If a per-entry blob is bytes we composed, a rebuild depends on our composition
being stable — and if the carving changes, old blobs and new ones differ for a
document nobody edited. That is a real NFR-4 concern and it is why `raw/` is
"irreplaceable".

**Two answers, and the first is stronger:**

- **Carve the `<item>` element verbatim.** A feed entry is a *subrange of the
  bytes the server served*. Storing that byte range is not re-serialisation at
  all — it is the same relationship `offset_map` already has to a flattened
  thread, and it makes the per-entry blob as original as the feed blob is.
- **Or re-serialise deterministically, as X and HuggingFace already do.**
  `json.dumps(..., sort_keys=True)` is stable, and the project has accepted that
  standing twice. This is the weaker answer and it is the one already in use.

**The feed blob is kept either way.** Nothing proposes discarding it; it is the
discovery artifact and the rebuild input. The per-entry blob is derived *from a
blob we keep*, which is what makes the rebuild argument survivable at all.

## What it unblocks, measured

**Both Medium feeds produce documents from bytes already on disk. No request,
no terms movement, no ruling change.**

The class B ruling requires `feed_carries_full_text: [true]` and says so in its
own words: *"This costs nothing, because the feed carries the whole post."*
`fetch.py:471` already writes the feed bytes to `raw/` on every run.

Measured on this machine's `raw_store`, parsed with the project's own
`parse_feed` and `extract_article_text`, no network:

```
                                 snapshots  entries   DISTINCT entries with
                                  on disk   each      an extractable body
blog:netflixtechblog.com             4       10              11
blog:medium.com/airbnb-engineering   4       10              11
                                                     ────────────────────
                                                             22
```

```
                        content:encoded HTML   extracted TEXT
netflixtechblog.com          median 18,256      median 10,622
medium.com/airbnb-eng.       median 16,553      median  9,911
```

Note the two medians are different measurements and only one is the document
body. `contract/sources.yaml` records `median_body_chars` 18,722 and 15,636 —
those are **HTML** lengths, and mine agree within a snapshot's drift. The
document would carry the **extracted text**, ~10,600 and ~9,900 characters.
Neither is a truncated teaser.

**22 documents, from 8 feed payloads already in `raw/`.** The corpus is 121
blog documents across 7 hosts; this takes it to **143 across 9**, and the two
new hosts are the only ones in the contract that have produced nothing since
they were added.

**Denominator, stated (rule 7):** 11 per feed is *distinct entries across the
four snapshots this machine happens to hold*, not a rate. A feed carries ten
items at a time and the snapshots overlap, so 11 is what four overlapping
windows caught — it is a floor on what the feed has published, and it says
nothing about what a longer history would give.

## The reviewer question

**What is `raw/` a namespace for — bytes nobody derived, or bytes nobody can
regenerate?**

`rawstore.py` answers the second and the blog adapter assumes the first. Two
adapters already ship on the second reading. This proposal asks for that to be
**decided and written in `rawstore.py`**, where the namespace is defined, rather
than left as a sentence in one adapter's docstring that two other adapters
contradict.

- If the answer is **bytes nobody can regenerate**: the blog adapter's objection
  does not apply, both Medium feeds can produce documents, and the carving
  should prefer the verbatim `<item>` range.
- If the answer is **bytes nobody derived**: then `x.py` and `huggingface.py`
  are in breach today and that is the finding, not the blog adapter's caution.
  The two Medium feeds stay at zero documents and the class B ruling's *"this
  costs nothing"* becomes false and should be corrected.

**Either answer is fine and the present state is not**, because a rule that one
adapter enforces and two ignore is not a rule — and the next person to hit it is
whoever writes the Substack adapter.

## Not proposed here

- Any Substack ruling, adapter or feed row.
- Any change to `fetch_articles`, the class A/B split, or robots handling.
- Discarding the feed payload.
- Any write. Nothing in this proposal has been implemented.
