"""Guides phase B (2026-10-30): developer guides, tutorials and error fixes
written from the providers' official sources.

What is pinned here, without a database:
  - subjects come from seo/keyword_plan.yaml's lists, every one of them, and a
    phrase with no terms stops the run rather than matching on nothing;
  - a subject no official file mentions is passed over, and says so;
  - ranking is a WEIGHT (rule 8): every matching file is counted and scored, a
    cap keeps the best and records the scores of what it left out, and a
    low-scoring file within the cap is kept;
  - code is COPIED, never written: a snippet passes only when its code is in
    the fenced code of the official source it names (whitespace-normalised),
    fails when altered, when it names no source, or names an engineer report;
    a post may not reprint most of a source's code;
  - a talk is referenced only by an id from the pack;
  - the three new body blocks are built once (judge/guide_blocks.py), accepted
    by the stored-post check, and rendered by the real views.js;
  - the Guides hub classifies the formats (web/src/blogs/guideKinds.js).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

import generate_sample_blogs as g
from judge import blog_posts
from judge import guide_blocks as gb

ROOT = Path(__file__).resolve().parents[1]
CFG = g.guides_cfg()
LISTS = g.planner_lists()

STREAM_CODE = """from openai import OpenAI
client = OpenAI()
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say hello"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")"""

OFFICIAL_1 = f"""# How to stream completions

Set `stream=True` to receive the reply as it is generated.

```python
{STREAM_CODE}
```

The rest of this notebook measures the time to the first token.

```python
import time
start_time = time.time()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{{"role": "user", "content": "Count to 100"}}],
)
print(f"Full response received {{time.time() - start_time:.2f}} seconds after request")
collected_messages = []
for chunk in response:
    collected_messages.append(chunk)
```
"""
OFFICIAL_2 = """# Rate limits

```python
from tenacity import retry, stop_after_attempt, wait_random_exponential

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs):
    return client.chat.completions.create(**kwargs)
```
"""
REPORT = (
    "I set stream=True and the first chunk took four seconds. Then I printed every chunk."
    "\n\n```python\nprint('mine')\n```"
)


def _rules(snippets=(1, 4), videos=("V1",)):
    return {
        "guide": {"official": [1, 2], "videos": list(videos), "max_source_code_share": 0.5},
        "snippets": snippets,
    }


def _essay(snippets, prose="Stream with `stream=True` as the notebook shows [1].", videos=()):
    return {
        "title": "t",
        "sections": [{"heading": "Stream the reply", "paragraphs": [prose], "snippets": snippets}],
        "videos": list(videos),
    }


def _snip(code, source=1, language="python", label="Stream the reply"):
    return {"label": label, "variants": [{"language": language, "code": code, "source": source}]}


TEXTS = [OFFICIAL_1, OFFICIAL_2, REPORT]


# ── subjects ─────────────────────────────────────────────────────────────────


def test_every_planner_task_and_error_is_a_subject_for_every_provider():
    providers = g.guide_providers(CFG, LISTS)
    assert providers == [
        p for p in LISTS["vendor"] if p in {"openai", "anthropic", "google", "mistral"}
    ]
    dev = g.guide_subjects("developer-guide", CFG, LISTS)
    assert {s["key"] for s in dev} == {
        f"{p}/{g.guide_slug(t)}" for p in providers for t in LISTS["devtask"]
    }
    assert len(dev) == len(providers) * len(LISTS["devtask"])
    err = g.guide_subjects("error-fix", CFG, LISTS)
    assert {s["phrase"] for s in err} == set(LISTS["error"])
    # DIAGONAL: the first picks of a batch differ in provider AND phrase.
    first = dev[: len(providers)]
    assert (
        len({s["provider"] for s in first}) == len({s["phrase"] for s in first}) == len(providers)
    )


def test_a_planner_phrase_with_no_terms_stops_the_run(monkeypatch):
    cfg = {
        **CFG,
        "devtask_terms": {k: v for k, v in CFG["devtask_terms"].items() if k != "count tokens"},
    }
    with pytest.raises(g.BuildError, match="count tokens"):
        g.guide_subjects("developer-guide", cfg, LISTS)


def test_a_notebook_title_is_matched_to_the_planners_phrases():
    found = {
        f["phrase"]
        for f in g.notebook_terms(
            "Multimodal RAG with CLIP Embeddings and GPT-4 Vision", CFG, LISTS
        )
    }
    assert {"create embeddings", "send images", "rag"} <= found
    assert g.notebook_terms("A notebook about nothing in the plan", CFG, LISTS) == []


def test_the_plan_key_and_the_search_phrases():
    subj = next(
        s
        for s in g.guide_subjects("error-fix", CFG, LISTS)
        if s["key"] == "anthropic/529-overloaded"
    )
    fmt = next(f for f in g.load_formats()["formats"] if f["key"] == "error-fix")
    post = g.planned_guide_post(fmt, subj, CFG)
    assert post["plan"]["plan_key"] == "error-fix:anthropic/529-overloaded"
    assert post["seo"]["primary"] == "Claude API 529 overloaded" and post["seo"]["subject"] == [
        "Claude API"
    ]
    assert post["byline"] == g.GUIDE_BYLINE and post["prices"] is False


# ── the pack: passing over, and ranking as a weight ──────────────────────────


class StubReader:
    """GuideReader's surface guide_official / build_guide use, without a database."""

    def __init__(self, rows):
        self.cfg, self._rows, self.unreadable = CFG, rows, []

    def docs(self, provider):
        return self._rows

    def official(self, row, kind):
        return {
            "repo": "openai/openai-cookbook",
            "path": row["path"],
            "ref": row["blob_sha"][:7],
            "licence": "MIT",
            "read_at": "2026-10-30",
            "url": row["html_url"],
            "kind": kind,
        }


