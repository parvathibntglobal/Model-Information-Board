# Proposal: a recorded undertaking, read instead of `ENVIRONMENT`

**Proposed 2026-09-15 by anooj + Claude. `contract/` needs two eyes — this is
proposed, not taken.**

---

## The problem, stated precisely

The hosted backend refuses Reddit, arXiv and X on NFR-5. Measured on run
`mv_b3508133423993d7-63cc3e42`, machine `dbdf571f8b13`, 2026-09-14 13:38Z:

```
E2R  Harvest · Reddit   error    Refusing to harvest: 1 source(s) failed the NFR-5 terms check (reddit):
E2A  Harvest · arXiv     skipped  Refusing to harvest: 1 source(s) failed the NFR-5 terms check (arxiv):
E2X  Harvest · X         skipped  Refusing to harvest: 1 source(s) failed the NFR-5 terms check (x):
```

Those three are exactly the rulings that carry `use_basis` as a
`live_precondition`. `observe_use_basis()` returns
`internal-development-only` unless `ENVIRONMENT == "production"`, the container
runs `production`, so the basis reads false and the ruling refuses.

**The rulings are right and the refusal is correct.** What is wrong is the
instrument.

`ENVIRONMENT` is a **deployment mode**. The rulings turn on **who can reach the
site**. Those are different facts, and one is being used to answer the other.
`collect/adapters/basis.py` says so itself, in its own docstring, before any of
this happened:

> ⚠ IT IS A PROXY, AND SAYING SO IS THE WHOLE VALUE OF THIS DOCSTRING.
> `ENVIRONMENT` is the only signal the process has. […] it does NOT catch:
>   - a staging instance that has acquired external users
>   - a local build shown to somebody outside the team
>   - anything at all about PUBLICATION, which is what the rulings actually
>     turn on
>
> Publication is a property of who is looking at a page. **No environment
> variable knows that.**

So the file already named the gap. This proposes closing it the way the same
docstring implies: *"not a substitute for a person honouring the condition"* —
so **let a person state it, with a name and a date, and have the observer read
the statement.**

---

## The shape

### 1 · The undertaking, in `contract/sources.yaml`

```yaml
use_basis_undertaking:
  asserts: internal-development-only
  asserted_by: parvathi
  asserted_on: 2026-09-15
  review_valid_days: 30

  #: WHAT IS BEING ASSERTED, in the terms the rulings use. Each of these is a
  #: fact a person can check in ten minutes and no process can check at all.
  conditions:
    auth_walled: true          # every reachable surface requires a sign-in
    external_users: false      # nobody outside the team has an account
    publicly_linked: false     # the URL is not published, indexed or shared
    monetized: false

  #: WHAT VOIDS IT, BEFORE THE DATE. Any one of these ends it immediately and
  #: the undertaking must be re-asserted or the rulings stop applying.
  voided_by:
    - an account issued to anybody outside the team
    - the URL published, linked or indexed anywhere
    - the auth wall removed or bypassed on any surface
    - any payment taken for access to the board
```

**Why in `sources.yaml` rather than a new file.** The rulings that depend on it
are in that file, the loader already reads it, and it is the one document that
means *"the terms agreement"*. A reviewer changing a ruling sees the undertaking
in the same diff. The counter-argument is real and worth hearing: an undertaking
is a **person's assertion about the world**, not a reading of terms, and it
renews on a different cadence — a separate `contract/undertaking.yaml` would say
that more clearly. I have taken the single-file version; say if the split reads
better.

### 2 · The observer reads it

`observe_use_basis()` stops consulting `settings().environment` and returns the
undertaking's `asserts` value when the undertaking is present, unexpired and
self-consistent — and a **named refusal value** otherwise, so the gate's error
says which of those failed rather than only that a precondition did:

```
"use_basis": "internal-development-only"                      # undertaking holds
"use_basis": "no-undertaking (contract/sources.yaml)"         # absent
"use_basis": "undertaking-expired (asserted 2026-09-15, expired 2026-10-15)"
"use_basis": "undertaking-void (external_users: true)"
```

**Absent is not permissive (rule 6).** No undertaking means no basis, means
every one of the eight rulings refuses. That makes the default *refuse*, which
is the correct direction and the opposite of today's default.

**This also removes a live defect rather than only a proxy.** Today
`ENVIRONMENT` unset observes as internal, so a misconfigured container harvests
under a basis nobody asserted. Under the undertaking a misconfigured container
harvests nothing.

### 3 · What invalidates it

You asked for this explicitly and it is the half that decides whether the
undertaking is worth having.

| | |
|---|---|
| **A date** | `asserted_on`, so an undertaking is always attributable to a moment |
| **A review interval** | `review_valid_days: 30`, expiring **far sooner than** `review_valid_days: 90` on the rulings themselves. The undertaking is about a fact that can change in an afternoon; a terms reading is about a document that changes in months. |
| **Named voiding conditions** | `voided_by`, listed above — any one ends it before the date |
| **A person** | `asserted_by`, because *"somebody reviewed this"* is not a fact anyone can follow up — the same reason `reviewed_by` exists on a ruling |

