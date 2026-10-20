"""The reported style (blog_rules.yaml, 2026-10-20): posts in the reporter's
own words, a reference number after each reported fact, a source's words only
as one whole sentence in a highlight box, Reddit and X only as embeds.

The checks are `generate_sample_blogs.reported_violations`, reading their
thresholds from blog_rules.yaml; the rules Admin -> Blogs shows are
`judge.blog_rules.rules()`, from the same file.
"""

from __future__ import annotations

import pytest

import generate_sample_blogs as g
from judge import blog_rules

DOCS = [
    "We moved the batch jobs to the smaller model in March. "
    "The cost of the nightly run fell from $310 to $42 "
    "after the switch. Latency stayed under two seconds for most requests.",
    "A Reddit thread about the same migration.",
    "Context windows are not memory. "
    "A long prompt costs money on every call, and the model forgets it the "
    "moment the call ends.",
]
SOURCES = ["devto", "reddit", "hackernews"]
EMBED_ONLY = ("reddit",)
LIMITS = g.newsroom()["limits"]


def essay(paras, **extra):
    return {
        "title": "t",
        "dek": "A short dek.",
        "tldr": "A short line.",
        "sections": [{"heading": "h", "paragraphs": paras}],
        **extra,
    }


def run(e, need=1):
    return g.reported_violations(e, DOCS, SOURCES, EMBED_ONLY, facts_text="", need_refs=need)


def rule_ids(v):
    return {x.split(":")[0] for x in v}


def test_a_clean_reported_paragraph_passes():
    e = essay(
        [
            "One team moved its nightly batch to a smaller model, "
            "and the bill dropped from $310 to $42 [1].",
            "We think that holds only for batch work. "
            "Prompts are not memory; they are paid for each call [3].",
        ]
    )
    assert run(e) == []


def test_a_partial_quote_is_refused():
    v = run(essay(["The team said «the cost of the nightly run fell» after the switch [1]."]))
    assert "own-words" in rule_ids(v)


def test_copying_a_run_of_words_is_refused():
    v = run(
        essay(
            ["The cost of the nightly run fell from $310 to $42 after the switch, they wrote [1]."]
        )
    )
    assert "no-copied-runs" in rule_ids(v)


def test_a_credited_claim_needs_its_reference():
    v = run(
        essay(
            [
                "One engineer reported the bill dropped sharply after the move.",
                "Prompts are paid for on every call [3].",
            ]
        )
    )
    assert any(x.startswith("reference-every-claim") and "credits a source" in x for x in v)


def test_reddit_is_never_cited_by_number():
    v = run(essay(["A poster described the same move [2]. Prompts cost money on each call [3]."]))
    assert "reddit-x-embedded" in rule_ids(v)


def test_a_reference_must_be_a_source():
    v = run(essay(["The bill dropped after the move [9]."]))
    assert any("is not a source number" in x for x in v)


def test_every_section_cites_something():
    v = run(
        {"sections": [{"heading": "h", "paragraphs": ["Our own view, with no source behind it."]}]}
    )
    assert any("cites no source" in x for x in v)


def test_a_sourced_figure_carries_a_reference():
    v = run(
        essay(
            ["The nightly bill fell to $42 after the move.", "Prompts cost money on each call [3]."]
        )
    )
    assert any("the figure $42 comes from a source" in x for x in v)


def test_a_whole_sentence_highlight_passes():
    e = essay(
        ["Prompts cost money on every call [3]."],
        highlights=[{"section": 0, "discussion": 3, "text": "Context windows are not memory."}],
    )
    # 5 words is under the minimum, so make it long enough to be about length only:
    long_ok = essay(
        ["Prompts cost money on every call [3]."],
        highlights=[
            {
                "section": 0,
                "discussion": 1,
                "text": "The cost of the nightly run fell from $310 to $42 after the switch.",
            }
        ],
    )
    assert not [x for x in run(long_ok) if "whole sentence" in x]
    assert any("words;" in x for x in run(e))  # too short, said as length


def test_a_fragment_is_not_a_highlight():
    e = essay(
        ["Prompts cost money on every call [3]."],
        highlights=[
            {
                "section": 0,
                "discussion": 1,
                "text": "the cost of the nightly run fell from $310 to $42.",
            }
        ],
    )
    assert any("is not one whole sentence" in x for x in run(e))


def test_a_reddit_highlight_is_refused():
    e = essay(
        ["Prompts cost money on every call [3]."],
        highlights=[
            {"section": 0, "discussion": 2, "text": "A Reddit thread about the same migration."}
        ],
    )
    assert any("embedded, never quoted" in x for x in run(e))


def test_sentences_stay_short():
    long = " ".join(["word"] * (LIMITS["sentence_max_words"] + 2)) + " [3]."
    v = run(essay([long]))
    assert any(
        x.startswith("short-sentences") and f"at most {LIMITS['sentence_max_words']}" in x
        for x in v
    )


def test_the_average_is_checked():
    # Sentences just under the maximum, enough of them to outweigh the short
    # dek and tldr, which count too.
    s = " ".join(["word"] * (LIMITS["sentence_max_words"] - 1)) + "."
    v = run(essay([f"{s} {s} {s} Costs fell [3].", f"{s} {s} {s}"]))
    assert any("sentences average" in x for x in v)


def test_whether_is_rationed():
    n = LIMITS["whether_max_per_post"] + 1
    v = run(essay(["We asked whether it worked [3]. " * n]))
    assert "whether-sparingly" in rule_ids(v)


def test_pull_quotes_are_gone():
    e = essay(["Prompts cost money on every call [3]."])
    e["sections"][0]["pull_quote"] = "Context windows are not memory."
    assert any("pull quotes are gone" in x for x in run(e))


