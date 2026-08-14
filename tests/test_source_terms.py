"""NFR-5: terms reviewed and recorded per source, enforced rather than hoped.

The first version of this gate grepped `tos_notes` for a `REVIEW REQUIRED`
placeholder. That caught "nobody did the reading" and nothing else, and let
through the worse failure: a ruling made once, dated, and asserted forever
against a site that changed its terms three months later.

So the gate is now a known unexpired ruling, evidence that has not gone stale,
and preconditions re-verified on the run. These are the tests that make each of
those a gate rather than a hope.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import yaml

from collect.config import CONTRACT_DIR
from collect.registry.assertions import TermsNotReviewedError, assert_terms_reviewed
from collect.registry.sources import (
    SourcesContractError,
    load_sources,
    parse_sources,
    ruling_for,
)

SOURCES_YAML = CONTRACT_DIR / "sources.yaml"

#: The day the class rulings and every feed measurement were made.
REVIEWED_ON = date(2026, 8, 14)


def _contract():
    return yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))


def _feed(feed_id: str):
    return next(f for f in _contract()["feeds"] if f["id"] == feed_id)


def _observations(source, *, allowed=True):
    """What a healthy run would observe for one source."""
    evidence = source.get("terms_evidence") or {}
    if source.get("endpoint") is None:
        return {"endpoint_is_null": True}
    return {
        "endpoint_is_null": False,
        "robots_status": evidence.get("robots_status"),
        "feed_path_allowed": allowed,
        "access_path": evidence.get("access_path"),
    }


# ── the file itself ───────────────────────────────────────────────────────


def test_the_contract_file_exists():
    """Sign-off item 13. Without it, watermark.source_id has nothing to point at."""
    assert SOURCES_YAML.exists()


def test_all_three_platforms_are_declared():
    ids = {s["id"] for s in _contract()["sources"]}
    assert ids == {"github", "blogs", "reddit"}


def test_base_trust_matches_the_documented_weights():
    """github 0.95 / blog 0.90 / reddit 0.85 — weights, so rule 5 puts them here."""
    trust = {s["id"]: s["base_trust"] for s in _contract()["sources"]}
    assert trust == {"github": 0.95, "blogs": 0.90, "reddit": 0.85}


def test_every_source_and_feed_has_tos_notes():
    """`source.tos_notes` is NOT NULL precisely so this cannot be skipped."""
    contract = _contract()
    assert all(s.get("tos_notes") for s in contract["sources"])
    assert all(f.get("tos_notes") for f in contract["feeds"])


# ── the seeded feeds ──────────────────────────────────────────────────────


def test_nine_feeds_are_seeded():
    """Nine, not ten. Dropbox is dropped on data quality, not on terms."""
    feeds = _contract()["feeds"]
    assert len(feeds) == 9
    assert not any("dropbox" in f["id"] for f in feeds)


def test_dropbox_is_recorded_as_checked_and_rejected():
    """A rejection nobody wrote down gets re-litigated every quarter."""
    text = SOURCES_YAML.read_text(encoding="utf-8")
    assert "dropbox.tech" in text
    assert "cumulative" in text


def test_every_seeded_row_carries_provenance():
    """Item 20's shape. Without it a discovered feed inherits a vetted ruling."""
    contract = _contract()
    for row in (*contract["sources"], *contract["feeds"]):
        assert row.get("provenance") == "seed", row["id"]


def test_every_feed_dates_its_measurements():
    """A class ruling on a stale robots check is a placeholder with a date."""
    for feed in _contract()["feeds"]:
        assert feed["terms_evidence"]["checked_on"] == REVIEWED_ON, feed["id"]
        assert feed["measured"]["checked_on"] == REVIEWED_ON, feed["id"]


