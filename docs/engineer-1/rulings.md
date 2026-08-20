# The rulings, and what each one ruled out

Eleven decisions that shaped this lane. Each has three parts, and the second is
the one that earns the format:

| | |
|---|---|
| **decided** | what holds now, and where it is enforced |
| **the alternative** | what was not chosen, stated well enough to be re-chosen |
| **what would revise it** | the evidence that would reopen it |

**A decision without its alternative reads as the only option available**, and
that is how a considered trade-off becomes folklore that nobody may question. In
eight weeks this file should have been argued with at least twice.

*Verified against `origin/main` at `225b126`. Mechanism lives in
`../how-it-works.md`; this records the decisions.*

---

## 1 · Routes are not models

**Decided**, 2026-08-18. `is_route()` in `collect/registry/propose.py`: the `~`
prefix the feed uses for floating pointers, and the `openrouter/` namespace.
Enforced on three call paths — `propose()`, `tracked.select()`,
`entity.build_population()`.

The reason is FR-4 rather than tidiness. A claim about `free` resolves to a
pointer, and the model that actually served the request is unknown, so the
mention is **unattributable by construction** — not merely unattributed. FR-4
exists so a mention resolves to what existed when it was written, and a pointer
has no such thing.

**The alternative was seat-and-flag**, and it is the one that sounds more
cautious: keep the 17 pointers in the tracked set, mark them, let the coverage
page explain. It was refused because *"unseated today"* is a weaker claim than
what is true — **a pointer names whatever the vendor currently resolves it to, so
it has no capability to report on and can never be seated correctly.** Nothing
observed it and nothing will. A row for it is not a thin row, it is a category
error, and `INCOMPLETE` on every slot renders as *"nobody has discussed this
model"* — rule 4, applied to a thing that is not a model.

A third option was considered and rejected for a different reason: **filter
routes out of `model_version` at admission.** Refused because a registry that
silently omits 17 feed rows disagrees with the feed, and FR-3's whole job is
diffing the feed. The exclusion belongs downstream, which is why the ruling has
call sites rather than a single choke point — and why it has already been missed
twice.

**What would revise it.** A provider publishing a pointer's resolution history,
so a mention could be attributed to what the pointer meant *at the time*. That is
exactly what FR-4 does for aliases, and it would make a route an alias rather
than a category error.

**Measured, so it is not a taste.** Excluding the 17 ids takes non-technical
control survival from **1.3% to 0.0%** and costs **10.6 points** of the
unfiltered sample — those documents say "free" and "auto", and they do not name a
model (`measurements.md` §8).

---

## 2 · Alias surfaces come from the contract, and the floor counts renderings

**Decided.** `contract/registry.yaml` sets `declared_surfaces_only: true` and
`expand_mechanically: false`. Only surfaces hand-written in `seed_models.yaml`
become search queries; the canonical id and its local part are added for
**attribution** and earn no query. And `check_spelling_coverage` fails the seed
load unless every model declares a **spaced, a hyphenated and a concatenated**
form.

**The alternative was mechanical expansion**, and its reasoning was sound: search
APIs have no fuzzy operator, so `gpt-4.1-mini` and `gpt 4.1 mini` are different
literal queries matching different posts, and breadth is not optional. Measured,
re-expanding each declared surface cost **1,752 queries per platform against a
~600-query budget**, and adding the id rows cost a further **516**, for forms
nobody types. So breadth moved from code into the YAML — where a human supplies
it and a gate checks it, because *human-supplied is fine; human-supplied and
unverified is not.*

**The second alternative, refused on #33: make the floor count attested
surfaces.** The corpus attests a median of 2 surfaces per model, so a floor of
three looks unmet by **55 of 72** models. It was refused for two reasons. The
remedy would be **fabrication** — 55 models each fixed by somebody inventing a
spelling, and **a check whose remedy is fabrication is worse than no check**. And
spaced/hyphenated/concatenated are always derivable *from the id*, which is the
property that makes it fair to fail a load over. "Always" has one counted
exception, pinned in `tests/test_registry_spelling.py`: a single-token local part
has no separator to vary — 1 of 155 ids, `openrouter/auto`, which names a router.

