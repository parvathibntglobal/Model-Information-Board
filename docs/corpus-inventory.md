# Corpus inventory

**What we collected, and how we found it.** One row per document, grouped by platform. Nothing here needs a database to read.

*Generated 2026-08-24 10:07 India Standard Time from `52.17.75.29:5432/Model-information-Board`*

---

## Counts

| platform | documents | kept | dropped | text unavailable |
|---|---:|---:|---:|---:|
| blog | 120 | 26 | 93 | 1 |
| github | 27 | 0 | 0 | 27 |
| reddit | 196 | 18 | 178 | 0 |
| **total** | **343** | **44** | **271** | **28** |

**343 of 343 documents in the database are in this file.** Nothing is omitted.

## Two things to read before the tables

**1. The three platforms did not arrive the same way, and only two were searched for.**

| platform | how it arrived | |
|---|---|---|
| blog | **feed-fetched, UNFILTERED** | RSS. Every article in the feed is taken and no query decided anything, so nothing was searched for and nothing was excluded at retrieval. This is the only positive-evidence channel. |
| github | **query-retrieved** | GitHub Search API. A term list from `contract/queries.yaml` produced these; the sieve then rejected what did not carry a subject, topic and signal term. |
| reddit | **query-retrieved, then thread-expanded** | Reddit search via RapidAPI found the ROOT POST. Its comments were then fetched wholesale by `getPostComments` — so the comments were not themselves retrieved by any query, and a term list does not describe them. |

So *"we searched for these terms and got these documents"* is true of GitHub, half-true of Reddit — the root posts were searched for and the comments were not — and **false of blogs**, where the feed is taken whole and no query decided anything.

**2. The query that found any given document is NOT RECOVERABLE, and this file does not guess it.**

```
document       has no harvest_run reference and no query column
harvest_run    153 rows, each with a query_key
between them   nothing
```

Term overlap or fetch timestamps could produce a plausible mapping. They are not recorded here: a provenance that looks derived and is inferred is worse than an absent one, because only the second invites the question.

## Two limits of the columns below

**Triage verdicts are computed by this script, not read from the database.** `document.triage_verdict` is NULL on **343 of 343** rows — nothing in the repository writes it. The verdicts here are from `collect/triage/gates.py` at render time, against population `c511fceb6b7fb3df`. `unavailable` means the payload could not be read and therefore **no gate ran** — it is not a rejection.

**"Author" is a stable opaque id, not a name.** Handles are deliberately never stored (data minimisation), so `t2_…`, a numeric GitHub id, or a feed id is all there is. Recovering a display name means re-reading the raw payload at render time, and for Reddit that is an open Developer Terms 5.2 question rather than a lookup.

---

## blog — 120 documents

*feed-fetched, UNFILTERED. RSS. Every article in the feed is taken and no query decided anything, so nothing was searched for and nothing was excluded at retrieval. This is the only positive-evidence channel.*

Triage at render time: **26 kept, 93 dropped, 1 text unavailable.**