def test_every_feed_records_the_mechanical_evidence():
    """robots status and code, both paths, paywall, feed type, date checked."""
    required = {
        "checked_on",
        "robots_status",
        "robots_http",
        "feed_path_allowed",
        "article_path_allowed",
        "paywall_observed",
        "login_required",
        "feed_type",
    }
    for feed in _contract()["feeds"]:
        assert required <= set(feed["terms_evidence"]), feed["id"]


def test_every_feed_names_a_declared_ruling():
    contract = load_sources()
    for feed in contract.feeds:
        assert feed["terms_ruling"] in contract.rulings, feed["id"]


def test_the_two_classes_split_self_hosted_from_platform_hosted():
    contract = load_sources()
    by_class = {}
    for feed in contract.feeds:
        ruling = contract.rulings[feed["terms_ruling"]]
        by_class.setdefault(ruling.klass, []).append(feed["id"])

    assert sorted(by_class["B"]) == [
        "blog:medium.com/airbnb-engineering",
        "blog:netflixtechblog.com",
    ]
    assert len(by_class["A"]) == 7


def test_the_medium_ruling_is_feed_only_and_says_why():
    """Two independent grounds, and neither is "we got a 403 so we stopped"."""
    ruling = load_sources().rulings["blog-class-b-medium"]
    assert ruling.fetch_articles is False
    assert ruling.platform_host == "medium.com"
    assert "/*/*source=" in ruling.summary
    assert "403" in ruling.summary
    # The gate cannot see the robots rule, and saying so is the point.
    assert "urllib.robotparser" in ruling.summary


def test_the_medium_ruling_demonstrates_the_split_rather_than_asserting_it():
    """Measured on 2026-08-14: 37 identical rule lines, one templated Sitemap.

    The `License` line is *not* substituted — it reads medium.com from both
    hosts. A custom domain is a skin over one host's rules, which is the whole
    argument for reading the platform's document rather than the publisher's.
    """
    summary = load_sources().rulings["blog-class-b-medium"].summary
    assert "netflixtechblog.com/robots.txt" in summary
    assert "37 rule lines" in summary
    assert "https://medium.com/license.xml" in summary
    assert "Sitemap" in summary


def test_the_medium_feeds_record_the_refusal_rather_than_a_clean_bill():
    for feed_id in ("blog:netflixtechblog.com", "blog:medium.com/airbnb-engineering"):
        evidence = _feed(feed_id)["terms_evidence"]
        assert evidence["article_path_allowed"] is False
        assert evidence["article_http"] == 403
        assert evidence["article_fetch_refused"] is True
        # Rule 6: a 403 page cannot show a paywall, so we do not claim it has none.
        assert evidence["paywall_observed"] == "unknown"


def test_the_class_a_ruling_carries_the_404_caveat_in_its_text():
    """In the ruling, not a footnote — it is the reasoning, not a remark."""
    summary = load_sources().rulings["blog-class-a-self-hosted"].summary
    assert "404" in summary
    assert "no crawl rules" in summary
    assert "engineering.grab.com" in summary
    assert "dropbox.tech" in summary


def test_grab_is_the_live_404_case():
    evidence = _feed("blog:engineering.grab.com")["terms_evidence"]
    assert evidence["robots_status"] == "no-rules"
    assert evidence["robots_http"] == 404


def test_team_bylined_feeds_collapse_to_one_voice_not_zero():
    """Engineer 2's ruling. Reading a team blog as no voice loses the evidence."""
    for feed_id in (
        "blog:netflixtechblog.com",
        "blog:engineering.atspotify.com",
        "blog:engineering.grab.com",
    ):
        measured = _feed(feed_id)["measured"]
        assert measured["byline_source"] == "team"
        assert measured["resolves_to_voices"] == 1


def test_simon_willison_passes_on_the_declared_fact():
    measured = _feed("blog:simonwillison.net")["measured"]
    assert measured["byline_source"] == "feed_declared"
    assert measured["declared_author"] == "Simon Willison"
    assert measured["entry_bylines_present"] == 0  # nothing dissents
    assert measured["resolves_to_voices"] == 1


