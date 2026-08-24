"""The answer path's memory: what was asked, what we said, and what happened.

    task_profile   what they described, and what we guessed
    role           one job inside it - where the money multiplies
    answer         what we said, INCLUDING what we rejected
    outcome        whether it held

WHY REJECTED CANDIDATES ARE STORED, WHICH IS THE WHOLE DESIGN

FR-36 makes *"why not X?"* a first-class query. It is answerable only if the
answer remembers X. Storing the winner alone makes every such question a
re-computation against today's cells - which have moved - so the honest reply
would be "here is what I would say now", not "here is why I said that".

Those are different answers and only the second is accountable. So `candidates`
carries every model considered, with the band it landed in and the reason it
did, and a rejection is a row rather than an absence.

AN ABSTENTION IS A RESULT

`abstained` is not a failure to answer. FR-35 requires the advisor to decline
when the evidence will not carry a recommendation, and to NAME the capability
that lacks it. An abstention with no named gap is indistinguishable from a
broken query, so `reason` is required whenever `abstained` is true - checked
here rather than hoped for.

EVERY JUSTIFICATION IS BOUND TO A QUOTE

FR-34. The sentence explaining a pick carries the quote ids it rests on, in
the same object, for the reason the model page does it: a justification whose
evidence lives elsewhere is a justification somebody renders without evidence.
This is precisely where a model would otherwise invent a persuasive rationale,
and nothing here calls a model at all.

`outcome` IS THE ONLY THING THAT DECIDES WHETHER THIS PRODUCT WORKS

Roster completeness and quote fidelity are non-negotiable, but they are
hygiene. The question that decides whether any of it was worth building is
whether adopted recommendations held, and that answer only exists if somebody
writes it down.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from judge.store.claims import PIPELINE_VERSION


def _derived_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class Candidate:
    """One model considered, whether or not it was recommended.

    A REJECTED CANDIDATE IS A ROW. FR-36's "why not X?" reads this, and it
    cannot read a model that was filtered out before anything was written.
    """

    model_version_id: str
    band: str  # recommended | qualified | rejected | no_evidence
    reason: str
    cost_per_task: float | None = None

    #: FR-34. The quotes this reason rests on, beside the reason itself.
    quote_ids: tuple[str, ...] = ()

    @property
    def is_justified(self) -> bool:
        """A rejection ON EVIDENCE needs quotes. One on absence does not.

        The distinction matters: "engineers report it failing" and "nobody has
        reported on it" are opposite rejections, and only the first has
        anything to cite. Collapsing them would either demand quotes that
        cannot exist or accept a claim with none.
        """
        if self.band == "no_evidence":
            return True
        return bool(self.quote_ids) or not self.reason


@dataclass(frozen=True)
class Answer:
    """What we said about one role."""

    role_id: str
    candidates: tuple[Candidate, ...] = ()
    abstained: bool = False
    reason: str | None = None
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.abstained and not (self.reason or "").strip():
            raise ValueError(
                "an abstention must name what is missing. FR-35 requires the "
                "capability that lacks evidence, and an abstention with no "
                "reason is indistinguishable from a broken query."
            )
        if not self.abstained and not self.candidates:
            raise ValueError(
                "a non-abstaining answer with no candidates says nothing and "
                "claims to have answered. Abstain instead, and say why."
            )

    @property
    def answer_id(self) -> str:
        return _derived_id("ans", self.role_id, PIPELINE_VERSION)

    @property
    def recommended(self) -> tuple[Candidate, ...]:
        return tuple(c for c in self.candidates if c.band == "recommended")

    @property
    def rejected(self) -> tuple[Candidate, ...]:
        """Kept, not discarded. FR-36 reads these."""
        return tuple(c for c in self.candidates if c.band == "rejected")

    @property
    def unevidenced(self) -> tuple[Candidate, ...]:
        """Shown in their own section, never mixed into the ranking.

        Hiding unproven models makes the board conservative in a way that
        quietly costs money - they are disproportionately the cheap ones.
        """
        return tuple(c for c in self.candidates if c.band == "no_evidence")

    def unjustified(self) -> tuple[Candidate, ...]:
        """Candidates asserting something with no quote behind it (FR-34)."""
        return tuple(c for c in self.candidates if not c.is_justified)

    def why_not(self, model_version_id: str) -> Candidate | None:
        """FR-36, answerable because the rejection was stored.

        Returns None only when the model was never considered - which is a
        different answer from "considered and rejected", and the caller must
        be able to tell them apart.
        """
        for candidate in self.candidates:
            if candidate.model_version_id == model_version_id:
                return candidate
        return None


class AnswerStore:
    """Writes `task_profile`, `role`, `answer`, `outcome`. Never commits."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def write_profile(
        self,
        *,
        raw_text: str,
        profile: dict,
        inferred_fields: tuple[str, ...],
        complexity_tier: int | None = None,
        error_cost: str | None = None,
        requests_per_month: int | None = None,
    ) -> str:
        """`inferred_fields` is FR-30's record of what we guessed.

        Stored rather than derived later: which fields the USER stated and
        which we filled in is not recoverable from the finished profile, and
        it is the difference between a recommendation they confirmed and one
        we assembled.
        """
        profile_id = _derived_id("tp", raw_text, json.dumps(profile, sort_keys=True))
        self._conn.execute(
            """
            INSERT INTO task_profile (id, raw_text, profile, complexity_tier,
                                      error_cost, requests_per_month, inferred_fields)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                profile_id,
                raw_text,
                json.dumps(profile),
                complexity_tier,
                error_cost,
                requests_per_month,
                list(inferred_fields),
            ),
        )
        return profile_id

    def write_role(
        self,
        *,
        task_profile_id: str,
        name: str,
        capability_needs: dict,
        runs_per_request: int = 1,
        failure_mode: str | None = None,
        error_cost: str | None = None,
        dependents: tuple[str, ...] = (),
    ) -> str:
        """`runs_per_request` is where the money is, and it is multiplied ONCE.

        Role volume derives from it. A caller that also multiplies request
        volume by it produces a cost estimate off by that factor, which is why
        the column comment says so and this docstring repeats it.
        """
        role_id = _derived_id("rl", task_profile_id, name)
        self._conn.execute(
            """
            INSERT INTO role (id, task_profile_id, name, capability_needs,
                              runs_per_request, failure_mode, error_cost, dependents)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                role_id,
                task_profile_id,
                name,
                json.dumps(capability_needs),
                runs_per_request,
                failure_mode,
                error_cost,
                list(dependents),
            ),
        )
        return role_id

    def write_answer(self, answer: Answer) -> str:
        """Every candidate, not only the winners.

        Refuses an answer carrying a justification with no evidence behind it
        (FR-34). Writing it and flagging it later would put an unfalsifiable
        rationale in the table that "why not X?" reads from.
        """
        unjustified = answer.unjustified()
        if unjustified:
            names = ", ".join(c.model_version_id for c in unjustified)
            raise ValueError(
                f"refusing to store a justification with no quote behind it: "
                f"{names}. FR-34 binds every sentence of justification to a "
                f"quote id, and this table is what 'why not X?' reads."
            )

        self._conn.execute(
            """
            INSERT INTO answer (id, role_id, candidates, abstained, reason, assumptions)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                candidates  = EXCLUDED.candidates,
                abstained   = EXCLUDED.abstained,
                reason      = EXCLUDED.reason,
                assumptions = EXCLUDED.assumptions
            """,
            (
                answer.answer_id,
                answer.role_id,
                json.dumps(
                    [
                        {
                            "model_version_id": c.model_version_id,
                            "band": c.band,
                            "reason": c.reason,
                            "cost_per_task": c.cost_per_task,
                            "quote_ids": list(c.quote_ids),
                        }
                        for c in answer.candidates
                    ]
                ),
                answer.abstained,
                answer.reason,
                list(answer.assumptions),
            ),
        )
        return answer.answer_id

    def record_outcome(
        self,
        *,
        answer_id: str,
        adopted: bool,
        model_version_id: str | None = None,
        success: bool | None = None,
        retries: int | None = None,
        latency_ms: int | None = None,
        cost_usd: float | None = None,
        failure_kind: str | None = None,
        what_happened: str | None = None,
    ) -> None:
        """The only measurement that says whether this product works.

        `success=None` is NOT failure. An adopted recommendation nobody has
        reported back on is unmeasured, and counting it as either outcome
        would manufacture the one number the project is judged on (rule 6, on
        the figure that matters most).
        """
        if not adopted and model_version_id is not None:
            raise ValueError(
                "a model was named on an unadopted recommendation. Which model "
                "they did not use is a different fact from which they used, "
                "and storing it here would inflate the adoption count."
            )
        self._conn.execute(
            """
            INSERT INTO outcome (answer_id, adopted, model_version_id, success,
                                 retries, latency_ms, cost_usd, failure_kind,
                                 what_happened)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (answer_id) DO UPDATE SET
                adopted       = EXCLUDED.adopted,
                success       = EXCLUDED.success,
                retries       = EXCLUDED.retries,
                latency_ms    = EXCLUDED.latency_ms,
                cost_usd      = EXCLUDED.cost_usd,
                failure_kind  = EXCLUDED.failure_kind,
                what_happened = EXCLUDED.what_happened
            """,
            (
                answer_id,
                adopted,
                model_version_id,
                success,
                retries,
                latency_ms,
                cost_usd,
                failure_kind,
                what_happened,
            ),
        )

    def held_rate(self) -> tuple[int, int, int]:
        """`(held, measured, adopted)` — the success criterion, with its population.

        Three numbers rather than a percentage, because the gap between
        `measured` and `adopted` is the whole caveat. A board reporting "90%
        held" over ten measured outcomes out of four hundred adopted has said
        almost nothing, and a single figure hides which of those it is
        (rule 7).
        """
        row = self._conn.execute(
            "SELECT count(*) FILTER (WHERE success), "
            "count(*) FILTER (WHERE success IS NOT NULL), "
            "count(*) FILTER (WHERE adopted) FROM outcome"
        ).fetchone()
        return (int(row[0]), int(row[1]), int(row[2])) if row else (0, 0, 0)


__all__ = ["Answer", "AnswerStore", "Candidate"]
