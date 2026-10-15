"""Style problems are advisory after one repair; integrity problems still fail.

Team decision 2026-10-13, on cost: 10 of 30 runs that day failed with only
style left, and 23% of writing spend paid for style-only repairs.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import generate_sample_blogs as g  # noqa: E402

STYLE = [
    "paragraphs: 9 of 24 open with 'the'; reopen at least 1 of these differently: ...",
    "vocabulary: 'whether' used 3 times (at most 2); rewrite 1 of these without it: ...",
    "vocabulary: the stock phrase 'not proof that' is refused; say it another way",
    "rhythm: 11 of 33 longer paragraphs have a sentence of 8 words or fewer",
    "sentences: the median is 16 words; keep it at 15 or under",
    "sections[2].paragraphs[1]: a sentence of 37 words (limit 30); split it: ...",
    "the post reads as 1767 words (~8 min); write 1,850 to 3,450",
    "prices recited 4 times in prose ('per million'); the rate card shows them",
    "sections[6]: needs 3 to 5 paragraphs, has 6",
    "sections[6].paragraphs[1]: refers to its inputs: 'the discussions'",
]

INTEGRITY = [
    "sections[1].paragraphs[0]: «a fantastic coder» is not verbatim in any discussion",
    "sections[0].paragraphs[0]: the number 42 appears in no discussion and not in the fact sheet",
    "sections[0].paragraphs[0]: «very fast» copies the words of a Reddit post (discussion 1).",
    "sections[0].paragraphs[0]: credits practitioners ('one engineer') without a «verbatim»",
    "sections[0].paragraphs[0]: writes a handle, subreddit or link - the embed shows those: 'u/x'",
    "embeds: 0; embed 1 to 4 of the EMBED ONLY discussions (1, 3)",
    "sections[0].paragraphs[0]: counts people or reports: '2 threads'",
    "sections[0].paragraphs[0]: a score out of 10 or 100: '8/10'",
    "a message nobody has classified yet",
]


def test_style_rules_are_recognised():
    assert [v for v in STYLE if not g.is_style(v)] == []


def test_integrity_rules_and_unknown_messages_are_never_style():
    assert [v for v in INTEGRITY if g.is_style(v)] == []


def test_style_gets_one_repair_round():
    assert g.STYLE_REPAIRS == 1
