# Two security keys, not one

*anooj · 2026-09-22 · a proposal for `contract/`. Nothing in `contract/` is
edited by it.*

**For: parvathi.** `contract/` gets two eyes, so this is the proposal half.
Evidence: `docs/measurements/round3-first-reading-2026-09-22.md` and
`docs/measurements/the-key-that-takes-anything-2026-09-22.md`.

---

## 0 · What triggered it

Round 3's gold labelled nine of 36 rows `no-key-fits`. **Four of the nine are
one missing key, and the extractor put all four in the same wrong place:**

```
row 15  "none of the 720 attack attempts succeeded …"          -> instruction.adherence
row 25  "… prompt injection and data exfiltration …"           -> instruction.adherence
row 27  "Claude Haiku 4.5 was the easiest to attack."          -> instruction.adherence
row 30  "Auto mode would have blocked 89% of those actions."   -> instruction.adherence
```

Unanimous, not four scattered guesses.

**And the extractor had already said so itself.** `capability_candidate` holds
`security.prompt_injection_resistance` proposed **twice, from two independent
documents** — `devto:4541618` and `hackernews:49317694` — and the second quotes
row 15 verbatim. It named the gap unprompted while being forced to file the
claim under `instruction.adherence`. All 160 candidates are still
`ruling: null`.

That is exactly the trigger `capabilities.yaml` writes for itself: *"A growing
unclassified cluster is the signal that engineers are discussing something we
do not track — and the trigger to add it."*

---

## 1 · The dispersal, measured

Shared staging DB, **2026-09-22**. Slugs matched on the board's `capability`
section; a slug is counted once per entry.

### Defensive — the model is the target

| slug | entries |
|---|---|
| `jailbreak-resistance` | 7 |
| `prompt-injection-resistance` | 4 |
| `adversarial-review` | 2 |
| `safety-evaluation` | 2 |
| `sandbagging` | 2 |
| `sabotage` | 1 |
| `prompt-injection-robustness` | 1 |
| `reasoning-trace-injection` | 1 |
| **total** | **20** |

**Filed under, today:**

```
11  instruction.adherence
 7  over_refusal
 2  reasoning.multistep
```

Three keys, and not one of them is about resisting an attack. This is the
`vision` dispersal shape: 33 entries across four keys, none of which was vision.

### Offensive — the model is the actor

| slug | entries |
|---|---|
| `cybersecurity` | 7 |
| `vulnerability-discovery` | 4 |
| `exploit-development` | 3 |
| `vulnerability-detection` | 2 |
| `cyber-capability` | 2 |
| `vulnerability-exploitation` | 2 |
| `smart-contract-exploitation` | 2 |
| `multi-host-red-team` | 1 |
| `long-horizon-cyber` | 1 |
| `autonomous-exploit-generation` | 1 |
| **total** | **25** |

**Filed under, today:**

```
13  code.generation           2  context.effective_window
 5  reasoning.multistep       2  instruction.adherence
 2  over_refusal              1  tool_calling.long_chain_reliability
```

Six keys.

---

## 2 · The diversity figures

Both clusters, and the gate they would have to clear
(`judge/curate/gate.py`: `n_eff >= 3.0`, `platform_count >= 2`, author cap):

| | entries | documents | authors | models | platforms |
|---|---|---|---|---|---|
| **defensive** | 20 | 10 | **8** | 10 | **3** |
| **offensive** | 25 | 11 | **10** | 12 | **2** |

Both clear the platform minimum and both have author counts well past three.
**Neither has ever had a key to accumulate under**, so neither has ever
produced a cell. That is the point: this is not evidence that the board would
publish tomorrow, it is evidence that the reason it cannot is a missing row in
a YAML file rather than missing evidence.

⚠ **The offensive cluster is on TWO platforms, not three.** It scrapes the
minimum. Worth saying because a single platform going quiet drops it below the
gate, and nothing would say why.

---

## 3 · `cybersecurity` is the too-wide key, already present

Its seven entries, with the ratified key each was forced into:

```
[neutral ] over_refusal           Astra reaches its Critical threshold for cybersecurity capability
[positive] code.generation        GLM 5.3 is getting 84% on CyberGym
[neutral ] instruction.adherence  Astra can … find previously unknown security flaws and develop …
[positive] code.generation        a whopping 54.5 score on Exploit Gym
[neutral ] over_refusal           it found and used two previously unknown zero-days
[positive] code.generation        the model can independently identify and develop working exploits
[positive] instruction.adherence  Astra will help with secure code review and patching
```

**One slug holding a capability threshold, two benchmark scores, autonomous
zero-day discovery, and secure code review and patching** — under three
different ratified keys. Finding a zero-day and reviewing a patch are not one
capability, and a page headed `cybersecurity` renders them as though they were.
This is `extraction.faithfulness` absorbing facial recognition, and
`swe-bench` absorbing nine benchmarks, in a third place.

**⚠ ONE CORRECTION TO THE BRIEF, AND IT MAKES THE POINT NARROWER AND TRUER.**
I said earlier that `cybersecurity` sits *across* the defensive and offensive
clusters. Reading its seven quotes, **it does not** — every one is offensive or
security-engineering work, and none is about resisting an attack. So it is not
evidence that the two clusters are already being merged. It is evidence of
something more directly useful: **that a single "security" label demonstrably
absorbs unlike things on this corpus, inside one cluster.** A key spanning both
clusters would be that failure one level larger, which is the argument for two
keys — but the argument is by analogy, not by an instance we have.

---

## 4 · The proposal

Two keys. `contract/capabilities.yaml`:

