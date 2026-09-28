# The class A re-review, 2026-09-18 — and what the three would contribute

**A re-reading of `blog-class-a-self-hosted`, not three rows added under it. The
clause fires once and covers all three. Its central deferred assumption — that
no terms page has been read for any feed — now has one confirmed
counter-example, and the re-reading has to say so.**

*anooj · 2026-09-18 · PROPOSED, NOT MERGED. `contract/` is the agreement and
gets two eyes. Evidence in `_class_a_evidence/`; the naming figures below are a
fresh measurement and are §1 rather than a footnote, because they are what
decides whether the re-review is worth doing at all.*

---

## 1 · What the three would contribute, before anything is harvested

Measured over the **ten most recent entries** of each feed, against the registry
as it stands (348 polled models). `lilianweng.github.io` and `eugeneyan.com`
carry summaries in their feeds (817 and 95 median chars), so their figures are
over **article text**; `jack-clark.net` carries full text in the feed.

| feed | entries in feed | names a model | **resolves to one** | models per naming entry |
|---|---:|---:|---:|---|
| `lilianweng.github.io` | 53 | 6/10 | **3/10** | 13, 3, 1, 1, 2, 1 |
| `eugeneyan.com` | 212 | 4/10 | **1/10** | 16, 1, 5, 2 |
| `jack-clark.net` | 10 | 8/10 | **0/10** | 3, 11, 11, 2, 6, 12, 8, 4 |

The board today, for comparison: **56 naming of 180 (31%), 18 resolving (10%)**.

⚠ **The two populations are not the same and the difference favours the
candidates.** The board's figures are over every document nine feeds have
accumulated since August; these are over each feed's ten most recent entries, in
a field where recency correlates with model mentions. A like-for-like comparison
needs the candidates' whole feeds, which needs the fetch the ruling gates. So
read these as an upper bound on what the first ten would give, not as a rate.

**With that caveat, the "twelfth feed is worth one naming document" expectation
does not hold for these three.** `hamel.dev` contributes 1 naming document from
12, `jxnl.co` 1 from 20, `vickiboykis.com` 2 from 22. These are 6, 4 and 8 from
ten. The expectation was drawn from feeds that write about practice rather than
about models, and these three write about models.

**`jack-clark.net` is the one to look at twice.** 8 of 10 name a model and **0
of 10 resolve to one** — Import AI is a weekly survey that names a dozen models
per issue. High naming and zero resolving is the `danluu.com` shape: real
evidence that extraction may or may not be able to attribute. `lilianweng.github.io`
is the opposite and the strongest of the three: 3 of 10 resolving is three times
the board's current rate.

---

## 2 · The re-review

Replacing the `reviewed_on`, `reviewed_by` and summary of
`blog-class-a-self-hosted`. Everything not shown is unchanged.

```yaml
  - id: blog-class-a-self-hosted
    class: A
    party: publisher
    reviewed_on: 2026-09-18          # was 2026-08-14
    reviewed_by: <name>              # a person, not UNRATIFIED-DRAFT
    basis: internal-development-only
    review_valid_days: 90            # reset from 2026-09-18
    evidence_valid_days: 90
    fetch_articles: true
```

and this added to the summary, above the existing text:

```
      RE-READ 2026-09-18, ON ADDING THREE FEEDS. The clause below fires on
      "adding a feed outside the nine assessed", and this is that reading.

      THE DEFERRAL BELOW NOW HAS ONE CONFIRMED COUNTER-EXAMPLE, and it is the
      reason this is a re-reading rather than a date change. The text says
      terms review is deferred and that the condition "a source whose terms
      forbid this use is dropped" HAS NOT BEEN TESTED. It has now been tested
      once - on Substack, 2026-09-18 - and it failed:

        - robots ALLOWED the article path and the feed;
        - the Acceptable Use Policy prohibited crawling any page or portion of
          the platform, and separately prohibited storing any significant
          portion of its content;
        - the prohibition was UNCONDITIONAL, so internal-development-only did
          not reach it.

      Two things follow for this ruling and neither is hypothetical.

      FIRST, ROBOTS AND TERMS CAN DIVERGE IN THE PERMISSIVE-TO-RESTRICTIVE
      DIRECTION. This ruling rests on robots carrying the weight while the
      reading is deferred - "where robots is silent, the class A reading is
      doing all of the work". Substack is a case where robots was not silent,
      was affirmative, and did not predict the outcome.

      SECOND, AN UNCONDITIONAL PROHIBITION IS NOT HELD OPEN BY THE BASIS. Every
      other unresolved condition in this file is about publication, monetization
      or audience, and internal-development-only genuinely speaks to those. A
      crawl clause that is contingent on nothing has nothing for the basis to
      hold.

      WHAT THAT DOES NOT SAY. The denominator is 1 of 1 terms documents read,
      and it was read on a PLATFORM with a drafted Acceptable Use Policy. The
      three feeds added today have no terms document at all - checked in two
      places, see each row's tos_notes - and a practitioner blog is a different
      kind of publisher from a platform. The finding is that the deferral is a
      real risk rather than a formality, not that the nine are likely to refuse.

      WHERE THE RISK CONCENTRATES, AND IT IS CHEAP TO CLOSE. The feeds likely to
      carry a drafted terms document are the corporate three - Grab, Slack,
      Spotify - and `docs/engineer-1/four-scopes-before-building.md` §3.4
      measures them at 1 model-naming document each and 0 resolving to a single
      model. Reading those three closes the deferral exactly where an
      unconditional clause is plausible, and drops them at near-zero
      evidentiary cost if any refuses. A person-afternoon, and it is the next
      thing this ruling should have done to it.

      TWELVE FEEDS AS OF THIS READING, NOT NINE.
```

