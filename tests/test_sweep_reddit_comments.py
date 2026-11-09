"""The listing sweep stores each survivor's comments, not only its post.

Until 2026-10-05 `collect/ops/sweep_reddit.py` wrote posts and nothing under
them, so every thread it produced assembled as `post_body_only`: 17 of the 1,507
roots it wrote on staging had any comment document. These tests pin the four
outcomes of the comment fetch apart, because one of them - a FAILED fetch - is
an absence we caused and must not read like a thread nobody answered.

No database: the harvester, the writer and the ledger are fakes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from collect.adapters.reddit import ThreadFetch
from collect.ops import sweep_reddit as mod


@dataclass
class Post:
    external_id: str
    sieve_text: str = "a post about a model"
    raw: dict = field(default_factory=dict)
    subreddit: str = ""


@dataclass
class Comment:
    external_id: str
    raw: dict = field(default_factory=dict)


@dataclass
class Run:
    posts: list
    query: str = "r/ClaudeAI"
    survivors: list = field(default_factory=list)
    verdicts: list = field(default_factory=list)
    pages_fetched: int = 1
    http_errors: int = 0
    rate_limited: int = 0
    quota_exhausted: bool = False
    quota_remaining: int | None = None
    quota_limit: int | None = None
    exhausted: bool = True
    truncated_by: str | None = None
    #: As `RedditRun` carries it since the over_18 skip (#602 item 9).
    adult_skipped: int = 0

    def harvest_run_fields(self) -> dict:
        return {}


class Stored:
    def __init__(self, n: int) -> None:
        self.ref = f"raw/{n}"
        self.content_hash = f"h{n}"


class Store:
    def __init__(self) -> None:
        self.puts: list[bytes] = []

    def put(self, data: bytes, namespace=None) -> Stored:
        self.puts.append(data)
        return Stored(len(self.puts))


def _fetch(**kw) -> ThreadFetch:
    return ThreadFetch(thread_url="u", started_at=datetime.now(UTC), **kw)


class Harvester:
    def __init__(self, posts, fetches) -> None:
        self._store = Store()
        self._posts = posts
        self._fetches = fetches
        self.asked: list[str] = []

    def list_subreddit(self, name, *, pages, sort):
        return Run(posts=list(self._posts))

    def fetch_comments(self, post):
        self.asked.append(post.external_id)
        return self._fetches[post.external_id]


class Conn:
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class Contract:
    sweep_subreddits = {
        "members": ["ClaudeAI"],
        "pages_per_subreddit": 1,
        "posts_per_page": 25,
        "sort": "new",
    }


@dataclass
class Verdict:
    passed: bool = True
    topic: bool = False
    signal: bool = False


@pytest.fixture
def writes(monkeypatch):
    calls: list[dict] = []

    def write_documents(conn, items, *, retrieval_provenance, harvest_run_id, refs):
        calls.append({"items": list(items), "run": harvest_run_id, "refs": dict(refs)})
        return {"documents_inserted": len(items)}

    class Opened:
        id = 77

    import importlib

    # The package re-exports the FUNCTION `sieve`, shadowing the submodule on
    # attribute access, so the module is fetched by name.
    sieve_mod = importlib.import_module("collect.adapters.queries.sieve")
    import collect.adapters.reddit_write as writer_mod
    import collect.ops.ledger as ledger_mod

    monkeypatch.setattr(writer_mod, "write_documents", write_documents)
    monkeypatch.setattr(ledger_mod, "open_harvest_run", lambda conn, fields: Opened())
    monkeypatch.setattr(ledger_mod, "close_harvest_run", lambda *a, **k: None)
    monkeypatch.setattr(sieve_mod, "sieve", lambda terms, text: Verdict())
    monkeypatch.setattr(mod, "_seated_term_sets", lambda conn: {"m": ((), (object(),))})
    monkeypatch.setattr(mod, "sweep_budget", lambda cadence: (900, 35))
    return calls


def test_every_survivor_gets_a_comment_fetch_and_its_comments_are_written(writes):
    posts = [Post("t3_a"), Post("t3_b"), Post("t3_c"), Post("t3_d")]
    harvester = Harvester(posts, {
        "t3_a": _fetch(comments=(Comment("t1_x"), Comment("t1_y"))),
        "t3_b": _fetch(),                       # the platform says: no comments
        "t3_c": _fetch(http_errors=1),          # we failed to ask
        "t3_d": _fetch(not_a_thread=True),      # a link post, no thread
    })

    report = mod.sweep_reddit(Conn(), harvester, contract=Contract())

    assert harvester.asked == ["t3_a", "t3_b", "t3_c", "t3_d"]
    # First write: the posts. Second: one thread, post first, carrying the run id.
    assert [p.external_id for p in writes[0]["items"]] == ["t3_a", "t3_b", "t3_c", "t3_d"]
    assert len(writes) == 2
    thread = writes[1]
    assert [i.external_id for i in thread["items"]] == ["t3_a", "t1_x", "t1_y"]
    assert thread["run"] == 77
    assert set(thread["refs"]) == {"t3_a", "t1_x", "t1_y"}

    assert report.comment_requests == 3          # the link post costs no request
    assert report.threads_with_comments == 1
    assert report.threads_without_comments == 1
    assert report.threads_not_a_thread == 1
    assert report.comment_fetch_failures == ["t3_c"]
    assert report.http_errors == 1


def test_a_failed_fetch_is_named_in_the_summary(writes):
    harvester = Harvester([Post("t3_c")], {"t3_c": _fetch(http_errors=1)})
    report = mod.sweep_reddit(Conn(), harvester, contract=Contract())
    text = report.summary()
    assert "1 FAILED fetch(es)" in text
    assert "t3_c" in text


def test_comment_payloads_are_stored_as_the_platform_sent_them(writes):
    harvester = Harvester(
        [Post("t3_a", raw={"title": "p"})],
        {"t3_a": _fetch(comments=(Comment("t1_x", raw={"body": "café"}),))},
    )
    mod.sweep_reddit(Conn(), harvester, contract=Contract())
    # post payload, then the comment's - house spelling, non-ASCII kept.
    assert harvester._store.puts[-1] == '{"body": "café"}'.encode()


class TestTheReviewOf503:
    """Three gaps found in review: a 429 read as "no comments", one exception
    ending the sweep, and the listing's older quota reading overwriting the
    comment loop's newer one."""

    def test_a_rate_limited_fetch_is_a_failure_not_an_absence(self, writes):
        harvester = Harvester([Post("t3_r")], {"t3_r": _fetch(rate_limited=1)})
        report = mod.sweep_reddit(Conn(), harvester, contract=Contract())
        assert report.comment_fetch_failures == ["t3_r"]
        assert report.threads_without_comments == 0

    def test_one_failing_post_does_not_end_the_sweep(self, writes):
        class Boom(Harvester):
            def fetch_comments(self, post):
                if post.external_id == "t3_bad":
                    raise ValueError("malformed response")
                return super().fetch_comments(post)

        harvester = Boom([Post("t3_bad"), Post("t3_ok")],
                         {"t3_ok": _fetch(comments=(Comment("t1_z"),))})
        report = mod.sweep_reddit(Conn(), harvester, contract=Contract())
        assert report.comment_fetch_failures == ["t3_bad"]
        assert report.threads_with_comments == 1

    def test_the_lower_quota_reading_wins(self, writes, monkeypatch):
        harvester = Harvester([Post("t3_q")],
                              {"t3_q": _fetch(comments=(Comment("t1_q"),), quota_remaining=900)})
        original = harvester.list_subreddit

        def listing(name, *, pages, sort):
            run = original(name, pages=pages, sort=sort)
            run.quota_remaining = 950          # read BEFORE the comment request
            return run

        monkeypatch.setattr(harvester, "list_subreddit", listing)
        report = mod.sweep_reddit(Conn(), harvester, contract=Contract())
        assert report.quota_remaining == 900



