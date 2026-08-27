"""The model page: what engineers report about one model, and what nobody has said.

FR-23, FR-24, FR-25, FR-26. This is the first page that renders a QUOTE, so it
carries every constraint the rest of the lane has been deferring.

FOUR THINGS THAT ARE NOT STYLE

1. SILENCE RENDERS DISTINCTLY FROM CRITICISM (FR-24, rule 4). A capability with
   no cell and a capability with a negative cell are opposite states, and a page
   listing only what it has evidence for shows them identically - as nothing.
   So the page enumerates the FULL capability list and says, per capability,
   which of three states it is in. That is why `unreported` is computed from
   `contract/capabilities.yaml` rather than from the rows returned.

2. CONDITIONS ARE PRESERVED, NEVER AVERAGED (FR-25). Cells arrive per
   `(capability, condition_bucket)` and stay that way. "Praised under 5 tools,
   two engineers report schema failures above 6" is the finding; averaging it
   publishes "mediocre", which is true-ish, useless, and buries the rule a
   reader would act on.

3. EVERY PHRASE IS BOUND TO ITS QUOTES (FR-26). `quote_ids` travels with the
   phrase in the same object. A page that renders `consensus_phrase` and drops
   `quote_ids` has produced an unfalsifiable claim, which is the one thing this
   product exists not to do.

4. THE QUOTE IS THE RAW SPAN (FR-23), and `claim.quote` already holds it -
   `judge/extract/verify.py` step 3 stores the raw text, never the normalised
   form, so `[upside_down_face]` cannot reach here. This page does no
   transformation of quote text at all, which is the only safe amount.

WHAT THIS PAGE CANNOT PROMISE

`judge/CLAUDE.md` records it and it belongs in front of whoever renders this:
a verified quote is exactly what we were GIVEN, not exactly what was
PUBLISHED. For Reddit those coincide. For blogs, trafilatura's decode sits
between, so a quote reading `>` may have been written `&gt;`. Recoverable from
the raw store, unchecked on the nightly path, and not this module's to fix -
but it is this module's to not overstate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from judge.config import capabilities


@dataclass(frozen=True)
class Quote:
    """One piece of evidence, as written.

    `polarity` says whether the engineer was praising or criticising — read
    straight from `claim.polarity`, never inferred here. `sign_disputed` is the
    read-time twin of the extraction guard (`ExtractedClaim.polarity_contradicts_pain`):
    a stored claim marked `positive` while carrying a `pain_point` contradicts
    itself, and the page must SAY SO rather than render a green "positive" that
    is lying. New extractions drop such claims; this flags the ones already
    stored before the guard existed, without silently rewriting the count a
    re-run would fix (rule 6 — surface the contradiction, do not convert it).
    """

    claim_id: str
    text: str
    permalink: str
    platform: str
    claimed_at: str | None = None
    polarity: str | None = None
    sign_disputed: bool = False


@dataclass(frozen=True)
class ConditionSlice:
    """One `(capability, condition_bucket)` cell, kept separate on purpose."""

    capability_key: str
    condition_bucket: str
    status: str
    consensus_phrase: str | None
    conditional_note: str | None
    independent_voices: int
    platform_count: int
    positive: int
    negative: int
    quote_ids: tuple[str, ...] = ()

    @property
    def publishes(self) -> bool:
        return self.status == "published"

    @property
    def is_bound_to_evidence(self) -> bool:
        """FR-26. A phrase with no quotes behind it is unfalsifiable.

        Checked rather than assumed: the phrase and the ids come from different
        columns, and a cell can carry one without the other.
        """
        return not self.consensus_phrase or bool(self.quote_ids)


@dataclass(frozen=True)
class CapabilityView:
    """One capability, in exactly one of three states.

    The three-state shape is FR-24 made structural. A page that models this as
    "cells I have" collapses `unreported` into `insufficient` and reports "no
    concerns" where the truth is "nobody has looked".
    """

    key: str
    failure_mode: str
    slices: tuple[ConditionSlice, ...] = ()

    @property
    def unreported(self) -> bool:
        """Nobody has said anything. NOT the same as nobody has complained."""
        return not self.slices

    @property
    def insufficient(self) -> bool:
        """Somebody has, and it does not yet clear the bar."""
        return bool(self.slices) and not any(s.publishes for s in self.slices)

    @property
    def needs_positive_consensus(self) -> bool:
        """A silent failure cannot be cleared by an absence of complaints.

        A summary quietly dropping a fact produces no error and no alert, so
        "nobody complained" is not evidence about it - only positive reports
        are.
        """
        return self.failure_mode == "silent"

    @property
    def headline(self) -> str:
        if self.unreported:
            if self.needs_positive_consensus:
                return (
                    "Nobody has reported on this. It fails silently, so an "
                    "absence of complaints is not reassurance - a failure here "
                    "would produce no error for anyone to report."
                )
            return "Nobody has reported on this."
        if self.insufficient:
            voices = sum(s.independent_voices for s in self.slices)
            return (
                f"{voices} {'person has' if voices == 1 else 'people have'} "
                f"reported on this, which is not yet enough to publish a finding."
            )
        return "; ".join(
            s.consensus_phrase for s in self.slices if s.publishes and s.consensus_phrase
        )


@dataclass(frozen=True)
class ModelPage:
    """One model, and the full capability list rather than the evidenced part."""

    model_version_id: str
    display_name: str
    capabilities: tuple[CapabilityView, ...] = ()
    quotes: dict[str, Quote] | None = None

    #: When this model was last SWEPT for evidence — `model_version.last_swept_at`.
    #: NULL means NEVER SWEPT, which is not "swept long ago" and not "no evidence
    #: found": it is "WE HAVE NOT LOOKED at this model" (#33 Q2). That is a third
    #: silence, distinct from the per-capability "nobody discussed this", and rule
    #: 4 says the two must render differently — "we never asked" and "nobody
    #: answered" are opposite claims about the world, and only one is about the
    #: model. Kept as the timestamp rather than a bool so a page can also say
    #: WHEN, and so `None` cannot be mistaken for `False`.
    swept_at: Any = None

    @property
    def tracked(self) -> bool:
        """Has this model been swept for evidence at all? The third-state test.

        `last_swept_at is None` -> never swept -> NOT TRACKED. Everything below on
        the page is then an absence of LOOKING, not an absence of findings.
        """
        return self.swept_at is not None

    @property
    def reported(self) -> tuple[CapabilityView, ...]:
        return tuple(c for c in self.capabilities if not c.unreported)

    @property
    def unreported(self) -> tuple[CapabilityView, ...]:
        return tuple(c for c in self.capabilities if c.unreported)

    @property
    def silent_and_unreported(self) -> tuple[CapabilityView, ...]:
        """The most dangerous cell on the page, and it is an empty one.

        A silent-failure capability nobody has discussed is where a reader is
        most likely to assume safety from an absence.
        """
        return tuple(c for c in self.unreported if c.needs_positive_consensus)

    @property
    def summary(self) -> str:
        """Rule 7: the counts carry the list they were drawn from.

        And rule 4 at the MODEL level: an untracked model leads with WHY it is
        empty. "0 of 12 have reports" on a model nobody has swept reads as "we
        looked and found nothing" — the exact conflation #33 Q2 ruled against. So
        the not-tracked caveat comes first, because it changes what every figure
        after it means.
        """
        total = len(self.capabilities)
        reported = len(self.reported)
        if not total:
            return "No capability list is loaded, so this page is not a finding."
        if not self.tracked:
            return (
                "This model has NOT been swept for evidence — nobody has looked at "
                "it yet. The capabilities below are empty because we have not "
                f"asked, not because engineers reported no problems. All {total} "
                "read as not-yet-looked-at rather than as a clean bill of health."
            )
        body = f"{reported} of {total} tracked capabilities have any reports at all."
        silent = len(self.silent_and_unreported)
        if silent:
            body += (
                f" {silent} of the {total - reported} unreported "
                f"{'fails' if silent == 1 else 'fail'} silently, where an "
                f"absence of complaints is not evidence of safety."
            )
        return body

    def unbound_phrases(self) -> tuple[ConditionSlice, ...]:
        """FR-26's check, surfaced rather than trusted.

        Any published slice whose phrase has no quote ids behind it. Returned
        so a caller can refuse to render rather than discovering it visually.
        """
        return tuple(
            s
            for c in self.capabilities
            for s in c.slices
            if s.publishes and not s.is_bound_to_evidence
        )


class ModelPageReader:
    """Reads `cell` and `claim`. Writes nothing."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def build(self, model_version_id: str, *, display_name: str = "") -> ModelPage:
        rows = self._conn.execute(
            """
            SELECT capability_key, condition_bucket, status, consensus_phrase,
                   conditional_note, independent_voices, platform_count,
                   positive, negative, quote_ids
            FROM cell
            WHERE model_version_id = %s
            ORDER BY capability_key, condition_bucket
            """,
            (model_version_id,),
        ).fetchall()

        by_capability: dict[str, list[ConditionSlice]] = {}
        for r in rows:
            by_capability.setdefault(r[0], []).append(
                ConditionSlice(
                    capability_key=r[0],
                    condition_bucket=r[1],
                    status=r[2],
                    consensus_phrase=r[3],
                    conditional_note=r[4],
                    independent_voices=r[5],
                    platform_count=r[6],
                    positive=r[7],
                    negative=r[8],
                    quote_ids=tuple(r[9] or ()),
                )
            )

        # THE FULL LIST, not the rows returned. This is FR-24: a capability
        # missing from `cell` must appear here as "nobody has reported", and
        # iterating the query result cannot produce a row that does not exist.
        views = tuple(
            CapabilityView(
                key=key,
                failure_mode=capability.failure_mode,
                slices=tuple(by_capability.get(key, ())),
            )
            for key, capability in sorted(capabilities().items())
        )
        # WHETHER WE HAVE LOOKED AT THIS MODEL (#33 Q2). `model_version` is
        # collect/'s table; this reads it, exactly as this lane already reads
        # `document` and `thread_context`. NULL `last_swept_at` is never-swept —
        # the third silence — and `_conn.execute` returning no row at all (a
        # model id the registry does not carry) is treated the same: not looked
        # at, rather than invented as swept.
        swept_row = self._conn.execute(
            "SELECT last_swept_at FROM model_version WHERE id = %s",
            (model_version_id,),
        ).fetchone()
        swept_at = swept_row[0] if swept_row else None

        return ModelPage(
            model_version_id=model_version_id,
            display_name=display_name or model_version_id,
            capabilities=views,
            swept_at=swept_at,
        )

    def quotes_for(self, claim_ids: tuple[str, ...]) -> dict[str, Quote]:
        """The raw spans behind a phrase.

        `claim.quote` already holds the raw text - `verify.py` step 3 stores it
        that way - so this does no transformation, which is the only safe
        amount to do to a verbatim quote.

        `quote_verified` is in the WHERE clause even though a CHECK enforces
        it. The CHECK protects the table; this protects the page against a
        future path that writes around it, and costs one predicate.

        `claimed_at` IS `document.created_at`, WHICH IS NOT `claim.created_at`.
        This selected `c.claim_date` — a column that has never existed on
        `claim` — so the page raised `UndefinedColumn` the first time a cell
        had a quote to show, which was the first time any claim was stored.

        The near-miss is the point: `claim.created_at` exists, would have run,
        and is the moment WE EXTRACTED, not the moment somebody wrote the
        sentence. Every quote would have rendered as fresh, the recency the
        weighting decays would disagree with the date on the page, and it fails
        in the flattering direction. The date a claim was made lives on the
        document, and `Pipeline.run` already weights from exactly that field.
        """
        if not claim_ids:
            return {}
        # `d.created_at`, not `c.claim_date`. There is no `claim_date` column -
        # the name is a PYTHON one, a field on StoredClaim and a parameter to
        # weight.recency_factor, and `pipeline.py` sets it from
        # `document.created_at` at both call sites. This query read it as though
        # it were on the table and raised UndefinedColumn.
        #
        # It survived because `quotes_for` is only reached when a cell HAS quote
        # ids, and there were no cells until the first pipeline run. The whole
        # branch was unreachable, so every test of this page exercised the empty
        # case and passed. The first model page with evidence on it 500ed.
        #
        # And `d.created_at` is the right column rather than the near-miss:
        # `claimed_at` is when the PERSON said it, which is the document's date.
        # `c.created_at` is when we extracted it, which is a fact about our
        # batch schedule and would age every quote to the day we ran.
        rows = self._conn.execute(
            """
            SELECT c.id, c.quote, d.url, d.source, d.created_at,
                   c.polarity, c.pain_points
            FROM claim c JOIN document d ON d.id = c.document_id
            WHERE c.id = ANY(%s) AND c.quote_verified
            """,
            (list(claim_ids),),
        ).fetchall()
        return {
            r[0]: Quote(
                claim_id=r[0],
                text=r[1],
                permalink=r[2],
                platform=r[3],
                claimed_at=str(r[4]) if r[4] else None,
                polarity=r[5],
                # The same contradiction the extraction guard now discards, read
                # off a row stored before it existed: a pain point present while
                # the sign is anything but negative (positive or neutral).
                sign_disputed=(bool(r[6]) and r[5] != "negative"),
            )
            for r in rows
        }
