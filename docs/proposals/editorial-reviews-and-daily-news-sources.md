# Editorial tech sites: one review source, a wider news lane, and entities beyond models

*anooj · 2026-11-09 · PROPOSAL. Nothing under `contract/` changes in this PR. Each part below
becomes its own change after review.*

## Decisions (reviewed by Parvathi on #614, 2026-11-09)

| Question | Decision |
|---|---|
| **1. Every as an evidence source** | **Not yet.** It's press: #611 left open whether journalists' reviews count as "voices", and seating Every as a blog row would decide that by default. `blog-class-a-self-hosted` doesn't fit either, because Every is a paid publication and taking only the free opening needs its own terms ruling. Every waits for the press decision and that ruling. Before seating, extraction is run locally on the 10 sampled free openings and the first-hand evaluative claims it keeps are counted. The 9 evaluative-cue sentences suggest the verdict often sits behind the paywall. |
| **2. The news lane** | **Agreed as proposed**, Every's headlines included, since a headline isn't a voice. Each source's terms are read when its row is written, The Verge and MIT Technology Review especially. |
| **3. The sponsored badge** | **Agreed:** a printed-label match, never a default filter. VentureBeat's row carries it from its first run. |
| **4. Tools and products next** | **Agreed, scoped once test B reports.** The word-safety rule also covers product names that contain model-family words ("Codex", "Claude Code" against Claude, "Gemini CLI"): longest match decides, pinned by a test as the Meta Muse case was on #610. |

The "61 of 326" tool count below is a **ceiling** wherever it's quoted, because `Cursor`, `Dots`,
`Muse` and `Duet` are also English words.

Next: the news-lane sources and the sponsored badge go in one `contract/news_sources.yaml` PR,
with a second review. That file is itself still `status: proposed`.

## Why now

The scope is wider than model versions. anooj, 2026-11-09: *"we have to go broader than LLM
models, we have to cover everything that is coming up daily related to LLM models"*: agents,
coding tools, products and releases, not only `model_version` rows.

So I checked 18 editorial tech sites shaped like InfoQ. The question was which of them review
models and agents (evidence for the board), and which report what happened today (news).

## Two lanes, kept apart

| | Evidence | News |
|---|---|---|
| file | `contract/sources.yaml` | `contract/news_sources.yaml` |
| what it makes | verified quotes, board entries | headlines on `/news` and AI Updates |
| model calls | extraction (rule 2) | none |
| what qualifies | a first-hand, evaluative account | anything that happened |

**A release story is good news and never evidence.** A press release reports what a vendor says
about its own product. Filed as evidence, it would count a vendor's claim as an engineer's report
(rules 4 and 7). That's why most of these sites go to the news lane.

## The measurement

`docs/measurements/editorial-and-news-sites-2026-11-09.py`, with its output beside it. It's
read-only and stores nothing. The registry was read with `default_transaction_read_only=on`,
population fingerprint `150e9ba1f03700b4`.

- **Population:** each site's AI feed as served on 2026-11-09, and up to the first 10 AI-related
  items in it.
- **Article text:** the feed body when it's full, otherwise one read of the article page.
- **"Names a model":** a sentence names a registry model through `RegistrySurfaceFinder`, so
  versioned names count. A bare family ("Claude") or a product ("Claude Code") counts as nothing.
- **"Exactly one":** the sentence-level measure from `local-attributability-2026-09-22.py`: of
  sentences naming a model, how many name exactly one owner.
- **"Names a tool":** over every feed item's title, summary and first 600 characters, an item
  naming one of 26 agents, tools and protocols listed in the script. That list was chosen for
  this probe and isn't a registry. `Muse`, `Dots`, `Duet` and `Cursor` are also English words, so
  those counts are a ceiling.
- **Limits:** one day and at most 10 articles per site. §3a of `sources.yaml` notes that a
  ten-entry sample overstates naming on deeper feeds. These are readings from one day, not rates
  for the publication.
- **Terms were set aside for this pass** (anooj, 2026-11-09). Terms findings inform and never
  block, and each source's terms are read when its row is written.