def test_a_feed_with_no_byline_and_no_org_stays_unresolved():
    """rule 6. Inferring the author from the domain manufactures the byline."""
    measured = _feed("blog:vickiboykis.com")["measured"]
    assert measured["byline_source"] == "none"
    assert measured["declared_author"] is None
    assert measured["resolves_to_voices"] is None


def test_the_entry_byline_beats_the_declaration():
    """hamel.dev declares nothing and its entries name two people, not one."""
    measured = _feed("blog:hamel.dev")["measured"]
    assert measured["byline_source"] == "entry"
    assert measured["distinct_entry_bylines"] == 2
    assert measured["resolves_to_voices"] == 2


def test_every_feed_becomes_a_source_row():
    """Seeded in contract/, ordinary rows at runtime — seed_models' pattern."""
    contract = load_sources()
    rows = {row["id"]: row for row in contract.source_rows()}
    assert len(rows) == 12  # three platforms + nine feeds
    assert rows["blog:simonwillison.net"]["provenance"] == "seed"
    assert rows["blog:simonwillison.net"]["terms_checked_on"] == REVIEWED_ON
    assert all(row["base_trust"] for row in rows.values())


# ── the gate ──────────────────────────────────────────────────────────────


def test_reddit_still_blocks_and_now_for_a_stronger_reason():
    """Not a marker in prose. There is no ruling for it to name."""
    contract = load_sources()
    reddit = next(s for s in contract.platforms if s["id"] == "reddit")
    assert "terms_ruling" not in reddit

    with pytest.raises(TermsNotReviewedError) as excinfo:
        assert_terms_reviewed(
            [reddit], rulings=contract.rulings, observations={}, today=REVIEWED_ON
        )
    assert "names no terms ruling" in str(excinfo.value)


def test_every_seeded_feed_passes_when_the_run_observes_what_was_recorded():
    """The state this commit is claiming: nine feeds cleared to harvest."""
    contract = load_sources()
    observations = {f["id"]: _observations(f) for f in contract.feeds}
    assert_terms_reviewed(
        contract.feeds,
        rulings=contract.rulings,
        observations=observations,
        today=REVIEWED_ON,
    )


def test_github_and_blogs_pass_and_reddit_does_not():
    contract = load_sources()
    observations = {s["id"]: _observations(s) for s in contract.platforms}
    with pytest.raises(TermsNotReviewedError) as excinfo:
        assert_terms_reviewed(
            contract.platforms,
            rulings=contract.rulings,
            observations=observations,
            today=REVIEWED_ON,
        )
    message = str(excinfo.value)
    assert "reddit" in message
    assert "github" not in message and "blogs" not in message


def test_a_ruling_that_expired_stops_the_run():
    """The October failure, which the marker check could never have caught."""
    contract = load_sources()
    feed = _feed("blog:simonwillison.net")
    ruling = contract.rulings[feed["terms_ruling"]]
    a_day_late = ruling.expires_on() + timedelta(days=1)

    with pytest.raises(TermsNotReviewedError, match="expired") as excinfo:
        assert_terms_reviewed(
            [feed],
            rulings=contract.rulings,
            observations={feed["id"]: _observations(feed)},
            today=a_day_late,
        )
    assert "Re-read the terms rather than extending the date" in str(excinfo.value)


def test_evidence_that_went_stale_stops_the_run_even_under_a_fresh_ruling():
    """The ruling reads a document; the evidence measures a host. Both age."""
    contract = load_sources()
    feed = dict(_feed("blog:engineering.grab.com"))
    feed["terms_evidence"] = {**feed["terms_evidence"], "checked_on": date(2025, 1, 1)}

    with pytest.raises(TermsNotReviewedError, match="stale") as excinfo:
        assert_terms_reviewed(
            [feed],
            rulings=contract.rulings,
            observations={feed["id"]: _observations(feed)},
            today=REVIEWED_ON,
        )
    assert "Re-check robots.txt" in str(excinfo.value)


