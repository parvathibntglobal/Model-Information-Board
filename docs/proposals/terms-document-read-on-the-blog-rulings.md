# Proposal: `terms_document_read` on the two blog rulings, in a field rather than a sentence

**Proposed 2026-09-17 by anooj + Claude. `contract/` needs two eyes — this is
proposed, not taken.**

---

## The problem, stated precisely

Both blog rulings state in prose that no terms page has been read.
`blog-class-a-self-hosted`, in its summary:

> NO TERMS PAGE HAS BEEN READ FOR ANY OF THE NINE FEEDS.

`blog-class-b-medium`, in its summary:

> TERMS REVIEW IS DEFERRED HERE TOO … Medium's terms of service have not been
> read.

Neither records it as a fact. Their `recorded_evidence` blocks are:

```
blog-class-a-self-hosted   article_path_allowed, paywall_observed, login_required
blog-class-b-medium        feed_carries_full_text, article_fetch_refused, login_required
```

Both blocks record what was *observed mechanically*. Neither records the one
thing both summaries go out of their way to say.

The five platform rulings record the same fact properly, in both halves — the
ruling's `recorded_evidence` **and** each source's own `terms_evidence`:

```
                 ruling.recorded_evidence   source.terms_evidence
arxiv                     [false]                   present
x                         [false]                   present
devto                     [false]                   present
hackernews                [false]                   present
huggingface               [false]                   present
─────────────────────────────────────────────────────────────────
9 blog feeds              ABSENT                    ABSENT  (0 of 9)
```

So a machine check over `recorded_evidence` reads the blog feeds as **absent**
where the platform sources read as **false**. That is rule 6 inside the
contract: a fact that was established and written down in prose is, to every
reader that is not a person, missing. And rule 6's cost is the usual one —
absent and false are different, and only one of them is what we know.

It is the same declare-versus-enforce shape as the eight-declare-three-enforce
`use_basis` gap, which `_ruling_from` now raises on at load time.

---

## What is proposed

**One key, on two rulings, carrying the value the prose already states.** No
new fact, no re-reading of anything, no change of position:

```yaml
# blog-class-a-self-hosted
recorded_evidence:
  article_path_allowed: [true]
  paywall_observed: [false]
  login_required: [false]
  terms_document_read: [false]      # ← the summary already says this

# blog-class-b-medium
recorded_evidence:
  feed_carries_full_text: [true]
  article_fetch_refused: [true]
  login_required: [false]
  terms_document_read: [false]      # ← the summary already says this
```

---

## ⚠ IT IS NOT A ONE-LINE CHANGE, AND THE ONE-LINE VERSION REFUSES ALL NINE FEEDS

`recorded_evidence` is **not** a passive record. `assert_terms_reviewed` feeds
it to `_check_facts` ([collect/registry/assertions.py:267](../../collect/registry/assertions.py#L267)),
which requires every key the ruling names to be present in each *source's*
`terms_evidence`:

> ruling {ruling} conditions on {key}, which this source's `terms_evidence`
> does not record. Absent is not acceptable (rule 6) — measure it.

**Measured, not reasoned.** Loading `contract/sources.yaml` with the ruling key
added and nothing else, against `assert_terms_reviewed` at `today=2026-09-17`:

```
A · as-is                        PASSES
B · ruling key ONLY              REFUSED — 9 of 9 feeds, recorded-evidence-missing
C · ruling key + all 9 feeds     PASSES
```

So the change is **paired or it is a harvest outage**:

1. `terms_document_read: [false]` on both rulings, and
2. `terms_document_read: false` in the `terms_evidence` of **all nine feed
   rows** — the seven class A and the two class B.

Adding (1) without (2) stops every blog feed at the NFR-5 gate. That is the
gate working correctly; it is still an outage, and it is the reason this is a
proposal with a measurement in it rather than a one-line PR.

---

## Should anything enforce it?

**Yes, and the precedent is exact.** `_ruling_from` already raises at load time
on a ruling that names a `basis` and does not enforce it, with this reasoning:

> Raised at LOAD time rather than checked in a test, because the next ruling
> somebody adds is the one that reopens the gap, and a test only fails after it
> is written.

That reasoning transfers without modification. A rule that lives only in review
habit is the rule that the sixth ruling — Substack — quietly skips.

**The proposed check, and its limit stated honestly.** No check can tell whether
a terms document was *actually* read. What a loader check *can* enforce is that
a ruling **answers the question in a field**:

```
A ruling whose summary states a terms position must carry
`terms_document_read` in `recorded_evidence`. Absent is refused;
`[true]` and `[false]` are both accepted.
```

It enforces *recorded*, never *read* — the same standing as `use_basis`, which
checks that a basis is wired to a precondition and cannot check that the basis
is true.

**Two candidate trigger conditions, and I recommend the second:**

| trigger | catches | cost |
|---|---|---|
| grep the summary for terms language | today's two, by their prose | a string match on prose; brittle, and a ruling that says nothing escapes |
| **require the key on every ruling with a `recorded_evidence` block** | every ruling that records anything at all | `blog-umbrella-not-a-fetch-target` and `reddit` need a considered value |

The second is the `use_basis` shape: unconditional, no prose parsing, and it
fails the *next* ruling rather than only the two we just looked at.

**It needs two decisions before it can be written**, which is why this proposal
stops here rather than shipping a check:

- **`reddit`** has no ruling at all — deliberately, and rule 6 protects that.
  A loader check must not turn the one honestly-unreviewed row into a refusal.
- **`blog-umbrella-not-a-fetch-target`** is not a fetch target, so "has anyone
  read the terms" has no meaningful answer. Its `recorded_evidence` is `{}`
  today, so the second trigger would leave it untouched — but that is an
  accident of it recording nothing, not a considered exemption, and it should
  be made explicit either way.

---

## Rule 9: what would read this

**Today: one test, and no production code.**
`tests/test_arxiv_and_x_terms_gate.py:194` asserts
`recorded_evidence["terms_document_read"] == [False]` for arXiv and X. Nothing
in `collect/` or `judge/` branches on the value.

Adding it to two more rulings therefore adds a recorded fact with **no new
reader**, and rule 9 says to say so rather than leave it. It is not unconsumed,
though: `_check_facts` consumes the *key* — it forces all nine feeds to record
an answer, and refuses the source if they do not. **The key is enforced even
where the value is not yet branched on**, which is a stronger position than the
prose has today and is the whole point of the change.

---

## What this does not do

- It does not read anybody's terms, or change our position on any host.
- It does not touch `fetch_articles`, the class A/B split, or any per-feed
  measurement.
- It does not make the blog rulings safer. It makes them **legible to a
  machine**, which is the gap.

---

## The decision asked for

1. Take the paired change — two rulings, nine feed rows — or reject it.
2. Rule on whether the loader check is written, and if so which trigger, plus
   the `reddit` and `blogs` exemptions above.
