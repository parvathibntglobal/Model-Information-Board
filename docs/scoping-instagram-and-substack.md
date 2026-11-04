# Scoping: Instagram and Substack as sources

**2026-11-04.** Asked: scope Instagram (through the RapidAPI key now in `.env`)
and Substack as sources, for each kind of fetch: evidence (the board's
reports), model information, and blog material. Also: how much Substack
content we get today, and whether Substack scraping is worth it. Terms are
not treated as a blocker here (as asked, and as we treat terms findings
generally).

Every figure below says what it counts. All probes were read-only and small:
Instagram 2 API calls (of a 15,000-a-month plan), Substack 3 feeds, 2
robots.txt files, 1 sitemap and 1 search call.

## Two things this touches, and who decides

- **CLAUDE.md, "Stack decisions": "Official APIs and public feeds only - no
  scraping."** Instagram has no official route to public hashtag posts, so any
  Instagram source is a third-party scraper. That is also true of our X route,
  which went through a ratified contract entry (`x-via-rapidapi-scraper`,
  2026-09-08). Substack's RSS feeds are public feeds and fit the rule as
  written. Substack's back catalogue and discovery do not.
- **Correction, same day: Substack by feed is already allowed on `main`.**
  The ruling `newsletter-substack-feed-only` was seated 2026-10-26 as a team
  decision. This document first quoted the 2026-09-18 refusal from an older
  local checkout of `contract/sources.yaml`. On `main`, the three Substack
  feeds were removed 2026-10-30 for a different reason: Substack's robots.txt
  refuses the scheduled runner but answers developer machines normally. See
  `docs/proposals/substack-feeds-back-and-seeded.md`.

## Substack

### What we get today

| | Count | What it counts |
|---|---|---|
| Documents at a `substack.com` address | **60** of 61,470 | All documents in the shared database, 2026-11-04 |
| Publications they come from | **3** | cameronrwolfe, chinai, epochai, 20 posts each, fetched as blog feeds |
| Passed triage | **37** of 60 | 23 dropped |
| Board entries from them | **0** | None has been extracted |
| Threads that link a `*.substack.com` post | **34** of 9,587 | Flattened thread texts on this machine; about 25 publications |

The last row is a lower bound. Substacks on their own domains (Latent Space,
One Useful Thing, Interconnects) don't contain "substack.com" in the link.

**So Substack contributes nothing to the board today.** The 37 kept posts are
the cheapest first step: extract them and see what they yield.

### How it can be fetched

| Route | What it gives | Rule status |
|---|---|---|
| **RSS feed** (`/feed`) | Full text of free posts, **the latest 20 per publication**. Gary Marcus: 20 posts back to 23 Sep 2026, median about 2,300 characters. Cameron Wolfe: 20 posts back to Jul 2025, median about 75,000 characters. | A public feed. Fits the rule, and allowed by `newsletter-substack-feed-only` on `main`. The open problem is that the scheduled runner is refused by robots.txt. |
| **Sitemap + post pages** | The whole back catalogue. Gary Marcus's sitemap lists **627 posts**. | Fetching post pages is scraping. robots.txt allows `/p/` pages; it blocks comments, private feeds and sign-in. |
| **Discovery** | Which publications exist | Substack's search returned nothing to an outside caller. Discovery starts from the ~25 publications our own corpus links, the 3 we already fetch, and a curated list. |

**A nightly RSS read misses nothing new.** A publication rarely posts more
than 20 times between nightly reads. **Scraping only buys history:** a
one-time backfill per publication.

### By kind of fetch

| Fetch | Value | Notes |
|---|---|---|
| **Evidence** | **High per post.** Long-form, first-hand tests and critiques by named authors. | Long posts cost more to extract. Our $0.00208 is per thread; a 75,000-character post is many threads' worth. Measure on 10 posts before committing. Quotes come from the post text, so verification works as it does for blogs. |
| **Model information** | **Medium.** Newsletters cover launches within days. | Useful as a launch signal and for release-week reactions. Not a replacement for the registry. |
| **Blog** | **High.** Ideas, arguments and linkable sources for our posts. | Linking to a Substack post is allowed whatever we decide about fetching it. |

## Instagram

### The route

RapidAPI **"Instagram Looter"** (`instagram-looter2.p.rapidapi.com`), a
third-party scraper; Instagram has no official public-search API open to us.
The plan allows **15,000 requests a month**. Two endpoints worked on the first
try:
- `/search?query=` returns accounts.
- `/tag-feeds?query=<hashtag>` returns 32 recent and 9 top posts per page,
  with more pages.

Each post carries its caption, timestamp, owner, likes and comment count.

### What the posts say

From the 41 posts one `/tag-feeds` call returned for **#claudeai** (10 Aug to
4 Nov 2026). Instagram counts 351,029 posts on that tag.

| | Count, of 41 |
|---|---|
| Name a model | 38 |
| **Read like first-hand use** ("I used / tried / built / switched…") | **4** |
| Carry promotion markers ("link in bio", "comment X", "save this"…) | 9 |
| Not in English | most of the first 12 read (Chinese, Spanish, Polish, German, French) |

Median caption: about 820 characters. Most are **news recaps and creator
carousels**, and the real content is often in the slide images, which a
caption doesn't capture. Now and then there is a genuine small test (a French
post comparing free Gemini and others on reading a quote, dated 4 Nov). That
is one sample of one hashtag (n=41), so it is a first look, not a rate.

### By kind of fetch

| Fetch | Value | Notes |
|---|---|---|
| **Evidence** | **Low.** About 1 in 10 posts in the sample is first-hand, against heavy promotion. | Would need triage to weight promotion and language (as weights, never gates: rule 8). Treat it like Reddit and X: counted, not quoted, until publication is decided. |
| **Model information** | **Low.** Secondhand news ("Anthropic filed an S-1"). | Not a dependable source of release facts. |
| **Blog** | **Medium.** Shows what non-engineers and creators are saying and sharing. | Good for topic discovery and the "I make things" audience. Embedding posts in a blog needs Meta's official embed (an app token). |

**Volume, if trialled:** 10 hashtags, one page each per day, is about 300
calls a month (2% of the plan) and about 320 posts a day. At the sample's
first-hand share, that's roughly 30 candidates a day before triage.

## Recommendation

1. **Extract the 37 Substack posts we already hold.** Tried 2026-11-04: their
   text is only on the machine that harvested them by hand on 27 Oct, so it
   has to run there. Folded into the proposal in step 2.
2. **Substack by RSS for a seed list.** Proposed in
   `docs/proposals/substack-feeds-back-and-seeded.md`: 20 publications, picked
   from 27 by a stated rule, harvested from a developer machine. The ruling
   already allows feeds; the proposal adds the feeds and says where they run.
3. **Back-fill Substack history by sitemap only if step 2 earns it.** That is
   scraping, so it needs the stack rule changed as a team decision.
4. **Instagram as a two-week trial aimed at the blog,** on 3 to 5 hashtags.
   Measure the first-hand share on a population we didn't choose before it
   feeds the board at all. A scraper route needs the same contract entry X
   got.

## What was run

Probe scripts are in the session scratchpad and are not committed:
`ig_probe.py` (2 calls) and the Substack feed, sitemap and search checks.
Database counts were read through the read-only option on 2026-11-04.
