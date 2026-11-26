# Reading the text in pictures the Industry AI lane cannot read (#679 step 3)

**Status: PROPOSED** by anooj on 2026-11-26, for Parvathi's review.

- Nothing here is in force until this PR merges.
- No code is written yet.
- This PR adds two PROPOSED entries to `CLAUDE.md`, shaped exactly like the reel entries #681 put in force: a fetch exception and a rule 2 record. Merging this PR is agreeing to them.

**Why step 3 comes before step 2's code.** #681's robots.txt check found that Instagram's CDN and X's video host refuse all automated clients. That leaves reel transcription with Reddit and Bluesky video only, so step 2's code is held. The picture hosts of X, Reddit and Bluesky all allow it (table below). Parvathi agreed on #681 that step 3 comes next, with its own exception in its own PR.

## The problem

A picture post with too few words to judge is **not readable** (#676). Its content is in the picture, which the lane cannot read.

**The sample, 26 Nov 2026 (#679).**

- **Population:** picture posts (image or gallery, no video) in the 25 Nov observer dry-run pages whose own words come to under 80 characters once links, @handles and #tags are removed. The AI-term filter was not applied.
  - Distinct picture posts: Bluesky 200, Instagram 112, Reddit 333, X 249.
  - Of those, under 80 characters: Bluesky 81, Instagram 13, Reddit 113, X 58.
- **Sample:** 7 per platform, the first image of each post, judged by Claude Code looking at the picture.
- **Result:** 9 of 28 about AI, 12 not, 7 can't tell.
  - **6 of the 9 AI pictures carried their message as text inside the image:** screenshots of posts or chats about AI tools, tutorial covers, a product's screen.
  - For the three platforms this step can fetch, that is **4 of 21** (Bluesky 2, X 2). Reddit's 2 AI pictures had no text to read.
  - These per-platform text counts come from the sample's own notes, read back by keyword, so treat them as a reading, not a measurement.

**This is a sample, not a rate.** It shows that reading the text in a picture would recover some posts a caption never could, and that it won't recover AI-looking art that says nothing.

**What robots.txt allows (checked 2026-11-26, #681):**

| platform | picture host | rule for `*` | short-caption picture posts, 25 Nov pages |
|---|---|---|---:|
| X | `pbs.twimg.com` | allowed | 58 |
| Reddit | `i.redd.it`, `preview.redd.it` | allowed | 113 |
| Bluesky | `cdn.bsky.app` | no robots.txt (404) | 81 |
| Instagram | `*.fbcdn.net`, `*.cdninstagram.com` | **`Disallow: /`** | 13 |

So the fetch reaches **252 of the 265** short-caption picture posts in those pages. Instagram's 13 stay "not readable", recorded as `refused`.

## What step 3 does

In the scheduled Industry AI run, after the posts are labelled:

1. **Pick the posts.** Take the posts labelled **not readable** in this run whose media kind is `image` or `gallery`, and whose provider page gave a picture link:
   - X: `media_url_https`;
   - Reddit: the post's `url` when `post_hint` is `image`, or a gallery's `media_metadata` source;
   - Bluesky: the embed's `fullsize`.
2. **Get the picture.** Download only the **first** picture of the post into a temporary folder, with a size limit (`ocr.max_bytes`).
3. **Read it.** Tesseract OCR reads the text on the runner. Words below `ocr.min_confidence` are dropped.
4. **Delete.** The folder is deleted in a `finally` block, whatever happened. GitHub discards the runner at the end of the job anyway.
5. **Store and count.** The text and its status are stored on the post. The AI-term and industry-term matching runs on caption + picture text, and the result is stored as a **flag only**.

### Shadow mode first (rule 8)

For the first week, the picture text changes **no** label. A post stays "not readable", and the flag records what reading the picture would have decided.

After that week:

- **Hand-check** a sample of the flagged posts against their pictures.
- **Promote, or not:** promotion is a one-line contract change (`ocr.affects_labels: true`), reviewed like any contract change. On promotion, the picture text joins `media_text` as a fourth kind (`picture_text`), so the same rules, flag and page line cover it.

### OCR's known failure, and why the confidence threshold

Tesseract reads clean screenshot text well. On photos, stylised art and memes it can produce stray letters. The lane's AI terms include short ones (`ai`), so stray "AI" letters in a photo could look like a match.

Two things stand between that and a label:

- **`ocr.min_confidence`:** Tesseract's own per-word confidence. Low-confidence words are not kept.
- **The shadow week's hand-check:** a person compares the flagged posts with their pictures before any label depends on picture text.

`no_text` is recorded when nothing passes the threshold. It is never read as "the picture is not about AI" (rule 6).

## What is stored, and for how long

| what | where | how long |
|---|---|---|
| the picture | the runner's temporary folder | deleted right after reading; never in the raw store, the database, Railway or an artifact |
| the picture link | nowhere | used in memory during the run |
| the picture text | `iai_item.ocr_text` in shadow mode | cleared after `retention.clear_text_after_days` **whatever the post's label**, `''` where there was text; the same rule #681 set for transcripts |
| the status | `iai_item.ocr_status` | as long as the row: `ok`, `no_text`, `failed`, `too_large`, `over_cap`, `refused` (robots.txt); NULL = not tried |

**Where it appears.**

- No page shows picture text in shadow mode.
- AI Watch counts posts by status, so "not tried" never reads as "no text" (rule 4).

## The two CLAUDE.md entries this PR proposes

### 1. A fourth fetch exception: a "not readable" post's picture

Its conditions mirror #681's reel entry. Where they differ, the reason is in brackets.

1. **Only picture links the provider's own API response gave**, for posts the run itself labelled "not readable". No search, crawl or discovery.
2. **No cookies, logins, API keys, browser or page fetch.** A plain request with the identifying User-Agent.
3. **The first picture of a post only, at most `ocr.max_bytes`.**
   - The picture goes to a temporary folder and is deleted in the same run (`finally`).
   - It never goes to the raw store, the database or an artifact.
   - Only the text read from it is stored, cleared after `retention.clear_text_after_days` even where the post's caption is kept.
4. **At most `ocr.max_per_run` posts a run** (proposed: 150, since reading a picture takes about a second where a reel takes many).
   - When more qualify, they are taken in turn by platform, then by account within a platform, newest first.
   - A post over the cap is recorded as `over_cap`.
5. **`robots.txt` is always asked**, once a run per picture host, with the identifying User-Agent, and for every host a redirect leads to as well. There is no switch to turn it off. A refusal is recorded as `refused`.
6. **`ocr.enabled: false` turns it off as a whole.** It ships `false`.

### 2. Rule 2: Tesseract is a model, recorded, deciding nothing

**What it is.** Tesseract (version 4 and later) reads characters with a neural network (LSTM).

**Why record it.** As with Whisper (#681), it's written down here instead of argued out of rule 2.

**What it does.** It turns the pixels of text into characters, and nothing else:

- code matches the AI and industry terms in that text;
- in the shadow week, nothing is decided on it at all.

**Its known failure.** Stray letters on photos and art. `ocr.min_confidence` and the hand-check are the guards (above).

**What it costs.**

- It runs on the runner's CPU from the Ubuntu package, with no API and no spend.
- The package version is pinned in the workflow.

## Volume and time: estimates, measured in the shadow week

- **Volume:** 252 short-caption picture posts on X, Reddit and Bluesky in the 25 Nov pages. Those pages came from dry runs, and how many days they cover differs by source, so this is not a daily figure.
- **Time:** about a second per picture to read, plus the download. With the cap of 150, that is a few minutes a run.
- **What the shadow week reports, from the run itself:** read, `no_text`, failed, over the cap, refused, and minutes taken.

## What it does NOT do

- **No model describing a picture.** "Made with AI" art with no text stays "not readable", and the definition question from #679 stays open.
- **No Instagram,** while its CDN refuses.
- **No more than the first picture of a gallery.** It can be raised by contract after the shadow week, if the counts say later pictures carry text.
- **No change to step 2:** reel transcription stays held (#681).

## Order of work

1. This PR. If agreed, it merges and the two entries are in force.
2. The code PR:
   - `iai_item.ocr_text` and `ocr_status` with a migration;
   - the `ocr:` contract block shipped `false`;
   - a workflow step installing a pinned `tesseract-ocr`;
   - tests.
3. A contract PR turns on `ocr.enabled` for the shadow week.
4. The counts and the hand-check are posted on #679, and a separate decision is made on `ocr.affects_labels`.
