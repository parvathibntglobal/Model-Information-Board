"""The Sources page names the blog feeds, not just the word "blogs".

`contract/sources.yaml` keeps PLATFORMS under `sources` and FEEDS under
`feeds`, two separate top-level keys. `/admin/sources` read only the first, so
the page rendered eight rows — one of them *"blogs · public feeds, then the
article"* — and could not name a single feed.

Eighteen are seated. `swyx.io` alone holds 432 documents, about a third of the
blog corpus, and two of the eighteen have harvested nothing at all. None of
that was answerable from the admin page; you had to open the contract file.

⚠ AND THE COUNT IS WHY IT IS WORTH RENDERING. A list of eighteen names tells a
  reader nothing they could not guess. `0` against a seated feed is a finding.
"""

from __future__ import annotations

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract" / "sources.yaml"
APP = ROOT / "judge" / "app.py"
PANEL = ROOT / "web" / "src" / "components" / "SourcesPanel.jsx"


def _contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8")) or {}


class TestTheContractKeepsThemApart:
    def test_feeds_are_a_separate_key_from_sources(self):
        """The premise of the defect. If these ever merge, the endpoint's two
        reads become one and this whole file is describing history."""
        doc = _contract()
        assert "sources" in doc and "feeds" in doc
        platform_ids = {str(s.get("id")) for s in doc["sources"]}
        feed_ids = {str(f.get("id")) for f in doc["feeds"]}
        assert not (platform_ids & feed_ids)
        assert all(i.startswith("blog:") for i in feed_ids)

    def test_the_endpoint_reads_both(self):
        src = APP.read_text(encoding="utf-8")
        assert 'platforms = list(doc.get("sources") or [])' in src
        assert 'feeds = list(doc.get("feeds") or [])' in src, (
            "the endpoint is back to reading only the platforms, so the page "
            "cannot name a feed"
        )


class TestACountWeCouldNotTakeIsNotAZero:
    """⚠ RULE 6, AND THE FIRST VERSION GOT THIS WRONG FOUR LINES UNDER ITS OWN
    COMMENT ABOUT IT.

    `harvested.get(host)` returns `None` for a feed with no documents — so
    `mattrickard.com`, seated and genuinely empty, reported the same value as
    a feed whose count failed to read. Those are opposite claims: one is a
    measurement, the other is an absence of one.
    """

    def test_a_readable_count_of_zero_is_zero(self):
        src = APP.read_text(encoding="utf-8")
        assert "harvested.get(host, 0) if counts_unreadable is None else None" in src, (
            "a seated feed that has harvested nothing must report 0, and only "
            "a failed read may report None"
        )

    def test_the_failure_is_carried_rather_than_swallowed(self):
        src = APP.read_text(encoding="utf-8")
        assert '"blog_counts_unreadable": counts_unreadable,' in src
        panel = PANEL.read_text(encoding="utf-8")
        assert "blog_counts_unreadable" in panel, (
            "the page must say the counts are unknown rather than print zeros"
        )

    def test_the_endpoint_still_answers_without_a_database(self):
        """It answered from the contract alone before the counts existed, and
        that property is worth more than the counts: a page that cannot list
        its sources because the database is down is a worse page."""
        src = APP.read_text(encoding="utf-8")
        block = src[src.index("def admin_sources"):]
        block = block[:block.index(chr(10) + "@app.")]
        assert "except Exception as exc:  # noqa: BLE001" in block
        assert "counts_unreadable = _safe_detail(exc)" in block, (
            "a database failure must be captured, not raised - and through "
            "`_safe_detail`, or the DSN host reaches the page"
        )


class TestTheRowSaysWhatItCannotClaim:
    def test_a_shared_host_count_is_marked(self):
        """`blog:medium.com/airbnb-engineering` is one feed on a host the
        harvester keys by, so its number is the host's. Rule 7: the figure
        travels with what it was drawn from."""
        src = APP.read_text(encoding="utf-8")
        assert '"count_is_for_the_host": shared_host,' in src
        assert "count_is_for_the_host" in PANEL.read_text(encoding="utf-8")

    def test_the_entry_byline_feeds_are_marked(self):
        """#373: an `entry` feed writes author rows that no document links.
        Marking them here is how a reader sees which feeds are affected."""
        panel = PANEL.read_text(encoding="utf-8")
        assert "byline_source === 'entry'" in panel

    def test_terms_not_read_is_not_terms_refused(self):
        """Rule 4, the same as the platform rows: `false` means nobody read the
        document, not that it was read and found wanting."""
        panel = PANEL.read_text(encoding="utf-8")
        assert "robots only" in panel and "not recorded" in panel
        assert re.search(r"terms_document_read === true", panel)
