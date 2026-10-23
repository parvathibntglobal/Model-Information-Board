"""The evidence feed (PROPOSED 2026-10-21): the reports behind every count.

    items       the read path: a model's reports, the count's own population
    paraphrase  one paraphrase per report, stored once code checks its shape
    summary     one page per model, stored pending until a person approves it
    checks      what code checks in both, and why it cannot check more
    llm         the one model call both make

Settings: contract/evidence_feed.yaml. Publication terms: contract/
publication.yaml `evidence_feed`. Rule 2: docs/proposals/evidence-feed.md.
"""
