"""E1 — the registry.

Ground truth about every model: canonical id, aliases, prices, lifecycle,
context, feature flags, and for every one of those a source URL and the date
it was read (FR-2).

Seeded from `contract/seed_models.yaml` now; polled from week 5 into the same
tables, so the swap is a data-source change and not a rewrite.

**A social post may trigger a re-check here. It may never write here (FR-5).**
Nothing in this package imports from `collect.adapters`, `collect.assemble`
or `collect.triage`, and nothing here reads `document` or `claim`.
"""

from __future__ import annotations
