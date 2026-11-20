# Field report spec

```
python -m judge.content_workspace media-spec field-report --model <id> [--weeks 4] [--start DATE] --out spec.json
CHROME=<chrome.exe> node tools/media/field-report/make_field_report.mjs spec.json <outdir>
```

The generator renders a 3-page carousel (1080×1350, one PNG per page plus a PDF) from one
JSON spec. `media-spec` writes the spec from the board, read-only, through the content
workspace's own week reader, so the figures are the ones the workspace's trajectory
suggestion shows (`judge/content_workspace/media_specs.py`, `field_report`).

Every field is required unless marked optional. A missing or wrong field stops the
render with the field's name; nothing is filled in.

| Field | What it is | Why |
|---|---|---|
| `title` | The model's name as readers know it, with no provider prefix | |
| `subtitle` | Line under the title | |
| `path` | The model page path, printed in the footer and on page III | Every figure points to its evidence |
| `release_date` | YYYY-MM-DD | Says "from release" only when `start` equals it |
| `start` | First day of week 1, YYYY-MM-DD | |
| `read_on` | The day the counts were read, YYYY-MM-DD | A figure carries its date (rule 7) |
| `weeks[]` | 1 to 4 complete weeks: `from`, `to` (YYYY-MM-DD), `people`, `posts`, `pos`, `neg` | `pos` and `neg` are POSTS with such a report; one post can have both |
| `proofs[]` | 0 to 2 cards: `side` (positive or negative), `week`, `platform` (display name), `date`, `text` | `text` is the board's stored paraphrase, never a user's words |
| `file_slug` | Optional; names the output files | |
| `source`, `topic` | Optional notes for people; not printed | |

**Checks on the numbers.** Every count is a whole number of at least 0, and no week has
more people than posts, or more positive or negative posts than posts.

**What it refuses, rather than squeezing onto the page:**
- more than 4 weeks;
- a week still running (`media-spec`);
- more than about 400 people in a week, past which one dot per person no longer fits;
- more posts than two rows of tallies hold;
- more than 2 proof cards;
- a platform with no display name (`media-spec`, `PLATFORM_NAMES`).

**Silence is said, not drawn.**
- A week with nobody: the dots give way to "nobody posted about it this week", and the
  tallies to "nothing to count for or against".
- No proof cards: page III says the board holds no restated report yet.

**Layout guard.** The render fails if anything leaves the page, touches the footer, or
overlaps the footnote.

**Example:** `examples/example.json` is SYNTHETIC (an invented model and invented card
text, for trying the generator). Specs made from the board are not committed: they can
carry restated reports.
