"""/filtered — every document we threw away, and the rule that threw it.

FR-18. A filter you cannot inspect cannot be trusted, and this audience will
audit it. So a rejected document stays in the database and appears here with
its trigger NAMED, not summarised as "removed for policy reasons". A reader who
disagrees with a specific rule can then disagree with that rule, rather than
with our judgement in general.

THE STATUS THAT MUST NEVER APPEAR HERE

`document.status` has four values and only two belong on this page.

    kept        not filtered; belongs on the board, not here
    filtered    dropped by triage
    rejected    hard-rejected by judge/vet/reject.py
    tombstoned  A DELETION HONOURED. NEVER DISPLAY.

`tombstoned` is NFR-6: "tombstone a document; its quotes vanish next run, only
the content hash remains". Rendering one would republish the thing somebody
asked us to delete, and it would do it on the page whose whole argument is that
we are being transparent. The exclusion is in the query and asserted in a test,
because a later "show everything we filtered" refactor is exactly the helpful
change that would undo it.

AN UNEXPLAINED REJECTION IS SHOWN, NOT HIDDEN

A document with `status = 'rejected'` and no `filter_reasons` is a defect: we
discarded somebody's writing and cannot say why. The tempting handling is to
omit it, since it has nothing to display - and that would make the page's
completeness claim false in the direction that flatters us, hiding our worst
rows on the page that exists to show them.

So it appears, labelled. Rule 6 on a page rather than in a store: a missing
reason stays missing and visible, and never becomes a plausible one.

RULE 7

"12 documents rejected" is not a claim. "12 of 1,297 documents" is, and the
difference decides whether the filter looks reasonable or looks like a purge.
Every count here carries its denominator or it is not reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from judge.vet.reject import RejectionTrigger

#: The only statuses this page may render. `tombstoned` is absent on purpose
#: and `kept` is absent because it is not filtered.
DISPLAYABLE = ("filtered", "rejected")

#: Never rendered, under any option this module offers. Named as a constant so
#: the test asserting its absence has something to assert against, rather than
#: a string that a refactor could quietly change in both places at once.
NEVER_DISPLAYED = "tombstoned"


@dataclass(frozen=True)
class FilteredDocument:
    """One discarded document, and why."""

    document_id: str
    url: str
    source: str
    status: str
    reasons: tuple[str, ...]
    filtered_at: datetime | None

    @property
    def explained(self) -> bool:
        """False means we discarded this and cannot say why."""
        return bool(self.reasons)

    @property
    def triggers(self) -> tuple[tuple[str, str], ...]:
        """Each reason paired with its explanation.

        A reason string that is not a known `RejectionTrigger` is SURFACED with
        its raw value rather than dropped. A rule that fires under a name this
        page does not recognise is the most important thing on the page - it is
        a filter running that nobody is reviewing - and dropping it would make
        the document look explained by whatever else it carried.
        """
        out: list[tuple[str, str]] = []
        for reason in self.reasons:
            try:
                out.append((reason, RejectionTrigger(reason).explain()))
            except ValueError:
                out.append(
                    (
                        reason,
                        "This rule is not one this page knows about. It fired, "
                        "and nobody has written down what it means.",
                    )
                )
        return tuple(out)

    @property
    def headline(self) -> str:
        if not self.explained:
            return (
                "Discarded with no reason recorded. This is a defect in our "
                "pipeline, not a judgement about the document."
            )
        return ", ".join(reason for reason, _ in self.triggers)


@dataclass(frozen=True)
class FilteredReport:
    """What was filtered, against what it was filtered from."""

    documents: tuple[FilteredDocument, ...] = ()

    #: The population. `None` means it was not counted, and the summary then
    #: refuses to quote a rate rather than quoting one against an assumed
    #: denominator (rules 6 and 7 together).
    total_documents: int | None = None

    #: How many are filtered IN TOTAL, against however many this page is
    #: showing. Separate from `len(documents)` because `report(limit=...)`
    #: truncates, and a page showing 200 of 900 while saying "200 filtered"
    #: under-reports its own filter by a factor of four.
    #:
    #: The coverage page had this same defect and it was fixed there first: a
    #: cap is only honest when it is stated. `None` means uncounted.
    total_filtered: int | None = None

    @property
    def truncated(self) -> bool:
        return self.total_filtered is not None and self.total_filtered > len(self.documents)

    @property
    def unexplained(self) -> tuple[FilteredDocument, ...]:
        return tuple(d for d in self.documents if not d.explained)

    @property
    def unknown_rules(self) -> tuple[str, ...]:
        """Reason strings no `RejectionTrigger` matches, deduplicated."""
        known = {t.value for t in RejectionTrigger}
        seen = {r for d in self.documents for r in d.reasons if r not in known}
        return tuple(sorted(seen))

    @property
    def summary(self) -> str:
        # The FULL count, never the shown count. Reporting the page size as the
        # finding is the silent-cap failure.
        n = self.total_filtered if self.total_filtered is not None else len(self.documents)
        if self.total_documents is None:
            # No denominator, so no rate. "12 rejected" alone invites a reader
            # to supply their own population, and every population they might
            # guess is wrong.
            body = (
                f"{n} {'document' if n == 1 else 'documents'} filtered. The total "
                f"number of documents was not counted, so this is not a rate."
            )
        else:
            share = (n / self.total_documents) if self.total_documents else 0.0
            body = (
                f"{n} of {self.total_documents} "
                f"{'document' if self.total_documents == 1 else 'documents'} "
                f"filtered ({share:.1%})."
            )

        if self.truncated:
            body += f" Showing the {len(self.documents)} most recent."

        # `unexplained` and `unknown_rules` are computed over the SHOWN
        # documents, so on a truncated page they are page figures rather than
        # population figures. Saying "1 carry no reason" under "900 filtered"
        # states a fact about 200 rows in a sentence about 900 - rule 7 with
        # the denominator silently swapped, which is the failure this project
        # keeps finding. So the scope is named whenever it is not the whole.
        shown = len(self.documents)
        if self.unexplained:
            n_bad = len(self.unexplained)
            verb = "carries" if n_bad == 1 else "carry"
            lead = f"Of the {shown} shown, {n_bad}" if self.truncated else f"{n_bad}"
            body += (
                f" {lead} {verb} no reason at all, which is a defect in the "
                f"filter rather than a fact about the documents."
            )
        if self.unknown_rules:
            n_rules = len(self.unknown_rules)
            noun, names = ("rule", "a name") if n_rules == 1 else ("rules", "names")
            lead = f"Among the {shown} shown, {n_rules}" if self.truncated else f"{n_rules}"
            body += (
                f" {lead} {noun} fired under {names} this page does not "
                f"recognise: {', '.join(self.unknown_rules)}."
            )
        return body


class FilteredPage:
    """Reads `document`. Writes nothing."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def report(self, *, limit: int = 200) -> FilteredReport:
        rows = self._conn.execute(
            """
            SELECT id, url, source, status, filter_reasons, fetched_at
            FROM document
            WHERE status = ANY(%s)
            ORDER BY fetched_at DESC
            LIMIT %s
            """,
            (list(DISPLAYABLE), limit),
        ).fetchall()

        total_row = self._conn.execute(
            "SELECT count(*) FROM document WHERE status <> %s", (NEVER_DISPLAYED,)
        ).fetchone()
        filtered_row = self._conn.execute(
            "SELECT count(*) FROM document WHERE status = ANY(%s)", (list(DISPLAYABLE),)
        ).fetchone()

        return FilteredReport(
            documents=tuple(
                FilteredDocument(
                    document_id=r[0],
                    url=r[1],
                    source=r[2],
                    status=r[3],
                    reasons=tuple(r[4] or ()),
                    filtered_at=r[5],
                )
                for r in rows
            ),
            total_documents=total_row[0] if total_row else None,
            total_filtered=filtered_row[0] if filtered_row else None,
        )
