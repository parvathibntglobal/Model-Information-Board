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
SURFACE.** `undeclared_models` below reports the gap per model rather than leaving
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

# The route ruling. Same package, so no boundary question: the lane test forbids
# `collect/registry/` importing `collect/adapters/`, not registry-internal
# imports. `propose` imports nothing from here, so there is no cycle.
from collect.registry.propose import is_route

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
    #: `~vendor/family-latest` pointer entries skipped (they carry `alias_target`).
    alias_entries: int = 0

    @property
    def distinct_models(self) -> int:
        return len(self.models)

    def describe(self) -> str:
        return (
            f"{self.raw_entries} feed entries -> {self.distinct_models} models "
            f"({self.tier_entries} service-tier entries folded in, "
            f"{self.alias_entries} alias pointer entries skipped)"
        )


class UnreadableFeed(TypeError):
    """The payload is not a feed. Raised rather than returning an empty result."""


def parse_models(payload: Any, *, retrieved_at: datetime) -> PollResult:
    """The feed to rows. Service tiers folded into the model they belong to.

    RAISES ON A PAYLOAD IT CANNOT READ, and it did not until 2026-08-20. The
    line below returned `PollResult(retrieved_at, 0, (), 0)` for anything that
    was not a list — which converted a caller's type error into the sentence
    *"the feed has no models"*, reported by the nightly chain as **OK**.

    That is what happened for the whole life of the chain. `fetch_models`
    returns a `Response` — deliberately, so the caller can store the bytes
    before parsing — and `_poll_registry_stage` handed it straight to this
    function without `.json()`. A `Response` is not a dict and not a list, so
    every poll parsed to zero models and the stage reported success:

        parse_models(response)  ->  0 feed entries -> 0 models        OK
        parse_models(.json())   ->  414 feed entries -> 340 models

    The fourth instance of one shape in a day, and the worst of the four: the
    other three REFUSED and named a reason, and a refusal is legible. This one
    succeeded and produced nothing, which is rule 6 inside the module written to
    uphold it — an unreadable payload becoming a definite statement about the
    world.

    So the defensive branch is now a refusal. An empty `data` list is still a
    legitimate zero and still returns one: the distinction is between *the feed
    said nothing* and *this is not the feed*.
    """
    entries = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise UnreadableFeed(
            f"expected a feed document or a list of entries, got "
            f"{type(payload).__name__}. If this is an httpx Response, the caller "
            f"owes it a `.json()` — `fetch_models` returns the response on "
            f"purpose so the bytes can be stored before parsing, and skipping "
            f"the parse produced a silent 0-model poll for the whole life of "
            f"the nightly chain."
        )

    by_base: dict[str, dict[str, Any]] = {}
    batch_by_base: dict[str, dict[str, Any]] = {}
    tier_count = 0
    alias_count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model_id = str(entry.get("id") or "")
        if not model_id:
            continue
        # ⚠ A `~vendor/family-latest` ENTRY IS A POINTER, NOT A MODEL. The
        #   catalogue marks it with `alias_target` naming the real model -
        #   `~openai/gpt-astra-latest` -> `openai/gpt-6-astra` - and writing it
        #   as a row gives one model two registry ids and splits its evidence.
        #   12 such rows were written by the 2026-08 polls. Skipped and COUNTED.
        if entry.get("alias_target"):
            alias_count += 1
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
    return PollResult(retrieved_at, len(entries), models, tier_count,
                      alias_entries=alias_count)


