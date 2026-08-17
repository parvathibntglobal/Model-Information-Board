"""E1 — the OpenRouter model list, mapped to `model_version` and `price_tier`.

**This module does not touch the sweep.** It populates the registry and stops.
That boundary is deliberate and it is not a scheduling detail:

    900 daily request cap / 81.45 requests per model = 11 models a night.
    The feed carries 340. A full rotation would take 31 days, against a 30-day
    half-life on `ops.latency_ttft` - so the rotation loses to the decay curve
    and no `last_swept_at` fixes that.

So "which models do we track" is a decision, raised on #33, and the field it
turns on - `slot` - is not in the feed and is not in `contract/tables.sql`
either. A poller that fed 340 models into `plan_searches` would answer that
question by accident, at 30.8x the cap.

NO CREDENTIAL. Measured 2026-08-17: the endpoint returns HTTP 200
unauthenticated, 414 entries, 681 KB, and sends no rate-limit headers. If that
ever changes it gets its OWN variable rather than sharing `OPENROUTER_API_KEY`:
extraction spend is metered and registry reads are not, and NFR-3's budget
degrades to triage-only, so a shared key would let the extraction ceiling
throttle the registry. A stale registry is what makes evidence unattributable,
which is the opposite of what that ceiling is for.

WHAT THE FEED CANNOT SUPPLY, AND WHY THAT MATTERS MORE THAN IT SOUNDS
---------------------------------------------------------------------
`aliases`. `alias_rows` reads `model.aliases.surface` and `.variants`, and
`test_hand_written_variants_are_what_gets_searched` pins that what somebody
wrote in `contract/` is what gets issued. The feed gives
`anthropic/claude-opus-5` and `Anthropic: Claude Opus 5`. It does not give
`claude opus 5`, `opus 5`, `opus5`, `claude opus`, or the family surface `opus`.

**So this replaces the FACTS in `contract/seed_models.yaml` and not the SEARCH
SURFACE.** `alias_coverage` below reports the gap per model rather than leaving
it to be discovered when a sweep finds nothing.

SERVICE TIERS ARE NOT MODELS
----------------------------
`:batch`, `:free`, `:extended`, `:thinking` and `-fast` are the same model billed
or served differently. Counting them as models would multiply the registry - and
therefore the sweep - by billing tier. 414 feed entries are 340 models.

The `:batch` sibling is not discarded, though: its existence is the only evidence
in the feed that a model supports batching, and its price ratio is the discount.

RULE 6 IS THE WHOLE DIFFICULTY HERE
-----------------------------------
Five `supports_*` columns carry `DEFAULT false`. That default is exactly the
defect `CLAUDE.md` rule 6 cites - `judge/`'s hard filter read an absent
`supports_tools` as "cannot" and took a candidate list from 11 models to 1. So
every mapped row passes an explicit value or an explicit `None`, and `None` is
passed where the feed is silent rather than letting the default speak.

Coverage measured over 414 entries: `pricing.prompt` and `context_length` are
complete; `knowledge_cutoff` 194, `input_cache_read` 247, `hugging_face_id` 166,
`expiration_date` 4. Those four stay NULL where absent.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

log = logging.getLogger(__name__)

MODELS_URL = "https://openrouter.ai/api/v1/models"

#: Suffixes that mark a service tier rather than a distinct model.
TIER_SUFFIX = re.compile(r":(batch|free|extended|thinking|online|nitro|floor)$")
#: `-fast` is a latency tier on the same weights.
FAST_SUFFIX = re.compile(r"-fast$")

#: What `supported_parameters` has to contain for each capability flag. Absence
#: of the key means NULL, never False - the feed not listing `tools` is not the
#: provider saying tools are unsupported.
TOOL_PARAM = "tools"
STRUCTURED_PARAM = "structured_outputs"


def base_id(model_id: str) -> str:
    """The model behind a service tier. `anthropic/claude-opus-5:batch` -> …-5."""
    return FAST_SUFFIX.sub("", TIER_SUFFIX.sub("", model_id))


def _decimal(value: Any) -> float | None:
    """A price string to a float, or None. `"0"` is a real price, not absent."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _per_million(per_token: Any) -> float | None:
    """The feed prices per token; the schema stores USD per 1M tokens.

    A NEGATIVE PRICE IS A SENTINEL FOR UNKNOWN, AND STAYS UNKNOWN. OpenRouter's
    router pseudo-models — `openrouter/auto`, `fusion`, `bodybuilder`,
    `pareto-code` and `auto-beta` — price at `-1` per token, meaning "depends
    which model this routes to". Multiplied out that is -1,000,000 USD per
    million tokens, which overflows `numeric(12,6)` and would, in a wider column,
    store a negative price as fact.

    So it returns None. Rule 6, in the form the rule names: a sentinel meaning
    "not published" must not become a definite value. Found by a live poll; the
    captured fixture slice did not contain one until it was added deliberately.
    """
    value = _decimal(per_token)
    if value is None:
        return None
    if value < 0:
        return None
    return value * 1_000_000


