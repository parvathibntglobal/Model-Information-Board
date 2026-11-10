# Registry rows for catalogue models: evidence filed, no daily fetch

*anooj · 2026-11-09 · PROPOSAL. Nothing under `contract/` changes in this PR. The change it
proposes touches `contract/tables.sql` (a provenance value) and needs a second review.*

## The problem

**ElevenLabs v4 has evidence and no row to file it under.** v3's own searches collected 255 Reddit
and 4 dev.to documents with "eleven" and "v4" in their URL. v4 is in OpenRouter's catalogue
(`elevenlabs/eleven-v4`, output `speech`), but it has no `model_version` row. So its claims
were dropped before #612, and since #612 they would only be held. 0 board entries quote it, and
its name is on no page. (Read-only, shared database, 2026-11-09.)

**It is one of hundreds, and the cause is structural:**
- **The registry poll seats only what OpenRouter's main model list carries.** Of the 283 polled
  rows, none outputs speech. Every media model so far was seated by hand (ElevenLabs v3,
  `3e1c343`, 2026-09-15: "the poll will never carry").
- **`auto_track` admits only `polled` rows** (ours, `24c34f2`, 2026-10-06), so it can never pick
  up a media model either.
- **`seating_bar`** (3 held entries from 2 authors, Parvathi, `bba66c8`, 2026-11-06) decides when
  a *held* model is put to a person to seat. It is a lower bound, because an unseated model is
  never searched for, and it hides nothing that is seated. It is not what stopped v4.

## The measurement

`docs/measurements/catalogue-registry-rows-2026-11-09.py`, with its output beside it.
Read-only, run 2026-11-09 over the shared database.

- **Population:** every `model_catalog` row with no `model_version` row.
- **Kind:** read from OpenRouter's published `output_modalities`, never from the name.
- **Name used for a seat:** the catalogue name, with its "Provider: " prefix removed, lowercased.

| | count |
|---|---|
| catalogue rows | 766 |
| **with no registry row** | **501** |
| set apart, not separate models: `:free` listings (the model they are free of) | 26 |
| set apart: routers (`openrouter/auto`) | 1 |
| out of scope: embeddings, rerank | 66 |
| **in scope** (text 229, image 52, decisions 35, speech 34, transcription 30, video 28) | **408** |
| **the existing alias rules would seat** | **392** |
| set aside for a person: would resolve only at family level (the pending ruling) | 9 |
| set aside for a person: one word, no digit, possibly an ordinary word (rule 10) | 7 |
| refused: two in-scope names fold to one key ("Command R" / "Command R+") | 2 |
| refused: key already owned by another model | 0 |
| listed by OpenRouter since 2026-10-01 | 67 |
| held claims that would file at once | 49 |

The 49 held claims are GPT Image 2.6 Flare 21, GPT Image 2.6 Sunburst 21, FLUX 3 Image 6 and
GPT Image 2.5 Flare 1. ElevenLabs v4, v4 Turbo, Jev 1.14 and Grok Imagine Video 1.5 Lite are
all among the 392, each as a `snapshot` spelling (the name is the id's local part).

## What is proposed

**A registry row, not a tracked model** (anooj, 2026-11-09). There are two layers, and only the
first changes:

| | registry row (`model_version` + aliases) | tracked list (`tracked_models.yaml` / `auto_track`) |
|---|---|---|
| effect | a claim about the model, found in any thread we already read, is filed as a board entry | a daily fetch searches for the model; it is listed on the models page |
| extra cost | none: no searches, no extraction of its own | requests and extraction spend per model, every night |
| **this proposal** | **yes** | **no** |

1. **A new provenance value: `catalogued`.**
   - Not `polled`, because the poll did not bring it. Not `unpolled`, because that means
     hand-entered.
   - CLAUDE.md's fixtures section records what happened when a third kind of row was labelled
     with an existing word.
   - It needs the `model_version_provenance_ck` CHECK widened, with one migration, run by its
     owner straight after merge.
2. **A writer, `scripts/seat_catalogue_models.py`, with `--dry-run` / `--apply`.** It builds each
   row from the catalogue: canonical id, provider, the cleaned name, and spellings from the
   existing `query_variants`. Then it loads through the existing `load_seed` checks: spelling
   coverage, the collision check, and source coverage (FR-2, with the catalogue as the source
   and `last_seen_at` as the date). A name the checks refuse is listed with its reason, never
   guessed. **No prices go on the row:** price stays in `model_catalog`, where the catalogue
   page already reads it.
3. **Set aside for a person, not seated:**
   - names that would resolve only at family specificity, until the family-claims ruling;
   - single digitless words (rule 10: where it is unclear whether a name is a word, nothing
     links).

   They are listed in the run's output.
4. **Never tracked, by construction.** `auto_track`'s query requires `provenance = 'polled'`, so a
   `catalogued` row can never start a daily fetch. A test pins that. Promoting one to tracked
   stays a hand-written `tracked_models.yaml` entry, as now.
5. **Upgrades, never downgrades.** If the poll later brings a catalogued model, its row becomes
   `polled`. `polled` or `unpolled` never becomes `catalogued`, the same rule as
   `_refuse_provenance_downgrade`.
6. **Where it runs:** in the registry-poll workflow, after the catalogue is read, beside
   `auto_seat.py`. Its counts go in the same issue comment, so a new listing gets a row the
   day it appears.
7. **Catching up the backlog,** in the order agreed on #612 and #602:
   - `attribute_unresolved_entries.py --apply` files the held claims (49 today);
   - #613's re-triage, `--dry-run` first, re-reads documents dropped as naming no model before
     their row existed. That is where ElevenLabs v4's 255 posts get read.

## What it does not decide

- **Display.** Entries filed under an untracked model appear wherever the board lists entries.
  The models page lists only tracked models. That gap is already measured on #550 (56 untracked
  models holding 859 claims on 2026-11-09), and how to show them is a separate decision.
- **The 16 set aside.** Each is a person's call, under the family ruling or rule 10.
- **Tracking any of them.** Seating a row says the model exists. It does not say the board
  searches for it.

## Questions for the reviewer

1. `catalogued` as the provenance value, with the CHECK widened and one migration?
2. A writer in the registry-poll workflow, through `load_seed`'s existing checks, with the 16
   set aside?
3. `:free` listings and routers set apart, as above?
4. After merge: the held claims filed, then the re-triage, in the #602 order?

## Rule check

- **Rule 2:** no model call. The writer is code over the catalogue.
- **Rule 6:** a NULL in the catalogue stays NULL on the row; the kind is read, not guessed.
- **Rule 7:** every count states its population (the catalogue as polled, 2026-11-09).
- **Rule 10:** ordinary-word names and family-level names are not seated, and they are listed.
- **Rule 12:** a refused name is reported, never forced through.
- **`contract/`:** unchanged here. The CHECK change comes as its own PR, with a second review.
