"""RFC 9309 rule matching, against the files that made it necessary.

`urllib.robotparser` implements the 1996 draft: no `*`, no `$`, and
first-match-in-file-order rather than most-specific-match. Both read a
forbidden path as permitted, which is the one direction a robots gate must
never fail in.

Every case here is either measured against a real host on 2026-08-14 or is a
construct RFC 9309 names. The Medium fixture is the real file, byte for byte,
so the ruling in `contract/sources.yaml` and the file it describes cannot
drift apart silently.
"""

from __future__ import annotations

from pathlib import Path
from urllib.robotparser import RobotFileParser

import pytest

from collect.adapters.blog.rules import (
    MAX_WILDCARDS,
    allowance_for,
    compile_pattern,
    decide,
    path_for_matching,
    rules_from_entry,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "blog"
UA = "modelboard/0.1 (+https://modelboard.invalid/about)"


def parser_for(name: str) -> RobotFileParser:
    parser = RobotFileParser()
    parser.parse((FIXTURES / name).read_text(encoding="utf-8").splitlines())
    return parser


def allowed(name: str, agent: str, url: str) -> bool:
    return allowance_for(parser_for(name), agent, url).allowed


def stdlib_allowed(name: str, agent: str, url: str) -> bool:
    """What we shipped before this module, for the side-by-side."""
    return parser_for(name).can_fetch(agent, url)


# ── wildcards ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("agent", "url", "permitted"),
    [
        # medium.com's live rule against a real Medium feed link.
        ("case-medium-source",
         "https://medium.com/airbnb-engineering/x-3a8a4c9?source=rss----53c7---4", False),
        # ... and the same rule against a URL with no ?source=.
        ("case-medium-source", "https://medium.com/airbnb-engineering/x-3a8a4c9", True),
        ("case-mid-path", "https://x.invalid/private/a/secret", False),
        ("case-mid-path", "https://x.invalid/private/secret", True),
        ("case-end-anchor", "https://x.invalid/docs/manual.pdf", False),
        # The anchor means the pattern ends: .pdf.html is a different path.
        ("case-end-anchor", "https://x.invalid/docs/manual.pdf.html", True),
        ("case-anchor-excludes", "https://x.invalid/page", False),
        ("case-anchor-excludes", "https://x.invalid/page/sub", True),
        # RFC 9309 2.2.2: an empty Disallow forbids nothing.
        ("case-empty-disallow", "https://x.invalid/anything", True),
    ],
)
def test_wildcards_are_honoured(agent, url, permitted):
    assert allowed("robots_wildcards.txt", agent, url) is permitted


def test_the_wildcard_cases_are_ones_the_stdlib_gets_wrong():
    """The regression, stated as a comparison rather than asserted in prose.

    Three URLs the host forbids and `can_fetch` permits. If a future Python
    fixes `RuleLine.applies_to`, this test starts failing and the module can
    be reconsidered — which is the outcome we would want to notice.
    """
    leaks = [
        ("case-medium-source",
         "https://medium.com/airbnb-engineering/x-3a8a4c9?source=rss----53c7---4"),
        ("case-mid-path", "https://x.invalid/private/a/secret"),
        ("case-end-anchor", "https://x.invalid/docs/manual.pdf"),
    ]
    for agent, url in leaks:
        assert stdlib_allowed("robots_wildcards.txt", agent, url) is True, url
        assert allowed("robots_wildcards.txt", agent, url) is False, url


# ── precedence ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("agent", "url", "permitted", "note"),
    [
        ("case-leak", "https://x.invalid/private/secret", False,
         "broad allow first, narrow disallow after — the leak"),
        ("case-overrestrictive", "https://x.invalid/blog/post", True,
         "broad disallow first, narrow allow after"),
        ("case-equivalent", "https://x.invalid/x", True,
         "equivalent rules resolve to allow (RFC 9309 2.2.2)"),
        ("case-wp-admin", "https://x.invalid/wp-admin/admin-ajax.php", True,
         "live on slack.engineering 2026-08-14"),
        ("case-wp-admin", "https://x.invalid/wp-admin/options.php", False,
         "the narrow allow does not open the rest of /wp-admin/"),
        ("case-static-assets", "https://x.invalid/static/images/logo.png", True,
         "live on engineering.atspotify.com 2026-08-14"),
        ("case-static-assets", "https://x.invalid/static/app.js", False,
         "the narrow allow does not open the rest of /static/"),
    ],
)
def test_most_specific_match_wins(agent, url, permitted, note):
    assert allowed("robots_precedence.txt", agent, url) is permitted, note


