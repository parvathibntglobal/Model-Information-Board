"""The Reddit listing sweep as a stage. Its own module, and its own denominator.

`chain.py` has carried `Stage("sweep-reddit", run=None, ...)` since `ops/` was
built, with its `starves=` naming what was missing: *"no Reddit documents, and no
document writer for them either."* The writer landed 2026-08-21
(`collect/adapters/reddit_write.py`). This is the stage.

WHY A LISTING AND NOT A SEARCH
------------------------------
Both shapes were costed. The listing wins on cost by a wide margin -- 84 requests
a day against 2,176, and 87 minutes overruns `harvest.yaml`'s 35-minute daily
ceiling -- but cost is not the deciding argument.

**The deciding argument is the kind of truncation.** Both shapes stop early. A
search stops at the most RELEVANT n, and GitHub's `max_pages = 1` is what that
costs: 321 of 1,019 runs hit the top-100 ceiling and supplied 51% of the yield,
so the retrieved set is the most favourable hundred the index could offer and
every rate over it is an upper bound. A listing sorted NEW stops at the most
RECENT n, and recency is unrelated to whether a post carries evidence -- so a
rate over it estimates the population rather than ceilings it.

`scripts/unfiltered_sweep.py` states the same conclusion from the other side:
*"the index ranks, and ranking is the selection effect this exists to escape."*

THREE THINGS THIS DELIBERATELY DOES NOT DO
------------------------------------------
**No `mark_swept`.** Stated rather than solved -- see `sweep_reddit`.

**No `truncated_by = 'quota'`.** That CHECK has no such value. An exhausted
monthly quota is recorded on `quota_exhausted` and named in the summary, because
`rate-limit` means retry in ~60 seconds and quota means stop for 23.893 days, and
a scheduler told the first when the second is true spends the exhausted quota
discovering it. Proposed as a sixth value in PR #161.

**No platform budget.** `harvest.yaml`'s `sweep_budget` has no platform
dimension, so the cap read here is GitHub's 900. Borrowed visibly rather than
silently: the report says whose it is. Proposed in PR #161.

Both gaps are named rather than allowed to hold the build, which is the
arrangement asked for.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from collect.ops.sweep import seated_variants, sweep_budget

log = logging.getLogger(__name__)

#: What this stage records, TYPED FROM THE FIRST ROW rather than inherited later.
#: `reddit_write.py` used to hardcode a provenance string for every caller, and
#: the per-model fetch's query arm wrote 853 rows through it asserting there had
#: been nothing to record. The writer now refuses to guess.
#:
#: `run_recorded`, AND THAT IS A CORRECTION. This was `no_run_for_source` on the
#: grounds that a listing renders no query -- true, and not what the value says.
#: It says THIS SOURCE ISSUES NO PER-QUERY RUN, so a NULL `harvest_run_id` is
#: complete. This stage opens a `harvest_run` row per subreddit, so a run DOES
#: exist and the documents can point at it, which is the whole purpose of the
#: column. `document_retrieval_provenance_agrees_ck` then requires this value.
LISTING = "run_recorded"

#: Where a subreddit's documents land when the LEDGER WRITE FAILED. A run
#: existed, its id never reached the writer, and that is `not_recorded` exactly.
#: Not `no_run_for_source`: claiming completeness because our own bookkeeping
#: broke is the positive-claim failure the 853 rows already demonstrated.
LISTING_WITHOUT_LEDGER = "not_recorded"


@dataclass
class SubredditSweep:
    """One subreddit's share of a listing sweep."""

    name: str
    requests: int = 0
    candidates: int = 0
    kept: int = 0
    stored: int = 0
    harvest_runs: int = 0
    exhausted: bool = False
    hit_page_ceiling: bool = False


