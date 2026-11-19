# Post formats on the platforms we fetch, measured 2026-11-18

Asked for by anooj, 2026-11-18: research the format of posts (not comments) on
the platforms we have fetched data from, and update the content workspace's
rules from it.

## Population (rule 7)

- **Posts, never comments:** `document.parent_id IS NULL`. X and Bluesky
  payloads that are replies were dropped too.
- **Only posts our fetches retrieved**, which are search and listing results
  that name a tracked model or agent. This is not a platform-wide sample.
  - X was searched mostly by `Top`, so its pool leans to popular posts.
  - Reddit and Bluesky were searched by recency.
- **Dates:** created 2026-08-01 to 2026-11-18. The shared DB was read
  read-only on 2026-11-18.
- **Sample:** random, seed 20261118, 400 per source. Hugging Face had 325,
  because its pool is 337.
- **Unreadable payloads were counted, not guessed:** reddit 3, hackernews 22,
  devto 8, huggingface 12.
- **Engagement is as of fetch time.** The measure per platform:
  - Reddit: score;
  - X: likes;
  - Bluesky: likes;
  - HN: points;
  - dev.to: reactions;
  - GitHub: upvotes;
  - forum: replies;
  - Hugging Face: comments.
- **Engagement is usable on Reddit, X and HN only.** For dev.to, Bluesky,
  forum, GitHub and Hugging Face the median is 0 or 1, so their quarters
  describe shape, not performance.

## Files

| File | What it holds |
| --- | --- |
| `profile.py` | Reads the payloads in bulk from `raw_blob` and skips tombstoned refs. Writes one feature row per post, with no text. |
| `summarise.py` → `summary.out.txt` | Shape per source. Top quarter vs bottom quarter by engagement. |
| `controls.py` → `controls.out.txt` | Confound checks. |

The confound checks:

- **X, likes per view** (posts with 500 or more views, 291 of 400). This
  partly removes account reach.
- **Reddit, score within each subreddit** (subreddits with 15 or more sampled
  posts, 7 of them).
- **HN, link stories only**, by title colon and title length.

The posts' text was read for the qualitative notes from a scratch file that
was not kept: it is users' verbatim text.

## Findings that survived the confound checks

### X

- Media did not lift likes per view: photo or video 10.4 per 1,000 views, text
  9.9. The media lead in the top quarter was the reach of the big accounts.
- Hashtags: 5.0 likes per 1,000 views with one (n=18), 10.6 without.
- Long posts (over 280 characters): 10.8 vs 8.6 likes per 1,000 views.
  Bookmarks per 1,000 views: 4.4 vs 1.4.
- A list of short lines: 13.0 vs 9.3 (n=75).

### Reddit

- Image, video and gallery posts beat text posts on median score in all 7
  subreddits.
- Question titles scored lower in 5 of 7, and about level in the other 2.

### Hacker News

- Titles of 50 characters or fewer: median 199 points (n=179). Longer titles:
  146 (n=167).
- A colon in the title made no difference: 185.5 vs 182.5.

## Confounds that were refused

- **Digits in Reddit titles** (88 of the top 100 vs 51 of the bottom 100).
  Model names carry digits, so this measures nothing (the `_HAS_QUANTITY`
  lesson, CLAUDE.md rule 12).
- **The X top quarter's media share.** It is reach, as the likes-per-view
  check shows.

Every rule added from this is `warn` or `manual`, never `fail`: these are
correlations in one sample (rule 8).