| Site | Feed items | Full text in feed | Bylines (distinct) | Titles with a release verb | Articles naming a model | Sentences naming exactly one | Items naming a tool |
|---|---|---|---|---|---|---|---|
| **Every (Vibe Check)** | 50 | 0 | 50 (15) | 0 | **8 of 10** | **55 of 63** | **23 of 50** |
| ZDNET | 25 | 0 | 25 (11) | 0 | 1 of 10 | 11 of 12 | 1 of 25 |
| The Pragmatic Engineer | 20 | 15 | 20 (1) | 0 | 2 of 10 | 7 of 7 | 1 of 20 |
| The New Stack | 26 | 26 | 26 (16) | 1 | 2 of 10 | 3 of 9 | 5 of 26 |
| IEEE Spectrum | 30 | 0 | 30 (26) | 1 | 2 of 10 | 2 of 2 | 7 of 30 |
| InfoQ | 15 | 0 | 15 (9) | 2 | 1 of 10 | 2 of 2 | 2 of 15 |
| The Verge | 10 | 1 | 10 (6) | 0 | 2 of 8 | 4 of 4 | 1 of 10 |
| MIT Technology Review | 10 | 10 | 10 (6) | 0 | 1 of 8 | 1 of 1 | 2 of 10 |
| TechCrunch | 20 | 0 | 20 (11) | 3 | 1 of 10 | 0 of 2 | 3 of 20 |
| SD Times | 10 | 10 | 10 (5) | **5** | 1 of 6 | 1 of 1 | 2 of 10 |
| InfoWorld | 20 | 0 | **0** | 2 | 0 of 10 | — | 7 of 20 |
| Tom's Guide | 50 | 50 | 50 (6) | 1 | 0 of 10 | — | 3 of 50 |
| Ars Technica | 20 | 0 | 20 (7) | 3 | 1 of 10 | 1 of 1 | 2 of 20 |
| HackerNoon | 20 | 19 | 20 (20) | 1 | 1 of 9 | 2 of 2 | 2 of 20 |
| VentureBeat | **429 on the feed** | | | | | | |
| The Register | **answered 200 with something that isn't a feed** | | | | | | |
| DevClass | **answered 200 with something that isn't a feed** | | | | | | |

Notes:
- **Every:** pages read 10 of 10. **8 of 10 carry a paywall marker, and the median text read is
  1,458 characters.** We get the free opening of each review and never more.
- **Ars Technica:** the feed works, but article pages answer 405 to our client (10 of 10).
- **HackerNoon:** its robots.txt disallows our User-Agent.
- **The Register:** served a full-text Atom feed (50 items) on the first probe that day, then a
  non-feed answer on later runs. It needs a re-probe before anything is written.
- **VentureBeat:** read once through a page fetch. Of its 10 latest AI stories, 4 were release
  stories with company-reported benchmarks, 3 were labelled "Partner Content", and none was a
  hands-on test.

## 1. Every's Vibe Check: an evidence source

It's the only site of the 18 whose articles are evaluations of named models and agents. Recent
titles include "Claude Opus 5 Is Brilliant in Flashes, Frustrating in Practice", "GPT-6 Sol vs.
Opus 5.5", and reviews of Duet and Dots, two of the nine agents on #610. 55 of 63 model-naming
sentences name exactly one model, and 15 named authors wrote the 50 items.

**Proposed row:** `blog:every.to`, endpoint `https://every.to/vibe-check/feed`, under
`blog-class-a-self-hosted`. The site is self-hosted (Next.js behind Cloudflare), not Substack, and
that class already carries `fetch_articles: true`, which a summary-only feed needs.

**What to know before seating:**
- **The paywall:** the fetch takes what the page serves to anyone, which is the free opening. A
  claim beyond it simply isn't there. No login, no workaround (stack decisions: no paywall
  circumvention).
- **The advertised feed is broken:** the page's `<link rel="alternate">` points at
  `/vibe-check/feed.xml`, which answers 404. `/vibe-check/feed` works. The row should name the
  working URL and say why.
- **Comparison pieces exist** ("GPT-6 Sol vs. Opus 5.5"). 8 of the 63 naming sentences named two
  or more models, and extraction files those by the usual rules.
