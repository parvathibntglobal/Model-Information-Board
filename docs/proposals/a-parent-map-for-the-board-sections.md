# Propose: a parent map for the board sections, at read time, in its own contract file

*Engineer 1 · 2026-09-23 · measured against the shared staging database at 06:40Z*

**Proposing a new file, `contract/slug_parents.yaml`, and NOT an edit to
`contract/capabilities.yaml`.** The two are different vocabularies serving
different renderers, and conflating them is the failure mode this document
spends most of its length guarding against.

Nothing here is built. `contract/` is proposed and reviewed, never taken solo.

---

## 1 · The shape, measured

```
board_entry   1,528 entries   393 distinct slugs   3 sections
```

⚠ **Every count below is a record with a time on it, not a claim about now**
(rule 11). It moved while this document was being written — see §10, which
is the shortest argument in here for one of the rulings.

| section | entries | slugs | entries/slug | largest |
|---|---:|---:|---:|---|
| capability | 712 | 198 | 3.60 | `instruction-following` (81) |
| metric | 534 | 136 | 3.93 | `cost-per-token` (167) |
| best_for | 282 | 77 | 3.66 | `coding-agent` (142) |

**Slugs held by entry count:**

| section | =1 | =2 | 3–4 | 5–9 | 10+ | slugs |
|---|---:|---:|---:|---:|---:|---:|
| capability | **116** | 36 | 22 | 15 | 9 | 198 |
| metric | **84** | 25 | 15 | 7 | 5 | 136 |
| best_for | **56** | 8 | 6 | 4 | 3 | 77 |

59% / 62% / 73% of slugs hold exactly one entry, and those hold only
16% / 16% / 20% of entries. **Grouping the tail removes most of the headings
and moves almost none of the evidence.** That asymmetry is the case for doing
this at all.

The number that matters more is models, not entries:

```
capability   150 of 198 slugs carry ONE model   (75.8%)
metric        97 of 136                          (71.3%)
best_for      64 of  77                          (83.1%)
```

Three quarters of every section is a heading about a single model. That is
rule 4's problem rather than a tidiness problem: a one-model heading renders
as a statement about a capability when it is a statement about one post.

### The spelling half is already done

Folding separators mechanically across all 1,528 entries — rule 10's
`spelling_key`, the half that is *"a judgement about nothing"* — finds three
collisions in the entire corpus:

```
capability   over-thinking(1) + overthinking(1)
metric       exploit-bench(1) + exploitbench(4)
metric       exploit-gym(2)   + exploitgym(2)
```

**Three slugs, eleven entries.** Whatever this proposal is for, it is not
spelling. The problem is meaning, which rule 10 assigns to a person.

---

## 2 · ⚠ Which surface. This is the part a proposal gets silently wrong

**There are two vocabularies on this board and they are not connected.**

```
capability_key   closed at 12    ->  315 cells  ->  n_eff, consensus phrases,
                                                    judge/pages/capability.py
slug             open at 393     ->  1,528 board entries  ->  board sections,
                                                             navigation
```

Verified in code, not assumed:

- `judge/pages/capability.py:123` builds from `capability_key`, and at `:125`
  **refuses a key not in `contract/capabilities.yaml`**. It never reads `slug`.
- `n_eff` does not reference `slug` anywhere in the tree. Consensus arithmetic
  runs on `cell`, which is keyed `(model_version_id, capability_key,
  condition_bucket)`.
- The only writers of `board_entry.slug` semantics are the extractor and the
  `ruling` / `ruling_target` overlay in `judge/app.py`.

**So this file touches the 393-slug board sections and touches nothing on the
12-key capability page.** A parent map cannot corrupt consensus arithmetic,
because slugs never fed it.

That is a stronger argument for read-time grouping than the usual one, and it
is also the sentence most likely to be assumed rather than checked by whoever
implements this. **If a reviewer reads only one section of this document, this
is the one.**

---

## 3 · The three rulings, written into the file rather than described near it

### Ruling 1 — a parent carries a count of LEAVES, never a count of VOICES

The `coding` parent would show 93 entries across 22 models. Those are 12
leaves whose **median is one model**:

```
code-generation             55 entries   17 models
code-review                 18            7
coding                       3            2
code-fixing                  3            2
code-quality                 3            3
test-generation              2            1
debugging                    2            1
frontend-code-generation     2            1
code-editing-diff-fidelity   2            2
repository-level-coding      1            1
surgical-fixes               1            1
long-refactors               1            1
PARENT (union)              93 entries   22 models
```

