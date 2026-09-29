"""E3's flattener, and the map that cannot be rebuilt afterwards.

`collect/CLAUDE.md`: `offset_map` is about ten lines while you are already
walking the tree and impossible to reconstruct later, so every quote extracted
against a wrong one has to be re-extracted — and extraction is the only paid
stage. **This is the one piece where a defect is expensive rather than merely
wrong**, which is why the first test is byte equality against a map built
independently and the rest are the cases that map cannot reach.
"""

from __future__ import annotations

import json

import pytest

from collect.assemble.flatten import (
    JOINER,
    Segment,
    flatten,
    flatten_document,
    substitute,
)
from collect.config import REPO_ROOT

FIXTURE = REPO_ROOT / "fixtures" / "threads" / "thread-1u1b22l.json"


@pytest.fixture(scope="module")
def reference() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# ── the first test, and the one that matters most ────────────────────────


def test_byte_equality_with_the_reference_flattening(reference):
    """Two independent implementations of one specification, on real data.

    `fixtures/threads/build.py` is Engineer 2's, built from the raw payload for
    `verify.py` to test against. This module is E3's, written from
    `contract/tables.sql` and the fixture's observable properties without
    reading hers.

    Until they agreed, neither had evidence for being right: hers had only ever
    been checked against its own output, and mine had never been run.

    The first agreement was over six documents that agreed everywhere either had
    looked. **The seventh, added 2026-08-18, is the first thing either
    implementation met that the other had not already agreed on** — and it is a
    shrinking substitution, the direction neither had exercised. That run is the
    real test; the first was a rerun.
    """
    documents = [
        (doc_id, reference["raw_text_of"][doc_id])
        for doc_id in reference["member_document_ids"]
    ]
    assert flatten(documents).text == reference["flattened_text"]


def test_the_offset_map_matches_segment_for_segment(reference):
    """Byte equality of the text is not enough. The same string can be produced
    with a different segmentation, and it is the segmentation `verify.py`
    resolves against."""
    documents = [
        (doc_id, reference["raw_text_of"][doc_id])
        for doc_id in reference["member_document_ids"]
    ]
    assert flatten(documents).as_offset_map() == reference["offset_map"]


def test_the_reference_actually_exercises_substitutions(reference):
    """Habit 4: a check that iterates must count what it iterated over.

    Byte equality over a fixture with no substitutions would prove nothing and
    would look identical to this passing.
    """
    documents = [
        (doc_id, reference["raw_text_of"][doc_id])
        for doc_id in reference["member_document_ids"]
    ]
    result = flatten(documents)
    assert len(result.segments) == 22
    assert result.substitutions == 11
    assert len(result.member_document_ids) == 7

    # THE SEVENTH DOCUMENT, added 2026-08-18, is the one that makes this
    # fixture reach an entity at all — and it is a SHRINKING substitution,
    # 4 raw characters to 1 flat, where the other ten grow.
    shrinking = [
        seg for seg in result.segments
        if not seg.is_identity
        and (seg.raw_end - seg.raw_start) > (seg.flat_end - seg.flat_start)
    ]
    assert len(shrinking) == 1, "the &gt; case"
    assert shrinking[0].raw_end - shrinking[0].raw_start == 4


# ── the entity case, which the reference cannot reach ────────────────────
#
# Six `body` fields in the source payload carry entities and NONE of the six
# documents the reference selected is among them. So these are the rules that
# fixture cannot check, and each is its own test.


def test_an_entity_is_a_shrinking_substitution():
    """`&gt;` is 4 raw characters and 1 flat. The first shrink.

    Every substitution in the reference grows — emoji at 1 character to 12–47.
    Nothing in `_resolve_raw_span` cares about the direction, and nothing had
    ever exercised the other one.
    """
    text, segments = flatten_document("&gt;quoted", "d1")
    assert text == ">quoted"
    assert segments[0] == Segment(0, 1, "d1", 0, 4)
    assert not segments[0].is_identity
    assert segments[1] == Segment(1, 7, "d1", 4, 10)
    assert segments[1].is_identity


