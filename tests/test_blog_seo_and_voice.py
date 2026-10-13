"""Blog posts written for search and in a blogger's voice (2026-10-13).

What is pinned, with no database and no model:
- first-person EXPERIENCE ("we tried", "we measured") must retell a WHAT WE TRIED
  note from blog_experiences.yaml - a figure or four words of it - and is refused
  outright when the post has no note; first-person OPINION needs no record;
- a note's figures pass the number check, but a note is never quotable as an
  engineer's «words»;
- the primary keyword sits in the title, description, short answer or opening,
  first in `keywords`, and in at least one FAQ question;
- the FAQ has 3 to 5 questions ending in "?", answered in 40 to 90 words that
  open on a short direct answer.
"""
from __future__ import annotations

import generate_sample_blogs as g

NOTE = ("We ran DeepSeek V4 Flash and Gemini 2.5 Flash as the claim extractor in our own "
        "pipeline on the same 2 threads. DeepSeek V4 Flash produced 17 verified claims and "
        "the two threads took 73 seconds.")
EXP = g.norm(NOTE)


# ── first-person experience ────────────────────────────────────────────────────


def test_an_opinion_needs_no_record():
    opinion = "We think the cheaper model is the better default here."
    assert g.experience_unanchored(opinion, "") is None
    assert g.experience_unanchored("We disagree with that reading.", EXP) is None


def test_an_experience_without_any_note_is_refused():
    why = g.experience_unanchored("We tried it on our own pipeline and it held up.", "")
    assert why and "no WHAT WE TRIED note" in why


def test_an_experience_carrying_the_notes_figure_passes():
    assert g.experience_unanchored("We ran it ourselves and got 17 verified claims.", EXP) is None


def test_an_experience_carrying_the_notes_wording_passes():
    sent = "We tried it as the claim extractor in our own pipeline."
    assert g.experience_unanchored(sent, EXP) is None


def test_an_invented_experience_is_refused_even_with_notes():
    sent = "We tested it on a legal corpus and it hallucinated twice."
    why = g.experience_unanchored(sent, EXP)
    assert why and "retells no WHAT WE TRIED note" in why


def _essay(paragraph: str) -> dict:
    return {"title": "t", "dek": "", "description": "", "tldr": "", "keywords": [],
            "sections": [{"heading": "h", "paragraphs": [paragraph], "skim": []}]}


def test_a_notes_figure_passes_the_number_check_but_is_not_quotable():
    ctx = "an engineer wrote that it never broke"
    rules = dict(g.LEGACY_RULES, sections=(0, 99), matrix=False, tree=False,
                 code=(0, 99), words=(0, 99999))
    ok = g.check(_essay("We ran it and the two threads took 73 seconds."), ctx, rules, EXP)
    assert not [v for v in ok if "73" in v]
    para = "It held: «DeepSeek V4 Flash produced 17 verified claims»."
    quoted = g.check(_essay(para), ctx, rules, EXP)
    assert any("not verbatim in any discussion" in v for v in quoted)


def _retrace_essay(*paras):
    return {"sections": [{"heading": "h", "paragraphs": list(paras)}]}


def test_retracing_an_engineers_test_with_their_words_passes():
    para = ("We went through one engineer's arena test move by move. At the key turn Sol "
            "attacked instead of blocking: «does not block K8, and attacks instead».")
    assert g.retrace_violations(_retrace_essay(para)) == []


def test_retracing_without_quoting_them_is_refused():
    v = g.retrace_violations(_retrace_essay("We retraced how a team moved their pipeline."))
    assert any("without quoting them" in x for x in v)


def test_a_post_retraces_at_least_one_engineers_work():
    v = g.retrace_violations(_retrace_essay("We think the cheaper model wins here."))
    assert any(x.startswith("retracing:") for x in v)


def test_retracing_never_licenses_we_ran_it():
    sent = "We ran the arena test ourselves and Sol lost."
    assert g.experience_unanchored(sent, "") is not None


def test_we_read_is_allowed_but_naming_the_reading_list_is_not():
    import re
    assert not any(re.search(pat, "we read one developer's complaint", re.I) for pat, _ in g.BANNED)
    assert any(re.search(pat, "we read the threads", re.I) for pat, _ in g.BANNED)