def _row(i, title, text, path=None):
    return {
        "id": f"odoc_{i}",
        "repo_key": "openai_cookbook",
        "provider": "openai",
        "path": path or f"examples/f{i}.md",
        "format": "md",
        "blob_sha": f"{i:040d}",
        "licence": "MIT",
        "html_url": f"https://github.com/o/r/blob/main/f{i}.md",
        "title": title,
        "clean_title": title,
        "text": text,
        "changed_at": datetime(2026, 10, 30, tzinfo=UTC),
    }


def test_a_subject_no_official_file_mentions_is_passed_over_and_says_so(capsys):
    subj = next(
        s
        for s in g.guide_subjects("developer-guide", CFG, LISTS)
        if s["key"] == "openai/count-tokens"
    )
    fmt = next(f for f in g.load_formats()["formats"] if f["key"] == "developer-guide")
    gr = StubReader([_row(1, "Fine-tuning a classifier", "Nothing about the subject here.")])
    assert g.build_guide(gr, fmt, subj, used_any=set()) is None
    out = capsys.readouterr().out
    assert (
        "passed over developer-guide:openai/count-tokens" in out
        and "no official openai cookbook file" in out
    )


def test_ranking_is_a_weight_scores_recorded_and_nothing_dropped_for_scoring_low():
    terms = CFG["devtask_terms"]["stream responses"]
    rows = [
        _row(1, "How to stream completions", "streaming " * 20),
        _row(2, "Batch jobs", "one mention of streaming"),
    ]  # a single hit: score 1
    docs, summary = g.guide_official(StubReader(rows), "openai", terms)
    assert [d["official_id"] for d in docs] == [
        "odoc_1",
        "odoc_2",
    ]  # the weak one is KEPT, after the strong one
    assert docs[1]["why"]["score"] == CFG["match_weights"]["text"]
    assert docs[0]["why"]["hits"]["streaming"]["text"] == CFG["text_hits_cap"]
    # A CAP keeps the best and records what it left out, with scores.
    many = [_row(i, f"Doc {i}", "streaming " * i) for i in range(1, 9)] + [
        _row(99, "Unrelated", "nothing")
    ]
    docs, summary = g.guide_official(StubReader(many), "openai", terms)
    assert len(docs) == CFG["max_official_docs"]
    assert summary["matched"] == 8 and summary["capped"] == 8 - CFG["max_official_docs"]
    assert summary["no_term"] == 1 and summary["considered"] == 9
    assert all("score" in x for x in summary["capped_scores"]) and summary["capped_scores"]
    assert all(d["why"]["score"] >= x["score"] for d in docs for x in summary["capped_scores"])


