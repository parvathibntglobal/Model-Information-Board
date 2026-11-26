"""The kept-post review (iai-7, 2026-11-26, agreed with the team): what matching
ignores, the six review flags (never drops), use-case patterns that must name AI,
Supply chain's software senses, and the two new duplicate folds.

Every case runs on the real contract (contract/industry_ai.yaml), so a contract
change that alters what one of these posts becomes is seen here.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, FLAG_NAMES, IndustryAIConfigError
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import Item, match_text, review_flags, sieve

NOW = datetime(2026, 11, 26, tzinfo=UTC)
SINCE = NOW - timedelta(days=365)


@pytest.fixture(scope="module")
def cfg():
    return iai_config.load()


@pytest.fixture
def raw():
    return copy.deepcopy(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))


def item(text, *, platform="reddit", hints=("finance",), iid=None, author="t2_a",
         hours=72, keys=None, title=""):
    iid = iid or f"{platform}:{abs(hash((text, platform, author))) % 10**8}"
    return Item(
        id=iid, platform=platform, external_id=iid.split(":", 1)[1],
        url=f"https://e.x/{iid}", title=title, body=text,
        created_at=NOW - timedelta(hours=hours), author_id=author,
        engagement={"score": 5}, domain_hints=set(hints),
        query_keys=set(keys or [f"iai:{hints[0]}:{platform}:q"]),
    )


def run(cfg, *items):
    results, _ = evaluate(list(items), cfg, since=SINCE, now=NOW)
    return results


# ── what matching ignores ────────────────────────────────────────────────────


def test_links_and_handles_are_taken_out_and_hashtags_stay(cfg):
    assert cfg.run["match_strip"] == ["links", "handles"]
    t = match_text("See https://e.x/accounting-ai and @accounting_ai on #accounting", cfg)
    assert "https" not in t and "@accounting_ai" not in t and "#accounting" in t


def test_an_industry_word_only_in_a_link_does_not_file_a_post(cfg):
    r = run(cfg, item("Thoughts on ChatGPT this week, worth a read https://e.x/accounting-tips"))
    only = next(iter(r.values()))
    assert (only.verdict, only.reason) == ("dropped", "no_domain_term")


def test_an_ai_word_only_in_a_handle_does_not_count(cfg):
    why, _, ai = sieve(item("Our accounting team met @chatgpt_fan for coffee and cake today."), cfg)
    assert why == "no_ai_term" and ai == []


def test_an_email_address_is_not_a_handle(cfg):
    assert "ops@chatgpt.example" in match_text("Write to ops@chatgpt.example today", cfg)


def test_a_hashtag_still_counts(cfg):
    it = item("Month-end close went faster this quarter. #ChatGPT #accounting")
    why, terms, _ = sieve(it, cfg)
    assert why is None and "finance" in terms


# ── the flags: present, named, never a drop ──────────────────────────────────


def test_every_flag_has_a_name_the_pages_know():
    from pathlib import Path

    posts = (Path(__file__).resolve().parents[1] / "web" / "src" / "industry-ai"
             / "posts.jsx").read_text(encoding="utf-8")
    for name in FLAG_NAMES:
        assert f"  {name}: '" in posts, f"{name} has no words in posts.jsx FLAG_LABEL"


GITHUB = ("[Feature] Add an LLM step to the accounting export\n\n"
          "- [ ] parse invoices\n- [ ] acceptance criteria written")


def test_a_github_todo_list_is_flagged_and_kept(cfg):
    it = item(GITHUB, platform="github")
    assert "github_tracking" in review_flags(it, cfg)
    r = run(cfg, it)[it.id]
    assert r.verdict == "kept" and "github_tracking" in r.flags
    # GitHub only: the same words on Reddit are not a tracker.
    assert "github_tracking" not in review_flags(item(GITHUB, platform="reddit"), cfg)


def test_the_word_epic_is_not_a_tracker(cfg):
    it = item("An epic thread on how our accounting team uses ChatGPT.", platform="github")
    assert "github_tracking" not in review_flags(it, cfg)


def test_market_chatter_needs_two_tickers_in_capitals(cfg):
    assert "market_chatter" in review_flags(
        item("$NVDA and $AMD both slid today; AI accounting fears again."), cfg)
    assert "market_chatter" not in review_flags(
        item("I spent $5k on an AI accounting tool and $2k on training."), cfg)
    assert "market_chatter" not in review_flags(
        item("An AI start-up for accounting raised $12M in a seed round."), cfg)


def test_for_sale_is_flagged(cfg):
    it = item("Premium AI domain name for sale, ideal for fintech.")
    assert "for_sale" in review_flags(it, cfg)
    # 2026-11-26 sample: a news line, not an offer.
    news = item("Your AI friend is going bankrupt. Your secrets are now for sale, says the BBC.")
    assert "for_sale" not in review_flags(news, cfg)


def test_a_short_x_reply_is_flagged_and_a_full_one_is_not(cfg):
    floor = int(cfg.run["reply_min_own_words"])
    short = item("@someone yes, ChatGPT handles our accounting now", platform="x")
    assert "reply_fragment" in review_flags(short, cfg)
    long_ = item("@someone " + " ".join(["word"] * floor) + " ChatGPT accounting", platform="x")
    assert "reply_fragment" not in review_flags(long_, cfg)
    not_reply = item("Yes, ChatGPT handles our accounting now", platform="x")
    assert "reply_fragment" not in review_flags(not_reply, cfg)


FILLER = "the cat sat on the mat and then it slept for a while. " * 8


def test_ai_far_from_the_industry_word_is_flagged(cfg):
    far = item("Accounting season is here for the team. " + FILLER
               + "Separately I asked ChatGPT about holiday plans.")
    r = run(cfg, far)[far.id]
    assert r.verdict == "kept" and "ai_far_from_industry" in r.flags
    near = item("Our accounting team uses ChatGPT to draft reminders for clients each week.")
    assert "ai_far_from_industry" not in run(cfg, near)[near.id].flags


def test_a_heavy_poster_is_flagged_and_a_watched_account_never(cfg):
    floor = int(cfg.run["heavy_poster_min_posts"])
    # Different WORDS per post: duplicate checks ignore digits, so "case 1" and "case 2"
    # would be one post repeated.
    nouns = ["invoices", "payroll", "audits", "budgets", "receipts", "ledgers", "taxes",
             "forecasts", "expenses", "reconciliations", "statements", "accruals"]
    def text(i):
        return f"Our accounting team tried ChatGPT on {nouns[i]} this week, with mixed results."

    many = [item(text(i), iid=f"reddit:h{i}", author="t2_heavy") for i in range(floor)]
    results = run(cfg, *many)
    assert all("heavy_poster" in results[it.id].flags for it in many)
    assert all(results[it.id].verdict == "kept" for it in many), "a flag, never a drop"
    fewer = run(cfg, *many[:-1])
    assert not any("heavy_poster" in r.flags for r in fewer.values())
    watched = [item(text(i), iid=f"reddit:w{i}", author="t2_w",
                    keys=["watch:reddit:r/accounting"]) for i in range(floor)]
    assert not any("heavy_poster" in r.flags for r in run(cfg, *watched).values())


def test_a_long_post_kept_on_the_bare_word_ai_is_flagged(cfg):
    words = int(cfg.run["long_post_words"])
    body = "Our accounting team closed the books early this quarter. " + " ".join(
        ["the", "cat", "sat", "on", "a", "mat"] * (words // 6 + 1))
    weak = item(body + " Someone mentioned ai once.")
    r = run(cfg, weak)[weak.id]
    assert r.verdict == "kept" and "weak_ai_long_post" in r.flags
    strong = item(body + " We use ChatGPT for the reminders.")
    assert "weak_ai_long_post" not in run(cfg, strong)[strong.id].flags
    short = item("Our accounting team uses ai for reminders every single week now.")
    assert "weak_ai_long_post" not in run(cfg, short)[short.id].flags


# ── use cases must name AI in the same sentence ──────────────────────────────


def test_since_a_month_without_ai_in_the_sentence_is_not_a_use_case(cfg):
    it = item("Most AI projects promise a lot. "
              "Our accounting shop made $120K revenue since February.")
    r = run(cfg, it)[it.id]
    assert r.verdict == "kept" and r.content_type != "use_case"


def test_ai_in_production_is_still_a_use_case(cfg):
    it = item("Our accounting team has run an AI agent in production since March.")
    assert run(cfg, it)[it.id].content_type == "use_case"


def test_every_use_case_pattern_names_ai(cfg):
    assert all({"ai", "sentence"} & set(p.groupindex) for p in cfg.type_patterns["use_case"])


def test_the_sentence_stops_at_its_ends_and_its_bound():
    from collect.industry_ai.rules import SENTENCE_CHARS, sentence_of

    text = "We love AI. Our shop grew since February! Next."
    i = text.index("since")
    assert sentence_of(text, i, i + 5) == " Our shop grew since February"
    long_ = "x" * (SENTENCE_CHARS * 2) + " since May " + "y" * (SENTENCE_CHARS * 2)
    j = long_.index("since")
    assert len(sentence_of(long_, j, j + 5)) == SENTENCE_CHARS * 2 + 5


# ── supply chain's software senses ───────────────────────────────────────────


def test_a_software_supply_chain_is_not_supply_chain(cfg):
    _, terms, _ = sieve(item("Our LLM scanner catches npm supply chain attacks in packages.",
                             hints=("supply_chain",)), cfg)
    assert "supply_chain" not in terms


def test_root_cause_analysis_of_software_is_not_supply_chain(cfg):
    _, outage, _ = sieve(item("We use an LLM for root-cause analysis of website outages.",
                              hints=("supply_chain",)), cfg)
    assert "supply_chain" not in outage
    _, logs, _ = sieve(item("Our SRE team reads logs, and ChatGPT now drafts the root cause "
                            "analysis.", hints=("supply_chain",)), cfg)
    assert "supply_chain" not in logs
    plant_post = item("We use an LLM for root-cause analysis of defects on the factory floor.",
                      hints=("supply_chain",))
    _, plant, _ = sieve(plant_post, cfg)
    assert "supply_chain" in plant


def test_put_away_in_ordinary_english_is_not_a_warehouse_step(cfg):
    def sc(text):
        return sieve(item(text, hints=("supply_chain",)), cfg)[1].get("supply_chain")

    assert sc("AI must be put away now, before it ruins every classroom.") is None
    assert sc("Our LLM plans the put-away route for every pallet.") is not None
    assert sc("ChatGPT tells pickers where to put away stock in the warehouse.") is not None


# ── duplicates: other accounts, and cross-posts by anyone ────────────────────


TEXT = "Accounting firms are now using ChatGPT to draft client reminders, a big change"


def test_the_same_text_from_another_account_is_one_post(cfg):
    a = item(TEXT + " https://t.co/AAA", platform="x", author="1", iid="x:1", hours=10)
    b = item(TEXT + " https://t.co/BBB @friend", platform="x", author="2", iid="x:2", hours=8)
    r = run(cfg, a, b)
    assert r["x:1"].verdict == "kept" and r["x:1"].share_count == 1
    assert (r["x:2"].reason, r["x:2"].canonical_of) == ("copied_post", "x:1")


def test_a_text_that_only_starts_the_same_is_two_posts(cfg):
    a = item(TEXT + ".", platform="x", author="1", iid="x:3")
    b = item(TEXT + ". And our auditors approved the new month-end checklist too.",
             platform="x", author="2", iid="x:4")
    r = run(cfg, a, b)
    assert r["x:3"].verdict == r["x:4"].verdict == "kept"


def test_a_cross_post_by_anyone_is_one_post(cfg):
    x = item(TEXT, platform="x", author="1", iid="x:5", hours=10)
    b = item(TEXT, platform="bluesky", author="did:plc:someone", iid="bluesky:6", hours=9)
    r = run(cfg, x, b)
    assert (r["bluesky:6"].reason, r["bluesky:6"].canonical_of) == ("cross_post", "x:5")
    assert "cross_post" in r["x:5"].flags


# ── the contract refuses what it cannot apply ────────────────────────────────


@pytest.mark.parametrize("mutate, says", [
    (lambda r: r["run"].pop("heavy_poster_min_posts"), "heavy_poster_min_posts"),
    (lambda r: r["run"].update(match_strip=["links", "emoji"]), "match_strip"),
    (lambda r: r["run"].update(reply_min_own_words=0), "reply_min_own_words"),
    (lambda r: r["run"].update(weak_ai_terms=["not an ai term"]), "weak_ai_terms"),
    (lambda r: r["run"].pop("long_post_words"), "long_post_words"),
    (lambda r: r["flag_patterns"].pop("for_sale"), "flag_patterns must name exactly"),
    (lambda r: r["flag_patterns"].update(mystery={"platforms": "all", "patterns": ["x"]}),
     "flag_patterns must name exactly"),
    (lambda r: r["flag_patterns"]["for_sale"].update(platforms=["myspace"]), "unknown"),
    (lambda r: r["flag_patterns"]["for_sale"].update(patterns=[]), "must not be empty"),
    (lambda r: r.pop("flag_patterns"), "flag_patterns"),
])
def test_a_missing_or_unknown_setting_is_refused(raw, mutate, says):
    mutate(raw)
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(raw)