def test_unescape_happens_exactly_once():
    """`&amp;gt;` is a literal somebody typed. Decoding twice turns their text
    into markup they did not write.

    Structural rather than checked: the walk consumes `&amp;`, emits `&`, and
    resumes AFTER it, so `gt;` is never re-examined.
    """
    text, segments = flatten_document("&amp;gt;", "d1")
    assert text == "&gt;"
    assert text != ">"
    assert segments[0] == Segment(0, 1, "d1", 0, 5)


def test_only_reddits_five_entities_are_decoded():
    """A general unescaper would rewrite `&copy;` and `&mdash;` too, which a
    user may have typed literally. That is a change to authorship rather than
    to transport."""
    text, segments = flatten_document("&copy; &mdash; &nbsp;", "d1")
    assert text == "&copy; &mdash; &nbsp;"
    assert len(segments) == 1
    assert segments[0].is_identity


def test_an_ampersand_inside_a_url_is_still_a_substitution():
    """From the payload: `?width=1444&amp;format=png&amp;auto=webp`.

    Two substitutions inside one URL. The only hazard is a quote starting
    mid-URL, which takes the whole substitution — and that is correct.
    """
    raw = "https://x.invalid/a?w=1&amp;f=png&amp;auto=webp"
    text, segments = flatten_document(raw, "d1")
    assert text == "https://x.invalid/a?w=1&f=png&auto=webp"
    assert sum(1 for s in segments if not s.is_identity) == 2


def test_entities_are_decoded_before_symbols_are_substituted():
    """Ruled 2026-08-18. Entities undo how the text ARRIVED; symbols change how
    it READS, so decoding first means everything downstream operates on what the
    person typed.

    `&gt;😄` is the case where the order shows: both rewrites are adjacent, and
    doing symbols first would substitute into a string still carrying `&gt;`.
    """
    text, segments = flatten_document("&gt;\U0001f604", "d1")
    assert text == ">[smiling_face_with_open_mouth_and_smiling_eyes]"
    assert segments[0] == Segment(0, 1, "d1", 0, 4)       # &gt; -> >
    assert segments[1].raw_start == 4 and segments[1].raw_end == 5  # the emoji
    assert not segments[1].is_identity


# ── the substitution rule, measured from the reference ───────────────────


def test_only_category_so_is_substituted():
    """Not "emoji". `█` FULL BLOCK is not one and is substituted; `’` is
    RIGHT SINGLE QUOTATION MARK, category `Pf`, and is kept.

    Read off the reference fixture rather than chosen.
    """
    assert substitute("\U0001f604") == "[smiling_face_with_open_mouth_and_smiling_eyes]"
    assert substitute("█") == "[full_block]"
    assert substitute("’") is None
    assert substitute("a") is None


def test_a_symbol_with_no_unicode_name_is_kept():
    """`[]` is worse than a character the extractor can at least see."""
    assert substitute("\U000e0000") is None


def test_consecutive_substitutions_stay_separate():
    """Seven `█` in the reference produce seven segments, not one.

    Merging would break `_resolve_raw_span`: a substitution is taken whole, so a
    merged run of seven would map a quote touching one block to all seven.
    """
    _text, segments = flatten_document("█" * 7, "d1")
    assert len(segments) == 7
    assert all(not s.is_identity for s in segments)


# ── the joiner ───────────────────────────────────────────────────────────


def test_the_joiner_belongs_to_no_segment():
    """A quote spanning it overlaps two documents, so `verify.py` returns
    SPAN_CROSSES_COMMENTS. Leaving it unmapped makes that automatic."""
    result = flatten([("d1", "first"), ("d2", "second")])
    covered = set()
    for s in result.segments:
        covered.update(range(s.flat_start, s.flat_end))
    joiner_range = set(range(len("first"), len("first") + len(JOINER)))
    assert not (covered & joiner_range)


def test_a_single_document_gets_no_joiner():
    result = flatten([("d1", "only")])
    assert result.text == "only"


