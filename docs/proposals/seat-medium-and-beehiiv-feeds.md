# Proposal: seat four Medium feeds and one beehiiv newsletter

**For review by Parvathi. Proposed 2026-11-05 (anooj).** A `contract/`
change, so nothing is edited until it's agreed.

## The ask

Add five feed rows to `contract/sources.yaml`, under rulings that already
exist. No ruling changes.

| Row | Ruling |
|---|---|
| `blog:medium.com/google-cloud` | `blog-class-b-medium` |
| `blog:medium.com/google-developer-experts` | `blog-class-b-medium` |
| `blog:medium.com/mongodb` | `blog-class-b-medium` |
| `blog:medium.com/pinterest-engineering` | `blog-class-b-medium` |
| `blog:www.theunwindai.com` | `newsletter-beehiiv-feed-only` |

Both rulings are feed only (`fetch_articles: false`), so no article page is
ever requested. Each row gets the same `terms_evidence` and `measured`
blocks as the other blog rows. Per the team's position, terms are recorded,
not a reason to hold a feed back.

## Why

**Blogs feed the board, but only from blogs that name models.** Blog feeds
are harvested nightly and never searched per model. When a model is fetched,
its extraction step also reads stored posts that name it, blogs included.
From the shared database, read-only, 2026-11-05:

- 234 of the 1,015 stored blog posts have been through extraction, and 19
  of them carry 102 claims about 23 models.
- Nearly all of those claims come from five self-hosted blogs:
  simonwillison.net 35, slack.engineering 25, jack-clark.net 22,
  minimaxir.com 15, eugeneyan.com 4.
- **The two Medium feeds we seat today name no model**: Airbnb 0 of 10 and
  Netflix 0 of 10 on the measure below. Medium currently gives the board
  nothing to extract.

So the test for a new feed is how often its posts name a model, and the
first-run figures below are that test.

## How the candidates were measured

`docs/measurements/medium-beehiiv-feeds-2026-11-05.py`. For each candidate:
its robots.txt, then its feed. For beehiiv, the homepage was also read once,
only to find a feed link. Nothing was stored, and no article page was
requested.

- **Names a model** counts entries whose title or body names one of 13 model
  families, as an exact case-sensitive word. It is the measure the seated
  newsletter rows use. It counts mentions, not first-hand reports; extraction
  decides which posts carry reports.
- **The window is what the feed serves**: Medium gives the latest 10 posts,
  beehiiv the latest 20. Every rate is over that window, never over the
  whole publication.

## The five proposed

All are full text in the feed (no members-only stubs) and robots.txt
allows the feed path.

| Feed | Names a model | Window | Bylines | Note |
|---|---|---|---|---|
| medium.com/google-cloud | 6 of 10 | 4–5 Nov | 10 | Busy: 10 posts in about a day and a half |
| medium.com/google-developer-experts | 6 of 10 | 14 Oct – 4 Nov | 7 | |
| medium.com/mongodb | 5 of 10 | 8–30 Oct | 1 | One company byline on every post |
| medium.com/pinterest-engineering | 3 of 10 | 26 Aug – 4 Nov | 1 | One of the five the contract named on 2026-08-14 as "first candidates to add" |
| theunwindai.com (beehiiv) | 19 of 20 | 28 May – 29 Sep | 2 | Newest post 36 days old: may have stopped |

Three things for review:

- **Google Cloud posts several times a day.** A nightly read of its latest 10
  keeps up at that pace, but a night the run is skipped loses whatever falls
  past the tenth post.
- **MongoDB and Pinterest post under one company account each**, so every
  claim from either resolves to one voice. That's a count of one, however
  many posts there are.
- **Unwind AI hasn't posted since 29 Sep.** I'd re-check it when seating, and
  drop it if there is still nothing new.

## Checked and not proposed

**Medium, from the 2026-08-14 candidate list:**

- tech.instacart.com: 4 of 10, newest 3 Sep.
- eng.lyft.com: 4 of 10, newest 10 Sep.
- craft.faire.com: 1 of 10, newest 3 Sep.
- expedia-group-tech: 0 of 10.

Instacart and Lyft name models but have posted nothing in about two months.
Worth a re-check later rather than a row now.

**Medium engineering blogs that rarely name a model (0 to 2 of 10):**
Booking, Razorpay, Wise, Strava, Walmart, Myntra, Neo4j, PayPal, Udemy.

**Medium publications whose feed is mostly stubs** (members-only posts cut
to a teaser):

- data-science-collective: median body 195 characters.
- generative-ai: 164.
- towards-data-science: 143, newest Feb 2025.

Towards AI was rejected on 2026-10-26 for the same reason.

**Dormant:**

- zillow-tech-hub: newest 2021.
- disney-streaming: 2023.
- llamaindex-blog: Mar 2024.
- miro-engineering: Jul 2024.
- the-ai-forum: 7 of 10 name a model, but its newest post is Apr 2026.

**Didn't answer:** swiggy-bytes timed out on both runs, and better-programming
on the first.

**beehiiv: feeds are opt-in per publication, and most AI newsletters haven't
opted in.** Of the 14 checked, only Unwind AI's homepage links a feed.
`/feed` was also tried on each by hand (curl), and only The Rundown answered
with one: the teaser feed rejected on 2026-10-26.

No feed was found for: AI Breakfast, Mindstream, The Deep View, Turing Post,
The AI Valley, AI Tool Report, AI Fire, Neat Prompts, Not A Bot, Superhuman
and AI Agents Simplified. The Code (thecode.ai) timed out on both runs.

## Medium throttles repeated reads

A second run of the same script, about 15 minutes after the first, got 503
or 504 from Medium for 16 of its 32 feeds, Airbnb and Netflix among them.
Both runs are kept (`.run1.out.json`, `.run2.out.json`).

The nightly harvest reads Medium once a day: six feeds with these four
added, a feed and a robots.txt each. That is far below what a probe of 32
feeds does. The runner reads both seated Medium feeds without trouble: the
scheduled run of 2026-11-05 (GitHub Actions run 41945038707, blog step at
00:58 UTC) got `robots=rules feed_allowed=True` and 10 entries from each,
all already stored. So I don't expect the nightly read to hit this, but the
threshold is unknown. If a Medium feed
starts coming back `refused` or 5xx at night, this is the first suspect.

## Order, and who does what

1. **After #601 merges.** Both change the pinned feed counts in
   `tests/test_source_terms.py`, `tests/test_blog_parse.py` and
   `tests/test_source_load_db.py`. Seating these on top of #601 avoids two
   PRs editing the same numbers.
2. **A seating PR** adds the five rows with their evidence blocks and
   updates those counts. It is a `contract/` change, so it gets the second
   review.
3. **Whoever merges it runs `registry load-sources`.** The harvest refuses a
   feed with no `source` row (#564). The next nightly run then harvests all
   five. None needs a harvest by hand: in the same run's log, the seated
   Medium feeds and The Neuron (beehiiv) were all read by the runner.