# ── search: keyword placement and the FAQ ──────────────────────────────────────

ANSWER = ("Claude Opus 5 is the safer pick for long refactors. Teams that moved to it saw fewer "
          "stalled tool loops, though it costs more per call. If your workload is short "
          "single-file edits, the cheaper model is usually enough, and the difference "
          "rarely shows up.")


def _seo_essay(**over) -> dict:
    e = {"title": "Claude Opus 5 vs GPT-6 Sol: which one holds up?",
         "description": "Claude Opus 5 vs GPT-6 Sol in production: where each breaks.",
         "tldr": "Pick Claude Opus 5 vs GPT-6 Sol by workload, not by benchmark.",
         "keywords": ["Claude Opus 5 vs GPT-6 Sol", "AI model comparison"],
         "sections": [{"heading": "h", "paragraphs": [
             "We agree with the teams that pin a provider. "
             "We are not convinced the cheaper model wins every refactor."]}],
         "faq": [{"question": "Is Claude Opus 5 vs GPT-6 Sol worth the price?", "answer": ANSWER},
                 {"question": "Which is better for coding agents?", "answer": ANSWER},
                 {"question": "Does GPT-6 Sol stall in tool loops?", "answer": ANSWER}]}
    e.update(over)
    return e


SEO = {"primary": "Claude Opus 5 vs GPT-6 Sol", "secondary": [],
       "subject": ["Claude Opus 5", "GPT-6 Sol"]}


def test_a_well_placed_keyword_and_faq_pass():
    assert g.seo_violations(_seo_essay(), SEO) == []


def test_the_keyword_must_be_in_title_description_and_lead():
    v = g.seo_violations(_seo_essay(title="Two models compared", description="A comparison.",
                                    tldr="It depends."), SEO)
    assert any(x.startswith("title:") for x in v)
    assert any(x.startswith("description:") for x in v)
    assert any(x.startswith("tldr or first paragraph:") for x in v)


def test_the_keyword_is_listed_first():
    kws = ["AI model comparison", "Claude Opus 5 vs GPT-6 Sol"]
    v = g.seo_violations(_seo_essay(keywords=kws), SEO)
    assert any(x.startswith("keywords:") for x in v)


def test_the_faq_answers_questions_people_type():
    short = _seo_essay(faq=[{"question": "A statement.", "answer": "Too short."}])
    v = g.seo_violations(short, SEO)
    assert any("needs exactly 3 questions" in x for x in v)
    assert any("ending with '?'" in x for x in v)
    assert any("answer in 40 to 90" in x for x in v)


def test_one_faq_question_names_the_subject():
    faq = [{"question": "Which is better for coding agents?", "answer": ANSWER}] * 3
    v = g.seo_violations(_seo_essay(faq=faq), SEO)
    assert any("at least one question must name" in x for x in v)
    named = [{"question": "Is GPT-6 Sol good for coding agents?", "answer": ANSWER}] * 3
    assert not [x for x in g.seo_violations(_seo_essay(faq=named), SEO) if "must name" in x]


def test_a_post_that_takes_no_position_is_refused():
    flat = _seo_essay(sections=[{"heading": "h", "paragraphs": ["The provider matters."]}])
    assert any(x.startswith("voice:") for x in g.seo_violations(flat, SEO))


def test_stance_is_a_position_not_an_experience():
    assert g.STANCE.search("In our view, pin the provider.")
    assert g.STANCE.search("We are not convinced by that claim.")
    assert not g.STANCE.search("We ran it twice.")


def test_keyword_matching_ignores_case_and_punctuation():
    assert g._kw_in("claude opus 5 VS gpt 6 sol - a review", "Claude Opus 5 vs GPT-6 Sol")
    assert not g._kw_in("GPT-6 Sol vs Claude", "Claude Opus 5 vs GPT-6 Sol")


# ── planning: keywords, notes, trending ────────────────────────────────────────


def test_keyword_plans_per_subject_kind():
    cfg = g.load_keywords()
    pair = g.keyword_plan({"kind": "pair", "a": "A", "b": "B", "label": "x"}, cfg)
    model = g.keyword_plan({"kind": "model", "a": "A", "b": "", "label": "A"}, cfg)
    assert pair["primary"] == "A vs B" and model["primary"] == "A review"
    topic = g.keyword_plan({"kind": "topic", "a": "", "b": "", "label": "Coding Agent"}, cfg)
    assert topic["primary"] == "best AI model for coding agent"


