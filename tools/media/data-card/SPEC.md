# Data card spec

```
python -m judge.content_workspace media-spec data-card --capability <slug> --text text.json --out spec.json
CHROME=<chrome.exe> node tools/media/data-card/make_data_card.mjs spec.json <outdir>
```

Every field is required, and none has a default (rule 12).
A missing or ill-typed field, or a total that disagrees with the rows, stops the
run with the field's name. A layout overflow also stops it, and nothing is
written.

| Field | Meaning | Rule it serves |
|---|---|---|
| `slug` | Output file name: `data-card-<slug>-p1.png` and so on | — |
| `topic` | Topic label, uppercased in each page's kicker | — |
| `filed_under` | The board label the reports were filed under, in prose ("from N reports the board filed under …") | 7: what was counted |
| `path` | Board page in the footer of every page | proof one click away |
| `window.from`, `window.to` | First and last post date counted (YYYY-MM-DD). The kicker reads "posts from 20 Oct to 19 Nov 2026"; `{window_days}` is derived from these two | 7: population and dates |
| `read_on` | When the figures were read; printed as "Read 19 Nov 2026" | 11: a count is a dated record |
| `population` | Plain-text record of the query (tables, filters, how people were counted). Not printed; kept for review | 7 |
| `headline` | The line under the big number, e.g. "people reported on …". It must describe `totals.people` | — |
| `sides.negative` / `sides.positive` | `stat` (page 1 label), `legend` (page 2 legend), `bar` (word after each bar's count). The board's polarity stays as filed; only the words are topic-specific | 3: counts, not a score |
| `totals.people` | Distinct authors across all models | 7: the denominator |
| `totals.negative`, `totals.positive` | Distinct authors with at least one report on that side | 3 |
| `totals.models` | Models named. Must equal `rows` + `rest.models` (checked) | — |
| `totals.entries`, `totals.no_author_entries` | Board entries counted, and how many had no author (not people). Checked: entries ≥ people + no_author | 7 |
| `rows[]` | Up to 8 models, most people first: `model`, `people`, `negative`, `positive` | 4: a model with no report has no row; a row with 0 people is refused |
| `rest` | The remaining models: `models`, `people_min` and `people_max` (people per model, printed "1 person each" or "1–3 people each"), and `negative`, `positive`, `neither`, each a SUM over those models of that model's people (so one person on two models counts twice) | 7 |
| `sources[]` | Distinct people per NAMED platform (`platform`, `people`). Together with the not-named row, at most 8 rows | 7 |
| `sources_not_named` | `{people, platforms}`: people who posted only on platforms the publication contract does not name in public (`withheld_from_public`), drawn as one "Not named" row. `0` and `0` when none. Named people + not-named people must be ≥ `totals.people` | publication contract: no per-platform number for a withheld platform |
| `page2_head`, `page3_head` | Headline lines. `{platforms_word}` becomes "Seven", from the number of sources | 11: counts in prose are computed |
| `page2_note` | Says that no bar is not "no limit". `{window_days}` is filled from the window | 4: silence is not praise |
| `not_a_measurement` | Ends the sentence "Not a measurement …", saying what the card is NOT | 3 |

**Checks that compare stated totals with the rows** (people are distinct, so a
sum of rows is an upper bound, not an equality):
- `models` equals rows + rest;
- `people` is no more than the sum the models allow, and no fewer than the
  largest row;
- each side total is no more than `people`, and no more than rows + rest;
- each source (and the not-named row) is no more than `people`, and together
  they are at least `people`.

**Zero reports** (`totals.people` 0, no rows, no rest): page 1 says "No reports
on <filed_under> in these N days", and page 2 says no model had a report.
Nothing is drawn as a bar of 0.

**A 0 printed beside a bar** ("0 held up") is a count: none of that model's
people took that side. A model with no reports is never a row.

**Bar scale:** 44 px per person, shrinking when the largest side passes 10, so
the longest bar stays at 440 px.

**Example:** `examples/example.json` is SYNTHETIC: invented model names over the
corrected structure of the approved usage-limits card (its withheld platforms
grouped as "Not named"). Specs made from the board are not committed.

## Builder

```
python -m judge.content_workspace media-spec data-card --capability <slug> --text text.json
    [--section capability] [--days 30] [--to YYYY-MM-DD] [--allow-running] [--out spec.json] [--force]
```

`judge/content_workspace/media_specs.py`, `data_card`.

**What it reads:** the board named by `DATABASE_URL`, in a read-only session.

**How it counts:** exactly as the public pages count:
- `judge.verdict.COUNTED` (no declined entry; only the sections
  `contract/verdict.yaml` counts) and `POST_DAY` (a post's UTC day).
- `judge.publication.sql_counted_document` for totals, and
  `sql_shown_document` for the per-platform page. That is how the withheld
  platforms become the not-named row.
- Grouping is by `section` + `slug`, the whole label (rule 10).
- People are distinct `author_id`s. Entries with no author are counted and
  reported, never treated as people.
- Rows run most people first; ties go by model name. Up to 8 rows, and the
  rest fold into `rest`.

**What a person writes:** every text field goes in the `--text` file
(`headline`, `sides`, `page2_head`, `page2_note`, `not_a_measurement`,
`path`; optionally `topic`, `filed_under`, `page3_head`). The builder has no
default text. `topic` defaults to the board's own name for the label.

**The window:** `--days` back from `--to` (default: yesterday, UTC). A window
that ends today or later is still running and is refused. `--allow-running`
exists only to reproduce a spec read on its own last day; it warns, and its
counts are a snapshot.

**It refuses** before writing anything:
- a running window;
- a label nothing is filed under (a shortened slug is not the label);
- a section public pages do not count;
- missing text keys;
- more named platforms than page 3 holds;
- an unknown platform key (`PLATFORM_NAMES`);
- an existing output file, unless given `--force`.

**The approved card was corrected by this builder (2026-11-19).** Rebuilt, every
figure matched (totals 51 / 44 / 6 / 19 / 68 / 0, the same 8 models and counts)
except two things the approved hand-made spec did wrong:
- the four models with 2 people now tie-break by name;
- Reddit 29, Bluesky 5 and X 4 on page 3 became "Not named: 38 people on 3
  platforms", as the publication contract requires.
