# The eight claims: no database holds them, and the input says they were over-read

**Asked for: the eight claims with model, capability, polarity, quote and
permalink. They do not exist in any database, and I can show what they were
extracted from — which answers the harder question the request was really about.**

*Engineer 1 · 2026-08-20 · every DSN checked below*

---

## 1 · No database holds them, and there is no artifact either

```
staging        52.17.75.29:5432/Model-information-Board    claim=0 cell=0 thread_extraction=0
local test     localhost:5433/modelboard_test              claim=0 cell=0 thread_extraction=0
local harvest  localhost:5433/modelboard_harvest_test      claim=0 cell=0 thread_extraction=0
```

No file under `_handoff/`, `fixtures/` or `docs/` contains a `quote_offset` or a
`capability_key`. The reason is on the record twice: the run was pre-registered to
a **disposable** instance so that *"did the extractor write that row or the
harvester"* stays answerable, and the eight were then dropped at
`judge/pipeline.py:150`, which keys on `resolved_version_id` — a field the
extractor is never shown. **8 proposed, 8 verified, 0 inserted.**

So the fields asked for cannot be printed. What can be printed is the input, and
that turns out to be the more useful half.

## 2 · What the run was given: 7 documents, 2 threads

Identified by matching `first-extraction-run.md`'s own figures — one Reddit thread
of 3,322 flattened characters, one blog of 1,607 — against `_handoff/threads/`.

| document | permalink | model surfaces resolved |
|---|---|---|
| `reddit:t3_1u1b22l` | [/r/ClaudeAI/…/introducing_claude_fable_5/](https://reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/) | Fable 5, Opus 4.8 |
| `reddit:t1_oqoc844` | […/oqoc844/](https://reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/oqoc844/) | Fable 5 |
| `reddit:t1_oqodw1j` | […/oqodw1j/](https://reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/oqodw1j/) | **none** |
| `reddit:t1_oqocfjv` | […/oqocfjv/](https://reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/oqocfjv/) | **none** |
| `reddit:t1_oqorjbe` | […/oqorjbe/](https://reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/oqorjbe/) | Fable 5, Opus 4.8 |
| `reddit:t1_oqocu7n` | […/oqocu7n/](https://reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/oqocu7n/) | Fable 5 |
| `blog:sha256:053141a14a3c0a43` | *"On Programming Joy and Octocat"* | **none** |

Surfaces resolved with `entity.resolve` against the live 1,224-surface population.

## 3 · Read as capability evidence, document by document

**The post is vendor copy.** *"state of the art on nearly all tested benchmarks,
with exceptional performance in software engineering"* — an announcement written by
`ClaudeOfficial`. It resolves two models and it is marketing. This board publishes
what **engineers** report; a claim extracted here is a vendor claim wearing a
Reddit permalink.

**Three of six comments are about billing, not capability.** `oqoc844`, `oqocu7n`
and `oqodw1j` are plan availability, usage credits and *"will cost like $5000/mo"*.
Nothing about what the model does.

**The one first-hand capability observation resolves to no model.** `oqocfjv`:
*"Fable uses up more tokens than a old Porsche gas"* 🤝 — verbosity, observed by a
user, and `Fable` alone does not resolve because bare `fable` is one of the 26
`FAMILY_WORDS` `_admissible` excludes. **The only engineer-observed capability
statement in the thread is invisible to the entity gate.**

**The one real comparison relays a benchmark rather than an experience.**
`oqorjbe`: *"Fable 5 on med is cheaper than Opus 4.8 on xhigh and gives 10%+ better
results on SWE-Bench (p 255 of the model card pdf)."* Two models, a condition
(`med` vs `xhigh`), a number, and a citation — **to the vendor's model card.** It
is a well-formed comparison and its evidentiary weight is the vendor's, not the
commenter's.

**The blog document resolves no model at all.** *"On Programming Joy and
Octocat"* is about GitHub's availability and the old internet. Whatever the eight
included, anything drawn from this document is a claim about a model from a text
that names none.

## 4 · So: over-read, and the interesting part is what could not have caught it

**Eight claims cannot be supported by this input.** Seven documents, of which two
resolve no model, three are billing, one is vendor copy, and one relays a vendor
benchmark. On the most generous reading there are **two** capability-shaped
statements and one of them is unattributable.

**And all eight passed quote verification.** That is not a contradiction — it is
the finding. Rule 1 checks that the quote exists byte-for-byte in the text the
model was shown, and every one of them did. **Quote verification cannot see
over-reading**, because the sentence is really there; what is invented is the claim
*about a model* that the sentence is said to support. A vendor announcement quoted
verbatim is a verbatim quote.

That gap is exactly what the third golden set measures, and it is why the set is
not optional: it is the only check in the design that can catch a true quote
carrying a false claim. Nobody had looked at these eight with that question, and
the input alone answers it without needing the rows.

## 5 · Two things this hands to Engineer 2

**A live instance for the family-surface question.** `oqocfjv` is a real engineer
observation about token consumption, dropped because `fable` is a family word.
That is the cost of excluding bare family words, measured on one comment rather
than argued in the abstract — and it is the other side of the ledger from the
`pro`-in-`problem` noise the exclusion prevents. Both are real; the trade is now
priced on both sides.

**A reason to re-run before the golden set is designed.** The eight are gone and
cannot be recovered. Re-running the extractor over these same seven documents costs
about $0.002 and would produce claims that can be examined against the table above
— with the input already characterised, so the comparison is against a known
answer rather than an impression. That is a model call in `judge/`, so it is hers
to run or to delegate.
