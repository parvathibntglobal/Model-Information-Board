# For Engineer 2: the blog run — characterisation, pre-registration, and how to get the bundle

**Read the pre-registration before running. Two outcomes are settled in advance
and neither is about extraction quality, and one number that reached me was
inverted in a way that would have set the wrong expectation.**

*Engineer 1 · 2026-08-20 ·
`postgresql://example_user@203.0.113.5:5432/Model-information-Board`*

---

## If you want to measure RECALL, this is the wrong corpus — GitHub is where it lives

**Put directly rather than left in the writeup, because it decides which run is
worth your time.**

```
blog     30 documents ·  4 carry a first-hand capability observation
                      · 23 relay somebody else's claim · 3 name no model
github   27 documents · 18 carry TWO OR MORE model surfaces in their own text
```

**The blog corpus can test precision and cannot test recall.** It is a good
population for *"does the extractor over-read a relayed claim"* — 23 of 30 are
exactly that shape, and 13 of them relay from our own page template. It is a poor
population for *"does the extractor find a capability report when one is there"*,
because four is not a denominator. A low yield on these thirty is not evidence
about recall, and I would not want it recorded as though it were.

**The GitHub issues are the recall population**, and two things are true of them
at once:

- **They are richer.** 18 of 27 carry two or more model surfaces in the issue body
  — bug reports with error strings and repro steps, which is what
  `collect/CLAUDE.md` calls the highest-signal source.
- **They are incomplete, and the missing part is the conversation.** Every one of
  the 27 is the issue **body alone**: `GitHubHarvester` records `comment_count`
  and calls no comments endpoint, so all 27 are one-member threads and 7 of them
  carry 74 unread comments between them, one with 46.

**And that matters for recall specifically**, because of what the unit measurement
found: a comparison is a property of a conversation rather than a message — 7 of
12 threads carried two surfaces against 2 of 812 comments. So the resolutions, the
corrections and the *"we moved off X because of Y"* sentences are in the comments
we have not fetched. Measuring recall on issue bodies alone would measure it on
the part of the thread least likely to carry a resolved claim.

**Comment fetching does not exist and is scoped:**
`docs/proposals/github-issue-comments.md` — ~7 core calls on the current corpus,
the coverage columns fill exactly because GitHub states the total up front, and
the one genuinely new decision is ranking, since GitHub comments have no score.

So the order I would suggest: precision on the blogs once the template block is
out, recall on GitHub once comments are fetched. Doing recall on GitHub bodies
today would produce a number that looks like recall and is not.

## The package

| | |
|---|---|
| **characterisation** | `docs/measurements/blog-corpus-characterisation.md` — the 30, by kind, with surfaces resolved and whose claim it is |
| **pre-registration** | `docs/measurements/blog-extraction-pre-registration.md` — written before any model call, so it cannot be edited into agreement with what arrives |
| **the bundle** | `python scripts/export_thread_contexts.py --out DIR --all` |
| **the store scope** | `docs/proposals/shared-raw-store.md` — why the bundle is still the shape, and where it stops |

## The number to correct before you plan against it

**It is not "27 of 30 mention no tracked model".** Measured over the flattened
text — the string the extractor is shown:

```
30  documents
27  carry the site template's "## Recent articles" block
27  of those 27 resolve model surfaces INSIDE that block
14  resolve a model surface in the ARTICLE BODY
16  resolve none in their own body — they name a model only via the template
 3  resolve none anywhere, template included
```

The 27 is the count *carrying the template*, not the count naming nothing. So a
plan built on "27 name nothing" would expect almost no claims for the wrong
reason, and would read a template-sourced claim as a surprise rather than as the
predicted artefact.

**The expectation should rest on the first-hand count instead: 4 of 30.**

## This corpus cannot test the extractor on capability observations

Said plainly because it bears on what your run can conclude:

```
 4 of 30  carry a first-hand capability observation (`I ran / tried / found`)
23 of 30  relay somebody else's claim — announcement, model card, benchmark,
          or another post's headline from our own template
 3 of 30  name no model at all
```

**That is a fact about a link blog, not a failure of the sweep.** Willison's format
is a sentence of commentary plus a pointer — median flattened length about 1,300
characters, shortest 367. It is a good corpus for testing *whether the extractor
over-reads relayed claims* and a poor one for testing *whether it recognises a
capability report*, because there are four of the latter.

So a low yield here is not evidence about the extractor's recall. If recall is
what you want to measure, the GitHub issues are the better population — 27
documents, and 18 of them carry two or more model surfaces in their own text.

## Two settled outcomes

**Nothing publishes, and it is the corpus.** `author` now holds 1 row, 30 of 30
documents carry an `author_id`, and there is 1 distinct author. So `n_eff ≤ 1.0`
against a 3.0 minimum, `max_author_share = 1.0` against a 0.50 cap — tripping the
diversity rule independently — and `platform_count = 1` against a minimum of 2.
**Three gates, each failed on its own, none about extraction.** Thirty perfect
observations from one byline would fail all three identically.

**And over-extraction from our template is predicted, with the quotes named.** 13
documents name a model only inside the "Recent articles" block, and that block
carries a complete capability claim from another post:

> *"Qwen 3.8 27B is excellent, but it defaults to wildly overthinking things"*

If that appears attributed to the post about DuckDB CSV imports, **the run
measured our flattener**. It is a `collect/` defect, it is mine, and my
recommendation is still to strip the block before spending the $0.062.

## The export command, and where the shape stops

`_handoff/` proved the shape; the objection was that a hand-built bundle is not an
interface. It now takes `--out`, `--limit` and `--all`, so the manual step is gone
without anybody having to decide about an object store first.

**Measured ceiling, so it is not left to be found:**

```
30 of 59 thread_contexts exportable      19,046 bytes inline per thread
29 NOT exportable — flattened_text_ref resolves in no store this process sees,
   because the GitHub sweep wrote its payloads outside RAW_STORE_PATH
0.54 MB for 30 threads · 16.1 MB projected at the 887-thread corpus
```

**Size is not the ceiling — resolvability is.** 16 MB of JSON is nothing. A bundle
that silently contains 30 of 59 threads is the problem, which is why the count is
printed rather than inferred. And the deeper limit is structural: **a bundle cannot
carry `MISSING`, `CORRUPT` or `TOMBSTONED`.** An unresolvable payload becomes an
absent key, so you see a shorter thread rather than a read failure — meaning your
four read outcomes stay untested however many bundles ship. That is the argument
for one addressable store, and it is scoped rather than built.

**So for this run: the 30 blog threads export cleanly. The 27 GitHub ones do
not, yet, and that is an operational fix on my side rather than a property of the
corpus.**
