# Transcribing reels the Industry AI lane cannot read (#679 step 2)

**Status: PROPOSED** by anooj on 2026-11-26, for Parvathi's review. **Updated the same day after her review (#681):**

- **Her changes:** a transcript is cleared after 30 days whatever the post's label, and the order posts are taken in when more than the cap qualify is stated.
- **robots.txt:** always asked, with no switch.
- **What that leaves:** checking robots.txt shows it leaves only Reddit and Bluesky video. **So the step 2 code is held, and step 3 (text in pictures) comes next.** See "What robots.txt leaves" below.

Other points:

- Nothing here is in force until this PR merges.
- No code is written.
- This PR adds two PROPOSED entries to `CLAUDE.md`, written the way #558 recorded the evidence feed. Merging this PR is agreeing to them.

## The problem

**The lane reads words only.** A video post with a short caption has its content in what is said, which the lane cannot read.

**What happens today.** #676 counts these posts as **not readable** (drop_stage `unread`), apart from "filtered out", so the page doesn't call them irrelevant (rules 4, 6). They are still never read.

**The sample, 26 Nov 2026 (#679).**

- **Population:**
  - video posts in the 25 Nov observer dry-run pages, 563 distinct;
  - 90 of them have under 80 characters of the author's own words once links, @handles and #tags are removed (Instagram 41, X 35, Reddit 14, Bluesky 0);
  - the AI-term filter was not applied, so this is wider than the "not readable" bucket.
- **Sample:** 6 per platform. The first 90 seconds of audio were transcribed locally with whisper.cpp `base.en`.
- **Results:**

| | has speech | about AI | not about AI | can't tell |
|---|---:|---:|---:|---:|
| Instagram | 6 of 6 | 4 | 1 | 1 |
| Reddit | 4 of 6 | 0 | 2 | 4 |
| X | 4 of 6 | 2 | 1 | 3 |

**This is a sample of 18, not a rate.** It shows where the hidden content is:

- Instagram reels from watched accounts say it out loud.
- Reddit and X clips are mostly music, memes or off-topic.

## What step 2 does

In the scheduled Industry AI run (GitHub Actions, `ubuntu-latest`), after the posts are labelled:

1. **Pick the posts.** Take the posts labelled **not readable** in this run whose media kind is `video` and whose provider page gave a media link with audio:
   - Instagram `video_url`;
   - X's lowest-bitrate `video/mp4` variant;
   - Reddit's `reddit_video.hls_url` (its `fallback_url` has no sound);
   - Bluesky's `playlist`.
2. **Get the audio.** ffmpeg reads the **first 90 seconds of audio only** (`-t 90 -vn`, 16 kHz mono) into a temporary folder.
3. **Transcribe.** whisper.cpp writes the transcript on the runner.
4. **Delete.** The temporary folder is deleted in a `finally` block, whether the transcript worked, failed or timed out. When the job ends, GitHub discards the whole runner anyway.
5. **Store and count.** The transcript and its status are stored on the post. The AI-term and industry-term matching runs on caption + transcript, and the result is stored as a **flag only**.

### Shadow mode first (rule 8)

For the first week, the transcript changes **no** label. A post stays "not readable", and the flag records what reading the transcript would have decided.

After that week:

- **Hand-check** a sample of the flagged posts.
- **Promote, or not:** if the transcripts were read correctly, switching labels on is a one-line contract change (`transcribe.affects_labels: true`). That switch is reviewed like any other contract change.

## What is stored, and for how long

| what | where | how long |
|---|---|---|
| the audio | the runner's temporary folder | deleted right after transcription; never in the raw store, the database, Railway or an artifact |
| the video | nowhere | only the audio track is read, never saved |
| the media link | nowhere | used in memory during the run (Instagram's links expire anyway) |
| the transcript text | `iai_item`, beside the title and body | cleared after `retention.clear_text_after_days` **whatever the post's label**, `''` where there was text. That includes a "not readable" post whose caption is kept while `retention.unread` is `false`: a transcript is a person's spoken words, often longer and more personal than a caption (Parvathi, #681). 30 days is more than the shadow week needs. |
| the transcript status and model | `iai_item` | as long as the row: `ok`, `no_audio`, `no_speech`, `failed`, `over_cap`, `refused` (robots.txt), `not_tried` |

**Missing stays missing (rule 6).** NULL means "not tried", which is not "no speech". `''` means "cleared by retention", as with `media_text` in #680.

**Where it appears.**

- No page shows transcript text.
- AI Watch counts posts by transcript status, so "not tried" never reads as "nothing said" (rule 4).
- Anywhere a transcript is shown later, it is labelled as transcribed, never as the author's words.

## The two CLAUDE.md entries this PR proposes

### 1. A third fetch exception: a reel's audio

The stack rule is official APIs and public feeds only. The two recorded exceptions (benchmark pages, news link previews) fetch pages, and the link-preview one never downloads a picture. Fetching a video's audio track is new, so it is recorded with conditions that are not settings:

1. **Only media links the provider's own API response gave**, for posts the run itself labelled "not readable". No search, crawl or discovery.
2. **No cookies, logins, API keys, browser, `yt-dlp` or page fetch.** A plain request with the identifying User-Agent.
3. **Audio only, the first `transcribe.max_seconds`** (90). The video is never saved, and the audio is deleted in the same run (`finally`). The transcript is cleared after `retention.clear_text_after_days` even where the post's caption is kept.
4. **At most `transcribe.max_per_run` posts per run** (60, agreed). When more qualify, they are taken **in turn by platform, then by account within a platform, newest first**. This goes one level finer than `harvest.round_robin`'s by-platform turn, so one prolific watched account can't take the cap every run either. Posts over the cap are recorded as `over_cap`, never silently skipped, so the shadow week's `over_cap` count has a stated population (rule 7).
5. **`robots.txt` is always asked** (Parvathi, #681):
   - once a run per media host;
   - with the identifying User-Agent;
   - for every host a redirect leads to as well.

   There is no switch to turn it off, as with the benchmark and link-preview exceptions. A refusal is recorded as `refused`, and that platform's reels stay "not readable".
6. **`transcribe.enabled: false` turns it off as a whole.** It ships `false`, and is set `true` for the shadow week by a contract PR.

### What robots.txt leaves (checked 2026-11-26)

I fetched each media host's `robots.txt` with a generic client name, for the hosts the 25 Nov pages' media links point at:

| platform | video host | its rule for `*` | picture host | its rule for `*` |
|---|---|---|---|---|
| Instagram | `*.fna.fbcdn.net`, `*.cdninstagram.com` (22 hosts in the pages) | **`Disallow: /`**, under a notice that automated collection needs Instagram's written permission | the same CDN | **`Disallow: /`** |
| X | `video.twimg.com` | **`Disallow: /`** (only Googlebot and Bingbot allowed) | `pbs.twimg.com` | allowed (`Disallow:` empty) |
| Reddit | `v.redd.it` | allowed | `i.redd.it`, `preview.redd.it` | allowed |
| Bluesky | `video.bsky.app` | no robots.txt (404) | `cdn.bsky.app` | no robots.txt (404) |

**For step 2, this leaves Reddit and Bluesky video only.** Of the 90 short-caption videos in the 25 Nov pages, that's 14 from Reddit and 0 from Bluesky. In the sample, none of the 6 Reddit clips was about AI. Instagram's reels, the case step 2 was for (4 of 6 about AI), and X's videos would all be `refused`.

**So the step 2 code is held.** The two entries are still worth agreeing now, so the rules are settled if a host's robots.txt changes, or if the team decides Reddit and Bluesky alone are worth it.

**Step 3 (text in pictures, OCR) comes next instead.** Its hosts are allowed for X, Reddit and Bluesky; only Instagram's are refused. In the picture sample, 6 of the 9 AI images carried their message as text inside the image. Step 3 needs its own fetch exception for pictures, which comes in its own PR with the same conditions.

### About the 26 Nov samples

The samples in #679 downloaded Instagram and X video, and Instagram pictures, from these same hosts, **without asking robots.txt first**. I didn't check it before running them.

- It was a one-off, local hand-check: 18 clips and 28 images.
- Nothing was kept except the private notes and counts.
- No step of the pipeline does it.

**Any later sample asks robots.txt first, as the pipeline will.** The step 2 and step 3 sample scripts (`mib-media-speech`, `mib-media-images`, private) will skip a refusing host. (Terms research stays reference only, and blocks nothing; robots.txt is the stack rule, not terms research.)

### 2. Rule 2: whisper.cpp is a model, recorded, deciding nothing

**What it is.** Whisper is a neural speech-to-text model, and its decoder is a language model over audio.

**Why record it instead of arguing it's out of scope.** It's simpler to write it down than to argue it falls outside rule 2.

**What it does.** It writes down what is said, and nothing else:

- code matches the AI and industry terms in that text;
- in shadow mode, nothing is decided on it at all;
- after promotion, code applies the same rules it applies to a caption.

"A model may propose, it may never decide" holds.

**Its known failure, and what catches it.** On music or silence Whisper can write words nobody said ("thanks for watching" is the classic).

- `no_speech` is recorded when whisper.cpp marks the audio as silence or the transcript is empty.
- The shadow-week hand-check reads the flagged posts against their audio before any label depends on it.

**What it costs.**

- No API and no spend ledger: it runs on the runner's CPU.
- The model file is `ggml-base.en.bin`, pinned by SHA-256 and cached between runs.
- whisper.cpp is built from a pinned release tag.

## Volume and time: estimates, measured in the shadow week

- **Estimated volume:** about 40 reels a day, plus a few X and Reddit clips. That is about 340 new Instagram posts a day in the 25 Nov pages, 69% of them video, about 17% of those under 80 characters.
- **Estimated time:** a few seconds per 90-second clip on a runner, so about 10 minutes a run. These are estimates, not measurements.
- **What the shadow week reports, from the run itself:** transcribed, over the cap, failed, and minutes taken.
- **Headroom:** the cap keeps the run inside its 180-minute timeout.

## What it does NOT do

- **No pictures.** Step 3 (OCR) is separate, after this.
- **No model describing images or video.**
- **No transcript of a post that is not "not readable".** A post that reads fine on its words is never fetched.
- **No change to the 80-character threshold.** That waits for a week of iai-5 counts (#676).

## Order of work (changed 2026-11-26, after the robots.txt check)

1. **This PR.** If agreed, it merges and the two CLAUDE.md entries are in force.
2. **#680 (step 1):** merged, and migration `20261126T0900` applied 08:02Z.
3. **Step 3 next:** text in pictures (OCR), for X, Reddit and Bluesky. It comes as a proposal for its own fetch exception, then a code PR shipped `false`, then a shadow week.
4. **The step 2 code is held.** It is reopened if Instagram's or X's video host stops refusing, or if the team decides Reddit and Bluesky video alone are worth it. If it is built:
   - columns and migration;
   - the `transcribe:` block shipped `false`;
   - workflow steps for ffmpeg and whisper.cpp;
   - tests;
   - then the shadow week and a separate decision on `affects_labels`.
