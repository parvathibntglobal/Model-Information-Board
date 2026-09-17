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
them. A single undertaking carrying both halves is right here, because the
hazard is the seam between them (§2.4) and two undertakings would put that seam
between two documents.

## 2 · The condition set

### The three proposed, and the verdict

```yaml
verbatim_quote_published:        false
source_link_rendered_externally: false
person_attributed_by_handle:     false
```

**The verdict: two are kept and moved, one is dropped.**

- `verbatim_quote_published` — **kept**, global, and it is the only one of the
  three with a real check behind it (§3).
- `source_link_rendered_externally` — **kept but moved per-source**, because a
  global `false` is a licence breach for CC-BY material (§2.1).
- `person_attributed_by_handle` — **dropped**, and the gap recorded as an
  absence instead. It would pass on 91% of the corpus by construction (§2.3).

And three the set was missing: the screenshot seam (§2.4), a floor on how many
sources a published assertion rests on (§2.2), and who writes the draft (§2.5).

### 2.1 · The conditions are PER SOURCE, and `unread` means do not publish

Conditions 2 and 3 **remove** attribution. A material fraction of what we hold
is user-authored under licences that **require** it. The project's own dev.to
ruling records this already:

> Articles are USER-AUTHORED and carry per-post licences. dev.to's own terms
> and the default article licence have not been read, so whether short
> quotation is permitted per article is UNANSWERED.

For anything CC-BY or CC-BY-SA, publishing derived work **without** attribution
is the breach, and a link is what cures it. A single global
`source_link_rendered_externally: false` is therefore protective for some
sources and a violation for others — **and which is which is exactly what the
unread readings would tell us.**

So the output conditions split in two. **What is true of every published post**
stays global; **what depends on a source's licence** moves onto the source.

#### The per-source record

On every fetch-target row in `contract/sources.yaml` — the 7 platform sources
with an endpoint and the 9 feeds, **16 rows**:

```yaml
publication:
  may_publish_from:     unread        # unread | true | false
  terms_read_on:        null          # date, and null while unread
  read_by:              null          # a person, like every other ruling
  quotation_permitted:  unread        # unread | true | false
  attribution:          unread        # unread | required | forbidden | optional
```

**`unread` is a third value and not a synonym for either.** It does not mean
assume permissive and it does not mean assume restrictive — it means *nobody has
looked, so nothing may be published from this source.* Rule 6 applied to a
condition rather than to a column: a missing value is never silently converted
into a definite one, and the definite one it would otherwise become here is
whichever the reader happens to be optimistic about.

**Why three fields and not one.** `may_publish_from` is the gate, and the other
two are why:

- `quotation_permitted` — settles whether a verbatim span may ever appear. Under
  this basis the global answer is no anyway, so this field is what would let a
  future ruling relax it for one source without reopening the basis.
- `attribution` — the field this whole section exists for. `required` and
  `forbidden` are **opposite instructions**, and a global condition can only
  encode one of them. A source marked `required` makes
  `source_link_rendered_externally: false` wrong for that source, and the
  per-source record is where that is allowed to be said.

`may_publish_from: true` requires `terms_read_on`, `read_by` and a non-`unread`
value in both other fields. A `true` with an `unread` beneath it is the
placeholder wearing a decision's clothes, and it should be refused at load the
way `_ruling_from` refuses a named-but-unenforced basis.

#### The default for the ten existing sources: do not publish, all of them

**All sixteen rows are `unread` today**, because no terms document has been read
for any of them. The ten rulings say so themselves — five carry
`terms_document_read: [false]`, the two blog rulings say it in prose across nine
feeds, and `github-api-terms` has never recorded the question at all.

So the honest consequence, stated plainly rather than discovered later:

> **Ratifying this basis permits no publication from anything.** Every source is
> `unread`, `unread` means do not publish, and the first thing that changes that
> is a reading somebody signs.

That is the right shape and it should not be read as an obstacle. A basis that
permitted publication on the day it was ratified would be permitting it on the
strength of nothing, which is the state we are leaving.

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

### 2.3 · The handle condition is DROPPED, and the gap is recorded instead

`person_attributed_by_handle: false` **is not proposed**, and it is worth being
explicit that this is a decision rather than an oversight.

**It would pass on 91% of the corpus by construction.** `author.external_id`
holds an opaque platform id for every source but one:

```
source        authors   external_id                    is it a handle?
reddit          6,243   't2_100vut'                    NO - opaque id
github          1,891   '100020685'                    NO - opaque id
devto             328   '100128'                       NO - opaque id
x                  99   '1017744254'                   NO - opaque id
huggingface        70   '5f1158120c833276f61f1a84'     NO - opaque id
hackernews        852   'zxspectrum1982'               YES - the handle
blog               14   'blog:slack.engineering#…'     the author's name
──────────────────────────────────────────────────────────────────────
checkable         866 of 9,497  =  9.1%
unverifiable    8,631 of 9,497  = 90.9%
```

**A draft naming a Reddit username passes a check against this table every
time**, because we never stored what that person is called. `handle_hash` is
populated for all 9,497 and does not rescue it: it is one-way, so it can confirm
a handle we already hold and cannot find one we do not.

**A check that passes on 90% of the corpus by construction is worse than no
check**, because its passing will be cited. That is rule 8's argument arriving
before the check ships rather than after — an unmeasured check is a weight, and
a check measured at 9.1% coverage is not a weight either, it is a number that
looks like assurance.

So the record carries the absence instead:

