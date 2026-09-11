"""Dedupe gets its writer, and URLs get one spelling.

WHAT WAS ACTUALLY MISSING. `collect/assemble/dedupe.py` (three mechanisms, the
sentinel trap) and `collect/assemble/signature.py` (MinHash, blockquotes
excluded, a measured 200-token floor) were both complete and both correct, and
NOTHING CALLED THEM. `collect/ops/chain.py` declared
`Stage("assemble-dedupe", run=None)`; `contract/column_states.yaml` said
`known_gap: E1's lane - dedupe is unwired`; and on staging
`dedup_cluster_id`, `is_canonical_in_cluster`, `minhash` and `simhash` were
populated on 0 of 7,479 documents.

WHY AN EMPTY COLUMN WAS THE SMALL PART. `judge/vet/reject.py:check` already
took `dedup_cluster_id` and `is_canonical_in_cluster` and defaulted to
"not clustered, is canonical" — so every syndicated copy of one post counted as
an independent voice, which is the condition the publication gate exists to
test, inverted. A starved consumer, not an absent one.

TWO THINGS THIS DOES NOT DO, BOTH BECAUSE SOMEBODY MEASURED:

  simhash            `signature.py` found MinHash separates better at EVERY
                     length, including the long bands simhash was specified
                     for, where its margin is one bit in 64. "Absent rather
                     than unimplemented."
  author clustering  `authors.py` found zero cross-platform identities in
                     4,153 documents and declined to write a rule from
                     imagination. Re-measured here on 8,143: TWO now exist.
                     That is evidence for a decision, not a licence to guess,
                     so this still does not cluster them.
"""

from __future__ import annotations

import pathlib

import pytest

from collect.assemble.urls import TRACKING_KEYS, canonical_url, expand_shortener, same_page

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestOneSpellingOfAPage:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("https://www.example.com/post?utm_source=reddit", "https://example.com/post"),
            ("https://example.com/post/", "https://example.com/post"),
            ("http://example.com/post#section", "http://example.com/post"),
            ("https://example.com/x?id=7&fbclid=abc", "https://example.com/x?id=7"),
            ("https://example.com:443/a", "https://example.com/a"),
            ("http://example.com:80/a", "http://example.com/a"),
            ("https://EXAMPLE.com/A", "https://example.com/A"),
        ],
    )
    def test_the_cosmetic_differences_collapse(self, raw, expected):
        assert canonical_url(raw) == expected

    def test_a_real_id_in_the_query_survives(self):
        # The single most dangerous over-reach available here: `?id=49610874`
        # IS the document on Hacker News, and a blanket "drop the query" would
        # turn every HN link into the same front page.
        url = "https://news.ycombinator.com/item?id=49610874"
        assert canonical_url(url) == url

    def test_hashbang_routing_is_kept(self):
        # `#!` addressed a page on older hosts; a plain `#section` never does.
        assert canonical_url("https://example.com/app#!/route") == "https://example.com/app#!/route"

    def test_the_path_is_not_otherwise_touched(self):
        # `/a/b` and `/a/B` are different pages on a case-sensitive host, and
        # lowercasing the path would merge them.
        assert canonical_url("https://example.com/A/b") == "https://example.com/A/b"

    def test_http_is_not_promoted_to_https(self):
        # It looks harmless and is a guess about what the host serves. A host
        # not answering on 443 would get a dead link out of a tidying pass.
        assert canonical_url("http://example.com/a").startswith("http://")

    @pytest.mark.parametrize("bad", [None, "", "   ", "not a url", "/relative/path"])
    def test_what_it_cannot_read_it_returns_unchanged(self, bad):
        # A link that still works is worth more than a tidy one that does not.
        assert canonical_url(bad) == bad

    def test_it_never_raises(self):
        for weird in ["http://[", "https://" + "a" * 5000, "::::", "https://exa mple.com/x"]:
            canonical_url(weird)

    def test_the_tracking_list_is_closed_rather_than_a_prefix_rule(self):
        # `utm_*` would match with a wildcard, but fbclid/gclid/igshid share no
        # prefix, and a wildcard broad enough for a future one is broad enough
        # to eat an id.
        assert "utm_source" in TRACKING_KEYS and "fbclid" in TRACKING_KEYS
        src = (ROOT / "collect" / "assemble" / "urls.py").read_text(encoding="utf-8")
        assert "startswith(\"utm_\")" not in src

    def test_same_page_names_the_question(self):
        assert same_page("https://www.example.com/p?utm_source=x", "https://example.com/p")
        assert not same_page("https://news.ycombinator.com/item?id=1",
                             "https://news.ycombinator.com/item?id=2")
        assert not same_page(None, "https://example.com")

    def test_the_shortener_seam_is_honest_about_doing_nothing(self):
        # Named so the gap is visible. Resolving a shortener needs a request per
        # URL and belongs in the harvest, not in a pure function called in a
        # loop over thousands of rows.
        assert expand_shortener("https://bit.ly/x") == "https://bit.ly/x"
        doc = expand_shortener.__doc__ or ""
        assert "NOT IMPLEMENTED" in doc