**The family surface is required-but-`INCOMPLETE`-able and never gated.** A bare
`opus` is attested 8,149 times and attributable to no single model; **62% of
family-word mentions carry no version at all**. A gate demanding one could only
be satisfied by asserting an attribution the data refuses.

**What would revise it.** A GitHub or blog surface extract. This is all measured
on Reddit prose, and the prediction is that id spellings rank very differently
there — `docs/measurements/alias-surfaces.md` §6.1 argues it from existing
figures and says so rather than claiming a measurement.

---

## 3 · Official APIs and public feeds only, and a ruling is dated

**Decided.** NFR-5, and it is not a posture statement — it is enforced.
`assert_terms_reviewed` refuses a source unless **all four** hold: it names a
known ruling; the ruling has not expired; the source's recorded evidence is not
stale and every fact the ruling conditions on is present and acceptable; and
**every live precondition is re-verified on this run.** `robots.txt` is re-read
every run and per redirect hop, so a host that adds `Disallow: /` is obeyed the
same day.

**The alternative was the first implementation**: grep `tos_notes` for a
placeholder marker. It caught the case where nobody had done the reading, and
nothing else. It let through the worse case — **a ruling made once, in August,
asserted forever against a site that changed its terms in October.** *A dated
placeholder is still a placeholder.*

**Two rulings enforce behaviour rather than recording it.**
`blog-class-b-medium` sets `fetch_articles: false`, so `BlogFetcher` refuses to
request articles at all — every article URL in a Medium feed carries `?source=`
and is both disallowed by robots and answered with 403. And
`reddit-via-rapidapi` carries `basis: internal-development-only` as a **live
precondition**, so the ruling stops applying the moment the deployment stops
being internal rather than the moment somebody remembers to revisit it. Its limit
is stated where it is observed: it catches a production deployment and **does not**
catch a staging instance that has acquired external users.

**The Reddit ruling is a permission, not a clearance**, and it records four
conditions it does not clear: Developer Terms 4.1's *"by or on behalf of a
business"* limb (no legal review has happened); Data API Terms 2.8 (credentials
must be issued by Reddit — a reseller route does not satisfy this regardless of
use); Developer Terms 5.2 (cite the author's username, and we store
`handle_hash` only); Data API Terms 3.2 (delete data not required for the
approved use case, against an immutable raw store). **None blocks anything built
today; all four block the publish path.**

**An alternative inside this ruling was refused, and it is the interesting
one: a second, lighter ruling for measurement sweeps that quote nobody and
publish nothing.** Refused because **purpose is self-declared** — an exempt
category is one everything ends up filed under, and the person writing the
justification is the person who wants the data. `assert_terms_reviewed` has no
concept of purpose, deliberately: it takes a source row and this run's
observations, and a fetch is a fetch. The retention difference is real and cuts
**the other way**: a measurement sweep keeps documents *because most of them are
about nothing*, and *"we cited you"* and *"you were in a denominator"* are
different answers to the same question. So it is handled as a property of the
sample — stored outside `raw/`, with a deletion date recorded at collection.

**What would revise it.** Any external publication, any external user, any
monetization, or a switch to a direct Reddit key. All four are named in the ruling
as re-review triggers, and the escalation to the MD is dated 2026-08-18.

---

## 4 · `text_ref` is a location, `content_hash` is identity — and there is no object store yet

**Decided.** Two columns, because they answer different questions, and **NFR-6 is
what forces the split**: *"tombstone a document; its quotes vanish next run, only
the content hash remains."* That only parses if the hash and the stored bytes are
separable things.

```
ref  = "raw/sha256/ab/cd/abcd...ef"    -> document.text_ref      LOCATION
hash = "abcd...ef"                      -> document.content_hash  IDENTITY
```

Keeping identity in the row means storage can move without rewriting what
anything *is*. Two namespaces with different durability: `raw/` is irreplaceable
and never evictable, `flattened/` is a regenerable cache — enforced in code
rather than left to a comment, because somebody will eventually write a cleanup
script.

