"""E4 — the specificity components, counted, and the floor that reads them.

**Real experience carries numbers and error strings; slop carries adjectives.**
This module decides which of those a document looks like, using nothing but
counting. No language model participates, here or anywhere in this lane.

WHAT THIS IS FOR, AND THE ORDER IT RUNS IN
------------------------------------------
Two consumers, and `docs/logic-and-workflow.md` currently describes the order
backwards — it says the score is *"already computed in E4 … so reuse it"* while
the pipeline is E3 assemble then E4 triage, so E3 would be reusing something
that does not exist yet. Child selection happens inside E3, so the score is
computed **per document at ingest**, before E3 ranks, and E4 is a second reader
rather than the producer.

    E4 floor      wants the five BOOLEANS. Its rule is a five-way AND — no
                  numbers, no error strings, no code, no conditions, no
                  version named -> opinion, not evidence.  ← wired here
    E3 ranking    wants the SCALAR, as specificity_score x log(1 + engagement).
                  Not wired. E3 is blocked on comment fetching and on three
                  columns proposed in issue #5, neither of which this unblocks.
                  See docs/specificity-score-report.md §3.

Both are stored, which is why `document` carries five component columns beside
the composite: a composite alone makes the floor's verdict unreconstructible
from the row, and the evidence drill-down has nothing countable to show.

THIS IS NOT `judge/vet/weight.py`'s `f_specificity`
---------------------------------------------------
They share a word and nothing else. **They must never be merged, and they must
never be compared** — a reader seeing 0.7 here and 0.7 there will want them to
mean the same thing, and they do not.

    this module            one DOCUMENT, five counted booleans, range 0-1
    weight.f_specificity   one CLAIM, four booleans of which two are emitted
                           by the extractor, range 0.3-1.0

Merging them would put a language-model-emitted boolean into thread-child
ranking, which rule 2 forbids. The matching note belongs in `weight.py`; that
file is Engineer 2's and the note is hers to add.

`has_numbers` IS READABLE FROM `judge/` AS A FALSIFIER, AND ONLY THAT
----------------------------------------------------------------------
`claim.has_numbers` is self-reported by the extractor and reaches `w_final`
with no code check. `document.has_numbers` is the same question asked of the
same text by code, so it can falsify that boolean — and **it falsifies, it
cannot confirm**:

    document.has_numbers is False  ->  a claim asserting has_numbers: true is
                                       a fabrication. There are no numbers in
                                       the document for the quote to contain.
    document.has_numbers is True   ->  says NOTHING about whether that quote
                                       contains one. The numbers may be
                                       anywhere in the document.

So it is a one-directional check and the asymmetry is not a detail: reading it
as confirmation would launder an unverified extractor boolean into a verified
one, which is worse than not checking at all.

RULE 6 — NULL IS NOT ZERO, AND IT BITES ON DAY ONE
---------------------------------------------------
Every `document` row written before this module existed carries NULL in all six
columns. `floor_verdict` therefore returns **UNKNOWN**, not DROPPED, when the
components are absent: coalescing NULL to 0 would drop every pre-scorer
document as "no signals present" and, in E3 later, sort them last while looking
scored. Absent stays absent through every layer that reads it.

WHY THE CONTRACT'S ERROR-STRING TERMS ARE NOT REUSED
-----------------------------------------------------
`contract/queries.yaml` carries about twenty error-string-shaped signal terms
(`invalid json`, `failed to parse`, `not in the schema`). Reusing them here
would couple a DOCUMENT-LEVEL property to the CAPABILITY VOCABULARY: editing
one capability's terms would silently re-rank thread children in every other
capability. The detector below is vocabulary-independent for that reason.

WHAT IS MEASURED, AND WHAT IS JUDGEMENT
----------------------------------------
The five detectors are countable and testable. The five weights are not
measured by anything — there is no corpus labelled for specificity to fit them
against. They are marked provisional in `contract/harvest.yaml`, the same
position `sieve.locality_window` was in, and the calibration that would revise
them is a re-score of the 174 GitHub candidates and 111 blog articles already
in the raw store. That is a re-score, not a fetch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

from collect.adapters.queries.sieve import EXCLUDED_CONTAINERS, author_prose


class SpecificityContractError(RuntimeError):
    """The contract is missing the configuration this module refuses to default."""


@lru_cache(maxsize=1)
def _contract() -> dict:
    """`contract/harvest.yaml:specificity`. Same shape as `sieve`'s loader.

    Rule 5: weights and the floor live in versioned YAML. Unlike
    `locality_window`, absence RAISES rather than disabling — a scorer with no
    weights would write zeroes into a real column, and a zero is a definite
    value where the truth is "not configured" (rule 6).
    """
    import yaml

    from collect.config import CONTRACT_DIR

    path = CONTRACT_DIR / "harvest.yaml"
    if not path.exists():  # pragma: no cover - contract is always present
        raise SpecificityContractError(f"{path} does not exist")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw.get("specificity") or {}


#: The five components, in the order `contract/harvest.yaml` lists their
#: weights. Also the column order on `document`.
COMPONENTS: tuple[str, ...] = (
    "has_numbers",
    "has_error_strings",
    "has_code",
    "has_conditions",
    "names_version",
)


class FloorVerdict(StrEnum):
    """Tri-state, because rule 6 forbids collapsing the third into the second."""

    KEPT = "kept"
    DROPPED = "dropped"
    UNKNOWN = "unknown"


# ── detectors ────────────────────────────────────────────────────────────
#
# Each is deliberately narrow. A detector that fires on everything carries no
# information, and the floor is the gate that decides whether a document costs
# an extraction call.

#: Numbers WITH UNITS. A bare integer is noise — issue numbers, dates, list
#: markers, and the version tokens `names_version` already counts. What marks
#: real measurement is a quantity: `1.8s`, `p95 420ms`, `32k tokens`, `$4.10`,
#: `12 tools`, `40%`. `tests/test_blog_parse.py` pins `1.8s` as the case, and
#: `collect/CLAUDE.md` names numbers-with-units as the specificity signal.
_NUMBER_UNIT = re.compile(
    r"""(?ix)
    (?: \$\s?\d[\d,]*(?:\.\d+)?                      # $4.10
      | \d[\d,]*(?:\.\d+)?\s?%                       # 40%
      | \d[\d,]*(?:\.\d+)?\s?
        (?: ms|s|sec|secs|second|seconds
          | m|min|mins|minute|minutes|h|hr|hrs|hour|hours
          | kb|mb|gb|tb
          | k|m|b                                    # 32k, 1m — with a noun below
          )\b
      | \d[\d,]*(?:\.\d+)?\s?
        (?: tokens?|tok|tps|qps|rps|rpm|requests?|calls?|tools?|turns?
          | docs?|documents?|rows?|files?|tickets?|runs?|retries|retry
          | dollars?|cents?|users?|prompts?
          )\b
      | \bp\d{2}\b                                   # p50, p95, p99
      )
    """
)

#: Error strings. Shapes, not vocabulary — see the module docstring for why
#: `contract/queries.yaml`'s terms are deliberately not reused.
_ERROR_STRING = re.compile(
    r"""(?x)
    (?: \bTraceback\ \(most\ recent\ call\ last\)
      | \b[A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning)\b   # KeyError, HTTPException
      | (?im:^\s*(?:error|fatal|panic|exception)\s*[:\[])   # error: / ERROR[
      | \b(?:HTTP\s?)?(?:4\d{2}|5\d{2})\s
        (?:error|status|response|bad\ request|unauthorized|forbidden|
           not\ found|too\ many\ requests|internal\ server)
      | \bstatus\ code\ (?:4\d{2}|5\d{2})\b
      | \b(?:errno|SIGSEGV|SIGABRT|core\ dumped)\b
      | \bat\ [\w.$]+\([\w.]+:\d+\)                          # java/js stack frame
      | (?im:^\s*File\ ".+",\ line\ \d+)                     # python frame
      )
    """
)

#: Conditions. The three dimensions of `contract/conditions.yaml` — tool count,
#: context size, structured mode — detected as STATED VALUES rather than as
#: bands. The weakest of the five: a document can state a condition in prose
#: this will not see. It is a floor input, not a bucket assignment; assigning
#: the band is `judge/`'s and happens per claim, not per document.
_CONDITIONS = re.compile(
    r"""(?ix)
    (?: \b\d+\s?tools?\b
      | \btool[_\s]?(?:count|choice)\b
      | \b\d+\s?(?:k|m)\s?(?:tokens?|context|ctx|window)\b
      | \b(?:context|ctx)\s?(?:window|length|size)\b
      | \b\d+\s?(?:k|m)\s?(?:token)?\s?(?:prompt|input)\b
      | \bjson[_\s]?mode\b
      | \bresponse[_\s]?format\b
      | \bstructured[_\s]?output(?:s)?\b
      | \bstrict\s?(?:mode|schema|json)\b
      | \bjson[_\s]?schema\b
      | \bgrammar[_\s]?constrained\b
      )
    """
)


def has_numbers(text: str) -> bool:
    """A quantity with a unit appears anywhere in the document."""
    return bool(_NUMBER_UNIT.search(text))


def has_error_strings(text: str) -> bool:
    """A machine-emitted failure appears anywhere in the document."""
    return bool(_ERROR_STRING.search(text))


def has_code(text: str) -> bool:
    """A code container appears — fenced, indented, inline or HTML.

    Reuses `sieve`'s exclusion set rather than a second definition of what code
    looks like. The sieve removes those spans to find the author's own prose;
    here their PRESENCE is the signal, which is the same fact read the other
    way round. Two definitions would drift.
    """
    return author_prose(text) != text


def has_conditions(text: str) -> bool:
    """A value for one of `contract/conditions.yaml`'s three dimensions."""
    return bool(_CONDITIONS.search(text))


def names_version(text: str, aliases) -> bool:
    """A model is named at `version` or `snapshot` specificity.

    `aliases` is the caller's pre-filtered surface list — family surfaces must
    already be excluded. A bare `sonnet` names a line rather than a tier, and
    counting it would credit a document that never said which model it meant.

    NORMALISES FIRST, AND THAT IS NOT OPTIONAL. `sieve.matches` documents itself
    as operating on "already-normalised text" and does not casefold: against raw
    text, `matches("claude opus 5", "We moved to Claude Opus 5")` is **False**.
    The first version of this function passed raw text and therefore missed
    every capitalised model name, which is how people write them — it scored
    1 of 111 blog articles where the true figure is 7. The four other detectors
    are case-insensitive regexes over RAW text, because they need the line
    structure `normalize` collapses, so the normalisation belongs here rather
    than once at the top of `score_document`.
    """
    from collect.adapters.queries.sieve import matches, normalize

    haystack = normalize(text)
    return any(matches(alias, haystack) for alias in aliases)


# ── the row ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Specificity:
    """The five components and the composite. What `document` stores."""

    has_numbers: bool
    has_error_strings: bool
    has_code: bool
    has_conditions: bool
    names_version: bool
    score: float

    @property
    def components(self) -> dict[str, bool]:
        return {name: getattr(self, name) for name in COMPONENTS}

    def as_row(self) -> dict[str, object]:
        """Column values for `document`. Six columns, not one."""
        return {**self.components, "specificity_score": self.score}

    def explain(self) -> str:
        """For the drill-down: what was counted, never the composite alone."""
        present = [name for name in COMPONENTS if getattr(self, name)]
        return f"{', '.join(present) or 'none'} -> {self.score:.2f}"


def weights() -> dict[str, float]:
    """Component weights from `contract/harvest.yaml`. Provisional — see there."""
    configured = _contract().get("weights")
    if not configured:
        raise SpecificityContractError(
            "contract/harvest.yaml has no `specificity.weights`. There is no "
            "built-in default on purpose: a second source of truth renders "
            "identically to the real one and diverges silently (rule 5)."
        )
    missing = [name for name in COMPONENTS if name not in configured]
    if missing:
        raise SpecificityContractError(
            f"contract/harvest.yaml `specificity.weights` is missing {missing}. "
            "A component with no weight would contribute zero, which is a "
            "silent change to every score rather than an error."
        )
    return {name: float(configured[name]) for name in COMPONENTS}


def floor_components() -> tuple[str, ...]:
    """Which components clear the floor, from the contract."""
    configured = _contract().get("floor_clears_on")
    if not configured:
        raise SpecificityContractError(
            "contract/harvest.yaml has no `specificity.floor_clears_on`."
        )
    unknown = [name for name in configured if name not in COMPONENTS]
    if unknown:
        raise SpecificityContractError(
            f"`specificity.floor_clears_on` names unknown components {unknown}"
        )
    return tuple(configured)


def score_document(text: str, *, version_aliases) -> Specificity:
    """Count the five components and combine them at the contract's weights.

    `version_aliases` is the registry's `version`/`snapshot` surfaces. Passed in
    rather than loaded here so the registry read happens once per sweep instead
    of once per document.
    """
    found = {
        "has_numbers": has_numbers(text),
        "has_error_strings": has_error_strings(text),
        "has_code": has_code(text),
        "has_conditions": has_conditions(text),
        "names_version": names_version(text, version_aliases),
    }
    w = weights()
    total = sum(w.values())
    if total <= 0:
        raise SpecificityContractError(
            "`specificity.weights` sum to zero, which would score every "
            "document identically."
        )
    score = sum(w[name] for name, hit in found.items() if hit) / total
    return Specificity(**found, score=score)


def floor_verdict(components: dict[str, bool | None] | None) -> FloorVerdict:
    """E4's specificity floor. Tri-state — rule 6.

    `None` for the whole mapping, or `None` for any component, means the
    document has not been scored. That is UNKNOWN, never DROPPED: a document
    written before this module existed has not failed the floor, it has not
    faced it. See the module docstring.
    """
    if components is None:
        return FloorVerdict.UNKNOWN
    clears_on = floor_components()
    values = [components.get(name) for name in clears_on]
    if any(v is None for v in values):
        return FloorVerdict.UNKNOWN
    return FloorVerdict.KEPT if any(values) else FloorVerdict.DROPPED


def filter_reason(verdict: FloorVerdict) -> str | None:
    """What `document.filter_reasons` records. UNKNOWN records itself.

    An unscored document must be visibly unscored rather than silently kept:
    a reader of the row can then tell "faced the floor and cleared it" from
    "never faced it", which is the distinction rule 6 exists to preserve.
    """
    return {
        FloorVerdict.KEPT: None,
        FloorVerdict.DROPPED: "specificity-floor",
        FloorVerdict.UNKNOWN: "specificity-unscored",
    }[verdict]


#: Documented so nobody has to grep for it: what the sieve calls a container.
CODE_CONTAINERS = EXCLUDED_CONTAINERS
