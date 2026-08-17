"""FR-16: deduplicate before anything is counted.

The acceptance test uses a REAL syndicated set, not a constructed one — a
constructed duplicate is a duplicate the matcher was designed to catch. Found by
surveying 6,824 stored documents: one author posted the same content to four
subreddits within 25 minutes, and **three of the four bodies are byte-identical
while the fourth is not**, so exact matching finds two groups where the answer is
one. That is what makes the signature load-bearing rather than decorative.

The other load-bearing test is the sentinel one. `[removed]` is the body of 57
distinct comments in one corpus and `[deleted]` of 38. Merging on identical text
would collapse each set into a single document and destroy the tree.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from collect.assemble.dedupe import DedupeInput, cluster
from collect.assemble.signature import (
    DedupeContractError,
    is_sentinel,
    min_tokens_for_signature,
    signature_of,
    signature_text,
    similarity_threshold,
    token_count,
)

FIXTURE = (Path(__file__).resolve().parents[1]
           / "fixtures" / "reddit" / "syndication-4-subreddits.json")


@pytest.fixture(scope="module")
def syndicated():
    posts = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [
        DedupeInput(
            external_id=p["external_id"],
            text="\n".join(filter(None, (p["title"], p["selftext"]))),
            created_at=datetime.fromtimestamp(p["created_utc"], tz=UTC),
        )
        for p in posts
    ]


def long_text(seed: str, tokens: int = 400) -> str:
    return " ".join(f"{seed}{i}" for i in range(tokens))


# ── FR-16's acceptance, on real syndication ──────────────────────────────


def test_the_real_syndicated_set_becomes_one_cluster(syndicated):
    """FR-16: "the affected cell's voice count increments by exactly one".

    Four posts, four subreddits, one author, 25 minutes apart. One cluster.
    """
    result = cluster(syndicated)
    assert len(syndicated) == 4
    assert len(result.clusters) == 1
    assert result.clusters[0].size == 4
    assert result.clusters[0].reach == 3, "three amplifications, one original"


def test_exact_matching_alone_would_get_this_wrong(syndicated):
    """Why the signature is load-bearing and not decoration.

    Three of the four bodies are byte-identical after normalisation and the
    fourth differs by ~120 characters, so grouping on exact text yields TWO
    groups. A dedupe built only on content hashing would report two voices where
    there is one, and the publication gate reads voices.
    """
    groups = {signature_text(d.text).strip() for d in syndicated}
    assert len(groups) == 2, "the corpus really does contain this shape"
    assert len(cluster(syndicated).clusters) == 1, "the signature closes the gap"


def test_the_canonical_is_the_earliest_not_the_most_upvoted(syndicated):
    """The earliest original is canonical; the rest are amplifications.

    Here the earliest also happens to carry the highest score, so the test pins
    the RULE rather than the coincidence — a later, more popular copy must not
    take over as the original.
    """
    result = cluster(syndicated)
    assert result.clusters[0].canonical_id == "t3_1tgecrq"
    earliest = min(syndicated, key=lambda d: d.created_at)
    assert result.clusters[0].canonical_id == earliest.external_id


def test_reach_counts_copies_and_nothing_computes_a_weight(syndicated):
    """Amplifications contribute to REACH, never to WEIGHT.

    A syndicated post reaching four subreddits is more READ and no better
    evidenced. This asserts the cluster exposes nothing a weighting pass would
    pick up — the next person wiring `f_*` will grep for exactly these names.
    """
    c = cluster(syndicated).clusters[0]
    assert c.reach == 3
    assert set(c.as_row()) == {"canonical_document_id", "size", "reach"}
    for forbidden in ("weight", "factor", "score", "confidence", "f_reach"):
        assert not hasattr(c, forbidden), f"{forbidden} would invite reach into weight"


def test_how_each_member_joined_is_recorded(syndicated):
    """A cluster from a platform declaration and one from a 0.93 Jaccard are
    different kinds of claim, and a size alone cannot tell them apart later."""
    c = cluster(syndicated).clusters[0]
    assert c.joined_by[c.canonical_id] == "canonical"
    others = {v for k, v in c.joined_by.items() if k != c.canonical_id}
    assert others, "every non-canonical member says how it got there"
    assert all(v.startswith(("exact", "minhash", "crosspost")) for v in others)


# ── the sentinel trap ────────────────────────────────────────────────────


@pytest.mark.parametrize("body", ["[deleted]", "[removed]", "  [removed]  "])
def test_sentinel_bodies_are_recognised(body):
    assert is_sentinel(body)


def test_identical_sentinel_bodies_are_never_merged():
    """57 `[removed]` and 38 `[deleted]` in one corpus, all distinct comments.

    Identical text is not identity. Merging them would collapse a thread and
    every voice count drawn from it.
    """
    docs = [DedupeInput(f"t1_{i}", "[removed]") for i in range(57)]
    docs += [DedupeInput(f"t1_d{i}", "[deleted]") for i in range(38)]
    result = cluster(docs)
    assert len(result.clusters) == 95, "one cluster each, nothing merged"
    assert all(c.is_singleton for c in result.clusters)


def test_a_sentinel_is_not_merged_even_by_a_crosspost_declaration():
    """The certainty mechanisms do not get to override this either."""
    docs = [
        DedupeInput("t3_a", "[removed]"),
        DedupeInput("t3_b", "[removed]", declared_copy_of="t3_a"),
    ]
    assert len(cluster(docs).clusters) == 2


def test_a_sentinel_gets_no_signature_and_says_why():
    sig = signature_of("t1_x", "[removed]", min_tokens=200)
    assert not sig.comparable
    assert sig.reason == "sentinel-body"


# ── blockquotes out, code in — from the sieve's one definition ────────────


def test_blockquotes_are_excluded_from_the_signature():
    """So commentary ABOUT a post is not merged into the post."""
    quoted = "> the original post said this\nI disagree completely"
    assert "the original post" not in signature_text(quoted)
    assert "disagree" in signature_text(quoted)


def test_two_replies_quoting_the_same_post_do_not_merge():
    """The case the exclusion exists for, end to end."""
    shared = "\n".join(f"> quoted line {i}" for i in range(200))
    a = DedupeInput("t1_a", shared + "\n" + long_text("alpha"))
    b = DedupeInput("t1_b", shared + "\n" + long_text("beta"))
    assert len(cluster([a, b]).clusters) == 2


def test_code_is_NOT_excluded_from_the_signature():
    """A pasted traceback distinguishes documents rather than conflating them.

    `author_prose` removes code because it is answering "did the author assert
    this". A signature asks a different question and wants a different subset,
    which is why `strip_container` takes one name instead of applying the set.
    """
    fenced = "prose here\n```\nTraceback most recent call last\n```"
    # `normalize` casefolds, so the comparison is lowercase. What is asserted is
    # that the span SURVIVES, not how it is cased.
    assert "traceback most recent call last" in signature_text(fenced)


def test_the_signature_uses_the_sieve_pattern_and_not_a_local_one():
    """Third consumer of one definition, pinned so a fourth never appears.

    `author_prose` for the sieve, `triage.specificity.has_code` for presence,
    this for one member. A local blockquote regex here would drift from the
    sieve's the first time someone fixed a bug in either.
    """
    import ast

    import collect.assemble.signature as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        f"{node.module}.{a.name}"
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
        for a in node.names
    }
    assert "collect.adapters.queries.sieve.strip_container" in imported

    # and no second definition of what a blockquote looks like
    assert "re.compile" not in source or ">" not in source.split("re.compile")[1][:40]


# ── the floor ────────────────────────────────────────────────────────────


def test_a_short_document_gets_no_signature_and_says_why():
    sig = signature_of("t1_x", "three tokens only", min_tokens=200)
    assert not sig.comparable
    assert sig.reason == "below-floor"
    assert sig.tokens == 3


def test_below_the_floor_similarity_is_not_attempted():
    """Neither method separates there, so guessing would be over-merging.

    Two short documents sharing most of their words stay separate — that is the
    measured behaviour, not a bug: the 0-50 token band had true pairs down to
    0.04 Jaccard and strangers up to 0.13, which do not separate.
    """
    a = DedupeInput("t1_a", "the model dropped the cancellation clause entirely")
    b = DedupeInput("t1_b", "the model dropped the cancellation clause almost")
    assert len(cluster([a, b]).clusters) == 2


def test_a_crosspost_declaration_works_below_the_floor():
    """Certainty is not subject to the floor. The floor is about inference."""
    a = DedupeInput("t3_a", "short link post title")
    b = DedupeInput("t3_b", "short link post title", declared_copy_of="t3_a")
    result = cluster([a, b])
    assert len(result.clusters) == 1
    assert result.clusters[0].joined_by["t3_b"] == "crosspost"


def test_exact_match_works_below_the_floor():
    a = DedupeInput("t3_a", "identical short body", created_at=datetime(2026, 1, 1, tzinfo=UTC))
    b = DedupeInput("t3_b", "identical short body", created_at=datetime(2026, 1, 2, tzinfo=UTC))
    result = cluster([a, b])
    assert len(result.clusters) == 1
    assert result.clusters[0].canonical_id == "t3_a"


# ── clustering behaviour ─────────────────────────────────────────────────


def test_merging_is_transitive():
    """A~B and B~C means one cluster, whatever order they arrive in."""
    base = long_text("shared")
    docs = [
        DedupeInput("a", base),
        DedupeInput("b", base + " tail one"),
        DedupeInput("c", base + " tail two"),
    ]
    assert len(cluster(docs).clusters) == 1
    assert len(cluster(list(reversed(docs))).clusters) == 1


def test_every_input_appears_in_exactly_one_cluster():
    """This reports a grouping. It does not filter, and it does not delete."""
    docs = [DedupeInput("a", long_text("x")), DedupeInput("b", "short"),
            DedupeInput("c", "[removed]"), DedupeInput("d", "")]
    result = cluster(docs)
    seen = [m for c in result.clusters for m in c.member_ids]
    assert sorted(seen) == ["a", "b", "c", "d"]
    assert len(seen) == len(set(seen))


def test_a_document_with_no_timestamp_does_not_win_canonical():
    """It cannot be SHOWN to be earliest, so it does not become the original."""
    docs = [
        DedupeInput("no_date", "identical body text here"),
        DedupeInput("dated", "identical body text here",
                    created_at=datetime(2026, 5, 1, tzinfo=UTC)),
    ]
    assert cluster(docs).clusters[0].canonical_id == "dated"


def test_an_empty_document_never_merges_with_another_empty_one():
    """An empty signature matches every other empty signature.

    Without the guard every blank document would land in one cluster, which is
    the shape of a merge nobody asked for.
    """
    docs = [DedupeInput("a", ""), DedupeInput("b", "   "), DedupeInput("c", "\n")]
    result = cluster(docs)
    assert len(result.clusters) == 3
    assert {s.reason for s in result.signatures.values()} == {"empty"}


def test_the_result_describes_why_documents_had_no_signature():
    docs = [DedupeInput("a", long_text("y")), DedupeInput("b", "tiny"),
            DedupeInput("c", "[deleted]")]
    described = cluster(docs).describe()
    assert "below-floor" in described and "sentinel-body" in described


# ── the contract ─────────────────────────────────────────────────────────


def test_thresholds_come_from_the_contract():
    assert min_tokens_for_signature() == 200
    assert 0 < similarity_threshold() <= 1


def test_a_missing_dedupe_block_raises_rather_than_defaulting(monkeypatch):
    """Rule 5. A built-in threshold renders identically to the real one."""
    import collect.assemble.signature as mod

    mod._contract.cache_clear()
    monkeypatch.setattr(mod, "_contract", lambda: {})
    with pytest.raises(DedupeContractError, match="min_tokens_for_signature"):
        min_tokens_for_signature()
    # monkeypatch restores the real `_contract`; calling cache_clear on the stub
    # would fail, and clearing afterwards is monkeypatch's job not ours.


def test_the_token_floor_is_measured_in_signature_tokens():
    """Blockquotes are out, so a heavily quoting document has fewer tokens
    than it looks like it has — and the floor must agree with the signature
    about what it is counting."""
    quoted = "\n".join(f"> quoted {i}" for i in range(300)) + "\nfive real words here now"
    assert token_count(quoted) == 5


# ── simhash is absent on purpose ─────────────────────────────────────────


def test_no_simhash_implementation_exists():
    """A measured decision, not a gap.

    MinHash separated better at every length; simhash's margin at 400-800 tokens
    was one bit of 64, and 0-12 bits in its conventional word-3-gram form. So
    `document.simhash` stays NULL and this module has no simhash — recorded here
    so nobody adds one back believing it was merely unfinished.
    """
    import collect.assemble.dedupe as dedupe_mod
    import collect.assemble.signature as sig_mod

    for mod in (sig_mod, dedupe_mod):
        source = Path(mod.__file__).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines()
            if not line.strip().startswith("#")
        )
        assert "def simhash" not in code