def undeclared_models(models: tuple[PolledModel, ...], declared: Any) -> tuple[str, ...]:
    """Polled models absent from `contract/seed_models.yaml`, so unsearchable.

    RENAMED FROM `alias_coverage(models, known)`, 2026-08-20, because both halves
    of that signature described something other than what they did and the
    output was quoted as a coverage figure on the strength of the name.

    `alias_coverage` reads as *"we checked each model's aliases"*. It does no such
    thing: it is a set difference against a build fixture. And `known` reads as
    *"known to the system"* — but every one of these models IS known, polled,
    stored and in the window; what they are is **undeclared**. A model absent
    from `known` is absent from an eleven-entry YAML, not from the registry.

    The number is therefore a ROSTER REACHABILITY figure — *"of everything the
    poller found, how much can a sweep look for"* — and not a load gap. That
    distinction is what `docs/proposals/coverage-page-scope.md` is about: the
    coverage page's four kinds are all properties of a LOAD, keyed to a model the
    load touched, and this is a property of the FEED. Same word, different
    question, and a reader seeing "333 gaps" concluded the first.

    Reported rather than papered over: `alias_rows` needs prose surfaces the feed
    does not carry, so a polled model with no entry in `contract/seed_models.yaml`
    lands in `model_version` and is invisible to every sweep. That should be a
    number somebody can look at rather than a silence — but the number has had no
    production caller since it was written, so today it is a silence with a
    function behind it.

    ROUTES ARE EXCLUDED, AND THIS IS THE FOURTH CALLER THE RULING NEEDED.
    `is_route` was ruled 2026-08-18 and had callers in `triage/entity.py`,
    `tracked.select` and — after the last fix — `propose()`. Not here. So this
    function counted **17 of its 333 answers as models awaiting a surface**, and
    a route is not a model missing a surface: it is a thing that must never be
    given one, because a pointer names whatever the vendor currently resolves it
    to and the mention is unattributable by construction (FR-4).

    The cost was a figure rather than a wrong verdict, which is why it survived a
    fourth time: 333 is quoted as the headline constraint in
    `docs/measurements/tracked-set.md` and in `docs/how-it-works.md`, and the
    honest split is **316 models plus 17 routes**. Wrong in the direction that
    overstates our own gap — the safer direction, and still rule 7.

    A ruling with a caller is not a ruling with every caller. This is the third
    time that sentence has been written about `is_route`; the standing lesson is
    that a ruling implemented as a predicate needs its call sites enumerated
    somewhere, because nothing about the predicate reveals which paths consult
    it. `tests/test_registry_openrouter.py` now pins this one.
    """
    return tuple(
        m.canonical_id
        for m in models
        if m.canonical_id not in declared and not is_route(m.canonical_id)
    )


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


