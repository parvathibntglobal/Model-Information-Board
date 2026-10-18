# Proposal: add Hugging Face Papers search to the `huggingface-api-terms` ruling

**Status:** proposed 2026-10-18 by anooj. Needs a second reviewer (contract/ gets two eyes).
**Changes:** `contract/sources.yaml`, the `huggingface-api-terms` ruling summary only.
No change to the gate, the basis, or any other ruling.

## What is being asked

The blog's topic harvest (`scripts/harvest_topics.py`, 2026-10-18) now calls
`GET https://huggingface.co/api/daily_papers?date=<YYYY-MM-DD>` - the papers
Hugging Face features each day - through
`collect/adapters/huggingface.py:HuggingFaceHarvester.daily_papers`. (Papers
search was tried first and dropped the same day: relevance-ordered, 25 of 750
hits were inside the window, and it drew 56 HTTP 429s.)

The ruling as written (2026-09-09, parvathi) describes the access as:

> the documented public API at huggingface.co/api - repo search and the
> discussions endpoints - never the site HTML and never model weights.

Daily papers is the same documented JSON API under `/api`, unauthenticated,
read-only, and returns metadata (arXiv id, title, abstract, authors, date,
upvotes). It is not one of the two endpoint families the summary names. So the
code is ahead of the ruling's wording, and this proposal brings the wording up
to the code rather than leaving the gap for a reader to find.

## Proposed wording (replace the first paragraph of the summary)

> RULED 2026-09-09; AMENDED <date> (<reviewer>). Access is the documented public
> API at huggingface.co/api - repo search, the discussions endpoints, and Papers
> search (`/api/papers/search`, metadata of arXiv papers as Hugging Face lists
> them) - never the site HTML and never model weights.

Everything else in the ruling stands unchanged: the internal-development-only
basis, the unread Terms of Service and Content Policy (still recorded as unread),
robots.txt unchecked, and re-review before any external publication.

## What the reviewer should check

1. **Content ownership.** A daily-papers item is an arXiv paper's metadata. The
   abstract text is the authors', distributed by arXiv; Hugging Face adds the
   page, upvotes and comments. A post quoting the abstract should credit the
   paper (as the arXiv path already does, with arXiv's acknowledgement), not
   Hugging Face. Today the harvester skips a daily-papers item whose arXiv id the
   arXiv arm already stored, so most papers enter through arXiv's own ruling.
2. **Rate.** One request per day of the window (`platforms.window_days`,
   30 on 2026-10-18 - 30 requests a run), spaced by the adapter's existing
   `HostLimiter`. No pagination.
3. **Nothing is published.** As with every other platform here, the position
   holds only while nothing derived is shown outside the team.

## If the amendment is refused

Set `platforms.huggingface_papers` aside in `blog_topics.yaml` (remove the key;
the harvester then refuses the run loudly, rule 12) or drop the arm from
`harvest_platforms`. No stored item depends on it: rows are `topic_item` with
`source = 'huggingface'` and `id` prefixed `hfpapers:`, deletable by that prefix.