def test_a_reference_marker_is_not_a_figure():
    """The number check strips [n] first: "[3]" is not an unverified 3."""
    v = g.check(
        essay(["Prompts cost money on every call [3]."]),
        "\n".join(DOCS),
        {
            "style": "reported",
            "sections": (1, 9),
            "per_section": (1, 9),
            "matrix": False,
            "tree": False,
            "code": (0, 9),
            "words": (0, 99999),
        },
        doc_texts=DOCS,
        doc_sources=SOURCES,
        embed_only=EMBED_ONLY,
    )
    assert not [x for x in v if "the number 3" in x]


# ── the rules file ──────────────────────────────────────────────────────────


def test_a_missing_limit_is_refused(tmp_path, monkeypatch):
    f = tmp_path / "blog_rules.yaml"
    f.write_text("style: reported\nlimits:\n  sentence_max_words: 25\n", encoding="utf-8")
    monkeypatch.setattr(g, "NEWSROOM_FILE", f)
    with pytest.raises(g.BuildError, match="limits missing"):
        g.newsroom()


def test_the_writer_gets_the_rules_not_the_quoting_instructions():
    sys_prompt = g.reported_system(g.SYSTEM)
    assert "«" not in sys_prompt.split("HOW TO WRITE THIS POST")[0]
    assert "NEWSROOM RULES" in sys_prompt
    assert f"none runs past {LIMITS['sentence_max_words']}" in sys_prompt


def test_the_schema_takes_highlights_not_pull_quotes():
    schema = g.reported_schema(g.TOOL["function"]["parameters"])
    assert "highlights" in schema["properties"]
    assert "pull_quote" not in schema["properties"]["sections"]["items"]["properties"]


def test_admin_shows_every_rule_with_its_threshold():
    r = blog_rules.rules()
    assert r["available"] and r["style"] == "reported"
    rules = {x["id"]: x for s in r["sections"] for x in s["rules"]}
    assert f"average {LIMITS['sentence_average_words']} words" in rules["short-sentences"]["detail"]
    assert {x["checked"] for x in rules.values()} <= {"code", "editor", "process"}
    assert r["counts"]["code"] >= 15


def test_a_rule_with_an_unknown_kind_is_refused(tmp_path):
    f = tmp_path / "r.yaml"
    f.write_text(
        "limits: {}\nsections:\n- name: x\n  rules:\n  - {id: a, rule: b, checked: maybe}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="checked='maybe'"):
        blog_rules.rules(f)


def test_a_highlight_opening_a_line_under_a_title_is_a_whole_sentence():
    """An abstract's first sentence sits under a title with no full stop.
    Folding the newline made the title look like the start of its sentence
    (computer-use pack, source 1, 2026-10-20)."""
    sentence = "Real desktop automation is neither purely visual nor purely programmatic."
    doc = "Desktop Agents at Work\n" + sentence
    assert g._whole_sentence_in(sentence, doc)
    assert not g._whole_sentence_in(sentence.removeprefix("Real desktop "), doc)


def test_the_store_accepts_a_highlight_with_its_reference():
    from judge import blog_posts

    post = {k: "x" for k in blog_posts.REQUIRED}
    post["sources"] = [{"n": 1}]
    post["body"] = [["highlight", {"text": "One whole sentence.", "n": 1}]]
    assert blog_posts._problem(post) is None
    post["body"] = [["highlight", {"text": "One whole sentence.", "n": 2}]]
    assert "does not list" in blog_posts._problem(post)
    post["body"] = [["highlight", {"n": 1}]]
    assert "without its text" in blog_posts._problem(post)


# ── where a draft is stored ─────────────────────────────────────────────────


def test_ingest_stores_drafts_in_the_shared_database():
    dsn = "postgresql://u:secret@shared.example:5432/board"
    assert g.drafts_dsn({"BLOG_DRAFTS_DATABASE_URL": dsn, "DATABASE_URL": "local"}) == dsn


def test_ingest_never_falls_back_to_the_local_database():
    """A fallback to DATABASE_URL would store the draft where only the writer
    can see it, and look like success (rule 12)."""
    with pytest.raises(g.BuildError, match="BLOG_DRAFTS_DATABASE_URL is not set"):
        g.drafts_dsn({"DATABASE_URL": "postgresql://postgres@localhost:5433/x"})


def test_the_store_line_names_the_database_and_never_the_password():
    assert g.db_where("postgresql://u:secret@shared.example:5432/board?ssl=1") == (
        "shared.example:5432/board"
    )


# ── one reference mark per paragraph (2026-10-20) ──────────────────────────


def test_one_mark_at_the_end_of_a_paragraph_passes():
    e = essay(
        [
            "One team moved its nightly batch to a smaller model. "
            "The bill dropped from $310 to $42, and prompts still cost money each call [1, 3]."
        ]
    )
    assert run(e) == []


def test_a_mark_after_every_sentence_is_refused():
    e = essay(["The bill dropped from $310 to $42 [1]. Prompts cost money on each call [3]."])
    assert "cite-once-per-paragraph" in rule_ids(run(e))


def test_a_single_mark_mid_paragraph_is_refused():
    e = essay(["The bill dropped from $310 to $42 [1]. We think that holds only for batch work."])
    assert any(x.startswith("cite-once-per-paragraph") and "not at the end" in x for x in run(e))


def test_the_end_mark_covers_a_credit_earlier_in_the_paragraph():
    """The credit is in the first sentence; the paragraph's one mark covers it."""
    e = essay(["One engineer reported the bill dropped sharply. It held for months [1]."])
    assert not [x for x in run(e) if "credits a source" in x]