def test_term_matching_is_whole_terms_and_records_where():
    s, hits = g.term_score(
        ["stream=True", "streaming"],
        title="Streaming replies",
        path="examples/stream_x.md",
        text="use stream=True; upstreaming is not a match",
        weights=CFG["match_weights"],
        cap=10,
    )
    assert hits["streaming"] == {"title": True, "path": False, "text": 0}
    assert hits["stream=True"]["text"] == 1


# ── the code check ───────────────────────────────────────────────────────────


def test_copied_code_passes_even_reindented():
    reflowed = "\n".join("  " + ln for ln in STREAM_CODE.splitlines())
    assert g.guide_violations(_essay([_snip(reflowed)]), TEXTS, _rules()) == []


def test_altered_code_fails():
    altered = STREAM_CODE.replace("gpt-4o-mini", "gpt-6-sol")
    [v] = g.guide_violations(_essay([_snip(altered)]), TEXTS, _rules())
    assert "not in source 1's code character for character" in v and "diverges after line 3" in v


def test_code_with_no_source_fails():
    snip = {"label": "x", "variants": [{"language": "python", "code": STREAM_CODE}]}
    [v] = g.guide_violations(_essay([snip]), TEXTS, _rules())
    assert "names no source" in v


def test_code_copied_from_an_engineer_report_fails():
    [v] = g.guide_violations(_essay([_snip("print('mine')", source=3)]), TEXTS, _rules())
    assert "not an OFFICIAL SOURCE number" in v


def test_code_from_another_official_source_names_that_source():
    code = (
        "def completion_with_backoff(**kwargs):\n"
        "    return client.chat.completions.create(**kwargs)"
    )
    [v] = g.guide_violations(_essay([_snip(code, source=1)]), TEXTS, _rules())
    assert "it is in source 2's code - name that source" in v
    # Prose is not code: a sentence of the notebook is not a code block of it.
    [v] = g.guide_violations(
        _essay([_snip("The rest of this notebook measures the time")]), TEXTS, _rules()
    )
    assert "not in source 1's code" in v


def test_a_guide_may_not_reprint_most_of_a_sources_code():
    v = g.guide_violations(
        _essay(
            [_snip(OFFICIAL_2.split("```python\n")[1].split("```")[0], source=2)],
            prose="Retry with backoff [2].",
        ),
        TEXTS,
        _rules(),
    )
    assert any("does not reprint them" in x for x in v)


def test_the_same_step_in_two_languages_is_one_snippet_and_a_language_once():
    snip = {
        "label": "x",
        "variants": [
            {"language": "python", "code": STREAM_CODE, "source": 1},
            {"language": "python", "code": "import time", "source": 1},
        ],
    }
    v = g.guide_violations(_essay([snip]), TEXTS, _rules())
    assert any("gives one language twice" in x for x in v)


def test_a_backticked_name_must_be_in_an_official_source():
    v = g.guide_violations(
        _essay([_snip(STREAM_CODE)], prose="Pass `stream_mode=fast` to stream [1]."),
        TEXTS,
        _rules(),
    )
    assert any("`stream_mode=fast` is in no official source" in x for x in v)


def test_the_snippet_count_is_the_formats():
    v = g.guide_violations(_essay([]), TEXTS, _rules(snippets=(2, 6)))
    assert any("0 copied code step(s); this format carries 2 to 6" in x for x in v)


def test_a_video_is_referenced_only_by_an_id_from_the_pack():
    ok = g.guide_violations(
        _essay([_snip(STREAM_CODE)], videos=[{"video": "V1", "section": 0}]), TEXTS, _rules()
    )
    assert ok == []
    v = g.guide_violations(
        _essay(
            [_snip(STREAM_CODE)],
            videos=[{"video": "V9", "section": 0}, {"video": "https://youtu.be/x", "section": 0}],
        ),
        TEXTS,
        _rules(),
    )
    assert sum("is not a VIDEO REFERENCES id from this pack" in x for x in v) == 2
    v = g.guide_violations(
        _essay([_snip(STREAM_CODE)], videos=[{"video": "V1", "section": 4}]), TEXTS, _rules()
    )
    assert any("videos[0].section" in x for x in v)