def test_undated_evidence_is_refused():
    contract = load_sources()
    feed = dict(_feed("blog:hamel.dev"))
    feed["terms_evidence"] = {
        k: v for k, v in feed["terms_evidence"].items() if k != "checked_on"
    }
    with pytest.raises(TermsNotReviewedError, match="no date"):
        assert_terms_reviewed(
            [feed],
            rulings=contract.rulings,
            observations={feed["id"]: _observations(feed)},
            today=REVIEWED_ON,
        )


def test_a_precondition_nobody_observed_is_not_a_precondition_that_passed():
    """Rule 6, at the gate. An empty observation set must not read as consent."""
    contract = load_sources()
    feed = _feed("blog:slack.engineering")
    with pytest.raises(TermsNotReviewedError, match="observed nothing"):
        assert_terms_reviewed(
            [feed], rulings=contract.rulings, observations={}, today=REVIEWED_ON
        )


def test_a_host_that_changed_its_mind_stops_the_run_the_same_night():
    """robots is re-read every run, so `Disallow: /` is obeyed immediately."""
    contract = load_sources()
    feed = _feed("blog:vickiboykis.com")
    observed = _observations(feed, allowed=False)

    with pytest.raises(TermsNotReviewedError, match="feed_path_allowed"):
        assert_terms_reviewed(
            [feed],
            rulings=contract.rulings,
            observations={feed["id"]: observed},
            today=REVIEWED_ON,
        )


def test_a_robots_refusal_stops_the_run():
    """`refused` is a 401/403 on robots.txt — not one of the accepted statuses."""
    contract = load_sources()
    feed = _feed("blog:jxnl.co")
    observed = {**_observations(feed), "robots_status": "refused"}

    with pytest.raises(TermsNotReviewedError, match="robots_status"):
        assert_terms_reviewed(
            [feed],
            rulings=contract.rulings,
            observations={feed["id"]: observed},
            today=REVIEWED_ON,
        )


def test_recorded_evidence_the_ruling_asks_for_and_the_source_lacks():
    contract = load_sources()
    feed = dict(_feed("blog:slack.engineering"))
    feed["terms_evidence"] = {
        k: v for k, v in feed["terms_evidence"].items() if k != "paywall_observed"
    }
    with pytest.raises(TermsNotReviewedError, match="paywall_observed"):
        assert_terms_reviewed(
            [feed],
            rulings=contract.rulings,
            observations={feed["id"]: _observations(feed)},
            today=REVIEWED_ON,
        )


def test_an_unknown_ruling_id_is_refused_and_lists_the_known_ones():
    contract = load_sources()
    row = {
        "id": "blog:example.com",
        "endpoint": "https://example.com/feed",
        "tos_notes": "Class A, obviously.",
        "terms_ruling": "class-a",  # nearly right, which is the dangerous kind
        "terms_evidence": {"checked_on": REVIEWED_ON},
    }
    with pytest.raises(TermsNotReviewedError, match="nothing declares"):
        assert_terms_reviewed(
            [row], rulings=contract.rulings, observations={}, today=REVIEWED_ON
        )


def test_a_row_naming_a_ruling_while_still_carrying_the_marker_contradicts_itself():
    contract = load_sources()
    row = {
        "id": "blog:example.com",
        "endpoint": "https://example.com/feed",
        "tos_notes": "REVIEW REQUIRED before first harvest.",
        "terms_ruling": "blog-class-a-self-hosted",
        "terms_evidence": {
            "checked_on": REVIEWED_ON,
            "robots_status": "rules",
            "article_path_allowed": True,
            "paywall_observed": False,
            "login_required": False,
        },
    }
    with pytest.raises(TermsNotReviewedError, match="One of the two is wrong"):
        assert_terms_reviewed(
            [row],
            rulings=contract.rulings,
            observations={row["id"]: _observations(row)},
            today=REVIEWED_ON,
        )


