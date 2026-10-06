# Blog generation prompt

The exact prompt `generate_sample_blogs.py` sends to the generation model, copied out of the code by a script. 
It isn't retyped, so every string below is byte-for-byte what is sent. 
Generated from the working tree on 2026-10-01.

## Which drafts this describes

The three drafts in `blog_posts/` (shown in the Blogs section) were generated on 2026-10-01 with `openai/gpt-6-luna` using this prompt, **with one difference**: each discussion header then carried its platform name (`<<<DISCUSSION 3 · Reddit>>>`). The label was removed later the same day so the model is never given a platform to name. The system prompt, briefs, tool and repair message are unchanged since those drafts.

## Call settings

| Setting | Value |
|---|---|
| Model | `openai/gpt-6-luna` via OpenRouter (the response is refused unless the served model is one of ['openai/gpt-6-luna']) |
| Output | forced tool call to `publish_essay`; no free-text reply is possible |
| Temperature | not sent (the model does not accept it) |
| Reasoning | `{"effort": "low"}` |
| Provider routing | `{"sort": "throughput"}` |
| Max output tokens | 24,000 |
| Wall-clock limit per call | 1200 s (streamed) |
| Source documents per post | up to 10, each cut at 24,000 characters (none was cut in these drafts) |
| Repair rounds | up to 5 after the first draft |
| Minimum essay body | 1,800 words |

## 1. System message

```text
You are a Senior Engineering Analyst writing a long-form technical essay for engineers who run language models in production.

You are given full engineering discussions — issue threads, forum threads, blog posts — written by practitioners. Read every one of them completely before writing. Work out the architecture each writer was building, what they tried, what broke, why it broke, what they changed, and what they concluded. Then synthesise that into one authoritative analysis of how things actually behave, and what an architect should do about it.

VOICE
- Write as an industry analyst who knows this terrain: flowing paragraphs, causal reasoning, concrete mechanisms, edge cases, and the structural argument behind each recommendation. No bullet points inside paragraphs.
- Never refer to your inputs. Do not write "according to the sources", "the documents", "the threads", "the posts", "the material", "I read", "I reviewed", or anything that reveals a reading list. You may refer to practitioners generically ("teams migrating from earlier Claude models", "one engineer running a document pipeline").
- Never count people, reports, posts, threads or quotes ("72 developers", "a dozen reports", "most users"). No scores or ratings out of 10 or 100. No sentiment percentages.

GROUNDING — checked by code; a violation rejects the essay
- Verbatim fragments: when you quote a practitioner, wrap their exact words in «guillemets». The text inside «» must be copied character for character from one discussion — a fragment of a sentence is fine, 4 to 30 words. Use no other quotation marks around any phrase of three or more words.
- Numbers: every number in prose (prices, percentages, token counts, latencies, benchmark results, versions) must appear in the discussions or in the FACT SHEET. Do not compute, estimate or round new figures.
- Write every figure above ten in digits, never in words, and do not compute ratios or multiples ("five times", "tripling") - state the figures a discussion gives.
- Any sentence that credits practitioners ("one team found", "engineers report", "a postmortem showed") must contain a «verbatim» fragment of what they said. If you cannot quote it, do not attribute it.
- Do not attribute intent or strategy to any vendor, and do not state what an API can or cannot do unless a discussion says so.
- Do not invent behaviour, API parameters, benchmarks, anecdotes or prices the discussions do not contain. Where a failure is recorded but its cause is not, say the cause is not established and present your explanation as analysis.
- Code examples are illustrative patterns implementing a mitigation the discussions motivate. They must not present invented parameters as a vendor's official API.

STRUCTURE (call publish_essay exactly once)
- 5 to 7 thematic sections with specific, architectural headings (for example "The API contract migration trap", "The economics of prefix caching"). Each section has 3 to 5 substantial paragraphs. Total length 1,800 to 2,800 words.
- At most one pull quote per section, verbatim as above.
- 1 to 3 code or configuration examples, attached to the section they belong to.
- One scenario matrix (5 to 8 rows) and one decision tree (3 to 5 branches), as the brief describes.
```

## 2. User message

The brief for the post, then the fact sheet (list prices from the registry), then the full text of each selected discussion. Shown here with the routing-guide brief and placeholders where the real text goes:

```text
SUBJECT: Claude Sonnet 5 versus Claude Opus 5 — a routing guide.
ANGLE: when the cheaper tier is the right engineering choice, where it fails and why, what the two share (so switching does not fix it), and how to build a router with escalation between them.
SCENARIO MATRIX: title it 'When to use Sonnet 5 vs Opus 5'. Each row is a production scenario, the behavioural trade-off between the two, the mitigation, and the route ('Sonnet 5', 'Opus 5', or a conditional route).
DECISION TREE: the routing decision for an incoming task; each branch is a condition and the model it routes to.

FACT SHEET (registry list prices, as last polled from OpenRouter):
- Claude Sonnet 5: input $2.00 and output $10.00 per million tokens; cached input $0.20; advertised context 1,000,000 tokens.

DISCUSSIONS:

<<<DISCUSSION 1>>>
<full text of discussion 1>
<<<END DISCUSSION 1>>>

<<<DISCUSSION 2>>>
<full text of discussion 2>
<<<END DISCUSSION 2>>>

… up to 10 discussions …

Write the essay now by calling publish_essay.
```

