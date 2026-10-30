"""Guides phase A (2026-10-30): official cookbooks, SDK releases, the OpenAI spec
and PyVideo's talk index, read through the GitHub REST API.

The contract, glob, notebook, title and PyVideo tests need no database; the
harvest tests need Postgres (the `test_dsn` fixture). GitHub is faked with
httpx.MockTransport - no test reaches the network.
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, date, datetime

import httpx
import psycopg
import pytest

from collect.http import build_client
from collect.ids import content_hash
from collect.official import harvest as official
from collect.official import parse as op
from collect.rawstore import RAW, build_ref

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
UA = "modelboard/0.1 (+https://modelboard.invalid/about)"
API = "https://api.github.example"

CONTRACT_YAML = f"""
version: 1
api: {API}
politeness: {{min_interval_seconds: 0, max_blob_fetches_per_run: 100,
              stop_below_remaining: 10, max_release_pages: 3, max_blob_bytes: 100000}}
repos:
  - {{key: cook, repo: o/cook, branch: main, provider: openai, kind: cookbook, licence: MIT,
     include: ["**/*.ipynb", "**/*.md"], exclude: [".github/**", "**/LICENSE*"]}}
  - {{key: sdk, repo: o/sdk, branch: main, provider: anthropic, kind: sdk,
     licence: Apache-2.0, include: [CHANGELOG.md], exclude: []}}
pyvideo:
  key: pyvideo
  repo: pv/data
  branch: main
  licence: CC0-1.0
  talk_glob: "*/videos/*.json"
  min_event_year: 2023
  no_publish_path: NO_PUBLISH.json
  video_hosts: {{youtube: [youtube.com, youtu.be], vimeo: [vimeo.com]}}
  llm_terms: [llm, "language model", claude, rag]
