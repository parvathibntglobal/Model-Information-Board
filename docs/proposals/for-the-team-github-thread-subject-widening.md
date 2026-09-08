# GitHub thread-subject: inherit only where the root names exactly one model

**2026-09-08, anooj. THE RECOMMENDATION IS OPTION 3: widen to GitHub, and
inherit only where the thread root resolves to exactly one model.** ~870
documents, from 231 of 459 roots.

Not implemented - `SUBJECT_FROM_THREAD_ROOT` is still
`frozenset({"hackernews"})` and the test still pins it, because this is a ruling
to make rather than a change to take. But it is put as THE recommendation and
not as one of three possibilities, and the last section says why the objection
does not survive the restriction.

The argument for widening GitHub is *identical in form* to the one that carried
Hacker News, and that is exactly why it must not carry automatically. **The HN
ruling was made on 511 comments in 2 threads. Unrestricted widening would apply
to 3,382 documents and move 1,388 of them** - four times larger than its own
evidence. The restriction below is what makes the size defensible rather than
merely smaller.

---

## 1 · The form of the argument is the same

Hacker News was admitted because it is the first platform whose subject line
lives in a **separate record** — a comment's payload is its body, and the story
is another row. That is a platform-shape fact, not a claim about aboutness.

**GitHub is the same shape.** A GitHub comment's payload is its `body`; the
issue title is in the parent row. At the triage stage a GitHub comment faces the
entity gate alone, exactly as an HN comment did.

| | what the gate reads | where the subject is |
|---|---|---|
| Reddit post | `title` + `selftext` | in the document |
| blog article | the extracted article | in the document |
| GitHub **issue** | `title` + `body` | in the document |
| GitHub **comment** | the comment body alone | **the issue, another row** |
| HN comment | the comment body alone | **the story, another row** |

The table in `collect/triage/gates.py` listed "GitHub issue" and stopped there.
That was true and incomplete: 2,016 of GitHub's 3,382 stored documents are
comments, not issues.

## 2 · What it would do, measured

Ruling scope versus counterfactual, on the 3,373 GitHub documents this host can
read (`--subject-sources hackernews,github`, which refuses to combine with
`--write`):

| | kept | survival | `no-resolvable-entity` drops | inherited |
|---|---|---|---|---|
| as ruled (HN only) | 1,447 | **42.9%** | 1,511 | 0 |
| widened to GitHub | 2,497 | **74.0%** | 123 | 1,388 |

**+1,050 documents kept. `no-resolvable-entity` falls by 1,388.** The root side
is fully reachable: 2,016 of 2,016 GitHub children resolve to a stored issue
row, across 584 distinct roots, so the cost is 584 raw-store reads and one join.

## 3 · What those 1,388 documents would actually inherit

This is the part that decides it, and it took a correction to get right.

Of the 459 distinct issue roots that would supply a subject:

| distinct models the root names | roots |
|---|---|
| exactly 1 | **231** (50.3%) |
| 2 | 123 |
| 3–5 | 78 |
| 6–14 | 23 |
| 0 (declared-only surface, no owner) | 4 |

**~870 of the 1,388 documents would inherit an unambiguous subject. ~518 would
inherit a root naming two or more models.**

> ⚠ **My first version of this table said "455 of 459 roots name more than one
> model", and that was wrong** — it counted *surfaces*, not models, and one
> model has several surfaces (`gemini 2.5 flash`, `gemini-2.5-flash`,
> `gemini2.5flash` are one model). Corrected to distinct owners, it is 224 of
> 459, not 455. Recording the error because it is rule 7's exact shape: a real
> count answering a question nobody asked, and it survived a first reading.

**For the gate itself, a multi-model root is not a problem.** The subject gate
asks one question — does this thread name any tracked model — and a root naming
six answers yes as well as a root naming one. The cost lands downstream, on
what a kept document is worth, not on whether keeping it was right.

## 4 · The two arguments, and the one the restriction answers

Both are real. The recommendation in §5 exists because the second one has a
shape that a restriction can remove rather than trade against.

**For widening.** The evidence GitHub exists for is in comments — repro steps,
error strings, the correction two replies down. `assemble_issue.py` already
treats an issue plus its comments as one document for extraction (584 issues
hold both `issue_body_only` and `issue_with_comments` shapes today), so the
thread *is* the unit at the next stage. A triage gate reading a narrower unit
than the extractor is an inconsistency we chose by accident, not on purpose.