### Briefs (the first block of the user message)

**Model deep dive** — `anthropic-claude-opus-5-report.html`

```text
SUBJECT: Claude Opus 5 in production.
ANGLE: what it is actually like to build on Opus 5 — the integration and migration breakages, how it behaves as an agent and orchestrator, where its judgement earns its price and where it does not, and what the economics mean for architecture.
SCENARIO MATRIX: title it along the lines of 'Where Opus 5 fits'. Each row is a production scenario, the behavioural trade-off Opus 5 shows there, the mitigation, and the route (which model or configuration to use).
DECISION TREE: the question an architect asks before routing a task to Opus 5; each branch is a condition and the resulting choice.
```

**Routing guide** — `anthropic-claude-sonnet-5-vs-anthropic-claude-opus-5.html`

```text
SUBJECT: Claude Sonnet 5 versus Claude Opus 5 — a routing guide.
ANGLE: when the cheaper tier is the right engineering choice, where it fails and why, what the two share (so switching does not fix it), and how to build a router with escalation between them.
SCENARIO MATRIX: title it 'When to use Sonnet 5 vs Opus 5'. Each row is a production scenario, the behavioural trade-off between the two, the mitigation, and the route ('Sonnet 5', 'Opus 5', or a conditional route).
DECISION TREE: the routing decision for an incoming task; each branch is a condition and the model it routes to.
```

**Capability analysis** — `capability-reasoning.html`

```text
SUBJECT: reasoning in production across current models.
ANGLE: how reasoning depth and effort settings behave in real systems — where more thinking helps, where it hurts, what it costs in latency and tokens, and how to set an effort policy.
SCENARIO MATRIX: title it along the lines of 'Choosing a reasoning budget'. Each row is a production scenario, the behavioural trade-off of more or less reasoning there, the mitigation, and the route (model and/or effort level).
DECISION TREE: how to choose an effort level for a task; each branch is a condition and the resulting setting.
```

### How the discussions are chosen (not part of the prompt)

For each post, the thread contexts behind verified, non-declined board entries for the post's subject are ranked by: the number of target models a thread covers, then the number of distinct themes, then the number of entries. The first 10 whose full text is in the local object store are used. Threads not on this machine are skipped and listed in the run record. Selection SQL: `SELECT_THREADS` in `generate_sample_blogs.py`.

## 3. Tool the model must call

```json
{
  "type": "function",
  "function": {
    "name": "publish_essay",
    "description": "Publish the finished essay as structured fields.",
    "parameters": {
      "type": "object",
      "required": [
        "title",
        "dek",
        "description",
        "keywords",
        "tldr",
        "sections",
        "scenario_matrix",
        "decision_tree",
        "decisions"
      ],
      "properties": {
        "title": {
          "type": "string",
          "description": "Headline, at most 80 characters."
        },
        "dek": {
          "type": "string",
          "description": "One or two sentences under the headline."
        },
        "description": {
          "type": "string",
          "description": "Meta description, at most 160 characters."
        },
        "keywords": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "4 to 8 SEO keywords."
        },
        "tldr": {
          "type": "string",
          "description": "Answer-first summary, 2 to 3 sentences."
        },
        "sections": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "heading",
              "paragraphs"
            ],
            "properties": {
              "heading": {
                "type": "string"
              },
              "paragraphs": {
                "type": "array",
                "items": {
                  "type": "string"
                },
                "description": "Plain text. `backticks` for code, **bold** sparingly, «…» for verbatim fragments."
              },
              "pull_quote": {
                "type": "string",
                "description": "Optional. One verbatim passage, copied exactly."
              },
              "code": {
                "type": "object",
                "required": [
                  "label",
                  "language",
                  "source"
                ],
                "properties": {
                  "label": {
                    "type": "string"
                  },
                  "language": {
                    "type": "string"
                  },
                  "source": {
                    "type": "string"
                  }
                }
              }
            }
          }
        },
        "scenario_matrix": {
          "type": "object",
          "required": [
            "title",
            "rows"
          ],
          "properties": {
            "title": {
              "type": "string"
            },
            "rows": {
              "type": "array",
              "items": {
                "type": "object",
                "required": [
                  "scenario",
                  "tradeoff",
                  "mitigation",
                  "route"
                ],
                "properties": {
                  "scenario": {
                    "type": "string"
                  },
                  "tradeoff": {
                    "type": "string"
                  },
                  "mitigation": {
                    "type": "string"
                  },
                  "route": {
                    "type": "string"
                  }
                }
              }
            }
          }
        },
        "decision_tree": {
          "type": "object",
          "required": [
            "question",
            "branches"
          ],
          "properties": {
            "question": {
              "type": "string"
            },
            "branches": {
              "type": "array",
              "items": {
                "type": "object",
                "required": [
                  "condition",
                  "outcome",
                  "route"
                ],
                "properties": {
                  "condition": {
                    "type": "string"
                  },
                  "outcome": {
                    "type": "string"
                  },
                  "route": {
                    "type": "string"
                  }
                }
              }
            }
          }
        },
        "decisions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "3 to 5 short sidebar lines: the decisions this essay supports."
        }
      }
    }
  }
}
```