def test_keywords_drop_the_build_date():
    plan = g.keyword_plan({"kind": "model", "a": "DeepSeek V4 Flash 0423", "b": "",
                           "label": "DeepSeek V4 Flash 0423"}, g.load_keywords())
    assert plan["primary"] == "DeepSeek V4 Flash review"
    assert plan["subject"] == ["DeepSeek V4 Flash"]
    assert all("0423" not in k for k in plan["secondary"])


def test_every_seeded_experience_names_its_source_and_date():
    entries = g.load_experiences()
    assert entries and all(e["source"] and e["date"] and e["said"] for e in entries)


def test_notes_follow_the_model_and_its_dated_builds():
    entries = [{"id": "x", "date": "2026-10-01", "source": "s", "said": "we did it",
                "models": ["deepseek/deepseek-v4-flash"], "topics": []}]
    post = {"subject": ["deepseek/deepseek-v4-flash-0731"],
            "plan": {"subject": "DeepSeek V4 Flash 0731"}}
    assert g.experiences_for(post, entries) == entries
    other = {"subject": ["openai/gpt-6-sol"], "plan": {"subject": "GPT-6 Sol"}}
    assert g.experiences_for(other, entries) == []


def test_the_brief_gains_keywords_notes_and_trending():
    post = {"brief": "SUBJECT: x.", "subject": ["deepseek/deepseek-v4-flash"],
            "plan": {"subject": "DeepSeek V4 Flash"},
            "names": {"kind": "model", "a": "DeepSeek V4 Flash", "b": "",
                      "label": "DeepSeek V4 Flash"}}
    g.add_search_and_experience(post, ["Tool calling", "Latency"])
    assert "PRIMARY KEYWORD: DeepSeek V4 Flash review" in post["brief"]
    assert post["seo"]["subject"] == ["DeepSeek V4 Flash"]
    assert "WHAT WE TRIED" in post["brief"] and post["experience_text"]
    assert "TRENDING IN RECENT REPORTS: Tool calling; Latency" in post["brief"]
    assert post["seo"]["primary"] == "DeepSeek V4 Flash review"


def test_a_post_with_no_matching_note_gets_no_first_person_licence():
    post = {"brief": "", "subject": ["openai/gpt-6-sol"], "plan": {"subject": "GPT-6 Sol"}}
    g.add_search_and_experience(post)
    assert post["experience_text"] == "" and "WHAT WE TRIED" not in post["brief"]


def test_trending_reads_recent_non_declined_entries():
    class Cur:
        def execute(self, sql, params):
            self.sql, self.params = sql, params

        def fetchall(self):
            return [{"name": "Tool calling"}, {"name": "Latency"}]

    cur = Cur()
    assert g.trending_terms(cur, 14, 2) == ["Tool calling", "Latency"]
    assert "declined" in cur.sql and cur.params == (14, 2)


# ── the instructions say it ───────────────────────────────────────────────────


def test_the_prompt_asks_for_the_voice_first_person_and_search():
    assert "FIRST PERSON" in g.SYSTEM and "SEARCH" in g.SYSTEM
    assert "Take positions" in g.SYSTEM and "Never invent something we did" in g.SYSTEM
    assert "faq" in g.TOOL["function"]["parameters"]["required"]
    fmt = g.load_formats()["formats"][0]
    assert "`faq`" in g.system_for(dict(fmt, prose=g.load_formats()["prose"]))


def test_the_description_and_keywords_reach_the_page():
    src = (g.ROOT / "generate_sample_blogs.py").read_text(encoding="utf-8")
    assert '"description": GUILLEMET.sub' in src and '"keywords": [k for k in' in src
    pages = (g.ROOT / "web" / "src" / "seo" / "pages.js").read_text(encoding="utf-8")
    assert "usable(post.description) || usable(post.dek)" in pages


# ── which discussions a post is written from ──────────────────────────────────

