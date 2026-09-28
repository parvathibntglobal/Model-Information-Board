# The undertaking does not void on derived publication, and that is the problem

**Raised 2026-09-17 by anooj + Claude. `contract/` — proposed, not taken.**

The position changed: we will not publish platform content directly, but we
will use what we gather to write Reddit posts, independent blogs and social
posts. This is what that does to the terms machinery.

---

## 1 · The undertaking does NOT void by its own terms

**Correcting the framing this started from**, because the distinction decides
what has to be done: *`voided_by` does not name this case.* All four clauses
are about **access to the board**, and so are all four conditions:

```
conditions                    voided_by
  auth_walled:      true        an account issued to anybody outside the team
  external_users:   false       the URL published, linked or indexed anywhere
  publicly_linked:  false       the auth wall removed or bypassed on any surface
  monetized:        false       any payment taken for access to the board
```

Writing a Reddit post from gathered evidence issues no account, publishes no
board URL, removes no auth wall and takes no payment. **All four conditions
remain literally true**, which is exactly the reading you predicted somebody
would apply — except the text supports it. The second half of the framing is
the accurate one: the conditions speak to auth-walling and external users, and
**none of them covers derived publication.**

So what actually happens at runtime is that nothing happens:

```
_undertaking_basis()   -> "internal-development-only"     (all conditions hold)
observe_use_basis()    -> {"use_basis": "internal-development-only"}
8 of 10 rulings        -> use_basis precondition PASSES
```

**The harvest keeps running on a basis that has stopped being true, and no code
notices.** That is worse than a refusal: `#314`'s lesson was that a checker
blind to what it was not told about passes because the named thing behaved, and
this is the same shape one level up — the undertaking is not wrong about
anything it asserts, it just does not assert the thing that changed.

### Two mechanisms, and they disagree

There is a second gate, and it is not the undertaking:

> **WHAT COUNTS AS PUBLICATION** … A QUOTE FROM A PLATFORM, SHOWN WITH A LINK,
> TO SOMEBODY OUTSIDE THE TEAM.

Nine `RE-REVIEW REQUIRED BEFORE` triggers turn on that definition. Whether the
new activity trips it depends on a detail nobody has settled:

- derived posts that **quote** a platform and link it → the trigger fires;
- derived posts that carry only aggregates → the definition says explicitly
  that *"an aggregate over those words is not one — '7 voices, 2 platforms' is
  a count and publishes nothing quotable."*

So the undertaking **cannot** fire and the publication trigger **may**. Neither
is enforced in code — the triggers are prose in nine summaries, and the
undertaking is the only machine-readable half. **The half that runs is the half
that cannot see this.**

### What it would take to make it void, and the mechanism already exists

`_undertaking_basis()` voids on an **unknown key**, a **missing key**, or a
**wrong value**, with `required_conditions` read from the contract as the source
of truth. That is the designed way to say something new:

```yaml
required_conditions:
  ...
  derived_publication: false     # add to BOTH blocks
conditions:
  ...
  derived_publication: true      # -> wrong value -> undertaking-void
```

Adding it to `conditions` alone also voids, as an unknown key. **Either way the
void is deliberate and authored** — which is right, because the undertaking is
an assertion somebody signs, and no check can observe what the team intends to
publish next month.

**There is also a backstop nobody should rely on:** `asserted_on: 2026-09-15`
plus `review_valid_days: 30` expires it on **2026-10-15**, 28 days from today.
It will void on its own. Letting that happen would be the worst option — it
voids as a stale date rather than as a decision, and the harvest keeps running
until it does.

## 2 · Scope: the list is missing its largest member

The new scope is direct-access platforms only. Mapped against what the corpus
actually holds:

```
source        documents   claims   board entries   route          terms read?
github          3,403        79        69          api DIRECT     never — no key at all
hackernews      1,056       146       180          api DIRECT     recorded false
devto             494       560       715          api DIRECT     recorded false
huggingface       164         6         9          api DIRECT     recorded false
blog              121        20         0          feeds DIRECT   recorded false
arxiv               0         0         0          api DIRECT     recorded false
─────────────────────────────────────────────────────────────────
reddit          9,001       313       165          RapidAPI       out of scope
x                 118         0         0          RapidAPI       out of scope
```

**GitHub is direct-access, is the second-largest source, produces 69 board
entries, has never had a terms reading — and is not on the list.** Its ruling
carries no `basis`, no `use_basis` precondition and no `terms_document_read`
key at all, so it is the one platform that would not even show up as deferred.
It should be the fifth reading, and by corpus share it is the largest.

