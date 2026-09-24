# e5.5 runs, 2026-09-23 and 2026-09-24: terminal logs and per-run figures

Eight `scripts/fetch_model.py` runs against the shared staging database, the
first under `pipeline_version` e5.5. Three were announced on #427, five on
#432. All ran on one machine (host-a).

**Why these are committed.** The raw logs live in `var/runs/`, which is
gitignored, so until now they existed on one machine only.

## The committed form, and what was taken out

Each `.log` here is the run's full stdout and stderr, captured with
`set -o pipefail` and followed by the recorded `PIPESTATUS`, with **one class of
line collapsed**: the `raw store: … missing with no tombstone` warning. It is
about 2,840 lines and about 620 KB per run, about 92% of each log, one line
per thread payload stored on another machine (#316, #321). The first
occurrence is kept, with a count line in its place:

```
[committed form: 2843 'raw store: ... missing with no tombstone' line(s) collapsed; full log in var/runs/<name> on host-a. First:]
```

Everything else is kept: stage lines, per-thread lines (where retries,
ceiling stops and 502s appear), the closing box and `PIPESTATUS`. The eight
come to 696 KB, against about 5.6 MB raw. The full logs remain in `var/runs/`
on host-a.

`batch-2026-09-24-figures.jsonl` is the batch driver's before and after
snapshot of the shared database for each of 2026-09-24's runs. Run 2's
**after** snapshot is empty: the database dropped the connection at the moment
it was taken (below).

## Conditions

```
extractor        deepseek/deepseek-v4-flash via OpenRouter
2026-09-23       main 78e7a1d; FETCH_MAX_THREADS unset (default 25), --fetch-cap 75
2026-09-24       main a9f7ff5 (#430 in); FETCH_MAX_THREADS=100, --fetch-cap 75
                 EXTRACTION_DAILY_BUDGET_USD=2.60 for that process only (see #381)
env              loaded explicitly from .env by the launcher; fetch_model does not load it
other writers    none, on any day's window (spend_ledger + fetch_log)
```

`--fetch-cap` bounds only GitHub issue fetches. `FETCH_MAX_THREADS` is the cap
on how many threads E5 selects. 2026-09-23's runs were capped at 25 by that
default, not by the size of the pool.

## Per run

Claims, board entries, cells and candidates are **deltas in the shared table**
across each run, from the driver's snapshots. They are not the run summary's
"stored" figure, which counts upserts (see caveats).

| run | model | end record | threads read | claims | board | cells | NULL key | candidates proposed (stored) | ceiling | 502 / 504, first attempt |
|---|---|---|---|---|---|---|---|---|---|---|
| 09-23 · 1 | Claude Opus 5 | RUN OK `(0)` | 24 of 24 | | | | | | | 0 / 0 |
| 09-23 · 2 | GPT-5.6 Sol | RUN OK `(0)` | 25 of 25 | | | | | | | 0 / 0 |
| 09-23 · 3 | DeepSeek V4 Pro | RUN ERROR `(1)`: E5, peer closed connection | 13 of 23 | | | | | | | 0 / 0 |
| 09-23 total | | | 62 | e5.5 claims 32 | | 0 | **32 / 32** | +41 in table | | |
| 09-24 · 1 | Claude Sonnet 5 | RUN ERROR `(1 0)`: arXiv arm only | 97 of 99 | +100 | +129 | 0 | **100 / 100** | 21 (12) | 1 | 0 / 5 |
| 09-24 · 2 | Claude Opus 4.8 | E5 error `(1 0)`: shared DB dropped the connection at 06:17:13Z | 71 of 99 | +42 | +87 | 0 | **42 / 42** | lost: E5b never ran | 2 | 5 / 3 |
| 09-24 · 3 | Claude Sonnet 4.6 | RUN OK `(0 0)` | 95 of 99 | +84 | +132 | 0 | **84 / 84** | 14 (12) | 1 | 6 / 1 |
| 09-24 · 4 | Gemini 2.5 Flash | RUN OK `(0 0)`, no stage errored | 98 of 98 | +50 | +90 | **2** | **48 / 50** | 35 (29) | 0 | 4 / 1 |
| 09-24 · 5 | GPT-4.1 | RUN ERROR `(1 0)`: arXiv arm only | 97 of 99 | +49 | +79 | **3** (1 new) | **48 / 49** | 25 (20) | 0 | 0 / 4 |
| **09-24 total** | | | 458 | **+325** | **+517** | 3 e5.5 cells | **354 / 357 e5.5** | 95 proposed, +73 in table | 4 | 15 / 14 |

2026-09-23's per-run claim and board deltas were not snapshotted per run;
their totals come from #427's baseline and closing comment.

### Retry outcomes, 2026-09-24

```
                first-attempt   recovered   unread
run 1                 5             3          2      all 504 idle timeout
run 2                 8             4          4      5 NextBit 502, 3 x 504
run 3                 7             3          4      6 NextBit 502, 1 x 504
run 4                 5             5          0      4 NextBit 502, 1 x 504
run 5                 4             2          2      all 504
```

NextBit's `did not return a valid tool call for the requested tool_choice`
appeared **only between 05:52Z and 08:23Z**, on 15 first attempts across runs
2-4, and never in runs 1 or 5.

It is **mostly, not only, long threads**:
- Over runs 1-3, inside the window, 9 of 17 threads of 8,000 characters or
  more hit it, against 2 of 96 shorter ones. Outside the window, 0 of 159
  threads did (study on #397).
- Run 4 then hit it on threads of 20,846, 14,393, **6,758 and 2,940**
  characters, so two of its four were short, and all four recovered on retry.

Which upstream served a retry is **not recorded by this client**. #435 adds
it, merged after this batch started, so these runs do not carry it.

### Cost, three ways, and none of them is the bill

The closing box prices tokens at the Gemini default constant. The DeepSeek
constant is closer. What OpenRouter actually billed depends on which of about
15 endpoints served each call, and on caching (#381).

```
                box ($, Gemini constant)   DeepSeek constant
run 1               0.1097                     0.2340
run 3               0.1185                     0.2528
run 4               0.1127                     0.2407
run 5               0.1050                     0.2244
key usage_daily for 2026-09-24, all calls on this key:   $0.4426
```

## Caveats a reader of these logs needs

- **"N stored" in each run's E5 line is not rows.** It counts upserts, and
  e5.5's empty capability key makes same-span claims collide: 154 against
  +100, 166 against +84, 89 against +50. See #444. Use the table deltas above.
- **Selection matched some threads through a prefix.** `gemini25flash` matches
  inside `gemini25flashlite`: 20 of run 4's 98 threads were about other
  models, and so were about half of run 5's early threads. Attribution stayed
  clean; the resolver filed those claims under Flash-Lite. See #441.
- **The three non-NULL keys under e5.5:** two are forced fits (speech-to-text
  filed as `extraction.faithfulness`, backend errors as `ops.latency_ttft`) and
  one is plausible (GPT-5-mini's task-following, filed as
  `instruction.adherence`). Every e5.5 cell is built on one of these three.
  See #443.
- **Run 2 is incomplete.** Its 28 unreached and 4 unread threads were never
  recorded as read, so a re-run of Opus 4.8 recovers them.
- **Ledger rows over these windows are about 4-5 times the billed spend**
  (#381), and about 30% of this machine's rows never reached the shared table
  (#393).

## Machine names are pseudonyms

`host-a`, `host-b` and `host-c` stand in for the three machine names that wrote
to staging in these windows. They are stable across every snapshot and log
here, which is all the figures need: `other_machines_since: []` means no other
host wrote. The mapping is kept off the repository.