@dataclass
class RedditSweepReport:
    """What the sweep read, kept and wrote -- and the denominator of every rate.

    `population_per_subreddit` is ON THE REPORT rather than left in the contract,
    because every rate below is over it. GitHub's `harvest_run` rows carry
    candidate counts and say nothing about the top-100 ceiling that governs them,
    and every figure derived from those rows has had to reconstruct the
    denominator afterwards. This does not repeat that.
    """

    subreddits: list[SubredditSweep] = field(default_factory=list)
    unreached: list[str] = field(default_factory=list)

    #: THE DENOMINATOR, from `contract/sources.yaml`: pages x posts_per_page.
    population_per_subreddit: int = 0
    pages_per_subreddit: int = 0
    sort: str = ""

    requests_planned: int = 0
    requests_issued: int = 0
    candidates: int = 0
    kept: int = 0
    stored: int = 0

    #: Distinct thread roots among the stored documents. **THE RESULT**, not
    #: `stored`. The existing corpus is 1,049 documents across eleven
    #: conversations with 190 from one launch thread, and reporting documents
    #: alone is what made that read as coverage.
    distinct_threads: int = 0
    group_hits: dict[str, int] = field(default_factory=dict)

    #: The comment fetch, one request per survivor. Four outcomes kept apart
    #: because they mean different things on the page: comments stored, a
    #: thread the platform says has none, a link post with no thread, and a
    #: fetch that FAILED - the last is an absence we caused, not one we found.
    comment_requests: int = 0
    threads_with_comments: int = 0
    comments_stored: int = 0
    threads_without_comments: int = 0
    threads_not_a_thread: int = 0
    comment_fetch_failures: list[str] = field(default_factory=list)

    harvest_runs_opened: int = 0
    harvest_runs_closed: int = 0
    documents_with_run_id: int = 0
    ledger_failures: list[str] = field(default_factory=list)
    http_errors: int = 0
    rate_limited: int = 0

    #: Posts the listings carried with Reddit's `over_18` flag, skipped before
    #: they became documents (#602 item 9). Not in `candidates`.
    adult_skipped: int = 0

    #: THE MEDIA BLOCK'S CAP COUNTS COMMENT REQUESTS TOO (#602). A comment
    #: request the cap stopped is DEFERRED - counted here and taken first by the
    #: next run - never silently dropped. `deferred_taken` is how many earlier
    #: deferrals this run fetched.
    comments_counted_in_cap: bool = False
    comments_deferred: int = 0
    deferred_taken: int = 0
    block: str = "sweep_subreddits"

    #: THE MEDIA BLOCK STORES EVERY POST (#602, Anooj's A). The pages are bought
    #: already, so the posts cost nothing; comments are fetched only for the
    #: posts that name a model the registry OR the catalogue knows. Both counts
    #: are said, so a hand run shows what the filter costs (rule 8).
    stores_every_post: bool = False
    posts_naming_a_known_model: int = 0
    posts_stored_without_comments: int = 0

    #: Set when the MONTHLY quota ran out. Deliberately not `truncated_by`.
    quota_exhausted: bool = False
    quota_remaining: int | None = None
    quota_limit: int | None = None

    cap: int = 0
    cap_borrowed_from: str = "github"

    @property
    def offered(self) -> int:
        """Posts the listing could have shown us. The rate denominator."""
        return self.population_per_subreddit * len(self.subreddits)

    @property
    def sieve_rates(self) -> dict[str, float]:
        """Per-group pass rate over candidates SEEN. Empty when none were.

        Rule 7: zero-of-zero and zero-of-many are different findings, and only
        one of them is about the sieve.
        """
        if not self.candidates:
            return {}
        return {g: h / self.candidates for g, h in sorted(self.group_hits.items())}

    def summary(self) -> str:
        lines = [
            f"sweep    : {len(self.subreddits)} subreddit(s) listed, "
            f"{len(self.unreached)} unreached, "
            f"{self.requests_issued} of {self.requests_planned} planned request(s)",
            f"           DENOMINATOR: the newest {self.population_per_subreddit} posts "
            f"per subreddit ({self.pages_per_subreddit} pages x 25, sort {self.sort}) "
            f"= {self.offered} offered",
            "           A RECENCY CUT, NOT A RANKING CUT. No index chose these posts, "
            "so a rate over them estimates the population rather than ceilings it.",
            f"           {self.candidates} candidate(s) of {self.offered} offered, "
            f"{self.kept} kept, {self.stored} document(s) stored",
            f"           DISTINCT THREADS: {self.distinct_threads}   <- the result",
            f"           adult-flagged (over_18) post(s) skipped before storing: "
            f"{self.adult_skipped}",
            (f"           media posts: every listed post stored; "
             f"{self.posts_naming_a_known_model} named a known model and had their "
             f"comments read, {self.posts_stored_without_comments} stored without "
             f"comments" if self.stores_every_post else "           media posts: -"),
            f"           block: {self.block}"
            + (f"; comment requests count against the cap - {self.comments_deferred} "
               f"deferred to the next run, {self.deferred_taken} earlier deferral(s) "
               f"taken this run" if self.comments_counted_in_cap else ""),
            f"           comments: {self.comment_requests} request(s) for {self.kept} "
            f"kept post(s); {self.threads_with_comments} thread(s) with comments "
            f"({self.comments_stored} comment document(s) stored), "
            f"{self.threads_without_comments} with none on the platform, "
            f"{self.threads_not_a_thread} link post(s) with no thread, "
            f"{len(self.comment_fetch_failures)} FAILED fetch(es)",
        ]
        if self.comment_fetch_failures:
            lines.append(
                "           * a FAILED comment fetch assembles body-only and reads as a "
                "post nobody answered. Re-fetch before assembly: "
                + ", ".join(self.comment_fetch_failures[:5])
            )
        if self.candidates:
            rates = ", ".join(
                f"{g} {h} ({100 * h / self.candidates:.1f}%)"
                for g, h in sorted(self.group_hits.items())
            )
            lines.append(
                f"           sieve, of {self.candidates} candidates: {rates or 'no group hits'}"
            )
        else:
            lines.append(
                "           sieve: NO CANDIDATES SEEN, so no rate. Not a rate of 0."
            )
        lines += [
            f"           harvest_run: {self.harvest_runs_opened} opened, "
            f"{self.harvest_runs_closed} closed",
            f"           documents carrying harvest_run_id: {self.documents_with_run_id} "
            f"of {self.stored}",
            f"           budget: {self.requests_issued}/{self.cap} requests, and that cap "
            f"is {self.cap_borrowed_from.upper()}'S -- harvest.yaml has no platform "
            f"dimension (PR #161)",
        ]
        if self.quota_exhausted:
            lines.append(
                "           * MONTHLY QUOTA EXHAUSTED. On quota_exhausted, NOT "
                "truncated_by: that CHECK has no 'quota' value, and 'rate-limit' would "
                "tell a scheduler to retry against a 23.893-day wall (PR #161)"
            )
        if self.quota_remaining is not None:
            limit = self.quota_limit if self.quota_limit is not None else "UNREAD"
            lines.append(f"           quota: {self.quota_remaining} remaining of {limit}")
        lines.append(
            "           last_swept_at: NOT STAMPED, deliberately. A listing sweep "
            "targets no model, so stamping would mark models it never aimed at and the "
            "rotation would read them as freshly covered"
        )
        if self.ledger_failures:
            lines.append(f"           ledger failures: {len(self.ledger_failures)}")
        return "\n".join(lines)