def test_the_leak_case_is_one_the_stdlib_gets_wrong():
    """`Allow: /` then `Disallow: /private/` — a forbidden path read as permitted.

    Absent from the nine seeded feeds as of 2026-08-14, which is why this fix
    is prospective rather than remedial. It is a common idiom elsewhere.
    """
    url = "https://x.invalid/private/secret"
    assert stdlib_allowed("robots_precedence.txt", "case-leak", url) is True
    assert allowed("robots_precedence.txt", "case-leak", url) is False


def test_the_two_live_conflicts_currently_cost_coverage_not_consent():
    """Both real instances err toward refusal. The fix returns two paths."""
    for agent, url in [
        ("case-wp-admin", "https://x.invalid/wp-admin/admin-ajax.php"),
        ("case-static-assets", "https://x.invalid/static/images/logo.png"),
    ]:
        assert stdlib_allowed("robots_precedence.txt", agent, url) is False
        assert allowed("robots_precedence.txt", agent, url) is True


# ── unparsable rules, and the prefix bound ────────────────────────────────


def test_an_unparsable_rule_refuses_only_under_its_literal_prefix():
    """The whole point of bounding: one bad rule must not take a host offline.

    `Disallow: /reports/$archive` has a `$` before the end, which RFC 9309
    leaves undefined. We refuse `/reports/*` — where it might apply — and
    clear everything else, because an unevaluable rule cannot match outside
    its literal prefix.
    """
    name = "robots_wildcards.txt"
    assert allowed(name, "case-unparsable", "https://x.invalid/reports/2026") is False
    assert allowed(name, "case-unparsable", "https://x.invalid/reports/") is False
    assert allowed(name, "case-unparsable", "https://x.invalid/blog/post") is True
    assert allowed(name, "case-unparsable", "https://x.invalid/") is True


def test_the_refusal_names_the_rule_and_the_scope():
    """A rejection nobody can audit is a rejection nobody will trust."""
    verdict = allowance_for(
        parser_for("robots_wildcards.txt"),
        "case-unparsable",
        "https://x.invalid/reports/2026",
    )
    assert verdict.allowed is False
    assert "could not evaluate" in verdict.reason
    assert "/reports/$archive" in verdict.reason
    assert "'/reports/'" in verdict.reason, "the reason must state the bounded scope"


def test_a_pathological_pattern_is_refused_rather_than_compiled():
    """robots.txt is input we do not control, and `.*` repeated backtracks."""
    rule = compile_pattern("/" + "*/" * (MAX_WILDCARDS + 1), allow=False)
    assert not rule.parsable
    assert "wildcards" in rule.unparsable_because
    assert rule.literal_prefix == "/", "still bounded, so it refuses only /"


def test_an_unparsable_allow_also_fails_closed():
    """Direction does not matter: we could not read it, so it did not say yes."""
    rules = [compile_pattern("/x/$y", allow=True)]
    assert decide(rules, "/x/anything").allowed is False
    assert decide(rules, "/other").allowed is True


# ── the real Medium file ──────────────────────────────────────────────────


def test_the_medium_fixture_is_the_file_the_ruling_describes():
    """`contract/sources.yaml`'s class B ruling cites this file. Pin it.

    The ruling says 39 lines, 37 rule lines, and a `License` line pointing at
    medium.com. If Medium changes the file, this fails and the ruling gets
    re-read — which is the point of an expiring ruling with dated evidence.
    """
    text = (FIXTURES / "robots_medium.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    rule_lines = [
        line for line in lines
        if line.strip().lower().startswith(("user-agent", "disallow", "allow"))
    ]
    assert len(lines) == 39
    assert len(rule_lines) == 37
    assert "License: https://medium.com/license.xml" in text
    assert "Disallow: /*/*source=" in text


def test_medium_forbids_every_article_link_its_own_feed_hands_us():
    """5 of 6 sampled Airbnb URLs, measured 2026-08-14, permitted by the stdlib."""
    url = (
        "https://medium.com/airbnb-engineering/"
        "flexible-authentication-3a8a4c917137?source=rss----53c7c27702d5---4"
    )
    assert stdlib_allowed("robots_medium.txt", UA, url) is True
    assert allowed("robots_medium.txt", UA, url) is False


