"""LiteLLM's community price list -> `unit_price` rows, as a fallback only.

#602 items 3 and 4. `contract/litellm_prices.yaml` holds every decision; this
module applies it and reports everything it did not do.

WHAT IT REFUSES, AND SAYS SO IN THE REPORT
  - a model OpenRouter already prices (`skipped_priced`): the fallback is only
    for "price not published", so the two sources never disagree on a model;
  - a mapped key LiteLLM no longer lists (`missing_keys`): no nearest name is
    tried in its place (rule 12);
  - an entry whose `mode` is not one the contract reads (`wrong_mode`);
  - a cost field the contract has no unit for (`unread_fields`);
  - a zero (`zero_fields`): in this file 0 means "not charged this way" as
    often as "free", so it is not stored as a price (rule 6).
And it names every unpriced model the map does not cover (`unmapped`), so
"no price" on the page is a state somebody can see the reason for.

NO DATABASE HERE. The script (`scripts/load_litellm_prices.py`) reads which
models are unpriced, calls `rows_from`, and writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

CONTRACT = Path(__file__).resolve().parents[2] / "contract" / "litellm_prices.yaml"
SOURCE = "litellm"

#: A resolution tier on a per-second field: `_720p`, `_1080p`, `_4k`, `_2k`.
_TIER = re.compile(r"^\d+(?:p|k)$")


class LitellmContractError(ValueError):
    """`contract/litellm_prices.yaml` is missing a key or has a wrong shape."""


@dataclass(frozen=True)
class LitellmContract:
    source_url: str
    fields: dict[str, tuple[str, str]]
    modes: frozenset[str]
    models: dict[str, str]
    excluded: dict[str, str]


def load_contract(path: Path | None = None) -> LitellmContract:
    raw = yaml.safe_load((path or CONTRACT).read_text(encoding="utf-8")) or {}
    for key in ("source_url", "fields", "modes", "models", "excluded"):
        if key not in raw:
            raise LitellmContractError(f"litellm_prices.yaml has no `{key}`")
    fields: dict[str, tuple[str, str]] = {}
    for name, spec in (raw["fields"] or {}).items():
        if not isinstance(spec, dict) or not {"unit", "direction"} <= set(spec):
            raise LitellmContractError(f"field {name!r} needs `unit` and `direction`")
        fields[str(name)] = (str(spec["unit"]), str(spec["direction"]))
    models = {str(k): str(v) for k, v in (raw["models"] or {}).items()}
    excluded = {str(k): str(v) for k, v in (raw["excluded"] or {}).items()}
    both = sorted(set(models) & set(excluded))
    if both:
        raise LitellmContractError(f"mapped and excluded at once: {both}")
    return LitellmContract(
        source_url=str(raw["source_url"]),
        fields=fields,
        modes=frozenset(str(m) for m in raw["modes"] or ()),
        models=models,
        excluded=excluded,
    )


@dataclass(frozen=True)
class UnitPriceRow:
    canonical_id: str
    unit: str
    direction: str
    variant: str
    usd: float
    source_key: str
    source_url: str
    retrieved_at: datetime
    source: str = SOURCE


@dataclass
class LoadReport:
    rows: list[UnitPriceRow] = field(default_factory=list)
    skipped_priced: list[str] = field(default_factory=list)
    missing_keys: dict[str, str] = field(default_factory=dict)
    wrong_mode: dict[str, str] = field(default_factory=dict)
    unread_fields: dict[str, list[str]] = field(default_factory=dict)
    zero_fields: dict[str, list[str]] = field(default_factory=dict)
    unmapped: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    #: Cost fields of one entry that map to the SAME (unit, direction, variant):
    #: two figures for one price. Neither is stored; both are named (#612 review).
    collisions: dict[str, list[str]] = field(default_factory=dict)

    @property
    def priced_models(self) -> list[str]:
        return sorted({r.canonical_id for r in self.rows})

    def summary(self) -> str:
        lines = [
            f"litellm  : {len(self.rows)} row(s) for {len(self.priced_models)} model(s)",
            f"           skipped, OpenRouter already prices them: {len(self.skipped_priced)}",
            f"           unpriced and not mapped (page shows no price): {len(self.unmapped)}"
            + (f" - {', '.join(self.unmapped)}" if self.unmapped else ""),
            f"           excluded by name: {len(self.excluded)}",
        ]
        for label, part in (
            ("MAPPED KEY NOT IN THE FILE", self.missing_keys),
            ("WRONG MODE, NOT READ", self.wrong_mode),
            ("cost fields with no unit, not stored", self.unread_fields),
            ("zero figures, not stored", self.zero_fields),
            ("TWO FIELDS FOR ONE PRICE, neither stored", self.collisions),
        ):
            if part:
                lines.append(f"           {label}: "
                             + "; ".join(f"{k}: {v}" for k, v in sorted(part.items())))
        return "\n".join(lines)


def _field_unit(name: str, fields: dict[str, tuple[str, str]]) -> tuple[str, str, str] | None:
    """(unit, direction, variant) for a LiteLLM cost field, or None if unread."""
    if name in fields:
        return (*fields[name], "default")
    for base, (unit, direction) in fields.items():
        if name.startswith(base + "_") and _TIER.match(name[len(base) + 1:]):
            return unit, direction, name[len(base) + 1:]
    return None


def rows_from(
    prices: dict[str, Any],
    contract: LitellmContract,
    *,
    unpriced: set[str],
    priced: set[str],
    retrieved_at: datetime,
) -> LoadReport:
    """The rows to write, and every refusal by name.

    `unpriced`: catalogue ids whose OpenRouter price is "not published".
    `priced`: catalogue ids OpenRouter prices. A mapped id in neither is not in
    the catalogue at all, and is reported as a missing key's sibling - it is
    not priced from a list nobody can link to.
    """
    report = LoadReport(excluded={k: v for k, v in contract.excluded.items() if k in unpriced})
    for cid in sorted(unpriced):
        if cid not in contract.models and cid not in contract.excluded:
            report.unmapped.append(cid)
    for cid, key in sorted(contract.models.items()):
        if cid in priced:
            report.skipped_priced.append(cid)
            continue
        if cid not in unpriced:
            report.missing_keys[cid] = "not in model_catalog's latest listing"
            continue
        entry = prices.get(key)
        if not isinstance(entry, dict):
            report.missing_keys[cid] = key
            continue
        mode = entry.get("mode")
        if mode not in contract.modes:
            report.wrong_mode[cid] = f"{key} has mode {mode!r}"
            continue
        # ONE FIGURE PER (unit, direction, variant). Two cost fields mapping to
        # the same slot would give two rows for one price, and picking either
        # would be a guess, so both are refused and named.
        slots: dict[tuple[str, str, str], list[str]] = {}
        for name in entry:
            spec = _field_unit(name, contract.fields) if "cost" in name else None
            if spec is not None:
                slots.setdefault(spec, []).append(name)
        clashing = {n for names in slots.values() if len(names) > 1 for n in names}
        if clashing:
            report.collisions[cid] = sorted(clashing)
        for name, value in sorted(entry.items()):
            if name in clashing:
                continue
            if "cost" not in name:
                continue
            spec = _field_unit(name, contract.fields)
            if spec is None:
                report.unread_fields.setdefault(cid, []).append(name)
                continue
            try:
                usd = float(value)
            except (TypeError, ValueError):
                report.unread_fields.setdefault(cid, []).append(name)
                continue
            if usd <= 0:
                report.zero_fields.setdefault(cid, []).append(name)
                continue
            unit, direction, variant = spec
            report.rows.append(UnitPriceRow(
                canonical_id=cid, unit=unit, direction=direction, variant=variant,
                usd=usd, source_key=key, source_url=contract.source_url,
                retrieved_at=retrieved_at,
            ))
    return report
