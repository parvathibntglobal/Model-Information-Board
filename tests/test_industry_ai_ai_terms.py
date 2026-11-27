"""The AI term list (768 terms since 2026-11-27) and the matcher that reads it.

Pins:
  * every AI term matches a sentence that names it, so no term is dead on arrival
    (a term ending in ".ai" would be: `global_exclude_phrases` removes ".ai" first);
  * no two terms differ only in case (the matcher folds case, so one is redundant);
  * the first-word pre-filter in `ai_terms_found` gives the same terms, in the same
    order, as asking every term, on strings built to break it;
  * the eight terms dropped after the 2026-11-27 hand-check stay out, and words that
    were judged too ambiguous to add do not match on their own.
The list's sources and method: docs/measurements/ai-terms-2026-11-27.md.
"""

from __future__ import annotations

import pytest

from collect.industry_ai import config as iai_config
from collect.industry_ai.rules import ai_terms_found, has_term, remove


@pytest.fixture(scope="module")
def cfg():
    return iai_config.load()


def _every_term(text: str, cfg) -> list[str]:
    """The answer without the pre-filter: every term asked, in list order."""
    clean = remove(text, cfg.global_exclude)
    return [t for t in cfg.all_ai_terms if has_term(clean, t)]


def test_every_ai_term_matches_a_sentence_naming_it(cfg):
    dead = [t for t in cfg.ai_terms
            if t not in ai_terms_found(f"Yesterday I tried {t} for work.", cfg)]
    assert dead == [], f"AI terms that cannot match a sentence naming them: {dead}"


def test_no_ai_term_ends_in_dot_ai(cfg):
    assert [t for t in cfg.ai_terms if t.lower().endswith(".ai")] == []


def test_no_two_ai_terms_differ_only_in_case(cfg):
    seen: dict[str, str] = {}
    dupes = []
    for t in cfg.ai_terms:
        k = t.lower()
        if k in seen:
            dupes.append((seen[k], t))
        seen[k] = t
    assert dupes == []


TRICKY = [
    "",
    "   ",
    "C++ and C# are not AI, but GPT-4o is.",
    "pip install huggingface_hub then push to the Hugging Face Hub",
    "HUGGINGFACE-HUB, hugging face hub, Hugging-Face_Hub",
    "DALL·E Mini made this; dall·e mini too",
    "Humanity’s Last Exam and Humanity's Last Exam",
    "Flux.1 Kontext vs flux.1-kontext",
    "We fine-tuned with QLoRA, scored on GSM8K and gsm8k, traced in LangSmith.",
    "scikit-learn / scikit_learn / scikit learn",
    "My site is evolving.ai and the file is logo.ai",
    "Group Relative Policy Optimization (GRPO) beat PPO",
    "k-means, K-Means clustering and KNN",
    "été Stable Diffusion über ChatGPT — 人工智能 AI",
    "_LangChain_ and __Ollama__ and #Claude and @OpenAI",
    "x" * 500 + " ai " + "y" * 500,
]


@pytest.mark.parametrize("text", TRICKY)
def test_prefilter_gives_the_same_terms_as_asking_every_term(text, cfg):
    assert ai_terms_found(text, cfg) == _every_term(text, cfg)


def test_prefilter_matches_every_term_in_every_spelling(cfg):
    """Each term upper-cased, lower-cased and with its spaces as hyphens, in one text
    per group of 25 so terms sit beside each other as they do in a post."""
    terms = list(cfg.ai_terms)
    for i in range(0, len(terms), 25):
        group = terms[i:i + 25]
        for spell in (str.upper, str.lower, lambda t: t.replace(" ", "-")):
            text = " , ".join(spell(t) for t in group)
            assert ai_terms_found(text, cfg) == _every_term(text, cfg), group


DROPPED_AFTER_CHECK = ["Make-A-Video", "active learning", "evals", "synthetic data",
                       "cross-validation", "pre-training", "Pretraining", "Agent Skills"]


def test_terms_dropped_after_the_hand_check_stay_out(cfg):
    listed = {t.lower() for t in cfg.ai_terms}
    assert [t for t in DROPPED_AFTER_CHECK if t.lower() in listed] == []


@pytest.mark.parametrize("text", [
    "Students sit their evals next week, then active learning in class.",
    "I want to make a video of the bolt and the cursor on my whisper-quiet fan.",
    "Pre-training camp starts Monday; the agent skills course is for insurance agents.",
    "We used synthetic data fixtures and cross-validation of the invoices.",
])
def test_words_judged_too_ambiguous_name_no_ai_term(text, cfg):
    assert ai_terms_found(text, cfg) == []