Rendering *"93 reports on coding"* is a figure about a category no writer
named, assembled from leaves that individually say very little. That is
rule 3's shape and rule 4's at once — a reader cannot tell a well-evidenced
parent from twelve thin leaves stacked.

**Proposed mechanically, not by convention:** the file's schema has no field
for a voice count, and a test refuses any key matching `voices|n_eff|weight|
score|consensus`. A parent that cannot express a voice count cannot publish
one by accident.

### Ruling 2 — no catch-all name

`extraction.faithfulness` is the worked example and it is not hypothetical:
one document produced **12 claims, all 12 keyed `extraction.faithfulness`, all
12 positive, and zero `capability_candidate` proposals** — every one of them
about facial recognition. The escape hatch was open and unused, because
nothing felt wrong. Five of 21 `extraction.faithfulness` cells are now sourced
*entirely* from facial-recognition or vision quotes, each rendering *"One
person mentioned extraction — not yet corroborated"* about a model for which
nobody mentioned extraction.

**A container wide enough to take anything does not announce itself. It fills
up and reads as evidence.**

The shape already exists at the leaf, and these are live slugs today:

```
capability   quality(1)  reliability(1)  consistency(1)  judgment(1)
             output-quality(1)  generation-quality(2)  synthesis(1)  research(1)
best_for     general-purpose(3)  general-purpose-chat(1)
metric       score(1)  other(1)  accuracy(2)  task-completion(1)
```

**Every one is a singleton or near it, and that is the only reason they are
harmless.** A parent taxonomy promotes exactly this vocabulary from leaf to
container, where it would fill within a run.

**Proposed mechanically:** a denylist in the file, tested. `general`,
`general-purpose`, `general-intelligence`, `overall`, `misc`, `other`,
`quality`, `capabilities`. And a second test: **no parent name may equal any
existing leaf slug**, so a parent cannot quietly become a leaf that also
collects.

### Ruling 3 — parents never rewrite leaves

The leaf row keeps its own `slug`, `quote`, `claim_id` and `document_id`. The
parent is an overlay read at render time.

