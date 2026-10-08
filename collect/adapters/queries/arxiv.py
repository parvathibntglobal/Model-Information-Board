"""Render one model-name surface as an arXiv `search_query`.

WHY THIS EXISTS (2026-10-07). `scripts/fetch_model.py` passed the bare name -
`DeepSeek V4` - as the search_query. arXiv reads unprefixed words as separate
terms, so that matched any paper containing any of them: measured 10,275 hits
for "DeepSeek V4" against 169 for the quoted phrase in title or abstract, and
the run fetched the five NEWEST of the 10,275, which were mostly about neither.

THE RENDERING: the name as a quoted PHRASE, in the title OR the abstract.

    ti:"DeepSeek V4" OR abs:"DeepSeek V4"

That is what someone searching by hand does, and it is where a paper names a
model it evaluated. `all:` adds the comments and journal-reference fields and
measured within two papers of this (171 against 169), so the narrower form is
kept.

NO CATEGORY FILTER, MEASURED RATHER THAN ASSUMED (rule 8). Restricting to a
list of cs.* categories was considered and measured on 2026-10-07: for "DeepSeek
V4" it dropped 14 of 169 papers, among them "DeepSeek-V4-Flash on AMD gfx90a:
Correctness Recovery and Inference Performance" (cs.DC), and for "GPT-5" it
dropped "Mathematical research with GPT-5" (math.PR) and several cs.CY studies.
The phrase match is the precision; a category gate would mostly lose evidence.
A paper's categories are a candidate WEIGHT, never a filter, until a filter's
error rate is measured against a population it did not choose.
"""
from __future__ import annotations


def arxiv_query(surface: str) -> str:
    """`ti:"<surface>" OR abs:"<surface>"` for one name surface.

    A double quote inside the name would end the phrase early, so it is
    dropped; whitespace is collapsed. An empty name raises rather than becoming
    a query that matches everything (rule 12).
    """
    name = " ".join(str(surface or "").replace('"', " ").split())
    if not name:
        raise ValueError("an arXiv query needs a non-empty model name")
    return f'ti:"{name}" OR abs:"{name}"'