**The alternative is `text_ref` being the hash itself**, which is tidier and was
left deliberately reachable: the public surface of `rawstore.py` is hash-first
**so that if the other lane prefers it, the change is one column write rather
than a redesign.** That is a live offer, not a closed decision.

**And no S3.** `BUILD-PLAN.md` specifies Postgres plus an object store, and that
is right eventually. Eight weeks on one machine does not need it, and `boto3`
bought now is a dependency bought before it is used. **Content addressing is what
makes this a deferral rather than a shortcut**: migrating is a file copy plus a
`text_ref` rewrite, and the surface is deliberately five verbs so an S3 backend
has a small target.

**What would revise it.** Volume, or a second machine. Either makes the file copy
the expensive half instead of the cheap half.

---

## 5 · Assembly refused to exist for eighteen days

**Decided.** `assemble_thread` raised `AssemblyNotBuilt` rather than returning a
tree, until the four coverage columns landed on 2026-08-18. And
`selection_method` now records
`specificity_x_log_engagement@observed` — never the schema's bare default.

The argument: **a selection that cannot state what it saw writes "the top 5
children" when it means "the top 5 of the 4% we happened to fetch."** One
`getPostComments` call returned **200 of 4,833** comments. Reddit orders
**siblings** rather than the tree, with 30% of adjacent pairs score inversions
and a depth-2 comment scoring 610 sitting under top-level comments scoring 6 — so
**the last-seen score bounds nothing unseen**, and a global ranking is not
available from this data at all.

**The alternative was to ship it and add coverage later**, which is what almost
every schedule wants. It was refused because the row it would have written is
indistinguishable from a correct one: `child_count = 5`, a valid `offset_map`, a
`selection_method` naming a global ranking. **Nothing downstream could have
detected the difference**, and claims extracted against it would have been
counted as *"five engineers"* with no record that five was out of two hundred out
of nearly five thousand.

**The narrower ruling inside it.** The bare `specificity_x_log_engagement` is the
schema DEFAULT and this module must never write it — a row reading the default
would be claiming exactly the thing the refusal spent eighteen days protecting
against. A one-member thread (a blog article) writes `whole_document`, which is
`NOT NULL` and not the default: nothing was ranked, so describing a ranking that
did not happen is the same failure one level out.

**What would revise it.** An API that returns the whole tree, or a documented
sibling ordering that lets an unseen score be bounded. Neither exists.

---

## 6 · The coverage columns are nullable, and a blog writes `None` rather than `0`

**Decided.** All four coverage columns on `thread_context` are nullable, because
**a row written before coverage existed has not been measured at 0% — it has not
been measured.** `coverage_ratio` is `GENERATED ALWAYS ... STORED`, so Postgres
computes it and rejects an explicit value, NULL included; the insert **omits the
column entirely**.

For a blog article the ruling is: `observed_children = 0` (**a measurement** — we
looked and stored none), `hidden_children_min = None` (**not 0** — we withheld
the comment section, so *"nothing was withheld"* is true of the platform and
false of us), `hidden_branches_unsized = 0` (a measurement — there are no `more`
markers).

**The alternative for `hidden_children_min` was 0**, which is what any
straightforward implementation writes, and it is wrong in the direction that
**flatters our own coverage**: a post with 400 comments and one with none would
both read 0. That is rule 6 leaning the unsafe way.

**Two design points that look like pedantry.** The ratio is **generated, not
stored beside its inputs** — the fifth instance of one drift on this project: a
derived value written next to what it derives from means somebody corrects
`hidden_children_min` in a backfill, does not recompute the ratio, and the row
disagrees with itself silently, in the direction that flatters coverage. And the
generated `CASE` has **no `ELSE`**, so an empty tree yields NULL rather than 1.0 —
0/0 cannot become full coverage.

**The cost, flagged rather than solved:** a NULL `coverage_ratio` now means both
*"no children exist"* and *"never measured"*, separable only by reading the
inputs. That is a display problem and it belongs to the other lane.

**What would revise it.** A `coverage_measured_at` column, or a fifth state — but
only if the display side actually needs to tell the two NULLs apart. Verified live
2026-08-20: **32 rows, 2 with a non-NULL ratio**, which is the blog case working
as ruled.

