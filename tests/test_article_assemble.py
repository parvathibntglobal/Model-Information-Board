"""E3 over a blog article: the one-member thread, and what it makes unreachable.

The widening in `collect/assemble/thread.py` existed for this. `assemble` no
longer knows a platform and `child_document_id` is required, so a blog row
cannot inherit `reddit:` ids by omission.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from collect.assemble.article import (
    BLOG_SOURCE,
    ArticleInput,
    assemble_article,
    blog_document_id,
    document_row,
)
from collect.assemble.thread import SELECTION_METHOD, WHOLE_DOCUMENT
from collect.rawstore import RawStore

ENTRY = "https://simonwillison.net/2026/Aug/13/sqlite-utils-2/"


def _store() -> RawStore:
    return RawStore(Path(tempfile.mkdtemp()))


def _assemble(text: str):
    return assemble_article(ArticleInput(ENTRY, text), store=_store())


# ── the rulings ───────────────────────────────────────────────────────────


def test_selection_method_says_nothing_was_selected():
    """`whole_document`, not a ranking that did not happen."""
    assembled = _assemble("The context window degrades past 200k tokens.")
    assert assembled.selection_method == WHOLE_DOCUMENT
    assert assembled.selection_method != SELECTION_METHOD
    assert assembled.selection_method != "specificity_x_log_engagement", "schema default"
    assert "@observed" not in assembled.selection_method
    assert assembled.child_count == 0


def test_hidden_children_min_is_null_because_we_withheld_the_comments():
    """Rule 6. `include_comments=False` is us, not the platform.

    0 would assert "nothing was withheld". A post with 400 comments and one with
    none would then write the same value, and the error leans towards flattering
    our own coverage.
    """
    assembled = _assemble("body text")
    assert assembled.hidden_children_min is None
    assert assembled.observed_children == 0, "a measurement: we looked, none stored"
    assert assembled.hidden_branches_unsized == 0, "a measurement: no markers exist"


def test_coverage_ratio_is_never_written_for_a_blog_either():
    """GENERATED ALWAYS rejects an explicit value, NULL included."""
    row = _assemble("body text").as_row()
    assert "coverage_ratio" not in row


def test_entity_decoding_is_off_so_trafilatura_output_survives_intact():
    """The third decode. Rule 1 cannot catch it: verification is a substring
    match against this same text, so both sides sit downstream of the decode."""
    arrived = "use a &gt; b to redirect"
    assembled = _assemble(arrived)
    assert assembled.flattened.text == arrived
    assert assembled.flattened.substitutions == 0


def test_symbols_are_still_substituted_and_that_is_known_wrong():
    """`So` stays global pending a corpus. Pinned so a narrowing is deliberate."""
    assembled = _assemble("Runs at 72°C — ship it \U0001f604")
    assert "[degree_sign]" in assembled.flattened.text
    assert "[smiling_face_with_open_mouth_and_smiling_eyes]" in assembled.flattened.text


# ── what a thread of one makes unreachable ────────────────────────────────


def test_span_crosses_comments_cannot_fire_on_a_one_member_thread():
    """One document_id in every segment, so the check has nothing to compare."""
    from judge.extract.verify import OffsetMapping, VerificationFailure

    assembled = _assemble("Opus 5 \U0001f604 held up \U0001f62e past 200k tokens.")
    mappings = [
        OffsetMapping(
            flat_start=s["flat_start"], flat_end=s["flat_end"],
            document_id=s["document_id"],
            raw_start=s["raw_start"], raw_end=s["raw_end"],
        )
        for s in assembled.as_row()["offset_map"]
    ]
    assert len({m.document_id for m in mappings}) == 1, (
        "SPAN_CROSSES_COMMENTS requires >1 distinct document_id in the "
        "overlapping segments; a thread of one can never supply a second"
    )
    assert VerificationFailure.SPAN_CROSSES_COMMENTS  # the reason still exists


def test_the_offset_map_of_one_document_is_gapless_so_no_span_is_unmapped():
    """`flatten` emits the JOINER only BETWEEN documents, so with one document
    there is no unmapped region at all — which is why UNMAPPED_SPAN cannot fire
    for an in-range span here."""
    assembled = _assemble("Runs at 72°C. Fast ✅ and \U0001f604 done.")
    spans = sorted(
        (s["flat_start"], s["flat_end"]) for s in assembled.as_row()["offset_map"]
    )
    cursor = 0
    for start, end in spans:
        assert start == cursor, f"hole at {cursor}..{start}"
        cursor = end
    assert cursor == len(assembled.flattened.text)
    assert "\n\n---\n\n" not in assembled.flattened.text, "no joiner with one member"


# ── ids and the document row ───────────────────────────────────────────────


def test_no_blog_id_can_acquire_the_reddit_prefix():
    assembled = _assemble("body")
    assert assembled.thread_root_id == blog_document_id(ENTRY)
    assert all(i.startswith("blog:") for i in assembled.member_document_ids)
    assert not any("reddit:" in i for i in assembled.member_document_ids)


def test_document_source_is_the_platform_not_the_feed():
    """`judge/store/cells.py` reads `document.source` AS the platform, so a feed
    id here would make two blogs count as two platforms in `platform_count`."""
    row = document_row(
        ArticleInput(ENTRY, "body", url=ENTRY),
        text_ref="raw/sha256/ab/cd/abcd", content_hash="abcd",
    )
    assert row["source"] == BLOG_SOURCE == "blog"
    assert "simonwillison" not in row["source"], "the feed is not the platform"
    assert row["status"] == "kept"


def test_an_empty_extraction_refuses_rather_than_assembling_nothing():
    """`extract_article_text` returns None for a nav page or a JS shell. A
    thread_context over an empty string rejects every quote as TEXT_MISMATCH,
    which reads as a fabricating extractor rather than as a missing article."""
    with pytest.raises(ValueError, match="nothing was extracted"):
        assemble_article(ArticleInput(ENTRY, ""), store=_store())
