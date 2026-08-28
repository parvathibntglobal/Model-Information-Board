# Model-only harvest, end to end: is it worth adopting?

**One run. Reddit only. Eleven models. A temporary classification prompt.**
Written to inform one decision — whether a subject-only sweep should become a
retrieval shape we keep — and every number below carries the denominator it was
drawn from, because none of them is a rate.

*Engineer 1 · 2026-08-28*

---

## 0 · What this run was, and what it was not

**Was:** a `/getSearchPosts` sweep with a bare model name as the query. No topic
token, no signal term. Eleven named models, 17 surfaces, one afternoon. Then the
existing triage unchanged, then one classification pass with a prompt written for
this run and thrown away after.

**Was not:** a sample of anything. One platform, one day, one prompt. **No figure
here is a rate.** The comparison to the recency listing is the same platform on
the same day and is the only comparison in this document that controls for
anything. The comparison to GitHub controls for neither platform nor day, and is
marked where it appears.

**And it is not a claim that the classifier is right.** It read 358 documents once
under a prompt nobody has validated against a labelled set. What it produces is a
direction and a set of quotes a person can check.

## 1 · The chain, with a denominator at every step

```
STEP                                    COUNT      DENOMINATOR
requests issued                           103      119 planned; 2 surfaces
                                                   exhausted before 7 pages
candidates returned                     2,500      of up to 2,975 offered
                                                   (17 surfaces x 7 pages x 25)

  subject verified locally                 729      29.2% of 2,500 candidates
  topic hit                                926      37.0% of 2,500  — GATED NOTHING
  signal hit                               126       5.0% of 2,500  — GATED NOTHING

documents stored                           699      of 729 subject-verified;
                                                   30 already in the corpus
                                                   (ON CONFLICT DO NOTHING)
  carrying harvest_run_id                  699      699 of 699
  carrying text_ref                        699      699 of 699
  carrying author_id                       699      699 of 699
  retrieval_provenance                run_recorded  699 of 699

triage survivors                           358      51.2% of 699 readable
                                                   documents. UPPER BOUND: two
                                                   of six gates could not run

classified                                 358      100% of survivors, $0.2607
                                                   of a $1.00 cap, 0 errors
  judged a capability report               255      71.2% of 358
  assigned an existing key                 252      of 255 reports
  proposed a new key                         0      of 255 reports
  neither assigned nor proposed              3      of 255 reports
  quote verified by exact match            187      of 255 reports
```

**Quota cost: 103 requests of a read 1,000,000 monthly allowance — 0.01%.**
**Model cost: $0.2607.** The whole chain cost about 26 cents and five minutes of
wall clock against a 35-minute contract ceiling.

## 2 · The headline, and the number that qualifies it

**71.2% of triage survivors are capability reports under the wider reading.** On a
corpus retrieved by model name alone, with no topic or signal term in the query.

That is the finding this run exists to produce, and the qualifier is in §1: it is
71.2% **of 358 triage survivors**, which is 51.2% of 699 stored, which is 29.2% of
2,500 candidates. Composed:

```
255 capability reports from 2,500 candidates  =  10.2%
255 capability reports from 103 requests      =  2.5 reports per request
```

**2.5 capability reports per request is the number to compare against anything
else**, because it is the one with retrieval cost in the denominator.

## 3 · The signal group, which is the reason to take this seriously

Same platform, same day, three retrieval shapes:

```
                        recency listing    model-only query
                        (no query at all)  (bare alias)
candidates                      1,950              2,500
subject                         10.9%              29.2%
topic                            4.5%              37.0%
signal                           0.4%               5.0%
```

**Signal fires 12.5x more often under a model-name query than under a recency
listing on the same subreddits on the same day.** Topic 8x. That is the first
evidence this week that retrieval shape changes *what arrives* rather than only
how precisely it arrives.

