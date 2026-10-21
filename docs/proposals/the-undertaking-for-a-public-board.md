# The undertaking for a public board

**Proposed 2026-10-05 by anooj + Claude, on branch `anooj_001`. A `contract/`
change - proposed, not taken. Nothing in `contract/sources.yaml` is edited by
this document; the YAML below is the text a reviewer would apply.**

## Why this cannot wait

`use_basis_undertaking` was asserted on 2026-09-17 with `review_valid_days: 30`.
`collect/adapters/basis.py:_undertaking_basis` refuses once
`asserted_on + 30 days < today`, so **from 2026-10-18 every ruling that rests on
`internal-development-only` refuses**. That is eight of the nine rulings:
Reddit, arXiv, X, dev.to, Hacker News, Hugging Face and both blog classes. Only
`github-api-terms` has no basis precondition.

What that does in practice, from 2026-10-18:

- every Fetch button run harvests GitHub only; the other arms report `skipped`
  with the expiry as the reason (#491's path), and the run still goes green;
- the scheduler, if enabled, does the same for every model, every night;
- nothing already collected is touched - extraction of stored threads continues.

## Why the current block cannot simply be re-dated

1. **It is false today.** `derived_publication: false` asserts that *nothing
   derived from the corpus has been published outside the team*. `articles/`
   (a Reddit data pull with 3,654 links, 936 usernames and 170 quoted lines,
   plus X and arXiv reports) has been on the public repository's `main` since
   2026-09-01. Re-dating would sign a statement we know is untrue.
2. **It describes a board we are not building.** `auth_walled: true` and
   `publicly_linked: false` are conditions about the *board*. The agreed
   position (2026-10-05) is a public board that withholds Reddit, arXiv and X
   (`contract/publication.yaml`). The day the board is public, both conditions
   become false and the block voids itself.
3. **It forbids what we now intend.** Its own `voided_by` includes *"any
   derived post, article or social message published outside the team from
   material in this corpus"*. The derived-posts exception
   (`contract/publication.yaml` `derived_posts.may_draw_on_withheld: true`)
   publishes exactly that. The first blog post voids it.

## The proposal: a new basis, `public-board-withheld-sources`

The basis says what is actually true and what is enforced: **the board may be
public; material from the withheld sources never appears on it; derived posts
may draw on them but carry no link, handle or platform name; the internal view
stays behind a sign-in.** Every condition below is checkable by a person in
minutes, and three of them are enforced in code, which is what makes them
assertable.

```yaml
use_basis_undertaking:
  asserts: public-board-withheld-sources
  asserted_by: ""            # a PERSON signs - empty ships as a proposal and
  asserted_on: ""            # refuses, exactly as the 2026-09-15 block did
  review_valid_days: 30

  required_conditions:
    withheld_sources_off_public_board: true
    internal_view_auth_walled: true
    admin_not_public: true
    derived_posts_unattributed: true
    monetized: false

  conditions:
    # Every deployment reachable without a sign-in renders the public view:
    # PUBLICATION_VIEW unset there, so judge/publication.py withholds the
    # sources in contract/publication.yaml from the board, model pages,
    # /compare, /filtered and /documents/{id}/source.
    # Check: the public service's variables; tests/test_public_surfaces_withhold_sources.py.
    withheld_sources_off_public_board: true
    # Any deployment with PUBLICATION_VIEW=internal requires a sign-in and is
    # not published, linked or indexed. Check: open it in a private window.
    internal_view_auth_walled: true
    # /admin/* is not reachable on the public deployment.
    # Check: request /admin/settings there without a token.
    admin_not_public: true
    # Derived posts carry no link, handle or platform name for any source.
    # Enforced by generate_sample_blogs.py's export and banned-phrase checks;
    # check: grep the published drafts for http, u/, r/ and platform names.
    derived_posts_unattributed: true
    monetized: false

  voided_by:
    - a quote, link, handle or count from a withheld source shown on any
      surface reachable without a sign-in
    - PUBLICATION_VIEW=internal set on a deployment reachable without a sign-in
    - /admin reachable on the public deployment
    - a derived post published with a link, handle or platform name
    - any payment taken for access
```

**What it changes in the rulings.** A ruling passes only if the observed basis
is in its `use_basis` list. Substituting the new name into the eight lists is
NOT proposed, because each was granted against the narrower internal use and
none carries over by substitution (the reasoning of
`the-derived-publication-basis.md` §4 holds here too):

| ruling | what a reviewer must decide before adding the new basis |
|---|---|
| `reddit-via-rapidapi`, `x-via-rapidapi-scraper`, `arxiv-api-terms` | collection continues; board shows nothing; **derived posts with verbatim «» fragments** draw on them - does each source's terms reading permit that? |
| `devto-api-terms`, `hackernews-algolia-terms`, `huggingface-api-terms`, `blog-class-a-self-hosted`, `blog-class-b-medium` | the public board WILL show their quotes and links - each needs a republication reading (quote + link) first. Until read, add the source to `contract/publication.yaml`'s withheld list, or keep it off the new basis |

## Order of operations

1. Review this document and `public-surfaces-withhold-reddit-arxiv-x.md`
   together - they are one decision.
2. A person reads each ruling above against the new basis and records it,
   adding `public-board-withheld-sources` to that ruling's `use_basis` only
   where the reading permits.
3. Apply the block, signed and dated by a person.
4. Merge before **2026-10-18**. If that slips, harvesting other than GitHub
   stops on 10-18 by design, and the fetch logs say so - an outage that names
   its cause, not a silent one.

## The dates that follow signing

Signing clears 2026-10-18 and nothing after it. The gate
(`collect/registry/assertions.py`) also refuses a ruling once
`reviewed_on + review_valid_days` has passed, and re-checks every live
precondition on every run. Read from `contract/sources.yaml` on 2026-10-05:

| what | expires | if missed |
|---|---|---|
| the new undertaking | 30 days after it is signed (2026-11-17 if signed 10-18) | all eight non-GitHub rulings refuse |
| `github-api-terms` | **2026-11-11** | GitHub refuses - the one source the undertaking does not cover |
| `blog-class-b-medium` | 2026-11-12 | that source refuses |
| `reddit-via-rapidapi` | 2026-11-16 | that source refuses |
| `arxiv-api-terms`, `x-via-rapidapi-scraper` | 2026-12-07 | that source refuses |
| `devto-api-terms`, `hackernews-algolia-terms`, `huggingface-api-terms` | 2026-12-08 | that source refuses |
| `blog-class-a-self-hosted` | 2026-12-20 | that source refuses |

Two more ways to refuse, on any day:

- **a live precondition fails** (X's credential or provider, a blog's
  `robots.txt`, an access path): that source only, named in the run's log;
- **a signed condition stops being true** - the public deployment set to
  `PUBLICATION_VIEW=internal`, `/admin` reachable publicly: the undertaking
  voids and all eight refuse at once, by design.

Each refusal is a `skipped` arm with its reason, never an error, so a run stays
green while collecting less. With the scheduler on, that is a nightly batch
shrinking quietly unless somebody reads the summaries - the November dates
want a calendar entry, not a memory.

**Before the board goes public**, also: the notice rendered on the page
(`sources_withheld` has no UI reader yet), `/admin` blocked, and the cell
phrases/counts recomputed without withheld voices - all listed in
`public-surfaces-withhold-reddit-arxiv-x.md`.
