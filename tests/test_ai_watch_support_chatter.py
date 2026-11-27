"""The AI Watch review (iai-8, 2026-11-27, agreed with the team), items 4 and 8:
  * `support_chatter`: a Reddit post that opens on an AI tool's account rather than its
    use is FLAGGED, never dropped (rule 8), unless it also says what someone did with
    the tool (`unless`);
  * every watch source's kept posts and how many carry a review flag, for the run log
    (pipeline `watch_sources`); the Sources tab's SQL is pinned in test_ai_watch_view.py.

Every case runs on the real contract (contract/industry_ai.yaml).
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, FLAG_NAMES, IndustryAIConfigError
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import Item, review_flags

NOW = datetime(2026, 11, 27, tzinfo=UTC)
SINCE = NOW - timedelta(days=365)
WATCH = "watch:reddit:r/ClaudeAI"


@pytest.fixture(scope="module")
def cfg():
    return iai_config.load()


@pytest.fixture
def raw():
    return copy.deepcopy(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))


def item(title, body="", *, platform="reddit", iid=None, keys=(WATCH,), author="t2_a"):
    iid = iid or f"{platform}:{abs(hash((title, body, platform, author))) % 10**8}"
    return Item(
        id=iid, platform=platform, external_id=iid.split(":", 1)[1],
        url=f"https://e.x/{iid}", title=title, body=body,
        created_at=NOW - timedelta(hours=5), author_id=author,
        engagement={"score": 5}, domain_hints=set(), query_keys=set(keys),
    )


def flagged(it, cfg):
    return "support_chatter" in review_flags(it, cfg)


@pytest.mark.parametrize("title", [
    "Hitting usage limits on the ChatGPT plan, how do you stretch it?",
    "Claude account banned with zero notice",
    "Anyone else having 529 overloaded_error from the Claude API today?",
    "How do I get a refund on my annual Mistral plan?",
    "Is Gemini down for anyone else?",
    "Weekly limit reset early for Codex users",
])
def test_support_chatter_is_flagged_and_kept(cfg, title):
    it = item(title, "Same here, ChatGPT and Claude both.")
    assert flagged(it, cfg)
    results, _ = evaluate([it], cfg, since=SINCE, now=NOW)
    assert results[it.id].verdict == "kept", "a flag, never a drop"
    assert "support_chatter" in results[it.id].flags


def test_a_limit_mentioned_deep_in_a_post_is_not_flagged(cfg):
    # 2026-11-27: about half the anywhere-in-the-text hits were benchmark and project
    # write-ups naming a limit in passing; only the opening counts.
    it = item("Two identical red-team runs of the same Claude agent scored 49 and 41",
              "We ran the same agent twice on the same afternoon. " * 6
              + "Between runs we hit the usage limit once.")
    assert not flagged(it, cfg)


def test_a_post_that_says_what_someone_did_is_not_flagged(cfg):
    assert not flagged(item("I made a tool to resume Claude Code tasks after usage limits"), cfg)
    assert not flagged(item("Rate limited on the OpenAI API: here's how we cut tokens by 40%"), cfg)
    # "built-in" is not "built".
    assert flagged(item("Anyone else having issues with the ChatGPT built-in browser?"), cfg)


def test_shadow_banned_and_a_suspended_person_are_not_support(cfg):
    assert not flagged(item("Shadow-banned progress topics in ChatGPT answers?"), cfg)
    assert not flagged(item("Lawyer suspended after AI fabricated court cases"), cfg)


def test_a_ban_is_an_account_ban_not_policy_news(cfg):
    # #689 review, point 3.
    assert flagged(item("I got suddenly banned from ChatGPT, nothing works"), cfg)
    assert not flagged(item("Italy banned DeepSeek from government phones"), cfg)
    assert not flagged(item("The agency banned staff from using ChatGPT"), cfg)


def test_down_must_end_the_question(cfg):
    # #689 review, point 4.
    assert flagged(item("Is Claude down right now?"), cfg)
    assert not flagged(item("How Claude is breaking down my codebase into modules"), cfg)


def test_an_ordinary_later_sentence_does_not_unflag_a_complaint(cfg):
    # #689 review, point 2: `unless` reads the whole post, so it needs a doing verb.
    assert flagged(item("Weekly limits on Claude", "These limits are killing my workflow."), cfg)
    assert flagged(item("Refund for ChatGPT Plus?", "I wrote to support twice, no reply."), cfg)
    assert flagged(item("Hitting usage limits on Codex", "We made the switch last month."), cfg)
    assert flagged(item("Hitting usage limits on Codex", "I wrote a long complaint."), cfg)
    assert not flagged(item("Hitting usage limits on Codex",
                            "I run my workflow through two accounts now."), cfg)


def test_reddit_only(cfg):
    assert not flagged(item("Hitting usage limits on ChatGPT again", platform="bluesky",
                            keys=("watch:bluesky:from:a.bsky.social",)), cfg)


def test_the_page_names_every_flag_and_judge_lists_the_same_flags():
    from judge.industry_ai.view import RUN_FLAGS, _contract

    assert "support_chatter" in FLAG_NAMES
    assert {*(_contract()["flag_patterns"]), *RUN_FLAGS} == set(FLAG_NAMES)


@pytest.mark.parametrize("mutate, says", [
    (lambda r: r["flag_patterns"]["support_chatter"].update(unless=[]), "unless must not be empty"),
    (lambda r: r["flag_patterns"]["support_chatter"].update(unless=["("]), "not a valid pattern"),
    (lambda r: r["flag_patterns"]["support_chatter"].update(when=["x"]), "when"),
])
def test_a_bad_unless_is_refused(raw, mutate, says):
    mutate(raw)
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(raw)


def test_watch_sources_count_kept_and_flagged_posts(cfg):
    support = item("Hitting usage limits on Claude again", "Pro plan, two hours in.",
                   iid="reddit:t3_s1", author="t2_s")
    fine = item("Claude wrote our whole migration plan", "It took an afternoon with ChatGPT.",
                iid="reddit:t3_f1", author="t2_f")
    other = item("ChatGPT voice mode is great for language practice", "Every morning.",
                 iid="reddit:t3_o1", author="t2_o", keys=("watch:reddit:r/ChatGPT",))
    keyword = item("ChatGPT for accounting close", "We use ChatGPT for the month-end close.",
                   iid="reddit:t3_k1", author="t2_k", keys=("iai:finance:reddit:q",))
    _, counts = evaluate([support, fine, other, keyword], cfg, since=SINCE, now=NOW)
    ws = counts["watch_sources"]
    assert ws[WATCH] == {"kept": 2, "flagged": 1, "flags": {"support_chatter": 1}}
    assert ws["watch:reddit:r/ChatGPT"] == {"kept": 1, "flagged": 0, "flags": {}}
    assert list(ws) == [WATCH, "watch:reddit:r/ChatGPT"], "busiest first, keyword keys out"