The existing `RE-REVIEW REQUIRED BEFORE` clause stands unchanged, and now reads
against twelve.

---

## 3 · The three rows

### 3.1 · `blog:lilianweng.github.io`

```yaml
  - id: blog:lilianweng.github.io
    platform: blog
    endpoint: https://lilianweng.github.io/index.xml
    site: https://lilianweng.github.io/
    template_block:
      status: verified
      checked_on: 2026-09-18
      pages_examined: 10
      headings: []
    base_trust: 0.9
    provenance: seed
    terms_ruling: blog-class-a-self-hosted
    terms_evidence:
      checked_on: 2026-09-18
      robots_status: rules
      robots_http: 200
      feed_path_allowed: true
      robots_allows_article_path: true
      article_http: 200
      paywall_observed: false
      login_required: false
      terms_document_read: false
      feed_type: rss20
    measured:
      checked_on: 2026-09-18
      entries: 53
      median_body_chars: 37207
      byline_source: none
      declared_author: null
      entry_bylines_present: 0
      distinct_entry_bylines: 0
      resolves_to_voices: 0
    notes: >-
      `User-agent: * / Disallow:` - an empty Disallow, which permits everything
      explicitly. NO BYLINE ANYWHERE: the feed declares no author and no entry
      carries one, so `resolves_to_voices` is 0 and every document from here is
      UNATTRIBUTED rather than attributed to Lilian Weng because the domain is
      hers (rule 6, the same reading applied to hamel.dev's 9 unbylined
      entries). The feed carries SUMMARIES (817 median chars), not full text,
      so article fetches are required for this feed to be worth anything.
      Ten most recent entries: 6 name a tracked model, 3 resolve to exactly one.
    tos_notes: >-
      Class A, ruling blog-class-a-self-hosted, evidence checked 2026-09-18.
      robots.txt 200 with an empty Disallow; feed path and article path both
      allowed; sample fetch 200, no paywall, no login. RSS 2.0.
      TERMS PAGE NOT FOUND, AND NOT THE SAME AS ABSENT. Checked in two places -
      the sitemap robots advertises, and the front-page markup for any link
      matching terms/legal/privacy/copyright/licence/tos/disclaimer/imprint.
      Zero matches in either. What the site carries instead is a bare copyright
      notice, which asserts the default position and says nothing about
      automated retrieval. Absent from both places a terms page is normally
      reachable is as far as this check goes without a lawyer.
```

### 3.2 · `blog:eugeneyan.com`

```yaml
  - id: blog:eugeneyan.com
    platform: blog
    endpoint: https://eugeneyan.com/rss/
    site: https://eugeneyan.com/
    template_block:
      status: verified
      checked_on: 2026-09-18
      pages_examined: 10
      headings:
        - "If you found this useful, please cite this write-up as:"
        - "Join 11,800+ readers getting updates on machine learning, RecSys, LLMs, and engineering."
    base_trust: 0.9
    provenance: seed
    terms_ruling: blog-class-a-self-hosted
    terms_evidence:
      checked_on: 2026-09-18
      #: ⚠ NO-RULES, NOT `rules`. robots.txt is a single `Sitemap:` line with NO
      #: `User-agent` block at all, so no group applies to us and nothing is
      #: stated. That is the absence of a crawl policy, which this ruling's
      #: live_preconditions accept - and it is NOT "rules, everything allowed".
      #: The 404 CAVEAT's reasoning applies unchanged: where robots is silent
      #: the class A reading is doing all of the work.
      robots_status: no-rules
      robots_http: 200
      feed_path_allowed: true
      robots_allows_article_path: true
      article_http: 200
      paywall_observed: false
      login_required: false
      terms_document_read: false
      feed_type: rss20
    measured:
      checked_on: 2026-09-18
      entries: 212
      median_body_chars: 15679
      byline_source: none
      declared_author: null
      entry_bylines_present: 0
      distinct_entry_bylines: 0
      resolves_to_voices: 0
    notes: >-
      212 entries, the longest archive of the three. TEMPLATE BLOCK IS REAL AND
      MEASURED: 4 lines in 9 of 10 pages - a newsletter call to action and a
      three-line BibTeX citation block. Both are appended to nearly every post
      and neither is the author writing about a model.
      ONE OF THE TEN SAMPLED ARTICLES IS AN HTML META-REFRESH REDIRECT STUB
      ("Redirecting... Click here if you are not redirected."), 50 characters.
      Not a paywall; recorded because a short body is the shape a paywall also
      has and the distinction should be on the row rather than rediscovered.
      The feed carries 95-character summaries, so article fetches are required.
      Ten most recent entries: 4 name a tracked model, 1 resolves to exactly one.
    tos_notes: >-
      Class A, ruling blog-class-a-self-hosted, evidence checked 2026-09-18.
      robots.txt 200 and states NO rules - a bare Sitemap line, no User-agent
      group. Article path is therefore unrestricted by omission rather than by
      permission. Sample fetch 200, no paywall, no login. RSS 2.0.
      TERMS PAGE NOT FOUND, checked in the sitemap and the front-page footer
      markup; zero matches in either. Absent from two places, not established as
      absent from the site.
```

