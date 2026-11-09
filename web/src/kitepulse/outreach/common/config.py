"""Load a platform's outreach YAML files (its own `config/` folder).

Every value the Finder uses comes from these files and has no default in code:
a missing key raises `ConfigError` rather than falling back to a value nobody
chose (CLAUDE.md rule 12). The folder has no default either; each platform
passes its own, so one platform can never read another's settings by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VENDOR_REPLY_STATES = ("allowed", "pending_review", "not_allowed")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Query:
    problem: str
    phrase: str


@dataclass(frozen=True)
class Community:
    key: str
    name: str
    vendor_replies: str
    rules_url: str


@dataclass(frozen=True)
class Pace:
    max_thread_age_days: int
    team_accounts: tuple[str, ...]


def _load(name: str, config_dir: Path) -> dict[str, Any]:
    path = config_dir / name
    if not path.is_file():
        raise ConfigError(f"missing config file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return data


def _require(mapping: Any, key: str, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping:
        raise ConfigError(f"{where}: missing key {key!r}")
    return mapping[key]


def names(filename: str, key: str, config_dir: Path) -> list[str]:
    """A required, non-empty list of non-empty strings, e.g. dev.to's tags."""
    values = _require(_load(filename, config_dir), key, filename)
    if not isinstance(values, list) or not values:
        raise ConfigError(f"{filename}: {key!r} must be a non-empty list")
    if not all(isinstance(v, str) and v.strip() for v in values):
        raise ConfigError(f"{filename}: every entry of {key!r} must be a non-empty string")
    return [v.strip() for v in values]


def queries(source: str, config_dir: Path) -> list[Query]:
    """Every (problem, phrase) pair for one source, in file order."""
    problems = _require(_load("queries.yaml", config_dir), "problems", "queries.yaml")
    out: list[Query] = []
    for problem, body in problems.items():
        phrases = _require(body, "phrases", f"queries.yaml: {problem}")
        for phrase in phrases.get(source) or ():
            if not isinstance(phrase, str) or not phrase.strip():
                raise ConfigError(f"queries.yaml: {problem}: empty phrase for {source}")
            out.append(Query(problem=problem, phrase=phrase.strip()))
    return out


def _all_communities(config_dir: Path) -> dict[str, Any]:
    entries = _require(_load("communities.yaml", config_dir), "communities", "communities.yaml")
    if not isinstance(entries, dict) or not entries:
        raise ConfigError("communities.yaml: 'communities' must be a non-empty mapping")
    return entries


def communities(config_dir: Path) -> list[Community]:
    """Every community in the file, in file order (Discourse: one per forum)."""
    return [community(key, config_dir) for key in _all_communities(config_dir)]


def community(key: str, config_dir: Path) -> Community:
    entry = _require(_all_communities(config_dir), key, "communities.yaml")
    state = _require(entry, "vendor_replies", f"communities.yaml: {key}")
    if state not in VENDOR_REPLY_STATES:
        raise ConfigError(
            f"communities.yaml: {key}: vendor_replies must be one of "
            f"{', '.join(VENDOR_REPLY_STATES)}, got {state!r}"
        )
    return Community(
        key=key,
        name=_require(entry, "name", f"communities.yaml: {key}"),
        vendor_replies=state,
        rules_url=_require(entry, "rules_url", f"communities.yaml: {key}"),
    )


def pace(source: str, config_dir: Path) -> Pace:
    data = _load("pace.yaml", config_dir)
    days = _require(data, "max_thread_age_days", "pace.yaml")
    if not isinstance(days, int) or days < 1:
        raise ConfigError(
            f"pace.yaml: max_thread_age_days must be a positive integer, got {days!r}"
        )
    team = _require(data, "team_accounts", "pace.yaml")
    accounts = _require(team, source, "pace.yaml: team_accounts")
    return Pace(max_thread_age_days=days, team_accounts=tuple(accounts or ()))