**This was demonstrated rather than asserted, two hours before this document.**
`ruling='merged'` had been used four times in the life of the board, and the
AIME one was backwards — the two rows carrying the complete name `aime-2026`
were folded into the truncation `aime`. Repairing it (#406) was three rows and
one field, because no slug had been rewritten. Had the merge rewritten leaves,
the complete names would have been gone and the quotes would have been the only
way back.

**Proposed mechanically:** the file maps `leaf -> parent` and has no field that
could name a replacement slug. `normalise_slug`'s existing refusal to fold
`tool-calling` into `function-calling` stays exactly as it is — a parent is not
a fold, and the day someone implements parents by rewriting leaf slugs, rule 10
has been broken.

### The property all three rest on, and it is the one to state

@parvathibntglobal's words, reviewing this, and it belongs in the file rather
than in a review thread:

> **A parent groups for reading and never implies the leaves are the same
> measurement.**

That sentence is what makes the three rulings above coherent rather than three
separate prohibitions, and it is what makes **a wrong member list cheap**:

> if it holds, a wrong member list costs a reader one click rather than costing
> the board a wrong number.

It answers §9's first question — the member lists cannot be reviewed by reading,
and two readers agreeing is not validation because *"two people with the same
priors are one prior."* The property is reviewable where the list is not, and
the test she gives is concrete: **does a parent ever put two slugs together that
a quote proves are different things?**

Under it, `osworld-verified` beside `osworld-2` is fine and `arc-agi` beside
`arc-agi-3` is fine — **because the parent is not a merge.** Those are four
different measurements filed adjacently, which is what a reader needs in order
to notice that three of them are one benchmark and one is not (#407).

So it goes in the file's header as the sentence the three constraints serve.

---

## 4 · The proposed map

### capability — 8 parents, 179 of 198 slugs, 569 of 712 entries

| parent | slugs | entries | singletons absorbed |
|---|---:|---:|---:|
| coding | 29 | 120 | 17 |
| reasoning | 16 | 108 | 7 |
| agentic | 17 | 81 | 8 |
| vision-media | 18 | 67 | 13 |
| performance-cost | 22 | 51 | 12 |
| reliability-safety | 33 | 48 | 25 |
| security | 20 | 47 | 8 |
| writing-language | 24 | 47 | 14 |
| **(ungrouped)** | **19** | **143** | 12 |

### metric — 6 parents, 116 of 136 slugs, 504 of 534 entries

| parent | slugs | entries | singletons |
|---|---:|---:|---:|
| price | 14 | 191 | 8 |
| benchmark | 63 | 131 | 43 |
| speed-latency | 11 | 80 | 6 |
| capacity-spec | 5 | 51 | 2 |
| token-usage | 10 | 29 | 4 |
| reliability-rate | 13 | 22 | 8 |
| **(ungrouped)** | **20** | **30** | 13 |

### best_for — 5 parents, all 77 slugs, all 282 entries

| parent | slugs | entries | singletons |
|---|---:|---:|---:|
| coding | 21 | 178 | 15 |
| text-knowledge | 20 | 59 | 12 |
| domain | 15 | 21 | 10 |
| media | 10 | 13 | 8 |
| agents-automation | 11 | 11 | **11** |

`agents-automation` is eleven slugs and eleven entries — every member a
singleton. It is the clearest single illustration of what this file is for.

---

## 5 · The 19 stay ungrouped, and so do the 20

**`instruction-following` (81) and `long-context` (32) do not fit any parent,
and they are the two largest capability slugs.** Together with 17 others they
carry **143 entries — more than any proposed parent.**

```
automated-ai-rd · biology-classification · biology-discussion · chip-design
discovery-in-games · explainable-recommendations · game-economy-management
incident-analysis · instruction-following · investigation-breadth
investigation-depth · long-context · medical-knowledge · research
scientific-replication · steerable-recommendations · structured-output
synthesis · tool-free-recommendation
```

Metric has 20 of its own, mostly security outcome counts (`exploit-count`,
`cve-exploitation-rate`, `network-compromise-rate`, `poc-success-rate`).

**They stay ungrouped, and the file must be able to say so.** Forcing
`instruction-following` under a parent to complete the taxonomy is the forcing
defect one layer up — the same move that produced *"pick the closest key and
move on"* and, with it, 63% of claims whose key does not name what the quote
describes. **A taxonomy that covers everything is a taxonomy that has forced
something.**

So `ungrouped` is the default and requires no entry. A slug absent from this
file renders at the top level beside the parents, not under a residual
heading. There is deliberately no `other` parent — see ruling 2.

---

## 6 · The proposed file

```yaml
# contract/slug_parents.yaml
#
# A READ-TIME grouping of `board_entry.slug` for navigation. Nothing here is a
# counting unit and nothing here rewrites a leaf.
#
# ⚠ THIS IS NOT `capabilities.yaml`. That file is the CLOSED, 12-key counting
#   vocabulary: it keys `cell`, it drives `n_eff`, and `judge/pages/capability.py`
#   refuses a key it does not contain. This file keys NOTHING. It maps the open
#   393-slug display vocabulary onto headings, and the capability page never
#   reads it.
#
# THE PROPERTY THIS FILE EXISTS TO HOLD, AND THE ONE TO CHECK A CHANGE AGAINST:
#
#     A PARENT GROUPS FOR READING AND NEVER IMPLIES THE LEAVES ARE THE SAME
#     MEASUREMENT.
#
#   It is why a wrong member list is cheap - it costs a reader one click, not
#   the board a wrong number - and it is the only part of this file reviewable
#   by reading, since the member lists are 292 slugs of one reader's judgement.
#   The check it licenses: DOES A PARENT PUT TWO SLUGS TOGETHER THAT A QUOTE
#   PROVES ARE DIFFERENT THINGS? `osworld-verified` beside `osworld-2` passes,
#   because the parent is not a merge and filing them adjacently is how a
#   reader notices three of the four are one benchmark (#407).
#
# THREE CONSTRAINTS SERVING IT, EACH WITH A TEST RATHER THAN A CONVENTION:
#   1. no voice counts   - this schema has no field for one, and a test refuses
#                          any key matching voices|n_eff|weight|score|consensus.
#   2. no catch-all      - `forbidden_parents` below, tested; and no parent name
#                          may equal an existing leaf slug.
#   3. no rewriting      - leaf -> parent only. There is no field that could
#                          name a replacement slug. `normalise_slug` still
#                          refuses synonym folds; a parent is not a fold.
#
# A slug absent from this file is UNGROUPED and renders at the top level.
# Absence is the default and is not a defect (rule 6): 19 capability slugs and
# 20 metric slugs are deliberately ungrouped, including the two largest
# capability slugs, and forcing them under a parent is the defect this file
# exists downstream of.

version: 1
reviewed_on: 2026-09-23
reviewed_by: PROPOSED - NOT YET REVIEWED

forbidden_parents:
  - general
  - general-purpose
  - general-intelligence
  - overall
  - misc
  - other
  - quality
  - capabilities

sections:
  capability:
    coding: [code-generation, code-review, code-quality, coding, code-fixing,
      code-editing-diff-fidelity, frontend-code-generation, debugging,
      test-generation, code-completeness, code-convention-adherence,
      code-regression, repository-level-coding, repository-level-editing,
      long-refactors, surgical-fixes, sql-generation, ui-generation,
      software-architecture, design-planning, design-review, adversarial-review,
      no-code-generation, api-migration, automated-patching, n-plus-one-detection,
      gpu-compiler-writing, development-speed, architectural-reasoning]
    reasoning: [reasoning, mathematical-reasoning, spatial-reasoning,
      long-horizon-reasoning, persistent-reasoning, no-cot-reasoning,
      cot-controllability, reasoning-effort, proof-writing, serial-arithmetic,
      letter-counting, over-thinking, overthinking, overcomplication,
      chain-of-thought-monitorability, chain-of-thought-monitoring]
    # …agentic, vision-media, performance-cost, reliability-safety, security,
    #   writing-language as measured in §4; full lists in the implementing PR.
  metric:
    price: [cost-per-token, cost-per-task, cost-per-character, ...]
    # …benchmark, speed-latency, capacity-spec, token-usage, reliability-rate
  best_for:
    coding: [coding-agent, code-review, code-generation, ...]
    # …text-knowledge, domain, media, agents-automation
```

The member lists are abbreviated here on purpose — they are 292 slugs and the
argument is not in them. They are reproducible from the measurement script and
would ship complete in the implementing PR.

---

## 7 · What I would argue against in my own proposal

**`benchmark` is the parent closest to the shape ruling 2 forbids.** 63 slugs,
131 entries, 43 of them singletons. It is very wide.

I still propose it, for a reason that is specific rather than a preference:
**a benchmark leaf is verifiable against its own quote and a capability leaf is
not.** `'Terminal-bench 4.0'` is a string in the text; no document says
"coding". So a wrong benchmark leaf is detectable — that is exactly what
`axis_verbatim` and `axis_quoted` were added for — while a wrong capability
leaf can only be argued about. The catch-all risk is real and it is the one
place where a mechanism already exists to catch it.

**⚠ And grouping benchmarks makes the #368 class MORE visible, not less.**
@parvathibntglobal's point on review, and it is close to the opposite of the
worry I raise below:

> `osworld`, `osworld-2`, `osworld-2-0` and `osworld-verified` are four slugs,
> three of them one benchmark, and **only the quotes can tell you which**. A
> `benchmark` parent would at least put them adjacent for the person who has to
> read them.

**Both are true, of different failure modes**, and naming which is which is the
useful part:

| | what it looks like | what a parent does |
|---|---|---|
| **dispersion** — one benchmark scattered across several slugs | `osworld` · `osworld-2` · `osworld-2-0` · `osworld-verified` | **surfaces it.** Four headings become four adjacent rows under one parent, and the reader who has to rule on them sees all four at once instead of in four places |
| **over-merge** — one slug holding several benchmarks | `swe-bench`, 39 rows naming nine different measurements | **does nothing, and looks tidier for it.** The defect is inside a single leaf; a heading above it adds an organised-looking layer over an unorganised leaf |

So the file helps with exactly half of #368 and the half it helps with is the
half nobody had a surface for. It is not a reason to expect it to help with the
other half, which is the next paragraph.

**And `swe-bench` is the over-merge half: a problem this file does not solve
and might hide.** It
holds 39 rows whose quotes name OSWorld-2.0, Terminal-Bench 4.0,
AutomationBench, CursorBench 3.2.0, DeepSWE v1.1, SWE-Bench Pro and SWE-bench
Verified — nine different measurements under one slug (#368). Putting it under
a `benchmark` parent makes the section tidier and the defect no less live.
**Grouping is orthogonal to correctness and must not be sold as a fix for it.**

**The 63% is untouched.** `text-to-speech-japanese` keyed `code.generation` is
wrong under any parent. Nothing in this file repairs a leaf.

---

## 8 · Not proposed

- **No edit to `capabilities.yaml`.** Different vocabulary, different renderer.
- **No new `ruling` value.** `merged` already exists and already works this
  way; a parent map is the standing version of what a reviewer does one slug
  at a time.
- **No write-time parenting.** The extractor is not asked to pick a parent.
  A parent cannot be verified against the text — no document says "coding" —
  so it can only be chosen, and a forced choice from a closed list is the
  defect measured at 63%. A parent taxonomy applied at write time is that
  defect one layer up.
- **No `other` parent and no residual bucket.** See §5.
- **No deletion of any slug**, including the 116 capability singletons. A
  one-entry slug is thin evidence, not absent evidence, and rule 4 wants the
  difference visible.

## 9 · What review should push on

1. **Are the member lists right?** They are one reader's judgement over 292
   slugs and nobody has checked them. The measurement is reproducible; the
   clustering is not a measurement.
2. ~~**Is `benchmark` acceptable, given §7?**~~ **ANSWERED on review: yes**, on
   the reason given, and #407 strengthens rather than weakens it. §7 now
   carries the visibility half.
3. ~~**Does `best_for` even need parents?**~~ **ANSWERED on review: no, and
   parents would make it worse.** One slug is half the section and the other 76
   have a median of one entry, so a parent map there groups a long tail nobody
   reads and leaves the actual defect untouched. **`best_for` wants
   `coding-agent` split, not a tier above it.** That is a leaf repair, out of
   scope here, and filed as **#412** — the scoping was hers and it is right.

   ⚠ **This changes the proposal**: `best_for` parents are now proposed as
   **deferred, not adopted**, pending that split. The capability and metric maps
   stand. Adding five parents over a section whose real problem is one
   50%-share leaf would be the tidiness-mistaken-for-a-fix that §7 warns about,
   one section over.
4. **Should the file carry the leaf counts** as a dated record, per rule 11?
   My inclination is **no** — a count in a config file rots exactly the way
   rule 11 describes, and the count is recomputable from `board_entry` at any
   time. Recording the date of the clustering is enough.


---

## 10 · ⚠ This document went stale while it was being written

The first measurement was taken at **05:55Z** and said `capability 710 entries`.
The script was re-run at **06:40Z** and said **712** — `agentic` moved 79 to 81.
Forty-five minutes.

**It moved again while the PR sat.** @parvathibntglobal read **716** on review,
and a re-run here confirms it:

```
05:55Z   capability 710
06:40Z   capability 712      +2   while this document was being written
06:42Z   capability 716      +4   while the PR sat, unreviewed, for two minutes
```

`metric` moved further in the same window — 534 to **563**. Three readings,
three answers, and nobody did anything wrong.

Two other machines were extracting into staging in that window:

```
LenovoPB          49 extract calls   05:05Z - 05:32Z
LAPTOP-TA28DHTF   17 extract calls   06:02Z - 06:09Z
22 new board_entry rows              05:04Z - 06:09Z
```

Nothing went wrong. **The point is that nothing had to.** This is `#384`'s class
arriving inside a document that argues about `#384`'s class, and the fastest
recorded instance on this board was thirty-five minutes — so forty-five is not
unusual, it is ordinary.

**It settles question 4 in §9.** I asked whether `contract/slug_parents.yaml`
should carry the leaf counts as a dated record. The answer is **no**, and not on
taste: a count in that file would be wrong by the next extraction run, and a
reviewer opening it to decide whether a parent is still justified would be
reading the state of the board on the afternoon somebody typed it. The counts
belong where they can be recomputed — this script — and the file carries only
the date the **clustering** was made, which is a judgement and does not rot the
same way.

It also sharpens **ruling 1**. If a *config file* cannot safely hold a count for
forty-five minutes, a *rendered page* certainly cannot hold a synthesised voice
count for a category no writer named. The parent shows leaves; the leaves show
their own evidence; both are computed at read time against whatever the board
holds at that moment.
