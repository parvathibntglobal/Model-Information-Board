"""`scripts/backfill_x_created_at.py` reads the TWEET's date from a stored payload.

An X payload carries two `created_at` values: the tweet's (`legacy.created_at`)
and its author's account date (`core.user_results.result.legacy.created_at`).
Dating a document from the second would put a 2026 post in 2023. No database.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "scripts" / "backfill_x_created_at.py"
_spec = importlib.util.spec_from_file_location("backfill_x_created_at", _PATH)
backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backfill)

TWEET = "Sat May 16 07:41:54 +0000 2026"
ACCOUNT = "Thu Nov 30 09:40:46 +0000 2023"


def _payload(**extra):
    return {
        "__typename": "Tweet",
        "rest_id": "1",
        "core": {"user_results": {"result": {"legacy": {"created_at": ACCOUNT}}}},
        "legacy": {"created_at": TWEET, "full_text": "x"},
        **extra,
    }


def test_the_tweet_date_not_the_account_date():
    assert backfill.tweet_date(_payload()) == TWEET


def test_a_visibility_wrapper_is_unwrapped_once():
    assert backfill.tweet_date({"__typename": "TweetWithVisibilityResults",
                                "tweet": _payload()}) == TWEET


def test_no_tweet_date_is_none_never_the_account_date():
    p = _payload()
    del p["legacy"]
    assert backfill.tweet_date(p) is None
    assert backfill.tweet_date("not a payload") is None