def test_a_guide_rests_on_an_official_source():
    v = g.guide_violations(
        _essay([], prose="One developer reported a slow first chunk [3]."),
        TEXTS,
        _rules(snippets=(0, 2)),
    )
    assert any("no official source is cited or copied" in x for x in v)


def test_check_runs_the_guide_check_and_refuses_without_the_texts():
    fmt = next(f for f in g.load_formats()["formats"] if f["key"] == "developer-guide")
    rules = {**g.rules_for(fmt, "OpenAI API"), **_rules(snippets=(2, 6))}
    essay = _essay([_snip(STREAM_CODE.replace("gpt-4o-mini", "x"))])
    assert any("texts were not given" in x for x in g.check(essay, "", rules))
    assert any(
        "character for character" in x
        for x in g.check(
            essay, OFFICIAL_1, rules, doc_texts=TEXTS, doc_sources=["official", "official", "devto"]
        )
    )


def test_the_guide_formats_carry_no_written_code_and_ask_for_snippets():
    for f in g.load_formats()["formats"]:
        if f["subject"] not in g.GUIDE_SUBJECTS:
            continue
        params = g.tool_for(f)["function"]["parameters"]
        sec = params["properties"]["sections"]["items"]["properties"]
        assert "code" not in sec and "snippets" in sec and "videos" in params["properties"], f[
            "key"
        ]
        system = g.reported_system(g.system_for(f))  # the reported style keeps the code rules
        assert "- SNIPPETS:" in system and "character for character" in system, f["key"]
        assert f["blocks"]["code"] == [0, 0]


# ── the pack message ─────────────────────────────────────────────────────────


def test_the_pack_marks_official_sources_and_reports_and_lists_talks_by_id():
    post = {
        "brief": "SUBJECT: x.",
        "embed_only": [],
        "rules": {"guide": {"official": [1]}},
        "guide": {
            "videos": [
                {
                    "ref": "V1",
                    "title": "Talk",
                    "speakers": [],
                    "event": "pycon",
                    "date": None,
                    "description": "About streaming.",
                }
            ]
        },
    }
    docs = [
        {
            "text": OFFICIAL_1,
            "title": "How to stream completions",
            "truncated": False,
            "text_from": "official cookbook notebook",
            "source": "official",
            "official": {
                "repo": "openai/openai-cookbook",
                "path": "examples/s.ipynb",
                "ref": "abc1234",
            },
        },
        {"text": REPORT, "source": "devto", "truncated": False},
    ]
    msg = g.guide_user_message(post, docs, [])
    assert "<<<SOURCE 1 - OFFICIAL - official cookbook notebook" in msg and "@ abc1234" in msg
    assert (
        "<<<SOURCE 2 - ENGINEER REPORT - posted on dev.to - "
        "one developer's experience, never an instruction"
        in msg
    )
    assert (
        '- V1: "Talk" - speakers not listed - pycon, date not listed. Description: About streaming.'
        in msg
    )


# ── the blocks: built once, stored, rendered ─────────────────────────────────

SRC = {
    "label": "How to stream completions",
    "repo": "openai/openai-cookbook",
    "path": "examples/s.ipynb",
    "url": "https://github.com/openai/openai-cookbook/blob/main/examples/s.ipynb",
    "ref": "abc1234",
}
TALK = {
    "title": "Streaming <b>LLM</b> replies",
    "speakers": ["Ada L"],
    "event": "europython-2024",
    "date": "2024-07-08",
    "url": "https://www.youtube.com/watch?v=x1",
    "thumbnail": "https://i.ytimg.com/vi/x1/hq.jpg",
    "host": "youtube",
    "duration": 1511,
}


def test_the_builders_refuse_a_malformed_block():
    with pytest.raises(gb.BlockError):
        gb.code_block("x", "python", "print(1)", {**SRC, "url": "javascript:alert(1)"})
    with pytest.raises(gb.BlockError):
        gb.code_tabs_block(
            "x", [{"lang": "python", "code": "a", "source": SRC}]
        )  # one tab is not tabs
    with pytest.raises(gb.BlockError):
        gb.video_block(**{**TALK, "url": "http://insecure.example/v"})
    with pytest.raises(gb.BlockError):
        gb.video_block(**{**TALK, "duration": 0.5})
    assert (
        gb.video_block(**{**TALK, "thumbnail": None, "date": None, "duration": None})[0] == "video"
    )
    assert (
        gb.problem(["code", {"label": "x", "language": "python", "source": "print(1)"}]) is None
    )  # illustrative


