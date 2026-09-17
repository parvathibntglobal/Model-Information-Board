# A basis for derived publication: `derived-publication-only`

**Proposed 2026-09-17 by anooj + Claude. `contract/` — proposed, not taken.**

The position: collect broadly; publish **derived** content (Reddit posts,
independent blogs, social posts) written from what we gather; retain source
links internally and never render them publicly; keep the board auth-walled and
internal.

This proposes a name, a condition set, what each condition is checkable
against, and what it does to the ten rulings. **Nothing here is implemented.**

---

## 1 · The name

**`derived-publication-only`**

The word doing the work is **only**: the sole thing that leaves the team is
prose we wrote. Source material does not, in any form — not as a quote, not as
a link, not as a screenshot of a board page carrying either.

It replaces `internal-development-only` as the value of `asserts`, and it is a
*wider* basis — it permits something the old one forbade. That direction
matters: **every ruling that rests on the old basis was granted against a
narrower use**, so none of them carries over by substitution. §4.

The board half does not go away. `derived-publication-only` asserts **two**
things at once — an internal board and derived-only output — so the four
existing conditions stay exactly as they are and the new ones are added beside
them. A single undertaking with eight conditions is right here, because the
hazard is the seam between them (§2.4) and two undertakings would put the seam
between two documents.

## 2 · The condition set

### The three proposed, and the verdict

```yaml
verbatim_quote_published:        false
source_link_rendered_externally: false
person_attributed_by_handle:     false
```

**All three are necessary. None is sufficient, and two may be wrong in
direction for some sources.** Taking the second claim first, because it is the
one that changes the plan.

### 2.1 · Stripping attribution can be the breach, not the compliance

Conditions 2 and 3 **remove** attribution. A material fraction of what we hold
is user-authored under licences that **require** it. The project's own dev.to
ruling already records this:

> Articles are USER-AUTHORED and carry per-post licences. dev.to's own terms
> and the default article licence have not been read, so whether short
> quotation is permitted per article is UNANSWERED.

For anything CC-BY or CC-BY-SA, publishing derived work **without** attribution
is the licence breach, and a link is what cures it. So
`source_link_rendered_externally: false` is not a safe default — it is a choice
that is protective for some sources and a violation for others, and **which is
which is exactly what the unread readings would tell us.**

**This is circular and the circularity should be visible rather than resolved
by assumption.** The basis was asked for before the readings so the readings
have something to rest on; one of the basis's conditions cannot be known correct
until a reading happens. The way out is not to guess: make the condition
**per-source** rather than global, with a safe default until read —

```yaml
source_link_rendered_externally: false      # global default
# and per source, once its licence is read:
#   attribution_required: true|false|unread
```

— and treat `unread` as *do not publish derived work from this source yet*.
That is rule 6 applied to a condition rather than to a column: an unread licence
is not a permissive one.

### 2.2 · What "no verbatim quote" does not catch

**Close paraphrase.** A derived post that follows one source's structure and
substance, changing the words, satisfies the condition and takes the thing the
condition exists to protect. Verbatim is a bright line, which is its virtue as a
check and its weakness as a rule.

There is no clean mechanical fix, but there is a checkable proxy that is worth
more than it looks:

```yaml
min_independent_sources_per_published_claim: 3
```

**A derived assertion resting on one document is a paraphrase of that
document.** The existing publication definition already gestures at this —
*"an aggregate over those words is not one — '7 voices, 2 platforms' is a count
and publishes nothing quotable"* — but it sets no floor, so a one-source
"aggregate" qualifies. A floor makes the aggregate claim true rather than
asserted, and the corpus can check it: every published assertion maps to the
documents behind it or it does not go out.

`3` is a placeholder. The number should come from the same place `N_EFF_MINIMUM`
came from, not from this document.

### 2.3 · Re-identification without a handle

`person_attributed_by_handle: false` is necessary and thin. A post can identify
somebody with no handle and no quote — *"the engineer who migrated a four-
million-line Rust codebase and wrote it up"* is one person, and a negative
claim about them is the harm the handle rule is aimed at.

```yaml
person_identifiable_without_handle: false
```

Asserted, not checkable. Worth writing down precisely **because** it is not
checkable: it is the part a reviewer has to read the draft for, and a condition
set that lists only the machine-checkable things trains people to think those
are the whole risk.

### 2.4 · The seam: the board is internal, and a screenshot is not