class TestTheWriterSignsProseAndNotThePayload:
    @staticmethod
    def _src() -> str:
        return (ROOT / "collect" / "assemble" / "dedupe_write.py").read_text(encoding="utf-8")

    def test_it_extracts_prose_before_signing(self):
        # THE 2026-09-10 LESSON. A raw JSON envelope shingled character-wise
        # clusters on `{"author":"…","children":`, which every document from a
        # platform shares - so everything would merge with everything.
        src = self._src()
        assert "prose.for_source(source)" in src

    def test_a_source_with_no_extractor_is_refused_not_signed_raw(self):
        src = self._src()
        assert "if extract is None:" in src
        assert "report.refused = len(rows)" in src

    def test_an_unreadable_payload_is_counted_rather_than_skipped_silently(self):
        # It stays a singleton, which is the under-merge direction, but the
        # count is what stops "0 clusters" reading as "nothing was duplicated"
        # when it means "nothing was checked".
        src = self._src()
        assert "report.unreadable += 1" in src
        assert "unreadable" in src.split("def describe")[1][:400]

    def test_nothing_is_deleted(self):
        """A duplicate keeps its row, its payload and its author; only its
        STATUS as an independent voice changes.

        Checked as a SQL statement, not as the word. The docstring says "NEVER
        DELETE" and the sentinel discussion quotes `[deleted]`, so a substring
        search fails on the file's own prose — which has now caught me five
        times in this codebase and is written down here for the sixth.
        """
        assert "DELETE FROM" not in self._src().upper()

    def test_the_cluster_id_is_derived_from_the_canonical(self):
        # So a re-run reuses the row rather than minting a second grouping for
        # the same content.
        from collect.assemble.dedupe_write import cluster_id_for

        assert cluster_id_for("doc_a") == cluster_id_for("doc_a")
        assert cluster_id_for("doc_a") != cluster_id_for("doc_b")

    def test_minhash_and_simhash_are_left_null_on_purpose(self):
        src = self._src()
        assert "simhash" in src and "minhash" in src
        assert "absent rather than" in src or "measured and dropped" in src


class TestTheStageIsWiredIntoTheRun:
    @staticmethod
    def _src() -> str:
        return (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")

    def test_there_is_a_dedupe_stage(self):
        assert "def dedupe_stage(" in self._src()

    def test_it_runs_after_assemble_and_before_score(self):
        # Clustering signs PROSE, and prose comes from the assemblers. Running
        # it first would sign whatever the adapter happened to store.
        src = self._src()
        assert src.index("assemble_stage(db.live(prog)") < src.index("dedupe_stage(db.live(prog)")
        assert src.index("dedupe_stage(db.live(prog)") < src.index("score_stage(db.live(prog)")

    def test_a_clustering_failure_never_ends_the_run(self):
        # The documents are stored and the threads are built; a missing
        # grouping costs precision on voice counts, not the corpus.
        src = self._src()
        body = src[src.index("def dedupe_stage("):src.index("def score_stage(")]
        assert "_safe_rollback" in body
        assert '"error"' in body

    def test_the_stage_reports_what_it_could_not_compare(self):
        src = self._src()
        body = src[src.index("def dedupe_stage("):src.index("def score_stage(")]
        for field in ("clusters", "amplifications", "signed", "unreadable", "refused"):
            assert field in body, field


def test_the_consumer_that_was_starved_still_takes_these_fields():
    """`judge/vet/reject.py` has always accepted them. That is why writing them
    matters: the default was "canonical", so every copy was an independent
    voice."""
    src = (ROOT / "judge" / "vet" / "reject.py").read_text(encoding="utf-8")
    assert "dedup_cluster_id: str | None = None" in src
    assert "is_canonical_in_cluster: bool = True" in src