---

## 7 · The locality window is 1,200 characters

**Decided.** `contract/harvest.yaml: sieve.locality_window: 1200` — how far apart
`topic` and `signal` may be and still count as one claim. Subject is deliberately
unconstrained: naming the model once is how a post establishes what it is about,
and a blog naming it in the introduction and reporting the failure in the
conclusion is the ordinary shape.

**Why there is a number at all.** The first nine-feed blog harvest kept exactly
one document: `vickiboykis.com/2026/04/20/build-yourself-flowers/`, 41,956
characters, filed `extraction.faithfulness: positive`, with `flash 2.5` in a
sentence about breaking a transcript into paragraphs, `extract` in a sentence
about a museum API, and `held up` meaning **delayed**, 3,899 characters away.
Three unrelated passages counted as one claim.

**The alternative was no window**, which is what the sieve did before, and it was
quietly stricter on GitHub than on blogs with no way to know: blog articles have
a median of **8,191 characters** against GitHub's **2,228**.

**The evidence is for a band, not for a number.** Measured over 111 blog articles
and 174 GitHub candidates, every passing document by the gap between its closest
topic–signal pair: **0, 356, 496, 3899, 4027**. The two known false positives are
the two far ones and **nothing sits between 496 and 3,899**. Every value in that
band keeps and drops exactly the same documents on this data, so **the choice
inside the band is judgement**, and the judgement is stated: ~1,200 characters is
two or three paragraphs, plausibly the unit "the claim and what it is about"
occupies; 2,000 is a page; 600 is one paragraph.

**It leans tight on purpose**, and the reason is recoverability rather than
precision: raw payloads are immutable and content-hash addressed, so **a window
that is too tight is fixed by re-sieving** — which costs nothing, because the text
is local. A document the sieve dropped is recoverable; a document never fetched
is not. The qualifier matters: recoverable **for the pages that were stored**,
and only page 1 is stored today.

**What would revise it.** A corpus with real positives in it. With one known
false positive per channel and five passing documents in total, this measures how
many documents a window **drops** and cannot measure whether it drops real
evidence. If real positives sit beyond 1,200, it is too tight, and the
measurement that would say so does not exist yet.

---

## 8 · Flattening rules are per-platform, and entities are decoded before symbols

**Decided.** `FlatteningRules` is a per-platform value, and `BLOG_RULES` sets
`decode_entities = False`. Entities are decoded **before** symbols are
substituted, in **one left-to-right walk**.

**The order first.** They are different *kinds* of operation — an entity undoes
how the text arrived, a substitution changes how it reads — so decoding first
means everything downstream operates on what the person typed. One walk is what
makes the order **structural** rather than a convention somebody has to remember,
and it is what makes *unescape exactly once* a property of the algorithm:
`&amp;gt;` is a literal somebody typed, the walk consumes `&amp;`, emits `&`, and
resumes **after** it, so `gt;` is never re-examined.

**The alternative was one global rule set**, which was true while there was one
platform and stopped being true the moment blog text arrived. Measured:
**trafilatura decodes twice.**

```
html          'type &amp;gt; here'
lxml alone    'type &gt; here'      <- one decode, correct
trafilatura   'type > here'         <- a second decode
```

An unknown entity survives as `&unknown;` through both, so the second pass is an
entity unescape and not generic cleanup. On blog text this module's entity pass
is a no-op in the ordinary case — **0 of the five entities survived into the
flattener across 53 articles, 519,997 characters** — and where it is *not* a
no-op it is a **third** decode.

**Rule 1 cannot catch that, which is why the rule is off rather than merely
unused.** Verification is a substring match against the text the extractor was
given, and the display step resolves against the same trafilatura output: **both
sides of the check sit downstream of the decode.** An author who wrote `&gt;` for
display gets quoted saying `>` — verified, attributed to the right person, at the
right offsets, and wrong. The honest statement of what step 1 proves is *the
quote is exactly what we were given, not exactly what was published.*

