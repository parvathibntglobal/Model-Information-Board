# NFR-11: derived publication

**Proposed 2026-09-17 by anooj + Claude. A REQUIREMENTS change. Proposed, not
taken.**

NFR-5 is scoped to the board (`nfr-5-stops-applying-to-derived-prose.md`). That
leaves the requirements table silent on what we now publish. This is the
requirement that fills it.

The per-source `publication` records are **the mechanism**. A mechanism is not a
requirement: it answers *may we publish from this source*, and there are things
that must be true of a derived post which no per-source flag can express.

---

## The requirement, in BUILD-PLAN's shape

```
| NFR-11 | DERIVED OUTPUT IS TRACEABLE, PERMITTED AT ITS SOURCES, AND CARRIES
          NOTHING TAKEN VERBATIM. Derived prose is the only thing published
          outside the board. It leaves no route back to a person, reproduces
          no source's words, and exists only where every source it rests on
          has been read and permitted.

          Accept: for any published derived post -
            1. its provenance record resolves to the document ids it rests on;
            2. every one of those documents' sources read
               `may_publish_from: true` on the date of publication, and
               `unread` refuses;
            3. no span of it appears in `flattened/` (the check rule 1 already
               runs, applied to the draft; the span length is measured, not
               chosen);
            4. no assertion in it rests on fewer than
               `min_independent_sources_per_published_claim` documents;
            5. no board surface is reproduced in it;
            6. the destination carries its own posting ruling;
            7. a tombstone on any cited document raises a retraction task
               within one nightly cycle.
          | E1 |
```

## What it must assert beyond the per-source flag, and why each is here

Your clause is (2), and it is the load-bearing one. These are the others, and
each is here because **no per-source flag can express it**.

### (1) Provenance — the one that makes the rest checkable

**Nothing else in this requirement can be evaluated without it.** A per-source
flag answers a question about a source; to ask that question you must first know
*which sources a post drew on*, and a derived post does not carry that by
construction. A person writes prose from what they read.

So the requirement is that **drafting records its own working**: every published
assertion maps to the document ids behind it. That is a process change, not a
code one, and it is the prerequisite for (2), (4) and (7) alike.

Without it, "every source reads `may_publish_from: true`" is a sentence nobody
can check — and an unverifiable clause in an acceptance criterion is the vacuous
test NFR-5 just got scoped to avoid.

### (3) Verbatim — global, because the per-source flag points the other way

`quotation_permitted` is per source and would, if `true`, permit a quote from
that source. Under this basis the answer is **no everywhere**, so the bar
belongs in the requirement and the per-source field is what a future ruling
would use to relax it for one source without reopening the basis.

The check is the operation rule 1 already runs — `p.quote in
thread.flattened_text`, plain Python, no model — applied to spans of the draft
instead of to a proposed quote. **The span length is a parameter and it is not
chosen here.** Too short and every common phrase trips; too long and a
paragraph passes. It should be measured against real drafts the way
`N_EFF_MINIMUM` was, and until it is, the check ships as a report (rule 8).

### (4) The source floor — a proxy for close paraphrase, and named as one

**Close paraphrase is what the verbatim bar does not catch**, and it is the
thing the bar exists to prevent: a post that follows one source's structure and
substance, changing the words, satisfies (3) completely.

There is no mechanical test for it. What there is, is a **proxy that is
checkable and that makes the bad case harder to reach**: an assertion resting on
one document is a paraphrase of that document; an assertion resting on several
is a synthesis. The existing publication definition already says *"an aggregate
over those words is not one"* and sets no floor, so a one-source "aggregate"
qualifies today.

**It is a proxy and the requirement should say so**, because a floor satisfied
is not close paraphrase absent — three sources can still be paraphrased one at a
time. The honest position is that (4) is checkable, (4) is not sufficient, and
the residue is a reviewer reading the draft. Writing that down is what stops the
floor being cited as though it settled the question.

### (5) The board surface — the seam no source flag can see

A screenshot of a board page publishes **quote and link** — the two things this
basis exists to keep in — and it does so without drawing on any source in a way
a per-source check would notice. The post's provenance record would be empty.
Every other clause passes.

It is stated here as well as in the basis conditions, deliberately: a reader
checking a draft against the acceptance criterion should not have to have found
the conditions block to know this is forbidden.

### (6) The destination ruling — the records describe sources, not targets

The per-source records describe **sources we read from**. Publishing *to* Reddit
is governed by Reddit's content policy and self-promotion rules — a different
document, binding on anyone who posts regardless of how they got their material.
Sixteen `may_publish_from: true` values would not make a post permissible on a
platform that forbids it.

This is the clause that catches the case the scoping rule misses: "RapidAPI-
routed, therefore out of scope" is about how we **read**.

### (7) Retraction — NFR-6's reach stops at the board, and this is where that shows

**NFR-6 promises that a tombstone makes a document's quotes vanish next run.**
That promise holds on the board, where the quotes are rows we control. It cannot
hold for a Reddit post somebody published last week.

So the requirement cannot be *derived output is retracted*, because we may not
be able to retract it. What it can be, and what (7) asserts, is that **a
tombstone raises a task naming the posts affected** — which is only possible
because of (1).

That is a weaker guarantee than NFR-6's and the difference should be visible in
the requirements table rather than discovered during a takedown. The same
applies when a source's `may_publish_from` goes from `true` to `false` — terms
change, and the rulings already carry `evidence_valid_days` because a ruling
made in August can be wrong in October.

## What NFR-11 deliberately does not assert

- **That derived output is accurate.** That is the board's problem and the
  extraction rules'. NFR-11 is about what may leave, not whether it is right.
- **That no person is named.** There is no check for it — we hold opaque
  platform ids for 8,631 of 9,497 authors — and the basis records that as a
  stated absence rather than a condition that would pass by construction. It
  remains a reviewer question, and (1) is what lets a reviewer answer it.
- **A cadence or volume bound.** Systematic republication reads differently from
  incidental use under several ToS shapes, but nobody has read those terms yet,
  so a number here would be invented.

## Owner

`E1`, matching NFR-5. The mechanism lives in `contract/sources.yaml`, which is
E1's, and the acceptance is a check over drafts against `flattened/`.

**Note this is the first NFR whose acceptance is not evaluable inside CI.** Every
other one can be tested against the system; this one needs a draft that exists
outside it. That is a real difference in kind and it argues for the provenance
record (1) being a stored artifact rather than a habit — a task somebody files,
not a note somebody keeps.