30 days is proposed rather than derived. The argument for shorter: the thing it
asserts is one careless link away from false. The argument for longer: an
expiry that fires constantly gets renewed without being re-checked, which is
worse than a longer one that is read. **Your call.**

**The self-consistency check matters as much as the expiry.** An undertaking
that says `asserts: internal-development-only` while `external_users: true` is
contradicting itself, and the loader should refuse to parse it rather than
letting the `asserts` line win. Same shape as the existing check that a source
naming a ruling must not still carry `REVIEW REQUIRED` in its notes.

---

## Closing the eight-declare, three-enforce gap

**Eight rulings name `basis: internal-development-only`. Three list `use_basis`
as a `live_precondition`.**

| ruling | names the basis | enforces it |
|---|---|---|
| `reddit-via-rapidapi` | yes | **yes** |
| `arxiv-api-terms` | yes | **yes** |
| `x-via-rapidapi-scraper` | yes | **yes** |
| `devto-api-terms` | yes | no |
| `hackernews-algolia-terms` | yes | no |
| `huggingface-api-terms` | yes | no |
| `blog-class-a-self-hosted` | yes | no |
| `blog-class-b-medium` | yes | no |

`TermsRuling.basis`'s own docstring already asks for this:

> Where a basis is named it should also be a `live_precondition`, so the fuse is
> checked rather than remembered.

It is a **should**, and the loader enforces nothing. The consequence is
measurable: on 2026-09-14 the same container refused Reddit and **harvested 60
dev.to items**, under the identical sentence in both rulings.

### Two changes, and the second is the one that lasts

1. **Add `use_basis: [internal-development-only]` to the five that lack it.**
   Mechanical.
2. **Make the loader refuse a ruling that names a basis without enforcing it.**
   This turns the *should* into a *must* and stops the gap reopening the next
   time somebody adds a ruling. Without it, change 1 is true until the next PR.

```python
if ruling.basis and ruling.basis not in (ruling.live_preconditions.get("use_basis") or ()):
    raise SourcesContractError(
        f"ruling {ruling.id!r} names basis {ruling.basis!r} and does not "
        f"enforce it. A named basis must be a live_precondition, or it is a "
        f"sentence rather than a fuse — eight rulings named one and three "
        f"checked it on 2026-09-14, and the same deployment refused Reddit "
        f"while harvesting dev.to."
    )
```

**Then all eight harvest or none do**, on the undertaking rather than on which
ruling happened to list a precondition. That is the point of the change: not
that more sources harvest, but that the answer stops depending on an
inconsistency.

---

## What this does NOT do, recorded so it is not mistaken for a clearance

**The durable answer is reading the terms, and this is not that.**

`terms_document_read: false` is recorded on **arXiv, X, dev.to, Hacker News and
Hugging Face**. Those readings were deferred deliberately while the project is
internal, and the deferral is written into each ruling rather than left as an
absence. Reddit is worse than deferred: four conditions are **unresolved**, two
of them direct conflicts with design decisions in this repository
(`Developer Terms 5.2` vs `author.handle_hash`; `Data API Terms 3.2` vs the
immutable store), escalated to the MD on 2026-08-18.

**The undertaking makes the current state honest. It does not make the reading
unnecessary, and it must not be allowed to feel like it has.** Its 30-day expiry
is partly for that: an undertaking that has been renewed four times is a visible
count of how long a deferral has run.

`RE-REVIEW REQUIRED BEFORE: any external publication, any external user, any
monetization` already appears in every one of these rulings. The undertaking
asserts that none of those has happened yet — it says nothing about what to do
when one does, which is still to read the terms.

---

## Meanwhile: the hosted backend is the constraint, not the UI

Worth saying plainly, because it is easy to read this as blocking work.

**A local backend harvests everything today.** `.env` is
`ENVIRONMENT=development`, the basis observes as internal, and all eight rulings
pass — the DeepSeek V4 Pro run on 2026-09-15 harvested Reddit (225 documents),
dev.to (50), Hacker News (77), Hugging Face (21), X (8) and GitHub (5) without a
single terms refusal.

**The UI can point at it.** `web/.env` takes `VITE_API_URL`, so the frontend
runs against `http://127.0.0.1:8000` with no code change.

So nothing here is blocked on this proposal. What is blocked is *the hosted
backend harvesting*, and that is the only thing.

---

## Summary of what is being asked

| | |
|---|---|
| **Decide** | is the undertaking true, and will you assert it by name? |
| **Decide** | `review_valid_days: 30` — too short, too long, or right? |
| **Decide** | one file or two — `sources.yaml`, or a separate `undertaking.yaml`? |
| **Review** | the loader change that makes a named basis a must rather than a should |
| **Note** | five rulings still carry `terms_document_read: false`, and this does not change that |
