# NFR-5 stops applying to derived prose, so it is scoped to the board

**Raised 2026-09-17 by anooj + Claude. A REQUIREMENTS change, written up as one.
Proposed, not taken.**

The `derived-publication-only` basis (`the-derived-publication-basis.md`) reads
as a contract change. It is a requirements change first, and this document
exists so it arrives as one rather than as a side effect of a basis rename.

---

## The requirement, as written

```
BUILD-PLAN.md:388

| NFR-5 | Official APIs and public feeds only · robots.txt · identifying
         User-Agent · no paywall circumvention · quote + attribution + link,
         never full text.
         Accept: per-source ToS reviewed and recorded; no page renders more
         than a bounded quote. | E1 |
```

NFR-5 carries two halves and only one of them survives the position change.

**The acquisition half survives unchanged.** Official APIs and public feeds,
robots.txt, an identifying User-Agent, no paywall circumvention — none of that
depends on what we publish. It governs how we collect, and we still collect.

**The publication half stops having a subject.**

## The acceptance criterion does not narrow or widen — it stops applying

> *Accept:* per-source ToS reviewed and recorded; **no page renders more than a
> bounded quote**.

That criterion is a **measurement over a rendered page**: find the quotes, check
none exceeds the bound. It is evaluable because the published artifact is
built *out of* quotes, so there is something to measure.

A derived post contains no quote. The criterion does not become stricter (it is
not "no quote at all") and it does not become looser (it is not "any length") —
**there is nothing on the page for it to range over.** Asked of a derived post,
"does this page render more than a bounded quote" has no true answer and no
false one. The test is vacuous, and a vacuous test **passes**.

That is the failure mode worth naming, because it is the one that will not
announce itself: NFR-5's acceptance would go on reporting green while the
requirement it encodes has nothing to say about what we now publish. Same shape
as `subscriptions_differ` never being able to fire, and as the near-miss flag
going silent exactly when both models were registered — **a check that cannot
fail is indistinguishable from one that keeps passing.**

The first half of the acceptance — *per-source ToS reviewed and recorded* —
does not become vacuous. It becomes **unmet**, everywhere, which is the honest
state and the subject of the per-source records in the basis proposal.

## The ruling: keep NFR-5 and scope it to the board

**Taken 2026-09-17: option 3.** NFR-5 stays, and its subject becomes *the
board*. The board still renders quote + attribution + link, still meets the
criterion, and the criterion stays evaluable because there is still something on
the page to measure.

**Derived prose is out of NFR-5's scope and is governed by the per-source
`publication` records** in `contract/sources.yaml` - `may_publish_from`,
`quotation_permitted` and `attribution`, with `unread` meaning do not publish.
See `the-derived-publication-basis.md` section 2.1.

### The acceptance criterion, with the scoping in it

The scoping has to be **in the criterion**, not in a note beside it, or it reads
as a bound on the project and a reader will check derived prose against it and
get a vacuous pass. Proposed replacement for `BUILD-PLAN.md:388`:

```
| NFR-5 | ACQUISITION, AND WHAT THE BOARD RENDERS.
         Official APIs and public feeds only - robots.txt - identifying
         User-Agent - no paywall circumvention.
         ON THE BOARD: quote + attribution + link, never full text.

         Accept: per-source ToS reviewed and recorded; NO BOARD PAGE renders
         more than a bounded quote.

         SCOPE: this requirement does not reach content published OUTSIDE the
         board. Derived prose is governed by the per-source `publication`
         records in contract/sources.yaml, where `unread` means do not
         publish. NFR-5 is not evidence about it IN EITHER DIRECTION. | E1 |
```

Three things that wording is doing:

- **"ON THE BOARD"** and **"NO BOARD PAGE"** make the subject explicit at both
  the rule and the acceptance, so neither can be read alone and generalised.
- **"in either direction"** is the important clause. Without it, *NFR-5 does not
  cover derived prose* reads to an optimist as *nothing forbids it* and to a
  pessimist as *NFR-5 forbids it*. It is neither: NFR-5 is silent, and silence
  is not evidence - which is this project's own repeated finding.
- Naming the per-source records **inside the requirement** means a reader who
  starts at NFR-5 arrives at the thing that does govern it, instead of
  concluding nothing does.

### What this ruling leaves open, stated rather than papered over

**Scoping NFR-5 to the board leaves the requirements table with nothing about
derived publication at all.** The per-source records are a *contract mechanism*;
an NFR is a *requirement with an acceptance criterion*. They answer different
questions - "may we publish from this source" versus "what must be true of what
we publish" - and only the first had a home.