def _row(i, models, entries, themes, neg=0, days_ago=1):
    from datetime import datetime, timedelta
    return {"id": f"t{i}", "models": models, "entries": entries, "themes": themes,
            "negatives": neg, "positives": entries - neg,
            "newest": datetime(2026, 10, 1) - timedelta(days=days_ago),
            "flattened_text_ref": f"r{i}", "source": "devto"}


SEL = {"per_post": 10, "min_entries": 3, "min_threads": 5, "disagreement_threads": 2}


def test_depth_about_the_subject_outranks_breadth():
    passing = _row(1, 2, 2, 9)            # names both models, 2 entries: a passing mention
    deep = _row(2, 1, 14, 3)              # one model, 14 entries
    both = _row(3, 2, 6, 2)
    rows = [passing, deep, both] + [_row(10 + i, 1, 4, 1) for i in range(4)]
    ranked, summary = g.rank_threads(rows, SEL)
    ids = [r["id"] for r in ranked]
    assert ids[0] == "t3" and ids[1] == "t2"          # both models first, then depth
    assert "t1" not in ids and summary["passing_mentions_set_aside"] == 1


def test_the_floor_relaxes_when_too_few_threads_and_says_so():
    ranked, summary = g.rank_threads([_row(1, 2, 2, 1), _row(2, 1, 1, 1)], SEL)
    assert len(ranked) == 2 and summary["floor_relaxed"] is True


def test_recency_breaks_ties_not_an_internal_id():
    old, new = _row(1, 1, 5, 2, days_ago=30), _row(2, 1, 5, 2, days_ago=1)
    ranked, _ = g.rank_threads([old, new] + [_row(9 + i, 1, 3, 1) for i in range(4)], SEL)
    assert [r["id"] for r in ranked][:2] == ["t2", "t1"]


def test_the_agreement_map_marks_splits_and_agreement():
    class Cur:
        def execute(self, sql, params):
            self.sql = sql

        def fetchall(self):
            def r(theme, name, model, polarity, n):
                return {"theme": theme, "name": name, "model": model, "polarity": polarity, "n": n}
            return [r("tool-use", "Tool use", "Alpha", "positive", 3),
                    r("tool-use", "Tool use", "Alpha", "negative", 2),
                    r("cost", "Cost", "Alpha", "positive", 2),
                    r("cost", "Cost", "Beta", "positive", 1)]

    post = {"where": "mv.canonical_id = ANY(%(subject)s)", "subject": ["a"]}
    out = g.agreement_map(Cur(), post, [{"thread_context_id": "t1"}])
    assert "Tool use - SPLIT - Alpha: 3 positive, 2 negative, 0 neutral" in out
    assert "Cost - AGREE" in out


def test_neutral_only_is_not_agreement():
    class Cur:
        def execute(self, sql, params):
            pass

        def fetchall(self):
            return [{"theme": "x", "name": "Exam", "model": "Alpha", "polarity": "neutral", "n": 3}]

    out = g.agreement_map(Cur(), {"where": "true", "subject": []}, [{"thread_context_id": "t"}])
    assert "Exam - NEUTRAL" in out


def test_engineers_are_quoted_from_three_discussions():
    docs = ["alpha said it never broke", "beta said it broke twice", "gamma liked the price"]
    two = {"sections": [{"heading": "h", "paragraphs": ["«it never broke» but «it broke twice»."]}]}
    assert g.voices_violations(two, docs)
    three = {"sections": [{"heading": "h", "paragraphs": [
        "«it never broke» but «it broke twice», and «liked the price»."]}]}
    assert g.voices_violations(three, docs) == []


def test_discussions_are_not_counted_in_prose():
    import re
    assert any(why == "counts people or reports"
               and re.search(pat, "across 4 discussions", re.I) for pat, why in g.BANNED)


def test_head_to_head_headings_are_statements_now():
    fmt = next(f for f in g.load_formats()["formats"] if f["key"] == "head-to-head")
    assert not fmt.get("headings_end_with_question")
    assert g.rules_for(fmt)["heading_no_wh"] is True


def test_the_faq_is_not_also_written_as_a_section():
    dup = _seo_essay(sections=[{"heading": "FAQ", "paragraphs": [
        "We agree with the teams that pin a provider. We are not convinced it wins."]}])
    assert any("belong in `faq` only" in x for x in g.seo_violations(dup, SEO))
