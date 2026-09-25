# Re-parsing the 30: the rule moves to the contract, and the re-assembly is dropped

**The template-block rule was a dict in `parse.py` with one key and no
production caller. Moving it to `contract/sources.yaml` found a second feed that
needs stripping and two pages of the first feed the rule was missing. Then the
re-assembly was DROPPED by the database — 30 of 30 — which answers the identity
question with a measurement rather than a reading.**

*Engineer 1 · 2026-08-20 · `postgresql://example_user@203.0.113.5:5432/Model-information-Board`*

---

## 1 · The rule was firing on zero feeds, not one

The previous commit described the rule as per-feed and "opt-in, so no existing
caller changes meaning". Both halves were true and together they meant
**nothing was stripped anywhere**: `extract_article_text` grew a
`template_block` parameter, and all three callers —
`collect/adapters/blog/write.py:190`, `scripts/blog_so_sweep.py:164`,
`scripts/export_thread_contexts.py:301` — passed nothing. `template_block_for`
had no caller outside `tests/`.

So the fix looked applied and did not exist in any path that writes a document.
It is now wired at `write.py`, the production writer, and the run report says
what the rule did or why it did nothing.

## 2 · "The other eight feeds have no stored HTML" — four of them do

Recorded because it is a rule 7 failure of exactly the shape the rule was added
for, and it was mine. Two different populations were stated as one:

```
TRUE     every blog DOCUMENT is simonwillison.net       30 of 30, checked
FALSE    the other eight feeds have no stored HTML      four of them do
```

`raw_store` holds **138 pages that declare their own URL**, across five hosts.
Documents were only ever written for one of them, so "no `document` row" was read
as "no stored page", and the conclusion — that eight templates were unverifiable
— followed from the wrong denominator.

Measured, per host, over every stored page that extracts:

| feed | pages | terminal heading | verdict |
|---|---|---|---|
| `simonwillison.net` | 62 | `Recent articles` ×57, `More recent articles` ×4 | **strips** — two spellings |
| `engineering.grab.com` | 10 | `Related jobs at Grab` ×10, opened by `Join us` ×10 | **strips** |
| `hamel.dev` | 12 | `Footnotes` ×9 — the author's own apparatus | verified clean |
| `vickiboykis.com` | 20 | 20 distinct article titles, nothing repeats | verified clean |
| `slack.engineering` | 8 | nothing occurring more than twice | verified clean |
| `jxnl.co`, `engineering.atspotify.com`, `netflixtechblog.com`, `medium.com/airbnb-engineering` | 0 | — | **unverified** |

**And the single-string rule was missing 4 pages of the one feed it did cover.**
`^\s{0,3}#{1,6}\s+Recent articles$` does not match `## More recent articles`, so
those four kept their block under a rule that looked applied. The contract holds
a list per feed and `strip_template_block` takes the earliest match, so the
order of that list cannot change how much text is removed.

## 3 · Three states, because two collapse the thing worth seeing

`contract/sources.yaml` now carries a `template_block` mapping on **every one of
the nine blog feeds**, and `template_block_for` returns a `TemplateBlockRule`
rather than `str | None`:

```
verified + headings     strip from the earliest match       2 feeds
verified + no headings  LOOKED AND FOUND NOTHING            3 feeds
unverified              NOBODY HAS LOOKED                   4 feeds
```

A `str | None` return collapses the last two into `None`, and then a rule that
does nothing because there is nothing to do is indistinguishable from a rule that
does nothing because no one has checked (rule 6). `inert_reason` is the string a
report prints; `strips` is the boolean control flow reads.

Every blog feed carries the key, so an unexamined feed is a row somebody can
count rather than a key that is missing — which is what makes **4** a number in
this document instead of a silence.

`BlogAssembleReport` now ends with `template block: N stripped (<reason>)`, and
N is measured by comparing lengths rather than by trusting that the rule fired: a
heading the contract names and a page does not carry reads as 0.

## 4 · Re-parsing the 30

All 30 documents' payloads resolve in `raw_store`, so this is the same bytes
re-read, not a re-fetch.

