"""Blog posts: a polished skim line per paragraph, and livelier, less repetitive prose.

Measured 2026-10-08 over the 12 drafts: of 224 paragraphs the skim view (each
paragraph's first sentence) showed 27 openers under 8 words, 13 leaning on the
sentence before ("That...", "This...") and 3 quotes; 'rather' ran to 10 a post,
'is listed at' recited a price in 7 posts, and sentence lengths were even
(spread/mean 0.32-0.43). These pin the checks that hold the generator to
blog_formats.yaml `prose`. No database, no model.
"""
from __future__ import annotations

import generate_sample_blogs as g

PROSE = g.load_formats()["prose"]
PARA = ("Opus cut a refactor short. The team had asked for every caller to move to the "
        "new client, and the model stopped after the first module. Nobody noticed until CI.")
GOOD_SKIM = ("Opus stopped a multi-module refactor after the first module, "
             "and the gap surfaced only in CI.")


def _section(paras, skim):
    return {"heading": "h", "paragraphs": paras, "skim": skim}


# ── skim lines ──────────────────────────────────────────────────────────────

def test_a_polished_skim_line_passes():
    assert g._skim_lines([_section([PARA], [GOOD_SKIM])], PROSE) == []


def test_one_line_per_paragraph():
    out = g._skim_lines([_section([PARA, PARA], [GOOD_SKIM])], PROSE)
    assert any("1 line(s) for 2 paragraph(s)" in v for v in out)


def test_a_fragment_is_refused():
    out = g._skim_lines([_section([PARA], ["Opus stopped short."])], PROSE)
    assert any("words; a skim line is one sentence" in v for v in out)


def test_a_quote_is_refused():
    line = ("Engineers said «it stopped after the first module» "
            "during a long multi-module refactor run.")
    out = g._skim_lines([_section([PARA], [line])], PROSE)
    assert any("no «quotes»" in v for v in out)


def test_a_line_leaning_on_an_unseen_sentence_is_refused():
    line = "This meant the refactor stopped after the first module and nobody noticed until CI."
    out = g._skim_lines([_section([PARA], [line])], PROSE)
    assert any("leans on a sentence" in v for v in out)


def test_an_unfinished_line_is_refused():
    line = ("Opus stopped a multi-module refactor after the first module "
            "and the gap surfaced only in CI")
    out = g._skim_lines([_section([PARA], [line])], PROSE)
    assert any("not a finished sentence" in v for v in out)


def test_a_line_about_something_else_is_refused():
    line = "Gemini handles long video transcripts with ease across a wide range of languages today."
    out = g._skim_lines([_section([PARA], [line])], PROSE)
    assert any("shares no key term" in v for v in out)


# ── livelier, less repetitive prose ─────────────────────────────────────────

def test_lively_prose_passes():
    paras = [PARA, "Cache hits changed the bill. "
                   "A stable prefix kept most input tokens warm across the session."]
    lens = [len(s.split()) for p in paras for s in g.sentences(p)]
    assert g._lively(paras, lens, PROSE) == []


def test_an_even_rhythm_is_recorded_not_refused():
    """Rule 8: the 0.45 target was set from the drafts it judged, and the first
    draft under it held at 0.43 for four repairs. Recorded, never a gate."""
    para = ("The model reads the whole file first. The team checks every changed line next. "
            "The harness runs the whole test suite after.")
    paras = [para] * 2
    lens = [len(s.split()) for p in paras for s in g.sentences(p)]
    assert not any("spread/mean" in v for v in g._lively(paras, lens, PROSE))
    cv = g.rhythm_cv({"sections": [{"paragraphs": paras}]})
    assert cv is not None and cv < PROSE["rhythm_cv_target"]


def test_too_few_sentences_have_no_rhythm_reading():
    assert g.rhythm_cv({"sections": [{"paragraphs": ["One. Two words."]}]}) is None


def test_a_stock_word_over_its_cap_is_refused():
    para = "Rather than wait, rather than guess, rather than retry, the team pinned the version."
    out = g._lively([para], [len(para.split())], PROSE)
    assert any("'rather' used 3 times" in v for v in out)


def test_a_set_phrase_is_refused():
    para = "The benchmark does not establish how it behaves in a long agent loop at scale."
    out = g._lively([para], [len(para.split())], PROSE)
    assert any("stock phrase 'does not establish'" in v for v in out)


def test_prices_belong_to_the_rate_card():
    para = ("Input costs $0.04 per million tokens. Output costs $0.08 per million tokens, "
            "and cached input $0.01 per million.")
    lens = [len(s.split()) for s in g.sentences(para)]
    assert any(v.startswith("prices recited 3 times") for v in g._lively([para], lens, PROSE))


def test_the_limits_are_configuration_not_defaults(tmp_path, monkeypatch):
    """Rule 12: the formats file must name every limit; none is assumed."""
    src = g.FORMATS_FILE.read_text(encoding="utf-8").replace("  rhythm_cv_target: 0.45\n", "")
    bad = tmp_path / "blog_formats.yaml"
    bad.write_text(src, encoding="utf-8")
    monkeypatch.setattr(g, "FORMATS_FILE", bad)
    try:
        g.load_formats()
    except g.BuildError as e:
        assert "rhythm_cv_target" in str(e)
    else:
        raise AssertionError("a formats file without rhythm_cv_target loaded")
