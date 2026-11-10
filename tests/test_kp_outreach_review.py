"""Kite Pulse outreach review queue (kp_review.py). No database, no network.

The SQL itself runs against the outreach database only; here are the rules
that decide before any SQL: the reply-URL check per source, the input
refusals, and that the migration's vocabulary matches the code's.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OUTREACH = ROOT / "web" / "src" / "kitepulse" / "outreach"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

import kp_review  # noqa: E402
from kp_review import Refused, check_reply_url  # noqa: E402

GH = {"source": "github", "root_id": None,
      "url": "https://github.com/someone/tool/discussions/12"}
DISC = {"source": "discourse", "root_id": "177461",
        "url": "https://forum.cursor.com/t/account-stuck/177461"}
HN = {"source": "hackernews", "root_id": "50323088",
      "url": "https://news.ycombinator.com/item?id=50334110"}
DEV = {"source": "devto", "root_id": "4968806",
       "url": "https://dev.to/karmabox/tracking-cost-per-finished-job-4842"}


@pytest.mark.parametrize("th, url", [
    (GH, "https://github.com/someone/tool/discussions/12#discussioncomment-998877"),
    (DISC, "https://forum.cursor.com/t/account-stuck/177461/4"),
    (DISC, "https://forum.cursor.com/t/177461/2"),
    (HN, "https://news.ycombinator.com/item?id=50399999"),
    (DEV, "https://dev.to/aloshy/comment/2k3j4"),
])
def test_a_reply_link_of_the_right_shape_is_accepted(th, url):
    assert check_reply_url(th, f"  {url} ") == url


@pytest.mark.parametrize("th, url, says", [
    (GH, "github.com/someone/tool/discussions/12", "starting with https://"),
    (GH, "https://gitlab.com/someone/tool/discussions/12#discussioncomment-1", "this thread is on"),
    (GH, "https://github.com/someone/tool/discussions/12", "the thread's own link"),
    (GH, "https://github.com/someone/tool/discussions/13#discussioncomment-1",
     "#discussioncomment"),
    (GH, "https://github.com/someone/tool/discussions/12#issuecomment-1",
     "#discussioncomment"),
    (DISC, "https://forum.cursor.com/t/other-topic/1/3", "/177461/<post number>"),
    (DISC, "https://forum.cursor.com/t/account-stuck/177461/1", "/177461/<post number>"),
    (HN, "https://news.ycombinator.com/item?id=50334110", "the thread's own link"),
    (HN, "https://news.ycombinator.com/user?id=me", "item?id=<number>"),
    (DEV, "https://dev.to/karmabox/tracking-cost-per-finished-job-4842#comments", "comment/<id>"),
])
def test_a_wrong_reply_link_is_refused_saying_what_is_wrong(th, url, says):
    with pytest.raises(Refused, match=re.escape(says)):
        check_reply_url(th, url)


def test_every_source_has_a_url_rule_and_says_how_far_it_checks():
    for source in ("github", "discourse", "hackernews", "devto", "reddit"):
        assert kp_review.URL_CHECK[source]
    with pytest.raises(Refused, match="no rule"):
        check_reply_url({"source": "x", "root_id": None, "url": "https://x.com/a"},
                        "https://x.com/b")


RD = {"source": "reddit", "root_id": "1xse2po",
      "url": "https://www.reddit.com/r/ClaudeCode/comments/1xse2po/turning_off_idle_compaction/"}


@pytest.mark.parametrize("url", [
    "https://www.reddit.com/r/ClaudeCode/comments/1xse2po/comment/nq3k2ab/",
    "https://reddit.com/r/claudecode/comments/1xse2po/turning_off_idle_compaction/nq3k2ab",
])
def test_a_reddit_reply_link_on_the_same_post_is_accepted(url):
    assert check_reply_url(RD, url) == url


@pytest.mark.parametrize("url", [
    "https://www.reddit.com/r/ClaudeCode/s/AbCdEf123",            # share link: names no post
    "https://www.reddit.com/r/ClaudeCode/comments/1xother/comment/nq3k2ab/",
    "https://www.reddit.com/r/ClaudeAI/comments/1xse2po/comment/nq3k2ab/",
    "https://www.reddit.com/user/me/comments/1xse2po/comment/nq3k2ab/",
])
def test_a_reddit_reply_link_that_cannot_be_tied_to_the_post_is_refused(url):
    with pytest.raises(Refused, match=re.escape("comments/1xse2po/comment/<id>")):
        check_reply_url(RD, url)


# --- refusals that happen before any SQL --------------------------------------

def test_a_skip_needs_a_known_reason_and_other_needs_a_note():
    with pytest.raises(Refused, match="reason must be one of"):
        kp_review.skip(None, 1, "boring", None, None)
    with pytest.raises(Refused, match="say why"):
        kp_review.skip(None, 1, "other", "   ", None)
    with pytest.raises(Refused, match="limit is 500"):
        kp_review.skip(None, 1, "not_relevant", "x" * 501, None)


def test_mark_posted_needs_an_account():
    with pytest.raises(Refused, match="which account"):
        kp_review.mark_posted(None, 1, "https://x", " @ ", None)


def test_an_unknown_tab_is_refused():
    with pytest.raises(Refused, match="tab must be one of"):
        kp_review.listing(None, "approved")


def test_an_unknown_view_or_a_view_outside_to_review_is_refused():
    with pytest.raises(Refused, match="view must be one of"):
        kp_review.listing(None, "found", view="best")
    with pytest.raises(Refused, match="To review only"):
        kp_review.listing(None, "posted", view="sent")


# --- the migration and the code agree ----------------------------------------

def test_the_skip_reasons_in_the_database_are_the_codes():
    sql = (OUTREACH / "migrations" / "20261109T1200_kp_outreach_thread_review.sql").read_text(
        encoding="utf-8")
    in_sql = set(re.findall(r"'(\w+)'", sql.split("skip_reason_ck")[1].split(")")[0]))
    assert in_sql == set(kp_review.SKIP_REASONS)


def test_review_actions_never_touch_a_dropped_thread():
    assert "dropped" in kp_review.TABS
    src = (OUTREACH / "kp_review.py").read_text(encoding="utf-8")
    assert '_require(th, t.STATUS_FOUND)' in src and '_require(th, "skipped", "posted")' in src


# --- the backend's import of this folder --------------------------------------

def test_the_module_refuses_to_run_from_another_folder(tmp_path):
    kp_review.assert_loaded_from(OUTREACH)
    with pytest.raises(RuntimeError, match="not from"):
        kp_review.assert_loaded_from(tmp_path)


def test_the_backend_appends_the_folder_and_uses_outreachs_own_database():
    app = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
    block = app.split("def _kp_review():")[1].split("@app.get(\"/admin/outreach/threads\")")[0]
    assert "sys.path.append(str(_KP_OUTREACH))" in block and "sys.path.insert" not in block
    assert "kp_review.assert_loaded_from(_KP_OUTREACH)" in block
    assert "_conn()" not in block      # never MIB's pooled connection
    routes = re.findall(r'@app\.(get|post)\("(/admin/outreach/[^"]+)"\)', app)
    assert routes == [("get", "/admin/outreach/threads"),
                      ("post", "/admin/outreach/threads/{thread_id}/skip"),
                      ("post", "/admin/outreach/threads/{thread_id}/posted"),
                      ("post", "/admin/outreach/threads/{thread_id}/reopen"),
                      ("post", "/admin/outreach/threads/{thread_id}/check")]