def sweep_reddit(
    conn,
    harvester,
    *,
    contract,
    cap: int | None = None,
    pages: int | None = None,
    subreddits: list[str] | None = None,
    limit_subreddits: int | None = None,
    source_id: str = "reddit",
    provenance: str = LISTING,
    fallback: str = LISTING_WITHOUT_LEDGER,
    block_key: str = "sweep_subreddits",
) -> RedditSweepReport:
    """List every contracted subreddit, sieve what comes back, store what passes.

    NO `mark_swept`, AND THAT IS STATED RATHER THAN SOLVED. `last_swept_at`
    answers *"when was this MODEL last covered"*, and a listing sweep covers
    subreddits -- which models appear in them is an outcome, not an input. Both
    tempting fixes are worse than the gap:

        stamp every model a swept post mentions
            a model named once in one comment reads as freshly covered, and the
            rotation then deprioritises models actually swept. That is the
            ordering working backwards, which `sweep_github` already refuses to
            do for a seat the clock cut short.

        stamp nothing and say nothing
            a Reddit sweep runs nightly and `last_swept_at` never moves, so the
            column silently means "last GitHub sweep" while being named for
            coverage in general.

    So this writes none and the report says why. A rotation reading a listing
    sweep as per-model freshness is rule 6 in the scheduler, and the
    deprioritisation it causes is invisible because it looks considered.
    """

    from collect.adapters.queries.sieve import matches, names_folded, normalize, sieve
    from collect.adapters.reddit_write import write_documents
    from collect.ops.ledger import close_harvest_run, open_harvest_run
    from collect.rawstore import RAW

    block = getattr(contract, block_key, None)
    if not block:
        raise RuntimeError(
            f"no `{block_key}:` in contract/sources.yaml, so there is nothing to "
            "list. A sweep over an empty subreddit list retrieves nothing and reports "
            "it as nobody discussing anything, which is rule 4 where nobody is looking."
        )

    # THE CONTRACT IS THE POPULATION; THE ARGUMENTS ONLY NARROW IT.
    # `subreddits` cannot introduce one the contract does not list -- a sweep of
    # an unchosen subreddit is a population nobody signed, and the chosen_on date
    # on the block would then describe something else.
    members = [str(m) for m in block.get("members") or []]
    if subreddits:
        wanted = set(subreddits)
        unknown = sorted(wanted - set(members))
        if unknown:
            raise RuntimeError(
                f"{unknown} are not in contract/sources.yaml's {block_key}. "
                f"The contract is the population; an argument may only narrow it."
            )
        members = [m for m in members if m in wanted]
    if limit_subreddits is not None:
        members = members[:limit_subreddits]
    # THE DENOMINATOR COMES FROM ONE PLACE. `pages` overrides the contract for a
    # smoke run, and it must reach the report -- an override that changed what was
    # fetched while the report kept quoting the contract's 175 would print a
    # denominator the run did not use, which is the exact failure rule 7 is about.
    pages = int(block["pages_per_subreddit"]) if pages is None else int(pages)
    per_page = int(block["posts_per_page"])
    sort = str(block.get("sort") or "NEW")
    contract_cap, _minutes = sweep_budget("daily")
    #: THE MEDIA BLOCK CARRIES ITS OWN BUDGET (#602 item 7), and it covers the
    #: comment requests as well as the listing pages. The text block keeps the
    #: borrowed GitHub cap, unchanged.
    own_cap = block.get("max_requests")
    subject_only = bool(block.get("subject_only"))
    report = RedditSweepReport(
        population_per_subreddit=pages * per_page,
        pages_per_subreddit=pages,
        sort=sort,
        cap=(int(own_cap) if own_cap is not None else contract_cap) if cap is None else cap,
        requests_planned=len(members) * pages,
        comments_counted_in_cap=own_cap is not None,
        block=block_key,
        stores_every_post=subject_only,
    )
    #: The names a media post must carry for its comments to be read: every
    #: model the registry or the catalogue knows, as the E4b weight counts
    #: them - so a post about a model nobody has seated yet still has its
    #: comments read, and their claims are held rather than never seen.
    known_names = _known_model_names(conn) if subject_only else ()
    comment_worthy: set[str] = set()
    if own_cap is not None:
        report.cap_borrowed_from = block_key

    def spent() -> int:
        """Requests against the cap: pages, plus comments where the block says so."""
        return report.requests_issued + (
            report.comment_requests if report.comments_counted_in_cap else 0)

    by_surface = _seated_term_sets(conn)
    if not by_surface:
        raise RuntimeError(
            "no rows in `model_alias`, so the sieve has nothing to match. A listing "
            "renders no query, so the terms do ALL of the narrowing here -- an empty "
            "term set keeps nothing and would report it as nobody discussing anything."
        )

    # The harvester owns the store; the stage borrows it to persist survivors.
    harvester_store = harvester._store  # noqa: SLF001 - one attribute, one caller

    roots: set[str] = set()

    # EARLIER DEFERRALS FIRST, before any new page is bought (#602).
    if report.comments_counted_in_cap:
        _take_deferred(conn, harvester, harvester_store, members, report, spent,
                       fallback=fallback, known_names=known_names)

    for name in members:
        if spent() + pages > report.cap:
            report.unreached.append(name)
            continue

        seat = SubredditSweep(name=name)
        run = harvester.list_subreddit(name, pages=pages, sort=sort)
        # COUNTED AS SOON AS BOUGHT, so the comment fetches below see them
        # against the cap. Added after the subreddit was done, the media
        # cap let one comment request too many through.
        report.requests_issued += run.pages_fetched

        # The row exists before anything is written, so a process killed
        # mid-subreddit leaves `finished_at IS NULL` -- the only carrier of
        # "started and never came back". Same two-phase shape as `sweep_github`.
        opened = None
        try:
            opened = open_harvest_run(
                conn, {**run.harvest_run_fields(), "source_id": source_id}
            )
            conn.commit()
            report.harvest_runs_opened += 1
        except Exception as error:  # noqa: BLE001
            log.warning("harvest_run could not be opened for %s: %s", run.query, error)
            report.ledger_failures.append(
                f"open {run.query}: {type(error).__name__}: {error}"
            )
            conn.rollback()

        # SIEVE AGAINST EVERY SEATED SPELLING, SUBJECT FIRST.
        #
        # Which spelling found a post says nothing about how the post NAMES the
        # model -- and here nothing found it at all, so the terms carry the whole
        # burden. That is 177 surfaces x 24 entries = 4,248 term sets, and the
        # naive arrangement ran `sieve()` for every one of them on every post:
        # 106,200 calls per 25-post page, each recomputing `normalize(text)` and
        # `normalize(author_prose(text))` from scratch. 8.9 million calls for a
        # full sweep, measured at minutes per page before this loop was changed.
        #
        # SUBJECT IS THE CHEAP DISCRIMINATOR AND IT IS SHARED. It is ALL-OF, it
        # is derived from the alias, and it is IDENTICAL across all 24 entries for
        # a given surface -- so it is tested once per surface against a haystack
        # normalised once per post, and 24 term sets are skipped together when it
        # fails. On the smoke page 2 of 25 posts named any seated model, so the
        # full sieve runs on a small fraction and the semantics are unchanged: a
        # post survives iff some (surface, entry) pair passes.
        for post in run.posts:
            text = post.sieve_text
            if subject_only:
                # STORED WHATEVER IT NAMES; its comments only if it names a
                # known model (Anooj's A on #602).
                run.survivors.append(post)
                if any(names_folded(name, text) for name in known_names):
                    comment_worthy.add(post.external_id)
                    report.group_hits["subject"] = report.group_hits.get("subject", 0) + 1
                continue
            haystack = normalize(text)
            passed = False
            groups_hit: set[str] = set()
            for subject_terms, term_sets in by_surface.values():
                if not all(matches(term, haystack) for term in subject_terms):
                    continue
                groups_hit.add("subject")
                for terms in term_sets:
                    verdict = sieve(terms, text)
                    run.verdicts.append(verdict)
                    for group in ("topic", "signal"):
                        if getattr(verdict, group):
                            groups_hit.add(group)
                    if verdict.passed:
                        passed = True
            for group in groups_hit:
                report.group_hits[group] = report.group_hits.get(group, 0) + 1
            if passed:
                run.survivors.append(post)

        # EACH SURVIVOR'S OWN PAYLOAD IS STORED BEFORE THE ROW IS WRITTEN.
        #
        # `document.text_ref` is NOT NULL, and the listing stores the PAGE in
        # `raw/` -- a page is not a document, so a row pointing at it could not
        # say which post it was. Storing per survivor makes `text_ref` a location
        # for THIS post and `content_hash` its identity, which is the split
        # `rawstore.py` opens with.
        #
        # Found by the first run that kept anything. Six earlier runs kept zero
        # and this path never executed, so the defect was invisible while the
        # sieve was passing nothing -- which is the shape worth recording: a
        # writer starved of input looks like a writer that works.
        refs = {}
        for post in run.survivors:
            # THE PAYLOAD, NOT THE PROSE, per the ruling in
            # `docs/engineer-1/ruling-what-content-hash-identifies.md`:
            #
            #     content_hash    the hash of the BYTES THE PLATFORM GAVE US.
            #     text_ref        the location of those same bytes.
            #     prose           DERIVED AT ASSEMBLY, never stored in place
            #                     of the payload.
            #
            # READ THE HISTORY BEFORE CHANGING THIS BACK. This line stored
            # prose from 2026-08-28 until 2026-09-14, under a comment arguing
            # that a stored envelope lets a quote verify against a field VALUE.
            # That hazard is real and it is not answered here - it is answered
            # at assembly by `collect/assemble/prose.py`, which extracts prose
            # from the payload and REFUSES bytes that are not one. The comment
            # that used to sit here was written three hours BEFORE the ruling
            # that overruled it, and because nothing touched this file
            # afterwards it read as dissent for fourteen days while 264 rows
            # accumulated that no assembler can use.
            #
            # Storing prose breaks two NFRs, neither about verification:
            #   NFR-6  `content_hash` must fingerprint what the AUTHOR
            #          published. Prose fingerprints a string WE assembled, so
            #          it moves whenever the extractor does.
            #   NFR-4  "reprocess from raw rather than re-fetching" needs the
            #          row to name its raw artifact. Prose names nothing, and
            #          on Reddit there is no re-fetch for an old thread.
            #
            # `sort_keys=True, ensure_ascii=False` is the house spelling
            # (`github.py:703`, `huggingface.py:710`, `x.py:1044`) so the same
            # post re-fetched hashes identically and the store deduplicates it.
            payload = json.dumps(post.raw, ensure_ascii=False, sort_keys=True)
            stored = harvester_store.put(payload.encode("utf-8"), namespace=RAW)
            refs[post.external_id] = (stored.ref, stored.content_hash)

        # THE RUN ID REACHES THE DOCUMENTS. `opened` is minted before the fetch
        # by the two-phase ledger, so it is already in scope -- one call site, not
        # a redesign. Where the ledger write failed there is no id to carry, and
        # the writer records `not_recorded` rather than inventing completeness.
        wrote = write_documents(
            conn,
            run.survivors,
            retrieval_provenance=provenance if opened is not None else fallback,
            harvest_run_id=opened.id if opened is not None else None,
            refs=refs,
        )
        conn.commit()

        # EVERY SURVIVOR'S DISCUSSION, NOT ONLY ITS POST. Added 2026-10-05.
        #
        # Until this loop the listing stored posts and nothing under them, so
        # the assembler found no comments and wrote `post_body_only`. Measured
        # on staging 2026-10-05: of 1,507 roots this sweep wrote (one run,
        # 2026-08-28), 17 had any comment document, while the platform's own
        # count said 1,417 of them had comments (median 50). The search arm in
        # `scripts/fetch_model.py` already fetched comments - 137 of its 185
        # roots carry them - so the gap was this stage alone.
        #
        # FETCHED BEFORE THE FIRST ASSEMBLY, WHICH IS THE ONLY CHEAP MOMENT. A
        # context's id does not hash its members and `write_thread_context` is
        # ON CONFLICT DO NOTHING, so a post assembled body-only stays body-only
        # when comments arrive later; repairing it is a rebuild and, where it
        # was extracted, a paid re-extraction.
        #
        # ALL OF THEM, AND THE TOP ONES ARE CHOSEN DOWNSTREAM. The whole tree
        # is stored; which replies reach the extractor is decided at assembly
        # by `collect/assemble/ranking.py` under `contract/harvest.yaml`
        # `child_ranking`. Nothing here filters a reply.
        #
        # One request per survivor, paced by the harvester's own limiter, and
        # NOT counted against `report.cap` - that cap is GitHub's page budget
        # (`cap_borrowed_from`). The bound is the survivor count, which the
        # listing caps at `offered`, and the summary prints both.
        def _store_comments(post, refs=refs, opened=opened) -> None:
            fetch = harvester.fetch_comments(post)
            report.comment_requests += 0 if fetch.not_a_thread else 1
            report.http_errors += fetch.http_errors
            report.rate_limited += fetch.rate_limited
            if fetch.quota_remaining is not None:
                report.quota_remaining = fetch.quota_remaining
            if fetch.quota_limit is not None:
                report.quota_limit = fetch.quota_limit
            if fetch.not_a_thread:
                report.threads_not_a_thread += 1
                return
            # A 429 IS A FAILED FETCH TOO (review of #503): the adapter counts
            # it in `rate_limited`, not `http_errors`, so testing only the
            # latter filed a rate-limited thread under "no comments on the
            # platform" - an absence we caused, read as one we found.
            if (fetch.http_errors or fetch.rate_limited) and not fetch.comments:
                report.comment_fetch_failures.append(post.external_id)
                return
            if not fetch.comments:
                # The platform returned a thread with no comments. Assembly
                # records it as body-only with coverage 0.0 - a true absence,
                # distinct from one we caused by not asking.
                report.threads_without_comments += 1
                return
            comment_refs = {}
            for comment in fetch.comments:
                payload = json.dumps(comment.raw, ensure_ascii=False, sort_keys=True)
                stored = harvester_store.put(payload.encode("utf-8"), namespace=RAW)
                comment_refs[comment.external_id] = (stored.ref, stored.content_hash)
            # The post rides along so the writer can root its comments; its own
            # row already exists and conflicts away.
            comment_refs[post.external_id] = refs[post.external_id]
            wrote_comments = write_documents(
                conn,
                [post, *fetch.comments],
                retrieval_provenance=provenance if opened is not None else fallback,
                harvest_run_id=opened.id if opened is not None else None,
                refs=comment_refs,
            )
            conn.commit()
            report.threads_with_comments += 1
            report.comments_stored += int(wrote_comments.get("documents_inserted", 0) or 0)

        for post in run.survivors:
            if subject_only and post.external_id not in comment_worthy:
                # NAMES NO KNOWN MODEL: stored above, no comment request spent.
                report.posts_stored_without_comments += 1
                continue
            if subject_only:
                report.posts_naming_a_known_model += 1
            if report.comments_counted_in_cap and spent() >= report.cap:
                # DEFERRED, NOT DROPPED: the post is stored, its comments are
                # not, and `_take_deferred` finds it first on the next run.
                report.comments_deferred += 1
                continue
            # ONE POST'S FAILURE IS ONE POST'S (review of #503). An exception
            # here - a malformed response, a dropped connection on the write -
            # used to propagate out of the sweep: the harvest_run was never
            # closed, the remaining subreddits were skipped and the report was
            # lost. Now the post is named in `comment_fetch_failures`, the
            # connection rolled back, and the sweep carries on.
            try:
                _store_comments(post)
            except Exception as error:  # noqa: BLE001 - recorded, not swallowed
                log.warning("comment fetch/write failed for %s: %s", post.external_id, error)
                report.comment_fetch_failures.append(post.external_id)
                conn.rollback()

        seat.requests = run.pages_fetched
        seat.candidates = len(run.posts)
        seat.kept = len(run.survivors)
        seat.stored = wrote["documents_inserted"]
        if opened is not None:
            report.documents_with_run_id += seat.stored
        seat.exhausted = run.exhausted
        seat.hit_page_ceiling = run.truncated_by == "result-ceiling"
        roots.update(post.external_id for post in run.survivors)

        report.adult_skipped += run.adult_skipped
        report.candidates += seat.candidates
        report.kept += seat.kept
        report.stored += seat.stored
        report.http_errors += run.http_errors
        report.rate_limited += run.rate_limited
        report.quota_exhausted = report.quota_exhausted or run.quota_exhausted
        # THE LOWER READING WINS (review of #503). The listing's figure was read
        # BEFORE this subreddit's comment requests, so letting it overwrite the
        # comment loop's later reading overstated the quota left by every
        # comment request. The quota only falls within its window.
        if run.quota_remaining is not None:
            report.quota_remaining = (
                run.quota_remaining if report.quota_remaining is None
                else min(report.quota_remaining, run.quota_remaining)
            )
        if run.quota_limit is not None:
            report.quota_limit = run.quota_limit

        if opened is not None:
            try:
                close_harvest_run(
                    conn, opened,
                    {**run.harvest_run_fields(), "source_id": source_id},
                    outcome="error" if run.http_errors else "ok",
                )
                conn.commit()
                report.harvest_runs_closed += 1
                seat.harvest_runs += 1
            except Exception as error:  # noqa: BLE001
                log.warning("harvest_run could not be closed for %s: %s", run.query, error)
                report.ledger_failures.append(
                    f"close {run.query}: {type(error).__name__}: {error}"
                )
                conn.rollback()

        report.subreddits.append(seat)

    report.distinct_threads = len(roots)

    return report


