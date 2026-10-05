# Public surfaces withhold Reddit, arXiv and X

**Proposed 2026-10-05 by anooj + Claude, on branch `anooj_001`. A `contract/`
change - proposed, not taken; it reaches `main` only through a reviewed PR.**

## The position

Agreed by the team on 2026-10-05:

> Nothing from Reddit, arXiv or X is published on our public platform. We may
> still collect from them for internal work; we do not intend to publish from
> them in any form.

This replaces the plan in #494's ops note ("repo private, the file gone, the
undertaking re-signed") as the answer to the terms problem that has kept the
scheduler off. The repository is expected to move to a private account; the
platform itself is what goes public.

"Any form" is read as widely as it can be: no quote, no link, no handle, no
derived prose (blog drafts included), and no count that includes them.

## What this branch implements

| | where |
|---|---|
| the list, as data | `contract/publication.yaml` - `withheld_from_public.sources: [reddit, arxiv, x]` |
| the one reader | `judge/publication.py` - `withheld_sources()`, `view()`, `withheld()`, `notice()`, `sql_public_document()` |
| board and capability pages | `judge/store/board_entries.py` `board_sections` - withheld rows skipped, counted under `_withheld_sources` |
| model evidence | `judge/store/board_entries.py` `evidence_for_model` - filtered in SQL so withheld rows cannot use up the `LIMIT`; counted under `withheld_sources` |
| `/compare` | `judge/app.py` - polarity, document, platform and reply counts exclude withheld sources |
| `/documents/{id}/source` | `judge/app.py` - a withheld document is refused (404), naming no platform |
| `/filtered` | `judge/pages/filtered.py` - withheld documents neither listed (their URLs) nor counted |
| models list | `judge/pages/roster.py` - board-entry counts exclude withheld sources |
| legacy claim quotes on a model page | `judge/pages/model.py` `quotes_for` - withheld quotes and permalinks not returned |
| blog drafts | `generate_sample_blogs.py` - a thread with ANY member from a withheld or unknown source is never selected, and subjects qualify on public threads only. Applies whatever the view, because blogs are public by design |
| tests | `tests/test_public_surfaces_withhold_sources.py` (11) |

**The view.** `PUBLICATION_VIEW` is `public` or `internal`. Unset means
`public`: a deployment that forgot to say what it is withholds, the safe
direction (an over-withheld page is visible and arguable; a published quote
cannot be taken back). Anything else raises (rule 12). The team's own board sets
`internal` and loses nothing.

**Unknown provenance is withheld** on a public view - a row whose document has
no source is not a row we can say is publishable (rule 6).

**Withholding is said, not silent (rule 4).** Payloads carry
`{"view", "sources_withheld", "entries"}`. The platforms are not named, keeping
the team's standing rule that public material names no source platform.

## What it does NOT cover yet - each is open work

1. **The legacy cell path.** `cell` / `cell_current` phrases and counts were
   computed from claims that include withheld voices. `/ask/recommend`, the
   capability phrases on `/models/{id}`, `/capabilities/{key}` and `/changelog`
   read cells. Their QUOTES are now withheld (`quotes_for`), but a phrase like
   "7 people report..." still counts Reddit voices. Fix: recompute cells over
   public claims for the public view, or hide cells there.
2. **The notice has no reader yet (rule 9).** `_withheld_sources` /
   `withheld_sources` are produced and not rendered. Intended reader:
   `web/src/board/views.js` beside `withheldNote()`, one line saying some
   sources are not shown here. Until it exists, a public page that lost rows
   reads as a page with fewer reports - rule 4's failure, so this should land
   before the platform is public.
3. **`/admin/*` is not gated** and must not be reachable on the public
   deployment at all; it is review tooling over the whole corpus.
4. **The other five sources are not cleared for publication by this.** Blogs
   (both classes), dev.to, Hacker News and Hugging Face rulings all rest on
   `basis: internal-development-only` today, exactly like the three withheld
   here. Showing their quotes and links publicly needs each source's terms
   read for republication (quote + link). Until each is read, the safe launch
   list is wider than three. **Reviewer decision.**
5. **The undertaking in `contract/sources.yaml` expires 2026-10-17.** Its
   conditions describe an auth-walled board that nobody outside the team can
   reach. A public platform makes `auth_walled: true` and
   `publicly_linked: false` false, which voids it and every ruling resting on
   it - all non-GitHub harvesting stops. It needs replacing before either the
   expiry or the launch, whichever is first: a basis for the withheld three
   that says "collected, never published, enforced by
   `judge/publication.py`", and per-source publication rulings for the rest.
   Re-dating the current block is not an option: `derived_publication: false`
   was not true while `articles/` was public.
6. **Files with platform material are still on `main`**, and all of it stays in
   history until the repository moves. This branch deletes `articles/` (the
   platform pulls, last at `4eab55a`) and 9 blog drafts drawn from Reddit.
   Still on `main` as of 2026-10-05: 9 files in `docs/measurements` (~2,560
   platform links), 5 in `fixtures/golden` (~889), 3 in `fixtures/reddit`, 1
   in `fixtures/threads`. The fixtures are test inputs; whether they stay
   until the move is a decision, not a cleanup.
7. **The blog generator only sees pre-#502 evidence.** It joins `board_entry`
   to `claim`, and entries written since #502 have no claim row. Unrelated to
   publication, found while testing this.

## Reviewer questions

- Is "no count that includes them" the reading we agree on? It is the widest;
  the narrower one (quotes and links only) would keep counts honest about
  volume but publish something derived from the three.
- Which of blogs, dev.to, HN and Hugging Face are cleared to show quotes and
  links publicly, and on whose reading?
- Does the public deployment set nothing (public by default) and the internal
  board `PUBLICATION_VIEW=internal`? Who sets them, on which service?
