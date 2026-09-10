"""E3 for the five platforms added 2026-09-07/09. One driver, not five.

WHY THIS EXISTS
---------------
The five adapters wrote `document` rows and NOTHING assembled them. GitHub and
Reddit each had a batch driver; arXiv, dev.to, Hacker News, Hugging Face and X
had none, so their documents never became a `thread_context`, never reached
extraction, and produced no claims. The harvest ran, cost requests, and could not
reach the board — the most expensive kind of gap, because every stage reported
success.

ONE DRIVER BECAUSE THEY SHARE A WRITER. All five go through
`collect/adapters/documents.py`, so their rows agree on `source`,
`thread_root_id` and `text_ref`. Five copies of one loop is five places for the
next change to be applied four times.

THE TWO SHAPES, AND WHY THE CHOICE IS MADE FROM THE DATA
--------------------------------------------------------
    thread-of-one   a paper, an article. No children exist, so `assemble_article`
                    is right and `assemble` would rank an empty list.
    a real thread   an HN story, a HF discussion, an X post with replies. The
                    replies are the point — on Hacker News the correction two
                    levels down is usually the claim worth having — so these go
                    through `assemble`, which ranks children by specificity.

The shape is decided by WHETHER CHILDREN EXIST IN THE DATABASE, never by which
platform it came from. A Hugging Face discussion with no replies is a
thread-of-one and is assembled as one; hard-coding "huggingface is threaded"
would produce a thread claiming children it does not have.

WHAT IT REFUSES, AND SAYS SO
----------------------------
A document whose `text_ref` does not resolve in the store is NAMED in the report
rather than skipped. Reassembly reads from the store, so a missing payload is a
missing document — and a driver that silently drops them reports a smaller
corpus as a complete one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The platforms this driver serves. Reddit and GitHub are absent on purpose:
#: each has its own driver with platform-specific prose extraction and ranking,
#: and folding them in here would mean re-deriving rules that are already
#: settled elsewhere.
PLATFORMS = ("arxiv", "devto", "hackernews", "huggingface", "x")


@dataclass
class _Member:
    """A child, in the shape `assemble` structurally expects."""

    external_id: str
    body: str
    score: int | None = None


@dataclass
class _Coverage:
    """What the fetch SAW versus what exists.

    All three default to the honest unknown rather than to zero. `observed_children`
    is what we actually pulled; `hidden_children_min` is a FLOOR on what we did
    not, taken from the platform's own count where it publishes one. A zero here
    would claim complete coverage of a thread we paged once.
    """

    observed_children: int = 0
    hidden_children_min: int = 0
    #: A COUNT of branches whose size is unknown, not a flag. The column is
    #: `int` and Reddit's `ThreadCoverage` declares it `int` for a reason the
    #: module docstring gives: it lets a cell say "at least 340 hidden across
    #: 126 branches, PLUS 126 branches of unknown size" rather than collapsing a
    #: measurement and a floor into one number.
    #:
    #: Declared `bool` here, which made every Hacker News and Hugging Face
    #: assembly fail with `column "hidden_branches_unsized" is of type integer
    #: but expression is of type boolean` — 162 of 200 documents on the
    #: 2026-09-10 run never became a thread_context.
    hidden_branches_unsized: int = 1


@dataclass
class _Thread:
    """A thread, in the shape `assemble` structurally expects."""

    root_post_id: str | None
    comments: tuple
    coverage: _Coverage


@dataclass
class PlatformAssemblyReport:
    source: str = ""
    roots: int = 0
    assembled: int = 0
    as_article: int = 0
    as_thread: int = 0
    refusals: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [
            f"{self.assembled}/{self.roots} assembled",
            f"{self.as_thread} thread(s)",
            f"{self.as_article} single(s)",
        ]
        if self.refusals:
            parts.append(f"{len(self.refusals)} refused")
        return ", ".join(parts)


def _version_aliases(conn) -> dict:
    """Alias surfaces per model version, for child specificity ranking.

    Read once per run rather than per thread: it is the same table every time and
    a per-thread read turns one query into one per root.
    """
    rows = conn.execute(
        "SELECT model_version_id, surface FROM model_alias "
        "WHERE valid_until IS NULL"
    ).fetchall()
    out: dict[str, set] = {}
    for mv_id, surface in rows:
        out.setdefault(mv_id, set()).add(surface)
    return out


def assemble_platform_documents(
    conn, *, source: str, store, limit: int | None = None
) -> PlatformAssemblyReport:
    """Assemble every stored root for `source` that has no `thread_context` yet.

    Selected by the ABSENCE of a context on the ROOT, so a re-run is a no-op —
    and `write_thread_context` is `ON CONFLICT DO NOTHING`, which makes that safe
    rather than merely tidy.
    """
    from collect.assemble import prose
    from collect.assemble.article import ArticleInput, assemble_article
    from collect.assemble.thread import assemble, write_thread_context
    from collect.rawstore_reader import RawStoreReader

    reader = RawStoreReader(store)
    report = PlatformAssemblyReport(source=source)

    roots = conn.execute(
        "SELECT d.id, d.external_id, d.url, d.text_ref, d.engagement "
        "FROM document d "
        "WHERE d.source = %s "
        # `status`, NOT `triage_verdict`. E4 writes the verdict as a RECORDED
        # FIELD and not a gate, deliberately: two of its six checks cannot run
        # (no language detector, no contract/bots.yaml) and its error rate has
        # never been measured against a pool it did not choose. Rule 8 - an
        # unmeasured check ships as a weight, never a gate - because a wrong
        # gate's false positives are invisible: it drops the document, and an
        # absence we caused reads as one we found. `status` is what judge/
        # filters on and what carries the index; promotion of the verdict to a
        # gate goes on measured evidence, not on it being available.
        "  AND d.status = 'kept' "
        # A ROOT IS EITHER UNPARENTED OR ITS OWN PARENT, and the second form is
        # not a curiosity - it is what Hacker News writes. Reddit and dev.to
        # leave a root's `thread_root_id` NULL; the HN adapter sets a story's
        # thread root to the story itself, so a first real run harvested 127 HN
        # documents and assembled 0 of them. Nothing failed: the query asked for
        # NULL, found none, and reported "0/0 assembled" - a shape that reads
        # exactly like a platform nobody had posted on.
        "  AND (d.thread_root_id IS NULL OR d.thread_root_id = d.id) "
        "  AND NOT EXISTS (SELECT 1 FROM thread_context tc WHERE tc.thread_root_id = d.id) "
        "ORDER BY d.id"
        + (f" LIMIT {int(limit)}" if limit else ""),
        (source,),
    ).fetchall()
    report.roots = len(roots)
    if not roots:
        return report

    aliases = _version_aliases(conn)

    for root_id, _root_external, root_url, root_text_ref, root_engagement in roots:
        if not root_text_ref:
            report.refusals.append(
                f"{root_id}: no text_ref, so there is no root body to flatten. "
                "The row exists and its text does not."
            )
            continue
        root_outcome = reader.resolve(root_text_ref)
        if not root_outcome.found:
            report.refusals.append(
                f"{root_id}: root body {root_text_ref} did not resolve in the "
                f"store ({root_outcome.outcome}). Reassembly reads from the "
                "store, so a missing payload is a missing document."
            )
            continue

        # PROSE, NOT THE PAYLOAD. This file flattened `reader.resolve(...)`
        # VERBATIM and had no reference to `prose` at all, so every
        # thread_context it built held raw JSON - `{"author":"...","children":
        # [{...,"text":"..."}]}` - and the classifier read field names, ids and
        # HTML entities as if they were what somebody wrote. A quote of a
        # `"text"` field value then verifies by exact substring, so
        # `quote_verified` reports TRUE for the wrong reason: rule 1 satisfied
        # with no symptom anywhere.
        #
        # `assemble/issue.py` documents this happening once already, to 80
        # github contexts, and `assemble/reddit.py` carries the same fix with
        # the note that it must RAISE rather than fall back - "that fallback is
        # the defect this line exists to fix".
        extract = prose.for_source(source)
        if extract is None:
            report.refusals.append(
                f"{root_id}: no prose extractor is mapped for source {source!r}. "
                "Refused rather than flattened verbatim, which would let a quote "
                "verify against a JSON field value."
            )
            continue
        try:
            root_body = extract(root_outcome.require())
        except Exception as exc:
            report.refusals.append(
                f"{root_id}: root payload refused by the {source} prose extractor "
                f"({str(exc).splitlines()[0][:120]}); the thread was not built."
            )
            continue
        # THE EXTRACTED PROSE, not the payload. `root_text` feeds the
        # single-document path and the thread's first member, so a payload here
        # is a payload in front of the model.
        root_text = root_body

        # Children are keyed by the ROOT'S DOCUMENT ID, because the shared writer
        # converts the platform's thread-root id into a document id before it
        # writes. Querying the external id here would silently match nothing and
        # turn every thread into a single.
        child_rows = conn.execute(
            "SELECT id, external_id, text_ref, engagement FROM document "
            # Children are gated on `status` too: a bot comment the ADAPTER
            # already filtered is still a bot comment, and flattening it puts it
            # in front of the model. Doing it HERE keeps the offset_map honest,
            # since the map is built over exactly what gets flattened.
            # `id <> %s` EXCLUDES THE ROOT FROM ITS OWN CHILDREN. Needed only
            # because of the self-referential form above: without it an HN story
            # would be flattened twice, once as the root and once as a child of
            # itself, and the same text would reach the model under two ids -
            # one author counted as two voices.
            "WHERE source = %s AND thread_root_id = %s AND id <> %s "
            "  AND status = 'kept' "
            "ORDER BY id",
            (source, root_id, root_id),
        ).fetchall()

        members: list[_Member] = []
        child_ids: dict[str, str] = {}
        for child_id, external_id, text_ref, engagement in child_rows:
            if not text_ref:
                continue
            body_outcome = reader.resolve(text_ref)
            if not body_outcome.found:
                # NAMED, not silently dropped: a comment we can count but cannot
                # read is a different fact from one that is not there.
                report.refusals.append(
                    f"{root_id}: child {external_id} body {text_ref} did not "
                    f"resolve ({body_outcome.outcome}); excluded from flattening."
                )
                continue
            # Same extraction as the root, and the same refusal. A member whose
            # payload its own extractor rejects is EXCLUDED and named - it is a
            # comment we can count but not read, which is a different fact from
            # one that is not there.
            try:
                child_body = extract(body_outcome.require())
            except Exception as exc:
                report.refusals.append(
                    f"{root_id}: child {external_id} payload refused by the "
                    f"{source} prose extractor "
                    f"({str(exc).splitlines()[0][:120]}); excluded from flattening."
                )
                continue
            score = (engagement or {}).get("score")
            members.append(
                _Member(external_id=external_id, body=child_body,
                        score=int(score) if isinstance(score, (int, float)) else None)
            )
            child_ids[external_id] = child_id

        try:
            if members:
                # The platform's own child count, where it published one. The
                # point of the coverage columns is the GAP between what exists
                # and what we fetched, so our own tally is the wrong side of it.
                stated = (root_engagement or {}).get("comments")
                stated = int(stated) if isinstance(stated, (int, float)) else 0
                assembled = assemble(
                    _Thread(
                        root_post_id=root_id,
                        comments=tuple(members),
                        coverage=_Coverage(
                            observed_children=len(members),
                            hidden_children_min=max(0, stated - len(members)),
                            # THESE PLATFORMS HAVE NO BRANCH STRUCTURE - a flat
                            # member list, not a tree. So the count is 1 when the
                            # platform stated no total (the thread is itself one
                            # branch of unknown size) and 0 when it did.
                            hidden_branches_unsized=1 if stated <= 0 else 0,
                        ),
                    ),
                    root_text=root_text,
                    root_document_id=root_id,
                    child_document_id=(lambda m, _ids=child_ids: _ids[m.external_id]),
                    store=store,
                    version_aliases=aliases,
                )
                report.as_thread += 1
            else:
                assembled = assemble_article(
                    ArticleInput(entry_id=root_id, text=root_text, url=root_url),
                    store=store,
                    document_id=root_id,
                )
                report.as_article += 1
        except Exception as exc:  # one bad root must not end the batch
            report.refusals.append(f"{root_id}: {str(exc).splitlines()[0][:160]}")
            continue

        write_thread_context(conn, assembled)
        report.assembled += 1

    return report


def assemble_all_platforms(
    conn, *, store, limit: int | None = None
) -> list[PlatformAssemblyReport]:
    """Every platform this driver serves, each reported separately.

    Separately because a platform that assembled nothing and a platform that was
    not tried look identical in a combined total, and the first is a defect while
    the second is a configuration.
    """
    return [
        assemble_platform_documents(conn, source=source, store=store, limit=limit)
        for source in PLATFORMS
    ]
