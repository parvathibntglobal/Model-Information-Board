# Evidence board spec

```
python -m judge.content_workspace media-spec evidence-board --model <canonical id> --out spec.json
CHROME=<chrome.exe> node tools/media/evidence-board/make_evidence_board.mjs spec.json <outdir>
```

Every field is required, and none has a default (rule 12). A missing or ill-typed field, or a figure that disagrees with
another, stops the run with the field's name. A layout overflow or two
overlapping boxes also stop it, and nothing is written.

| Field | Meaning | Rule it serves |
|---|---|---|
| `slug` | Output file name: `evidence-board-<slug>-p1.png` and so on | — |
| `model` | Model name on the case card | — |
| `path` | Model page in the footer of every page | proof one click away |
| `read_on` | When the figures were read; printed on page 3 | 11 |
| `population` | Plain-text record of the query. Not printed; kept for review | 7 |
| `kicker` | Page 1 kicker, the case in a few words | — |
| `card_caption` | Line under the model name, saying what the price table is and where it came from | 7 |
| `prices[]` | Registry price changes, oldest first: `date`, `input_from`, `input_to`, `output_from`, `output_to` (per 1M tokens). Each change must start where the previous one ended (checked). Up to 5; `[]` is allowed and prints no table | 6: a missing price is never 0 |
| `people.all` | Distinct authors of the model's board entries | 7: the denominator |
| `people.for`, `people.against`, `people.neither` | Distinct authors with a positive, negative or neutral entry. Each is no more than `all`, and together at least `all` (a person can sit in two rows). Up to 40 each, one pin per person | 3, 4: an empty row prints "no one" |
| `people.entries`, `people.no_author_entries` | Entries, and how many had no author (not people). Checked: entries ≥ all + no_author | 7 |
| `first_post`, `last_post` | Date range of the posts behind the entries; printed beside the people count | 7 |
| `note` | The sticky note (a string), or `null` for none. It must be stated either way | 4: say the silence |
| `cards_head` | Page 2 headline. The kicker ("Four of the reports, as filed") is derived from the number of cards | 11 |
| `cards[]` | 1 to 6 report cards: `side` ("for" or "against"), `what` (the capability as filed), `source` (platform), `date`, `text` (the board's stored paraphrase, never a quote; up to 160 characters). Each date must fall in first_post..last_post. A side with a card must have people | Quote rule: restated, never verbatim |
| `page3_head` | Page 3 headline lines | — |
| `extra_stats` | Exactly 2 cells for page 3: `value`, `label`, `counts`. `counts` is `"price_changes"` (value must equal the number of price rows), `"people_since"` (with `since`; 0 requires `last_post` < `since`, more than 0 requires `last_post` ≥ `since`), or `"other"` (not checked) | 11: counts in prose agree with the data |

**Not checked:** whether a card's paraphrase is faithful to its post. The
paraphrases are the evidence feed's stored rows, and per-item human approval of
those (#558) applies before any card is published.

**Long source names (fixed 2026-11-20, #641 review).** Page 2's two columns are
fixed halves (`minmax(0, 1fr)`), and a card's source line wraps. Before this, the
columns sized to their content and the source line did not wrap, so a card whose
source is a long name ("Hacker News", "Hugging Face") pushed the other column past
the page edge, and the layout guard refused the render. A long source line now
breaks onto a second line inside its card ("… · restated by the" / "board").
Re-checked with `compare_pages.py`: both approved evidence boards (Kimi K2.5 and
MiniMax M2.7) are pixel-identical before and after, because none of their sources
needed to wrap. Only a board with a long source name looks different, and before
the fix such a board could not be rendered at all.

**Example:** `examples/example.json` is SYNTHETIC: an invented model and
invented card text over the approved board's structure. Specs made from the
board are not committed: their cards are restated reports.

## Builder

```
python -m judge.content_workspace media-spec evidence-board --model <canonical id>
    [--cards 6] [--text text.json] [--out spec.json] [--force]
```

`judge/content_workspace/media_specs.py`, `evidence_board`.

**What it reads:** the board named by `DATABASE_URL`, in a read-only session.

**How it counts:** as the public pages count (`judge.verdict.COUNTED` +
`POST_DAY`, `judge.publication.sql_counted_document`), over all time.
- People for, against and with no side are distinct `author_id`s by entry
  polarity.
- `first_post` and `last_post` come from the counted posts.

**Prices:** the registry's `model_event` rows of type `price-change`, oldest
first, rounded to 6 decimals (3.3249999999999997 becomes 3.325). Every change
must start where the one before it ended, or the builder refuses: a change is
missing.

**Derived, not written:**
- the note ("nobody has reported on it since the 5 Nov cut", only when 0
  people posted since the last change);
- the page 3 headline;
- both extra stats;
- the kicker ("a price that kept moving", or "kept falling" / "kept
  rising" / "a price cut").

`--text` may override `kicker`, `note`, `cards_head` and `page3_head`.

**Cards** come from stored `feed_paraphrase` rows only, under the evidence
feed's terms:
- A held source (`publication.feed_hides`) and arXiv (its acknowledgement does
  not fit on a card) are never carded.
- A paraphrase over 160 characters is skipped.
- The stamp shows the WHOLE board label (rule 10: "quantization quality", not
  "quantization").
- Automatic choice keeps a card only when its label appears in its text (a
  word of 4+ letters, or its first five letters; a heuristic, said as one).
  Cards go newest first, alternating for and against.
- A short side gives its room to the other, and the count drops rather than
  padding. Why is written into `population`.
- `--text` `card_documents` pins a person's choice by document id, in order.

**It refuses** before writing anything:
- an unknown model;
- no price change, more than 5, or a broken price chain;
- more than 40 people in a pin row;
- `--cards` outside 1–6;
- an unknown `--text` key;
- a pinned document that cannot be carded;
- no cardable paraphrase;
- an unknown platform key;
- an existing output file, unless given `--force`.

**The approved board was corrected by this builder (2026-11-19, cards
pinned).** Prices, cards, note, stats and the cards' dates all matched. Three
differences, each the approved hand-made spec's error:
- **People:** 16 (8 for, 6 against, 3 no side), 21 entries, 0 without an
  author, last post 13 Sep. The approved board said 19 (7 no side), 36, 2 and
  21 Oct. It counted the `metric` section, which public pages do not: 15
  metric entries from 6 people, including both authorless entries and the
  21 Oct arXiv post.
- **Card 3's label:** "code review" instead of "coding agent". Both are the
  board's labels for that document; the builder takes the one that appears in
  the text.
- **Card 4's label:** "quantization quality" instead of "quantization".