#: Stored posts of a block's subreddits whose platform comment count is above
#: zero and which have no stored comment: the deferrals of an earlier run.
DEFERRED = """
    SELECT d.id, d.text_ref FROM document d
     WHERE d.source = 'reddit' AND d.thread_root_id IS NULL
       AND coalesce((d.engagement->>'comments')::int, 0) > 0
       AND d.url ~* %s
       AND NOT EXISTS (SELECT 1 FROM document c WHERE c.thread_root_id = d.id)
     ORDER BY d.fetched_at, d.id
     LIMIT %s
"""


def _known_model_names(conn) -> tuple[str, ...]:
    """Every model name the registry or the catalogue knows, "Provider: " dropped.

    The media sweep's comment test (#602). A catalogue that cannot be read
    leaves the registry's names, and the sweep summary is not quieter for it -
    the count of posts that named a known model is printed either way.
    """
    names = {r[0] for r in conn.execute(
        "SELECT display_name FROM model_version WHERE display_name IS NOT NULL").fetchall()}
    try:
        names |= {r[0] for r in conn.execute(
            "SELECT name FROM model_catalog WHERE canonical_id NOT LIKE '~%%'").fetchall()}
    except Exception:  # noqa: BLE001 - an unmigrated database is a state
        conn.rollback()
    # THE SEATED SPELLINGS TOO (2026-11-06). The registry's display name is one
    # spelling; people write "Eleven v3" for ElevenLabs v3 and "seedance-2.0"
    # for Seedance 2.0. Every live alias surface and variant is a known name.
    try:
        for surface, variants in conn.execute(
                "SELECT surface, variants FROM model_alias "
                "WHERE valid_until IS NULL OR valid_until > now()").fetchall():
            names.add(surface)
            names.update(v for v in (variants or []) if v)
    except Exception:  # noqa: BLE001 - an unmigrated database is a state
        conn.rollback()
    from collect.adapters.queries.sieve import name_forms

    out = {form for n in names if n for form in name_forms(n)}
    # A slug ("elevenlabs/eleven-v3") is not how a post names a model.
    return tuple(sorted(n for n in out if n and "/" not in n))