def test_a_discovered_feed_is_gated_exactly_like_a_seeded_one():
    """The point of provenance: it labels the row, it does not excuse it."""
    contract = load_sources()
    discovered = {
        "id": "blog:example.com",
        "platform": "blog",
        "endpoint": "https://example.com/feed",
        "base_trust": 0.90,
        "provenance": "discovered",
        "tos_notes": "Class A, checked on discovery.",
        "terms_ruling": "blog-class-a-self-hosted",
        "terms_evidence": {
            "checked_on": REVIEWED_ON,
            "robots_status": "rules",
            "article_path_allowed": True,
            "paywall_observed": False,
            "login_required": False,
        },
    }
    assert_terms_reviewed(
        [discovered],
        rulings=contract.rulings,
        observations={discovered["id"]: _observations(discovered)},
        today=REVIEWED_ON,
    )

    # ... and the same row with nothing measured underneath it does not pass.
    bare = {**discovered, "terms_evidence": {"checked_on": REVIEWED_ON}}
    with pytest.raises(TermsNotReviewedError, match="Absent is not acceptable"):
        assert_terms_reviewed(
            [bare],
            rulings=contract.rulings,
            observations={bare["id"]: _observations(bare)},
            today=REVIEWED_ON,
        )


def test_the_refusal_cites_the_requirement():
    contract = load_sources()
    reddit = next(s for s in contract.platforms if s["id"] == "reddit")
    with pytest.raises(TermsNotReviewedError, match="NFR-5"):
        assert_terms_reviewed(
            [reddit], rulings=contract.rulings, observations={}, today=REVIEWED_ON
        )


def test_one_unreviewed_source_blocks_the_run():
    """Fails closed. Eight good feeds do not excuse the ninth."""
    contract = load_sources()
    feeds = list(contract.feeds)
    observations = {f["id"]: _observations(f) for f in feeds}
    observations[feeds[-1]["id"]] = {}  # the run observed nothing for this one

    with pytest.raises(TermsNotReviewedError) as excinfo:
        assert_terms_reviewed(
            feeds,
            rulings=contract.rulings,
            observations=observations,
            today=REVIEWED_ON,
        )
    message = str(excinfo.value)
    assert feeds[-1]["id"] in message
    assert feeds[0]["id"] not in message


def test_it_accepts_objects_as_well_as_mappings():
    """The loader may hand it rows or dataclasses; neither should surprise it."""

    class Row:
        id = "blogs"
        tos_notes = "..."
        terms_ruling = None

    with pytest.raises(TermsNotReviewedError, match="blogs"):
        assert_terms_reviewed([Row()], observations={}, today=REVIEWED_ON)


def test_no_sources_is_not_a_failure():
    assert_terms_reviewed([], observations={}, today=REVIEWED_ON)


# ── the loader ────────────────────────────────────────────────────────────


def test_a_ruling_with_no_expiry_is_rejected_at_load():
    """An undated ruling is a placeholder that learned to spell."""
    with pytest.raises(SourcesContractError, match="review date and an expiry"):
        parse_sources(
            {
                "terms_rulings": [
                    {"id": "class-a", "summary": "trust me", "reviewed_on": REVIEWED_ON}
                ]
            }
        )


def test_ruling_for_resolves_a_source_to_its_ruling():
    contract = load_sources()
    feed = _feed("blog:netflixtechblog.com")
    assert ruling_for(feed, rulings=contract.rulings).id == "blog-class-b-medium"
    assert ruling_for({"terms_ruling": None}, rulings=contract.rulings) is None


def test_the_marker_lives_in_the_contract_file():
    """The assertion default and the YAML must not drift apart."""
    assert _contract()["review_marker"] == "REVIEW REQUIRED"
