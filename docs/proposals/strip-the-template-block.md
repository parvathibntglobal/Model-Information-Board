# Stripping the template block: what it costs, where it belongs, and the re-flatten that cannot land

**It belongs in the blog parser, not the export, and it affects every blog
document rather than these thirty. No trafilatura option removes it — measured.
And a re-flatten under changed rules currently writes nothing, because the
`thread_context` id does not carry what its own comment says it carries.**

*Engineer 1 · 2026-08-20 · nothing stripped yet*

---

## 1 · No extraction option removes it

Tested on the stored HTML for `blog:…/2026/Aug/13/alchemy-utils/`, whose flattened
text is 367 characters of which the block is most:

```
default (favor_precision=False)   367 ch   "Recent articles" present
favor_precision=True              302 ch   "Recent articles" present
include_tables=False              367 ch   "Recent articles" present
```

**So it is not boilerplate trafilatura recognises** — for this site's markup the
recent-articles list sits inside the content region. `favor_precision=True` drops
65 characters and does not drop the block, so flipping it would move every offset
in every article for no benefit here. It should not ride along with this fix; it is
still the calibration `options.py` says it is.

## 2 · It belongs at extraction, and the precedent is already recorded

`options.py` has the argument written down for a sibling case — the footnote
back-link `↩`, chrome the renderer emitted, in 10 of 106 documents:

> stripping it belongs at extraction rather than in the flattener **where it would
> look solved**

Same reasoning, same place. Two more reasons this is not the export's job:

- **The export is a transport.** Stripping there leaves the database holding
  contaminated `flattened_text_ref` content, so anything else that resolves a ref
  — the resolver we are about to wire — gets the template back.
- **`options.pipeline` exists for exactly this.** It is *"the generation of the
  processing this lane does AROUND the extraction call"*, and its docstring names
  the back-link strip as the change waiting on it. This is the second.

**Scope: every blog document, not these thirty.** 27 of 30 carry the block here,
and the same template is on every post of the site; the nine feeds in the contract
have their own templates and want the same question asked of each. So the strip is
per-feed knowledge, not a global regex — a `prune_xpath` or a per-feed selector,
recorded in `contract/sources.yaml` beside the byline metadata that is already
per feed.

## 3 · What it costs

**Cheap now and not later.** `claim` is 0 and `cell` is 0, so **no stored quote
resolves against these offsets.** Every character removed moves every offset after
it; today nothing holds one. This is the cheapest moment the fix will ever have.

**Then the re-flatten, and here is the problem.** All three assemblers derive the
row id the same way:

```python
# article.py:143, issue.py:86, thread.py:274
id=stable_id("thread_context", document_id, version)   # version = settings().pipeline_version
```

and `thread.py:271` claims:

> The flattening is part of what the row asserts, so the version is in the id: a
> re-flattening under changed rules is a different row rather than an overwrite of
> one nobody can tell changed.

**That is false as written.** The id carries `pipeline_version` — `collect-0.1.0`
— which does not move when extraction options or flattening rules change.
`extraction_version`, the value that actually fingerprints the rules, is **not in
the id**. And `write_thread_context` is `ON CONFLICT (id) DO NOTHING`.

**So a re-flatten under the new strip produces the same id and silently writes
nothing.** The old contaminated text stays, the report says the row was already
present, and the fix looks applied. Same shape as the export emitting 30 of 59
before the count was printed — a guarantee stated in a comment and enforced by a
value that does not carry it.

**Two ways out, and the second is the real fix:**

| | cost |
|---|---|
| delete the 30 rows and re-assemble | works today because nothing references them. Leaves the defect for the next rules change |
| put the extraction fingerprint in the id | the comment becomes true. Every existing row keeps its id; the next re-flatten gets a new one, which is what `ON CONFLICT DO NOTHING` was written to assume |

I would do the second and then the first, in that order, so the re-assembly is
itself the test that a rules change produces a new row.

## 4 · The 29 unexportable contexts: two causes, and only one is a config error

Measured by resolving every `flattened_text_ref` against both stores:

```
issue_body_only                        27  resolve in the SWEEP store
specificity_x_log_engagement@observed   2  resolve in NEITHER
whole_document                         30  resolve in raw_store
```

**The 27 GitHub contexts are a config error, and mine.** I passed
`--store <scratchpad>/_sweep_store` to the sweep and again to `assemble github`, so
the payloads were written — 153 files, they exist — to a directory that is not
`RAW_STORE_PATH`. Recoverable by copying that store into `raw_store`: the layout is
content-addressed and identical, so a copy is a merge and a collision can only be
the same bytes.

**The 2 Reddit contexts were never written.** They come from the fixture and export
path, where the text is inlined rather than `put`, so no store ever held their
flattened bytes. Not recoverable by a copy; they would have to be re-assembled from
the Reddit fixture.

**Not a second store in the architectural sense** — one store plus a stray
directory. Which is the same class one layer down, as you said: **`RawStore`
accepts any path and silently creates a new store rather than refusing**, and
nothing compares the path a writer used against the path the reader will use. A
`--store` flag with no relationship to `RAW_STORE_PATH` is a fork in the store that
reports success on both sides.

**The cheap guard:** a writer whose store path differs from `settings().raw_store_path`
should say so once, loudly, rather than be discovered when a reader cannot resolve
a ref. That is one comparison at construction and it would have printed on the
sweep three turns ago.