> **NO CHECK EXISTS FOR WHETHER A DRAFT NAMES A PERSON.** We hold opaque
> platform ids for 8,631 of 9,497 authors and could not detect a handle in a
> draft if one were there. Handles are not stored, so this is not a check
> somebody could write today — it is a gap in what was harvested. Whether a
> draft names anybody is a **reviewer question**, and re-identification without
> a handle (a distinctive anecdote, an unusual migration, a named employer) is
> the same question and has never had a check at all.

Rule 4's shape: an absence we caused must not read as an absence we found. A
condition list that silently omitted this would say, by omission, that naming
people is not a risk.

### 2.4 · The screenshot seam, named in the set rather than inherited

The board holds quote + attribution + link. A screenshot of a board page inside
a derived post puts both outside the team, and **satisfies every condition
above** — no verbatim quote was typed, no link was rendered as a link, no handle
was written.

```yaml
board_surface_reproduced_externally: false
```

**It is named here rather than left to the existing publication definition, and
that is deliberate.** The definition already covers it —

> a demo to a prospective user, a screenshot in a deck, a link to a deployed
> build, a shared PDF of a board page — each one trips this

— but it lives in a comment block above the rulings, and **the condition set
will be read on its own.** Somebody checking "have we met the conditions" reads
eight lines of YAML, not a prose definition three hundred lines away. A set that
relies on the reader having found that definition is a set that silently permits
the screenshot, because every explicit condition passes.

The two say the same thing twice on purpose. That is the cost of it being the
seam between the board half and the output half: it is the one failure that is
invisible from either side alone.

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

**Global — asserted once, in `use_basis_undertaking`:**

```yaml
required_conditions:
  # the four that exist, unchanged - they describe the BOARD
  auth_walled:                     true
  external_users:                  false
  publicly_linked:                 false
  monetized:                       false
  # new - they describe the OUTPUT
  verbatim_quote_published:            false
  board_surface_reproduced_externally: false
  person_identifiable_without_handle:  false
  derived_output_monetized:            false
  published_drafts_machine_generated:  false
  min_independent_sources_per_published_claim: 3
  # new - the gate that reads the per-source records
  every_source_published_from_is_readable: true
```

**Per source — 16 rows in `contract/sources.yaml`:**

```yaml
publication:
  may_publish_from:     unread
  terms_read_on:        null
  read_by:              null
  quotation_permitted:  unread
  attribution:          unread
```

`every_source_published_from_is_readable` is what joins them: it asserts that
every source a published post drew on carries `may_publish_from: true`. Without
it the per-source records exist and nothing obliges anybody to consult them,
which is the shape `terms_document_read` was in before it became a key
`_check_facts` reads.

**`person_attributed_by_handle` is deliberately absent.** See §2.3 — its absence
is recorded in the undertaking's prose so that omission reads as a decision
rather than an oversight.

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
| `every_source_published_from_is_readable` | `contract/sources.yaml` | the draft's source list against 16 `may_publish_from` values. A pure lookup, and the only new condition that is fully checkable without reading the draft's prose |
| `min_independent_sources_per_published_claim` | the draft's own working | checkable **only if drafting records which documents each assertion rests on**. That is a process change, not a code one, and without it this is an assertion |
| `board_surface_reproduced_externally` | nothing | asserted |
| `person_identifiable_without_handle` | nothing | asserted, reviewer reads the draft |
| `derived_output_monetized` | nothing | asserted |
| `published_drafts_machine_generated` | nothing | asserted |
| *(per source)* `attribution`, `quotation_permitted` | the terms document | asserted by whoever read it, with `read_by` and `terms_read_on`, like every other ruling |

### Why the handle check is not in that table

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

Saying "the handle check passes" without that denominator would be rule 7
exactly — a real value answering a question it was not asked. The decision in
§2.3 is not to ship it, and to carry the denominator table as the evidence for
that decision rather than deleting it with the condition.

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
where "RapidAPI-routed, therefore out of scope" does not hold: **the route is
how we read, and this is how we post.** A reseller can only ever govern the
former.

**So the reading list gains a document that is not a platform's terms of
access:**

```
Reddit content policy + self-promotion rules      THE POSTING DOCUMENT
```

It is distinct from `reddit-via-rapidapi` in every way that matters — different
document, different activity, and it binds anyone who posts regardless of how
they obtained their material. It also does not belong to any of the sixteen
per-source records above, because those describe **sources we read from** and
this is a **destination we write to**. If the derived posts go to Reddit, this
is the one reading that gates the activity rather than one source's contribution
to it.

The same question exists for wherever else the derived posts land — an
independent blog is our own surface and raises none of it, and a social platform
raises its own version.

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
2. **Ratify the per-source split** (§2.1) — the five-field record on 16 rows,
   with `unread` as a refusal rather than a default in either direction.
   **Note that this permits no publication on day one**, which is the point.
3. **Ratify dropping `person_attributed_by_handle`** (§2.3) and carrying the
   9.1% denominator table as the reason.
4. **Rule on §2.5** — whether a model may draft published text. That is a rule-2
   question and does not belong to the terms work.
5. **Set `min_independent_sources_per_published_claim`.** `3` is a placeholder
   and should be measured, not chosen here.
6. **Confirm the NFR-5 change is intended.** It is written up separately in
   `docs/proposals/nfr-5-stops-applying-to-derived-prose.md` — it is a
   requirements change and should be ruled on as one.
7. **Add Reddit's content policy and self-promotion rules to the reading list**
   as the posting document, and decide whether posting needs its own ruling. I
   think it does.

**Not proposed:** any edit to `use_basis_undertaking` or to any source row, any
ruling, any Substack work, any code. Nothing here has been implemented.
