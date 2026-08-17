"""Load `contract/queries.yaml` into typed entries.

Read-only. This lane renders the file and never writes it: it is shared, and
the semantic half is Engineer 2's under the split agreed on issue #5.

RULE 5, AND WHY THERE ARE NO DEFAULTS HERE
------------------------------------------
Every value comes from the contract. A missing file raises rather than falling
back to a built-in query set, because a built-in set is a second source of
truth that renders identically to the real one and diverges silently. The same
reasoning as `assert_contract_backed`.

PLACEHOLDERS
------------
`{alias}` is substituted once per alias variant, `{alias_b}` once per other
model. Substitution happens here rather than in each adapter so that "what
string did we actually search for" has one answer, and so that an entry needing
`{alias_b}` cannot be rendered without one — which would otherwise produce a
query containing the literal text `{alias_b}` and match nothing, silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from collect.config import CONTRACT_DIR

QUERIES_YAML = CONTRACT_DIR / "queries.yaml"

#: The stances FR-8's check reads. A third value would be a contract change.
STANCES = ("negative", "positive")

#: `direction: decided_at_extraction` — the one semantic property the contract
#: states about retrieval. It does not name a platform, deliberately: it says
#: WHERE DIRECTION IS DECIDED, which is a fact about the pipeline rather than
#: about any index, and leaves each adapter to decide what to do about
#: retrieving a direction-blind superset.
#:
#: Renamed from `phrase_binding`. That name asserted a cause the measurements
#: contradicted — it implied some index binds phrases, and none that has been
#: measured does. The behaviour here never depended on the cause, which is why
#: this is a rename and not a redesign.
DECIDED_AT_EXTRACTION = "decided_at_extraction"

#: Every value `direction:` may take. Checked at load, which the rename left
#: undone: `stance` and `records_condition` are validated and `direction` was
#: not, so the file's ONE machine-readable constraint was its only unchecked
#: field. `direction: decided_at_extration` would have loaded, turned the
#: constraint silently off, and let GitHub render substitution as though the
#: direction had survived retrieval — an absence with nothing on the page to
#: disagree with, which is the class of defect rule 6 is about.
DIRECTIONS = (DECIDED_AT_EXTRACTION,)

_PLACEHOLDER = re.compile(r"\{(alias|alias_b)\}")


class QueryContractError(RuntimeError):
    """The queries file is missing, malformed, or missing a required field."""


class MissingPlaceholderError(QueryContractError):
    """An entry needs `{alias_b}` and none was supplied.

    Rendering it anyway would emit the literal `{alias_b}` into a query, which
    matches nothing and looks like a source with no discussion.
    """


@dataclass(frozen=True)
class TermSet:
    """One entry's three term groups, with the semantics the contract states.

    `subject` is ALL-OF; `topic` and `signal` are ANY-OF. That asymmetry is the
    contract's, not a rendering choice: the subject identifies the model and
    every part of it must be present, while topic and signal are alternative
    ways of saying the same thing.
    """

    subject: tuple[str, ...]
    topic: tuple[str, ...]
    signal: tuple[str, ...]

    @property
    def all_terms(self) -> tuple[str, ...]:
        """Every term in every group, for questions that are about the entry.

        Stated once so it cannot be partially re-derived. `needs_second_model`
        read `topic + signal` and missed `subject`, and the cost of that was not a
        wrong answer — it was `False`, which reads as "this entry does not need a
        second model" and is indistinguishable from a correct answer. Anything
        asking "does this entry mention X anywhere" reads this.
        """
        return self.subject + self.topic + self.signal

    def substitute(self, alias: str, alias_b: str | None = None) -> RenderedTerms:
        def render(terms: tuple[str, ...]) -> tuple[str, ...]:
            out = []
            for term in terms:
                if "{alias_b}" in term and alias_b is None:
                    raise MissingPlaceholderError(
                        f"term {term!r} needs {{alias_b}} and none was given. Rendering it "
                        "would search for the literal text and return nothing, which reads "
                        "as an absence of discussion rather than as a bug."
                    )
                rendered = term.replace("{alias}", alias)
                if alias_b is not None:
                    rendered = rendered.replace("{alias_b}", alias_b)
                out.append(rendered)
            return tuple(out)

        return RenderedTerms(
            subject=render(self.subject),
            topic=render(self.topic),
            signal=render(self.signal),
            alias=alias,
            alias_b=alias_b,
        )


@dataclass(frozen=True)
class RenderedTerms:
    """A term set with its placeholders filled in. What the sieve reads."""

    subject: tuple[str, ...]
    topic: tuple[str, ...]
    signal: tuple[str, ...]
    alias: str
    alias_b: str | None = None

    @property
    def unresolved(self) -> tuple[str, ...]:
        """Terms still carrying a placeholder. Should always be empty."""
        return tuple(
            term
            for group in (self.subject, self.topic, self.signal)
            for term in group
            if _PLACEHOLDER.search(term)
        )


@dataclass(frozen=True)
class QueryEntry:
    """One entry from the contract. `capability` is None for substitution."""

    kind: str  # "capability" | "substitution"
    stance: str
    terms: TermSet
    records_condition: str
    intent: str = ""
    yields_claim_when: str = ""
    capability: str | None = None
    direction: str | None = None

    @property
    def label(self) -> str:
        """What to call this entry in a log line or a query key."""
        return f"{self.capability or 'substitution'}:{self.stance}"

    @property
    def direction_from_extraction(self) -> bool:
        """Direction is this entry's content and retrieval cannot carry it.

        True for the substitution entries and nothing else. An adapter reading
        this must either refuse, or accept a direction-blind superset as a
        stated coverage decision — never render it as though the direction
        survived retrieval.
        """
        return self.direction == DECIDED_AT_EXTRACTION

    @property
    def needs_second_model(self) -> bool:
        """Does any group carry `{alias_b}`? All three, not two of them.

        This read `topic + signal`. The substitution entries now carry both
        aliases in `subject` — which is all-of, so both models must be present,
        which is what lets `topic` hold bare switching verbs — and a topic-only
        read returns False there. No `alias_b` is supplied, and `substitute()`
        raises when it reaches the subject term.

        The failure is loud, which is luck rather than design: the same omission
        one group over, on a group that had no `{alias_b}` to find, would have
        rendered a query silently missing half its subject.
        """
        return any("{alias_b}" in term for term in self.terms.all_terms)


@dataclass(frozen=True)
class QuerySet:
    """Everything in `contract/queries.yaml`."""

    version: str
    capability_queries: tuple[QueryEntry, ...]
    substitution: tuple[QueryEntry, ...]

    @property
    def all_entries(self) -> tuple[QueryEntry, ...]:
        return self.capability_queries + self.substitution

    def for_capability(self, capability: str) -> tuple[QueryEntry, ...]:
        return tuple(e for e in self.capability_queries if e.capability == capability)

    @property
    def capabilities(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for entry in self.capability_queries:
            if entry.capability:
                seen.setdefault(entry.capability, None)
        return tuple(seen)


def _terms_of(raw: dict, label: str) -> TermSet:
    terms = raw.get("terms")
    if not isinstance(terms, dict):
        raise QueryContractError(f"{label}: entry has no `terms` block")
    out = {}
    for group in ("subject", "topic", "signal"):
        values = terms.get(group)
        if not values:
            raise QueryContractError(f"{label}: `terms.{group}` is missing or empty")
        out[group] = tuple(str(v) for v in values)
    return TermSet(**out)


def _entry_of(raw: dict, *, kind: str) -> QueryEntry:
    capability = raw.get("capability")
    label = f"{capability or kind}:{raw.get('stance')}"

    stance = raw.get("stance")
    if stance not in STANCES:
        raise QueryContractError(f"{label}: stance {stance!r} is not one of {STANCES}")

    records_condition = raw.get("records_condition")
    if not records_condition:
        raise QueryContractError(f"{label}: `records_condition` is missing")

    direction = raw.get("direction")
    if direction is not None and direction not in DIRECTIONS:
        raise QueryContractError(
            f"{label}: direction {direction!r} is not one of {DIRECTIONS}. An "
            "unrecognised value would load, read as absent, and turn the only "
            "machine-readable constraint in the contract off without saying so."
        )

    return QueryEntry(
        kind=kind,
        capability=capability,
        stance=stance,
        intent=str(raw.get("intent") or "").strip(),
        terms=_terms_of(raw, label),
        records_condition=str(records_condition),
        yields_claim_when=str(raw.get("yields_claim_when") or "").strip(),
        direction=direction,
    )


def load_queries(path: Path | str | None = None) -> QuerySet:
    """Read the contract. Raises rather than defaulting — see the module docstring."""
    source = Path(path) if path is not None else QUERIES_YAML
    if not source.exists():
        raise QueryContractError(
            f"{source} does not exist. Harvest is entirely query-driven, so an absent "
            "query set is not an empty harvest — it is a harvest that searches for "
            "nothing and reports no error."
        )

    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise QueryContractError(f"{source} did not parse to a mapping")

    entries = raw.get("queries")
    if not entries:
        raise QueryContractError(f"{source}: `queries` is missing or empty")

    return QuerySet(
        version=str(raw.get("version", "")),
        capability_queries=tuple(_entry_of(e, kind="capability") for e in entries),
        substitution=tuple(_entry_of(e, kind="substitution") for e in raw.get("substitution", [])),
    )
