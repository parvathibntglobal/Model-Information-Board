"""Topic and signal must be near each other. Subject may be anywhere.

THE DOCUMENT THAT ARGUED FOR THIS was the only one the first nine-feed blog
harvest kept: `vickiboykis.com/2026/04/20/build-yourself-flowers/`, 41,956
characters, filed `extraction.faithfulness:positive`.

    subject  `flash 2.5`  "ran it through gemini flash 2.5 ... to break into
                          paragraphs"           — genuine
    topic    `extract`    "i extracted each entry ... full metadata"
                          — a museum API, not the model
    signal   `held up`    "you're just going to get held up with your product"
                          — meaning DELAYED, 3,899 characters away

Three unrelated passages in one long essay, counted as one claim, because
nothing required them to be near each other.

The shapes below are SYNTHETIC and reproduce the real distances. The real
article is not checked in: `fixtures/blog/README.md` forbids real captures,
and 42,000 characters of somebody's personal essay in this repository is the
thing NFR-5 exists to prevent — quote, attribution and link, never full text.
The measured distances are the part that matters and they are preserved.
"""

from __future__ import annotations

import pytest

from collect.adapters.queries.contract import TermSet
from collect.adapters.queries.sieve import default_locality_window, sieve, sieve_any

ALIAS = "gemini-2.5-flash"

TERMS = TermSet(
    subject=(ALIAS,),
    topic=("extract",),
    signal=("held up",),
).substitute(ALIAS)


def document(*, subject_at: int, topic_at: int, signal_at: int, length: int = 42_000) -> str:
    """Filler with the three groups planted at exact offsets."""
    text = ["x"] * length
    for offset, phrase in (
        (subject_at, ALIAS),
        (topic_at, "extracted"),
        (signal_at, "held up"),
    ):
        for index, char in enumerate(f" {phrase} "):
            text[offset + index] = char
    return "".join(text)


# ── the rule ──────────────────────────────────────────────────────────────


def test_the_real_shape_is_rejected():
    """Topic and signal 3,899 apart, as measured on the live document."""
    verdict = sieve(TERMS, document(subject_at=20_000, topic_at=8_000, signal_at=11_899))
    assert not verdict.passed
    assert verdict.missing == ("locality",)


def test_the_same_document_passed_before_locality_existed():
    """`window=None` is the pre-2026-08-14 behaviour, and it still kept this."""
    verdict = sieve(
        TERMS,
        document(subject_at=20_000, topic_at=8_000, signal_at=11_899),
        window=None,
    )
    assert verdict.passed


def test_subject_may_be_as_far_away_as_it_likes():
    """Naming the model once is how a post establishes what it is about.

    Intro-to-conclusion is the ordinary shape of a blog post, not the
    exception, so constraining subject would have cost the normal case to
    catch the abnormal one.
    """
    verdict = sieve(TERMS, document(subject_at=41_000, topic_at=100, signal_at=300))
    assert verdict.passed, "subject 40,000 characters away must not fail it"


def planted_gap(gap: int) -> str:
    """A document whose topic and signal are EXACTLY `gap` characters apart.

    `document` pads each phrase with a space either side, so the offsets it is
    given are not the span boundaries. Computed rather than approximated,
    because a boundary test that is off by two tests the wrong boundary.
    """
    topic_at = 1_000
    topic_end = topic_at + len(" extracted")     # span ends after the word
    return document(
        subject_at=30_000, topic_at=topic_at, signal_at=topic_end + gap - 1
    )


@pytest.mark.parametrize("gap", [0, 100, 496, 1_199, 1_200])
def test_a_pair_inside_the_window_passes(gap):
    verdict = sieve(TERMS, planted_gap(gap))
    assert verdict.passed, f"gap {gap} is inside the {default_locality_window()} window"


@pytest.mark.parametrize("gap", [1_201, 1_400, 3_899, 10_000])
def test_a_pair_outside_the_window_does_not(gap):
    verdict = sieve(TERMS, planted_gap(gap))
    assert not verdict.passed
    assert verdict.missing == ("locality",)


def test_the_boundary_is_where_the_contract_says():
    """1200 passes and 1201 does not — the window is inclusive."""
    window = default_locality_window()
    assert sieve(TERMS, planted_gap(window)).passed
    assert not sieve(TERMS, planted_gap(window + 1)).passed


def test_order_does_not_matter():
    """Signal before topic is the same distance as topic before signal."""
    forward = sieve(TERMS, document(subject_at=30_000, topic_at=1_000, signal_at=1_400))
    backward = sieve(TERMS, document(subject_at=30_000, topic_at=1_400, signal_at=1_000))
    assert forward.passed is backward.passed is True


def test_the_nearest_pair_decides_it():
    """One distant topic mention must not veto a near one.

    A blog post that mentions the topic in passing early and then discusses it
    properly next to the claim should pass on the second mention.
    """
    text = document(subject_at=30_000, topic_at=100, signal_at=20_000)
    planted = list(text)
    for index, char in enumerate(" extracted "):
        planted[19_800 + index] = char
    assert sieve(TERMS, "".join(planted)).passed