class _NoRows:
    def fetchall(self):
        return []


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class MediaConn(Conn):
    """Answers the media sweep's three reads: the model names the registry and
    the catalogue know, and earlier deferrals (none here)."""

    def execute(self, sql, params=()):
        if "FROM model_version" in sql:
            return _Rows([("Kwaivgi: Kling 3.0",)])
        if "FROM model_catalog" in sql:
            return _Rows([("Google: Veo 3.1",)])
        assert "engagement->>'comments'" in sql
        return _NoRows()


class MediaContract:
    sweep_media_subreddits = {
        "members": ["aivideo"],
        "pages_per_subreddit": 1,
        "posts_per_page": 25,
        "sort": "new",
        "max_requests": 2,
        "subject_only": True,
    }


def test_media_cap_counts_comments_and_defers_what_it_stops(writes):
    """#602: one page + one comment request reaches the cap of 2, so the other
    two survivors' comments are DEFERRED - counted, and their posts stored -
    rather than fetched over budget or silently dropped."""
    posts = [Post("t3_a", "made this with Kling-3.0"), Post("t3_b", "Veo 3.1 test clip"),
             Post("t3_c", "Kling 3.0 again"), Post("t3_d", "weekend render, no model named")]
    harvester = Harvester(posts, {p.external_id: _fetch(comments=(Comment("t1_" + p.external_id),))
                                  for p in posts})
    report = mod.sweep_reddit(MediaConn(), harvester, contract=MediaContract,
                              block_key="sweep_media_subreddits")
    assert report.cap == 2 and report.comments_counted_in_cap
    assert harvester.asked == ["t3_a"]
    assert report.comments_deferred == 2
    # Anooj's A on #602: EVERY post is stored; comments only for the three that
    # name a model the registry or the catalogue knows (Veo 3.1 is catalogue-only).
    assert report.kept == 4
    assert report.posts_stored_without_comments == 1
    assert "2 deferred to the next run" in report.summary()
    assert "1 stored without comments" in report.summary()