The board holds quote + attribution + link. A screenshot of a board page inside
a derived post puts both outside the team, and **satisfies every condition
above** — no verbatim quote was typed, no link was rendered as a link, no handle
was written.

```yaml
board_surface_reproduced_externally: false
```

This is the one I would not drop. The existing publication definition already
names this exact failure — *"a screenshot in a deck, a link to a deployed
build, a shared PDF of a board page — each one trips this"* — and the new
condition set, read on its own, would let all three through.

### 2.5 · Who writes the derived post

If a model drafts from the corpus, verbatim regurgitation stops being
hypothetical and `verbatim_quote_published: false` has to be a **check on the
draft** rather than an intention of the author.

```yaml
published_drafts_machine_generated: true|false
```

It also opens a surface this project has not had. CLAUDE.md's rule 2 names
exactly two stages that may call a model, neither of which produces published
text. A model writing what goes out is a third, and whether it is permitted is a
rule-2 question rather than a terms question.

### 2.6 · Two smaller ones, named for completeness

```yaml
derived_output_monetized: false     # `monetized` today is about BOARD ACCESS
publication_cadence_bounded: true   # systematic republication reads differently
                                    # from incidental use in several ToS shapes
```

### The set, assembled

```yaml
required_conditions:
  # the four that exist, unchanged - they describe the board
  auth_walled:                     true
  external_users:                  false
  publicly_linked:                 false
  monetized:                       false
  # the new ones - they describe the OUTPUT
  verbatim_quote_published:            false
  source_link_rendered_externally:     false
  person_attributed_by_handle:         false
  person_identifiable_without_handle:  false
  board_surface_reproduced_externally: false
  derived_output_monetized:            false
  published_drafts_machine_generated:  false
  min_independent_sources_per_published_claim: 3
```

## 3 · What each is checkable against

**The existing four are checkable by inspecting the deployment.** Is there an
auth wall, are there external accounts, is the URL indexed, is anyone billed.
Somebody can go and look.

**The new ones are about artifacts outside this system** — a Reddit post a
person wrote. Nothing in this repository can observe them, and that makes them
strictly weaker. **But three of them become measurable the moment a draft is
supplied**, and that is worth building rather than asserting:

| condition | checkable against | how |
|---|---|---|
| `verbatim_quote_published` | the corpus | **the operation rule 1 already runs, reversed.** `judge/extract/runner.py:383` is `p.quote in thread.flattened_text` — plain Python, no model. For a draft: shingle it and search `flattened/`. |
| `source_link_rendered_externally` | `document.url` | scan the draft for URLs whose host matches a harvested document |
| `person_attributed_by_handle` | `author.external_id` | **partially — see below** |
| `board_surface_reproduced_externally` | nothing | asserted |
| `person_identifiable_without_handle` | nothing | asserted, reviewer reads the draft |
| `min_independent_sources_per_published_claim` | the draft's own working | asserted unless drafting records which documents each assertion rests on |
| `derived_output_monetized` | nothing | asserted |
| `published_drafts_machine_generated` | nothing | asserted |

### The handle check is 9% covered, measured

`author.external_id` holds a **platform id**, not a handle, for most sources:

```
reddit        6,243   't2_100vut'                    opaque id
github        1,891   '100020685'                    opaque id
devto           328   '100128'                       opaque id
x                99   '1017744254'                   opaque id
huggingface      70   '5f1158120c833276f61f1a84'     opaque id
hackernews      852   'zxspectrum1982'               THE HANDLE
blog             14   'blog:slack.engineering#…'     the name
```

**866 of 9,497 authors — 9.1% — can be checked. The other 8,631 cannot**, because
we never stored what those people are called. A draft naming a Reddit username
would pass a check against this table every time. `handle_hash` is populated for
all 9,497 and does not help: it is a one-way hash, so it can confirm a handle we
already have and cannot find one we do not.

So the condition stands as an **assertion** with a check that covers a named
9.1% — and saying "the handle check passes" without that denominator would be
rule 7 exactly.

### The shape they need

**Yes — the same signature-and-expiry shape, and for a stronger reason than the
existing four.** `_undertaking_basis()` already voids on an unknown key, a
missing key or a wrong value, with `required_conditions` as the source of truth.
An output condition written as a comment would be invisible to it, and the
undertaking would keep asserting a basis whose new half nothing evaluates —
which is the defect this whole exercise exists to fix.

Two things follow:

