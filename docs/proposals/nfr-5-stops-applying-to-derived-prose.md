# NFR-5 does not narrow or widen for derived prose — it stops applying

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

## Where the requirement is restated, and what has to move

The phrase `quote + attribution + link` appears **17 times**. It is not one line
to change:

### Normative — binding, and the ones that need a decision

```
BUILD-PLAN.md:388            NFR-5 itself, with its acceptance criterion
CLAUDE.md:227                a stack decision, listed under "do not relitigate"
contract/sources.yaml:216    blog-class-a-self-hosted, its permitted use
contract/sources.yaml:376    blog-class-b-medium, its entire cost argument
contract/sources.yaml:1066   the blogs platform row
```

### Lane instruction — read by whoever works in that lane

```
judge/CLAUDE.md:107          "published content is quote + attribution + link,
                              so a document with no …"
```

### Documentation — 8 places, which drift silently if the first five move

```
docs/how-it-works.md:801, :2678
docs/logic-and-workflow.md:300, :310
docs/onboarding.md:50
docs/three-decisions-ruled-2026-09-08.md:88
docs/measurements/three-scopes-prompt-ceiling-capability.md:148
docs/proposals/reddit-sweep-contract.md:31
```

`docs/logic-and-workflow.md:300` is the one to notice: it states the form as
part of a paragraph headed **"Legal posture, non-negotiable."**

### Fixture READMEs — 3, each explaining to a future reader why a fixture is shaped as it is

```
fixtures/blog/README.md:15
fixtures/github/README.md:13
fixtures/reddit/README.md:13
```

### And one in code

```
scripts/labelling_pools.py:1016
    "content_rule": "bounded snippet plus permalink, never full text"
```

A different phrasing of the same rule, carried as a **string in an export**. It
does not enforce anything, which is why it is easy to miss and why it will
outlive the change if nobody goes looking.

**A correction to my own earlier report**: I said five places. Five are
*normative*; seventeen state the rule. The distinction matters for a requirements
change, because the twelve non-normative ones are where a stale rule survives
longest — nothing fails when they go out of date.

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

1. **Rule on NFR-5.** Three options, and this proposal does not pick one:
   - **split it** — NFR-5 keeps the acquisition half, and a new NFR covers
     publication under the derived basis, with an acceptance criterion that can
     actually be evaluated against prose;
   - **rewrite it** in place, and say so in its row;
   - **keep it and scope it** — NFR-5 governs *the board*, which still renders
     quote + attribution + link and still meets it, and derived output is out of
     its scope entirely. **This may well be the right answer**, and it is the
     only one under which the existing acceptance criterion stays meaningful.
2. **Rule on the CLAUDE.md line explicitly** — amend it, scope it to the board,
   or strike it. Not by implication.
3. **Decide who updates the other twelve**, and when. They are not binding and
   they are what the next person reads.

**Not proposed:** any edit to `BUILD-PLAN.md`, `CLAUDE.md`, `contract/` or any
documentation. Nothing here has been implemented.