- **Terms** are read when the row is written, as for every source.

## 2. The news lane: which sites to add

`news_sources.yaml` reads 17 feeds today: AIWire, TechCrunch AI, six lab blogs, OpenRouter, three
writers, TLDR AI and four release feeds. The daily agent and tool stories the wider scope wants
come mostly from the trade press.

| Proposal | Sites | Why |
|---|---|---|
| **Add** | The New Stack, InfoQ, IEEE Spectrum, ZDNET, MIT Technology Review, The Verge, Every | Bylined, and between them they carry the day's agent and tool stories |
| **Add, feed only** | Ars Technica | The feed works; pages answer 405, so it goes in `link_preview.skip` with that reason |
| **Add, with a sponsored badge** | SD Times; VentureBeat once it answers | Release-heavy (SD Times: 5 of 10 titles carry a release verb). VentureBeat labels "Partner Content" itself. |
| **Optional** | Tom's Guide, The Pragmatic Engineer | Consumer-heavy, or one author |
| **Re-probe first** | The Register, DevClass | Non-feed answers today |
| **No** | HackerNoon, InfoWorld, Vellum | Robots disallows us; no bylines in the feed; a scored leaderboard (rule 3) |

**The sponsored badge** has the same shape as the LLM badge already in the file. It's a badge the
page shows and a filter a reader may turn on, **never a filter applied by default** (rule 8). It
fires only on a label the publisher prints itself ("Partner Content", "Sponsored", "Presented
by"), never on a guess from the wording. A release verb in a title is a cue, not a label, and
stays unbadged.

## 3. The real gap: entities beyond models

**Adding feeds won't make the coverage broad on its own.** A story page links "the models it
names", and `news_sources.yaml`'s story rule matches only names that carry a version digit, so
"Kiro", "Duet", "Claude Code" and "MCP" are never linked. Behind that, the resolver knows only
`model_version` rows, so the board can't hold evidence about them either.

How much that leaves out, on this one day: **at most 61 of 326 items** (a ceiling: `Cursor`,
`Dots`, `Muse` and `Duet` are also words) across the 14 readable feeds named a tool from the
probe's list, at most 38 of 276 without Every. The AWS Kiro launch alone appeared on
InfoWorld, The Register, VentureBeat and SD Times, and nothing on our site can connect to it.

The path, in order:
1. **Agents:** `kind: agent`, #609 to #611. Test B is fetching the nine agents on a local
   database now, and its results go on #610 first.
2. **Tools and products next:** coding agents and tools (Claude Code, Codex, Cursor, Kiro),
   protocols (MCP), and serving tools (vLLM, Ollama). Each is seated with its own kind, the way
   test B seats agents.
3. **Story pages link any seated entity**, not only versioned model names. This needs its own
   word-safety rule, because the digit rule exists to stop words matching. `Cursor`, `Dots`,
   `Muse` and `Duet` are English words, so the candidate is: seated compound names
   case-sensitively, and a one-word name only where it's not a dictionary word. Rule 10's
   ordinary-word clause applies: where it's unclear, nothing links.

## What this asks of the reviewer

1. Seat Every as an evidence source, with the paywall caveat written on its row?
2. The news-lane list above: add, feed only, badge, optional, re-probe, no.
3. The sponsored badge, as a printed-label match and never a default filter?
4. Tools and products as the entity kind after agents, scoped once test B reports?

## Rule check

- **Rule 1 and 2:** nothing here calls a model or makes a claim. Every's text would go through
  the existing extraction and quote check.
- **Rule 3:** Vellum is refused for its scores. No figure here is a synthesised score.
- **Rule 7:** every count above states its population (one day's feed window, at most 10
  articles) and how it was gathered.
- **Rule 8:** the sponsored badge is a badge, not a gate. No new filter drops anything.
- **Rule 10:** the entity-matching step names the ordinary-word problem before any code exists.
- **Rule 11:** the counts are a dated record of 2026-11-09, not present-tense claims.
- **`contract/`:** unchanged here. Each part is a separate change, with a second reviewer.
