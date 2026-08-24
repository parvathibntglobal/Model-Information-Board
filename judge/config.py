"""Read the shared contract.

`contract/` is the interface between two engineers. This module reads it and
never writes to it — changes there go through a PR (see CLAUDE.md).

Loaded once at import and cached. These files change perhaps five times in
eight weeks, so re-reading per request buys nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

CONTRACT_DIR = Path(__file__).resolve().parent.parent / "contract"

FailureMode = Literal["silent", "loud"]


@dataclass(frozen=True)
class Capability:
    """One entry from contract/capabilities.yaml."""

    key: str
    failure_mode: FailureMode
    description: str
    sounds_like: tuple[str, ...]

    @property
    def fails_silently(self) -> bool:
        """Silent failures require POSITIVE consensus, not merely absence of criticism.

        Loud failures error in seconds and a validation retry is a real
        mitigation, so weaker evidence is acceptable. This distinction decides
        how much evidence the answer path demands, and it matters more than how
        difficult the task is.
        """
        return self.failure_mode == "silent"


@dataclass(frozen=True)
class ConditionDimension:
    """One entry from contract/conditions.yaml."""

    key: str
    bands: tuple[str, ...]
    description: str


@lru_cache(maxsize=1)
def capabilities() -> dict[str, Capability]:
    raw = _read("capabilities.yaml")
    out: dict[str, Capability] = {}
    for entry in raw["capabilities"]:
        cap = Capability(
            key=entry["key"],
            failure_mode=entry["failure_mode"],
            description=entry.get("description", "").strip(),
            sounds_like=tuple(entry.get("sounds_like", ())),
        )
        out[cap.key] = cap
    return out


@lru_cache(maxsize=1)
def conditions() -> dict[str, ConditionDimension]:
    raw = _read("conditions.yaml")
    return {
        entry["key"]: ConditionDimension(
            key=entry["key"],
            bands=tuple(entry["bands"]),
            description=entry.get("description", "").strip(),
        )
        for entry in raw["dimensions"]
    }


@lru_cache(maxsize=1)
def dominant_dimension() -> dict[str, str]:
    """Which condition dimension forms the bucket key for each capability.

    A 12-tool task looks up `tools:6-15`, never the model's flattering average.
    """
    return dict(_read("conditions.yaml")["dominant_dimension"])


#: Vendor spellings of the same tier, folded onto the bands in
#: contract/conditions.yaml. Extraction can only produce the band names
#: themselves (`Conditions.reasoning_effort` is a Literal), so this exists for
#: every other writer - seeds, backfills, and whatever a human types.
_EFFORT_ALIASES: dict[str, str] = {
    "off": "off", "none": "off", "minimal": "off", "no-thinking": "off",
    "low": "low",
    "medium": "medium", "med": "medium", "default": "medium",
    "high": "high",
    "max": "max", "xhigh": "max", "highest": "max", "maximum": "max",
    "auto": "auto", "dynamic": "auto", "router": "auto", "auto mode": "auto",
}


def band_for(dimension: str, value: int | bool | str | None) -> str:
    """Place a raw value into its fixed band.

    Bands are fixed rather than continuous because buckets must be countable —
    "fine under 5 tools, breaks above 10" only exists if the buckets are
    discrete. An unknown value is honest: it becomes `unknown` rather than
    being guessed into a band.
    """
    if value is None:
        return "unknown"

    if dimension == "tool_count":
        n = int(value)
        if n == 0:
            return "none"
        if n <= 5:
            return "1-5"
        if n <= 15:
            return "6-15"
        return "16+"

    if dimension == "context_size":
        n = int(value)
        if n < 8_000:
            return "<8k"
        if n < 32_000:
            return "8k-32k"
        if n < 128_000:
            return "32k-128k"
        return "128k+"

    if dimension == "schema_enforced":
        return "on" if value else "off"

    if dimension == "reasoning_effort":
        band = _EFFORT_ALIASES.get(str(value).strip().lower())
        if band is None:
            # DELIBERATELY LOUD. Mapping an unrecognised effort to `unknown`
            # would turn a value somebody actually reported into missing data,
            # which is rule 6 pointed the wrong way. `unknown` is what an
            # ABSENT value produces (the `value is None` branch above), and it
            # must stay the answer to one question only.
            raise ValueError(
                f"unrecognised reasoning_effort {value!r}. Add it to "
                f"_EFFORT_ALIASES, or to the bands in contract/conditions.yaml "
                f"if it is a new tier. Do not let it fall to 'unknown'."
            )
        return band

    raise ValueError(f"unknown condition dimension: {dimension!r}")


def bucket_for(capability_key: str, conditions_seen: dict[str, int | bool | None]) -> str:
    """Build the `condition_bucket` string for a capability.

    Format is `<dimension>:<band>` — e.g. `tool_count:6-15`.
    """
    dim = dominant_dimension()[capability_key]
    return f"{dim}:{band_for(dim, conditions_seen.get(dim))}"


def _read(name: str) -> dict:
    path = CONTRACT_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. contract/ is the shared interface — it should "
            "be present in every checkout."
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def evidence_tier_by_speaking() -> dict[str, str]:
    """`contract/harvest.yaml` -> {speaking value: evidence tier}.

    Returns `{}` when the block is absent rather than raising, because the
    refusal belongs in `compute()` where the missing input can be named
    alongside anything else that is missing. A raise here would report one gap
    per round trip.
    """
    block = _read("harvest.yaml").get("evidence_tier_by_speaking") or {}
    return {
        key: value
        for key, value in block.items()
        if isinstance(value, str) and not key.startswith("not_a_")
    }
