# Publishing blog posts that use Reddit and X: a re-review proposal

Proposed 2026-10-13 for decision by anooj, a second reviewer, and the MD. The MD
is named because `reddit-via-rapidapi` was escalated to the MD on 2026-08-18.
This is decision support. Nothing in it blocks a build.

## The decision being asked for

May approved blog posts go public with Reddit and X content shown **only as the
platforms' official embeds**, and quotes only from other platforms?

Two recorded rules stand in the way today, and both are ours to change:

- **`reddit-via-rapidapi` and `x-via-rapidapi-scraper`** (`contract/sources.yaml`)
  rest on `basis: internal-development-only`, and say "RE-REVIEW REQUIRED BEFORE:
  any external publication".
- **"WHAT COUNTS AS PUBLICATION"** (ruled 2026-09-08) defines publication as "a
  quote from a platform, shown with a link, to somebody outside the team". A
  Reddit embed shows the post's words and links to it, so read literally it
  trips this.

The guideline below changes what a post shows. It does not change **how** the
posts were found. The re-review has to weigh both.

## What a published post would contain

| From Reddit and X | From every other platform |
|---|---|
| The platform's **official embed** of the post (X for Websites; Reddit's oEmbed markup). The platform renders the author, text and date. | **Quote + attribution + link**, as the contract already says: verbatim, credited to the platform and author, linked. |
| Our **own-words description**, naming the platform: "a developer on Reddit reported…" | Our own words around the quote |
| **No copied text**, no username or handle typed by us, no subreddit name in our prose | |

It would never contain: anything about how we collect or store, raw text from
Reddit or X outside an embed, or a count presented as a score.

**Checked in code, not by a reviewer's eye.** The demo generator refuses any
draft where a quote matches only a Reddit or X post. It also refuses embedding a
source that isn't Reddit or X, and typing a handle, subreddit or URL. Every
other quote is matched to its source word for word.

## What changes against each rule

**The display.** Embedding is the route both platforms offer to any website.
It doesn't need an API key or our collection route; it needs only the post's
public URL.

| Term (from `docs/platform-terms-reference.md`) | Quotes today | Official embed |
|---|---|---|
| X Display Requirements: author, avatar, unmodified text, timestamp, logo | ❌ a fragment is "modified text" | ✅ X renders exactly that |
| X Developer Policy, "Public display of Posts": use X for Websites, or the API, for the current version | ❌ | ✅ X for Websites |
| Reddit DT 5.2 attribution: username, link, "from Reddit" | ❌ we store no username | ✅ the embed shows all three |
| Deleted content is removed from display (Reddit DT 3.3; X DA IV.B) | ❌ our copy stays | ✅ a deleted post disappears from the embed |
| Reddit DAT 2.4: don't modify user content | ❌ cut fragments | ✅ shown whole, by Reddit |
| Reddit "Developer Platform": no Reddit content beside ads | - | ⚠ **no ads on pages carrying Reddit embeds** |

**The collection.** Embeds don't touch any of these.

| Recorded as unresolved in `sources.yaml` | Status |
|---|---|
| Reddit DAT 2.8: credentials issued by Reddit; a reseller route doesn't satisfy it "regardless of use" | Unchanged |
| Reddit DT 4.1: access "by or on behalf of a business" | Unchanged; no legal review yet |
| Reddit DAT 3.2 and Wiki: delete what isn't needed; deleted content even if de-identified | Unchanged for our stored copy |
| X ToS §4: our scraper route | Unchanged |
| Our description of a post is derived from content we collected | Commentary in our own words; the same position as press coverage, not a licence |

**Honest summary.** Embeds make what the public sees compliant with the
display rules. They leave the collection route exactly where the 2026-08-18 and
2026-09-08 rulings recorded it. Re-reviewing means deciding to publish
**with that known and accepted**, not deciding that it's resolved.

## What we say in public

Saying less about our methods is fine. Saying something untrue is not.

- **True, and enough:** "We read public discussions where engineers write about
  AI models (Reddit, X, Hacker News, GitHub, dev.to and engineering blogs) and
  count what they report."
- **Not true for every source, so never published:** "collected from official
  APIs" or "official APIs and public feeds only". The Reddit and X routes are
  recorded as a reseller and a scraper. An early Model Reports demo had this
  sentence; it has been corrected (2026-10-13).
- Not mentioning storage is a choice of detail. It doesn't change any term
  above, and nothing on the page should imply otherwise.

## Proposed amendment to "WHAT COUNTS AS PUBLICATION"

> An official platform embed, rendered by the platform from the post's public
> URL, is not a quote by us. A derived post may show Reddit and X content only
> through such embeds. Quoting Reddit or X text in our own prose, with or
> without a link, still counts as publication under this definition.

It needs `contract/sources.yaml` edited by its owner and a second reviewer. It
does not touch the `basis` of either ruling. The re-review records the decision
on those separately.

## To publish in the coming days

1. **Decide** this paper: the amendment, plus a re-review note on both rulings
   recording the accepted collection risk. Owner: anooj, second reviewer, MD.
2. **Generator: find all the evidence.** The generator reached threads through
   `claim`, and `board_entry.claim_id` is null for most current entries on
   every platform (all 525 X entries; 1,516 of 1,761 e5.5 dev.to entries; local
   backup, 2026-10-13). The fix joins through the entry's own document. It is
   written for 5 of 6 queries, but the edit to the sixth (topic candidates) was
   refused by a tool-permission check and is waiting on approval.
3. **Generator: embed mode** as a real feature, not the demo wrapper. It has to
   change three existing rules that otherwise fight it (measured over 6 runs):
   - the credit rule (an embed must count as the engineer's words);
   - the input-reference ban on "the post";
   - sentence length, since paraphrasing a post takes longer sentences than
     quoting it.
4. **Generator: platform diversity.** Configure a cap per platform and a
   minimum number of platforms per post in `blog_formats.yaml`, so a post
   draws on Reddit, X, Hacker News, GitHub, dev.to and blogs where the subject
   has them.
5. **Page:** fetch Reddit embed markup from Reddit's oEmbed endpoint at build
   time; the hand-written markup didn't render. No ads on any page that
   carries a Reddit embed.
6. **Per-post review:** a person approves each post before it's public. Only
   approved posts are indexable.

## Not decided here

- Whether to move Reddit to a direct, Reddit-issued Data API key with an
  approved use case. That is the only route that clears DAT 2.8; it takes
  longer than days.
- Whether to move X to the paid API. It isn't needed for embeds, which use only
  a post's public URL.
- Legal review of DT 4.1 ("on behalf of a business").