- **`review_valid_days` should be shorter than 30.** The existing figure suits a
  state that changes when somebody redeploys. These conditions change when
  somebody writes a post, and that is a faster clock.
- **The pre-publication check ships as a report, not a gate** (rule 8). Its
  error rate against real drafts is unmeasured, and a wrong gate would refuse a
  draft nobody could see the fault in. A report on every draft, measured for a
  fortnight, is what earns the gate.

## 4 · What it does to the ten rulings

### The structural finding, which is not about any one ruling

**Every ruling describes a use we are abandoning, and is silent on the one we
are adopting.**

```
contract/sources.yaml:216   "content is quote + attribution + link; full text is
                             retained privately … and is never republished"
contract/sources.yaml:376   "we publish quote + attribution + link taken from the
                             feed body Medium served us"
contract/sources.yaml:1066  "we publish quote + attribution + link only"
CLAUDE.md:227               "Published content is quote + attribution + link,
                             never full text"
BUILD-PLAN.md:388  NFR-5    "quote + attribution + link, never full text"
                            Accept: no page renders more than a bounded quote
```

Derived prose is not quote + attribution + link. It is not *more* than a bounded
quote and it is not *less* — **it is a different artifact, and NFR-5's
acceptance criterion cannot be evaluated against it.** The rulings do not forbid
it; they do not describe it. Silence is not permission, which is this project's
own repeated finding.

**So this is a requirements change before it is a contract change.** CLAUDE.md
lists the quote+attribution+link form under *stack decisions already made — do
not relitigate*. The position change relitigates it, legitimately, and that
should be explicit rather than arriving as a side effect of a new basis.

### Ruling by ruling

| ruling | under `derived-publication-only` |
|---|---|
| `blog-class-a-self-hosted` | carries the new basis. **7 publishers' terms unread**; its own RE-REVIEW trigger fires |
| `blog-class-b-medium` | carries it, **and needs rewriting**: its stated permission *is* the quote+link form. Not unsupportable — its justification simply describes nothing we would do |
| `blog-umbrella-not-a-fetch-target` | unaffected. No basis, not a fetch target |
| `github-api-terms` | **has no `basis` and no `use_basis` precondition at all**, so it changes nothing mechanically and that is the defect, not a pass. 3,403 documents, 69 board entries, never read |
| `arxiv-api-terms` | carries it. Zero documents, so read last |
| `devto-api-terms` | **the critical one.** Per-post licences, quotation UNANSWERED, and 715 board entries — the most of any source. §2.1's circularity lands here first |
| `hackernews-algolia-terms` | carries it. User-authored comments; third-party route already recorded |
| `huggingface-api-terms` | carries it. User-authored discussions |
| `reddit-via-rapidapi` | out of scope for reading — **and now a publication TARGET.** See below |
| `x-via-rapidapi-scraper` | out of scope |

### The one that is genuinely new: Reddit as a destination

We would publish **to** Reddit, using material partly gathered **from** Reddit.
No ruling covers that. `reddit-via-rapidapi` is about reading, the new scoping
puts Reddit out of scope for terms, and posting is governed by a third document
again — Reddit's content policy and its self-promotion rules, which bear on
anyone posting regardless of how they obtained their material.

**Nothing in this repository has ever looked at that**, and it is the one place
where "RapidAPI-routed, therefore out of scope" does not hold: the route is how
we *read*, and this is about how we *post*.

### Does any ruling become unsupportable?

**No — and that is the wrong question to have answered yes.** All eight that
name the basis need re-review rather than replacement, because re-review is what
their own text asks for and because none of them was written against this use.
The ruling that comes closest to unsupportable is `blog-class-b-medium`, whose
entire cost argument is *"This costs nothing, because the feed carries the whole
post"* — an argument about what we may republish, in a world where we republish
nothing.

## 5 · What is asked

1. **Ratify or rename the basis.** `derived-publication-only`.
2. **Rule on the condition set** — specifically §2.1, whether
   `source_link_rendered_externally` is global or per-source with `unread` as a
   refusal, which is the one that cannot be settled without a reading.
3. **Rule on §2.5** — whether a model may draft published text. That is a rule-2
   question and does not belong to the terms work.
4. **Confirm the NFR-5 change is intended** and relitigated on purpose.
5. **Decide whether posting to Reddit needs its own ruling.** I think it does.

**Not proposed:** any edit to `use_basis_undertaking`, any ruling, any Substack
work, any code. Nothing here has been implemented.
