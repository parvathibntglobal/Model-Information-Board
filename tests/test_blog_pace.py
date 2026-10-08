"""Planned blog posts are checked for pace and for how they end (2026-10-06).

Was, over the 12 drafts on 2026-10-06: median sentence 19 words, every lead a
paragraph, and 11 of 12 closing on a section about choosing a model. The team
read them as slow and samey. These are the code checks that hold the generator
to `blog_formats.yaml`'s `prose`, `opening` and `closing`. No database, no model.
"""
from __future__ import annotations

import generate_sample_blogs as g

# The real limits (blog_formats.yaml `prose`), so this file cannot pass against
# a config the generator no longer reads.
PROSE = g.load_formats()["prose"]
# Varied rhythm (3 words, then 11), as the rhythm rule now asks.
FAST = "Flash is cheap. It keeps repeated context warm, so cache hits cut the bill."


def _pace(paras, tldr="A short lead.", heads=("Cache warmth decides the bill",)):
    return g._pace({"tldr": tldr}, list(heads), list(paras), PROSE)


def test_a_fast_post_passes():
    assert _pace([FAST, FAST]) == []


def test_a_quoted_fragment_does_not_end_a_sentence():
    # «...» is copied exactly, full stops and all; it must not split the
    # sentence it sits in, or a long sentence hides behind a quote.
    assert len(g.sentences("One engineer wrote «it broke. Then it broke again» and moved on.")) == 1


def test_a_slow_median_is_refused():
    slow = "Word " + " ".join(["word"] * 18) + ". Word " + " ".join(["word"] * 18) + "."
    assert any(v.startswith("sentences: the median is 19") for v in _pace([slow]))


def test_one_long_sentence_is_named_even_when_the_median_is_fast():
    long = " ".join(["word"] * 31) + "."
    out = _pace([FAST, FAST, long])
    assert any(v.startswith("a sentence of 31 words") for v in out)
    assert not any(v.startswith("sentences:") for v in out)


def test_a_paragraph_for_a_lead_is_refused():
    assert any(v.startswith("tldr: 41 words") for v in _pace([FAST], tldr=" ".join(["w"] * 41)))


def test_a_post_may_not_end_on_choosing():
    for last in ("When to use Flash vs GLM 5", "Should your team adopt GPT-6 Astra now?",
                 "How should an incoming task be routed?",
                 "Which model should handle long context?"):
        assert any("not a choice" in v for v in _pace([FAST], heads=("Cache warmth", last))), last


def test_a_closing_that_is_not_a_choice_passes():
    for last in ("What would settle long-context quality?",
                 "The failure this pattern still lets through",
                 "Rolling back when acceptance drops", "Cache warmth decides the bill"):
        assert _pace([FAST], heads=("Cache warmth", last)) == [], last


def test_every_format_names_its_opening_and_closing():
    for f in g.load_formats()["formats"]:
        assert f["opening"].strip() and f["closing"].strip(), f["key"]
        assert f["prose"] == g.load_formats()["prose"]


def test_a_formats_file_without_prose_limits_is_refused(tmp_path, monkeypatch):
    # Rule 12: no limit in code stands in for one the file forgot.
    src = g.FORMATS_FILE.read_text(encoding="utf-8")
    start = src.index("\nprose:\n")
    end = src.index("\nplanner:\n")
    bad = tmp_path / "blog_formats.yaml"
    bad.write_text(src[:start] + src[end:], encoding="utf-8")
    monkeypatch.setattr(g, "FORMATS_FILE", bad)
    try:
        g.load_formats()
    except g.BuildError as e:
        assert "prose is missing" in str(e)
    else:
        raise AssertionError("a formats file with no prose limits loaded")
