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
