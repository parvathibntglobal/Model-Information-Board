# The evidence feed's upkeep agent

**Proposed 2026-10-27 by anooj. Agreed in discussion before it was built; the
`contract/` part (`evidence_feed.yaml` `revision` and `schedule`) and the
migration need a second reviewer.**

## What it does

| | when | what | approval | cap |
|---|---|---|---|---|
| Feed | nightly, after "Scheduled fetches" finishes | embeds and paraphrases for the reports fetched that night | none (as today: checked in code, source one click away) | `schedule.nightly_feed_usd`, $1 |
| Summary | weekly, Monday 07:00 UTC | a first draft for a model with none; a **point-level revision** of an approved one | a person, in Admin, every time | `schedule.weekly_summary_usd`, $1 |

`.github/workflows/evidence-feed.yml` runs both, behind `SCHEDULER_ENABLED`
like every other scheduled job.

## Revise, never rewrite

Agreed with anooj: the summary page should improve slowly, not churn. "An edit
should be done only if a point becomes more evident and relevant that is worth
adding... it doesn't mean to rewrite the whole 2 para." And "keep a point until
newer evidence replaces or contradicts it."

So once a model has an approved summary, the schedule never redrafts it
(`summary.models_due` skips it). Once a week, if paraphrased reports were posted
after the summary's newest, `judge/feed/revise.py`:

1. shows the model the approved summary **sentence by sentence** (`P2.3`) and
   **only the new reports** (`N1`...);
2. asks it to list `uncovered` themes - raised by the new reports, stated by no
   sentence - and then propose at most `revision.max_changes` (2) edits:
   `replace` one sentence, `add` a point after one, or `new_paragraph`;
3. **applies the edits in code.** Every sentence not edited is the approved
   text byte for byte - by construction, not by a check;
4. checks every changed paragraph as a draft is checked (numbers only from what
   it cites, no copied wording, no count of people), keeps the page inside the
   same word and paragraph limits, and requires every edit to cite a new report;
5. stores it `pending` with `changes` - before, after, reports, reason - which
   Admin shows side by side. Approving a revision of a summary that is no
   longer live is refused.

"No change" is a normal, stored answer. It is refused only when it contradicts
the model's own `uncovered` list: a theme it says no sentence covers, raised by
more than one new report. That is a consistency check on the model's answer,
not code judging content (rule 2).

## Nothing is paid for twice

Parvathi's #558 condition: no schedule until a refusal is remembered.

- `feed_paraphrase_refusal`: a paraphrase refused on every attempt, for these
  excerpts and this prompt. Asked again only when either changes.
- `feed_summary_attempt`: every draft and revision attempt - stored, refused or
  no change - with the newest report it considered. Not asked again until a
  newer report arrives and `revision.every_days` (7, with half a day of slack
  for cron drift) has passed.
- A call the cap or a dead key stopped is **not** remembered: it was never a
  verdict on the reports.

## Measured before proposing (local copy of the feed, 2026-10-27)

All against `mib_feed_local` on :5433, deepseek/deepseek-v4-flash, one call each:

| model | new reports | outcome | cost |
|---|---|---|---|
| ElevenLabs v3, Claude Haiku 5.5, GPT-6 Astra | 1, 1, 2 | no change, each with a specific reason | $0.0015 for the three |
| GPT-5.6 Sol, cut moved back 14 days | 47 | no change - correctly: the summary was written from those reports | $0.0021 |
| GPT-6 Astra, summary trimmed to its first paragraph, before `uncovered` | 56 | **no change, wrongly** - claimed cost and speed were covered | $0.0020 |
| the same, with `uncovered` | 56 | one point added to paragraph 1, citing 2 new reports, first attempt | $0.0008 |

The fourth row is why `uncovered` exists.

## Before it runs on the shared DB

1. Review and merge (contract change: two eyes).
2. **Migration `20261027T1200_feed_agent.sql`**: run on the shared DB by the
   person who merges, immediately after merge, and announced the same day. The
   workflow fails loudly until it has run.
3. The workflow needs no new secret: `STAGING_DATABASE_URL`,
   `OPENROUTER_API_KEY`, `USER_AGENT`, `SCHEDULER_ENABLED` already exist.
