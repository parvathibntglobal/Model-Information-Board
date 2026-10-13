"""Reddit and X appear in posts only as the platforms' official embeds; every
other source is quoted and credited with platform + link.

Re-reviewed 2026-10-13 (approved by the MD): contract/publication.yaml
`derived_posts.embed_only`, docs/proposals/publish-blogs-with-official-embeds.md.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import generate_sample_blogs as g  # noqa: E402

EMBED_ONLY = ("reddit", "x")
DOCS = ["A long Reddit post. MiniMax M3 is an incredible architect for big refactors.",
        "A dev.to write-up. The part a keyword search cannot do is the whole point.",
        "An X post. M3 has a million-token window and it shows on long tasks."]
SOURCES = ["reddit", "devto", "x"]


def essay(paras, embeds):
    return {"sections": [{"heading": "One", "paragraphs": paras}], "embeds": embeds}


def violations(e):
    return g.embed_violations(e, DOCS, SOURCES, EMBED_ONLY)


def test_a_quote_from_reddit_is_refused_and_names_the_fix():
    e = essay(["He said «MiniMax M3 is an incredible architect» and left."],
              [{"discussion": 1, "section": 0, "caption": "A Reddit thread on M3."}])
    out = [v for v in violations(e) if "copies the words of a Reddit post" in v]
    assert out and "embedded in section 0" in out[0]


def test_a_quote_from_another_platform_is_allowed():
    e = essay(["The engineer said «The part a keyword search cannot do»."],
              [{"discussion": 1, "section": 0, "caption": "A Reddit thread on M3."}])
    assert not [v for v in violations(e) if "copies the words" in v]


def test_only_embed_only_sources_may_be_embedded():
    e = essay(["A dev.to write-up made the point."],
              [{"discussion": 2, "section": 0, "caption": "A dev.to write-up."}])
    assert any("from dev.to, which is quoted, not embedded" in v for v in violations(e))


def test_a_post_with_reddit_or_x_threads_must_embed_one():
    assert any(v.startswith("embeds: 0") for v in violations(essay(["Plain prose."], [])))


def test_an_embed_caption_is_our_words():
    e = essay(["Prose."], [{"discussion": 3, "section": 0, "caption": "He said «it shows»."}])
    assert any("caption" in v for v in violations(e))


def test_crediting_an_embedded_poster_needs_no_quote():
    """The credit rule and the embed rule fought for nine repairs running in the
    demo (2026-10-13). An embedded post is the engineer's words on the page."""
    sent = "A developer on Reddit reported worse results on a large codebase."
    base = {"sections": [{"heading": "One", "paragraphs": [sent] * 3}]}
    kw = {"doc_texts": DOCS, "doc_sources": SOURCES, "embed_only": EMBED_ONLY}
    reddit = [{"discussion": 1, "section": 0, "caption": "A Reddit thread."}]
    without = g.check(dict(base, embeds=[]), "\n".join(DOCS), **kw)
    with_embed = g.check(dict(base, embeds=reddit), "\n".join(DOCS), **kw)
    assert any("credits practitioners" in v for v in without)
    assert not any("credits practitioners" in v for v in with_embed)


def _banned(text):
    return [why for pat, why in g.BANNED if __import__("re").search(pat, text, __import__("re").I)]


def test_platforms_may_be_named_but_handles_and_links_may_not():
    assert not _banned("A developer on Reddit and one engineer on X agreed.")
    assert _banned("As u/someone wrote") and _banned("see https://example.com")
    assert _banned("in r/LocalLLaMA")


def test_the_post_is_legal_the_posts_is_not():
    assert not [w for w in _banned("The post shows a stalled run.") if "inputs" in w]
    assert [w for w in _banned("The posts show a stalled run.") if "inputs" in w]


def test_the_writer_may_not_narrate_the_rules():
    assert _banned("We cannot quote that embed-only discussion.")


def test_a_credit_comes_from_the_url_alone():
    c = g.credit_of("devto", "https://dev.to/someone/can-gpt-6-astra-generate-a-pcb-1flg")
    assert c == {"platform": "dev.to", "who": "someone", "what": "Can gpt 6 astra generate a pcb",
                 "url": "https://dev.to/someone/can-gpt-6-astra-generate-a-pcb-1flg"}
    assert g.credit_of("github", "https://github.com/o/r/issues/7")["what"] == "Issue #7"


def test_an_unknown_platform_is_refused_not_guessed():
    with pytest.raises(g.BuildError):
        g.platform_name("somewhere-new")


def test_an_embed_url_of_the_wrong_shape_is_refused():
    with pytest.raises(g.BuildError):
        g.official_embed("x", "https://evil.example/status/1")
    with pytest.raises(g.BuildError):
        g.official_embed("reddit", "https://www.reddit.com/user/someone/")


def test_the_loader_refuses_a_missing_embed_only_key(monkeypatch):
    from judge import config, publication
    publication.derived_posts_embed_only.cache_clear()
    no_key = {"derived_posts": {"may_draw_on_withheld": True}}
    monkeypatch.setattr(config, "_read", lambda name: no_key)
    try:
        with pytest.raises(publication.PublicationConfigError):
            publication.derived_posts_embed_only()
    finally:
        publication.derived_posts_embed_only.cache_clear()


@pytest.fixture(scope="module")
def page():
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to render web/src/board/views.js")
    probe = str(ROOT / "tests" / "js" / "blog_embeds.mjs")
    run = subprocess.run([node, probe], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if run.returncode:
        pytest.fail(f"blog_embeds.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)["html"]


def test_the_page_credits_a_quote_with_platform_and_link(page):
    assert 'href="#es-src-1"' in page and 'id="es-src-1"' in page
    assert "https://dev.to/someone/a-write-up-1abc" in page and "dev.to" in page


def test_the_page_draws_the_platforms_own_embeds(page):
    assert 'class="reddit-embed-bq"' in page
    assert "https://www.reddit.com/r/LocalLLaMA/comments/1abcde" in page
    assert 'class="twitter-tweet"' in page
    assert "https://twitter.com/someone/status/1234567890" in page
    assert "if the post is deleted it disappears here too" in page


def test_an_embed_with_a_foreign_url_draws_nothing(page):
    assert "EVIL REDDIT" not in page and "EVIL X" not in page and "javascript:" not in page