def _date_of(value: Any) -> date | None:
    """An epoch or an ISO string to a date, or None. Never today's date."""
    if value in (None, "", 0):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC).date()
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


@dataclass(frozen=True)
class PolledModel:
    """One `model_version` row, with absent fields absent.

    Every field the feed does not state is None. Nothing here is inferred into a
    definite value, and the two that ARE derived say so in `sources`.
    """

    canonical_id: str
    provider: str
    display_name: str | None
    release_date: date | None
    retirement_date: date | None
    knowledge_cutoff: date | None
    advertised_context: int | None
    max_output_tokens: int | None
    price_in: float | None
    price_out: float | None
    price_cached_read: float | None
    batch_discount: float | None
    supports_tools: bool | None
    supports_structured_output: bool | None
    supports_vision: bool | None
    supports_caching: bool | None
    supports_batch: bool | None
    sources: dict[str, dict[str, str]] = field(default_factory=dict)

    #: Never set from the feed. `family`, `lifecycle` and `regions` are not in it,
    #: and `slot` is neither in the feed nor in the schema.
    UNAVAILABLE = ("family", "lifecycle", "regions", "slot")

    @property
    def populated(self) -> tuple[str, ...]:
        return tuple(
            name for name in (
                "display_name", "release_date", "retirement_date",
                "knowledge_cutoff", "advertised_context", "max_output_tokens",
                "price_in", "price_out", "price_cached_read", "batch_discount",
                "supports_tools", "supports_structured_output",
                "supports_vision", "supports_caching", "supports_batch",
            )
            if getattr(self, name) is not None
        )

    def as_row(self) -> dict[str, Any]:
        """Column values. `provenance` is `polled`; the schema allows seed|polled."""
        return {
            "canonical_id": self.canonical_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "release_date": self.release_date,
            "retirement_date": self.retirement_date,
            "knowledge_cutoff": self.knowledge_cutoff,
            "advertised_context": self.advertised_context,
            "max_output_tokens": self.max_output_tokens,
            "price_in": self.price_in,
            "price_out": self.price_out,
            "price_cached_read": self.price_cached_read,
            "batch_discount": self.batch_discount,
            # Explicit None rather than omission: these columns DEFAULT false,
            # and a default speaking for a silent feed is rule 6's own example.
            "supports_tools": self.supports_tools,
            "supports_structured_output": self.supports_structured_output,
            "supports_vision": self.supports_vision,
            "supports_caching": self.supports_caching,
            "supports_batch": self.supports_batch,
            "sources": self.sources,
            "provenance": "polled",
        }


def _source(field_name: str, retrieved_at: datetime, *, derived_from: str | None = None
            ) -> dict[str, str]:
    entry = {"url": MODELS_URL, "retrieved_at": retrieved_at.isoformat()}
    if derived_from:
        # FR-2 wants where a field came from. "the endpoint" is true and
        # insufficient when the value was computed rather than read.
        entry["derived_from"] = derived_from
    return entry