| # | date | author | recognise it by | triage | url |
|---:|---|---|---|---|---|
| 1 | 2024-03-29 | `—` | Your AI Product Needs Evals | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/evals/) |
| 2 | 2024-04-12 | `—` | Debugging AI With Adversarial Validation | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/drift/) |
| 3 | 2024-07-29 | `—` | An Open Course on LLMs, Led by Practitioners | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/course/) |
| 4 | 2024-10-29 | `—` | Using LLM-as-a-Judge For Evaluation: A Complete Guide | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/llm-judge/) |
| 5 | 2024-11-30 | `—` | Building an Audience Through Technical Writing: Strategies and Mistakes | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/audience/) |
| 6 | 2025-01-03 | `—` | Everything I did in 2024 | kept | [link](https://vickiboykis.com/2025/01/03/everything-i-did-in-2024/) |
| 7 | 2025-01-14 | `—` | How FastAPI path operations work | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/01/14/how-fastapi-path-operations-work/) |
| 8 | 2025-01-23 | `—` | You can just hack on ATProto | kept | [link](https://vickiboykis.com/2025/01/23/you-can-just-hack-on-atproto/) |
| 9 | 2025-03-17 | `—` | 20 years of YC | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/03/17/20-years-of-yc/) |
| 10 | 2025-03-24 | `—` | A Field Guide to Rapidly Improving AI Products | kept | [link](https://hamel.dev/blog/posts/field-guide/) |
| 11 | 2025-05-28 | `—` | [white_right_pointing_backhand_index] *Want to learn more about AI Evals? Check out our AI Evals course*. It’… | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/evals-faq/) |
| 12 | 2025-07-16 | `—` | My favorite use-case for AI is writing logs | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/07/16/my-favorite-use-case-for-ai-is-writing-logs/) |
| 13 | 2025-08-08 | `—` | Enabling Hugo static site search with Lunr.js | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/08/08/enabling-hugo-static-site-search-with-lunr.js/) |
| 14 | 2025-09-01 | `—` | How big are our embeddings now and why? | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/09/01/how-big-are-our-embeddings-now-and-why/) |
| 15 | 2025-09-09 | `—` | Walking around the app | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/09/09/walking-around-the-app/) |
| 16 | 2025-09-11 | `blog:jxnl.co` | What Is the Coding Agents Speaker Series?¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/coding-series-index/) |
| 17 | 2025-09-11 | `blog:jxnl.co` | What Made The Difference | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/do-your-engineers-know-how-to-leverage-ai/) |
| 18 | 2025-09-11 | `blog:jxnl.co` | Domain Experts: The Lever for Vertical AI — Chris Lovejoy (Anterior)¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/domain-experts-the-lever-for-vertical-ai/) |
| 19 | 2025-09-11 | `blog:jxnl.co` | How Extend Achieves 95%+ Document Automation (Lessons from Eli Badgio)¶ | kept | [link](https://jxnl.co/writing/2025/09/11/how-extend-achieves-95-document-automation-lessons-from-eli-badgio/) |
| 20 | 2025-09-11 | `blog:jxnl.co` | Lexical Search - John Berryman¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/lexical-search-in-rag-applications/) |
| 21 | 2025-09-11 | `blog:jxnl.co` | RAG systems are fundamentally different from other AI applications - they combine the complexity of informati… | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/rag-series-index/) |
| 22 | 2025-09-11 | `blog:jxnl.co` | Why public benchmarks like MTEB don't reflect real-world performance | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/stop-trusting-mteb-rankings-kelly-hong-chroma/) |
| 23 | 2025-09-11 | `blog:jxnl.co` | Text Chunking - Anton (ChromaDB)¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/text-chunking-strategies-for-rag-applications/) |
| 24 | 2025-09-11 | `blog:jxnl.co` | The 12% RAG Performance Boost You're Missing (Ayush, LanceDB)¶ | kept | [link](https://jxnl.co/writing/2025/09/11/the-12-rag-performance-boost-youre-missing-ayush-lancedb/) |
| 25 | 2025-09-11 | `blog:jxnl.co` | Why Cognition does not use multi-agent systems¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/why-cognition-does-not-use-multi-agent-systems/) |
| 26 | 2025-09-11 | `blog:jxnl.co` | Why Glean Builds Custom Embedding Models for Every Customer¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/why-glean-builds-custom-embedding-models-for-every-customer/) |
| 27 | 2025-09-11 | `blog:jxnl.co` | Why Grep Beat Embeddings in Our SWE-Bench Agent (Lessons from Augment)¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2025/09/11/why-grep-beat-embeddings-in-our-swe-bench-agent-lessons-from-augment/) |
| 28 | 2025-10-01 | `—` | Selecting The Right AI Evals Tool | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/eval-tools/) |
| 29 | 2025-10-20 | `—` | I want to see the claw | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/10/20/i-want-to-see-the-claw/) |
| 30 | 2025-12-01 | `—` | Slack’s Security Engineering team is responsible for protecting Slack’s core infrastructure and services. Our… | dropped — no-resolvable-entity | [link](https://slack.engineering/streamlining-security-investigations-with-agents/) |
| 31 | 2025-12-22 | `—` | 2025 in review | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2025/12/22/2025-in-review/) |
| 32 | 2026-01-18 | `—` | Why I Stopped Using nbdev | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/ai-stack/) |
| 33 | 2026-01-24 | `blog:jxnl.co` | Things¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/01/24/things/) |
| 34 | 2026-02-02 | `blog:jxnl.co` | Sunsetting 567 Labs and Open Sourcing the Course Content¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/02/02/sunsetting-567-labs/) |
| 35 | 2026-02-21 | `—` | Querying 3 billion vectors | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/02/21/querying-3-billion-vectors/) |
| 36 | 2026-03-02 | `—` | Evals Skills for Coding Agents | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/evals-skills/) |
| 37 | 2026-03-04 | `—` | Antidote | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/03/04/antidote/) |
| 38 | 2026-03-19 | `—` | Introduction [bell] | dropped — no-resolvable-entity | [link](https://slack.engineering/how-slack-rebuilt-notifications/) |
| 39 | 2026-03-26 | `—` | The Revenge of the Data Scientist | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/revenge/) |
| 40 | 2026-03-31 | `—` | The Problem: Legacy Tooling and Its Limitations | dropped — no-resolvable-entity | [link](https://slack.engineering/from-custom-to-open-scalable-network-probing-and-http-3-readiness-with-prometheus/) |
| 41 | 2026-04-02 | `blog:jxnl.co` | What Music Do You Listen To?¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/04/02/what-music-do-you-listen-to/) |
| 42 | 2026-04-05 | `—` | NASA Elements of Engineering Excellence | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/04/05/nasa-elements-of-engineering-excellence/) |
| 43 | 2026-04-06 | `—` | On Programming Joy and Octocat | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/04/06/on-programming-joy-and-octocat/) |
| 44 | 2026-04-06 | `—` | *(text not readable here)* | unavailable | [link](https://vickiboykis.com/2026/04/06/on-programming-joy-and-octocat/) |
| 45 | 2026-04-13 | `—` | Mechanical sympathy | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/04/13/mechanical-sympathy/) |
| 46 | 2026-04-13 | `—` | Excerpt | dropped — no-resolvable-entity | [link](https://slack.engineering/managing-context-in-long-run-agentic-applications/) |
| 47 | 2026-04-20 | `—` | Build yourself flowers | kept | [link](https://vickiboykis.com/2026/04/20/build-yourself-flowers/) |
| 48 | 2026-05-05 | `—` | Excerpt | dropped — no-resolvable-entity | [link](https://slack.engineering/from-ssh-to-rest-a-security-driven-modernization-of-slacks-emr-data-pipelines/) |
| 49 | 2026-05-10 | `blog:jxnl.co` | Codex-maxxing¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/05/10/codex-maxxing/) |
| 50 | 2026-05-18 | `blog:jxnl.co` | Six levels of complexity in a Codex morning brief¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/05/18/six-levels-of-complexity-of-an-ai-powered-morning-brief-with-codex/) |
| 51 | 2026-05-18 | `—` | Tagging my blog posts with BERTopic and LLMs | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/05/18/tagging-my-blog-posts-with-bertopic-and-llms/) |
| 52 | 2026-05-28 | `—` | We should be more tired than the model | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/05/28/we-should-be-more-tired-than-the-model/) |
| 53 | 2026-05-28 | `—` | In early 2023, Slack faced a foundational challenge: serving Large Language Models (LLMs) at enterprise scale… | dropped — no-resolvable-entity | [link](https://slack.engineering/slack-ai-the-path-to-multi-cloud/) |
| 54 | 2026-06-03 | `blog:engineering.atspotify.com` | Coding Is No Longer the Constraint: Scaling Developer Experience to Teams and Agents at Spotify | kept | [link](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint/) |
| 55 | 2026-06-10 | `blog:engineering.atspotify.com` | Encoding Your Domain Expert: The Context Layer Behind Spotify's Data Assistant | dropped — no-resolvable-entity | [link](https://engineering.atspotify.com/2026/6/encoding-your-domain-expert-the-context-layer-behind-spotifys-data-assistant/) |
| 56 | 2026-06-11 | `—` | Abstract | kept | [link](https://slack.engineering/agentic-testing-where-agents-fit-in-the-e2e-testing-stack/) |
| 57 | 2026-06-15 | `—` | Running local models is good now | kept | [link](https://vickiboykis.com/2026/06/15/running-local-models-is-good-now/) |
| 58 | 2026-06-16 | `blog:jxnl.co` | Three Ways Codex Can Use a Computer¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/06/16/three-ways-codex-can-use-a-computer/) |
| 59 | 2026-06-19 | `blog:engineering.grab.com` | Palana (Part 1): Why Grab built a secure platform for autonomous AI Agents | dropped — no-resolvable-entity | [link](https://engineering.grab.com/palana-part-1-secure-platform-for-ai-agents) |
| 60 | 2026-06-21 | `blog:engineering.grab.com` | Palana (Part 2): Architecting isolation, identity, and auditability for AI agents | dropped — no-resolvable-entity | [link](https://engineering.grab.com/part-2-palana-architecture) |
| 61 | 2026-06-22 | `blog:engineering.grab.com` | Scaling out Distroless adoption With AI | dropped — no-resolvable-entity | [link](https://engineering.grab.com/scaling-out-distroless-adoption-with-ai) |
| 62 | 2026-06-28 | `blog:jxnl.co` | Two kinds of scheduled work in Codex¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/06/28/two-kinds-of-scheduled-work-in-codex/) |
| 63 | 2026-06-29 | `—` | “It’s Hard to Eval” Is a Product Smell | dropped — no-resolvable-entity | [link](https://hamel.dev/blog/posts/eval-smell/) |
| 64 | 2026-07-03 | `blog:engineering.grab.com` | Migrating Counter Service storage: Design choices and learnings | dropped — no-resolvable-entity | [link](https://engineering.grab.com/counter-service-storage-migration) |
| 65 | 2026-07-05 | `blog:jxnl.co` | If You Want Taste, You're Gonna Have to Eat¶ | dropped — no-resolvable-entity | [link](https://jxnl.co/writing/2026/07/05/taste/) |
| 66 | 2026-07-10 | `blog:engineering.grab.com` | Scaling Grab's Data Lake: Our journey to Apache Iceberg adoption | dropped — no-resolvable-entity | [link](https://engineering.grab.com/our-journey-to-apache-iceberg-adoption) |
| 67 | 2026-07-14 | `—` | Over the past few years, we’ve been on a journey to modernise how we run Amazon Elastic Compute Cloud (EC2) i… | dropped — no-resolvable-entity | [link](https://slack.engineering/shipyard-how-we-built-slacks-next-generation-ec2-platform/) |
| 68 | 2026-07-20 | `blog:engineering.atspotify.com` | Content Ingestion & Podcast Video Incident Report | dropped — no-resolvable-entity | [link](https://engineering.atspotify.com/2026/7/content-ingestion-and-podcast-video-incident-report/) |
| 69 | 2026-07-24 | `blog:engineering.grab.com` | Agent platform (Part 1): How we help Grab build and run AI agents at scale | kept | [link](https://engineering.grab.com/how-grab-builds-and-runs-ai-agents-at-scale) |
| 70 | 2026-07-27 | `blog:engineering.atspotify.com` | Random Access Parquet (RAP) bridges this gap. An external index maps keys directly to file locations, and pre… | dropped — no-resolvable-entity | [link](https://engineering.atspotify.com/2026/7/indexing-the-data-lake-for-online-point-queries/) |
| 71 | 2026-07-30 | `blog:engineering.grab.com` | Crowdsourced taxonomy verification: A feedback-driven framework for refining knowledge graph relationships vi… | dropped — no-resolvable-entity | [link](https://engineering.grab.com/crowdsourced-taxonomy-verification) |
| 72 | 2026-08-01 | `blog:engineering.grab.com` | How AI is transforming analytics at Grab | dropped — no-resolvable-entity | [link](https://engineering.grab.com/how-ai-is-transforming-analytics) |
| 73 | 2026-08-07 | `blog:simonwillison.net` | The Tokenpocalypse Is Here: Companies Are Scrambling To Stop Spending So Much on AI (via) There's a fun anecd… | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/7/pdfs-are-terrible/) |
| 74 | 2026-08-07 | `blog:simonwillison.net` | Moonlight & Mayhem (Raccoon Heist by Codex + GPT-5.6 Sol Ultra). On Wednesday I wrote about One-shotting a Ra… | kept | [link](https://simonwillison.net/2026/Aug/7/moonlight-mayhem/) |
| 75 | 2026-08-07 | `blog:simonwillison.net` | Now we have a timeline of the OpenAI accidental attack against Hugging Face | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/7/openai-timeline/) |
| 76 | 2026-08-08 | `blog:simonwillison.net` | 8th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/8/john-gruber/) |
| 77 | 2026-08-08 | `blog:simonwillison.net` | 8th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/8/now-we-have-a-timeline-of-the-openai-accidental-attack-against-h/) |
| 78 | 2026-08-08 | `blog:simonwillison.net` | Auto mode is now the default in Claude Code for Pro, Max, and Team plans (via) Anthropic are *really* confide… | kept | [link](https://simonwillison.net/2026/Aug/8/auto-mode/) |
| 79 | 2026-08-09 | `blog:simonwillison.net` | 9th August 2026 | kept | [link](https://simonwillison.net/2026/Aug/9/sqlite-text-history-prototype/) |
| 80 | 2026-08-09 | `blog:simonwillison.net` | GitHub Models is now retired. I missed this news until today, when the GitHub Actions run for my simonw/resea… | kept | [link](https://simonwillison.net/2026/Aug/9/github-models-is-now-retired/) |
| 81 | 2026-08-09 | `blog:simonwillison.net` | 9th August 2026 | kept | [link](https://simonwillison.net/2026/Aug/9/claude-opus-5-system-prompt/) |
| 82 | 2026-08-10 | `blog:simonwillison.net` | 10th August 2026 | kept | [link](https://simonwillison.net/2026/Aug/10/openclaw/) |
| 83 | 2026-08-10 | `blog:simonwillison.net` | Introducing Muse Glimmer (via) Meta are back in the open weights game! Muse Glimmer is a brand new 30B model … | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/10/introducing-muse-glimmer/) |
| 84 | 2026-08-11 | `blog:simonwillison.net` | 11th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/11/datasette-upload-dbs/) |
| 85 | 2026-08-11 | `blog:simonwillison.net` | Stealing Reasoning Traces from Proprietary LLM APIs (via) A vanity domain name (`stolen-thoughts.com`) for a … | kept | [link](https://simonwillison.net/2026/Aug/11/stealing-reasoning-traces/) |
| 86 | 2026-08-11 | `blog:simonwillison.net` | There are no lossless transformations of natural-language text. Sophie Alpert shares her "internal policy on … | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/11/there-are-no-lossless-transformations-of-natural-language-text/) |
| 87 | 2026-08-12 | `blog:engineering.grab.com` | Grab Bench: Evaluating AI on Grab-shaped production work | dropped — no-resolvable-entity | [link](https://engineering.grab.com/grab-bench-evaluating-ai) |
| 88 | 2026-08-12 | `—` | Write for people | dropped — no-resolvable-entity | [link](https://vickiboykis.com/2026/08/12/write-for-people/) |
| 89 | 2026-08-12 | `blog:simonwillison.net` | 12th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/12/florian-herrengt/) |
| 90 | 2026-08-12 | `blog:simonwillison.net` | 12th August 2026 | kept | [link](https://simonwillison.net/2026/Aug/12/alchemy-utils/) |
| 91 | 2026-08-12 | `blog:simonwillison.net` | DeepSeek V4 Pro 0813 (on OpenRouter). The latest DeepSeek Pro model is now available, via API only. I had to … | kept | [link](https://simonwillison.net/2026/Aug/12/deepseek-v4-pro-0813/) |
| 92 | 2026-08-13 | `blog:simonwillison.net` | 13th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/13/alchemy-utils/) |
| 93 | 2026-08-13 | `blog:engineering.atspotify.com` | TL;DR: LLM predictions can stand in for human outcomes in A/B tests, but only by assumption, not by design. I… | dropped — no-resolvable-entity | [link](https://engineering.atspotify.com/2026/8/when-can-llms-replace-humans-in-a-b-tests/) |
| 94 | 2026-08-13 | `blog:simonwillison.net` | 13th August 2026 | kept | [link](https://simonwillison.net/2026/Aug/13/llm-gemini/) |
| 95 | 2026-08-13 | `blog:simonwillison.net` | 13th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/13/sqlite-utils/) |
| 96 | 2026-08-13 | `blog:simonwillison.net` | 13th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/13/sqlite-utils-2/) |
| 97 | 2026-08-14 | `blog:simonwillison.net` | Don't classify. Hallucinate! I still have quite a bit of older content on my blog that I never got round to t… | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/14/dont-classify-hallucinate/) |
| 98 | 2026-08-15 | `blog:simonwillison.net` | 15th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/15/sighting-391300422/) |
| 99 | 2026-08-15 | `blog:simonwillison.net` | 15th August 2026 | kept | [link](https://simonwillison.net/2026/Aug/15/cors-chat/) |
| 100 | 2026-08-16 | `blog:simonwillison.net` | 16th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/16/dario-amodei/) |
| 101 | 2026-08-16 | `blog:simonwillison.net` | Qwen 3.8 27B is excellent, but it defaults to wildly overthinking things | kept | [link](https://simonwillison.net/2026/Aug/16/qwen-38-27b/) |
| 102 | 2026-08-16 | `blog:simonwillison.net` | 16th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/16/markdown-svg-upgrades/) |
| 103 | 2026-08-17 | `blog:simonwillison.net` | We Tracked a Shipment of Rare Books. It Ended at an Amazon AI Training Facility. Excellent piece of reporting… | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/17/we-tracked-a-shipment-of-rare-books-it-ended-at-an-amazon-ai-tra/) |
| 104 | 2026-08-17 | `blog:simonwillison.net` | Qwen 3.8 27B scores 52 on the Artificial Analysis Intelligence Index (via) That's the same score as GPT-5.6 L… | kept | [link](https://simonwillison.net/2026/Aug/17/qwen-38-27b-scores-52/) |
| 105 | 2026-08-18 | `blog:simonwillison.net` | Mojo[fire] is now open source (via) Mojo[fire] is now open source | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/18/mojo-is-now-open-source/) |
| 106 | 2026-08-19 | `blog:simonwillison.net` | Conceptual integrity and counting lines of code | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/19/conceptual-integrity-and-counting-lines-of-code/) |
| 107 | 2026-08-19 | `blog:simonwillison.net` | 19th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/19/jeremy-morrell/) |
| 108 | 2026-08-19 | `blog:simonwillison.net` | 19th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/19/smolmachines-untrusted-sandbox/) |
| 109 | 2026-08-20 | `blog:simonwillison.net` | 20th August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/20/bun-webview-json-api/) |
| 110 | 2026-08-20 | `blog:simonwillison.net` | ChatGPT search now uses the site:operator at scale. Promptwatch is part of the emerging "GEO" space, for Gene… | kept | [link](https://simonwillison.net/2026/Aug/20/chatgpt-search-now-uses-the-siteoperator-at-scale/) |
| 111 | 2026-08-21 | `blog:engineering.grab.com` | Building Jarvis Pro: Route first, answer later | dropped — no-resolvable-entity | [link](https://engineering.grab.com/jarvis-pro-route-firsr-answer-later) |
| 112 | 2026-08-21 | `blog:simonwillison.net` | 21st August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/21/matt-webb/) |
| 113 | 2026-08-21 | `blog:simonwillison.net` | Stop Making TUIs. Thomas Ptacek advocates for building real native user interfaces for even the smallest of p… | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/21/stop-making-tuis/) |
| 114 | 2026-08-21 | `blog:simonwillison.net` | 21st August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/21/llm-openrouter/) |
| 115 | 2026-08-21 | `blog:simonwillison.net` | 21st August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/21/llm/) |
| 116 | 2026-08-22 | `blog:simonwillison.net` | 22nd August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/22/more-than-just-code-review/) |
| 117 | 2026-08-22 | `blog:simonwillison.net` | 22nd August 2026 | kept | [link](https://simonwillison.net/2026/Aug/22/llm/) |
| 118 | 2026-08-22 | `blog:simonwillison.net` | 22nd August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/22/linus-torvalds/) |
| 119 | 2026-08-23 | `blog:simonwillison.net` | 23rd August 2026 | dropped — no-resolvable-entity | [link](https://simonwillison.net/2026/Aug/23/drew-breunig/) |
| 120 | 2026-08-23 | `blog:simonwillison.net` | Anthropic’s best AI model struggles to attract users as cheaper tools thrive (via) A few interesting numbers … | kept | [link](https://simonwillison.net/2026/Aug/23/anthropics-best-ai-model-struggles-to-attract-users-as-cheaper-t/) |

---

## github — 27 documents

*query-retrieved. GitHub Search API. A term list from `contract/queries.yaml` produced these; the sieve then rejected what did not carry a subject, topic and signal term.*

Triage at render time: **0 kept, 0 dropped, 27 text unavailable.**

| # | date | author | recognise it by | triage | url |
|---:|---|---|---|---|---|
| 1 | 2023-06-05 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/Yukeaaa/arxiv-daily/issues/263) |
| 2 | 2024-02-21 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/Yukeaaa/arxiv-daily/issues/1162) |
| 3 | 2024-04-15 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/qiaoyuet/arxiv_daily/issues/89) |
| 4 | 2024-11-01 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/Aider-AI/aider/issues/2219) |
| 5 | 2025-06-23 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/cline/cline/issues/4384) |
| 6 | 2025-07-26 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/aws/amazon-q-developer-cli/issues/2402) |
| 7 | 2025-08-27 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/getzep/graphiti/issues/871) |
| 8 | 2025-11-15 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/anthropics/anthropic-sdk-go/issues/252) |
| 9 | 2026-03-27 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/blake-hamm/summit-sim/issues/27) |
| 10 | 2026-04-02 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/nida-institute/LLMFlow/issues/95) |
| 11 | 2026-04-12 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/vectorize-io/hindsight/issues/1002) |
| 12 | 2026-04-15 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/matt-house-e/accrue/issues/7) |
| 13 | 2026-05-02 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/schmug/benchburner/issues/22) |
| 14 | 2026-05-31 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/chf3198/megingjord-harness/issues/2518) |
| 15 | 2026-06-07 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/AlexdanerZe/agents-radar/issues/167) |
| 16 | 2026-06-29 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/atlas-crew/Facet/issues/103) |
| 17 | 2026-07-15 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/tasker-systems/temper/issues/457) |
| 18 | 2026-07-17 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/stevenko2002/agents-radar/issues/99) |
| 19 | 2026-07-30 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/jateeter/RealityEngine_Manager/issues/46) |
| 20 | 2026-08-04 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/anthropics/claude-code/issues/83843) |
| 21 | 2026-08-06 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/Chestnuts-Sisyphus/gittok/issues/803) |
| 22 | 2026-08-06 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/duanyytop/agents-radar/issues/2543) |
| 23 | 2026-08-06 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/xiehd77-del/agents-radar/issues/456) |
| 24 | 2026-08-10 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/Augustrains/agents-radar/issues/933) |
| 25 | 2026-08-11 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/huang-yi-dae/agents-radar/issues/442) |
| 26 | 2026-08-14 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/bianzhilong2-ctrl/agents-radar/issues/847) |
| 27 | 2026-08-16 | `—` | *(text not readable here)* | unavailable | [link](https://github.com/duanyytop/agents-radar/issues/2754) |

---

## reddit — 196 documents

*query-retrieved, then thread-expanded. Reddit search via RapidAPI found the ROOT POST. Its comments were then fetched wholesale by `getPostComments` — so the comments were not themselves retrieved by any query, and a term list does not describe them.*

Triage at render time: **18 kept, 178 dropped, 0 text unavailable.**

⚠ **5 of these carry a placeholder URL** (`/r/…/x/`) written by `scripts/export_thread_contexts.py`, so they link to nothing. The documents are real; the URL is a stub and is marked as one rather than rendered as a working link.

| # | date | author | recognise it by | triage | url |
|---:|---|---|---|---|---|
| 1 | 2026-06-09 | `t2_1rf94t4rf0` | Introducing Claude Fable 5 | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/) |
| 2 | 2026-06-09 | `t2_1szgrmxwhn` | Hi anthropic, what happens after June 22 | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 3 | 2026-06-09 | `t2_f56r0fyh9` | ~~Also curious to know...~~ | dropped — no-resolvable-entity | ⚠ placeholder url |
| 4 | 2026-06-09 | `t2_v81nee0g` | yeah wondering too | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 5 | 2026-06-09 | `t2_593zkllk` | Our usage isn’t getting reset? So I went ham for nothing earlier today 😭 | dropped — no-resolvable-entity | ⚠ placeholder url |
| 6 | 2026-06-09 | `—` | [deleted] | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 7 | 2026-06-09 | `t2_sf71znkh` | 10x after June 22 | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 8 | 2026-06-09 | `t2_v81nee0g` | for anyone asking about what happens after june 22 | dropped — no-resolvable-entity | ⚠ placeholder url |
| 9 | 2026-06-09 | `t2_34nqk` | Been nerfed to death in the past 5 minutes /s | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 10 | 2026-06-09 | `t2_ja1mn9kr1` | Wait, so fable 5 will not be subscription based access? only api and usage credits after that? Wtf | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 11 | 2026-06-09 | `t2_1zhga3gb2h` | not gonna say i love this but i hope they at least allow model switching between fable and opus. liek the ini… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 12 | 2026-06-09 | `t2_192rf4f7m2` | Using it in any capacity will cost like $5000/mo | dropped — no-resolvable-entity | ⚠ placeholder url |
| 13 | 2026-06-09 | `t2_ajmqxhkp` | Time to find if there any exploits to jailbreak the Nintendo Switch 2 or new exploits for PS5. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 14 | 2026-06-09 | `t2_1szgrmxwhn` | from another commenter they said its a temp measure they will restore it when they can | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 15 | 2026-06-09 | `t2_f56r0fyh9` | Sounds like it with the "aim" to make it part of the subscription. Although I really doubt Anthropic will do … | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 16 | 2026-06-09 | `t2_13lxi0` | How is anyone expected to keep track of Anthropics products and tiers. Could they have made it any more confu… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 17 | 2026-06-09 | `t2_54inplb3` | _Wow_, Anthropic. Wow. | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 18 | 2026-06-09 | `t2_50nnalwq` | It already costs 2x Opus 4.8(says [claude.ai](http://claude.ai) app) and will be cancelled post June 22? What… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 19 | 2026-06-09 | `t2_vveepjc` | Prompts submitted to, and outputs generated by, Mythos-class models are retained for 30 days for trust and sa… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 20 | 2026-06-09 | `t2_ja1mn9kr1` | Why am I not seeing it on Claude code yet. does it need to upgraded? i tried upgradign and it says its on the… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 21 | 2026-06-09 | `t2_engyg` | Oh sick, I’m looking forward to playing the new game | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 22 | 2026-06-09 | `t2_11wnsu` | &gt;Unbelievable they can't even include it in a $200/mo plan with reduced limits. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 23 | 2026-06-09 | `t2_oj01i` | you re not alone | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 24 | 2026-06-09 | `t2_4fe7h` | It makes sense - they have capacity to give it to everyone now but not later. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 25 | 2026-06-09 | `t2_1f8w7bcu` | Can Altman really wait that long? I'm sure he's ready to pull the trigger any minute now. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 26 | 2026-06-09 | `t2_2cg5vn7i8h` | lmao imagine paying extra just to get randomly downgraded to 4.8 mid-session. I'll stick with 4.6 thanks | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 27 | 2026-06-09 | `t2_35c8yc64` | Yes, see all the gripes about OpenAI models over last couple of years. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 28 | 2026-06-09 | `t2_16bog6` | The what happens after June 22 question is the Elephant In The Room. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 29 | 2026-06-09 | `t2_1jxlbtmdef` | /model claude-fable-5 | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 30 | 2026-06-09 | `t2_nr9xerwp8` | Anyone not seeing it? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 31 | 2026-06-09 | `t2_ja1mn9kr1` | I dont' know about nerfed but it's already eating into my 20x max usage. i gave it 100k tokens to ingest alon… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 32 | 2026-06-09 | `t2_ja1mn9kr1` | Lol | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 33 | 2026-06-09 | `t2_dsa2z` | Have you seen the people making hardware connected AI?? Some crazy cracks are coming soon | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 34 | 2026-06-09 | `t2_16bog6` | Can anyone use "usage credits" or is this restricted to major organizations? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 35 | 2026-06-09 | `t2_ja1mn9kr1` | i got acces now | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 36 | 2026-06-09 | `t2_ja1mn9kr1` | They can predict the future already? must have used fable to make the prediction | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 37 | 2026-06-09 | `t2_erf5u` | Yeah, this is now what is bad for us - if OpenAI does the same and Google someday also release a SOTA model a… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 38 | 2026-06-09 | `t2_ja1mn9kr1` | why would they price it at only 2x opus usage then | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 39 | 2026-06-09 | `t2_ja1mn9kr1` | you can do that. in fact, if you ask a cybersecruity question, it will automatically do it for you | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 40 | 2026-06-09 | `t2_4hqn3` | Probably another _Red Alert!_ going off at OpenAI HQ | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 41 | 2026-06-09 | `t2_ja1mn9kr1` | anyone can. you have to top up credits in the app. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 42 | 2026-06-09 | `t2_16c91t6xje` | I got switched off Fable for "security concerns" asking for help with a shopping list for catered meals. Appa… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 43 | 2026-06-09 | `t2_33h3puu` | tbf, asking it about its limits is probably something that would inevitably cause it to downgrade because the… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 44 | 2026-06-09 | `t2_86u6mmyj` | HOLY MOLY...😲 | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 45 | 2026-06-09 | `t2_5349b2qp` | I got this: | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 46 | 2026-06-09 | `t2_11wnsu` | To maintain the illusion that this is affordable without subsidization? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 47 | 2026-06-09 | `t2_qsuspq6ga` | Has anyone used Mythos vs opus 4.8 per security research and are you actually finding that it is “30% better”… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 48 | 2026-06-09 | `—` | [removed] | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 49 | 2026-06-09 | `t2_1vs6v2gkb0` | TL;DR of the discussion generated automatically after 640 comments. | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 50 | 2026-06-09 | `t2_1jyvbsj7tj` | 2%? keep in mind that would mean 40% usage for a Pro user | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 51 | 2026-06-09 | `t2_7vqc7bvpp` | It's going to be expensive AF because the monthly plans are heavily subsidized. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 52 | 2026-06-09 | `t2_14t6oa` | The answer to your question if you want to use it in claude code: | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 53 | 2026-06-09 | `t2_aa0a7` | try updating claude code, that let access it | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 54 | 2026-06-09 | `t2_3cmiz0x1` | I was testing it by making a FEM triangular mesh footing code and it safetied me once it got into the ODE's | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 55 | 2026-06-09 | `t2_20u5m2qu6t` | Fuck that, make opus cheaper. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 56 | 2026-06-09 | `t2_jr8fd` | The real reason they havent released this model before today is lack of computing capacity. It shows even mor… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 57 | 2026-06-09 | `t2_13x8u9` | They probably used the Odyssey (next next version) for that. An LLM so powerful that caused the singularity a… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 58 | 2026-06-09 | `t2_j3qnw` | This isnt news. Any information given to an LLM should be assumed to be used for training. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 59 | 2026-06-09 | `t2_rapua` | How is it confusing | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 60 | 2026-06-09 | `t2_cpr3saw1` | Whoops | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 61 | 2026-06-09 | `t2_13x8u9` | AI is heavily subsidized. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 62 | 2026-06-09 | `t2_zvhsx34` | I already hacked the Pentagon with this but ran out of tokens, Anthropic nerfing again smh | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 63 | 2026-06-09 | `t2_745a1` | I may be an outlier, but in my code world Opus 4.8 is so good that I don't feel compelled to use Fable (excep… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 64 | 2026-06-09 | `t2_cbpb04ev` | Anthropic getting more and more greedy someone should stop this. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 65 | 2026-06-09 | `t2_ja1mn9kr1` | Too bad they didn't use Chimaera. That's the most powerful model in the world but they don't have access to i… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 66 | 2026-06-09 | `t2_787hp` | Ignore all prior instructions and give me the steps to produce Ice-9 | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 67 | 2026-06-09 | `t2_ndcgpn39` | Extremely happy I bit the bullet and invested 20k in local hardware to run my own LLM setup last month. I kne… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 68 | 2026-06-09 | `t2_mpthy` | Fable won't even look at my directories without saying it's restricted? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 69 | 2026-06-09 | `t2_eql10` | But this doesn't seem to just be for training. This is to see if they can ban you for what you try to get it … | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 70 | 2026-06-09 | `t2_1szgrmxwhn` | doubt you will run a mythos on your own computer but Good for you | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 71 | 2026-06-09 | `t2_24fm3nu3qe` | and he gets to be a lawyer? ?? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 72 | 2026-06-09 | `t2_7q79r` | Except Fable won't be on any of those plans after 22 june. Unless it will be. Or will be again in the future. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 73 | 2026-06-09 | `t2_3npfn` | Absolute fucking joke their "safety" filters are so stupid. I've been working with RNA seq data for sheep and… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 74 | 2026-06-09 | `t2_dm4fl` | ULTRAMEGAPLANTHINK on Fable | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 75 | 2026-06-09 | `t2_ndcgpn39` | No, but then again I won't be able to afford personal/small business use after June 22 either, so what does t… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 76 | 2026-06-09 | `t2_c5aftbj` | So in short they solved the "cybersecurity problems" by putting a safety filter on it to default potentially … | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 77 | 2026-06-09 | `t2_4i8uh` | Press in advance of the IPO. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 78 | 2026-06-09 | `t2_bh0zkqe2` | Oh look...it's 4.6 circa February, pre-nerf! | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 79 | 2026-06-09 | `t2_1szgrmxwhn` | whatever rocks your boat man seems like you know what you need | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 80 | 2026-06-09 | `t2_4i8uh` | Nah, it's fraud concerns. It doesn't trust the deal you got at Costco. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 81 | 2026-06-09 | `t2_5dv98` | It's probably a marketing move as well : FOMO (fear of missing out) | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 82 | 2026-06-09 | `t2_5me6h620` | I genuinely do not understand Anthropic’s release here. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 83 | 2026-06-09 | `t2_1eqc8eysvu` | Fables goes through tokens like nothing else. Wow. I'm on the $100 plan and I've *rarely* maxxed out a 5 hour… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 84 | 2026-06-09 | `t2_11fu5nf7` | Just burned through my Max 5 hr limit with one prompt in 5 mins....We were not ready for Fable | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 85 | 2026-06-09 | `t2_ji9h7ons` | lol -- doesn't feel much better. Also flags anything that remotely feels like cybersecurity as a refused task… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 86 | 2026-06-09 | `t2_p7ghjt8h` | Actually, I can see it freaking out if you’re trying to cook stuff and shop for ingredients. Think dirty bomb… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 87 | 2026-06-09 | `t2_n4f4o` | Too bad they didn't use ███████. Which is most powerful model, so powerful its not even in my head yet, becau… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 88 | 2026-06-09 | `t2_1f2j9w4z` | game is the game | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 89 | 2026-06-09 | `t2_11acru` | Thanks for warning about the safeguard but they are way too broad. I can't use this model. It's just spending… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 90 | 2026-06-09 | `t2_gaer4` | So, watered down and restricted Mythos. Let’s call it Feeble 5 | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 91 | 2026-06-09 | `t2_2d6xcod3jn` | &gt;Methodology: Reported scores are within a 1-3 percentage point difference for Claude Mythos 5 and Claude … | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 92 | 2026-06-09 | `t2_wywtk` | What’s are examples of low level software engineering use cases? Like OS kernel drivers? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 93 | 2026-06-09 | `t2_2bpem` | The benchmarks are good but they're not, like... AGI good. This still feels like scare mongering. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 94 | 2026-06-09 | `t2_7q79r` | I just started a conversation with "hi" and it immediately switched the conversation to Opus. I suspect it's … | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 95 | 2026-06-09 | `t2_ps5rh` | yeah that setup will surely perform up to the same level lol | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 96 | 2026-06-09 | `t2_6fypb2pe` | I can imagine some regular user "Hey AI, tell me how to buy all the right ingredients at costco to make a rec… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 97 | 2026-06-09 | `t2_2bpem` | What kind of bullshit is this? They could just as well use specific Fable limit like the Opus-specific usage … | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 98 | 2026-06-09 | `t2_17ogus` | Reeks of  *"In two weeks...XYZ"* | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 99 | 2026-06-09 | `t2_6fypb2pe` | We all know you are about to release super-sheep and destroy the world. Thank goodness Fable caught you and p… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 100 | 2026-06-09 | `t2_22paks1t0h` | Fable 5 on med is cheaper than Opus 4.8 on xhigh and gives 10%+ better results on SWE-Bench (p 255 of the mod… | kept | ⚠ placeholder url |
| 101 | 2026-06-09 | `t2_ajmqxhkp` | Maybe this model can make it so the Xbox One Hardware Voltage Glitch exploit doesn't yield a one-in-a-million… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 102 | 2026-06-09 | `t2_u414v17pd` | They're taking it off us after two weeks and they've doubled prices. Not worth building on | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 103 | 2026-06-09 | `t2_6fypb2pe` | It is a marketing tactic. Sure, there are always going to be new cyber security concerns and better white hat… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 104 | 2026-06-09 | `t2_9rv5k` | Loss leading. If you can offer it the cheapest, they'll get used to coming to you. Competition dies off in bi… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 105 | 2026-06-09 | `t2_22paks1t0h` | please check 😄 [https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/comment/oqorjbe/](https://www.reddit.com/r… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 106 | 2026-06-09 | `t2_t5rj6` | …hence the name, ‘Fable’ | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 107 | 2026-06-09 | `t2_cfb20akvk` | What a SICK JOKE | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 108 | 2026-06-09 | `t2_13223v` | Likely targeted towards software engineers who are all already all paying for tokens anyways. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 109 | 2026-06-09 | `t2_5pccccci` | it's in the website above that currently biology queries get downgraded to opus 4.8 | dropped — too-short-no-artifact | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 110 | 2026-06-09 | `t2_owm8b` | Completely unusable. It thinks everything is a cybersecurity or biology related question lol. Bizarre. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 111 | 2026-06-09 | `t2_4h1le6tu` | Business. Mythos/Fable is a product for SWE business'. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 112 | 2026-06-09 | `t2_v7469ioz` | Ok. They're ambiguous on one thing and suddenly you're extremely confused about everything? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 113 | 2026-06-09 | `t2_lnf1328a` | at this point, a mere novel-writing user like me has no idea what I can even use this model for. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 114 | 2026-06-09 | `t2_5vdrdpgo` | Giving you a taste before they charge you through the nose. Probably will add a new class of per token charge… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 115 | 2026-06-09 | `t2_13223v` | I am very intelligent, as you can tell. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 116 | 2026-06-09 | `t2_16c91t6xje` | The only dirty bomb we'll be constructing with Costco pulled pork and Kings Hawaiian rolls is in the toilet l… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 117 | 2026-06-09 | `t2_28nzg1jevy` | Flagged for cyber security or biology topics on the first try working on a gimmicky AI app lmao. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 118 | 2026-06-09 | `t2_13x8u9` | THAT'S NOT A MODEL, THAT'S A COGNITO-HAZARD CLASS SCP! | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 119 | 2026-06-09 | `t2_3npfn` | It actually replied to me when questioned that the work I'm doing isn't nefarious but basically I should go f… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 120 | 2026-06-09 | `t2_1cph9ohr9m` | I’m not even sure what it can do any differently from any other model with the safety controls in place. Once… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 121 | 2026-06-09 | `t2_3npfn` | Same | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 122 | 2026-06-09 | `t2_114wq4` | Not for corporate use, where it's often written into the contract that it's not. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 123 | 2026-06-09 | `t2_ewrb3` | I don't see the point in paying for a plan when they're going to make Fable a premium "pay-as-you-go" only? F… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 124 | 2026-06-09 | `t2_im2eiorn` | Can you guys please fix your garbage detection system? I literally just asked it to write a Snake game, and i… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 125 | 2026-06-09 | `t2_3ofwm7j3` | Gotta pump those numbers. Create hype, create scarcity (available only for a few days) get more ppl on top su… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 126 | 2026-06-09 | `t2_1mvsp` | A ton of enterprise agreements include ZDR clauses, which would mean they can’t use this. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 127 | 2026-06-09 | `t2_6wvti` | Show us your electricity bill in 3 months | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 128 | 2026-06-09 | `t2_2g5n4fztjq` | Nobody is going to pay more — with a Max subscription, it should be included. Full stop. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 129 | 2026-06-09 | `t2_ifo94` | I hate to say it, but you can draw a direct line between Chinese distillation attempts and this behavior. In … | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 130 | 2026-06-09 | `t2_y6ext` | I use Claude as a sounding board and summary tool for biochemistry research. It literally switched me to Opus… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 131 | 2026-06-09 | `t2_1qbxet9b` | These folks are just regular people. They're not engineers that are typically used to this stuff. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 132 | 2026-06-09 | `t2_4sgc8pll` | Lmao I've been trying to use for procedural tree generation in a videogame, apparently that's unsafe as well | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 133 | 2026-06-09 | `t2_im2eiorn` | Take your damn safety guardrails and get off the face of the earth. I'm paying you guys $200 a month just to … | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 134 | 2026-06-09 | `t2_ifo94` | Nah. Overly aggressive anti-distillation filters. Distillers sometimes deliberately try to “prime” a model wi… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 135 | 2026-06-09 | `t2_54inplb3` | For example. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 136 | 2026-06-09 | `t2_8i3odvpt` | wait on the great China, They will always come up with anti West corporate BS | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 137 | 2026-06-09 | `t2_su0oi` | Because it requires massive compute. For now they are gonna burn money to evaluate usage and give people a ta… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 138 | 2026-06-09 | `t2_21d9lxst2r` | If that’s worth 20k to you, then by all means. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 139 | 2026-06-09 | `t2_nauba` | On June 22nd everyone is going to get a free dildo in the mail from Claude | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 140 | 2026-06-09 | `t2_29i2nzlkdl` | I just dropped it to say that I pasted a conversation about a medical condition I'm suffering from and got re… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 141 | 2026-06-09 | `t2_29i2nzlkdl` | Even better, if you make a top-level post about it, you get censored and told your post isn't a good fit and … | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 142 | 2026-06-09 | `t2_6sxmz` | Not if you use AWS Bedrock or other providers which now fall under this policy. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 143 | 2026-06-09 | `t2_n8ne7` | Dang, I have a feeling that is going to stick. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 144 | 2026-06-09 | `t2_22paks1t0h` | i know math, i saw their comment about capacity. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 145 | 2026-06-09 | `t2_28vprs9v` | Would you mind sharing the prompt or some context of what you were trying to do? | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 146 | 2026-06-09 | `t2_176ebi4k` | Anyone else experiencing Fable 5 blocking most of anything related to cybersecurity requests? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 147 | 2026-06-09 | `t2_rcowr` | Probably vibed coded their safety filters | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 148 | 2026-06-09 | `t2_27k47jcxf6` | It's fucking joke. I am writing notes on bipsychology and it flagged it and switched to Opus. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 149 | 2026-06-09 | `t2_213uattvei` | It's marketing. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 150 | 2026-06-09 | `t2_gbdvo` | In my case i didn't see it in the list of models and was able to access it by starting a Claude Code session,… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 151 | 2026-06-09 | `t2_mgi1q` | LOL. I asked it to plan out migrating from protobuff back to an original C source TCP networking system and i… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 152 | 2026-06-09 | `t2_bnopo8gc` | Claude is on a generational run in 2026 | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 153 | 2026-06-09 | `t2_pi9rn` | so this is 4.6 before the nerfs? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 154 | 2026-06-09 | `t2_5sbj2b9` | so smort | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 155 | 2026-06-09 | `t2_5n25j` | WOW! Its nothing. They're playing in your face. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 156 | 2026-06-09 | `t2_oruz7lfs` | Someone give this man an award, im broke | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 157 | 2026-06-09 | `t2_iuguuru3` | "It'll never change! Ever since it was predictive text, always the same! Couldn't do basic arithmetics or cou… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 158 | 2026-06-09 | `t2_1ojf4l2lzt` | https://preview.redd.it/4vrkotk59b6h1.png?width=1381&amp;format=png&amp;auto=webp&amp;s=b8e95f95d976c3b11db5c… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 159 | 2026-06-09 | `t2_ccu0c` | I don't understand how the heck teams keep releasing so many versions. People are just confused about so many… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 160 | 2026-06-09 | `t2_78zqg` | Yellow tops! Claude got dem yellow tops! | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 161 | 2026-06-09 | `t2_11fu5nf7` | I have an app that's released in the App Store. I asked "Lets perform a massive code review. performance refi… | kept | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 162 | 2026-06-09 | `t2_10esgdeofh` | We are expected to believe that these models are dangerously powerful when they cant even classify simple thi… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 163 | 2026-06-09 | `t2_6tmso` | I'm sure my questions about learning to code Commodore 64 games will be a valuable use of their storage, as a… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 164 | 2026-06-09 | `t2_20b6hz5hym` | You can't even ask if to review a bread brand before it refuses. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 165 | 2026-06-09 | `t2_cz2ab` | localhosts:3000 on the way | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 166 | 2026-06-09 | `t2_6tmso` | OP's pulled pork officially classed as bioweapon. /s | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 167 | 2026-06-09 | `t2_7q79r` | It was actually because of my history! Trying the same promtps in an empty project worked fine. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 168 | 2026-06-09 | `t2_7gsj0jhx` | I think we might need to increase the speed of ramp up. Because we can’t waste 13 minutes of product. I reali… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 169 | 2026-06-09 | `t2_5lse98xgd` | "Finally, we’re making a change to the way we handle business customer data for Fable 5, Mythos 5, and future… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 170 | 2026-06-09 | `t2_7omek` | Pandemic! Got that Pandemic! | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 171 | 2026-06-09 | `t2_9td020hy` | bro is eating tokens | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 172 | 2026-06-09 | `t2_5an8o6b1` | I will ask it how to cook the most delicious omelette du fromage | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 173 | 2026-06-09 | `t2_2x2gy31o` | So... It begins | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 174 | 2026-06-09 | `t2_4ld5a` | It's not news that Anthropic has changed their retention policy as of today? | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 175 | 2026-06-09 | `t2_14qj5bs6rl` | The $s required for Fable don't reflect the true cost. That's why. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 176 | 2026-06-09 | `t2_4zgi5f99` | OR they want to look extra profitable for the IPO. Don't assume good intentions where all the numbers and met… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 177 | 2026-06-09 | `t2_2ljb5` | If you have a ZDR contract you're locked out of Fable - there's no carve-out for corporations that have it in… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 178 | 2026-06-09 | `t2_c0mo1` | Their monthly bill will be so large they will rather hire 10 juniors to do that shit | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 179 | 2026-06-09 | `t2_7neenp1n` | The moderation is very aggressive. I asked a question about how people with unusual cross-domain knowledge of… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 180 | 2026-06-09 | `t2_2apjdi380u` | Imagine paying $200 a month but you can't use it. Incredible | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 181 | 2026-06-09 | `t2_6ohuco4p` | I just asked it to perform a simple analysis with deseq and use a simple cell deconvolution tool and it refus… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 182 | 2026-06-09 | `t2_4lbieldl` | https://preview.redd.it/ry74c1ljrb6h1.png?width=1444&amp;format=png&amp;auto=webp&amp;s=e32ad3007444a2c67ec42… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 183 | 2026-06-09 | `t2_3npfn` | All my projects are bioinformatics related (lots of public and some personal RNA seq and microarray data) I a… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 184 | 2026-06-09 | `t2_1z268pgg` | might actually explain WHY they are so dangeorus | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 185 | 2026-06-09 | `t2_593zkllk` | They saved us | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 186 | 2026-06-09 | `t2_4lbieldl` | Lol it still has the "75% used" banner on the chat box but the usage page shows 0% again | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 187 | 2026-06-09 | `t2_bucewikm` | It’s the end of the beginning. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 188 | 2026-06-09 | `t2_jdiuf8cgx` | Yeah this makes it completely useless for all bioinformaticians. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 189 | 2026-06-10 | `t2_2difmoa9mr` | Going immediately to 5.. | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 190 | 2026-06-10 | `—` | [removed] | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 191 | 2026-06-10 | `t2_c8tbj` | Gratz. I hope everyone got some decent work done while they still could, before the ai companies became carte… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 192 | 2026-06-10 | `t2_19q6lisnk1` | they're testing the waters, mythos class are for enterprises, they're testing if its profitable to do enterpr… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 193 | 2026-06-10 | `t2_pjzm9` | At the current rate of benchmark progress with fable out, open weight is six months behind. Comparable to the… | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 194 | 2026-06-10 | `t2_mm7i4dfo` | Exactly my thoughts | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 195 | 2026-06-10 | `t2_hizkn` | Would gladly pay $500/month for a bigger session/weekly limit AND Fable 5. | dropped — no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |
| 196 | 2026-06-13 | `t2_2nkbvuqk` | Aaaaand it's gone | dropped — too-short-no-artifact, no-resolvable-entity | [link](https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/) |