**And one narrowing was refused.** The symbol rule is Unicode category `So`, read
off **one Reddit fixture**. The blog corpus refused both candidate replacements —
the dominant class is box-drawing characters inside fenced code blocks, from **2
documents of 106**, which is a severity finding and not a frequency one.
Narrowing from a corpus of two would repeat the original mistake in the other
direction, so it **stays global and wrong-in-a-known-way.**

**What would revise it.** For `So`: enough blog documents to characterise the
symbol distribution rather than two. For the decode: a fourth verification step
against the stored HTTP bytes, which `blog/options.py` already makes practical by
versioning the derivation as `trafilatura-2.2.0+opts-…+pipeline-…`. **Worth doing
once against a blog sample before the publisher renders a blog quote** — a
rendered `>` where the author wrote `&gt;` is a misquotation with our
verification badge on it.

---

## 9 · Two import boundaries, and the inner one has already changed a design

**Decided.** Neither lane may import the other, and **`collect/registry/` may not
import `collect/adapters/`** — the registry must not be able to *see* harvest.
Both are asserted by AST in `tests/test_lane_boundary.py`.

**The inner boundary is the one that costs something**, and it has been paid
once. `propose._clean` casefolds and regularises separators, and it exists as a
third implementation because both alternatives were tried and rejected:
`sieve.normalize` is the right shape and importing it **breaks the boundary** —
the test caught it, and the boundary won over sharing; `registry.aliases.normalize`
is in-lane and strips every non-alphanumeric, so `gemini-3-pro` becomes
`gemini3pro`, which is a matching key by design and destroys the spacing
`_clean` exists to produce.

**The alternative was a shared utility module**, and refusing it is a deliberate
acceptance of duplication. The reasoning is that these two functions **will
diverge**: one takes a surface and one takes a document, and the first of them to
grow a rule about its own input would silently change the other.

**The lane boundary's real consequence** is the one the other lane documented: an
exception raised in one lane **cannot be caught in the other**, because the
exception type has nowhere to live that both can see. That is why a store read
returns a **value** with four outcomes rather than raising — and why
`collect/rawstore_reader.py` and `judge/extract/resolver.py` define mirrored
enums on purpose, with a normalising `__post_init__`, because StrEnum members of
different classes compare equal by value and are **never identical**.

**What would revise it.** Nothing about the lane boundary; it is the interface
between two people working in parallel. The intra-lane one would be revised by
the registry genuinely needing a harvest concept — at which point the concept
belongs in neither and moves to `collect/` top level.

---

## 10 · One dedupe method, not two

**Decided.** MinHash + LSH over character shingles, at every length.
`document.simhash` stays NULL. `min_tokens_for_signature: 200` is a **floor**
below which no signature is computed, and `similarity_threshold: 0.80`.

**The alternative is the one that was specified**, in `collect/CLAUDE.md`, on
reasoning that sounds right: simhash is built for long documents and MinHash's
signature is unstable below ~200 tokens, so switch methods at the boundary.
Measured over **79 ground-truth duplicate pairs and 951 stranger pairs from 3,767
Reddit documents**, MinHash separates better at **every** length, and simhash's
margin at 400–800 tokens is **one bit of 64** — re-run in simhash's conventional
word-3-gram tf-weighted form, its margins were 0–12 bits, so that is not an
artefact of the feature choice.

**So the number survived and its meaning changed.** 200 no longer switches
methods; it is the point below which neither method separates anything, and what
still applies below it is **certainty rather than similarity**: platform-declared
crossposts, and exact normalised match with the sentinels excluded. Those matter —
`[removed]` appears as the body of **57 distinct comments** and `[deleted]` of
**38** in one corpus, and merging them would collapse a thread.

**The direction is chosen, not incidental.** *Over-clustering is worse than
under-clustering*, because merging two genuinely independent reports destroys
corroboration — the only thing separating *"someone said this"* from *"this is
probably true"*. A higher floor merges fewer documents, so conservative means
high, and 200 is the top of the (50, 200) band the data supports.

**What would revise it.** True pairs in the 50–200 band, where n is currently 2
and 4. And **any blog syndication at all**: all 79 true pairs are Reddit
self-syndication and crossposts, and FR-16's own example is *"one blog syndicated
four times"*, so the channel the requirement is about is unmeasured.