"""


@pytest.fixture
def contract(tmp_path):
    p = tmp_path / "official_sources.yaml"
    p.write_text(CONTRACT_YAML, encoding="utf-8")
    return op.load_contract(p)


def _nb(cells, language="python"):
    return json.dumps({"metadata": {"kernelspec": {"language": language}} if language else {},
                       "nbformat": 4, "cells": cells}).encode()


NOTEBOOK = _nb([
    {"cell_type": "markdown", "source": ["##### Copyright 2026\n"]},
    {"cell_type": "markdown", "source": ["# Prompt caching\n", "\n", "Why it matters."]},
    {"cell_type": "code", "source": ["print('hi')"], "outputs": [{"text": "hi"}]},
    {"cell_type": "raw", "source": "%%nbconvert"},
    {"cell_type": "code", "source": [], "outputs": []},
])


# ── the contract ─────────────────────────────────────────────────────────────

def test_the_real_contract_loads_with_every_repository_and_pyvideo():
    c = op.load_contract()
    by_key = {r.key: r for r in c.repos}
    assert {r.kind for r in c.repos} == {"cookbook", "sdk", "spec"}
    assert by_key["openai_cookbook"].licence == "MIT"
    assert by_key["gemini_cookbook"].licence == "Apache-2.0"
    assert by_key["openai_openapi"].include == ("openapi.yaml",)
    assert c.pyvideo.repo == "pyvideo/data" and c.pyvideo.min_event_year == 2023
    assert c.api == "https://api.github.com"


@pytest.mark.parametrize("cut, says", [
    ("  min_event_year: 2023\n", "min_event_year"),
    ("max_blob_fetches_per_run: 100,", "max_blob_fetches_per_run"),
    ("licence: Apache-2.0, ", "licence is required"),
    ("  no_publish_path: NO_PUBLISH.json\n", "no_publish_path"),
    ("  llm_terms: [llm, \"language model\", claude, rag]\n", "llm_terms"),
])
def test_a_missing_value_is_refused_not_defaulted(tmp_path, cut, says):
    assert cut in CONTRACT_YAML
    p = tmp_path / "c.yaml"
    p.write_text(CONTRACT_YAML.replace(cut, "", 1), encoding="utf-8")
    with pytest.raises(op.OfficialContractError, match=says):
        op.load_contract(p)


def test_a_wrong_kind_and_an_other_host_label_are_refused(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(CONTRACT_YAML.replace("kind: cookbook", "kind: blog")
                 .replace("vimeo: [vimeo.com]", "other: [x.com]"), encoding="utf-8")
    with pytest.raises(op.OfficialContractError) as err:
        op.load_contract(p)
    assert "kind must be one of" in str(err.value) and "must not name `other`" in str(err.value)


# ── globs ────────────────────────────────────────────────────────────────────

def test_include_and_exclude_globs():
    inc, exc = ("**/*.ipynb", "**/*.md"), (".github/**", "**/LICENSE*", "**/data/**")
    assert op.selected("README.md", inc, exc)                       # **/ is also no folder
    assert op.selected("examples/rag/Intro.ipynb", inc, exc)
    assert not op.selected("examples/rag/chart.png", inc, exc)
    assert not op.selected(".github/ISSUE_TEMPLATE/bug.md", inc, exc)
    assert not op.selected("LICENSE.md", inc, exc) and not op.selected("sub/LICENSE.md", inc, exc)
    assert not op.selected("examples/data/notes.md", inc, exc)
    # `*` stays inside one folder.
    assert op.selected("CHANGELOG.md", ("CHANGELOG.md",), ())
    assert not op.selected("docs/CHANGELOG.md", ("CHANGELOG.md",), ())
    talk = op.glob_regex("*/videos/*.json")
    assert talk.match("pycon-us-2024/videos/a-talk.json")
    assert not talk.match("pycon-us-2024/category.json")
    assert not talk.match("a/b/videos/x.json")


# ── notebooks and titles ─────────────────────────────────────────────────────

def test_a_notebook_is_flattened_to_markdown_and_fenced_code_without_outputs():
    nb = op.flatten_notebook(NOTEBOOK)
    assert nb.text == ("##### Copyright 2026\n\n# Prompt caching\n\nWhy it matters.\n\n"
                       "```python\nprint('hi')\n```\n")
    assert "hi\"" not in nb.text and "nbconvert" not in nb.text   # outputs and raw cells dropped
    assert nb.h1 == "Prompt caching"                              # the first H1, not the H5


def test_a_notebook_without_a_language_gets_no_assumed_one():
    nb = op.flatten_notebook(_nb([{"cell_type": "code", "source": "x = 1"}], language=None))
    assert nb.text == "```\nx = 1\n```\n" and nb.h1 is None


def test_bytes_that_are_not_a_notebook_raise():
    with pytest.raises(ValueError):
        op.flatten_notebook(b"not json")
    with pytest.raises(ValueError):
        op.flatten_notebook(b'{"no": "cells"}')


def test_the_title_is_the_first_h1_outside_code_or_the_file_name_and_says_which():
    md = "Intro text\n\n```bash\n# not a title\n```\n\n## Section\n\n# Real title #\n"
    assert op.first_h1(md) == "Real title"
    assert op.first_h1("Setext title\n============\n\nbody") == "Setext title"
    assert op.first_h1("## only a section\n") is None
    assert op.title_for("a/b/guide.md", "Real title") == ("Real title", "h1")
    assert op.title_for("a/b/guide.md", None) == ("guide.md", "file_name")


def test_a_blob_is_named_by_gits_own_sha():
    # `printf 'hello\n' | git hash-object --stdin`
    assert op.git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


# ── PyVideo ──────────────────────────────────────────────────────────────────

def test_the_event_year_comes_from_the_name_or_not_at_all():
    assert op.event_year("pycon-us-2024") == 2024
    assert op.event_year("pydata-2019-2023-reunion") == 2023
    assert op.event_year("chipy") is None
    assert op.event_year("pycon-12345") is None          # not a year inside a longer number


def test_the_video_host_is_derived_from_the_link(contract):
    hosts = contract.pyvideo.video_hosts
    assert op.video_host("https://www.youtube.com/watch?v=x", hosts) == "youtube"
    assert op.video_host("https://youtu.be/x", hosts) == "youtube"
    assert op.video_host("https://player.vimeo.com/video/1", hosts) == "vimeo"
    assert op.video_host("https://notyoutube.com/x", hosts) == "other"
    assert op.video_host("https://archive.org/details/x", hosts) == "other"


def test_no_publish_must_be_a_list_of_ids():
    assert op.no_publish_ids(b"[2845, 5984]") == {2845, 5984}
    for bad in (b"{}", b"[\"x\"]", b"nope", b"[true]"):
        with pytest.raises(ValueError):
            op.no_publish_ids(bad)


def test_a_talk_keeps_what_pyvideo_gives_and_nothing_more(contract):
    rec = {"title": "RAG with Claude", "description": "Fewer hallucinations. Not a llmx.",
           "recorded": "2024-05-17", "speakers": ["Ann"], "language": "eng",
           "videos": [{"type": "youtube", "url": "https://www.youtube.com/watch?v=a"},
                      {"type": "mp4", "url": "https://archive.org/a.mp4"}, {"type": "x"}],
           "thumbnail_url": "https://i.ytimg.com/vi/a/hq.jpg", "copyright_text": "CC BY"}
    talk = op.parse_talk(json.dumps(rec).encode(), "conf-2024/videos/a.json", contract.pyvideo)
    assert talk["event"] == "conf-2024" and talk["recorded"] == date(2024, 5, 17)
    assert talk["video_urls"] == ["https://www.youtube.com/watch?v=a", "https://archive.org/a.mp4"]
    assert talk["video_hosts"] == ["youtube", "other"]
    assert talk["llm_terms"] == ["claude", "rag"]                  # "llmx" is not "llm"
    assert talk["pyvideo_id"] is None and talk["duration_seconds"] is None   # not given: None
    with pytest.raises(ValueError, match="not a date"):
        op.parse_talk(json.dumps(rec | {"recorded": "spring"}).encode(), "c/videos/a.json",
                      contract.pyvideo)
    with pytest.raises(ValueError, match="no title"):
        op.parse_talk(b'{"title": " "}', "c/videos/a.json", contract.pyvideo)


# ── a fake GitHub ────────────────────────────────────────────────────────────

def _talk(title, description="", **extra):
    return json.dumps({"title": title, "description": description, "recorded": "2024-05-17",
                       "speakers": ["S"], "videos": [{"type": "youtube",
                                                      "url": "https://youtu.be/" + title[:3]}],
                       **extra}).encode()


class FakeGitHub:
    """Repositories as {path: bytes}; serves the record, the tree, blobs by sha
    and releases, and remembers every request."""

    def __init__(self):
        self.repos = {
            "o/cook": {"licence": "MIT", "files": {
                "nb/caching.ipynb": NOTEBOOK, "guide.md": b"# Guide\n\nText.\n",
                "untitled.md": b"No heading here.\n", ".github/pr.md": b"# Template\n",
                "LICENSE.md": b"# MIT\n", "img/plot.png": b"\x89PNG"}},
            "o/sdk": {"licence": "Apache-2.0", "files": {"CHANGELOG.md": b"# Changelog\n",
                                                         "src/x.py": b"x = 1\n"}},
            "pv/data": {"licence": "CC0-1.0", "files": {
                "NO_PUBLISH.json": b"[7]",
                "conf-2024/category.json": b'{"title": "Conf 2024"}',
                "conf-2024/videos/rag.json": _talk("RAG with an LLM", "Language model talk"),
                "conf-2024/videos/plain.json": _talk("Packaging Python", "Wheels."),
                "conf-2024/videos/hidden.json": _talk("Hidden talk", id=7),
                "conf-2019/videos/old.json": _talk("Old talk"),
                "meetup/videos/m.json": _talk("Meetup talk")}},
        }
        self.releases = {"o/sdk": [
            [{"tag_name": "v2", "name": "v2", "html_url": "https://gh.example/v2",
              "published_at": "2026-10-29T10:00:00Z", "body": "## Fixes\n* a"},
             {"tag_name": "v1", "name": "", "html_url": "https://gh.example/v1",
              "published_at": None, "body": None, "prerelease": True}],
            [{"tag_name": "v0", "name": "v0", "html_url": "https://gh.example/v0",
              "published_at": "2026-01-01T00:00:00Z", "body": "first"}]]}
        self.requests: list[httpx.Request] = []
        self.remaining = 4000
        self.throttle_from: int | None = None

    def blobs(self):
        return {op.git_blob_sha(b): b for r in self.repos.values() for b in r["files"].values()}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        headers = {"x-ratelimit-remaining": str(self.remaining)}
        if self.throttle_from is not None and len(self.requests) > self.throttle_from:
            return httpx.Response(403, headers={"x-ratelimit-remaining": "0"},
                                  content=b'{"message": "API rate limit exceeded"}')
        path = request.url.path
        for name, repo in self.repos.items():
            base = f"/repos/{name}"
            if path == base:
                return httpx.Response(200, headers=headers,
                                      json={"license": {"spdx_id": repo["licence"]}})
            if path == f"{base}/git/trees/main":
                tree = [{"path": p, "type": "blob", "sha": op.git_blob_sha(b), "size": len(b)}
                        for p, b in repo["files"].items()]
                tree.append({"path": "nb", "type": "tree", "sha": "t"})
                return httpx.Response(200, headers=headers, json={"tree": tree,
                                                                  "truncated": False})
            if path.startswith(f"{base}/git/blobs/"):
                data = self.blobs().get(path.rsplit("/", 1)[-1])
                return (httpx.Response(200, headers=headers, content=data) if data is not None
                        else httpx.Response(404, headers=headers))
            if path == f"{base}/releases":
                pages = self.releases.get(name, [[]])
                page = int(request.url.params.get("page", "1"))
                if page < len(pages):
                    headers["link"] = f'<{API}{path}?page={page + 1}>; rel="next"'
                return httpx.Response(200, headers=headers, json=pages[page - 1])
        raise AssertionError(f"unexpected request to {request.url}")

    def blob_paths(self):
        by_sha = {}
        for repo in self.repos.values():
            for p, b in repo["files"].items():
                by_sha[op.git_blob_sha(b)] = p
        return [by_sha.get(r.url.path.rsplit("/", 1)[-1], "?") for r in self.requests
                if "/git/blobs/" in r.url.path]


class _Store:
    def __init__(self):
        self.put_count = 0
        self.tombstoned: list[str] = []

    def put(self, data, *, namespace=RAW):
        self.put_count += 1
        data = data.encode() if isinstance(data, str) else data
        return type("P", (), {"ref": build_ref(content_hash(data), namespace)})()

    def tombstone(self, ref, *, reason, detail=None):
        assert reason == "takedown-request"
        self.tombstoned.append(ref)


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
        yield c


NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


def _run(conn, contract, gh, store=None, **kw):
    with build_client(user_agent=UA, transport=httpx.MockTransport(gh)) as client:
        return official.harvest(conn, client, terms=lambda: None, token="t0ken",
                                store=store or _Store(), contract=contract,
                                clock=lambda: NOW, **kw)


# ── the harvest (Postgres) ───────────────────────────────────────────────────

def test_a_first_run_stores_what_is_in_scope_and_counts_the_rest(conn, contract):
    gh = FakeGitHub()
    out = _run(conn, contract, gh)
    cook, sdk, pv = (out["by_source"][k] for k in ("cook", "sdk", "pyvideo"))
    assert (cook["outcome"], cook["files_listed"], cook["files_new"]) == ("ok", 3, 3)
    assert cook["releases_seen"] is None and cook["talks_withheld"] is None   # not 0: n/a
    docs = dict(conn.execute("SELECT path, title || ' | ' || title_source FROM official_doc "
                             "WHERE repo_key = 'cook'").fetchall())
    # .github/ and LICENSE are excluded, the png was never a candidate.
    assert docs == {"nb/caching.ipynb": "Prompt caching | h1", "guide.md": "Guide | h1",
                    "untitled.md": "untitled.md | file_name"}
    nb = conn.execute("SELECT format, text_ref LIKE 'flattened/%%', raw_ref LIKE 'raw/%%', "
                      "html_url FROM official_doc WHERE path = 'nb/caching.ipynb'").fetchone()
    assert nb == ("ipynb", True, True, "https://github.com/o/cook/blob/main/nb/caching.ipynb")
    md = conn.execute("SELECT text_ref = raw_ref FROM official_doc WHERE path = 'guide.md'"
                      ).fetchone()
    assert md == (True,)                                  # markdown is its own text
    assert conn.execute("SELECT doc_kind, title FROM official_doc WHERE repo_key = 'sdk'"
                        ).fetchall() == [("changelog", "Changelog")]
    # Releases across both pages; a missing date stays missing.
    assert (sdk["releases_seen"], sdk["releases_new"]) == (3, 3)
    v1 = conn.execute("SELECT name, published_at, prerelease, raw_ref LIKE 'raw/%%' "
                      "FROM official_release WHERE tag = 'v1'").fetchone()
    assert v1 == (None, None, True, True)
    # PyVideo: the year rule and NO_PUBLISH, each counted.
    assert (pv["outcome"], pv["files_listed"], pv["talks_no_year"],
            pv["talks_before_min_year"], pv["talks_withheld"]) == ("ok", 3, 1, 1, 1)
    talks = dict(conn.execute("SELECT path, llm_terms FROM video_ref").fetchall())
    assert set(talks) == {"conf-2024/videos/rag.json", "conf-2024/videos/plain.json"}
    assert talks["conf-2024/videos/rag.json"] == ["language model", "llm", "rag"]
    assert talks["conf-2024/videos/plain.json"] == []    # a weight, never a gate (rule 8)
    assert conn.execute("SELECT video_hosts, event_year FROM video_ref "
                        "WHERE path = 'conf-2024/videos/plain.json'").fetchone() == (["youtube"],
                                                                                     2024)
    reads = dict(conn.execute("SELECT source_key, outcome FROM official_fetch").fetchall())
    assert reads == {"cook": "ok", "sdk": "ok", "pyvideo": "ok"}


def test_every_request_is_the_api_with_the_token_and_an_identifying_agent(conn, contract):
    gh = FakeGitHub()
    _run(conn, contract, gh)
    assert gh.requests and all(r.url.host == "api.github.example" for r in gh.requests)
    assert all(r.headers["authorization"] == "Bearer t0ken" for r in gh.requests)
    assert all(r.headers["user-agent"] == UA for r in gh.requests)


def test_an_unchanged_sha_is_not_fetched_again_and_a_changed_one_is(conn, contract):
    gh = FakeGitHub()
    _run(conn, contract, gh)
    gh.requests.clear()
    again = _run(conn, contract, gh)
    # Only NO_PUBLISH.json (read every run) and the withheld talk (nothing stored
    # to compare with) are fetched again.
    assert sorted(gh.blob_paths()) == ["NO_PUBLISH.json", "conf-2024/videos/hidden.json"]
    assert again["by_source"]["cook"]["files_unchanged"] == 3
    assert again["by_source"]["cook"]["files_fetched"] == 0
    assert again["by_source"]["sdk"]["releases_new"] == 0
    assert again["by_source"]["sdk"]["releases_changed"] == 0

    gh.repos["o/cook"]["files"]["guide.md"] = b"# Guide, revised\n"
    gh.releases["o/sdk"][0][0]["body"] = "## Fixes\n* a\n* b"
    gh.requests.clear()
    third = _run(conn, contract, gh)
    assert "guide.md" in gh.blob_paths() and "untitled.md" not in gh.blob_paths()
    assert (third["by_source"]["cook"]["files_changed"],
            third["by_source"]["sdk"]["releases_changed"]) == (1, 1)
    row = conn.execute("SELECT title, changed_at > first_seen_at OR changed_at = first_seen_at "
                       "FROM official_doc WHERE path = 'guide.md'").fetchone()
    assert row[0] == "Guide, revised"
    assert conn.execute("SELECT count(*) FROM official_fetch").fetchone()[0] == 9


def test_a_file_gone_from_the_listing_is_marked_never_deleted(conn, contract):
    gh = FakeGitHub()
    _run(conn, contract, gh)
    del gh.repos["o/cook"]["files"]["untitled.md"]
    out = _run(conn, contract, gh)
    assert out["by_source"]["cook"]["files_unlisted"] == 1
    assert conn.execute("SELECT unlisted_at FROM official_doc WHERE path = 'untitled.md'"
                        ).fetchone() == (NOW,)
    gh.repos["o/cook"]["files"]["untitled.md"] = b"No heading here.\n"
    _run(conn, contract, gh)                                    # back, unchanged: listed again
    assert conn.execute("SELECT unlisted_at FROM official_doc WHERE path = 'untitled.md'"
                        ).fetchone() == (None,)


def test_a_talk_listed_after_it_was_stored_is_withdrawn_and_its_bytes_tombstoned(conn, contract):
    gh = FakeGitHub()
    gh.repos["pv/data"]["files"]["conf-2024/videos/plain.json"] = _talk("Packaging", id=99)
    _run(conn, contract, gh)
    assert conn.execute("SELECT pyvideo_id FROM video_ref WHERE pyvideo_id = 99").fetchone()
    gh.repos["pv/data"]["files"]["NO_PUBLISH.json"] = b"[7, 99]"
    store = _Store()
    out = _run(conn, contract, gh, store=store)
    assert out["by_source"]["pyvideo"]["talks_withdrawn"] == 1
    assert conn.execute("SELECT count(*) FROM video_ref WHERE pyvideo_id = 99").fetchone() == (0,)
    assert len(store.tombstoned) == 1


def test_without_no_publish_the_talks_are_not_read(conn, contract):
    gh = FakeGitHub()
    del gh.repos["pv/data"]["files"]["NO_PUBLISH.json"]
    out = _run(conn, contract, gh)
    pv = out["by_source"]["pyvideo"]
    assert pv["outcome"] == "error" and "NO_PUBLISH.json is not in the tree" in pv["detail"]
    assert conn.execute("SELECT count(*) FROM video_ref").fetchone() == (0,)
    assert not [p for p in gh.blob_paths() if "/videos/" in p]


def test_a_licence_github_no_longer_reports_stops_that_repository(conn, contract):
    gh = FakeGitHub()
    gh.repos["o/cook"]["licence"] = "NOASSERTION"
    out = _run(conn, contract, gh)
    cook = out["by_source"]["cook"]
    assert cook["outcome"] == "licence_mismatch" and "GitHub reports NOASSERTION" in cook["detail"]
    assert not any("/repos/o/cook/git/" in r.url.path for r in gh.requests)
    assert out["by_source"]["sdk"]["outcome"] == "ok"           # the others still read


def test_the_per_run_cap_defers_the_rest_and_says_so(conn, tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(CONTRACT_YAML.replace("max_blob_fetches_per_run: 100",
                                       "max_blob_fetches_per_run: 2"), encoding="utf-8")
    out = _run(conn, op.load_contract(p), FakeGitHub(), only={"cook"})
    cook = out["by_source"]["cook"]
    assert (cook["files_fetched"], cook["files_deferred"], cook["outcome"]) == (2, 1, "partial")
    assert "1 deferred to a later run" in cook["detail"]
    assert set(out["by_source"]) == {"cook"}


def test_a_throttle_stops_the_run_and_every_unread_source_is_recorded(conn, contract):
    gh = FakeGitHub()
    gh.throttle_from = 3       # the cookbook's record, tree and one blob; then 403
    out = _run(conn, contract, gh)
    assert out["stopped"] and "throttled" in out["stopped"]
    outcomes = dict(conn.execute("SELECT source_key, outcome FROM official_fetch").fetchall())
    assert outcomes == {"cook": "rate_limited", "sdk": "rate_limited", "pyvideo": "rate_limited"}
    cook = out["by_source"]["cook"]
    assert cook["files_fetched"] == 1 and cook["files_deferred"] == 2
    assert "not read: the run stopped earlier" in out["by_source"]["sdk"]["detail"]


def test_the_run_stops_before_the_budget_falls_below_the_floor(conn, contract):
    gh = FakeGitHub()
    gh.remaining = 5          # below stop_below_remaining (10) from the first answer
    out = _run(conn, contract, gh)
    assert len(gh.requests) == 1 and "below stop_below_remaining" in out["stopped"]
    assert out["rate_remaining"] == 5


def test_bytes_that_are_not_the_listed_blob_are_refused(conn, contract):
    gh = FakeGitHub()
    real = gh.__call__

    def tampered(request):
        response = real(request)
        if request.url.path.endswith(op.git_blob_sha(b"# Guide\n\nText.\n")):
            return httpx.Response(200, headers=response.headers, content=b"# Something else\n")
        return response
    with build_client(user_agent=UA, transport=httpx.MockTransport(tampered)) as client:
        out = official.harvest(conn, client, terms=lambda: None, token="t", store=_Store(),
                               contract=contract, only={"cook"}, clock=lambda: NOW)
    cook = out["by_source"]["cook"]
    assert (cook["files_failed"], cook["files_new"], cook["outcome"]) == (1, 2, "partial")
    assert "not that blob" in cook["detail"]
    assert conn.execute("SELECT count(*) FROM official_doc WHERE path = 'guide.md'"
                        ).fetchone() == (0,)


def test_a_dry_run_reads_everything_and_writes_nothing(conn, contract):
    gh = FakeGitHub()
    store = _Store()
    out = _run(conn, contract, gh, store=store, dry_run=True)
    assert out["dry_run"] and out["by_source"]["cook"]["files_new"] == 3
    assert out["by_source"]["pyvideo"]["talks_withheld"] == 1
    assert store.put_count == 0                                 # its own store, writing nothing
    for table in ("official_doc", "official_release", "video_ref", "official_fetch"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)  # noqa: S608


def test_no_token_and_a_refused_terms_check_both_stop_before_any_request(contract):
    gh = FakeGitHub()
    with build_client(user_agent=UA, transport=httpx.MockTransport(gh)) as client:
        with pytest.raises(official.OfficialHarvestError, match="GITHUB_TOKEN"):
            official.harvest(None, client, terms=lambda: None, token="", contract=contract,
                             dry_run=True)

        def refuse():
            raise RuntimeError("terms refused")
        with pytest.raises(RuntimeError, match="terms refused"):
            official.harvest(None, client, terms=refuse, token="t", contract=contract,
                             dry_run=True)
    assert gh.requests == []