def map_model(entry: dict[str, Any], *, retrieved_at: datetime,
              batch_sibling: dict[str, Any] | None = None) -> PolledModel:
    """One feed entry to one `model_version` row.

    `batch_sibling` is the `:batch` entry for the same base model when the feed
    carries one. Its existence is the only statement in the feed that batching is
    supported, and the ratio of its prompt price to this one's is the discount.
    """
    model_id = base_id(str(entry.get("id") or ""))
    provider = model_id.split("/")[0] if "/" in model_id else ""
    pricing = entry.get("pricing") or {}
    arch = entry.get("architecture") or {}
    top = entry.get("top_provider") or {}
    params = entry.get("supported_parameters")
    modalities = arch.get("input_modalities")

    price_in = _per_million(pricing.get("prompt"))
    price_out = _per_million(pricing.get("completion"))
    cached = _per_million(pricing.get("input_cache_read"))

    batch_discount = None
    if batch_sibling:
        batch_price = _per_million((batch_sibling.get("pricing") or {}).get("prompt"))
        if batch_price is not None and price_in:
            batch_discount = round(batch_price / price_in, 3)

    values: dict[str, Any] = {
        "display_name": entry.get("name") or None,
        "release_date": _date_of(entry.get("created")),
        "retirement_date": _date_of(entry.get("expiration_date")),
        "knowledge_cutoff": _date_of(entry.get("knowledge_cutoff")),
        "advertised_context": entry.get("context_length") or None,
        "max_output_tokens": top.get("max_completion_tokens") or None,
        "price_in": price_in,
        "price_out": price_out,
        "price_cached_read": cached,
        "batch_discount": batch_discount,
        # A list that is present and lacks the key is a statement. A list that is
        # absent is not, so it stays None.
        "supports_tools": (TOOL_PARAM in params) if params is not None else None,
        "supports_structured_output": (
            (STRUCTURED_PARAM in params) if params is not None else None
        ),
        "supports_vision": (
            ("image" in modalities) if modalities is not None else None
        ),
        # A cache price is evidence OF caching. Its absence is not evidence
        # against, so False is never written here.
        "supports_caching": True if cached is not None else None,
        "supports_batch": True if batch_sibling else None,
    }

    sources = {}
    for name, value in values.items():
        if value is None:
            continue
        if name == "batch_discount":
            sources[name] = _source(name, retrieved_at,
                                    derived_from=f"{model_id}:batch pricing.prompt")
        elif name == "supports_batch":
            sources[name] = _source(name, retrieved_at,
                                    derived_from=f"presence of {model_id}:batch")
        elif name == "supports_caching":
            sources[name] = _source(name, retrieved_at,
                                    derived_from="pricing.input_cache_read")
        else:
            sources[name] = _source(name, retrieved_at)

    return PolledModel(
        canonical_id=model_id, provider=provider, sources=sources, **values
    )


@dataclass(frozen=True)
class PollResult:
    """One poll. Counts, not opinions."""

    retrieved_at: datetime
    raw_entries: int
    models: tuple[PolledModel, ...]
    tier_entries: int
    content_hash: str | None = None
    ref: str | None = None

    @property
    def distinct_models(self) -> int:
        return len(self.models)

    def describe(self) -> str:
        return (
            f"{self.raw_entries} feed entries -> {self.distinct_models} models "
            f"({self.tier_entries} service-tier entries folded in)"
        )


def parse_models(payload: Any, *, retrieved_at: datetime) -> PollResult:
    """The feed to rows. Service tiers folded into the model they belong to."""
    entries = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return PollResult(retrieved_at, 0, (), 0)

    by_base: dict[str, dict[str, Any]] = {}
    batch_by_base: dict[str, dict[str, Any]] = {}
    tier_count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model_id = str(entry.get("id") or "")
        if not model_id:
            continue
        base = base_id(model_id)
        if model_id.endswith(":batch"):
            batch_by_base[base] = entry
        if model_id != base:
            tier_count += 1
            # A tier entry never becomes the canonical row, but it must not
            # displace one either.
            by_base.setdefault(base, entry)
            continue
        by_base[base] = entry

    models = tuple(
        map_model(entry, retrieved_at=retrieved_at,
                  batch_sibling=batch_by_base.get(base))
        for base, entry in sorted(by_base.items())
    )
    return PollResult(retrieved_at, len(entries), models, tier_count)


def alias_coverage(models: tuple[PolledModel, ...], known: dict[str, Any]
                   ) -> tuple[str, ...]:
    """Which polled models have no hand-written alias list, and so are unsearchable.

    Reported rather than papered over. `alias_rows` needs prose surfaces the feed
    does not carry, so a polled model with no entry in `contract/seed_models.yaml`
    lands in `model_version` and is invisible to every sweep. That is a coverage
    gap and it should be a number somebody can look at, not a silence.
    """
    return tuple(m.canonical_id for m in models if m.canonical_id not in known)