```
                        one heading (committed)   two headings (contract)
chars                   63,869 -> 56,143          63,869 -> 55,751
                        (12.0% removed)           (12.7% removed)
documents shrunk        27 of 30                  29 of 30
documents resolving
a model surface         29 -> 14                  29 -> 13
```

**Which heading did the work: `Recent articles` on 27, `More recent articles` on
2, neither on 1.** So the two pages the committed rule missed were both in the
thirty, and stripping them removed one more document's only model mention.

**Sixteen of the thirty stopped appearing to mention a model** once the author's
own link index was gone. That is the over-read surface removed, and it is a
figure about *this* corpus of 30 simonwillison.net entries — not a naming rate
and not a property of blogs.

## 5 · What `extraction_version` changing does: DROPPED, and the database says so

The question was whether the existing 30 `thread_context` rows are superseded,
replaced or duplicated. **None of the three: the re-assembled rows are silently
discarded.**

`extraction_version` is now `trafilatura-2.2.0+pipeline-2+opts-b19cf430f6dd`, so
it did change. It is also **persisted nowhere** — there is no such column on
`thread_context` — and the id is `stable_id("thread_context", root_id,
pipeline_version)`, which reads `settings().pipeline_version`
(`collect-0.1.0`), a different field from `ExtractionOptions.pipeline`. So:

```
re-assembled all 30 against staging, in a transaction, then rolled back

  ids recomputed identical to the stored row   30 of 30
  rows written by ON CONFLICT DO NOTHING       0
  rows DROPPED                                 30
  new flattened blob differing from stored ref  29 of 30
```

Worked example:

```
blog:https://simonwillison.net/2026/Aug/10/introducing-muse-glimmer/
  thread_context id  thread_context_518d32b3cce10eae   (unchanged)
  stored ref         flattened/sha256/f2/fe/f2fe1f187ebc...
  re-assembled ref   flattened/sha256/16/e5/16e5370ec790...
  stored ref AFTER   flattened/sha256/f2/fe/f2fe1f187ebc...  <- old flattening
```

**The row keeps pointing at the contaminated flattening, and the fix looks
applied.** Note the new blob IS written to the object store before the insert is
attempted, so a re-parse leaves 29 orphaned blobs under `flattened/` — harmless,
because that namespace is a regenerable cache, but worth knowing before someone
reads a file count as a row count.

### The counterfactual, measured the same way

Bumping `pipeline_version` to `collect-0.2.0` and re-assembling, same transaction
discipline:

```
thread_context   59 -> 89   (+30)
thread_root_ids now holding MORE THAN ONE row   30
a column marking either row stale               NONE
```

So the three options resolve as:

| option | reachable? | how |
|---|---|---|
| **superseded** | **no** | no `superseded_by` column exists anywhere in `contract/tables.sql` |
| **replaced** | **no, by design** | `write_thread_context` is `ON CONFLICT DO NOTHING`; replacing `offset_map` in place would invalidate every quote already resolved against it |
| **duplicated** | yes, on a `pipeline_version` bump | two rows per article, neither marked current |
| **dropped** | **what actually happens** | 30 of 30, silently |

**So re-assembly is blocked on an identity decision, not on effort** — and the
decision is not "bump the version", because that trades a silent drop for a
silent duplicate. What distinguishes them is a stored identity for the
extraction, which is #5 A4 and unruled.

## 6 · The fingerprint is the one thing that would have noticed

`thread_extraction.content_fingerprint` is sha256 of the exact flattened bytes
the extractor was given, and it exists precisely because `thread_context.id`
ignores content. It is the only mechanism in the schema that can tell these 30
rows changed underneath a stable id:

```
introducing-muse-glimmer   f2fe1f187ebc  ->  16e5370ec790
```

**It has had no real reason to fire until now** — `thread_extraction` holds 0
rows — and this is that reason. It also means the ordering matters: extracting
the thirty *before* the re-parse lands writes a fingerprint of the contaminated
text, and the pre-registration's predicted template artefact would be measured
and billed for.

**The thirty have not been extracted, and must not be until the re-assembly
actually lands.** `judge extract` reads `thread_context.flattened_text_ref`,
which — per §5 — still points at the flattening that contains the block.