def write_model_versions(
    conn, result: PollResult, *, batch: int = 200, record_changes: bool = True
) -> dict[str, int]:
    """Upsert polled facts. Sets `last_swept_at` on NOTHING.

    BATCHED, AND THIS ONE RUNS NIGHTLY AT THE LARGEST VOLUME OF ANY WRITER HERE.
    340 models, one round trip each: about 44 seconds against a remote instance
    at the 130ms measured on `write_authors`, against roughly a second batched.
    Same shape as `write_authors` and `github.write_documents`, found by sweeping
    the other writers rather than by hitting it.

    `executemany(returning=True)` keeps the per-row `RETURNING`, so inserts and
    updates stay separable rather than summed into a single "written". That
    distinction is now load-bearing rather than merely tidy: `_record_changes`
    reads it to decide whether tonight's observation of a model is its FIRST,
    and a first observation is a baseline rather than a price change.

    FR-3'S PRODUCER LIVES HERE NOW. It used to live nowhere: `_record_event` and
    `_record_prices` were called from `load_seed()` only, so the 11 seeded models
    produced events and the 340 polled ones produced none — `model_event` held 0
    rows and a price could move nightly with nothing recording it. Pass
    `record_changes=False` to upsert without writing history or events; the
    default is on, because a caller who forgets is exactly how it came to be
    missing in the first place.

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

    params = []
    for model in result.models:
        row = model.as_row()
        params.append({
            **row,
            "id": stable_id("mv", row["canonical_id"]),
            "sources": _json(row["sources"]),
        })

    statement = """
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
            RETURNING id, (xmax = 0) AS was_insert, canonical_id
            """

    # The id travels back with the verdict rather than the caller re-deriving it
    # from position. Result sets do arrive in order, but an event attributed to
    # the wrong model by an off-by-one is a defect nobody would see: it would
    # read as a real price change on a real model.
    verdicts: dict[str, bool] = {}
    row_id_of: dict[str, str] = {}
    with conn.cursor() as cur:
        for start in range(0, len(params), batch):
            cur.executemany(statement, params[start:start + batch], returning=True)
            # One result set per row. `nextset()` walks them; the last returns
            # None, which ends the loop rather than an off-by-one.
            while True:
                outcome = cur.fetchone() if cur.pgresult is not None else None
                if outcome is not None:
                    verdicts[outcome[0]] = bool(outcome[1])
                    row_id_of[outcome[2]] = outcome[0]
                if not cur.nextset():
                    break

    # ⚠ THE ROW'S ID, NOT THE ONE COMPUTED ABOVE. The upsert matches on
    #   `canonical_id`, so a row that already exists under a DIFFERENT id - a
    #   hand-entered model the catalogue has since started listing - is updated
    #   in place and keeps its own id. Everything written after this point
    #   (`pricing_history`, `model_event`) is keyed on `model_version_id`, and
    #   keying it on `stable_id` pointed it at a row that does not exist: the
    #   first scheduled poll, 2026-09-24, died on a foreign-key violation for
    #   `anthropic/claude-fable-5.1`, whose row id is `anthropic/claude-fable-5-1`.
    #   Re-keying the row instead would move every claim that points at it.
    #   A canonical_id the upsert returned no row for is a defect, so it raises.
    missing = [p["canonical_id"] for p in params if p["canonical_id"] not in row_id_of]
    if missing:
        raise RuntimeError(
            f"upsert returned no row for {len(missing)} model(s): {missing[:5]}"
        )
    for p in params:
        p["id"] = row_id_of[p["canonical_id"]]

    counts = {
        "inserted": sum(1 for was_insert in verdicts.values() if was_insert),
        "updated": sum(1 for was_insert in verdicts.values() if not was_insert),
    }
    if not record_changes:
        return counts
    return {**counts, **_record_changes(conn, params, verdicts, batch=batch)}


def _record_changes(conn, params, verdicts, *, batch: int) -> dict[str, int]:
    """FR-3's producer: what moved tonight, recorded where an alert can read it.

    Runs AFTER the upsert and reads `pricing_history`, which the upsert does not
    touch — so there is no ordering hazard between the two. The registry row is
    already the new one; the comparison is against the last thing we OBSERVED,
    which is what `pricing_history` is for.

    Three writes, each batched: history rows, `new-model` events, `price-change`
    events. `observe_prices` decides all of it and is shared with the seed
    loader, so there is one definition of "the price moved" in the lane.

    NOT emitted here, and named rather than silently absent:
    `deprecation-announced`. A `retirement_date` appearing in the feed is a real
    event of that type, and it needs the prior value of THAT column to detect —
    a different comparison from the price one, against `model_version` rather
    than against an observation table. Worth building; not built here.
    """
    from collect.registry.events import (
        NEW_MODEL,
        PRICE_CHANGE,
        PRICE_COLUMNS,
        append_prices,
        latest_prices,
        observe_prices,
        write_events,
    )

    previous = latest_prices(conn, [row["id"] for row in params])

    to_append, observations = [], {}
    for row in params:
        observation = observe_prices(
            previous.get(row["id"]), {column: row[column] for column in PRICE_COLUMNS}
        )
        observations[row["id"]] = observation
        if observation.append:
            to_append.append({
                "model_version_id": row["id"],
                **{column: row[column] for column in PRICE_COLUMNS},
            })

    observed_at = append_prices(conn, to_append, batch=batch)

    events = []
    for row in params:
        if verdicts.get(row["id"]):
            # A NEW MODEL IS NOT A PRICE CHANGE, however different its prices
            # look from the nothing before them. Its first observation is a
            # baseline, written above and not announced.
            events.append({
                "model_version_id": row["id"],
                "type": NEW_MODEL,
                "occurred_at": row.get("release_date"),
                "payload": {"canonical_id": row["canonical_id"]},
            })
            continue
        observation = observations[row["id"]]
        if not observation.moved:
            continue
        events.append({
            "model_version_id": row["id"],
            "type": PRICE_CHANGE,
            "occurred_at": observed_at.get(row["id"]),
            "payload": {
                "canonical_id": row["canonical_id"],
                "changed": list(observation.changed),
                "from": {c: str(observation.previous[c]) for c in observation.changed},
                "to": {c: str(observation.incoming[c]) for c in observation.changed},
            },
        })

    write_events(conn, events, batch=batch)
    return {
        "prices_recorded": len(to_append),
        "events": len(events),
        "price_changes": sum(1 for e in events if e["type"] == PRICE_CHANGE),
        # A price we used to know and no longer do. Not an event and not a zero
        # — see `PriceObservation.withdrawn`. Counted here so it reaches the run
        # report rather than disappearing between two things it is not.
        "prices_withdrawn": sum(1 for o in observations.values() if o.withdrawn),
    }


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
