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

    harvest_runs_opened: int = 0
    harvest_runs_closed: int = 0
    documents_with_run_id: int = 0
    ledger_failures: list[str] = field(default_factory=list)
    http_errors: int = 0
    rate_limited: int = 0

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
        ]
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
    import json

    from collect.adapters.queries.sieve import matches, normalize, sieve
    from collect.adapters.reddit_write import write_documents
    from collect.ops.ledger import close_harvest_run, open_harvest_run
    from collect.rawstore import RAW

    block = contract.sweep_subreddits
    if not block:
        raise RuntimeError(
            "no `sweep_subreddits:` in contract/sources.yaml, so there is nothing to "
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
                f"{unknown} are not in contract/sources.yaml's sweep_subreddits. "
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

    report = RedditSweepReport(
        population_per_subreddit=pages * per_page,
        pages_per_subreddit=pages,
        sort=sort,
        cap=contract_cap if cap is None else cap,
        requests_planned=len(members) * pages,
    )

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

    for name in members:
        if report.requests_issued + pages > report.cap:
            report.unreached.append(name)
            continue

        seat = SubredditSweep(name=name)
        run = harvester.list_subreddit(name, pages=pages, sort=sort)

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

        seat.requests = run.pages_fetched
        seat.candidates = len(run.posts)
        seat.kept = len(run.survivors)
        seat.stored = wrote["documents_inserted"]
        if opened is not None:
            report.documents_with_run_id += seat.stored
        seat.exhausted = run.exhausted
        seat.hit_page_ceiling = run.truncated_by == "result-ceiling"
        roots.update(post.external_id for post in run.survivors)

        report.requests_issued += run.pages_fetched
        report.candidates += seat.candidates
        report.kept += seat.kept
        report.stored += seat.stored
        report.http_errors += run.http_errors
        report.rate_limited += run.rate_limited
        report.quota_exhausted = report.quota_exhausted or run.quota_exhausted
        if run.quota_remaining is not None:
            report.quota_remaining = run.quota_remaining
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
