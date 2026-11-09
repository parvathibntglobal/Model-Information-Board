# Proposal: track personal agents (Muse, Dots, Claude Duet, Grok Bot…) as a new kind

**For review by Parvathi. Proposed 2026-11-09 (anooj).** It would change
`contract/` (the tracked list, the unpolled seats and a new vocabulary heading
set), so nothing is edited until it's agreed. This PR adds only this document
and its measurement.

## The ask

1. **Agree the approach:** a personal agent is seated as a tracked row with
   `kind: agent`, hand-entered through `contract/unpolled_models.yaml` as
   ElevenLabs v3 is, so the existing pipeline collects, extracts and counts
   reports about it with no new adapter.
2. **Agree the first batch and the naming rule** below. Where an agent's name
   is an ordinary word, it gets compound aliases only ("Meta Muse", never
   "Muse"). The short name is used only where the thread says which agent is
   meant: a search pairs it with a giveaway word, and a quote may file under
   the agent only if its thread names the agent unambiguously.
3. **Agree the order:** after #602's PR A, which changes the same tracked list
   and the kind logic. The seating comes as its own `contract/` PR, then one
   fetch per agent run by hand, measured before anything goes nightly.

## Why

People increasingly hand tasks to agents (Meta's Muse, OpenAI's Dots,
Anthropic's Claude Duet, xAI's Grok Bot) rather than choosing a model and
version. The board collects nothing about them on purpose, so a report like
"Muse booked my flight but couldn't message the seller" has no row to land on
and is lost at resolution.