**That gap is now filled: `nfr-11-derived-publication.md`.** It carries the
things no per-source flag can express - provenance, the verbatim bar, the source
floor that proxies for close paraphrase, the screenshot seam, a destination
ruling, and the retraction task that is as far as NFR-6's promise can reach
outside the board.

## Where the requirement is restated, and the count has moved twice

**The rule is stated in 24 places. Five are normative. Nineteen are not, and
nothing fails when any of the nineteen goes stale.**

> WARNING: **I have given two wrong counts for this and both were too low** -
> first five, then seventeen. Each correction came from widening the search, not
> from reading more carefully, which is the evidence for the point rather than
> an aside: **a rule restated everywhere and enforced nowhere cannot be found by
> knowing it is there.** The count below is from three passes - the canonical
> phrase, then `.sql` and `.jsx`, then five variant phrasings - and I would not
> assert it is complete either.

### Normative - 5. This proposal is the decision for one of them

```
BUILD-PLAN.md:388            NFR-5 and its acceptance criterion   <- rewritten above
CLAUDE.md:227                a stack decision, "do not relitigate"
contract/sources.yaml:216    blog-class-a-self-hosted, permitted use
contract/sources.yaml:376    blog-class-b-medium, its cost argument
contract/sources.yaml:1066   the blogs platform row
```

### Non-normative - 19, by where they live and who reads them

**In `contract/`, as SQL comments - 2.** Commentary in the schema, enforced by
nothing:

```
contract/tables.sql:270               -- never republished: published content is
contract/migrations/baseline.sql:242     quote + attribution + link.
```

Identical text in both, and the ruling for the two is **opposite**.

#### RULED: `tables.sql:270` is updated, `baseline.sql:242` is LEFT ALONE

`contract/tables.sql` is the live schema. Its comments describe the system as it
is, so a comment that has stopped being true is a defect there and gets the same
scoping as NFR-5.

`contract/migrations/baseline.sql` is **immutable by policy**. It records what
the schema *was* — it is applied once, its content hash is in
`schema_migration`, and `collect.migrate.content_hash` is checked against it.
Editing it would do two things, and both are wrong:

- **It would make a historical artifact assert something about today.** The
  baseline is evidence of a past state. A 2026-09 sentence inside it would be
  the migration claiming a posture that did not exist when it ran, which is
  precisely the class of value this project calls a placeholder wearing a
  decision's clothes.
- **It would break the hash**, and the ledger's mismatch is not a formality:
  CLAUDE.md's entry on resolving one is a page long, because a stored hash that
  matches no encoding of the file on disk is how a revised migration becomes a
  database nobody can reason about.

**So it stays, wrong, on purpose** — and this paragraph is the record of that,
so the next person who greps for the stale phrase and finds it in a migration
does not helpfully fix it. The line is not a statement about our posture. It is
a statement about a file that was applied once, and it is accurate as that.

**Lane instruction - 1.** Read by whoever works in `judge/`:

```
judge/CLAUDE.md:107   "But published content is quote + attribution + link, so a
                       document with no ..."
```

**Documentation - 9.** The ones the next person reads:

```
docs/logic-and-workflow.md:300   under a heading reading "Legal posture,
                                  non-negotiable"
docs/logic-and-workflow.md:310   "the storage/display split"
docs/how-it-works.md:801
docs/how-it-works.md:2678
docs/onboarding.md:50            what a new joiner is told on day one
docs/three-decisions-ruled-2026-09-08.md:88
docs/measurements/three-scopes-prompt-ceiling-capability.md:148
docs/proposals/reddit-sweep-contract.md:31
docs/unfiltered-sweep-design.md:290
```

`logic-and-workflow.md:300` and `onboarding.md:50` are the two that matter most
and neither is binding: one calls the form **non-negotiable**, the other is the
first thing a new engineer reads.

#### RULED: `logic-and-workflow.md:300` is amended, not left to drift

The line reads:

> **Legal posture, non-negotiable:** official APIs and public feeds only ·
> `robots.txt` respected · identifying User-Agent with a contact URL ·
> conservative rate limits · no paywall circumvention · **published content is
> quote + attribution + link, never full-text republication** · a source whose
> terms forbid this is dropped, not worked around.

**The heading is load-bearing, and that changes the ruling.** A superseded
sentence under an ordinary heading is out-of-date documentation. A superseded
sentence under **"Legal posture, non-negotiable"** reads as binding — it is the
one place in the docs that announces itself as a rule rather than a
description, so a reader who finds a conflict between it and a ruling will not
assume the ruling wins. It is worse than stale: it is stale and it claims
authority.