**Against.** Rule 8's direction is one-way: a check is promoted on measured
evidence, and the HN ruling's evidence was 511 comments in 2 threads with **no
HN corpus stored at all** to confirm it against. Extending it to 1,388 real
documents makes those two threads carry four times the weight they were measured
at. And the ~518 ambiguous-root documents are the population the original
inheritance refusal was about: *"32 of 53 candidates named a second model, and
the 21 survivors were all in two announcement threads."*

**And the objection is specifically about the ~518, not the 1,388** - which is
the observation §5 turns on. Every claim from an inherited-subject
document is already labelled — `judge/pipeline.py:subject_was_inherited` derives
it in code and `quote_subject_verdict` returns `QUOTE_NAMES_NOTHING`. So
widening cannot smuggle a resolution claim past the inheritance ruling; the
weighting decision on that label stays where it is. **What widening changes is
how many documents arrive carrying it: 0 today, ~1,388 after.** Whether
`QUOTE_NAMES_NOTHING`'s weight is right at that volume is the question, and it
is Engineer 2's.

## 5 · The recommendation, and why it is not a compromise

**Inherit only where the root resolves to exactly one model.** ~870 documents of
the 1,388, from the 231 unambiguous roots of 459.

The reason to prefer it is not that it is smaller. **It removes the objection
rather than splitting it.**

The objection to widening was never about volume. It was the population the
original inheritance refusal was measured on: *"32 of 53 candidates named a
second model, and the 21 survivors were all in two announcement threads."* The
complaint is **ambiguity of subject** - a document arriving with a subject that
could be any of several models, which is unusable at resolution and worse than
unusable at aggregation, because it corroborates whichever cell it lands in.

Restricting to single-model roots does not reduce that risk proportionally. **It
eliminates the class.** A document inheriting from a root that names exactly one
model has one candidate subject and nothing left to disambiguate - which is a
different situation from inheriting from a root naming six, not a smaller
amount of the same situation.

And 231 of 459 roots is a real population rather than a residue: half the issue
threads in this corpus are about one model, which is what you would expect of a
bug report. It is not a sliver held back to look cautious.

**It is also the shape this codebase already uses for exactly this problem.**
`out_of_window` declines to place a document when its matched surfaces resolve
to several models with disagreeing window flags - NOT_APPLICABLE rather than
picking one. This is that rule one stage earlier: where a thread's subject is
ambiguous, decline to inherit it rather than inherit an ambiguity.

### What it costs to implement

One predicate in `collect/triage/run.py`, where the root's surfaces are already
resolved: keep the inherited subject when the root's surfaces have exactly one
distinct owner, drop it otherwise. **Not an entry in
`SUBJECT_FROM_THREAD_ROOT`**, so `test_the_ruling_scope_is_hacker_news_alone`
still passes and the scope test does not have to be weakened to ship this.

Measurable the same way this was. The figure to expect is ~870 inherited rather
than 1,388, and I have not run that variant because the predicate does not
exist - I would rather it be ruled first than arrive with the number already
banked.

### The two answers I am not recommending

- **Hold.** Defensible, with a cost that has to be said on the page: GitHub
  keeps 38.6% and rule 4 means that cannot render as "engineers report little on
  GitHub". The drops are ours.
- **Widen unconditionally.** +1,050 kept, ~518 of them on an ambiguous root.
  This is the one the objection actually lands on, and I am not asking for it.

### What stays yours either way

Every claim from an inherited-subject document is labelled:
`judge/pipeline.py:subject_was_inherited` derives it in code and
`quote_subject_verdict` returns `QUOTE_NAMES_NOTHING`. Widening cannot smuggle a
resolution claim past the inheritance ruling. What it changes is how many
documents arrive carrying that label - 0 today, ~870 under this recommendation -
and whether that label's weight is right at that volume is Engineer 2's call.
This proposal does not touch it.

---

*Figures: `docs/measurements/triage-github-subject-counterfactual-2026-09-08.json`
and `docs/triage-first-run-2026-09-08.md` §4. Population: the 3,373 GitHub
documents readable on this host, of 3,382 stored — not a sample of GitHub.*
