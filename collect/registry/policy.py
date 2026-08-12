"""Registry policy: values the code reads at runtime.

Rule 5 puts thresholds and filter rules in versioned YAML, not code. The
values below are the *proposed* contents of `contract/registry.yaml`, held
here as defaults only until that file is signed off. `load_registry_policy`
reads the contract file the moment it exists, so approving the proposal takes
effect with no code change.

Anything added here must be a value the pipeline reads while running. An
interpreter version is not one: by the time this module is imported, that
question is already answered, so the Python pin lives in `pyproject.toml`
where the tooling reads it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from collect.config import CONTRACT_DIR

REGISTRY_YAML = CONTRACT_DIR / "registry.yaml"


@dataclass(frozen=True)
class AliasSearchPolicy:
    """Which alias rows turn into harvest queries (FR-7, FR-11).

    Search eligibility and attribution eligibility are separate questions.
    **Every alias row stays attribution-eligible**, always: an exact mention
    of `anthropic/claude-haiku-4-5-20251001` in a pasted config has to resolve
    at snapshot specificity, and dropping that row would lose a claim.
    Whether that same string is worth spending a search query on is a
    different question, and the answer is no.
    """

    #: Only surfaces hand-written in `seed_models.yaml` become queries. The
    #: canonical id and its local part are added automatically so an exact
    #: mention resolves; nobody types them into a Reddit post.
    declared_surfaces_only: bool = True

    #: Re-expand each declared surface into spacing and hyphenation forms.
    #: Off, because the variant list in the contract file is already
    #: hand-curated spelling coverage, and expanding it again multiplies the
    #: query budget without adding a string a human would type.
    expand_mechanically: bool = False


#: Where a loaded policy came from. NFR-10's acceptance is that changing a
#: threshold needs no code deploy and produces a version diff. Defaults in
#: code satisfy that test today and stop satisfying it the moment somebody
#: edits a default instead of the YAML, so the origin is recorded and
#: checked rather than assumed.
CONTRACT = "contract"
DEFAULTS = "defaults"


@dataclass(frozen=True)
class RegistryPolicy:
    #: FR-1: the trailing window a model must fall inside to be listed.
    in_window_months: int = 18

    alias_search: AliasSearchPolicy = AliasSearchPolicy()

    #: `contract` or `defaults`. Compared, not decorative: see
    #: `collect.registry.assertions.assert_contract_backed`.
    source: str = DEFAULTS

    #: The file the values came from, for the coverage surface to display.
    source_path: str | None = None


DEFAULT_POLICY = RegistryPolicy()

log = logging.getLogger(__name__)


def load_registry_policy(path: Path | None = None) -> RegistryPolicy:
    """Read `contract/registry.yaml`, falling back to the built-in defaults.

    The fallback exists so this lane can be developed before the contract
    change lands. It is a hazard rather than a convenience, so every load
    says out loud which source it used, and `assert_contract_backed` refuses
    to start on defaults outside development.
    """
    path = path or REGISTRY_YAML
    if not path.exists():
        log.warning(
            "registry policy: %s not found, using built-in defaults. "
            "Production refuses to start in this state.",
            path,
        )
        return DEFAULT_POLICY

    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} does not contain a YAML mapping")

    search = raw.get("alias_search") or {}
    if not isinstance(search, dict):
        raise ValueError(f"{path}: alias_search must be a mapping")

    log.info("registry policy: loaded from %s (version %s)", path, raw.get("version", "?"))
    return replace(
        DEFAULT_POLICY,
        source=CONTRACT,
        source_path=str(path),
        in_window_months=int(raw.get("in_window_months", DEFAULT_POLICY.in_window_months)),
        alias_search=replace(
            DEFAULT_POLICY.alias_search,
            declared_surfaces_only=bool(
                search.get(
                    "declared_surfaces_only",
                    DEFAULT_POLICY.alias_search.declared_surfaces_only,
                )
            ),
            expand_mechanically=bool(
                search.get(
                    "expand_mechanically", DEFAULT_POLICY.alias_search.expand_mechanically
                )
            ),
        ),
    )
