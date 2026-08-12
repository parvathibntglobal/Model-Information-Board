"""collect/ — Engineer 1.

Registry, harvest, assemble, triage, ops. This lane never calls a language
model. It fills `document`, `thread_context`, `author`, `model_version` and
`model_alias`; `judge/` reads them and nothing flows back.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
