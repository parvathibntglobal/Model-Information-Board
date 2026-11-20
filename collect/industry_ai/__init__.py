"""The Industry AI agent's collect side: harvest, sieve, dedupe, filter, label.

A SEPARATE LANE from the model board (contract/industry_ai.yaml). It writes only
`iai_item` and `iai_run`, and calls no language model. judge/industry_ai/view.py
reads those two tables for the signed-in "AI in industries" page.
"""