**arXiv is the opposite case: a ruling and zero documents.** Nothing has ever
been harvested from it. Reading its terms is real work with no current
evidence behind it, so it is the one to do last rather than first.

**dev.to is where the value is concentrated** — 494 documents but **715 board
entries**, the most of any source. If one reading is done first, the corpus says
it should be that one.

### One concern about putting RapidAPI out of scope, stated once

The RapidAPI route determines **who we contracted with for access**. It does not
obviously determine **whose content we would be republishing**. Derived writing
built on 9,001 Reddit documents is built on Reddit's users' words however we
obtained them, and Reddit's terms bear on that independently of the reseller.
Raising it once because the scoping decision is yours; it does not change any
of the work below, and I have scoped everything to your list.

## 3 · What the readings would cost — and the reading is not the gating item

**The gating item is the basis, not the documents.** Every ruling that permits
harvesting today does so on `internal-development-only`:

```
rulings naming a basis              8 of 10
rulings enforcing it as a live precondition   8
"internal-development-only" in contract/sources.yaml   26 occurrences
"RE-REVIEW REQUIRED BEFORE" triggers                    9
```

A terms reading produces a ruling, and a ruling needs a basis to rest on. **No
platform ruling can be written until the new basis has a name and a definition**,
because the sentence each one would carry — *"proceeds on an
internal-development-only footing"* — is the sentence that just became false.
Reading dev.to's terms on Monday and writing the ruling on Monday afternoon
would produce a ruling asserting a basis nobody has defined.

So the order is:

1. **Define the new basis.** What it permits, what voids it, and its
   `required_conditions`. This is the morning's work that actually blocks
   everything, and it is a `contract/` change needing two eyes.
2. **Re-assert or withdraw the undertaking** under that definition. Withdrawing
   with nothing to replace it stops all eight rulings — a correct refusal and a
   full harvest outage, so the replacement wants to be ready first.
3. **Then** the per-platform readings, which can run in parallel.

### Per-platform, what one reading actually involves

The reading is the short part. The deliverable is a ruling that
`assert_terms_reviewed` accepts, which is:

- the terms document read, dated, and **what it says about republication and
  derived use** recorded — not just "permissive";
- `recorded_evidence` keys, **and every source row updated to carry them**.
  This is a paired change: `_check_facts` refuses any source missing a key its
  ruling names, so adding `republication_permitted` to a ruling without adding
  it to that platform's row takes the platform offline. `terms_document_read`
  did exactly this to all nine blog feeds last week;
- `UNRESOLVED, DELIBERATELY RECORDED` — what the reading did not settle;
- `RE-REVIEW REQUIRED BEFORE` triggers under the new basis;
- two eyes.

**A realistic shape, stated as an estimate and labelled as one:** the four API
platforms are probably a morning of *reading* and a day or two of *ruling*,
because the ruling is where the paired change and the re-review triggers live.
The blogs are not four — they are **seven distinct class A publishers plus
Medium**, each its own publisher terms, and the class A ruling says so:
*"NO TERMS PAGE HAS BEEN READ FOR ANY OF THE NINE FEEDS."* That is the long
pole and it is not in the "four short documents" estimate.

### The assumption most worth testing first

**"Probably permissive" is the load-bearing assumption and it is unmeasured.**
I have read none of these documents and am not in a position to say. What the
existing rulings already record is that the question is narrower than
permissiveness in general:

> Articles are USER-AUTHORED and carry per-post licences. dev.to's own terms
> and the default article licence have not been read, so whether short
> quotation is permitted per article is UNANSWERED.

That is dev.to — the platform with the most board entries. Hacker News comments
and Hugging Face discussions have the same shape: **the platform's terms may
permit our access and still not be the document that governs a user's words.**
If one thing is read first to find out whether the plan holds, it should be that
question on dev.to, not the four in sequence.

## 4 · What is asked

1. Rule on the **new basis** — name, definition, `required_conditions`. Nothing
   else can start.
2. Decide whether the derived posts will carry **quotes with links**. It decides
   whether nine `RE-REVIEW REQUIRED BEFORE` triggers have already fired.
3. Confirm whether **GitHub** belongs in scope. On corpus share it is the
   largest direct-access platform and it is currently absent from every list.
4. Note that the undertaking **expires 2026-10-15** regardless, and that
   allowing it to lapse rather than be withdrawn would be a decision by default.

**Not proposed here:** any edit to `use_basis_undertaking`, any ruling, any
Substack work. Nothing in this document has been implemented.
