"""E4 over the STORED corpus. The caller `triage` never had.

WHAT WAS WRONG, IN ONE SENTENCE. `collect/triage/gates.py` has run six gates,
been tested and been measured since it was built - and **nothing ever ran it
against the database**. `document.triage_verdict` is NULL on all 6,502 stored
rows, `collect/ops/chain.py` carries `Stage('triage', run=None)`, and every
survival figure this project has quoted came from a script building `Document`s
by hand off a JSONL export:

    scripts/labelling_pools.py        the 1,297-post substitution corpus
    scripts/corpus_inventory.py       a per-source inventory
    scripts/classify_capability_reports.py

Same shape as `score-documents` before 2026-08-31 and as issue #27: not a
broken gate, a gate that was never called. The 82.8% in `gates.py`'s docstring
is a real figure about a hand-built population and has never been a figure about
the corpus.

IT WRITES TWO COLUMNS AND DELIBERATELY NOT THE THIRD
-----------------------------------------------------
    triage_verdict   kept | dropped        WRITTEN
    filter_reasons   the gates that fired  WRITTEN
    status           kept | filtered | …   NOT WRITTEN. See below.

**Rule 8 is the whole reason for that split, and it is not caution.** Two of
the six gates cannot run: no language detector is installed and
`contract/bots.yaml` does not exist, so `wrong_language` and `known_bot` report
UNAVAILABLE for every document in the corpus. A check whose error rate has not
been measured against a population it did not choose ships as a **recorded
field**, never as a gate - and `document.status` is the gate action, because
`judge/` reads `status = 'kept'` (there is an index for exactly that predicate)
and `judge/pages/filtered.py` renders the rest. Writing `status = 'filtered'`
here would drop documents out of `judge/`'s view on the strength of four gates
out of six, and a false positive would be INVISIBLE: an absence we caused,
reading as one we found (rule 4, one stage earlier).

`triage_verdict = 'dropped'` records the same judgement where somebody can
count it, argue with it, and measure its error rate against the labelling pool.
Promotion to `status` is one-way and goes on that evidence, never before it.

THE SUBJECT GATE READS THE THREAD ROOT, AND THE ROOT IS REACHED BY A JOIN
--------------------------------------------------------------------------
Ruled 2026-09-08 (`gates.py`, `Document.thread_subject_text`): on a platform
whose subject line is a separate record, the subject gate may resolve against
the thread root's text. **Nothing supplied it until this module.**

The root needs NO NEW STORAGE. `document.thread_root_id` already points at the
root's own `document` row, and that row already carries a `text_ref`, so the
subject text is `thread_root_id -> document.text_ref -> raw store -> the
platform's prose function`. Measured on staging 2026-09-08:

    source     children  thread_root_id set  root row resolves  distinct roots
    github         2016                2016               2016             584
    reddit         1420                1420                  0              24
    blog              0                   0                  0               0
    hackernews        0  -- NO HN DOCUMENT IS STORED ON THIS DATABASE

So the cost is one extra raw-store read **per distinct thread root**, not per
document - 584 reads for GitHub's 2,016 children, a ratio of 1:3.45 - plus one
`LEFT JOIN` on the primary key. `_root_text` caches per root within a run, so
the reads are the distinct count and not the child count.

⚠  AND `reddit` IS WHY A DANGLING ROOT IS COUNTED RATHER THAN READ AS ABSENT.
   All 1,420 Reddit children resolve to NOTHING, because two writers use two
   conventions for one column:

       reddit_write.py    thread_root_id = 't3_1v6a104'          bare fullname
       documents.py       thread_root_id = 'reddit:t3_1v6a104'   <source>:<id>

   Re-joined with the prefix added, all 1,420 resolve. The rows are there; the
   reference is not. That is a real defect and it is NOT repaired here - a
   repair rewrites 2,840 stored references and belongs in its own change - but
   it is the reason `root_unresolvable` is a counter with a name. A join that
   read a dangling id as "this document has no subject line" would report an
   absence we caused as one we found, on the exact platform where the count is
   largest.

`SUBJECT_FROM_THREAD_ROOT` holds the platforms the ruling covers. It is Hacker
News alone, and it is a frozenset here rather than in `contract/` on purpose:
this is not a threshold or a filter rule, it is the answer to "does this
platform put its subject line in another record", which is a platform-shape
fact the adapter knows and nobody tunes. Hugging Face discussions are next on
the same argument and are not in it.

⚠  GITHUB IS NOT IN IT EITHER, AND ITS 2,016 COMMENTS ARE IN THE SAME POSITION.
   A GitHub comment's payload is its `body` alone; the issue title lives in the
   parent row, exactly as an HN comment's story does. **HELD DELIBERATELY, not
   pending**: widening moves GitHub from 42.9% to 74.0% and inherits on 1,388
   documents, which is a change four times larger than the 511-comment
   two-thread measurement the Hacker News ruling was made on. The argument being
   identical in form is the reason it must not carry automatically.

   Put up for its own ruling in
   `docs/proposals/for-the-team-github-thread-subject-widening.md`, with the
   measurement of what those 1,388 documents would inherit: 231 of 459 roots
   resolve to exactly one model, 224 to two or more. That third option - widen
   only where the root is unambiguous, ~870 documents - is a predicate here and
   not an entry in the set above.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from collect.triage.gates import GATE_ORDER, Document, Verdict, triage

log = logging.getLogger(__name__)

#: Platforms whose SUBJECT LINE IS A SEPARATE RECORD, so the subject gate is
#: given the thread root's text. Ruled 2026-09-08, Hacker News alone. See the
#: module docstring on why this is not a `contract/` entry, and on why GitHub is
#: absent despite being the same shape.
SUBJECT_FROM_THREAD_ROOT = frozenset({"hackernews"})


def _prose_by_source() -> dict[str, tuple[object, bool]]:
    """source -> (the function that turns its payload into prose, wants_bytes).

    IMPORTED LAZILY, because `blog` needs `trafilatura` and the other seven do
    not - a module-level import would make every triage run depend on a parser
    library that `tests/test_lane_boundary.py` deliberately confines to one
    importer.

    NO FALLBACK, AND NO SNIFFER. An unmapped source raises rather than passing
    the payload through: `collect/assemble/prose.py` exists because a raw
    payload flattened verbatim let a quote verify against a FIELD VALUE while
    `quote_verified` reported true. The same passthrough here would make the
    entity gate resolve model names out of JSON keys and URLs.
    """
    from collect.adapters.blog.parse import extract_article_text
    from collect.assemble import prose

    def _blog(blob: bytes) -> str:
        """⚠ BLOG TAKES BYTES AND EVERY OTHER EXTRACTOR TAKES STR.

        Found by the first run, not by review: handing `store.get_text()` to
        `extract_article_text` refused all 120 readable blog documents through
        `_require_bytes`, and they landed in `not_prose` - a real count, with a
        cause that was ours rather than the corpus's. The bytes go over
        undecoded on purpose, because trafilatura's charset detection beats a
        guess made here and a mis-decoded article produces mojibake that
        verifies as a quote.

        `None` IS NOT AN EMPTY DOCUMENT. trafilatura returns None for a
        navigation page, a paywall stub or a JS shell, and
        `extract_article_text`'s own docstring says the caller must not turn
        that into an empty string - so it is raised as `NotAPayload` and lands
        in `not_prose`, where it is counted rather than gated as a short
        document with no artifact.
        """
        text = extract_article_text(blob)
        if text is None:
            raise prose.NotAPayload(
                "blog payload: trafilatura found no article body. A navigation "
                "page, a paywall stub or a JS shell - NOT an empty article."
            )
        return text

    #: ⚠ THE SECOND ELEMENT IS WHETHER THE EXTRACTOR WANTS RAW BYTES. Seven of
    #: the eight parse JSON and take `str`; blog hands HTML to trafilatura
    #: undecoded. Carried in the table rather than sniffed at the call site,
    #: because the first run silently refused every blog document by getting
    #: this wrong in the direction that looks like a corpus finding.
    return {
        "github": (prose.github_issue_prose, False),
        "reddit": (prose.reddit_prose, False),
        "blog": (_blog, True),
        "arxiv": (prose.arxiv_paper_prose, False),
        "devto": (prose.devto_article_prose, False),
        "hackernews": (prose.hackernews_prose, False),
        "huggingface": (prose.huggingface_prose, False),
        "x": (prose.x_post_prose, False),
    }


def _own_commentary(source: str, blob) -> str | None:
    """The POSTER'S OWN body, where the platform separates it. For `pure_link_post`.

    NOT A COLUMN, AND DELIBERATELY. `pure_link_post` needs two facts - is this a
    link post, and did the poster write anything themselves - and only the first
    is stored (`document.is_self_post`, 2026-09-08). The second is `selftext` /
    `text`: the payload's own body, which `text_ref` already addresses. Storing
    it would duplicate the payload and put derived bytes beside a hash that
    identifies the original, which is the ruling
    `collect/assemble/prose.py` exists to enforce. So it is read here, from the
    payload this function's caller has already parsed for prose.

    NOT THE PROSE. `reddit_prose` returns title + selftext joined, and a title
    is not commentary - reading it as one would make every link post look like
    it carried the poster's own words, which is precisely the gate's question.

    None where the platform has no such notion, which `pure_link_post` never
    reaches: it returns NOT_APPLICABLE on `is_self_post is None` first, and the
    two are absent together on every platform that has neither.
    """
    import json as _json

    if source not in ("reddit", "hackernews"):
        return None
    try:
        payload = _json.loads(blob if isinstance(blob, str) else blob.decode())
    except Exception:
        return None
    if source == "reddit":
        data = payload.get("data", payload)
        return data.get("selftext") if isinstance(data, dict) else None
    return payload.get("text")


#: The root is LEFT JOINed on the primary key, so a document whose root is not
#: stored comes back with `root_text_ref IS NULL` and is COUNTED - never read as
#: "no subject". `d.thread_root_id <> d.id` excludes a root pointing at itself:
#: a story anchor is its own root by convention (`hackernews.drafts`), and
#: handing a document its own text as its subject would make every root
#: self-inherit and the flag meaningless.
_SELECT = """
SELECT d.id, d.source, d.text_ref, d.created_at, d.lang, d.parent_id,
       d.thread_root_id, d.is_self_post,
       a.external_id AS author_external_id,
       r.text_ref    AS root_text_ref