# ── locality is its own failure, not a missing group ──────────────────────


def test_too_far_apart_is_distinguishable_from_absent():
    """Three states, and collapsing them would lose the vocabulary feedback.

    "the term is not here", "the term is here but only somebody else said it",
    and "both terms are here but in unrelated passages" are different facts
    about a document and want different responses.
    """
    far = sieve(TERMS, document(subject_at=100, topic_at=8_000, signal_at=20_000))
    absent = sieve(TERMS, document(subject_at=100, topic_at=8_000, signal_at=8_100)
                   .replace("held up", "xxxx xx"))

    assert far.missing == ("locality",)
    assert absent.missing == ("signal",)
    assert far.topic and far.signal, "both groups matched; only the distance failed"
    assert absent.topic and not absent.signal


def test_locality_is_not_checked_when_a_group_is_already_missing():
    """`missing` names the first thing wrong, and absence outranks distance."""
    verdict = sieve(TERMS, document(subject_at=100, topic_at=8_000, signal_at=20_000)
                    .replace("gemini-2.5-flash", "someone-elses-model"))
    assert "subject" in verdict.missing
    assert "locality" not in verdict.missing


def test_signal_still_has_to_be_the_authors_own_words():
    """Locality is an extra condition, not a replacement for containment."""
    text = document(subject_at=100, topic_at=1_000, signal_at=1_200)
    quoted = text.replace(" held up ", " `held up` ")
    verdict = sieve(TERMS, quoted)
    assert not verdict.passed
    assert "signal" in verdict.missing
    assert "held up" in verdict.signal_in_excluded


# ── the wrapper must not lose the option ──────────────────────────────────
#
# `sieve_any` is now the site of THREE defects the tests were silent about:
# it returned the last failing verdict rather than the furthest, it did not
# forward `window` at all, and — found by auditing the first two — no test
# ever passed `window` to it, so the forwarding fix had no guard either.
#
# All three are the same shape: a wrapper that loses something on the way
# through. Its own docstring says callers are steered towards it "so it cannot
# be used the wrong way by accident", which makes a dropped option worse here
# than anywhere else in the module.


def test_sieve_any_forwards_the_window():
    """It did not, and nothing failed. That is the defect this pins."""
    far = document(subject_at=20_000, topic_at=8_000, signal_at=11_899)

    assert sieve_any([TERMS], far, window=None).passed, "window=None must reach sieve"
    assert not sieve_any([TERMS], far, window=1200).passed
    assert not sieve_any([TERMS], far).passed, "the contract default must apply"


def test_sieve_any_and_sieve_agree_when_given_the_same_window():
    """A wrapper that disagrees with what it wraps is worse than no wrapper."""
    for gap in (100, 3_899):
        text = planted_gap(gap)
        for window in (None, 600, 1200, 6000):
            assert (
                sieve_any([TERMS], text, window=window).passed
                == sieve(TERMS, text, window=window).passed
            ), f"disagreement at gap={gap} window={window}"


def test_sieve_any_still_returns_the_furthest_verdict_when_none_passes():
    """The first defect, re-pinned alongside the others it keeps company with.

    A locality failure is 'furthest' — subject, topic and signal all matched —
    so it must win over a variant that missed a group outright.
    """
    wrong_alias = TermSet(
        subject=("some-other-model",), topic=("extract",), signal=("held up",)
    ).substitute("some-other-model")
    far = document(subject_at=20_000, topic_at=8_000, signal_at=11_899)

    verdict = sieve_any([wrong_alias, TERMS], far, window=1200)
    assert not verdict.passed
    assert verdict.missing == ("locality",), (
        "the furthest verdict is the one that matched all three groups, not "
        "the one that missed the subject"
    )


# ── the configured number ─────────────────────────────────────────────────


def test_the_window_comes_from_the_contract():
    """Rule 5: a threshold lives in versioned YAML, not in code."""
    import yaml

    from collect.config import CONTRACT_DIR

    raw = yaml.safe_load((CONTRACT_DIR / "harvest.yaml").read_text(encoding="utf-8"))
    assert raw["sieve"]["locality_window"] == default_locality_window() == 1200


def test_an_absent_setting_means_no_window_rather_than_a_default(tmp_path, monkeypatch):
    """Rule 6 at the config boundary: absent must not become definite.

    A contract predating this key reads as "no locality", which is what it
    meant when it was written — not as whatever number happens to be current.
    """
    import importlib

    module = importlib.import_module("collect.adapters.queries.sieve")

    older = tmp_path / "contract"
    older.mkdir()
    (older / "harvest.yaml").write_text(
        "version: '1.0'\ncadence_days:\n  daily: 1\n", encoding="utf-8"
    )
    monkeypatch.setattr("collect.config.CONTRACT_DIR", older)
    module.default_locality_window.cache_clear()
    try:
        assert module.default_locality_window() is None
    finally:
        # Undo before re-reading, or the cache repopulates from tmp_path and
        # every later test in the session inherits a window of None.
        monkeypatch.undo()
        module.default_locality_window.cache_clear()

    assert default_locality_window() == 1200, "the real contract still carries it"