# ── the round trip through the consumer ──────────────────────────────────


def test_a_quote_resolves_back_through_verify(reference):
    """The actual contract: `judge/extract/verify.py` must resolve a span this
    module produced back to the raw text it came from.

    Byte equality proves the string; this proves the map is usable by the thing
    that exists to use it.
    """
    from judge.extract.verify import OffsetMapping, _resolve_raw_span

    documents = [
        (doc_id, reference["raw_text_of"][doc_id])
        for doc_id in reference["member_document_ids"]
    ]
    result = flatten(documents)
    mappings = [OffsetMapping(**s.as_dict()) for s in result.segments]

    # A span inside the reply that carries an emoji, chosen so it crosses an
    # identity run and stops before the substitution.
    #
    # The document is found by SUFFIX rather than named in full. It was written
    # `reddit:oqosfnq`, and the id convention moved under it when the fixture
    # took the `t1_` fullnames `collect/` actually stores - so this test failed
    # only in the merge, passing on both branches alone. A literal id here is a
    # second place the convention has to be remembered, and this is the file
    # that proves conventions do not get remembered.
    document_id = next(
        d for d in reference["member_document_ids"] if d.endswith("oqosfnq")
    )
    target = next(s for s in result.segments if s.is_identity and s.raw_start == 0
                  and s.document_id == document_id)
    start, end = target.flat_start, target.flat_end
    overlapping = [m for m in mappings if m.overlaps(start, end)]
    raw_start, raw_end = _resolve_raw_span(overlapping, start, end)

    raw = reference["raw_text_of"][document_id]
    assert raw[raw_start:raw_end] == result.text[start:end]


# ── the assembler, end to end on the real payload ────────────────────────


def test_assembly_over_the_real_thread_selects_and_maps():
    """The write path's inputs, on the payload the fixture was built from.

    Not a database test — that ran against staging and is reported in
    `docs/measurements/first-thread-context.md`. This pins the shape so a
    change to selection or flattening fails here rather than there.
    """
    import json as _json
    import tempfile
    from pathlib import Path as _Path

    from collect.adapters.reddit import reddit_document_id
    from collect.adapters.reddit_comments import parse_thread
    from collect.assemble.thread import SELECTION_METHOD, assemble
    from collect.rawstore import RawStore

    payload = _json.loads(
        (REPO_ROOT / "fixtures" / "reddit" / "thread-1u1b22l-getPostComments.json")
        .read_text(encoding="utf-8")
    )
    thread = parse_thread(payload, url="https://www.reddit.com/r/ClaudeAI/x/")
    root = payload["data"][0]["data"]["children"][0]["data"]
    root_text = (root.get("title", "") + "\n\n" + (root.get("selftext") or "")).strip()

    assembled = assemble(
        thread,
        root_text=root_text,
        root_document_id=reddit_document_id(root.get("name")),
        child_document_id=lambda c: reddit_document_id(c.external_id),
        store=RawStore(_Path(tempfile.mkdtemp())),
        version_aliases=(),
    )

    # The contract's cap (`child_ranking.max_children`, 25 since 2026-09-24),
    # reached because 195 comments were observed.
    from collect.assemble.thread import MAX_CHILDREN

    assert assembled.child_count == MAX_CHILDREN
    assert len(assembled.member_document_ids) == MAX_CHILDREN + 1
    assert assembled.observed_children == 195
    assert assembled.hidden_children_min == 623

    # A REDDIT-SHAPED INVARIANT, AND IT IS STATED GLOBALLY. Scoped to this
    # test's Reddit thread on 2026-08-18: a one-member blog thread writes
    # `whole_document`, which has no `@observed` suffix and correctly has none,
    # because nothing was ranked. Same class as the three lane assertions
    # enforced on one side only — an invariant that was true of the only
    # platform there was, written as though it were true of the schema.
    # `test_a_one_member_thread_records_that_nothing_was_selected` is the
    # other half.
    # `selection_method` NEVER gets the schema default. The bare value asserts
    # a global ranking and 195 of 818 known-minimum comments is not one.
    assert assembled.selection_method == SELECTION_METHOD
    assert assembled.selection_method != "specificity_x_log_engagement"
    assert "@observed" in assembled.selection_method