**It does not overturn the signal finding.** 5.0% is still the smallest of the
three by a factor of six, and 126 of 2,500 candidates carrying a signal term
against 255 of 358 survivors being capability reports is the same gap in a new
place: **the sieve's signal vocabulary identifies a small fraction of the
capability reports a reader finds.** What changes is the size of the pool the
vocabulary is failing to catch.

*(The GitHub figures — 0.39% per-entry, 0.13% on the model-name arm — are a
different platform on a different day and are not compared here.)*

## 4 · The evidence, one verified quote per key

Eleven of the twelve keys were used. `extraction.faithfulness` was not.

| key | n | a verified quote |
|---|---|---|
| `code.generation` | 59 | *"Planing and also refactoring is not as good as with Sonnet"* — [1obwk0l](https://www.reddit.com/r/ClaudeAI/comments/1obwk0l/is_anthropic_forcing_us_to_use_haiku_45/) |
| `reasoning.multistep` | 50 | *"Even with detailed descriptions and reasoning, the output is just terrible."* — [1ow5lk0](https://www.reddit.com/r/ClaudeAI/comments/1ow5lk0/what_are_your_thoughts_on_haiku_45/) |
| `instruction.adherence` | 43 | *"It's great following instructions for atomic tasks."* — [1pew2p9](https://www.reddit.com/r/GithubCopilot/comments/1pew2p9/my_unpopular_opinion_claude_haiku_45_is_all_you/) |
| `over_refusal` | 39 | *"Haiku, in my experience, has the highest likelihood of rejecting documentations"* — [1o7vg95](https://www.reddit.com/r/claudexplorers/comments/1o7vg95/20251015_claude_haiku_45lcr_brief_thoughts_on/) |
| `ops.latency_ttft` | 23 | *"It is definitely faster, compared to Sonnet 4/4.5 - that's for sure"* — [1o9ctet](https://www.reddit.com/r/claude/comments/1o9ctet/how_do_you_feel_haiku_45_thus_far/) |
| `summarization.fidelity` | 17 | *"he is damn good at poring through multiple documents and finding misalignments"* — [1r1e6um](https://www.reddit.com/r/ClaudeAI/comments/1r1e6um/i_want_to_throw_some_love_toward_haiku_45/) |
| `code.editing_diff_fidelity` | 9 | *"I'm using it to refactor my portfolio website, and the inference is amazing"* — [1qwz2tw](https://www.reddit.com/r/ClaudeAI/comments/1qwz2tw/i_wish_opus_46_can_stay_this_powerful_forever/) |
| `context.effective_window` | 5 | *"Haiku 4.5 session limits feel significantly better, possibly 2x 2.5x Sonnet 4.5"* — [1o7wzuz](https://www.reddit.com/r/ClaudeAI/comments/1o7wzuz/just_have_a_session_this_morning_and_haiku_45/) |
| `tool_calling.long_chain_reliability` | 4 | *"forgets to use it's tools very very often"* — [1uo23dh](https://www.reddit.com/r/Claudeopus/comments/1uo23dh/opus_46_is_best_in_every_way/) |
| `tool_calling.schema_accuracy` | 2 | *"Garbled tool calls causing mass hallucination."* — [1tskdus](https://www.reddit.com/r/ClaudeCode/comments/1tskdus/psa_if_claude_has_been_acting_up_this_week_its_a/) |
| `format.structured_output` | 1 | — |
| `extraction.faithfulness` | **0** | — |

**Every assigned key is one of the twelve.** Nothing outside the contract
vocabulary was invented under the guise of assignment.

## 5 · Zero new capabilities were proposed, and that cuts two ways

**0 of 255 reports proposed a new key.** The prompt invited it explicitly, gave
the dotted-name convention, and asked for a definition and a motivating quote.

**Reading one: the twelve keys are adequate for this corpus.** Eleven of twelve
were used and every report fitted one. That is real evidence against the
open worry in `the-vocabulary-hypothesis.md` that a majority of claims would come
back `no-key-fits`.

**Reading two, and it cannot be dismissed: the prompt anchored.** It listed twelve
keys with definitions and then said "propose sparingly". A model shown a
comprehensive-looking list and told to be sparing will assign rather than propose,
and this run cannot distinguish that from adequacy.

**What separates them is one cheap experiment**: the same 358 documents with the
key list withheld, asking only "what capability is being reported, in your own
words", then comparing the free-text answers to the twelve. That is a second
temporary prompt, another ~26 cents, and it is the run I would do before anybody
concludes the vocabulary is complete.

**So: no proposal file, because there were no proposals.** `capability_candidate`
is still proposed rather than needed — see
`docs/proposals/for-engineer-2-capability-candidate.md` — and the honest state is
that the table has no rows to hold yet.

## 6 · The negatives, which are what decide the architecture question

**103 of 358 survivors (28.8%) were judged not to be capability reports.** What
model-only retrieval fetched that is not evidence:

```
r/SillyTavernAI   "announces a new model release and asks for user experiences,
                   but does not contain any reports of model behavior"
r/GithubCopilot   "the user is making a suggestion for a base model, not
                   reporting on its behavior"
r/AugmentCodeAI   "asking a question about potential credit usage, not reporting
                   on actual model behavior"
r/claudexplorers  "announces a new model and invites discussion"
r/ClaudeCode      "an announcement of a new model release"
```

**The negatives are dominated by launch-adjacent posts** — announcements,
"what are your thoughts", questions awaiting answers. That is a coherent failure
mode rather than noise, and it is the failure mode a model-name query would
produce: searching a model's name surfaces the launch thread first.

**This is the number the architecture question rests on, and it is favourable.**
28.8% of what survives triage is not evidence — which means model-only retrieval
is fetching evidence with a minority of chaff, not chaff with occasional
evidence. Compare the alternative reading of the same corpus at the retrieval
layer: 10.2% of raw candidates are capability reports, so **triage is doing most
of the discrimination and doing it cheaply**, without a model call.

## 7 · Quote verification: 34 fabrications, not 68

187 of 255 quotes verified by exact substring match. The 68 failures split
exactly in half:

```
present after unicode/whitespace normalisation    34    ENCODING
genuinely absent from the document                34    fabricated or paraphrased
present exactly (harness bug)                      0
```

**So the fabrication rate is 34 of 255 — 13.3% — not 26.7%**, and reporting the
raw failure count would have doubled it. The encoding half is smart quotes,
em-dashes and non-breaking spaces: the model returned `Augment's` where the
document has `Augment’s`.

**This matters beyond this harness.** `judge/extract/verify.py` performs no
Unicode normalisation — no `NFKC`, no quote folding — so the production verifier
has the same exposure, and `ExtractionRun.rejected` may be conflating the two
causes at a similar ratio. The runner's own docstring says a rejection is *"the
most interesting thing this stage produces"*, and it is much less interesting if
half of them are apostrophes.

**The fix is not to normalise.** Rule 1's guarantee is byte-for-byte existence in
the text the model was shown, and normalising the haystack weakens it. The free
change is to **report the two causes separately** — an encoding near-miss and a
fabrication want opposite responses, and today they are one counter. Raised for
`judge/` rather than taken.

## 8 · Three findings from this run that are not about classification

### 8.1 · Alias rendering: 148 against 0, and it is not about spacing

```
                          surfaces  candidates  subject   rate
registry HYPHENATED             5         875       20    2.3%
registry SPACED                 5         750      454   60.5%
run-local (display_name)        5         875      255   29.1%
```

`claude-opus-4.8` returned **0** subject hits; `opus 4.8` returned **148**.
`claude-sonnet-4.6` returned 1; `sonnet 4.6` returned 37.

**And the Qwen case inverts it, which is the actual finding.** For
`qwen/qwen3.8-27b`, of 175 candidate titles:

```
116  'qwen3.8-27b'    HYPHENATED — the dominant form
 42  'qwen3.8 27b'    spaced — what I queried, and exactly the 42 that verified
```

133 candidates failed subject verification on a hyphen, and they are capability
reports: *"Running Qwen3.8-27B dense fully on a single RTX 5060 Ti — ~45–47
tok/s"*, *"The difference between medium and xhigh reasoning effort for
Qwen3.8-27B"*.

**So "Reddit prefers spaces" is wrong.** The surface people write is **the
vendor's own marketing form**, and the convention differs by vendor: Anthropic
markets *Claude Opus 4.8* and people write `opus 4.8`; Qwen markets *Qwen3.8-27B*
and people copy it verbatim. Neither registry field is reliably correct —
`display_name` won for Claude, `canonical_id` won for Qwen.

**Which makes the fix smaller than the per-platform renderer I scoped earlier.**
`propose.py:mechanical_variants` already emits spaced, hyphenated and
concatenated forms. Seat all three and let the sieve match any — `sieve_any`
already reads a document against every spelling. Retrieval then issues both forms
at one extra request per surface, which here would have recovered 133 of 175 Qwen
candidates for 7 extra requests.

GitHub's hyphenation rule stays as it is and for its own reason: `github_alias_form`
hyphenates a trailing numeral because the *index* matches it against the issue
number. That is a fact about GitHub. This is a fact about vendors.

### 8.2 · Seating: 41 of 342, with 247 of 729 behind it

`model_alias` holds 105 rows over **41 of 342 models**, and 6 of these 11 were
outside it: Fable 5, Gemini 3.7 Flash, GPT-5.6 Luna, Sol, Sol Pro, Qwen3.8 27B.

**Those six contributed 247 of 729 subject hits — 34% of the run** — from
surfaces derived at runtime from `display_name` and never written to the
registry. Skipping them would have lost a third of the yield and reported eleven
models swept.

`propose.py` already derives correctly from `display_name`, including the
family+version form (`fable 5`) that scored 70–85%. **So this is a seating gap,
not a derivation gap**, and the fix is `registry propose-aliases` plus
`registry load-tracked-set` for these models. It is the first number behind the
alias-coverage question.

### 8.3 · Signal at 5.0% against 0.4% — see §3

## 9 · The decision this document is for

**On the evidence here, model-only retrieval is worth keeping as a shape.** The
case:

```
FOR    2.5 capability reports per request, at 0.01% of monthly quota
       71.2% of triage survivors are capability reports
       signal fires 12.5x more often than under a recency listing, same
         platform, same day
       negatives are a coherent, cheap-to-drop class (launch-adjacent posts)

AGAINST
       every figure is one run on one platform with one prompt
       the 71.2% rests on an unvalidated classifier, not a labelled set
       zero new-key proposals may be prompt anchoring rather than adequacy
       34 of 255 quotes were fabricated or paraphrased
```

**What I would not do on this evidence:** replace capability queries with
model-only queries, or wire a classification stage. The first is a coverage
decision that needs the same measurement on GitHub and blogs; the second is a
third model-calling stage and `CLAUDE.md` permits two.

**What I would do next, in order:**

1. **Seat the six unseated models' aliases, all three forms.** §8.1 and §8.2, one
   command each, and it is the cheapest thing on this page.
2. **Re-run the classification with the key list withheld.** §5. ~26 cents, and
   it is what separates "the vocabulary is adequate" from "the prompt anchored".
3. **Separate the two verification failure causes in `judge/`.** §7. Free, and it
   makes an existing counter mean one thing.
4. **The same sweep on GitHub**, so the comparison in §3 controls for platform.

## 10 · Where the artifacts are

```
scripts/model_only_sweep.py                  the sweep
scripts/classify_capability_reports.py       the temporary prompt
model_only_sweep.jsonl                       2,500 candidates with per-candidate
                                             subject/topic/signal
classification.jsonl                         358 verdicts with quote, key,
                                             permalink and verification status
docs/proposals/for-engineer-2-capability-candidate.md
                                             where a proposal WOULD be stored;
                                             no rows yet, because none were made
```

`harvest_run` carries 17 rows for this sweep with `query_key` naming the surface,
the sort and the page depth — so the population of every figure above is
recoverable from the database rather than from this document.
