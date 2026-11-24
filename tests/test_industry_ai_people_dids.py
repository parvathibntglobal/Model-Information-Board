"""Two follow-ups to the people map (#653 review, 2026-11-24).

1. `bluesky_did`: a Bluesky post names its author only by DID. With the DID in the
   map, a post found by a KEYWORD query links to its person too, and a `from:<handle>`
   post by another DID - a handle that changed hands - links to no one.
2. `quiet_people`: a run-log note for each mapped handle whose watch query answered
   and found nothing - quiet for a week, or a handle that changed. A note, never a
   gate.
All pure: no network, no database.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.harvest import Harvest, QueryStat, quiet_people
from collect.industry_ai.rules import Item, person_of

NOW = datetime(2026, 11, 24, tzinfo=UTC)
MOLLICK_DID = "did:plc:flxq4uyjfotciovpw3x3fxnu"


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg(raw):
    return iai_config.parse(copy.deepcopy(raw))


def bsky(author, keys=()):
    return Item(id=f"bluesky:{author}:{len(keys)}", platform="bluesky", external_id="1",
                url="https://bsky.app/profile/x/post/1", title="", body="text",
                created_at=NOW, author_id=author, query_keys=set(keys))


# ── the DIDs ─────────────────────────────────────────────────────────────────


def test_every_mapped_bluesky_handle_has_its_did(cfg):
    people = cfg.watch["people"]
    with_bluesky = [p for p, e in people.items() if "bluesky" in e]
    assert sorted(cfg.person_by_did().values()) == sorted(with_bluesky)
    assert cfg.person_by_did()[MOLLICK_DID] == "ethan_mollick"
    assert all(k[0] != "bluesky_did" for k in cfg.person_by_handle()), "an id is not a handle"


@pytest.mark.parametrize("mutate, says", [
    (lambda p: p["max_woolf"].update(bluesky_did="did:plc:short"), "not a Bluesky DID"),
    (lambda p: p["max_woolf"].update(bluesky_did=MOLLICK_DID), "already belongs"),
    (lambda p: p.update(nobsky={"x": "karpathy", "hackernews": "tptacek",
                                "bluesky_did": "did:plc:aaaaaaaaaaaaaaaaaaaaaaaa"}),
     "needs a bluesky handle"),
    # A DID is not a platform: it never makes up the two a person needs.
    (lambda p: p.update(one={"x": "karpathy", "bluesky_did": "did:plc:bbbbbbbbbbbbbbbbbbbbbbbb"}),
     "at least two platforms"),
])
def test_the_did_is_read_strictly(raw, mutate, says):
    bad = copy.deepcopy(raw)
    mutate(bad["watch"]["people"])
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(bad)


def test_a_keyword_found_post_links_by_its_did(cfg):
    assert person_of(bsky(MOLLICK_DID, ["iai:marketing:bluesky:q"]), cfg) == "ethan_mollick"


def test_a_from_post_by_another_did_links_no_one(cfg):
    """The handle has passed to another account: linking it would count a stranger."""
    stranger = bsky("did:plc:zzzzzzzzzzzzzzzzzzzzzzzz", ["watch:bluesky:from:emollick.bsky.social"])
    assert person_of(stranger, cfg) is None
    same = bsky(MOLLICK_DID, ["watch:bluesky:from:emollick.bsky.social"])
    assert person_of(same, cfg) == "ethan_mollick"


def test_without_a_did_the_handle_still_links(raw):
    """`bluesky_did` is optional: a person written without one links by handle, as before."""
    r = copy.deepcopy(raw)
    del r["watch"]["people"]["ethan_mollick"]["bluesky_did"]
    cfg = iai_config.parse(r)
    post = bsky("did:plc:zzzzzzzzzzzzzzzzzzzzzzzz", ["watch:bluesky:from:emollick.bsky.social"])
    assert person_of(post, cfg) == "ethan_mollick"


# ── quiet handles ────────────────────────────────────────────────────────────


def _x_item(handle, iid):
    return Item(id=f"x:{iid}", platform="x", external_id=iid,
                url=f"https://x.com/{handle}/status/{iid}", title="", body="t",
                created_at=NOW, query_keys={"watch:x:(from:emollick OR from:karpathy)"})


def test_a_handle_whose_query_answered_empty_gets_a_note(cfg):
    out = Harvest()
    out.queries = [
        QueryStat("watch:bluesky:from:emollick.bsky.social", "watch", "bluesky",
                  "from:emollick.bsky.social", items=0),
        QueryStat("watch:hackernews:hn:author:simonw", "watch", "hackernews",
                  "hn:author:simonw", items=4),
        QueryStat("watch:x:(from:emollick OR from:karpathy)", "watch", "x",
                  "(from:emollick OR from:karpathy)", items=1),
    ]
    out.items = {"x:1": _x_item("emollick", "1")}
    notes = quiet_people(cfg, out)
    assert any("bluesky: emollick.bsky.social (ethan_mollick)" in n for n in notes)
    assert any("x: karpathy (andrej_karpathy)" in n for n in notes), "X: no post of his came back"
    assert not any("x: emollick" in n for n in notes)
    assert not any("hackernews: simonw" in n for n in notes)


@pytest.mark.parametrize("status", ["error", "skipped", "capped"])
def test_a_query_that_did_not_answer_says_nothing_about_the_handle(cfg, status):
    out = Harvest()
    out.queries = [QueryStat("watch:bluesky:from:emollick.bsky.social", "watch", "bluesky",
                             "from:emollick.bsky.social", items=0, status=status),
                   QueryStat("watch:x:(from:emollick OR from:karpathy)", "watch", "x",
                             "(from:emollick OR from:karpathy)", status=status)]
    assert quiet_people(cfg, out) == []


def test_a_platform_not_run_says_nothing(cfg):
    assert quiet_people(cfg, Harvest()) == []