### 3.3 · `blog:jack-clark.net`

```yaml
  - id: blog:jack-clark.net
    platform: blog
    endpoint: https://jack-clark.net/feed/
    site: https://jack-clark.net/
    template_block:
      status: verified
      checked_on: 2026-09-18
      pages_examined: 10
      headings:
        - "Welcome to Import AI, a newsletter about AI research."
        - "Thanks for reading!"
    base_trust: 0.9
    provenance: seed
    terms_ruling: blog-class-a-self-hosted
    terms_evidence:
      checked_on: 2026-09-18
      robots_status: rules
      robots_http: 200
      feed_path_allowed: true
      robots_allows_article_path: true
      article_http: 200
      paywall_observed: false
      login_required: false
      terms_document_read: false
      feed_type: rss20
    measured:
      checked_on: 2026-09-18
      entries: 10
      median_body_chars: 16731
      byline_source: entry
      declared_author: null
      entry_bylines_present: 10
      distinct_entry_bylines: 1
      resolves_to_voices: 1
    notes: >-
      THE ONLY ONE OF THE THREE WITH A BYLINE. 10 of 10 entries carry one and
      they name one person, so `resolves_to_voices` is 1 - the only candidate
      whose documents attribute to a voice without inference.
      SHORTEST FEED WINDOW OF ANY SEATED FEED: 10 entries. An article that drops
      out of that window cannot be re-assembled from the feed, which is the
      hazard that nearly destroyed a grab.com context on 2026-09-18 - a delete
      plus re-harvest does not restore a post older than the window. Anything
      rebuilding this feed's contexts must work from stored payloads.
      The feed carries FULL TEXT (16,315 median chars), so this is the one feed
      of the three that could be harvested without article fetches at all.
      Ten most recent entries: 8 name a tracked model, 0 resolve to exactly one.
      Import AI is a weekly survey naming a dozen models per issue - high
      naming, zero resolving, and whether that becomes evidence depends on
      extraction splitting a survey into per-model claims. Unproven.
    tos_notes: >-
      Class A, ruling blog-class-a-self-hosted, evidence checked 2026-09-18.
      robots.txt 200, WordPress defaults - Disallow /wp-admin/ with an Allow for
      admin-ajax.php; feed and article paths both allowed. Sample fetch 200, no
      paywall, no login. RSS 2.0.
      TERMS PAGE NOT FOUND, checked in the sitemap and the front-page footer.
      ⚠ THIS CHECK IS THE WEAKEST OF THE THREE: jack-clark.net's sitemap is 518
      bytes - an index pointing at sub-sitemaps which were NOT followed. Absent
      from the index and the footer; a sub-sitemap could carry one.
      IMPORT AI ALSO PUBLISHES AT importai.substack.com, which is refused under
      blog-class-b-substack. Same publication, two hosts, two rulings: this row
      covers the self-hosted one and does not reach the Substack mirror.
```

---

## 4 · `sebastianraschka.com` is not seated

Drafted in #361 and deliberately left out. **44 of its 54 feed entries point
off-host** — to `magazine.sebastianraschka.com` (Substack) and `lightning.ai`.

The class A ruling permits *"the feed and the article URLs in it"*, and the
article URLs in this feed are mostly on a platform we refuse. `BlogFetcher`
gates every hop on robots and **nothing checks that an entry's host is the host
whose ruling authorised the fetcher** — all seven seated class A feeds are
on-host, so the gap has never fired, and seating this feed is what would fire
it.

Its on-host content is also 919–2,956 character stubs pointing at the real
article elsewhere: median 1,463 against `lilianweng.github.io`'s 37,207.

**Precondition for reconsidering it: the same-host check exists**, as a recorded
field first per rule 8, because its error rate against the seated nine is zero
of seven and that is a population it did not choose.

---

## 5 · What this proposal does not settle

- **The deferral is still deferred on all twelve.** `terms_document_read: false`
  on every row. This re-reading records that the assumption has failed once; it
  does not read eleven terms documents.
- **Whether a comparative survey yields per-model claims.** `jack-clark.net` at
  0/10 resolving and `lilianweng.github.io` at 3/10 are different bets, and only
  extraction settles which. That is model spend and a separate decision.
- **The same-host check.** Not proposed here; it is `collect/`'s and it gates
  `sebastianraschka.com` rather than these three.
