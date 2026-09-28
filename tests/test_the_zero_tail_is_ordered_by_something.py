"""#307: 84% of replies score zero, and the ranking ordered them alphabetically.

Filed by @anoojntglobal-sudo, who picked two of four options and asked for both:

    option 1   order the zero tail by specificity      SHIPPED HERE
    option 4   pass `root_text` into `rank_children`   MEASURED, NOT SPENT
    option 2   rejected - reaches 9 of 848
    option 3   deferred - needs a version bump and a re-flatten

⚠ OPTION 4 REGRESSED THE ACCEPTANCE CASE, WHICH IS WHY IT IS NOT APPLIED. The
  existing test `test_a_version_and_error_comment_outranks_a_bare_reaction` is
  the one that says why this ranking exists at all, and inheriting the root's
  version token broke it on the first run:

      claude sonnet 4 throws JSONDecodeError at 6 tools, tool_choice=auto
          own 0.800  x log1p(1)   = 0.555      1 vote
      same lol
          own 0.000  x log1p(500) = 0.000      500 votes
          INHERITED 0.150 x log1p(500) = 0.932   <- wins

  The cause is general. Inheritance adds a flat `names_version` weight (0.15 of
  1.0) to every child that does not name the version, so a zero-specificity
  comment becomes `0.15 x log1p(votes)` and **the whole zero tail is then
  ordered by vote count alone** - the "one very popular joke outranks several
  specific corrections" failure `log1p` exists to damp, arriving through the
  term meant to fix the tail.

  `names_version` does two jobs: it identifies the SUBJECT and it earns
  SPECIFICITY weight. A reply inherits the first and has not earned the second,
  and the composite cannot separate them. Separating them is option 3.

  So `subject_inherited` and `would_score` are recorded, the report prints the
  share, and the score is untouched until there is a number to rule on.

⚠ AND OPTION 1 STILL DOES THE WORK IT WAS PICKED FOR, which is the part worth
  checking rather than assuming. The tail is zero because `log1p(0) = 0` on a
  comment with no votes, NOT because its specificity is zero - a two-line
  correction naming a version and an error scores 0.80 and still multiplies to
  0.0 against no votes. Ordering that tail by specificity reaches exactly those
  comments, with no help from inheritance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from collect.assemble.thread import rank_children
from collect.triage.specificity import score_document, score_if_version_inherited, weights

ALIASES = ["claude sonnet 4", "sonnet 4"]

ROOT_NAMES_IT = "anyone else seeing claude sonnet 4 drop tool calls?"
ROOT_NAMES_NOTHING = "anyone else seeing this drop tool calls?"

SPECIFIC = "claude sonnet 4 throws JSONDecodeError at 6 tools, tool_choice=auto"
SPECIFIC_ANAPHORIC = "it throws JSONDecodeError at 6 tools when tool_choice=auto"
BARE = "same lol"


@dataclass(frozen=True)
class _Comment:
    external_id: str
    body: str
    score: int | None


def _rank(comments, root=ROOT_NAMES_IT):
    return rank_children(tuple(comments), version_aliases=ALIASES, root_text=root)


class TestTheZeroTailIsOrderedBySpecificity:
    def test_a_specific_comment_with_no_votes_outranks_an_empty_one(self):
        """The whole of option 1. Both multiply to 0.0, so before this they
        sorted on `external_id` - which is arrival order presented as
        relevance."""
        bare = _Comment("t1_aaa", BARE, score=0)
        specific = _Comment("t1_zzz", SPECIFIC, score=0)
        ranked = _rank([bare, specific])
        assert [r.member.external_id for r in ranked] == ["t1_zzz", "t1_aaa"]

    def test_both_still_score_zero(self):
        """⚠ THE TIE-BREAK DOES NOT INVENT A SCORE. If ordering the tail had
        been done by nudging the product off zero, every figure downstream that
        reads `score` would have shifted with it."""
        ranked = _rank([_Comment("t1_a", BARE, 0), _Comment("t1_z", SPECIFIC, 0)])
        assert [r.score for r in ranked] == [0.0, 0.0]

    def test_external_id_is_still_the_final_key(self):
        """A re-run must produce the same row. Two comments with identical
        specificity and identical engagement still order deterministically."""
        first = _rank([_Comment("t1_b", BARE, 0), _Comment("t1_a", BARE, 0)])
        second = _rank([_Comment("t1_a", BARE, 0), _Comment("t1_b", BARE, 0)])
        assert [r.member.external_id for r in first] == ["t1_a", "t1_b"]
        assert [r.member.external_id for r in first] == [
            r.member.external_id for r in second
        ]

    def test_the_tail_is_zero_from_votes_and_not_from_specificity(self):
        """The premise of option 1, checked rather than assumed. If the tail
        were zero because specificity were zero, ordering it by specificity
        would order it by nothing all over again."""
        specificity = score_document(SPECIFIC, version_aliases=ALIASES).score
        assert specificity > 0.5
        assert specificity * math.log1p(0) == 0.0


class TestInheritanceIsMeasuredAndNotSpent:
    def test_the_acceptance_case_still_holds(self):
        """⚠ THIS IS THE TEST OPTION 4 BROKE. A bare reaction with 500 votes
        must not outrank a correction naming a version, an error and a
        condition at 1 vote."""
        reaction = _Comment("t1_reaction", BARE, score=500)
        specific = _Comment("t1_specific", SPECIFIC, score=1)
        ranked = _rank([reaction, specific])
        assert ranked[0].member.external_id == "t1_specific"

    def test_spending_the_inheritance_would_break_it(self):
        """The measurement, kept executable so the argument on #307 option 3
        is re-checkable rather than quoted. If this ever stops holding, the
        weights moved and the whole trade-off needs re-reading."""
        reaction = score_document(BARE, version_aliases=ALIASES)
        specific = score_document(SPECIFIC, version_aliases=ALIASES)
        would = score_if_version_inherited(reaction) * math.log1p(500)
        actual = specific.score * math.log1p(1)
        assert reaction.score * math.log1p(500) == 0.0
        assert would > actual, "the regression this records has gone away"

    def test_the_flag_is_set_where_the_root_names_it_and_the_child_does_not(self):
        anaphoric = _Comment("t1_it", SPECIFIC_ANAPHORIC, score=3)
        [ranked] = _rank([anaphoric])
        assert ranked.subject_inherited is True
        assert ranked.would_score > ranked.specificity

    def test_it_is_not_set_where_the_child_names_it_itself(self):
        """Inheriting on top of a component already counted would double it."""
        [ranked] = _rank([_Comment("t1_own", SPECIFIC, score=3)])
        assert ranked.subject_inherited is False
        assert ranked.would_score == ranked.specificity

    def test_it_is_not_set_where_the_root_names_nothing(self):
        """A root with no version token has no subject to pass down, so an
        anaphoric reply under it is genuinely unattributed rather than
        inheriting."""
        [ranked] = _rank([_Comment("t1_it", SPECIFIC_ANAPHORIC, 3)], root=ROOT_NAMES_NOTHING)
        assert ranked.subject_inherited is False

    def test_the_flag_changes_no_score(self):
        """⚠ THE ONE PROPERTY THE WHOLE DECISION RESTS ON. Measured and not
        spent means the ranking is bit-identical to what it would be with the
        flag absent."""
        comments = [
            _Comment("t1_it", SPECIFIC_ANAPHORIC, 3),
            _Comment("t1_own", SPECIFIC, 3),
            _Comment("t1_bare", BARE, 500),
        ]
        under_root = _rank(comments)
        without = _rank(comments, root=ROOT_NAMES_NOTHING)
        assert [r.score for r in under_root] == [r.score for r in without]
        assert any(r.subject_inherited for r in under_root)
        assert not any(r.subject_inherited for r in without)


class TestRootTextIsRequired:
    def test_it_has_no_default(self):
        """A default of `""` would report that no thread names anything, which
        is the defect arriving silently in whichever caller forgot. Same reason
        `child_document_id` has no default."""
        import inspect

        parameter = inspect.signature(rank_children).parameters["root_text"]
        assert parameter.default is inspect.Parameter.empty
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


class TestTheWeightsThisReasoningUses:
    def test_names_version_is_a_minority_weight(self):
        """The regression's size is `names_version / sum(weights)`. Recorded as
        a test rather than a number in prose (rule 11) because the contract can
        change and the argument on #307 would then be about a figure that no
        longer holds."""
        w = weights()
        assert 0 < w["names_version"] / sum(w.values()) < 0.5
