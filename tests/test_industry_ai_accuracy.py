"""The accuracy fixes from the first real run's review (2026-11-24, pipeline_version iai-3).

Each case is a shape read on the first run's stored posts (contract/industry_ai.yaml says
what each pattern fired on): the real contract must make of it what is asserted here. A
contract change that breaks one brings back a misfire someone has already read.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from collect.industry_ai import config as iai_config
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import Item

NOW = datetime(2026, 11, 24, tzinfo=UTC)


@pytest.fixture(scope="module")
def cfg():
    return iai_config.load()


def item(text, *, hints=("finance",), platform="reddit", days_old=3):
    iid = f"{platform}:{abs(hash((text, platform, hints))) % 10**8}"
    return Item(
        id=iid,
        platform=platform,
        external_id=iid.split(":", 1)[1],
        url=f"https://e.x/{iid}",
        title="",
        body=text,
        created_at=NOW - timedelta(days=days_old),
        author_id="t2_a",
        lang=None,
        engagement={"score": 5},
        link=None,
        domain_hints=set(hints),
        query_keys={f"iai:{hints[0]}:{platform}:q"},
    )


def one(cfg, it):
    since = NOW - timedelta(days=int(cfg.run["window_days"]))
    results, _ = evaluate([it], cfg, since=since, now=NOW)
    return results[it.id]


# ── the window ───────────────────────────────────────────────────────────────


def test_a_post_older_than_the_window_is_out_and_a_recent_one_is_kept(cfg):
    assert cfg.run["window_days"] == 90
    text = "Our accounting team uses ChatGPT to draft month-end close notes for the CFO."
    assert one(cfg, item(text, days_old=120)).reason == "outside_window"
    assert one(cfg, item(text, days_old=60)).verdict == "kept"


# ── domain terms ─────────────────────────────────────────────────────────────


def test_bare_reverse_engineering_is_not_security_work(cfg):
    r = one(cfg, item("Reverse engineering an old game with AI so it runs in a browser.",
                      hints=("security_it",)))
    assert r.reason == "no_domain_term"
    ok = one(cfg, item("I used Claude for malware reverse engineering on a ransomware sample.",
                       hints=("security_it",)))
    assert ok.verdict == "kept" and ok.domains == ["security_it"]


def test_audit_counts_for_finance_only_near_a_finance_word(cfg):
    security = one(cfg, item("Our AI agents passed the security audit after a long review."))
    assert security.reason == "no_domain_term"
    books = one(cfg, item("I used ChatGPT to prepare for the audit of our books and tax filings."))
    assert books.verdict == "kept" and books.domains == ["finance"]


# ── filters ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("text", [
    "Analysts say a state-sponsored group used AI to fake the accounting records.",
    "I tested this AI accounting app myself, not sponsored.",
    "FactSet launches an AI-native banking solution in partnership with a startup.",
    "Show HN: an AI bookkeeping game, try it at https://example.com/?ref=hn",
])
def test_ordinary_posts_are_not_promo(cfg, text):
    assert one(cfg, item(text)).reason != "promo"


@pytest.mark.parametrize("text", [
    "AI bookkeeping for small firms: try our new accounting tool today #ad",
    "This webcast on AI in banking is produced in partnership with a vendor.",
    "AI accounting tool: https://example.com/signup?aff=g454021",
])
def test_a_promo_is_dropped(cfg, text):
    assert one(cfg, item(text)).reason == "promo"


def test_a_promo_code_is_an_ad_and_code_talk_is_not(cfg):
    ad = one(cfg, item("Black Friday: our AI bookkeeping app, use code BLACKFRIDAY30 at checkout."))
    assert ad.reason == "signup_ad"
    dev = one(cfg, item("Claude writes our accounting scripts, and we use the code review step "
                        "to question every change."))
    assert dev.reason != "signup_ad"


def test_register_now_is_an_ad_only_as_a_call(cfg):
    assert one(cfg, item("Register now: free AI webinar for accountants, limited seats.")
               ).reason == "signup_ad"
    assert one(cfg, item("Our vendor register now separates ledger rows for the AI "
                         "accounting import.")).reason != "signup_ad"


def test_a_job_seeker_is_not_a_hiring_post(cfg):
    r = one(cfg, item("ChatGPT helped me rewrite my cover letter for a job posting at a bank.",
                      hints=("personal",)))
    assert r.reason != "hiring"


def test_a_giveaway_mention_is_not_spam_but_a_giveaway_call_is(cfg):
    assert one(cfg, item("Weekly AI news for e-commerce payments, plus marketplace giveaway "
                         "notices.")).reason != "spam"
    assert one(cfg, item("Enter the giveaway: win our AI invoicing tool!")).reason == "spam"


# ── content type and stage ───────────────────────────────────────────────────


def test_a_use_case_names_an_ai_tool(cfg):
    journal = one(cfg, item("Any note-taking apps without AI? I use it for my diary and "
                            "shopping lists.", hints=("personal",)))
    assert journal.content_type != "use_case"
    used = one(cfg, item("I used Claude to sort our bookkeeping into tax categories."))
    assert used.content_type == "use_case" and used.stage_guess == "first_hand"


def test_four_words_fit_between_the_verb_and_to_or_for(cfg):
    r = one(cfg, item("I used Claude Code each morning for our bookkeeping checks."))
    assert r.content_type == "use_case"


def test_production_code_is_not_a_deployment(cfg):
    r = one(cfg, item("The vendor says its AI moves accounting mockups into production code "
                      "overnight."))
    assert r.content_type != "use_case"
    ok = one(cfg, item("Our bank put an AI fraud detection model into production this year."))
    assert ok.content_type == "use_case" and ok.stage_guess == "deployed"


def test_the_ai_group_reads_every_match_not_only_the_first(cfg):
    r = one(cfg, item("I use it for budgets. Last month I used ChatGPT to tidy our bookkeeping "
                      "before tax season."))
    assert r.content_type == "use_case"
