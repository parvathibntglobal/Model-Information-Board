"""Q4-Q7 over real cells, and the answer written down so it can be questioned.

`gate()` and `rank()` were built and correct. `AnswerStore` was built and
correct. Nothing read cells from the database, ran one through the other, and
stored the result - so the ranking logic had no evidence and the store had no
caller. Thirteenth instance of that shape here.

THE ANSWER IS PERSISTED BEFORE IT IS RETURNED

FR-36 makes "why not X?" first-class, and it is answerable only against what we
said AT THE TIME. Cells move nightly, so re-deriving the answer later produces
"here is what I would say now" - a different and unaccountable claim. Every
candidate is stored, rejected ones included, because a rejection that leaves no
row is a question nobody can ask.

NOTHING HERE CALLS A MODEL

Q1 interprets the request. From here on it is counting, gating, banding,
ranking - all of which rule 2 names explicitly. The justification is assembled
from the cells that produced it and carries their quote ids, which is the
alternative to a model writing a persuasive sentence nobody can check.

ABSTAINING IS THE ANSWER WHEN THERE IS NOTHING TO SAY

Not an error, and not an empty list. FR-35 requires naming the capability that
lacks evidence, because "no recommendation" and "no recommendation because
nobody has reported on summarization fidelity for any model you could afford"
are different answers and only the second is actionable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from judge.ask.profile import RoleRequirement
from judge.ask.rank import Band, Candidate, CellStatus, CellView, gate, rank
from judge.store.answers import Answer, AnswerStore
from judge.store.answers import Candidate as StoredCandidate

#: `rank.Band` to the string `answer.candidates` records. Kept explicit rather
#: than `str(band)`, so a rename in one vocabulary cannot silently change what
#: a stored answer means to a page reading it a month later.
BAND_TO_STORED: dict[Band, str] = {
    Band.RECOMMENDED: "recommended",
    Band.ALSO_WORKS: "qualified",
    Band.DOESNT_QUALIFY: "rejected",
    Band.NO_EVIDENCE: "no_evidence",
}


@dataclass(frozen=True)
class CellReader:
    """Reads published cells for the models a question is about.

    `cell_current` rather than `cell`: the view is `published` plus
    `contested`, so an `insufficient` cell cannot reach a recommendation by
    accident. A cell that did not clear the gate is evidence that something was
    said, not evidence of what it said.
    """

    conn: Any

    def cells_for(self, model_version_ids: list[str]) -> dict[str, dict[tuple[str, str], CellView]]:
        if not model_version_ids:
            return {}
        rows = self.conn.execute(
            """
            SELECT model_version_id, capability_key, condition_bucket, status,
                   independent_voices, positive, negative, consensus_phrase,
                   quote_ids
            FROM cell_current
            WHERE model_version_id = ANY(%s)
            """,
            (list(model_version_ids),),
        ).fetchall()
        out: dict[str, dict[tuple[str, str], CellView]] = {}
        for r in rows:
            # `gate` keys on (capability_key, condition_bucket) - it reads ONE
            # model's cells at a time, at the task's bucket. Grouping per model
            # here rather than flattening keeps that contract intact; a shared
            # dict would let one model's cell answer for another.
            out.setdefault(r[0], {})[(r[1], r[2])] = CellView(
                capability_key=r[1],
                condition_bucket=r[2],
                status=CellStatus(r[3]),
                direction="negative" if r[6] > r[5] else "positive",
                consensus_phrase=r[7] or "",
                voices=r[4],
                positive=r[5],
                negative=r[6],
                quote_ids=list(r[8] or ()),
            )
        return out


def justify(candidate: Candidate) -> str:
    """The sentence, assembled from counts. Never model-written (rules 2 and 3).

    Names the WEAKEST evidenced capability even when everything passes, because
    that is the one that will break in production and a summary that mentions
    only strengths is a sales pitch.
    """
    weakest = candidate.weakest
    if candidate.band is Band.NO_EVIDENCE:
        return "Nobody has reported on the capabilities this task needs."
    if candidate.band is Band.DOESNT_QUALIFY:
        reason = candidate.disqualified_by
        if weakest and weakest.cell and weakest.cell.consensus_phrase:
            return f"Rejected: {weakest.cell.consensus_phrase}."
        return f"Rejected: {reason.value if reason else 'requirements not met'}."
    if weakest and weakest.cell:
        voices = weakest.cell.voices
        return (
            f"Weakest evidenced capability is {weakest.cell.capability_key} at "
            f"{weakest.cell.condition_bucket}, on {voices} "
            f"{'voice' if voices == 1 else 'voices'}."
        )
    return "Qualified, with no capability standing out as weakest."


def answer_for(
    conn: Any,
    *,
    role_id: str,
    requirement: RoleRequirement,
    model_version_ids: list[str],
    display_names: dict[str, str] | None = None,
    assumptions: tuple[str, ...] = (),
) -> Answer:
    """Gate, band, rank, and build the `Answer` that gets stored.

    Every model asked about comes back in the result, including the ones that
    failed and the ones nothing is known about. A candidate filtered out here
    is a question FR-36 can no longer answer.
    """
    names = display_names or {}
    cells = CellReader(conn).cells_for(model_version_ids)

    candidates: list[Candidate] = []
    for model_version_id in model_version_ids:
        verdicts = gate(requirement, cells.get(model_version_id, {}))
        candidates.append(
            Candidate(
                model_version_id=model_version_id,
                display_name=names.get(model_version_id, model_version_id),
                verdicts=verdicts,
            )
        )

    ranked = rank(candidates)
    by_id = {c.model_version_id: c for c in ranked}
    ordered = [by_id.get(c.model_version_id, c) for c in candidates]

    stored = tuple(
        StoredCandidate(
            model_version_id=c.model_version_id,
            band=BAND_TO_STORED[c.band],
            reason=justify(c),
            cost_per_task=c.cost.per_request if c.cost else None,
            # FR-34. A reason with no quote behind it is refused at write, and
            # `no_evidence` is exempt because there is nothing to cite.
            quote_ids=tuple(c.quote_ids),
        )
        for c in ordered
    )

    def persisted(answer: Answer) -> Answer:
        """Stored before it is returned, never after.

        Returning first and storing later means a caller that raises has been
        given an answer that no longer exists to be questioned - and FR-36 asks
        about what we SAID, not what we would say now. `write_answer` refuses a
        justification with no quote behind it, so an unfalsifiable rationale
        cannot reach the table at all. No commit here; the caller owns the
        transaction.
        """
        AnswerStore(conn).write_answer(answer)
        return answer

    recommending = [c for c in stored if c.band in ("recommended", "qualified")]
    if not recommending:
        # ABSTAIN, and name what is missing. An empty ranked list and a refusal
        # to answer look identical to a caller and mean different things.
        missing = sorted({need.key for need in requirement.capabilities})
        return persisted(
            Answer(
                role_id=role_id,
                candidates=stored,
                abstained=True,
                reason=(
                    "No model has evidence clearing the bar for "
                    + ", ".join(missing)
                    + ". This is an absence of reports rather than a report of failure."
                    if missing
                    else "No capability requirements were derived, so there is nothing to check."
                ),
                assumptions=assumptions,
            )
        )

    return persisted(Answer(role_id=role_id, candidates=stored, assumptions=assumptions))