def test_the_insert_omits_the_generated_column():
    """`coverage_ratio` is GENERATED ALWAYS, so Postgres rejects an explicit
    value — including an explicit NULL. Omitting the key is how it is written,
    and passing None would be an error rather than a no-op."""
    import tempfile
    from pathlib import Path as _Path

    from collect.adapters.reddit import reddit_document_id
    from collect.adapters.reddit_comments import ParsedThread, ThreadCoverage
    from collect.assemble.thread import assemble
    from collect.rawstore import RawStore

    thread = ParsedThread(
        root_post_id="t3_x",
        comments=(),
        coverage=ThreadCoverage(0, 0, 0, None, 0, 0),
    )
    assembled = assemble(
        thread, root_text="body", root_document_id="reddit:t3_x",
        child_document_id=lambda c: reddit_document_id(c.external_id),
        store=RawStore(_Path(tempfile.mkdtemp())), version_aliases=(),
    )
    row = assembled.as_row()
    assert "coverage_ratio" not in row
    assert "observed_children" in row


# ── the platform-neutral surface ──────────────────────────────────────────


def test_assemble_refuses_to_invent_a_child_document_id():
    """`child_document_id` is required, so no platform can inherit `reddit:`.

    `assemble` built child ids itself as `f"reddit:{c.external_id}"` while
    taking `root_document_id` from its caller — two conventions chosen in two
    modules for the two ids in one row. A default here, even a Reddit one, is
    what would let a blog row acquire `reddit:` silently, and a silent wrong id
    is only visible from the other lane.
    """
    import tempfile
    from pathlib import Path as _Path

    from collect.adapters.reddit_comments import ParsedThread, ThreadCoverage
    from collect.assemble.thread import assemble
    from collect.rawstore import RawStore

    thread = ParsedThread(
        root_post_id="t3_x", comments=(), coverage=ThreadCoverage(0, 0, 0, None, 0, 0)
    )
    with pytest.raises(TypeError, match="child_document_id"):
        assemble(
            thread,
            root_text="body",
            root_document_id="blog:example",
            store=RawStore(_Path(tempfile.mkdtemp())),
            version_aliases=(),
        )


def test_assemble_ranks_a_non_reddit_member_type():
    """`ThreadMember` is structural, so assembly is not about Reddit.

    Three attributes — `external_id`, `body`, `score`. This passes a type that
    is not `RedditComment` and never was, which is the whole content of the
    widening: ranking Reddit comments was what assembly DID, not what it is.
    """
    import tempfile
    from dataclasses import dataclass
    from pathlib import Path as _Path

    from collect.assemble.thread import assemble
    from collect.rawstore import RawStore

    @dataclass(frozen=True)
    class Note:
        external_id: str
        body: str
        score: int | None

    @dataclass(frozen=True)
    class Feed:
        root_post_id: str | None
        comments: tuple
        coverage: object

    @dataclass(frozen=True)
    class Coverage:
        observed_children: int
        hidden_children_min: int | None
        hidden_branches_unsized: int

    feed = Feed(
        root_post_id="hn:1",
        comments=(
            Note("a", "the context window degrades past 200k tokens", 40),
            Note("b", "same", 2),
        ),
        coverage=Coverage(2, 0, 0),
    )
    assembled = assemble(
        feed,
        root_text="root text",
        root_document_id="hn:1",
        child_document_id=lambda c: f"hn:{c.external_id}",
        store=RawStore(_Path(tempfile.mkdtemp())),
        version_aliases=(),
    )
    assert assembled.member_document_ids[0] == "hn:1"
    assert all(i.startswith("hn:") for i in assembled.member_document_ids), (
        "a non-Reddit thread must not acquire reddit: ids"
    )
    assert not any("reddit:" in i for i in assembled.member_document_ids)
    assert assembled.child_count == 2