[assistantbenchmark.com](https://assistantbenchmark.com/) shows the demand.
It covers 75 assistants (30 scored, 45 pending), each with a per-assistant page
and a "What people say" section: 175 quotes for Muse, tagged Praise, Use case,
Comparison, Complaint and Bug. But its "Overall 9.3" is a synthesised score with
no published formula, its tests are one reviewer's hands-on threads, and its
quotes are mostly press articles. What we would show instead is set out in "What
this enables" below.

## What we already hold, and what's out there

`docs/measurements/agent-discussion-2026-11-09.py`, run 2026-11-09, read-only.

**Stored threads.** All 10,578 thread texts readable in the shared raw store
(of 15,405 thread contexts; the rest are held only where they were assembled)
were searched. They were collected by MODEL searches, so every mention is
incidental.

**Hacker News.** Exact phrase, stories and comments since 2026-08-01.

| Agent | Maker | Stored threads naming it | …of them since 1 Aug | HN stories / comments |
|---|---|---|---|---|
| Hermes Agent | Nous Research | 128 | 128 | 27 / 96 |
| Grok Bot | xAI | 93 | 93 | 81 / 178 |
| OpenClaw | open source | 82 | 66 | 84 / 571 |
| ChatGPT Work | OpenAI | 61 | 60 | 18 / 89 |
| Muse ("Meta Muse") | Meta | 54 (bare "Muse": 204) | 53 | 82 / 82 |
| Claude Cowork | Anthropic | 51 | 44 | 12 / 64 |
| Claude Duet | Anthropic | 38 | 38 | 8 / 19 |
| Doubao | ByteDance | 19 | 17 | 6 / 9 |
| Dots ("OpenAI Dots") | OpenAI | 11 (bare "Dots": 32) | 11 | 12 / 17 ("openai dots" + "chatgpt dots", summed) |
| Siri AI | Apple | 5 | 5 | 29 / 137 |
| Gemini Spark | Google | 4 | 3 | 1 / 6 |
| Manus, Letta, Lindy, Perplexity Comet | | 2–7 each | | 0–4 each |
| Hark, Instinct, Tomo, Pally, Zapia, Joshu, Poke | startups | 0 | 0 | 0 |

**What the numbers say:**

- **The discussion is real and recent.** Almost every stored mention is from
  after 1 August, which is when most of these launched.
- **It's concentrated in the big-vendor and open-source agents.** The startup
  long tail on assistantbenchmark has none in any source we read.
- **What we hold is mostly news and lists, not use.** A spot check of the stored
  matches found launch coverage, roundups and tutorials, much of it in Chinese,
  Korean or Thai. First-hand reports are a minority, which is what a search by
  agent name would change.
- **GitHub totals are excluded.** They read as separate-word matches ("meta
  muse": 31,560), so they don't measure the phrase. They're recorded in the
  output for completeness.

## Naming: compound aliases, short names only in context

Muse, Dots, Duet and Spark are English words. Bare "Muse" matched 204 stored
threads against 54 for the compound forms. An ordinary-word name never gets a
bare alias (rule 10's ordinary-word case). But people do use the short name,
so it is handled in context: see "Short names" below.

| Agent | Proposed aliases | Collision checked (shared `model_alias` and `model_version`, 2026-11-09) |
|---|---|---|
| Grok Bot | `grok bot`, `grokbot`, `grok-bot` | none |
| OpenClaw | `openclaw` | none |
| Hermes Agent | `hermes agent`, `hermes-agent` | none. Distinct from Nous's Hermes models by the second word. |
| Muse | `meta muse`, `muse by meta` | ⚠ **Meta's models are also called Muse** (`meta/muse-spark-1.3`, `muse-wonder`, `muse-glimmer-30b`, …). "Muse Spark 1.3" resolves to the model by the longest match. A bare "Meta Muse" is ambiguous between the agent and the model family, and needs a ruling. |
| ChatGPT Work | `chatgpt work` | none |
| Claude Cowork | `claude cowork`, `cowork` | none. `cowork` is coined, but the first run should be checked for the verb. |
| Claude Duet | `claude duet`, `anthropic duet` | none |
| Dots | `openai dots`, `chatgpt dots` | ⚠ `dots-studio/dots-3-note-preview` is a model, and the dots.llm models exist. The compound forms avoid both. |
| Gemini Spark | `gemini spark` | ⚠ beside `meta/muse-spark-*`. No shared surface, but "Spark" alone must never be an alias. |
| Siri AI | `siri ai`, `new siri` | none, but noisy: "new Siri" predates the agent. Measure on the first run before keeping it. |

**The first batch, by volume:** Grok Bot, OpenClaw, Hermes Agent, Muse,
ChatGPT Work, Claude Cowork, Claude Duet and Dots. Then Siri AI and Gemini
Spark: low volume, but from major vendors.

### Short names: the compound rule alone would miss about half of Muse and Dots

People name the agent once ("Meta launched Muse") and then write "Muse".
`docs/measurements/agent-short-names-2026-11-09.py` sorts every stored thread
that uses the bare word (the same 10,578, read-only) into four groups:

| | Caught by a compound form | Bare only, giveaway within 200 characters (probably the agent) | Bare only, all a **model** name (Muse Spark, Wonder, Glimmer; dots models) | Bare only, no giveaway |
|---|---|---|---|---|
| Muse | 51 | **45** | 73 | 35 |
| Dots | 10 | **15** | 0 | 7 |
| Duet | 38 | **3** | n/a | 2 |

The giveaways are words like Meta, WhatsApp or "agent" for Muse; OpenAI,
ChatGPT or Altman for Dots; Claude or Anthropic for Duet. **The test is rough,
so the middle column is an estimate, not a count.** Even so:

- compound-only would miss about 45 of roughly 96 Muse threads, and about 15
  of 25 Dots threads;
- it misses almost nothing for Duet, which people write as "Claude Duet";
- a bare alias would be worse: 73 bare-only Muse threads are about Meta's
  Muse **models**, and 35 more look like other senses of the word.

**So the short name is used in context, at two stages:**

1. **Finding threads.** Search the bare name with a giveaway word, not the
   compound phrase: `muse meta`, `muse whatsapp`, `dots openai`, `dots
   chatgpt`. Reddit and Hacker News search match all the words anywhere in a
   post, so this finds "Meta launched Muse… Muse booked my flight". Later, if
   the first runs justify it, a sweep of agent-specific subreddits, where the
   short name is the natural one.

   **These pairs are query terms, never aliases (#609 review).** On #602's
   branch, the Reddit arm fetches comments only for a post that names a
   variant (`_names_a_variant`: separators folded, the whole phrase in order),
   and the same test decides what X keeps for media kinds. "Meta launched
   Muse… Muse booked my flight" doesn't contain the phrase `muse meta`. So if
   the pairs were aliases, the threads this stage exists to find would be
   stored without their comments. They go in their own field on the seat
   (say `search_terms:`), read by the search arms.

   **Holding them apart isn't enough on its own.** That post contains neither
   alias as a whole phrase either ("meta muse", "muse by meta"), so the
   comment check would still skip it. For an agent, the check has to accept a
   post that names an alias, **or** contains every word of one search pair
   anywhere, separators folded as `names_folded` does. That's the in-context
   rule from stage 2, applied one step earlier. It decides only whether
   comments are fetched, never attribution. The seating PR should count both
   ways a post qualified, so the first runs show what the pair rule adds.
2. **Filing a quote.** A quote that says only "Muse" files under the agent
   only when **its thread** names the agent unambiguously ("Meta Muse", "Muse
   by Meta", or Meta together with agent wording), **and** the quote doesn't
   name a Muse model. Otherwise it is held in `unresolved_entry` (#602, the
   `held_entries` path: held by the name as written), never
   guessed. A missed mention costs a count; a wrong one files an agent's
   complaint under Meta's model (rules 6 and 10).

**The second stage is a new, narrow mechanism:** a short name valid only inside
a thread that has already named its owner. It decides attribution, so it ships
as a weight first (rule 8). On the first hand runs, read every quote it filed
by the bare name and count the wrong ones, over that denominator, before it's
trusted.

**And it stays agent-only for now.** Models have the same habit: people write
"Opus" or "Sonnet", and the board loses those today, because family-level
short names aren't used for attribution. `collect/triage/entity.py` says that
ruling is pending, and not to touch `FAMILY_WORDS` until it exists. If the
agent version measures well, it's evidence for that ruling. It is not a way
around it.

## The search probe: what the names actually find (2026-11-09, #610)

`docs/measurements/agent-search-probe-2026-11-09.py`, read-only: public search
APIs, no database, no model call. It asked each platform once per query, for 18
queries over the 9 agents agreed on #610, and sorted each result. 90 queries
cost 18 Reddit and 18 X requests.

**The sort:** names the agent by a compound alias; or the bare name with a
giveaway word within 200 characters (Muse and Dots only); or a Muse **model**;
or unclear.

**Compound aliases.** The cells are results naming the agent by a compound
alias, out of results sampled; "+N ctx" is the bare name beside a giveaway:

| Agent | Hacker News (since 1 Aug) | Reddit | X | Bluesky |
|---|---|---|---|---|
| Grok Bot | 78 / 78 | 63 / 83 | 28 / 42 | 82 / 98 |
| OpenClaw | 40 / 40 | 37 / 41 | 11 / 22 | 44 / 50 |
| Hermes Agent | 40 / 40 | 33 / 44 | 23 / 26 | 35 / 49 |
| Claude Cowork | 71 / 72 | 37 / 81 | 24 / 41 | 89 / 100 |
| Claude Duet | 25 / 27 | 29 / 37 | 29 / 49 | 46 / 54 |
| ChatGPT Work | 32 / 38 | 20 / 39 | 6 / 21 | 30 / 50 |
| Gemini Spark | 7 / 7 | 27 / 39 | 14 / 21 | 41 / 50 |
| Muse | 27 / 46 +18 ctx | 34 / 73 +17 ctx | 19 / 48 +8 ctx | 50 / 88 +14 ctx |
| Dots | 18 / 29 +8 ctx | 26 / 80 | 27 / 43 | 53 / 100 +6 ctx |

**How to read it.** One page per query, so these are shares of a first page,
not population rates. Each cell is **summed over the agent's alias queries,
with overlap not removed**: a post returned by both `grok bot` and `grokbot`
is counted twice. The Claude Cowork Reddit cell, 37 / 81, includes the stemmed
`cowork` query, which is dropped below. Reddit and X count a post's title and
body as separate texts. dev.to is left out of the table: its search returns titles and
descriptions only, which isn't enough to sort, and of its 30 results a query
matched the compound form in 0 to 15. The board reads dev.to bodies, so it gets
measured on the hand run.

**What it changes for the seating PR:**

- **Drop `cowork` as a search query.** Reddit's search stems it: 2 of 41
  results contain "cowork", and the rest are about coworkers. Keep it only as
  an alias for matching, where the word boundary already refuses "coworker".
  Search with `claude cowork`.
- **Drop `anthropic duet`:** 0 on Hacker News, 3 on Reddit. `claude duet`
  carries the agent.
- **Add plurals and spacing as aliases,** for example "Grok Bots". A Reddit
  post about someone's Grok Bots setup missed `grok bot` because of the
  plural.
- **Keep `muse whatsapp` as a search pair. It finds first-hand reports the
  compound form misses:** 35 of 50 Bluesky results, 19 of 38 Reddit and 16 of
  22 X are the bare "Muse" beside a giveaway. For example, posts about
  removing Muse from WhatsApp, and about there being no WhatsApp connector.
  `muse meta` adds less, and on Hacker News it matches 3,236 items, so it is
  broad.

  **A pair hit that names only "Muse" is an in-thread short name** (#610,
  decision 4). On the first hand runs it is **counted, not filed**: it's held
  in `unresolved_entry` like any other short-name quote, and read before the
  rule files anything. The seating PR must not file pair hits directly.
- **The Dots pairs are noisy.** `dots chatgpt` sorted only 3 of 40 Hacker News
  results as compound and 13 as context, and `dots openai` 14 and 8 of 40.
  Start Dots with its compound aliases only (`openai dots`; `chatgpt dots` was
  weak on Reddit at 6 of 40), and add a pair only if the hand run shows
  missed reports.
- **Muse models barely contaminate:** 0 to 6 per sample, so the longest-match
  rule is enough.
- **Treat the subreddit as a giveaway.** Many "unclear" Reddit results are the
  agent named bare in its home subreddit. For example: a post in an OpenAI
  subreddit asking what Dots is, without naming OpenAI; and a post in the Grok
  subreddit weighing Grok against Dots and Muse by their bare names. The
  in-context rule should count the thread's subreddit as naming the owner
  (r/grok for Grok Bot, the Meta subreddits for Muse, r/OpenAI and r/ChatGPT
  for Dots). **Its error rate is reported per subreddit,** not as one figure,
  because r/OpenAI and r/ChatGPT are general enough that "dots" can mean other
  things there.
- **Expect referral spam.** Posts sharing a Muse invite code for a reward came
  back on X. That is E6's discount-code trigger, which runs on every fetch
  since #608.

**No Reddit or X text is quoted in this section.** Each case above is described
in our own words, because the repo is public and `contract/publication.yaml`
withholds Reddit and X text. An earlier commit on this branch quoted four
snippets; #611's review caught it.

## How it would collect

Nothing new to build for collection. A tracked row's aliases already drive
the per-model search on every source we harvest: Reddit, Hacker News, X,
Bluesky, dev.to, GitHub and arXiv. Triage, verbatim-quote extraction (rule 1)
and counting apply unchanged. The changes are:

- **`kind: agent`, with a decision per search arm (#609 review).**
  `judge/config.py` accepts any `kind` string. But #602 branches the harvest
  on `MEDIA_KINDS`, and every other kind takes the text-model path, which
  would cut agents off:
  - **X** keeps a text-model post only if it names the model **and** a
    capability phrase from `contract/queries.yaml` ("tool call", "didn't
    follow"). "Muse booked my flight but couldn't message the seller" has
    neither. Media lost almost everything the same way (X kept 1 of 71
    Seedance 2.0 posts) before the fix.
  - **GitHub** crosses the name with the same text vocabulary, in LLM-tooling
    repos, where agents are rarely discussed.

  **So for the first runs, `agent` takes the media path: name-only.** The
  "agent tasks" headings below can become its own query vocabulary once
  they're built from real quotes. The seating PR also adds `agent` to
  `KIND_LABEL` and the Models page's Type chips. Without that, an agent row
  shows no label and no chip.
- **No price column at first.** #602's `unit_price` holds per-unit rates (per
  second, per image, per million characters), and its fallback source,
  LiteLLM's list, has no agents. A subscription ("$20 a month, includes Muse")
  isn't a per-unit rate. So an agent shows "no price published" until there's
  a cited plan-price source and somewhere to keep it. That's the honest state,
  and it's a later decision.
- **Non-text kinds on the tracked list today** are image, video and speech
  (Nano Banana 2, GPT Image 2.5 Sunburst, Seedance 2.0, ElevenLabs v3). Jev
  1.13 went back to `kind: text` on #602's branch, because the SEO keyword
  plan pairs it with text models.
- **An "agent tasks" heading set** in the vocabulary, proposed through the
  curation proposals and regenerated through `choose_name` (#607). It would be
  built from the first run's real quotes, using assistantbenchmark's 15
  dimensions as a checklist: travel booking, email, purchasing, routines,
  connected apps, permissions and privacy, memory, proactivity, phone calls,
  group chats, multi-step tasks, restraint, reliability.
- **One attribution rule**, for the extractor's subject decision: a quote about
  what the agent did ("Muse booked the flight") files under the agent. A quote
  about the model inside it ("Grok Bot is slow because Grok 4.6…") files under
  the model. Per quote, never per thread.
- **Later, if the first runs justify it:** a listing sweep of agent-specific
  subreddits, shaped like #602's media sweep (store every post, fetch comments
  only where a known name appears).

## How a report is shown (added 2026-11-09, #610)

assistantbenchmark's Muse page reads better than a board row, and it's worth
being exact about why. Of the 20 items visible on 2026-11-09:

- **18 are from news and review outlets and 2 from a blog.** None is from
  Reddit, X or a forum, and every one is dated 23–24 September, the launch
  coverage.
- **Each item is a long excerpt, 80 to 800 characters,** with no quotation
  marks, written by a journalist. That's why it reads as polished.
- **No method is stated** beyond "175 quotes, linked to source", and some
  tags don't fit their text.

So the gap isn't that their claims are crafted and ours are quotes. A
one-sentence verbatim quote from a user often lacks the context that makes it
mean something. The agent page should close that gap without giving up the
verbatim proof (rule 1), and without crossing the publication terms each source
carries. Reviewed on #611, which corrected the first draft of this section.

### What a report shows depends on its source

The first draft said Reddit and X context "comes through the official embed".
That's the **evidence feed's** term, not the board's. Under
`contract/publication.yaml` today:

- **The board** withholds Reddit, X, arXiv and Bluesky entirely (`withheld_from_public`): no quote, no
  link, no handle, no platform name, and no embed.
- **The feed** follows the derived-post terms: a paraphrase for every report,
  Reddit and X cited only by their official embed, and no verbatim quote from
  any source.

Most agent reports will come from Reddit and X (that's where the nightly
searches sized on #610 look), so the page needs a rule per source:

| Source | What the agent page shows |
|---|---|
| A source the board shows (blogs, Hacker News, GitHub, dev.to, Hugging Face, the forum) | The paraphrase, then the verbatim quote with its context and a link |
| Reddit, X | The paraphrase and the official embed, never their text |
| arXiv | The paraphrase and a link, with the arXiv acknowledgement |
| Bluesky | Listed and counted only, until its hold is lifted |

**Which terms the agent page follows is a `contract/` change.** It's either an
agent-page line in `publication.yaml` or a statement that it follows the
feed's terms. It gets proposed with the page, for review.

### 1. Context around the quote: verbatim, and capped

- **Only for sources the board shows.** The page shows the sentence before and
  after the quote, taken from the source text.
- **Found by exact substring match.** `board_entry` keeps the quote and its
  `document_id`, but not the quote's position: that lived on `claim` rows,
  which stopped being stored in #502. So the context is found by exact
  substring match of the stored quote in the document's text, the same match
  rule 1 uses, or by storing the offset on the row.
- **When the match fails, the page says no context could be found** (rule 4),
  rather than showing the quote alone as if it had none.
- **The context stays a short quotation.** Every quote rests on the use-basis
  undertaking in `contract/sources.yaml`: "a short quotation, attributed and
  linked, for commentary and comparison, never the full text". The sentences
  around a quote could turn a short post into the whole post. A
  three-sentence comment whose middle sentence is the quote would be shown in
  full. So there are two limits:
  - a cap on the characters shown in total, quote plus context;
  - a cap on the share of the document's text shown, with no context at all
    when that share would be crossed.
- **Past either limit, the page says "context not shown"**, not nothing (rule
  4). The numbers are the team's call, and they belong in `publication.yaml`
  beside the per-source rule above, proposed with the page.

### 2. A plain-language line above the report's quotes

- **The evidence feed already writes the line.** `judge/feed/paraphrase.py`
  writes **one paraphrase per report** (one document about one model), from
  all of that report's excerpts, worded as "The author found…". It stores it
  only after code checks its shape: no long run copied from the excerpts,
  every number present in the source, no handle, URL or embed-only platform
  name.
- **So the agent page shows it above that report's group of quotes, not
  above each quote.** The first draft's example ("Users report Muse can't
  message sellers directly") was a per-quote claim spoken for many users, and
  the stored paraphrase is neither. A per-quote headline would need a new
  prompt, and so a new model call, which is a separate decision.
- **Agents get paraphrases with no new wiring.** They are stored for every
  model with reports and shown for the seated ones, so a seated agent gets
  them, at the feed stage's spend, outside the extraction cap.
  `paraphrase_problem` exempts the model's own label, and none of the nine
  agent names carries a number or a domain, so the number and identity checks
  behave as they do for models.
- **The per-model summary stays pending until a person approves it,** as now.
- **The rule-2 record in `CLAUDE.md` names the feed** (#558) as the surface
  where model text reaches a page with no person reading each item. Showing
  the same stored text on agent pages makes no new model call, but it is a
  second such surface. So the change that ships the agent page also adds one
  line to that record naming it.

### 3. Hands-on reviews as one more source, labelled as press

- **Journalists' first-hand testing is real evidence** ("I then booked the
  flights myself…"), and the blog harvest can take review feeds.
- **Open question: does press count towards "voices"?** The board's totals
  count people reporting their own use. If reviews count, then at launch,
  when press dominates (18 of 20 items on assistantbenchmark's Muse page), an
  agent's count could be mostly press with nothing on the page saying so.
  The source proposal must answer it either way:
  - press is listed and labelled, but **not** counted in voices or reports;
    this is #611's recommendation, so that "voices" means one thing on every
    page;
  - or press is counted, and the total shows how many of the voices are
    press.

**The order:** 1 and 2, the per-source rule, the context limits and the
rule-2 line all come with the agent page (step 4 of the order below), not the
seating PR. 3 is a separate source proposal, after the first hand runs show
how much users alone produce.

## What this enables

Things assistantbenchmark can't show:

1. **Users' reports, not the press.** Verbatim, linked and counted with their
   denominators. No score (rule 3).
2. **What each agent is used for and where it fails,** ranked by report counts
   per task.
3. **Who switches,** from comparison quotes ("moved from Muse to Duet").
4. **The model under the agent.** Grok Bot runs on Grok and Duet on Claude, so
   an agent page can link into that model's evidence on the board. Nobody else
   connects the two.
5. **Nightly freshness.**

It would sit beside the "Run agents safely" family in the 2026-11-04 landing
preview (`idea/whole-tree`, a local branch not yet pushed). The page itself is
a later proposal.

## Cost

A fetch costs about $0.01 a night per model: the three nights to 2026-11-09
averaged $0.0103 over 38 fetches. Ten agents is about $0.10 a night, plus about
$0.03 for each first fetch at the 100-thread cap.

**Search requests are the larger cost.** #602's media runs used about 9 Reddit
requests per model fetch (3 searches plus comment threads) and 1 to 3 X
requests. Ten agents nightly is roughly 90 Reddit and 10 to 30 X requests a
night. That's well inside the quotas: the latest readings, 2026-11-09 01:03
UTC, were Reddit 999,021 of 1,000,000 a month left and X 99,747 of 100,000.
But it's the number to watch, and it would be read again from the first hand
runs before anything goes nightly.

**Scope:** the tracked list was set at 25 entries on 2026-11-06. The first
batch would add 8 to 10 rows, which is Parvathi's call alongside the open
questions.

## Open questions

1. **Muse:** does a bare "Meta Muse" file under the agent, or stay unresolved
   while Meta's models share the name?
2. **`kind: agent`, or a separate entity?** Seating agents in `model_version`
   reuses everything, but "model version" is the wrong word for them. I'd
   start with the kind and revisit only if the pages need something it can't
   carry.
3. **Siri AI:** keep it in the first batch, or wait until "new Siri" can be
   told apart from the agent?
4. **The in-thread short name:** is the two-condition rule above (the thread
   names the agent unambiguously, and the quote names no Muse model) enough? Or
   should the first runs file nothing by the short name, and only count what
   the rule would have filed?

## Order, and who does what

1. **This PR:** the proposal and the measurement, for review.
2. **After #602's PR A merges:** a seating PR adds the first batch to
   `unpolled_models.yaml` and `tracked_models.yaml` with `kind: agent` and the
   aliases above. It's a `contract/` PR, so it gets the second review. Its body
   names who runs `load_unpolled_models.py --apply` and when.
3. **One fetch per agent by hand,** with the numbers posted on the seating PR:
   threads, verified quotes, entries about the agent, and bare-word false
   matches.
4. **Then** the agent-task headings, and the page.