def _take_deferred(conn, harvester, store, members, report, spent, *, fallback,
                   known_names=()) -> None:
    """Fetch the comments of posts an earlier run stored but could not afford.

    ONLY POSTS THAT NAME A KNOWN MODEL. The media block stores every post and
    reads comments only for those, so a stored post with no comments is usually
    one it chose not to read - not a deferral. Re-testing the name here keeps
    the next sweep's cap for the posts a cap really stopped.
    """
    import re

    from collect.adapters.queries.sieve import names_folded
    from collect.adapters.reddit import _post_of
    from collect.adapters.reddit_write import write_documents
    from collect.rawstore import RAW

    if not members:
        return
    pattern = "reddit\\.com/r/(" + "|".join(re.escape(m) for m in members) + ")/"
    rows = conn.execute(DEFERRED, (pattern, max(report.cap - spent(), 0))).fetchall()
    for doc_id, text_ref in rows:
        if spent() >= report.cap:
            report.comments_deferred += 1
            continue
        try:
            post = _post_of(json.loads(store.get_text(text_ref)))
        except Exception:  # noqa: BLE001 - its payload is not here; named
            report.comment_fetch_failures.append(doc_id)
            continue
        if known_names and not any(names_folded(n, post.sieve_text) for n in known_names):
            continue  # stored without comments on purpose, not deferred
        fetch = harvester.fetch_comments(post)
        report.comment_requests += 0 if fetch.not_a_thread else 1
        if not fetch.comments:
            continue
        refs = {}
        for comment in fetch.comments:
            blob = json.dumps(comment.raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
            stored = store.put(blob, namespace=RAW)
            refs[comment.external_id] = (stored.ref, stored.content_hash)
        wrote = write_documents(conn, list(fetch.comments), retrieval_provenance=fallback,
                                refs=refs)
        conn.commit()
        report.deferred_taken += 1
        report.comments_stored += int(wrote.get("documents_inserted", 0) or 0)


def _seated_term_sets(conn):
    """`{surface: (subject_terms, term_sets)}` -- grouped so subject tests once.

    A listing renders no query, so the terms do ALL of the narrowing -- which
    `collect/adapters/queries/__init__.py` describes as the design rather than a
    fallback: *"SIEVE local, exact, identical on all three platforms. This is
    where the terms do their actual work."*

    GROUPED BY SURFACE, NOT FLAT, and that is a performance fact with a semantic
    reason behind it: `subject` is ALL-OF and alias-derived, so every entry for a
    given surface carries the same subject. Testing it once per surface skips 24
    term sets together, and the grouping is what makes a full sweep finish. See
    the loop in `sweep_reddit` for the measured cost of not doing this.

    The two substitution entries are excluded for the same reason every renderer
    excludes them: `direction: decided_at_extraction` is a fact about the
    pipeline, not about an index.
    """
    from collect.adapters.queries import load_queries
    from collect.adapters.queries.sieve import normalize

    entries = [e for e in load_queries().all_entries if not e.direction_from_extraction]
    surfaces = sorted({s for v in seated_variants(conn).values() for s in v})
    out = {}
    for surface in surfaces:
        term_sets = tuple(entry.terms.substitute(surface) for entry in entries)
        if not term_sets:
            continue
        # Every entry's subject is the same rendered alias, so any of them will
        # do. Taken from the first rather than recomputed per entry.
        out[normalize(surface)] = (term_sets[0].subject, term_sets)
    return out
