"""The parse boundary: bytes in, absent stays absent, comments stay out.

Recorded fixtures only. No test here touches the network, and
`test_blog_no_network.py` proves that claim rather than restating it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.conftest import require_feed_libraries

# Above the imports it guards. See tests/conftest.py:require_feed_libraries.
require_feed_libraries()

from collect.adapters.blog.options import (  # noqa: E402
    DEFAULT_EXTRACTION,
    ExtractionOptions,
    UnrosteredOption,
)
from collect.adapters.blog.parse import (  # noqa: E402
    NotBytesError,
    current_extraction_version,
    extract_article_text,
    parse_feed,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "blog"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ── the bypass this module exists to prevent ─────────────────────────────


@pytest.mark.parametrize(
    "payload",
    [
        "https://notes.example.invalid/feed.xml",
        "fixtures/blog/feed_rss.xml",
        "<rss version='2.0'></rss>",
    ],
    ids=["url", "path", "xml-string"],
)
def test_parse_feed_refuses_str(payload):
    """A str could be a URL or a path, and feedparser would fetch either.

    This is the first of the three enforcements: the argument through which a
    URL could arrive does not accept one.
    """
    with pytest.raises(NotBytesError) as excinfo:
        parse_feed(payload)
    assert "build_client" in str(excinfo.value)


def test_extract_article_text_refuses_str():
    with pytest.raises(NotBytesError):
        extract_article_text("<html><body><p>hello</p></body></html>")


# ── RSS ──────────────────────────────────────────────────────────────────


def test_rss_entries_carry_identity_and_metadata():
    parsed = parse_feed(fixture("feed_rss.xml"), feed_url="https://notes.example.invalid/feed.xml")

    assert not parsed.malformed
    assert parsed.unidentifiable == 0
    assert parsed.feed_title == "Synthetic Engineering Notes"
    assert len(parsed.entries) == 2

    first = parsed.entries[0]
    assert first.entry_id == "urn:uuid:1f0c9a10-0000-4000-8000-000000000001"
    assert first.url == "https://notes.example.invalid/posts/summariser-swap"
    assert first.published_at == datetime(2026, 8, 4, 9, 15, tzinfo=UTC)
    assert "Alex Rivera" in (first.author or "")
    # A teaser and a full body are different facts, kept separately: a summary
    # read as the post would make a truncated article look complete.
    assert first.summary_html == "A teaser that is not the whole post."
    assert "held" in (first.content_html or "")


def test_missing_author_stays_missing():
    """Rule 6. A feed-level author standing in would attribute a guest post."""
    parsed = parse_feed(fixture("feed_rss.xml"))
    assert parsed.entries[1].author is None


def test_feed_level_author_never_fills_an_entry():
    parsed = parse_feed(fixture("feed_atom.xml"), feed_url="https://atom.example.invalid/feed.xml")
    assert parsed.entries[0].author is None


# ── Atom ─────────────────────────────────────────────────────────────────


def test_atom_published_is_not_updated():
    """`updated` is when it was edited. Reading it as `published` misdates.

    FR-4 resolves aliases against the date a claim was made, so a corrected post
    read as a fresh one can resolve to a model that did not exist when it was
    written.
    """
    parsed = parse_feed(fixture("feed_atom.xml"), feed_url="https://atom.example.invalid/feed.xml")
    entry = parsed.entries[0]
    assert entry.published_at == datetime(2026, 8, 6, 11, 0, tzinfo=UTC)
    assert entry.published_at != datetime(2026, 8, 7, 8, 30, tzinfo=UTC)


def test_relative_entry_link_resolves_against_the_feed_url():
    """Without the feed URL a relative link stays relative and cannot be fetched."""
    parsed = parse_feed(fixture("feed_atom.xml"), feed_url="https://atom.example.invalid/feed.xml")
    assert parsed.entries[0].url == "https://atom.example.invalid/posts/long-context"


def test_without_a_feed_url_a_relative_link_is_not_invented():
    parsed = parse_feed(fixture("feed_atom.xml"))
    assert parsed.entries[0].url == "/posts/long-context"


# ── malformed and unidentifiable ─────────────────────────────────────────


def test_malformed_feed_still_yields_entries_and_says_so():
    parsed = parse_feed(fixture("feed_malformed.xml"))
    assert parsed.malformed
    assert parsed.malformed_detail
    assert len(parsed.entries) == 1, "one bad character must not cost the whole feed"


def test_entries_with_no_identity_are_dropped_and_counted():
    """A dropped entry that nobody counted is a silent exclusion (rule 6)."""
    parsed = parse_feed(fixture("feed_no_ids.xml"))
    assert parsed.unidentifiable == 1
    assert len(parsed.entries) == 1
    # A link is identity enough: it is the publisher's own, and it does not
    # change when the post is edited.
    assert parsed.entries[0].entry_id == "https://anon.example.invalid/posts/link-only"


# ── extraction ───────────────────────────────────────────────────────────


def test_article_text_keeps_code_and_numbers():
    text = extract_article_text(
        fixture("article.html"), url="https://notes.example.invalid/posts/summariser-swap"
    )
    assert text
    assert "1.8s" in text, "numbers-with-units are the specificity signal"
    assert "max_tokens=6000" in text, "code must survive extraction"
    assert "archive" not in text, "navigation is boilerplate"


def test_comments_never_reach_the_article_body():
    """The attribution defect. trafilatura's default would include these.

    A comment extracted into the body is attributed to the post author, and it
    would then verify as a quote by exact substring match against text that
    author never wrote — rule 1 broken at the source rather than at the check.
    """
    text = extract_article_text(
        fixture("article_with_comments.html"),
        url="https://notes.example.invalid/posts/tool-calling-notes",
    )
    assert text
    assert "invalid" in text and "seventh call" in text
    assert "COMMENT BY SOMEBODY ELSE" not in text
    assert "COMMENT BY A THIRD PARTY" not in text


def test_default_options_are_the_ones_that_matter():
    assert DEFAULT_EXTRACTION.include_comments is False
    assert DEFAULT_EXTRACTION.deduplicate is False
    assert DEFAULT_EXTRACTION.include_formatting is True


def test_nothing_extractable_returns_none_not_empty_string():
    """None means nothing was extracted. An empty document is a claim of absence.

    A JS shell — the shape a paywall or an SPA arrives in — has no body text at
    all. Note that trafilatura is *not* shy on thin pages: given a bare
    `<nav>menu</nav>` it returns "menu", so "extraction succeeded" is not
    evidence that an article was found. Triage is what decides that; this only
    has to keep an absence from arriving as an empty string.
    """
    assert extract_article_text(b"<html><body></body></html>") is None


def test_extraction_version_moves_with_the_options():
    """An option change must be visible in the version, not inferred from a date.

    Every offset in every `offset_map` derived after a change depends on it.
    """
    baseline = current_extraction_version()
    changed = current_extraction_version(ExtractionOptions(include_comments=True))
    assert baseline != changed
    assert baseline.startswith("trafilatura-")


def test_the_pipeline_generation_reaches_the_version_and_the_fingerprint():
    """The gap this closes: our own steps moving offsets under one identifier.

    `pipeline` is not a trafilatura option, so nothing about trafilatura's
    version or options moves when it changes. It has to move BOTH halves of the
    identifier - the legible component and the opts hash - or a reader has two
    values that can disagree about the same field.
    """
    baseline = current_extraction_version()
    bumped = current_extraction_version(ExtractionOptions(pipeline=2))

    assert "+pipeline-1+" in baseline
    assert "+pipeline-2+" in bumped
    assert DEFAULT_EXTRACTION.fingerprint() != ExtractionOptions(pipeline=2).fingerprint()


def test_pipeline_is_fingerprinted_and_not_passed():
    """Both facts about one field, asserted together because they are a pair.

    Fingerprinted and passed is what a trafilatura option is; fingerprinted and
    not passed is what ours is. A field that is neither is the failure below.
    """
    assert "pipeline" not in DEFAULT_EXTRACTION.as_kwargs()
    assert "pipeline" in {
        pair.split("=")[0]
        for pair in _fingerprint_payload(DEFAULT_EXTRACTION)
    }


def _fingerprint_payload(options: ExtractionOptions) -> list[str]:
    """What `fingerprint()` hashes, rebuilt from the same rostered fields.

    Reaches into a private method on purpose: the alternative is asserting that
    two hashes differ, which cannot say WHICH field made the difference.
    """
    return [f"{key}={value}" for key, value in sorted(options._rostered().items())]


def test_an_option_in_neither_roster_refuses_rather_than_being_folded_in():
    """The difference between a fingerprint and a hash of whatever is in the dict.

    A new field arriving silently is the shape this whole change is about: the
    identifier keeps its meaning only while what it ranges over is declared.
    Silently including an unknown field would still change the hash, which is
    why this is easy to get wrong - the value moves, so it looks like it worked,
    and nothing states whether the field reaches trafilatura.
    """
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class WithAnUndeclaredStep(ExtractionOptions):
        strip_footnote_links: bool = True

    with pytest.raises(UnrosteredOption) as refusal:
        WithAnUndeclaredStep().fingerprint()

    assert "strip_footnote_links" in str(refusal.value)
    assert "_PIPELINE_KEYS" in str(refusal.value)


def test_a_roster_entry_with_no_field_behind_it_refuses(monkeypatch):
    """The quiet direction: the roster over-claims and the hash still moves.

    Removing a field changes the fingerprint, so nothing looks wrong from
    outside while the set of inputs it covers has shrunk. This is the check
    that makes the roster a statement about coverage rather than a comment.
    """
    from collect.adapters.blog import options as options_module

    monkeypatch.setattr(
        options_module,
        "_PIPELINE_KEYS",
        frozenset({"pipeline", "strip_footnote_links"}),
    )

    with pytest.raises(UnrosteredOption) as refusal:
        DEFAULT_EXTRACTION.fingerprint()

    assert "strip_footnote_links" in str(refusal.value)


def test_every_option_reaches_trafilatura(monkeypatch):
    """The call site lists options explicitly, so it can drift from the dataclass.

    Explicit keywords buy real type checking — unpacking a `dict[str, object]`
    into a typed library erases every parameter type — at the cost of two places
    to keep in step. This is the check that keeps them in step: a new field on
    `ExtractionOptions` that nobody wired up fails here rather than being
    silently ignored at extraction time.
    """
    from collect.adapters.blog import options as options_module
    from collect.adapters.blog import parse as parse_module

    captured: dict[str, object] = {}

    def fake_extract(_content, **kwargs):
        captured.update(kwargs)
        return "text"

    monkeypatch.setattr(parse_module.trafilatura, "extract", fake_extract)
    parse_module.extract_article_text(b"<html><body><p>x</p></body></html>", url="http://x.invalid")

    passed = {key: value for key, value in captured.items() if key != "url"}
    assert passed == DEFAULT_EXTRACTION.as_kwargs()
    # `as_kwargs` is now a filtered view rather than the whole dataclass, so
    # this asserts the roster too: a trafilatura option dropped from
    # `_TRAFILATURA_KEYS` would vanish from both sides and pass silently.
    assert set(passed) == set(options_module._TRAFILATURA_KEYS)