FROM document d
LEFT JOIN author a ON a.id = d.author_id
LEFT JOIN document r
       ON r.id = d.thread_root_id
      AND d.thread_root_id <> d.id
      AND d.source = ANY(%(subject_sources)s)
WHERE d.triage_verdict IS NULL
  AND (%(sources)s::text[] IS NULL OR d.source = ANY(%(sources)s))
ORDER BY d.source, d.id
"""

#: `triage_verdict IS NULL` in the WHERE makes a second run a no-op, and the
#: re-check here makes two runs racing unable to half-write a row - the same
#: arrangement `collect/triage/store.py:_UPDATE` uses and for the same reason.
#:
#: ⚠ `status` IS ABSENT ON PURPOSE AND IS NOT AN OVERSIGHT. See the module
#:   docstring: two gates cannot run, so this is a recorded field and not a
#:   gate, and `status` is what `judge/` filters on.
_UPDATE = """
UPDATE document
SET triage_verdict = %(triage_verdict)s,
    filter_reasons = %(filter_reasons)s
WHERE id = %(id)s
  AND triage_verdict IS NULL
"""


@dataclass
class TriageStoreRun:
    """What one pass did, per source, with every denominator attached."""

    #: Rows with `triage_verdict IS NULL` when the pass started.
    eligible: int = 0
    #: Of those, rows whose prose this host could produce. THE DENOMINATOR for
    #: every rate below - the others were never gated and must not sit in one.
    triaged: int = 0
    kept: int = 0
    dropped: int = 0
    written: int = 0

    #: Payload absent from this raw store. NAMED, never gated as a drop: this
    #: host could not read the text, which is not a fact about the document.
    unreadable: int = 0
    #: Payload present and not prose - `NotAPayload`. A DIFFERENT FINDING from
    #: unreadable: the bytes are here and the extractor refused them, which is
    #: a provenance or shape problem and is repairable, where an absent payload
    #: on this host may just be another machine's raw store.
    not_prose: int = 0
    #: Source with no prose function. Refused rather than passed through.
    unmapped_source: int = 0

    #: Per source: {source: {counter: n}}. A per-platform pattern and a
    #: scattered one are different faults with different repairs.
    by_source: dict[str, dict[str, int]] = field(default_factory=dict)
    #: Drops by gate, over `triaged`.
    by_reason: dict[str, int] = field(default_factory=dict)
    #: Non-dropping observations, by name - `TriageResult.flags`. THE NUMBER
    #: THAT DECIDES WHETHER A JUDGEMENT BECOMES A GATE: what the check would
    #: have dropped, measured on documents it did not drop. Rule 8's evidence.
    #:
    #: ⚠ NOT STORED ON THE ROW. `filter_reasons` is why a document was DROPPED,
    #:   so a flag there would make a kept document carry a drop reason. There
    #:   is no column for a non-dropping observation today, which means these
    #:   counts live in the run report and in the measurement JSON and nowhere
    #:   queryable. Naming that rather than leaving it to be discovered: giving
    #:   flags a column is a `contract/` change nobody has proposed.
    by_flag: dict[str, int] = field(default_factory=dict)
    #: Gates that COULD NOT RUN, by name. Falls to empty as the build catches up.
    never_ran: dict[str, int] = field(default_factory=dict)
    #: Gates with NOTHING TO RUN ON. Grows with the corpus; not a regression.
    not_applicable: dict[str, int] = field(default_factory=dict)

    #: Documents whose subject came from their thread root.
    subject_inherited: int = 0
    #: Documents on a `SUBJECT_FROM_THREAD_ROOT` platform whose root text was
    #: wanted and could not be had. THE reddit-shaped counter - see the module
    #: docstring. An unresolvable root is not "no subject".
    root_unresolvable: int = 0
    #: Root text_ref resolved to a row and the PAYLOAD would not read.
    root_unreadable: int = 0

    population_fingerprint: str | None = None

    def _bump(self, source: str, counter: str, n: int = 1) -> None:
        self.by_source.setdefault(source, {})
        self.by_source[source][counter] = self.by_source[source].get(counter, 0) + n

    @property
    def survival(self) -> float | None:
        """Kept over TRIAGED, never over eligible. None on an empty pass."""
        return self.kept / self.triaged if self.triaged else None

    def describe(self) -> str:
        """The figures with their denominators and their holes (rules 4 and 7)."""
        if not self.triaged:
            return (
                f"eligible {self.eligible}, triaged 0 - NOTHING WAS GATED. "
                f"{self.unreadable} payloads absent from this raw store, "
                f"{self.not_prose} present and not prose, "
                f"{self.unmapped_source} from a source with no prose function."
            )
        lines = [
            f"triaged {self.triaged}/{self.eligible} eligible  "
            f"(population {self.population_fingerprint})",
            f"  kept {self.kept}/{self.triaged} = {100 * self.kept / self.triaged:.1f}%"
            f"   dropped {self.dropped}",
        ]
        for reason, count in sorted(self.by_reason.items(), key=lambda kv: -kv[1]):
            lines.append(
                f"    dropped {reason:<24} {count:>6}  "
                f"{100 * count / self.triaged:.1f}% of triaged"
            )

        if self.never_ran:
            missing = ", ".join(
                f"{g} ({n})"
                for g, n in sorted(self.never_ran.items(), key=lambda kv: -kv[1])
            )
            lines.append(
                f"  GATES THAT COULD NOT RUN: {missing}. THIS SURVIVAL RATE IS AN "
                "UPPER BOUND - documents these gates would have dropped are "
                "counted as kept. BUILDING THEM RESOLVES IT."
            )
        if self.not_applicable:
            na = ", ".join(
                f"{g} ({n})"
                for g, n in sorted(self.not_applicable.items(), key=lambda kv: -kv[1])
            )
            lines.append(
                f"  GATES WITH NOTHING TO RUN ON: {na}. Also an upper bound and a "
                "PERMANENT one - these documents lack the input."
            )

        if self.unreadable or self.not_prose or self.unmapped_source:
            lines.append(
                f"  NOT GATED AND NOT DROPPED: {self.unreadable} unreadable "
                f"payload(s), {self.not_prose} present-but-not-prose, "
                f"{self.unmapped_source} unmapped source. These are OUTSIDE the "
                "denominator above - they were never gated, so counting them as "
                "dropped would report our coverage as the corpus's quality."
            )
        for flag, count in sorted(self.by_flag.items(), key=lambda kv: -kv[1]):
            lines.append(
                f"  FLAGGED, NOT DROPPED: {flag} on {count} of {self.triaged} "
                f"triaged ({100 * count / self.triaged:.1f}%). Those documents "
                "were KEPT. This is what promoting the check to a gate would "
                "cost, measured on documents it did not drop - the evidence "
                "rule 8 asks for before a weight becomes a gate."
            )
        if self.subject_inherited:
            lines.append(
                f"  SUBJECT INHERITED FROM THE THREAD ROOT: "
                f"{self.subject_inherited} of {self.triaged}. Triaged at a "
                "DIFFERENT READING UNIT, so this survival figure is over a "
                "mixed population."
            )
        if self.root_unresolvable or self.root_unreadable:
            lines.append(
                f"  ⚠ THREAD ROOT WANTED AND NOT AVAILABLE: "
                f"{self.root_unresolvable} thread_root_id(s) resolve to no "
                f"stored row, {self.root_unreadable} resolve to a row whose "
                "payload would not read. These documents faced the subject gate "
                "ALONE, so a drop among them is an absence WE caused."
            )
        lines.append(f"  written {self.written}")
        return "\n".join(lines)

    def per_source_table(self) -> str:
        """One row per source. The figure the first run was asked for."""
        header = (
            f"{'source':<12}{'eligible':>9}{'triaged':>8}{'kept':>7}{'dropped':>8}"
            f"{'survival':>10}{'ungated':>9}"
        )
        lines = [header, "-" * len(header)]
        for source in sorted(self.by_source):
            counts = self.by_source[source]
            triaged = counts.get("triaged", 0)
            kept = counts.get("kept", 0)
            ungated = (
                counts.get("unreadable", 0)
                + counts.get("not_prose", 0)
                + counts.get("unmapped_source", 0)
            )
            rate = f"{100 * kept / triaged:.1f}%" if triaged else "n/a"
            lines.append(
                f"{source:<12}{counts.get('eligible', 0):>9}{triaged:>8}{kept:>7}"
                f"{counts.get('dropped', 0):>8}{rate:>10}{ungated:>9}"
            )
        return "\n".join(lines)


def triage_stored(
    conn,
    store,
    *,
    batch: int = 200,
    dry_run: bool = True,
    sources: tuple[str, ...] | None = None,
    subject_sources: frozenset[str] | None = None,
    in_window: dict[str, bool] | None = None,
    allowed_languages: frozenset[str] | None = None,
) -> TriageStoreRun:
    """Run all six gates over every document with no verdict, and record it.

    Args:
        conn: an open connection. Not opened here - the chain owns it and the
            ledger row wrapping the stage.
        store: a `RawStore`. Passed rather than constructed so a caller can
            point at another root without an environment variable.
        batch: documents gated, then written, per commit. Bounds what a crash
            loses AND how long the connection sits idle - `triage/store.py`
            records the run this cost when the server closed an idle socket.
        dry_run: gate and count, write nothing. **The default is True here and
            False in `score_unscored`, and the asymmetry is deliberate.** That
            one writes recorded fields nobody gates on; this one writes a
            verdict over 6,502 rows on a SHARED database, and CLAUDE.md's
            convention is that a staging write session is announced first. A
            caller that wants the write says so.
        sources: restrict to these, or None for every source.
        subject_sources: platforms whose subject gate reads the thread root.
            Defaults to `SUBJECT_FROM_THREAD_ROOT`, which the 2026-09-08 ruling
            scopes to Hacker News. **A PARAMETER SO A COUNTERFACTUAL IS
            REPRODUCIBLE RATHER THAN A MONKEYPATCH**: the question "what would
            widening this to GitHub's 2,016 comments cost" is answered by a run
            with a different value here, recorded beside the ruling's own run.
            Passing something wider does NOT widen the ruling - it measures
            what widening would do.
        in_window: `model_version.in_window`, per canonical id. Absent means
            UNKNOWN, never out (`out_of_window`).
        allowed_languages: None leaves `wrong_language` UNAVAILABLE, which is
            the honest state: no detector is installed.
    """
    from collect.assemble.prose import NotAPayload
    from collect.triage.bots import load_bot_list
    from collect.triage.store import registry_population

    extractors = _prose_by_source()
    # ONE registry read per run, through the one shared construction. Two
    # builders would be two chances to diverge, and a figure resolved against a
    # different surface set is not comparable to one that was not.
    population = registry_population(conn)

    # None, not an empty list. `known_bot` turns None into UNAVAILABLE, which is
    # what "nothing is curated" means; an empty list would claim the list exists
    # and declares no bots.
    bots = load_bot_list()
    if in_window is None:
        in_window = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT canonical_id, in_window FROM model_version "
                "WHERE in_window IS NOT NULL"
            ).fetchall()
        }

    if subject_sources is None:
        subject_sources = SUBJECT_FROM_THREAD_ROOT
    pending = conn.execute(
        _SELECT,
        {
            "subject_sources": list(subject_sources),
            "sources": list(sources) if sources else None,
        },
    ).fetchall()

    run = TriageStoreRun(
        eligible=len(pending), population_fingerprint=population.fingerprint
    )
    for row in pending:
        run._bump(row[1], "eligible")

    #: root document id -> its prose, or None where it would not read. Cached so
    #: the raw-store reads are the DISTINCT-root count and not the child count.
    root_cache: dict[str, str | None] = {}

    def _root_text(root_id: str, root_ref: str, source: str) -> str | None:
        if root_id in root_cache:
            return root_cache[root_id]
        text: str | None = None
        extractor, wants_bytes = extractors[source]
        try:
            blob = store.get(root_ref) if wants_bytes else store.get_text(root_ref)
            text = extractor(blob)
        except Exception:
            # COUNTED, not silently absent. A root whose payload will not read
            # leaves its children facing the subject gate alone, which is a
            # different state from a platform that has no subject line.
            run.root_unreadable += 1
            run._bump(source, "root_unreadable")
        root_cache[root_id] = text
        return text

    def _flush(rows: list[dict]) -> None:
        """`conn.commit()`, not `conn.transaction()`.

        `collect.db.connect` leaves autocommit off, so the SELECT above has
        already opened a transaction; `conn.transaction()` inside one opens a
        SAVEPOINT whose exit releases and commits nothing. That shape reported
        rows written and stored none - see `collect/triage/store.py:_flush`,
        which paid for the lesson.
        """
        if dry_run or not rows:
            return
        for record in rows:
            conn.execute(_UPDATE, record)
        conn.commit()
        run.written += len(rows)

    writes: list[dict] = []
    for (
        doc_id,
        source,
        text_ref,
        created_at,
        lang,
        parent_id,
        thread_root_id,
        is_self_post,
        author_external_id,
        root_text_ref,
    ) in pending:
        mapped = extractors.get(source)
        if mapped is None:
            run.unmapped_source += 1
            run._bump(source, "unmapped_source")
            continue
        extractor, wants_bytes = mapped
        try:
            blob = store.get(text_ref) if wants_bytes else store.get_text(text_ref)
        except Exception:
            run.unreadable += 1
            run._bump(source, "unreadable")
            continue
        try:
            text = extractor(blob)
        except NotAPayload:
            run.not_prose += 1
            run._bump(source, "not_prose")
            continue
        except Exception:
            # A parser that raised something else is still "the bytes are here
            # and did not become prose", and it is counted there rather than
            # crashing a 6,502-row pass on one malformed payload.
            run.not_prose += 1
            run._bump(source, "not_prose")
            continue

        subject_text: str | None = None
        if source in subject_sources and parent_id is not None:
            if root_text_ref is None:
                # The id is set and points at nothing stored. NAMED.
                if thread_root_id is not None:
                    run.root_unresolvable += 1
                    run._bump(source, "root_unresolvable")
            else:
                subject_text = _root_text(thread_root_id, root_text_ref, source)

        result = triage(
            Document(
                text=text,
                created_at=created_at.date() if created_at else None,
                lang=lang,
                source=source,
                author_external_id=author_external_id,
                # ⚠ BOTH SUPPLIED SINCE 2026-09-08, and neither was before.
                # This read "`is_self_post` and `body` are NOT reconstructed
                # from the row; neither is a column, so passing anything would
                # be inventing it" - true then, and `pure_link_post` returned
                # NOT_APPLICABLE on all 5,010 documents because of it.
                #
                # `is_self_post` is now a column, carrying the PLATFORM'S own
                # flag (backfilled from stored payloads by
                # `scripts/backfill_is_self_post.py`, never inferred). `body` is
                # read from the payload rather than stored - see
                # `_own_commentary` for why duplicating it would be wrong.
                #
                # A NULL `is_self_post` still means NOT_APPLICABLE, which is the
                # permanent and correct answer for a blog article, a GitHub
                # issue and a comment on any platform.
                is_self_post=is_self_post,
                body=_own_commentary(source, blob),
                thread_subject_text=subject_text,
            ),
            population=population,
            bots=bots,
            in_window=in_window,
            allowed_languages=allowed_languages,
        )

        run.triaged += 1
        run._bump(source, "triaged")
        if result.verdict is Verdict.KEPT:
            run.kept += 1
            run._bump(source, "kept")
        else:
            run.dropped += 1
            run._bump(source, "dropped")
        for reason in result.reasons:
            run.by_reason[reason] = run.by_reason.get(reason, 0) + 1
            run._bump(source, f"reason:{reason}")
        for flag in result.flags:
            run.by_flag[flag] = run.by_flag.get(flag, 0) + 1
            run._bump(source, f"flag:{flag}")
        for gate in result.unavailable:
            run.never_ran[gate] = run.never_ran.get(gate, 0) + 1
        for gate in result.not_applicable:
            run.not_applicable[gate] = run.not_applicable.get(gate, 0) + 1
        if result.subject_was_inherited:
            run.subject_inherited += 1
            run._bump(source, "subject_inherited")

        writes.append(
            {
                "id": doc_id,
                "triage_verdict": str(result.verdict),
                # None, not `[]`. An empty array asserts "gated and nothing
                # fired"; NULL on a kept row is the same absence every other
                # writer records, and `filter_reasons` has no NOT NULL.
                "filter_reasons": list(result.reasons) or None,
            }
        )
        if len(writes) >= batch:
            _flush(writes)
            writes = []
    _flush(writes)
    return run


def gate_availability(run: TriageStoreRun) -> str:
    """Which gates ran, which could not, and what each missing one needs.

    SEPARATE FROM `describe` BECAUSE IT IS THE QUESTION SOMEBODY ASKS FIRST.
    A survival figure is worthless without it, and "which gates could not run"
    has a different answer per gate WITH A DIFFERENT REMEDY - one needs a
    dependency decision, one needs a `contract/` file, one needs a column no
    writer sets.
    """
    needs = {
        "wrong-language": (
            "no detector is installed and none is declared in pyproject.toml. "
            "Adding one is a DEPENDENCY DECISION, not a line of code. "
            "`document.lang` is now written for platforms that declare one "
            "(un-reserved 2026-09-08) but is NULL on all 6,502 older rows, so "
            "even with a detector the gate has no input on the stored corpus"
        ),
        "known-bot": (
            "`contract/bots.yaml` does not exist. The DETECTOR is built "
            "(collect/triage/bots.py, 2026-09-07); the LIST is a contract "
            "change, proposed in docs/proposals/for-engineer-2-the-bot-list.md. "
            "Reports UNAVAILABLE per source, so this count shrinks platform by "
            "platform as each is curated"
        ),
        "pure-link-post": (
            "`is_self_post` and the poster's own commentary are not columns on "
            "`document`, so a stored row cannot answer this. NOT_APPLICABLE "
            "rather than UNAVAILABLE where the platform has no such notion at "
            "all - a blog article has no link-post flag and never will"
        ),
        "out-of-window": (
            "NOT_APPLICABLE where no matched surface has a known owner, or "
            "where owners disagree on the window flag. A property of the "
            "document, not of the build"
        ),
    }
    lines = ["GATES, AND WHAT EACH ONE ACTUALLY DID"]
    for gate in GATE_ORDER:
        never = run.never_ran.get(gate, 0)
        na = run.not_applicable.get(gate, 0)
        fired = run.by_reason.get(gate, 0)
        ran = run.triaged - never - na
        lines.append(
            f"  {gate:<24} ran on {ran:>5}/{run.triaged}  dropped {fired:>5}  "
            f"could-not-run {never:>5}  nothing-to-run-on {na:>5}"
        )
        if never or na:
            lines.append(f"      {needs.get(gate, 'see collect/triage/gates.py')}")
    return "\n".join(lines)