def test_text_block_is_unchanged_by_the_media_options(writes):
    posts = [Post("t3_a"), Post("t3_b")]
    harvester = Harvester(posts, {p.external_id: _fetch(comments=(Comment("t1_x"),))
                                  for p in posts})
    report = mod.sweep_reddit(Conn(), harvester, contract=Contract)
    assert not report.comments_counted_in_cap and report.comments_deferred == 0
    assert harvester.asked == ["t3_a", "t3_b"]


class SearchHarvester(Harvester):
    """Records each search the media search sweep makes (2026-11-09)."""

    def __init__(self, posts, fetches) -> None:
        super().__init__(posts, fetches)
        self.searched: list[tuple] = []

    def search(self, query, *, sort, pages):
        self.searched.append((query, sort, pages))
        return Run(posts=list(self._posts), query=query)

    def list_subreddit(self, name, *, pages, sort):
        raise AssertionError("a search block must not list subreddits")


class SearchContract:
    sweep_subreddits = {"search_excluded": [{"id": "AIcrack", "reason": "cracked software"}]}
    sweep_media_subreddits = {
        "queries": [{"query": "kling", "kind": "video"}, {"query": "veo", "kind": "video"}],
        "pages_per_query": 1,
        "posts_per_page": 25,
        "sort": "NEW",
        "max_requests": 10,
        "subject_only": True,
    }


def test_the_media_sweep_searches_each_query_and_skips_excluded_subreddits(writes):
    """THE MEDIA SWEEP SEARCHES (2026-11-09): one newest-first search per query,
    in place of a subreddit listing that returned titles only. A hit in a
    subreddit the per-model search excludes is skipped and counted, never stored."""
    posts = [Post("t3_a", "Kling 3.0 test", subreddit="KlingAI_Videos"),
             Post("t3_b", "Veo 3.1 cracked", subreddit="AIcrack")]
    harvester = SearchHarvester(posts, {"t3_a": _fetch(comments=(Comment("t1_a"),))})
    report = mod.sweep_reddit(MediaConn(), harvester, contract=SearchContract,
                              block_key="sweep_media_subreddits")
    assert harvester.searched == [("kling", "NEW", 1), ("veo", "NEW", 1)]
    assert report.unit == "query" and report.search_excluded_skipped == 2
    assert "t3_b" not in harvester.asked
    assert "2 query(s) searched" in report.summary()


class ReadConn(MediaConn):
    """t3_a's comments are already stored (2 of them, 2 seen when stored)."""

    def execute(self, sql, params=()):
        if "FROM document d WHERE d.id" in sql:
            return _One((2, 2) if params[0] == "reddit:t3_a" else None)
        return super().execute(sql, params)


class _One:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


def test_a_thread_already_read_is_not_read_again(writes):
    """A weekly brand search returns posts an earlier run already read; run 2 of
    2026-11-09 re-read 29 such threads for nothing. Its count has not grown, so
    no request is spent; a post seen for the first time is still read."""
    posts = [Post("t3_a", "Kling 3.0 again", subreddit="KlingAI_Videos"),
             Post("t3_b", "Kling 3.0 new one", subreddit="KlingAI_Videos")]
    for p, n in zip(posts, (2, 5), strict=True):
        p.num_comments = n
    harvester = SearchHarvester(posts, {"t3_b": _fetch(comments=(Comment("t1_b"),))})
    report = mod.sweep_reddit(ReadConn(), harvester, contract=SearchContract,
                              block_key="sweep_media_subreddits")
    assert "t3_a" not in harvester.asked and "t3_b" in harvester.asked
    assert report.comments_already_stored == 2  # t3_a, once per query
    assert "already stored and had not grown" in report.summary()