---

## 11 · The seating floor is 20 mentions, and the launch window is 30 days

**Decided as a proposal, not yet in `contract/`.** `TrackedSetPolicy` takes both
values as **required arguments with no defaults** — deliberately unlike
`RegistryPolicy`, which carries proposed values as code defaults. That pattern is
documented in `policy.py` as a hazard tolerated so the lane could be developed
before the contract file existed; here there is no signed-off value for a default
to shadow, so **a caller must supply both and nothing can pick up a threshold
nobody agreed to.**

Two grounds, kept as separate values rather than collapsed to a boolean: **by
mentions** (measured, so it is primary) and **by launch window** (a model released
last week has no discussion history for the corpus to carry, and the launch
window is exactly when people post).

**The alternative was the budget**, and this is the part worth keeping. The
staleness bound affords 77 models, so the obvious move is to take 77 — or a round
50, which had been proposed. The curve says otherwise: ranks 1–40 carry **97.4%**
of the 7,202 attributable mentions, and ranks 41–72 — thirty-two models, 44% of
everything the corpus has ever discussed — carry **2.6%** between them. **A floor
of 20 sits in the flat part rather than on a cliff**, and covers 97.7%. So the
number comes from the corpus and the budget is not binding, which means it can be
argued with on evidence rather than on capacity.

**The ranking key was also a choice: mentions, not release date.** 11 of the 340
ids are `~vendor/…-latest` pointers whose `release_date` is when the pointer
moved. A date sort seats several of those and drops
`anthropic/claude-sonnet-4.5` — sixteen months old and still discussed, at **32
non-slice mentions**. (That figure was published as 426 and corrected: **394 of
426 was substitution-slice**, 92%, and a slice measurement was doing duty as a
corpus measurement inside the argument for the ranking method itself. The
conclusion survives on the smaller number.)

**What would revise it.** A GitHub or blog surface extract, because the ranking
is Reddit-only and that is the most likely way it misleads. And a second poll:
all 340 rows carry one `first_seen_at`, so **cadence is unmeasured** — *"the feed
has it"* and *"the feed keeps up"* are different claims and only the first is
supported.

> **The count is date-dependent and the published figure is not what the code
> returns.** `docs/measurements/tracked-set.md` reports **64** at 2026-08-18.
> Re-derived against the live registry: **63** at that date — the difference is
> the route now refused under §1 — and **62** at 2026-08-20, because the launch
> window slid two days and a model aged out. The `by mentions` half is stable at
> 41. **A tracked-set count needs its `as_of` the way every other figure needs its
> population.**

---

## Two decisions that belong to the other lane and constrain this one

Recorded here so they are not rediscovered as objections.

**Do not store the Reddit handle** (2026-08-18). The obligation under Developer
Terms 5.2 attaches at **publication**, and a column in `author` does not
discharge it — only rendering does. Storing now pays the privacy cost in advance
of any benefit and cannot be undone if publication is refused. Recovery is a raw
store read: `document.text_ref` points at an immutable payload carrying `author`
in full.

**Re-verified for this document**, because it is the whole evidence that the
handle is recoverable and therefore the whole reason not storing it costs
nothing. Against the committed
`fixtures/reddit/thread-1u1b22l-getPostComments.json`: **195 `t1_` comments, all
195 carrying `author`, 3 lacking `author_fullname` — and all 3 of those are
`[deleted]`**, so they have neither. Exactly as recorded in `judge/CLAUDE.md`.

And kept beside the
ruling: **we already publish the permalink, and the permalink displays the
username** — hashing protects the author from our database and not from our page,
which argues for publishing the handle *when we publish*, not for storing it now.

**One extractor, decided rather than selected.** An earlier draft specified
running three candidates against the golden set and choosing on measured
F1-per-dollar, with a second qualified for failover. Cut. What it costs is
recorded: the extractor is a model behind a stable name, and this product exists
because models change silently behind stable names — so with nothing to fail over
to, **a silent regression is caught rather than absorbed.** That is a smaller
mitigation than failover and a deliberate trade.
