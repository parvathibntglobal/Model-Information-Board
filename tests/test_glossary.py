"""The AI glossary (2026-10-20): glossary.yaml, judge/glossary.py and the two
public endpoints. The file is reviewed copy; these tests are what keeps it
reading like a glossary - one short paragraph per term, every related link
landing on a real term, no figure that claims how well something works.
"""

from __future__ import annotations

import pytest
import yaml
from fastapi.testclient import TestClient

from judge import gate, glossary
from judge.app import app

LIMITS = glossary._limits()

GOOD = {
    "slug": "context-window",
    "term": "Context window",
    "aka": ["context length"],
    "category": "prompting",
    "teaser": "The most text a model can read and write in one call, counted in tokens.",
    "definition": (
        "A context window is the most text a model can handle in one call. "
        "Everything counts against it, the answer included. "
        "A request past the limit is refused. "
        "A larger window lets a model read a whole contract at once. "
        "It does not mean every part is used equally well. "
        "So teams still trim what a task does not need."
    ),
    "related": ["token", "max-tokens"],
}
KNOWN = {"context-window", "token", "max-tokens"}


def problems(**change):
    return glossary.problems([{**GOOD, **change}], known=KNOWN, limits=LIMITS)


# ── the file as shipped ─────────────────────────────────────────────────────


def test_the_glossary_file_passes_every_check():
    entries = glossary.load()
    assert len(entries) >= 100


def test_every_category_in_the_file_is_named():
    assert {e["category"] for e in glossary.load()} <= set(glossary.CATEGORIES)


# ── the checks ──────────────────────────────────────────────────────────────


def test_a_good_entry_passes():
    assert problems() == []


def test_a_definition_is_a_paragraph_not_a_post():
    long = " ".join(["A context window is short."] + ["It holds tokens."] * 12)
    assert any("sentences; 6 to 10" in p for p in problems(definition=long))
    assert any("sentences; 6 to 10" in p for p in problems(definition="A context window is small."))


def test_the_first_sentence_names_the_term():
    d = GOOD["definition"].replace("A context window is", "It is", 1)
    assert any("must name the term" in p for p in problems(definition=d))


def test_an_aka_name_counts_as_naming_it():
    d = GOOD["definition"].replace("A context window is", "Context length is", 1)
    assert problems(definition=d) == []


def test_sentences_stay_short():
    s = " ".join(["word"] * (LIMITS["sentence_max_words"] + 1)) + "."
    d = GOOD["definition"] + " " + s.capitalize()
    assert any("-word sentence" in p for p in problems(definition=d))


def test_no_performance_figure():
    d = GOOD["definition"].replace("is refused.", "is refused about 30% of the time.")
    assert any("performance figure" in p for p in problems(definition=d))
    d = GOOD["definition"].replace("is refused.", "is 3x slower.")
    assert any("performance figure" in p for p in problems(definition=d))


def test_a_precision_is_not_a_performance_figure():
    """4-bit describes a format; it does not claim a result."""
    d = GOOD["definition"].replace("is refused.", "is refused in 4-bit too.")
    assert not [p for p in problems(definition=d) if "performance figure" in p]


def test_no_quotes():
    assert any("quotes something" in p for p in problems(teaser='The "most" text a model reads.'))


def test_the_teaser_is_one_short_sentence():
    assert any("one sentence" in p for p in problems(teaser="Short. Two sentences."))
    assert any("characters" in p for p in problems(teaser=("word " * 40).strip() + "."))


def test_related_terms_must_exist_and_not_be_itself():
    assert any("is not in the glossary" in p for p in problems(related=["token", "nope"]))
    assert any("lists itself" in p for p in problems(related=["token", "context-window"]))
    assert any("2 to 5" in p for p in problems(related=["token"]))


def test_a_name_belongs_to_one_term():
    other = {**GOOD, "slug": "token", "term": "Token", "aka": ["context length"],
             "related": ["context-window", "max-tokens"]}
    out = glossary.problems([GOOD, other], known=KNOWN, limits=LIMITS)
    assert any("is also" in p for p in out)


def test_an_unknown_category_is_refused():
    assert any("category" in p for p in problems(category="misc"))


def test_a_broken_file_is_refused_with_every_reason(tmp_path):
    f = tmp_path / "g.yaml"
    bad = {**GOOD, "category": "misc", "related": ["nope", "token"]}
    f.write_text(yaml.safe_dump({"terms": [bad]}), encoding="utf-8")
    with pytest.raises(glossary.GlossaryError) as e:
        glossary.load(f)
    assert "category" in str(e.value) and "not in the glossary" in str(e.value)


# ── the cache (2026-10-21, #552) ────────────────────────────────────────────


def _count_reads(monkeypatch) -> list:
    reads = []
    real = glossary._read
    monkeypatch.setattr(glossary, "_read", lambda p: reads.append(p) or real(p))
    return reads


def test_the_file_is_read_once_until_it_changes(monkeypatch):
    """Parsing and checking cost ~117 ms a call; a page should not pay it."""
    glossary._CACHE.clear()
    reads = _count_reads(monkeypatch)
    first = glossary.load()
    assert glossary.load() == first and glossary.index()["terms"]
    assert len(reads) == 1


def test_an_edited_file_is_read_again_without_a_restart(tmp_path, monkeypatch):
    f = tmp_path / "g.yaml"
    f.write_text(yaml.safe_dump({"terms": []}), encoding="utf-8")
    reads = _count_reads(monkeypatch)
    assert glossary.load(f) == []
    f.write_text(yaml.safe_dump({"terms": []}) + "\n# edited\n", encoding="utf-8")
    glossary.load(f)
    assert reads == [f, f], "a changed size or mtime must mean a fresh read"


def test_what_one_caller_changes_the_next_is_not_served():
    glossary._CACHE.clear()
    mine = glossary.load()
    mine[0]["term"] = "CHANGED"
    mine[0]["aka"].append("CHANGED")
    fresh = glossary.load()
    assert fresh[0]["term"] != "CHANGED" and "CHANGED" not in fresh[0]["aka"]


def test_a_broken_file_is_never_kept(tmp_path):
    f = tmp_path / "g.yaml"
    f.write_text(yaml.safe_dump({"terms": [{**GOOD, "category": "misc"}]}), encoding="utf-8")
    for _ in range(2):
        with pytest.raises(glossary.GlossaryError):
            glossary.load(f)
    assert f not in glossary._CACHE


# ── the pages ───────────────────────────────────────────────────────────────


def test_the_glossary_is_a_public_read():
    assert "/glossary-terms" in gate.PUBLIC_READ_PATHS
    assert "/glossary-terms/" in gate.PUBLIC_READ_PREFIXES


def test_the_index_and_a_term_are_served_without_a_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "s3cret")
    c = TestClient(app)
    idx = c.get("/glossary-terms")
    assert idx.status_code == 200
    first = idx.json()["terms"][0]
    assert set(first) == {"slug", "term", "aka", "category", "teaser"}
    one = c.get(f"/glossary-terms/{first['slug']}")
    assert one.status_code == 200
    body = one.json()
    assert body["definition"] and body["related"] and body["previous"] is None
    assert c.get("/glossary-terms/no-such-term").status_code == 404


def test_a_broken_file_is_a_503_naming_the_problem(monkeypatch, tmp_path):
    f = tmp_path / "g.yaml"
    f.write_text(yaml.safe_dump({"terms": [{**GOOD, "category": "misc"}]}), encoding="utf-8")
    monkeypatch.setattr(glossary, "PATH", f)
    r = TestClient(app).get("/glossary-terms")
    assert r.status_code == 503 and "category" in r.json()["detail"]