def fetch_models(client, *, url: str = MODELS_URL):
    """GET the feed. No credential; see the module docstring.

    Returns the response so the caller can store the bytes before parsing —
    same order the adapters use, so a mapping change is a re-parse.
    """
    response = client.get(url)
    if response.status_code != 200:
        log.warning("openrouter: HTTP %s from %s", response.status_code, url)
        return None
    return response


def write_model_versions(conn, result: PollResult) -> dict[str, int]:
    """Upsert polled facts. Sets `last_swept_at` on NOTHING.

    THE SEPARATION THIS FUNCTION EXISTS TO KEEP. Polling reads facts about a
    model; sweeping looks for what engineers said about it. `updated_at` moves
    here and `last_swept_at` does not, because a poll is not a sweep and writing
    both would make a model that has never been searched look freshly searched —
    which is the exact confusion the column was added to prevent.

    Absent fields are written as NULL explicitly. Five `supports_*` columns
    carry DEFAULT false, so omitting a column would let the default assert a
    capability claim the feed never made (rule 6).
    """
    from collect.ids import stable_id

    inserted = updated = 0
    for model in result.models:
        row = model.as_row()
        row_id = stable_id("mv", row["canonical_id"])
        outcome = conn.execute(
            """
            INSERT INTO model_version (
                id, canonical_id, provider, display_name,
                release_date, retirement_date, knowledge_cutoff,
                advertised_context, max_output_tokens,
                price_in, price_out, price_cached_read, batch_discount,
                supports_tools, supports_structured_output, supports_vision,
                supports_caching, supports_batch,
                sources, provenance, updated_at
            ) VALUES (
                %(id)s, %(canonical_id)s, %(provider)s, %(display_name)s,
                %(release_date)s, %(retirement_date)s, %(knowledge_cutoff)s,
                %(advertised_context)s, %(max_output_tokens)s,
                %(price_in)s, %(price_out)s, %(price_cached_read)s,
                %(batch_discount)s,
                %(supports_tools)s, %(supports_structured_output)s,
                %(supports_vision)s, %(supports_caching)s, %(supports_batch)s,
                %(sources)s, 'polled', now()
            )
            ON CONFLICT (canonical_id) DO UPDATE SET
                display_name               = EXCLUDED.display_name,
                release_date               = EXCLUDED.release_date,
                retirement_date            = EXCLUDED.retirement_date,
                knowledge_cutoff           = EXCLUDED.knowledge_cutoff,
                advertised_context         = EXCLUDED.advertised_context,
                max_output_tokens          = EXCLUDED.max_output_tokens,
                price_in                   = EXCLUDED.price_in,
                price_out                  = EXCLUDED.price_out,
                price_cached_read          = EXCLUDED.price_cached_read,
                batch_discount             = EXCLUDED.batch_discount,
                supports_tools             = EXCLUDED.supports_tools,
                supports_structured_output = EXCLUDED.supports_structured_output,
                supports_vision            = EXCLUDED.supports_vision,
                supports_caching           = EXCLUDED.supports_caching,
                supports_batch             = EXCLUDED.supports_batch,
                sources                    = EXCLUDED.sources,
                provenance                 = 'polled',
                updated_at                 = now()
                -- last_swept_at is NOT touched. See the docstring.
            RETURNING (xmax = 0) AS was_insert
            """,
            {**row, "id": row_id, "sources": _json(row["sources"])},
        ).fetchone()
        if outcome and outcome[0]:
            inserted += 1
        else:
            updated += 1
    return {"inserted": inserted, "updated": updated}


def mark_swept(conn, canonical_ids, *, at: datetime) -> int:
    """Record that these models were SWEPT, which polling never does.

    The only writer of `last_swept_at`. Separate from `write_model_versions` so
    that a poll cannot set it by accident — the whole value of the column is that
    it answers a different question from `updated_at`.

    `at` is passed rather than defaulted to `now()` so a caller records the time
    the sweep ran rather than the time the bookkeeping did.
    """
    ids = list(canonical_ids)
    if not ids:
        return 0
    result = conn.execute(
        "UPDATE model_version SET last_swept_at = %s WHERE canonical_id = ANY(%s)",
        (at, ids),
    )
    return result.rowcount


def _json(value) -> str:
    import json

    return json.dumps(value, default=str)