# ── per-platform flattening rules (ruled 2026-08-18) ──────────────────────


def test_blog_rules_do_not_decode_entities_because_trafilatura_already_did():
    """A third decode is not a no-op, and rule 1 cannot catch it.

    trafilatura decodes twice — measured against bare lxml — so text reaching
    the flattener has already been unescaped. Triple-encoded input arrives here
    as `&gt;`, and Reddit's rules would turn it into `>`: text the author never
    wrote, which then verifies by exact substring match against our own stored
    copy and is attributed to them correctly. Verified and wrong.
    """
    from collect.assemble.flatten import BLOG_RULES, REDDIT_RULES, flatten_document

    arrived_from_trafilatura = "type &gt; here"

    reddit_text, _ = flatten_document(arrived_from_trafilatura, "d", rules=REDDIT_RULES)
    assert reddit_text == "type > here", "Reddit's rules decode, which is correct there"

    blog_text, blog_segments = flatten_document(
        arrived_from_trafilatura, "d", rules=BLOG_RULES
    )
    assert blog_text == arrived_from_trafilatura, (
        "blog text must survive byte-identical; trafilatura already decoded it"
    )
    assert all(s.is_identity for s in blog_segments), (
        "no substitution segment, so no offset drift to resolve"
    )


def test_blog_rules_still_substitute_symbols():
    """`So` is NOT per-platform yet, and that is deliberate.

    The rule was measured off one Reddit fixture and does not generalise, but
    the blog corpus refused both candidate replacements too — 0 occurrences of
    `°`, `©`, `®`, `™` in 519,997 characters, and the dominant class was
    box-drawing characters inside code fences, from 2 documents. Narrowing from
    that would repeat the original mistake in the other direction. It stays
    global and known-wrong until the evidence supports a rule.
    """
    from collect.assemble.flatten import BLOG_RULES, flatten_document

    text, segments = flatten_document("ship it \U0001f604", "d", rules=BLOG_RULES)
    assert "[smiling_face_with_open_mouth_and_smiling_eyes]" in text
    assert any(not s.is_identity for s in segments)


def test_flatten_defaults_to_reddit_rules_so_existing_callers_are_unchanged():
    """The default matches the tested path, which is where a wrong one shows up."""
    from collect.assemble.flatten import DEFAULT_RULES, REDDIT_RULES, flatten

    assert DEFAULT_RULES is REDDIT_RULES
    assert flatten([("d", "a &gt; b")]).text == "a > b"


def test_a_one_member_thread_records_that_nothing_was_selected():
    """`whole_document`, not a ranking that did not happen.

    The other half of the `@observed` assertion above, which is a Reddit-shaped
    invariant stated globally. A blog article is a thread of one: nothing is
    ranked, so the value must not name a ranking.
    """
    from collect.assemble.thread import (
        BLOG_COVERAGE_HIDDEN_CHILDREN_MIN,
        SELECTION_METHOD,
        WHOLE_DOCUMENT,
    )

    assert WHOLE_DOCUMENT == "whole_document"
    assert "@observed" not in WHOLE_DOCUMENT, "nothing was observed being ranked"
    assert WHOLE_DOCUMENT != "specificity_x_log_engagement", "the schema default"
    assert WHOLE_DOCUMENT != SELECTION_METHOD

    # Rule 6: include_comments=False means WE withheld, so this is not 0.
    assert BLOG_COVERAGE_HIDDEN_CHILDREN_MIN is None


def test_blog_coverage_ratio_is_null_either_way_so_honesty_is_free():
    """The generated CASE yields NULL for 0 observed and NULL hidden alike."""

    def generated(observed, hidden_min):
        total = (observed or 0) + (hidden_min or 0)
        return None if total <= 0 else observed / total

    assert generated(0, 0) is None, "the value we rejected"
    assert generated(0, None) is None, "the value we chose — same ratio"
    assert generated(None, None) is None, "a pre-#54 row, indistinguishable HERE"
    assert generated(200, 4633) is not None, "a measured Reddit thread still computes"