```yaml
  - key: security.attack_resistance
    failure_mode: silent
    description: >
      Holding its instructions when the INPUT is hostile — indirect prompt
      injection from a fetched page or a read file, a jailbreak, a
      persona-override. The model is the target, not the actor. Silent because
      a successful injection produces a confident, well-formed, wrong action:
      you find out from the consequence, not from an error.
    sounds_like:
      - "prompt injection"
      - "jailbreak"
      - "easiest to attack"
      - "ignored its system prompt"
      - "exfiltrated"

  - key: security.offensive_capability
    failure_mode: loud
    description: >
      Finding vulnerabilities, writing working exploits, and security
      engineering work the model PERFORMS — the model is the actor. Loud
      because the claim is checkable: an exploit either runs or it does not,
      and these reports carry benchmark names and scores far more often than
      most. Record the benchmark in the metric section, never here.
    sounds_like:
      - "found a zero-day"
      - "working exploit"
      - "CTF"
      - "vulnerability discovery"
      - "red team"
```

**Why `failure_mode` differs, and it is the field that matters most.**
`capabilities.yaml` says the failure mode "matters MORE than how difficult the
task is. It is why the advisor will happily move a strict-JSON role to a cheap
model and refuse on an equally simple summariser. Not difficulty — whether you
would find out."

- **Resistance is `silent`.** An injection that works looks like the model doing
  what it was asked. Nobody files a bug. So positive consensus is required and
  "nobody complained" is not evidence — rule 4's whole point, and the reason
  row 15's *"none of the 720 attack attempts succeeded"* is a **finding** rather
  than an absence.
- **Offensive is `loud`.** The exploit runs or it does not.

Putting both under one key would force one failure mode onto both, and whichever
was chosen would be wrong for half the evidence. **That is the strongest
argument for two keys and it is a property of the schema rather than a
judgement about taxonomy.**

### What else has to land in the same PR, or the keys are a no-op

A key added to `capabilities.yaml` alone is not an addition. Four files:

| file | what | if omitted |
|---|---|---|
| `contract/capabilities.yaml` | the two keys | — |
| `contract/conditions.yaml` | `dominant_dimension` for each | `bucket_for` raises `KeyError`, every claim lands in `cell_refusals` |
| `contract/queries.yaml` | ≥1 query each, **a negative for each**, **a positive for the silent one** | `test_queries_contract.py` fails; and harvest is query-driven, so the cells stay empty forever |
| `judge/vet/weight.py` | half-life membership | falls through to `HALF_LIFE_DAYS_SLOW` (180d) — see below |

**Proposed `dominant_dimension`** — `context_size` for both, matching every
capability that is not tool-count or schema-shaped. I am not confident about
this one and it is the least evidenced thing in the proposal: an injection's
difficulty plausibly depends on tool count more than context length, and I have
no measurement either way. Rule 8 says the unmeasured version ships as the
coarser choice, and `context_size` is what eleven of twelve already use.

**Proposed half-life** — `security.attack_resistance` into `_MEDIUM_DECAY`
(120d), because a provider hardening a model changes the answer within a
release cycle; `security.offensive_capability` left at SLOW (180d), because a
model that found a zero-day still found it. Both are judgements with no
measurement behind them and both are cheap to change.

---

## 5 · The spelling question, which is yours and not code's

```
prompt-injection-resistance   4 entries
prompt-injection-robustness   1 entry
```

**One thing, two words, and `normalise_slug` must NOT fold them.** It folds
separators and case and nothing else, and its docstring is explicit about why:

> `tool-calling` is NOT folded into `function-calling` here, however obvious
> that looks: a synonym table in code is a judgement about meaning, and the
> moment it is wrong it silently merges two genuinely different sections. That
> call belongs to a person, through `ruling`.

`resistance` → `robustness` is a synonym, not punctuation. `spelling_key` would
correctly leave them alone; folding them in code is the day CLAUDE.md rule 10
gets read as licence for a synonym table, which it says explicitly it is not.

**So it is a `ruling`**, and the mechanism already exists:
`judge/store/board_entries.py` takes `adopted | declined | merged` with a
`ruling_target`, grouped by `(section, slug)` — *"merging 'tool-calling' into
'function-calling' is one decision about a word, not nine about nine quotes."*
A ruling here is consolidation and not publication; both entries are already on
the board.

**My reading, for you to overrule:** `merged`, target `prompt-injection-resistance`
— 4 entries against 1, and "resistance" is the term the two independent
`capability_candidate` proposals both chose. But it is one word against
another and I have no evidence beyond the count.

**And the same question is open on the offensive side, where I have no
recommendation at all:** `vulnerability-discovery` (4), `vulnerability-detection`
(2) and `vulnerability-exploitation` (2) may be three things or two or one.
Discovery and detection look like one; exploitation looks like a different
step. That is three rulings and I would rather you took them than guessed.

---

## 6 · What I am asking for

1. **The two keys** — and specifically the `silent` / `loud` split, which is
   the part that cannot be deferred, because it decides what the advisor does
   with the evidence.
2. **The `dominant_dimension` call** (§4), which is my weakest claim.
3. **The `resistance` / `robustness` ruling** (§5), and the three on the
   offensive side.
4. **Whether this is one PR or two.** The defensive key is the one round 3
   produced evidence for; the offensive key is corpus evidence only, and has
   no golden-set support. A reasonable answer is to take the defensive key now
   and hold the offensive one until it has a labelled row behind it.

Nothing here is measured against a re-run: no extraction has happened under
`e5.5`, so whether the extractor would now *use* `security.attack_resistance`
on rows 15, 25, 27 and 30 is unknown. Adding a key backfills from the immutable
raw store, which `capabilities.yaml` notes costs nothing — but it is a re-run,
and it is the thing that would confirm this rather than the thing that assumes
it.