def test_a_search_offers_what_it_returned():
    """A search page holds 22 posts, not the 25 a listing holds: the denominator
    is what came back, never pages x an assumed page size."""
    report = mod.RedditSweepReport(unit="query", population_per_subreddit=25,
                                   pages_per_subreddit=1)
    report.subreddits = [mod.SubredditSweep(name="kling"), mod.SubredditSweep(name="veo")]
    report.candidates = 44
    assert report.offered == 44


class _DeferStore(Store):
    """Payloads for the deferral candidates, by ref."""

    def __init__(self, payloads):
        super().__init__()
        self._payloads = payloads

    def get_text(self, ref):
        return self._payloads[ref]


class _DeferConn(MediaConn):
    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=()):
        if "engagement->>'comments'" in sql:
            assert "LIMIT" not in sql, "a LIMIT lets deliberate rows starve real deferrals"
            return _Rows(self._rows)
        return super().execute(sql, params)


def _payload(post_id, title):
    import json
    return json.dumps({"kind": "t3", "data": {"name": post_id, "title": title, "selftext": "",
                       "permalink": f"/r/x/comments/{post_id[3:]}/p/", "subreddit": "x",
                       "num_comments": 3}})


def _defer_report(cap):
    report = mod.RedditSweepReport(cap=cap)
    report.comments_counted_in_cap = True
    return report


def test_a_real_deferral_is_reached_behind_many_posts_stored_on_purpose(writes):
    """#612 review, point 4: 60 posts stored without comments on purpose sit in
    front of the one real deferral. With the old LIMIT the deferral was never
    reached; now the deliberate ones are passed over before the cap is asked."""
    rows = [(f"reddit:t3_u{i}", f"ref{i}") for i in range(60)] + [("reddit:t3_named", "refN")]
    payloads = {f"ref{i}": _payload(f"t3_u{i}", "my cat") for i in range(60)}
    payloads["refN"] = _payload("t3_named", "Kling 3.0 test")
    store = _DeferStore(payloads)
    harvester = Harvester([], {"t3_named": _fetch(comments=(Comment("t1_n"),))})
    report = _defer_report(cap=5)
    mod._take_deferred(_DeferConn(rows), harvester, store, ["kling"], report, lambda: 0,
                       fallback="x", known_names=("Kling 3.0",), by_query=True)
    assert harvester.asked == ["t3_named"]
    assert report.deferred_taken == 1 and report.comments_deferred == 0


def test_a_failed_deferred_read_is_counted_and_the_next_one_still_runs(writes):
    """Point 5: a read that raises is that post's failure, rolled back and named,
    and the sweep carries on to the next deferral."""
    rows = [("reddit:t3_a", "refA"), ("reddit:t3_b", "refB")]
    store = _DeferStore({"refA": _payload("t3_a", "Kling 3.0 one"),
                         "refB": _payload("t3_b", "Kling 3.0 two")})

    class Flaky(Harvester):
        def fetch_comments(self, post):
            self.asked.append(post.external_id)
            if post.external_id == "t3_a":
                raise RuntimeError("connection reset")
            return self._fetches[post.external_id]

    harvester = Flaky([], {"t3_b": _fetch(comments=(Comment("t1_b"),))})
    report = _defer_report(cap=5)
    mod._take_deferred(_DeferConn(rows), harvester, store, ["kling"], report, lambda: 0,
                       fallback="x", known_names=("Kling 3.0",), by_query=True)
    assert harvester.asked == ["t3_a", "t3_b"]
    assert "t3_a" in report.comment_fetch_failures and report.deferred_taken == 1


@pytest.mark.parametrize(("stored", "seen_then", "now", "skip"), [
    (2, 2, 2, True),    # nothing new since the first read
    (2, 2, 5, False),   # it grew: read it
    (5, 2, 5, True),    # grew once, the re-read stored all 5: not read again (point 6)
    (0, 2, 2, False),   # never read: read it
])
def test_a_thread_is_re_read_only_when_it_holds_more_than_we_do(stored, seen_then, now, skip):
    class C:
        def execute(self, sql, params=()):
            return _One((stored, seen_then) if stored else None)

    from types import SimpleNamespace

    post = SimpleNamespace(external_id="t3_x", num_comments=now)
    assert mod._comments_already_read(C(), post) is skip


def test_the_media_block_refuses_to_borrow_a_cap(writes):
    """#612 review, point 9: without `max_requests` the media sweep silently ran
    on harvest.yaml's 900-request GitHub budget."""
    class NoCap:
        sweep_media_subreddits = {k: v for k, v in SearchContract.sweep_media_subreddits.items()
                                  if k != "max_requests"}

    with pytest.raises(RuntimeError, match="max_requests"):
        mod.sweep_reddit(MediaConn(), SearchHarvester([], {}), contract=NoCap,
                         block_key="sweep_media_subreddits")
