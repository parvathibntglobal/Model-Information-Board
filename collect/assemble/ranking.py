"""E3 child ranking: which comments of a thread reach the extractor.

    score = specificity
          + engagement_weight x log1p(max(upvotes, 0))
          + first_hand bonus      (the author says they did it)
          + relevance[tier]       (how the comment relates to the thread subject)

Every weight is in `contract/harvest.yaml:child_ranking` (rule 5) and the block
there carries the argument. This module counts and adds; NO MODEL PARTICIPATES
(rule 2), and nothing here drops a comment - the only drop is the caller's
`max_children` cut (rule 8).

WHY A SUM AND NOT THE OLD PRODUCT
---------------------------------
`specificity x log1p(engagement)` made any zero fatal. `log1p(0) = 0`, so a
comment at 0 upvotes ranked 0 however specific it was - and on Hacker News,
which publishes no comment score to anyone, EVERY child ranked 0 and the
`external_id` tie-break chose by arrival order under a label that said
"ranked". With a sum, a missing score costs the engagement term and nothing
else. GitHub's assembler dropped the engagement term for exactly this reason
(`collect/assemble/issue.py`); it can now share this ranker instead.

RELEVANCE IS LEXICAL, AND IT SAYS SO
------------------------------------
A comment's tier comes from which model names appear in it and in the ROOT,
matched against `model_alias` surfaces and keyed by family, so `Opus 4.8` in a
comment under a `Claude Opus 5` root lands on the same key. A short or generic
surface can false-match ("flash" in "flash attention"); that is why the tier is
printed for every selected child in the E3 log rather than trusted silently.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

#: The five tiers, in the order the log prints them. See `contract/harvest.yaml`.
SUBJECT = "subject"
TOPIC_ONLY = "topic_only"
OTHER_MODEL = "other_model"
UNRELATED = "unrelated"
UNKNOWN = "unknown"
TIERS = (SUBJECT, TOPIC_ONLY, OTHER_MODEL, UNRELATED, UNKNOWN)

#: Surfaces shorter than this are not matched for relevance. Two-character
#: aliases ("o1", "r1") hit version strings and identifiers far more often than
#: they name a model, and a wrong `other_model` tier is a silent demotion.
MIN_SURFACE_CHARS = 3


class RankingContractError(RuntimeError):
    """`contract/harvest.yaml:child_ranking` is missing something this refuses to default."""


# ── configuration ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RankingConfig:
    max_children: int
    engagement_weight: float
    first_hand_bonus: float
    first_hand_phrases: tuple[str, ...]
    relevance: Mapping[str, float]


@lru_cache(maxsize=1)
def ranking_config() -> RankingConfig:
    """Read the contract. An absent key RAISES, like `specificity.weights`.

    A ranker with a defaulted weight would rank on a number nobody chose, and
    the result would look exactly like a considered ranking (rule 6).
    """
    import yaml

    from collect.config import CONTRACT_DIR

    raw = yaml.safe_load((CONTRACT_DIR / "harvest.yaml").read_text(encoding="utf-8")) or {}
    block = raw.get("child_ranking")
    if not block:
        raise RankingContractError("contract/harvest.yaml has no `child_ranking` block.")
    try:
        first_hand = block["first_hand"]
        relevance = {tier: float(block["relevance"][tier]) for tier in TIERS}
        config = RankingConfig(
            max_children=int(block["max_children"]),
            engagement_weight=float(block["engagement_weight"]),
            first_hand_bonus=float(first_hand["bonus"]),
            first_hand_phrases=tuple(str(p) for p in first_hand["phrases"]),
            relevance=relevance,
        )
    except (KeyError, TypeError) as exc:
        raise RankingContractError(
            f"contract/harvest.yaml `child_ranking` is missing {exc}. Every weight "
            "is required; a defaulted one ranks on a number nobody chose."
        ) from exc
    if config.max_children < 1:
        raise RankingContractError("`child_ranking.max_children` must be at least 1.")
    if not config.first_hand_phrases:
        raise RankingContractError("`child_ranking.first_hand.phrases` is empty.")
    return config


def max_children() -> int:
    return ranking_config().max_children


@lru_cache(maxsize=1)
def topic_terms() -> tuple[str, ...]:
    """Every capability `terms.topic` phrase in `contract/queries.yaml`, normalised."""
    from collect.adapters.queries.contract import load_queries
    from collect.adapters.queries.sieve import normalize

    seen: dict[str, None] = {}
    for entry in load_queries().capability_queries:
        for term in entry.terms.topic:
            if "{" not in term:
                seen.setdefault(normalize(term), None)
    return tuple(seen)


# ── the model lexicon ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ModelLexicon:
    """Normalised alias surface -> the model keys it names.

    A key is the alias's `family` where the registry records one, else its
    `model_version_id`. Family is what makes "Opus 4.8" in a comment and
    "Claude Opus 5" in the root the SAME subject.
    """

    surfaces: Mapping[str, frozenset[str]]

    def models_in(self, normalised_text: str) -> frozenset[str]:
        """The model keys named in already-normalised text.

        A substring test first and the whole-word pattern only on a hit: the
        lexicon holds every alias in the registry, and running every pattern
        over every comment of a 200-comment thread is the slow way to find the
        three that appear.
        """
        from collect.adapters.queries.sieve import matches

        found: set[str] = set()
        for surface, keys in self.surfaces.items():
            if surface in normalised_text and matches(surface, normalised_text):
                found.update(keys)
        return frozenset(found)


def load_lexicon(conn) -> ModelLexicon:
    """Every current alias, once per assembly run."""
    from collect.adapters.queries.sieve import normalize

    rows = conn.execute(
        "SELECT surface, normalized, family, model_version_id FROM model_alias "
        "WHERE valid_until IS NULL"
    ).fetchall()
    return lexicon_from_rows(
        ((surface, normalized, family or mv_id) for surface, normalized, family, mv_id in rows),
        normalize=normalize,
    )


def lexicon_from_rows(rows: Iterable[tuple[Any, Any, Any]], *, normalize=None) -> ModelLexicon:
    """`(surface, normalized, key)` rows -> a lexicon. Split out so tests need no database."""
    if normalize is None:
        from collect.adapters.queries.sieve import normalize
    table: dict[str, set[str]] = {}
    for surface, normalized, key in rows:
        if not key:
            continue
        for form in {normalize(str(surface or "")), normalize(str(normalized or ""))}:
            if len(form) >= MIN_SURFACE_CHARS:
                table.setdefault(form, set()).add(str(key))
    return ModelLexicon({s: frozenset(k) for s, k in table.items()})


def version_surfaces(conn) -> set[str]:
    """VERSION and SNAPSHOT surfaces, the input `names_version` expects.

    Family surfaces are excluded because `names_version` asks whether a SPECIFIC
    version is named; a bare `sonnet` is the case ranking exists to sink. The
    same query `collect/assemble/reddit.py:_version_aliases` runs.
    """
    rows = conn.execute(
        "SELECT DISTINCT normalized FROM model_alias "
        "WHERE normalized IS NOT NULL AND specificity IN ('version', 'snapshot')"
    ).fetchall()
    return {r[0] for r in rows if r[0]}


# ── the terms ────────────────────────────────────────────────────────────


def is_first_hand(text: str, phrases: Iterable[str] | None = None) -> bool:
    """The AUTHOR says they did it: "I tried", "we switched", "our testing".

    Read from `author_prose`, so "I tried" inside a quoted block or a code fence
    is somebody else's sentence and does not count - a relay quoting a
    first-hand report is exactly what this term exists to tell apart.
    """
    from collect.adapters.queries.sieve import author_prose, matches, normalize

    phrases = ranking_config().first_hand_phrases if phrases is None else phrases
    prose = normalize(author_prose(text))
    return any(matches(normalize(p), prose) for p in phrases)


def thread_subjects(root_text: str, lexicon: ModelLexicon | None) -> frozenset[str] | None:
    """The models the ROOT names. None when there is nothing to compare against.

    None, not an empty set, when no lexicon was supplied or the root names no
    model: every child is then `unknown`, which scores 0, rather than
    `unrelated`, which is a penalty for a subject that was never established.
    """
    if lexicon is None or not root_text:
        return None
    from collect.adapters.queries.sieve import normalize

    named = lexicon.models_in(normalize(root_text))
    return named or None


def relevance_of(
    text: str, subjects: frozenset[str] | None, lexicon: ModelLexicon | None
) -> str:
    """One of `TIERS`. See `contract/harvest.yaml:child_ranking.relevance`."""
    if subjects is None or lexicon is None:
        return UNKNOWN
    from collect.adapters.queries.sieve import matches, normalize

    haystack = normalize(text)
    named = lexicon.models_in(haystack)
    if named & subjects:
        return SUBJECT
    if named:
        return OTHER_MODEL
    if any(term in haystack and matches(term, haystack) for term in topic_terms()):
        return TOPIC_ONLY
    return UNRELATED


# ── the ranking ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RankedChild:
    """One child, its score, and every term that went into it - for the log."""

    member: Any
    score: float
    specificity: float
    engagement_term: float
    #: None when the platform published no score, so the log says `n/a`
    #: rather than printing a 0 the platform never reported (rule 6).
    upvotes: int | None
    first_hand: bool
    first_hand_term: float
    relevance: str
    relevance_term: float

    @property
    def external_id(self) -> str:
        return self.member.external_id

    def describe(self) -> str:
        """` 1.050 = spec 0.550 + eng 0.104 (votes 7) + first-hand 0.300 + rel +0.200 [subject]`."""
        votes = "n/a" if self.upvotes is None else str(self.upvotes)
        return (
            f"{self.score:6.3f} = spec {self.specificity:.3f}"
            f" + eng {self.engagement_term:.3f} (votes {votes})"
            f" + first-hand {self.first_hand_term:.3f}"
            f" + rel {self.relevance_term:+.3f} [{self.relevance}]"
        )


@dataclass(frozen=True)
class Selection:
    """What ranking did to one thread: the kept children, and the whole field.

    `ranked` covers EVERY observed child, so the log can say "25 of 140" and
    how the unselected ones split by tier. Consumer (rule 9): `selection_lines`,
    printed by `scripts/fetch_model.py:assemble_stage`. Not persisted.
    """

    ranked: tuple[RankedChild, ...]
    selected: tuple[RankedChild, ...]
    subjects: frozenset[str] | None = None
    tiers_observed: Mapping[str, int] = field(default_factory=dict)

    @property
    def first_hand_observed(self) -> int:
        return sum(1 for r in self.ranked if r.first_hand)

    @property
    def first_hand_selected(self) -> int:
        return sum(1 for r in self.selected if r.first_hand)


def rank_children(
    comments: Iterable[Any],
    *,
    version_aliases,
    root_text: str = "",
    lexicon: ModelLexicon | None = None,
    config: RankingConfig | None = None,
) -> list[RankedChild]:
    """Every child scored, highest first. Ties break on `external_id`.

    `lexicon=None` is legitimate - a caller with no registry - and makes every
    child `unknown` for relevance, which scores 0 rather than a penalty.
    """
    from collect.triage.specificity import score_document

    config = config or ranking_config()
    subjects = thread_subjects(root_text, lexicon)
    ranked: list[RankedChild] = []
    for comment in comments:
        specificity = score_document(comment.body, version_aliases=version_aliases).score
        upvotes = comment.score if isinstance(comment.score, int) else None
        engagement = config.engagement_weight * math.log1p(max(upvotes or 0, 0))
        first_hand = is_first_hand(comment.body, config.first_hand_phrases)
        first_hand_term = config.first_hand_bonus if first_hand else 0.0
        tier = relevance_of(comment.body, subjects, lexicon)
        relevance_term = config.relevance[tier]
        ranked.append(RankedChild(
            member=comment,
            score=specificity + engagement + first_hand_term + relevance_term,
            specificity=specificity,
            engagement_term=engagement,
            upvotes=upvotes,
            first_hand=first_hand,
            first_hand_term=first_hand_term,
            relevance=tier,
            relevance_term=relevance_term,
        ))
    ranked.sort(key=lambda r: (-r.score, r.external_id))
    return ranked


def select_children(
    comments: Iterable[Any],
    *,
    version_aliases,
    root_text: str = "",
    lexicon: ModelLexicon | None = None,
    limit: int | None = None,
) -> Selection:
    """Rank, then keep the top `limit` (default: the contract's `max_children`)."""
    config = ranking_config()
    ranked = rank_children(
        comments, version_aliases=version_aliases, root_text=root_text,
        lexicon=lexicon, config=config,
    )
    keep = config.max_children if limit is None else limit
    return Selection(
        ranked=tuple(ranked),
        selected=tuple(ranked[:keep]),
        subjects=thread_subjects(root_text, lexicon),
        tiers_observed=dict(Counter(r.relevance for r in ranked)),
    )


#: How much of each comment the E3 log shows. Matches the E5 quote width in
#: `scripts/fetch_model.py` (CONSOLE_QUOTE_CHARS) so the two blocks read alike.
EXCERPT_CHARS = 150

#: Comments BELOW the cut shown per thread, so the log shows what the ranking
#: dropped as well as what it kept - the only way to judge a cut by reading it.
DROPPED_SHOWN = 5


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    """One line of a comment for the log: whitespace collapsed, cut with `...`."""
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def selection_lines(
    thread_id: str, selection: Selection, *, dropped_shown: int = DROPPED_SHOWN
) -> list[str]:
    """The E3 log block for one thread.

    A summary line; then every KEPT child as its score breakdown with the
    comment's text beneath it; then the first `dropped_shown` children below the
    cut, marked `dropped`, so the boundary the ranking drew is visible.
    """
    observed = len(selection.ranked)
    kept = len(selection.selected)
    tiers = " ".join(
        f"{tier}={selection.tiers_observed.get(tier, 0)}"
        for tier in TIERS if selection.tiers_observed.get(tier)
    ) or "none"
    subjects = ", ".join(sorted(selection.subjects)) if selection.subjects else "none named"
    lines = [
        f"    {thread_id}: kept {kept} of {observed} comment(s) | first-hand "
        f"{selection.first_hand_selected} kept / {selection.first_hand_observed} seen"
        f" | subject: {subjects} | tiers seen: {tiers}"
    ]
    for rank, child in enumerate(selection.selected, start=1):
        lines.append(f"      #{rank:<2} {child.describe()}  {child.external_id}")
        lines.append(f'            "{excerpt(child.member.body)}"')
    below = selection.ranked[kept:kept + dropped_shown]
    if below:
        lines.append(
            f"      -- dropped: showing {len(below)} of {observed - kept} below the cut --"
        )
        for rank, child in enumerate(below, start=kept + 1):
            lines.append(f"      #{rank:<2} {child.describe()}  {child.external_id}  dropped")
            lines.append(f'            "{excerpt(child.member.body)}"')
    return lines