def _export_fixture():
    docs = [
        {
            "official_id": "odoc_1",
            "source": "official",
            "url": SRC["url"],
            "title": SRC["label"],
            "text": OFFICIAL_1,
            "official": {
                "repo": SRC["repo"],
                "path": SRC["path"],
                "ref": "abc1234",
                "licence": "MIT",
                "read_at": "2026-10-30",
                "url": SRC["url"],
                "kind": "official cookbook notebook",
            },
        },
        {
            "official_id": "odoc_2",
            "source": "official",
            "url": SRC["url"].replace("s.ipynb", "r.ipynb"),
            "title": "Rate limits",
            "text": OFFICIAL_2,
            "official": {
                "repo": SRC["repo"],
                "path": "examples/r.ipynb",
                "ref": "def5678",
                "licence": "MIT",
                "read_at": "2026-10-29",
                "url": SRC["url"].replace("s.ipynb", "r.ipynb"),
                "kind": "x",
            },
        },
        {
            "thread_context_id": "tc_1",
            "source": "devto",
            "url": "https://dev.to/a/b-1abc",
            "text": REPORT,
        },
    ]
    post = {
        "rules": {
            "guide": {"official": [1, 2], "videos": ["V1", "V2"], "max_source_code_share": 0.5}
        },
        "guide": {
            "videos": [
                {"ref": "V1", **TALK},
                {"ref": "V2", **{**TALK, "title": "No picture", "thumbnail": None}},
            ]
        },
    }
    essay = {
        "sections": [
            {
                "heading": "Stream the reply",
                "paragraphs": ["As the notebook shows [1]."],
                "snippets": [
                    _snip(STREAM_CODE),
                    {
                        "label": "Two languages",
                        "variants": [
                            {"language": "python", "code": STREAM_CODE, "source": 1},
                            {"language": "bash", "code": "import time", "source": 1},
                        ],
                    },
                ],
            },
            {
                "heading": "Retry",
                "paragraphs": ["Back off and retry [2]. A developer saw it too [3]."],
            },
        ],
        "videos": [{"video": "V1", "section": 0}, {"video": "V2", "section": 1}],
    }
    return post, essay, docs