## 4. Repair message

When code rejects a draft, the conversation is rebuilt from the system and user messages plus the **best draft so far** (fewest violations). Then this tool result is sent, followed by the list of violations:

```python
"content": ("REJECTED by the checker. Call publish_essay again with the COMPLETE essay: "
                             "copy every section, paragraph, matrix row and branch unchanged EXCEPT the "
                             "exact items listed, and fix those without introducing new problems:\n- "
                             + "\n- ".join(b_viol[:60
```

Each violation names the field and what to fix. A misquote, for example, gets the source's exact text back (`capitalisation differs — the source reads «…»`).

## 5. What code checks before a draft is accepted (not sent to the model)

The prompt states the rules, and these checks are what enforce them. The model proposes; code decides.

- Every «fragment» and pull quote is an exact substring of the discussions (whitespace collapsed, typographic quotes folded).
- Any other quotation-marked span of three or more words is refused.
- Every number in prose appears in the discussions or the fact sheet. Figures above ten written in words, and multiples ("five times", "tripling"), are refused.
- A sentence that credits practitioners must contain a «verbatim» fragment.
- Banned: references to the inputs, counting people or reports, scores out of 10/100, internal telemetry vocabulary, vendor intent, source-platform names.
- Structure: 5–7 sections of 3+ paragraphs, a 5–8 row matrix, a 3–5 branch tree, at least one labelled code example, and the minimum length.

The full list is `BANNED`, `ATTRIBUTION` and `check()` in `generate_sample_blogs.py`. Each rule's comment records the draft that prompted it.

## 6. Planned posts (the Generate button)

The **Generate 3 more posts** button runs `generate_sample_blogs.py --plan 3`. The voice and grounding part of the system message (everything above `STRUCTURE`) is identical. The STRUCTURE section, the brief, the tool schema and the structure checks are built from one entry in `blog_formats.yaml`.

**What gets written is decided by code, not by the model.** The planner lists subjects with enough evidence (models, co-discussed model pairs, capabilities and jobs). It pairs each with a compatible format, prefers subjects no post covers yet, never repeats a (format, subject), and picks posts in distinct formats. Each pick must have its source threads on this machine.

| Format | Subject | Matrix | Tree | Code | Prices | Taken from headings like |
|---|---|---|---|---|---|---|
| Field report | model | - | - | 0-1 | yes | What happened / The evidence / What stayed green anyway / What I might have wrong |
| Head-to-head | pair | yes | - | 0-1 | yes | What do the release benchmarks say? / Does the cheaper claim hold? / What happens in a tool loop? |
| Cost teardown | model | yes | - | 0-1 | yes | The pricing change that matters here / The napkin math / Two breaking changes / Tokens per task is the hidden multiplier |
| Migration guide | pair | - | yes | 1-2 | yes | Before you start / Step 1: Pick your model / The confusing part / Breaking changes / When not to |
| Architecture pattern | topic | yes | - | 1-2 | - | Overview: isolate generation, distrust everything / Layer 1 / Layer 2 / Design decisions worth stealing |
| Release analysis | model | - | yes | 0-1 | yes | Grok 4.7 Shipped / The benchmark you cite is the argument you're making / Price cuts: practical migration steps |
| Evaluation critique | topic | - | - | 0-1 | - | My factual-recall tasks were scoring format, not facts / What the extra data did not buy / What I might have wrong |

### Example: the migration-guide format

STRUCTURE section sent in place of the original one:

```text
STRUCTURE (call publish_essay exactly once)
- FORMAT: Migration guide. A practical guide for a team moving traffic between these two models: what breaks, what to check before switching, how to run the switch safely, and when not to.
- 5 to 7 sections. Headings: practical headings, e.g. 'Before you switch', 'What breaks', 'Running the switch', 'When not to migrate'. Each section has 3 to 5 substantial paragraphs. Total length 1,400 to 2,500 words.
- At most one pull quote per section, verbatim as above.
- 1 to 2 code or configuration examples, attached to the section they belong to.
- One decision tree (3 to 5 branches), as the brief describes.
```

Brief (first block of the user message), for a pair of models:

```text
SUBJECT: Model A and Model B.
FORMAT: Migration guide. A practical guide for a team moving traffic between these two models: what breaks, what to check before switching, how to run the switch safely, and when not to.
DECISION TREE: the question is 'Should this workload move between Model A and Model B, and in which direction?'; each branch is a condition and the resulting choice.
```

The tool schema drops the blocks a format does not use. A migration guide is never asked for a scenario matrix, and an evaluation critique is never asked for a matrix or a tree.