So it is amended, and the amendment carries the scope the way NFR-5's now does:

```
**Legal posture, non-negotiable:** official APIs and public feeds only ·
`robots.txt` respected · identifying User-Agent with a contact URL ·
conservative rate limits · no paywall circumvention · **on the board,
published content is quote + attribution + link, never full-text
republication** · **derived prose published outside the board is governed by
NFR-11 and the per-source `publication` records, not by this line** · a source
whose terms forbid this is dropped, not worked around.
```

Everything else on that line survives untouched — it is the acquisition
posture, and acquisition did not change. Only the publication clause is scoped,
and the pointer is added so a reader who stops here is sent to the thing that
does govern derived output instead of concluding this line covers it.

**`onboarding.md:50` follows the same ruling for the same reason**, one level
softer: it is not headed non-negotiable, but it is what a new engineer reads on
day one, and a joiner who learns the old form learns it as the rule.

**Fixture READMEs - 3.** Each explains why a fixture is shaped as it is:

```
fixtures/blog/README.md:15
fixtures/github/README.md:13
fixtures/reddit/README.md:13
```

**A test - 1.** A docstring, so it asserts nothing:

```
tests/test_sieve_locality.py:20   "thing NFR-5 exists to prevent - quote,
                                   attribution and link, never full text."
```

**An article - 1.** Published output describing our own posture:

```
articles/deepseek-v4-pro/independent-blogs-report.md:353   "never republished."
```

**Code - 2, and this is the one that will outlive the rest:**

```
scripts/labelling_pools.py:141    prose: "bounded snippet and the permalink, so
                                   the pools stay inside the same rule the ..."
scripts/labelling_pools.py:1016   "content_rule": "bounded snippet plus
                                   permalink, never full text"
```

**`:1016` is a string in an exported payload.** It enforces nothing, it ships in
an artifact somebody else reads, and - the part that matters - **it does not
contain the canonical phrase.** A sweep for `quote + attribution + link` finds
none of `labelling_pools.py`, `test_sieve_locality.py` or
`unfiltered-sweep-design.md`. It says *"bounded snippet plus permalink"*, which
is the same rule in different words, and different words are exactly what a grep
cannot follow.

So it will go stale silently and then travel: an export carrying a
`content_rule` that describes a posture we no longer hold, read by whoever
receives the pool rather than by anybody who would recognise it as out of date.

## It relitigates a decision CLAUDE.md lists as settled

```
CLAUDE.md, "Stack decisions already made - do not relitigate"
  - Published content is *quote + attribution + link*, never full text.
```

**The position change relitigates that line, and that is legitimate.** A
"do not relitigate" list records decisions taken so they are not re-argued by
whoever finds them inconvenient in month four; it is not a claim that the
project's purpose can never change. What it does require is that a change to one
of its entries is **a decision somebody takes on the record**, not a consequence
that falls out of a different decision.

Ratifying a new basis without ruling on this line would do exactly that: the
basis would be the record, and the stack decision would quietly stop being true
with nothing pointing at it. That is how the entry would go stale in the way
CLAUDE.md's own `assert_no_fixtures` entry describes — *"a claim about wiring
goes stale silently, so this entry is the one to re-check rather than
re-read."*

## What is asked

1. **Ratify the NFR-5 rewrite above** - keep it, scope it to the board, name the
   per-source records inside the criterion, and keep the "in either direction"
   clause.
2. **Rule on the CLAUDE.md:227 line explicitly** - amend it, scope it to the
   board as NFR-5 now is, or strike it. Not by implication.
3. **Ratify NFR-11** (`nfr-11-derived-publication.md`), which fills the gap
   scoping NFR-5 leaves. Its acceptance has two parameters that are
   deliberately unset: the verbatim span length, and
   `min_independent_sources_per_published_claim`. Both should be measured.
4. **Ratify the two rulings above** - `logic-and-workflow.md:300` amended with
   its scope, `contract/migrations/baseline.sql:242` left alone with the reason
   recorded here so nobody fixes it.
5. **Decide who updates the remaining seventeen, and when.**
   `scripts/labelling_pools.py:1016` first, because it is the only one that
   leaves the repository.

**Not proposed:** any edit to `BUILD-PLAN.md`, `CLAUDE.md`, `contract/`, any
documentation or any code. Nothing here has been implemented.