def test_export_builds_the_three_blocks_from_the_pack():
    post, essay, docs = _export_fixture()
    snippets, videos, stamp = g.guide_export(post, essay, docs)
    assert [b[0] for b in snippets[0]] == ["code", "code_tabs"]
    assert snippets[0][0][1]["source"] == SRC and snippets[0][0][1]["lang"] == "python"
    assert videos[0][0][1]["title"] == TALK["title"] and videos[1][0][1]["thumbnail"] is None
    # The stamp names the official sources the post USES - copied or cited -
    # never the engineer report.
    assert stamp[0] == "sources_stamp"
    assert [(x["repo"], x["ref"]) for x in stamp[1]["items"]] == [
        (SRC["repo"], "abc1234"),
        (SRC["repo"], "def5678"),
    ]
    for blocks in (snippets[0], videos[0], videos[1], [stamp]):
        for b in blocks:
            assert gb.problem(b) is None, b


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to render web/src/board/views.js")
    post, essay, docs = _export_fixture()
    snippets, videos, stamp = g.guide_export(post, essay, docs)
    body = [
        stamp,
        ["h2", {"text": "Stream the reply", "num": "01", "id": "stream"}],
        ["p", "As the notebook shows."],
        *snippets[0],
        *videos[0],
        ["h2", {"text": "Retry", "num": "02", "id": "retry"}],
        ["p", "Back off."],
        *videos[1],
        ["code", {"label": "Illustrative pattern", "language": "python", "source": "x = 1"}],
    ]
    doc = {
        "slug": "guide-probe",
        "title": "Stream with the OpenAI API",
        "dek": "d",
        "tag": "Developer guide",
        "kicker": "Developer guide",
        "by": g.GUIDE_BYLINE,
        "lead": "Short answer.",
        "meta": [],
        "tags": [],
        "decisions": [],
        "body": body,
        "sources": [],
        "cite": {},
        "layout": "runbook",
        "provenance": {
            "plan_key": "developer-guide:openai/stream-responses",
            "format": "developer-guide",
            "model": "claude",
            "checks": "x",
        },
    }
    assert blog_posts._problem(doc) is None
    f = tmp_path_factory.mktemp("guide") / "post.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    run = subprocess.run(
        [node, str(ROOT / "tests" / "js" / "guide_blocks.mjs"), str(f)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    if run.returncode:
        pytest.fail(f"guide_blocks.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def test_the_stored_post_check_refuses_a_malformed_guide_block():
    doc = {k: "x" for k in blog_posts.REQUIRED} | {
        "body": [["video", {"title": "t"}]],
        "provenance": {},
    }
    assert "video needs exactly" in blog_posts._problem(doc)


def test_the_page_draws_official_code_with_its_source_and_a_copy_button(page):
    html = page["html"]
    assert html.count('class="es-copy" data-copy') == 3  # one block + two tabs
    assert (
        "Official code" in html
        and 'href="https://github.com/openai/openai-cookbook/blob/main/examples/s.ipynb"' in html
    )
    assert "openai/openai-cookbook · examples/s.ipynb @ abc1234" in html
    assert "client.chat.completions.create(" in html and "&quot;gpt-4o-mini&quot;" in html
    # Tabs: a radio per language, the first open.
    assert html.count('class="es-tab-in"') == 2 and 'for="es-ct1-1">bash</label>' in html
    # The illustrative form still renders as illustrative.
    assert "es-illus" in html and ">Illustrative<" in html


def test_the_page_draws_a_talk_as_a_title_card_and_never_a_broken_image(page):
    html = page["html"]
    assert html.count('class="es-video"') == 2
    assert (
        'href="https://www.youtube.com/watch?v=x1" target="_blank" rel="nofollow noopener"' in html
    )
    assert (
        'src="https://i.ytimg.com/vi/x1/hq.jpg"' in html
        and html.count('class="es-video-thumb"') == 1
    )
    assert (
        "Streaming &lt;b&gt;LLM&lt;/b&gt; replies" in html and "<b>LLM</b>" not in html
    )  # escaped
    assert (
        "Ada L" in html
        and "europython-2024 · 2024-07-08 · 25:11" in html
        and "Watch on YouTube" in html
    )
    no_pic = html[html.index("No picture") - 400 : html.index("No picture") + 200]
    assert "es-video-blank" in no_pic


def test_the_page_stamps_what_it_was_checked_against_near_the_top(page):
    html = page["html"]
    stamp = html.index('class="es-stamp"')
    assert stamp < html.index("Stream the reply")
    assert (
        "Verified against <a "
        'href="https://github.com/openai/openai-cookbook/blob/main/examples/s.ipynb" '
        'rel="nofollow noopener" target="_blank">openai/openai-cookbook</a> '
        "@ <code>abc1234</code>, read 2026-10-30"
    ) in html
    assert "MIT licence" in html
    # A guide's footer says its code is copied, not illustrative.
    assert "Code is copied from the official source named under it" in html
    assert "the providers' official sources and engineers' public discussions" in html
    # Only a migration guide has the registry-facts slot.
    assert 'id="guide-facts"' not in html


def test_the_hub_classifies_the_guide_formats(page):
    k = page["kinds"]
    assert page["formats"] == ["migration-guide", "developer-guide", "tutorial", "error-fix"]
    assert k["migration-guide"] == {
        "guide": True,
        "migration": True,
        "official": False,
        "tab": "migration",
    }
    assert k["developer-guide"] == {
        "guide": True,
        "migration": False,
        "official": True,
        "tab": "developer",
    }
    assert k["error-fix"] == {
        "guide": True,
        "migration": False,
        "official": True,
        "tab": "developer",
    }
    assert k["tutorial"] == {
        "guide": True,
        "migration": False,
        "official": True,
        "tab": "tutorials",
    }
    for other in ("field-report", "topic-synthesis", "(none)"):
        assert k[other] == {"guide": False, "migration": False, "official": False, "tab": None}