def test_the_same_rule_does_not_reach_a_custom_domains_article_paths():
    """The finding that only decomposed measurement surfaces.

    `netflixtechblog.com` serves the same 37 rule lines. `/*/*source=`
    compiles to `^/.*/.*source=`, which needs two slashes before `source=`:

        medium.com/airbnb-engineering/<slug>?source=   two   disallowed
        netflixtechblog.com/<slug>?source=             one   NOT disallowed

    A publication on medium.com is /<publication>/<slug>; a custom domain is
    /<slug>. So the identical rule set means different things on the two
    hosts, and on Netflix only the 403 stops us. `contract/sources.yaml`
    claimed otherwise until this was measured.
    """
    on_medium = "https://medium.com/airbnb-engineering/x-3a8a4c9?source=rss----53c7---4"
    on_custom = "https://netflixtechblog.com/x-0f34683?source=rss----2615---4"

    assert allowed("robots_medium.txt", UA, on_medium) is False
    assert allowed("robots_medium.txt", UA, on_custom) is True
    assert path_for_matching(on_custom).count("/") == 1


def test_medium_still_permits_the_feed_path():
    """Feed-only is a real permission, not a consolation prize."""
    assert allowed("robots_medium.txt", UA, "https://medium.com/feed/airbnb-engineering")
    assert allowed("robots_medium.txt", UA, "https://netflixtechblog.com/feed")


def test_medium_disallows_what_it_says_it_disallows():
    for path in ("/m/signin", "/me/settings", "/r/abc", "/trending"):
        assert allowed("robots_medium.txt", UA, f"https://medium.com{path}") is False


# ── the user-agent claim the class B ruling rests on ──────────────────────


def test_our_user_agent_matches_none_of_mediums_named_bot_group():
    """`contract/sources.yaml` says so in prose. This is the check.

    Medium disallows ClaudeBot, GPTBot, Bytespider, Amazonbot,
    Applebot-Extended, FacebookBot, GoogleOther and meta-externalagent from
    everything. Our token is `modelboard`, so the `*` group applies — and the
    day somebody puts one of those strings in the User-Agent, the ruling is
    void and the feeds are disallowed outright. That is a live dependency of
    the class B ruling and it was resting on a paragraph.
    """
    named = (
        "ClaudeBot", "GPTBot", "Bytespider", "Amazonbot",
        "Applebot-Extended", "FacebookBot", "GoogleOther", "meta-externalagent",
    )
    text = (FIXTURES / "robots_medium.txt").read_text(encoding="utf-8")
    for bot in named:
        assert f"User-Agent: {bot}" in text, f"{bot} left Medium's named group"

    feed = "https://medium.com/feed/airbnb-engineering"
    assert allowed("robots_medium.txt", UA, feed) is True

    for bot in named:
        assert allowed("robots_medium.txt", f"{bot}/1.0", feed) is False, (
            f"{bot} is disallowed from everything, including the feed"
        )


def test_the_user_agent_token_is_what_matching_uses():
    """`Entry.applies_to` splits on '/' and takes the first token."""
    assert UA.split("/")[0].lower() == "modelboard"


# ── plumbing ──────────────────────────────────────────────────────────────


def test_the_query_string_is_part_of_the_path_that_rules_see():
    """`/*/*source=` says nothing about a path without the query."""
    assert path_for_matching("https://x.invalid/a/b?source=rss") == "/a/b?source=rss"
    assert path_for_matching("https://x.invalid/a/b#frag") == "/a/b"
    assert path_for_matching("https://x.invalid") == "/"


def test_percent_encoded_patterns_are_decoded_before_comparison():
    """RobotFileParser stores `/*/*source=` as `/%2A/%2Asource%3D`.

    Recovering the pattern is what makes wildcards visible at all. The
    documented cost is that a literal `%2A` in a robots.txt is now
    indistinguishable from `*` — over-broad, so it refuses more than the
    publisher wrote rather than less, which is the safe direction.
    """
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /*/*source="])
    stored = parser.default_entry.rulelines[0].path
    assert stored == "/%2A/%2Asource%3D", "the encoding this module has to undo"

    rules = rules_from_entry(parser.default_entry)
    assert rules[0].pattern == "/*/*source="
    assert rules[0].parsable


def test_an_empty_disallow_is_dropped_rather_than_matched():
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow:"])
    assert rules_from_entry(parser.default_entry) == ()


def test_a_group_that_does_not_apply_leaves_us_allowed():
    parser = RobotFileParser()
    parser.parse(["User-agent: SomeOtherBot", "Disallow: /"])
    verdict = allowance_for(parser, UA, "https://x.invalid/anything")
    assert verdict.allowed is True
