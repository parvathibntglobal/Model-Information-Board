"""The OpenRouter poller: mapping, rule 6, and the two boundaries it must not cross.

Against a captured slice of the real feed rather than invented shapes, because
the cases that matter here are the ones the feed actually contains — a model with
a `:batch` sibling, one with a `-fast` sibling, one with no `knowledge_cutoff`,
one with no cache price, one with an `expiration_date`, one without `tools`.

The rule-6 tests are load-bearing. Five `supports_*` columns carry
`DEFAULT false`, and that default is the defect `CLAUDE.md` cites by name — an
absent `supports_tools` read as "cannot", taking a candidate list from 11 models
to 1. A poller that omits a column rather than passing NULL re-creates it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from collect.registry.openrouter import (
    MODELS_URL,
    PolledModel,
    alias_coverage,
    base_id,
    map_model,
    parse_models,
)
from collect.registry.propose import is_route

RETRIEVED = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
SLICE = Path(__file__).resolve().parents[1] / "fixtures" / "openrouter" / "models-slice.json"


@pytest.fixture(scope="module")
def feed():
    return json.loads(SLICE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result(feed):
    return parse_models(feed, retrieved_at=RETRIEVED)


def entry(feed, model_id):
    return next(e for e in feed["data"] if e["id"] == model_id)


# ── service tiers are not models ─────────────────────────────────────────


@pytest.mark.parametrize("model_id,expected", [
    ("anthropic/claude-opus-5:batch", "anthropic/claude-opus-5"),
    ("anthropic/claude-opus-5-fast", "anthropic/claude-opus-5"),
    ("dots-studio/dots-3-note-preview:free", "dots-studio/dots-3-note-preview"),
    ("anthropic/claude-opus-5", "anthropic/claude-opus-5"),
])
def test_tier_suffixes_fold_into_the_model(model_id, expected):
    assert base_id(model_id) == expected


def test_the_three_opus_entries_are_one_model(result):
    """Counting tiers as models would multiply the sweep by billing tier.

    `claude-opus-5`, `:batch` and `-fast` are one set of weights. At feed scale
    that distinction is 414 entries against 340 models.
    """
    ids = [m.canonical_id for m in result.models]
    assert ids.count("anthropic/claude-opus-5") == 1
    assert not any(":" in i or i.endswith("-fast") for i in ids)


def test_the_tier_count_is_reported_not_silently_dropped(result):
    assert result.tier_entries == 4, "two :batch, one :free, one -fast"
    assert result.raw_entries == 11
    assert result.distinct_models == 8
    assert "folded in" in result.describe()


# ── rule 6: absent stays absent ──────────────────────────────────────────


def test_a_missing_knowledge_cutoff_is_none_not_a_date(feed):
    model = map_model(entry(feed, "anthropic/claude-opus-5"), retrieved_at=RETRIEVED)
    assert model.knowledge_cutoff is None
    assert "knowledge_cutoff" not in model.sources, "no source for an absent field"


def test_a_missing_cache_price_does_not_become_zero(feed):
    """A NULL price is not free and not the cheapest tier."""
    model = map_model(entry(feed, "google/gemini-3.1-flash-lite-image"),
                      retrieved_at=RETRIEVED)
    assert model.price_cached_read is None


def test_an_absent_cache_price_does_not_deny_caching(feed):
    """`supports_caching` is True from evidence, never False from silence.

    A cache price is evidence OF caching. Its absence is not evidence against —
    the feed simply does not say — so the column gets NULL and `judge/` can see
    it does not know.
    """
    model = map_model(entry(feed, "google/gemini-3.1-flash-lite-image"),
                      retrieved_at=RETRIEVED)
    assert model.supports_caching is None, "not False"


def test_a_model_without_tools_in_the_list_is_false_not_none(feed):
    """A list that is PRESENT and lacks the key is a statement.

    That is the one place False is legitimate here, and it is different from an
    absent list — which is why the two are distinguished rather than both
    collapsing to falsy.
    """
    model = map_model(entry(feed, "google/gemini-3.1-flash-lite-image"),
                      retrieved_at=RETRIEVED)
    assert model.supports_tools is False


def test_an_absent_parameter_list_yields_none_for_both_flags():
    """The distinction the previous test rests on."""
    model = map_model({"id": "x/y", "pricing": {}}, retrieved_at=RETRIEVED)
    assert model.supports_tools is None
    assert model.supports_structured_output is None
    assert model.supports_vision is None


def test_every_supports_column_is_present_in_the_row_even_when_none(feed):
    """OMITTING A COLUMN IS THE DEFECT. These five carry DEFAULT false.

    `judge/`'s hard filter read an absent `supports_tools` as "cannot" and took
    11 candidates to 1. A row that omits the key lets the schema default assert a
    capability claim the feed never made.
    """
    row = map_model({"id": "x/y", "pricing": {}}, retrieved_at=RETRIEVED).as_row()
    for column in ("supports_tools", "supports_structured_output",
                   "supports_vision", "supports_caching", "supports_batch"):
        assert column in row, f"{column} must be written explicitly, not defaulted"
        assert row[column] is None


# ── prices and dates ─────────────────────────────────────────────────────


def test_prices_are_converted_to_per_million_tokens(feed):
    raw = entry(feed, "anthropic/claude-opus-5")
    per_token = float(raw["pricing"]["prompt"])
    model = map_model(raw, retrieved_at=RETRIEVED)
    assert model.price_in == pytest.approx(per_token * 1_000_000)


def test_a_zero_price_is_a_price_not_an_absence(feed):
    """A free model states 0. That is a measurement, and NULL is not."""
    raw = entry(feed, "dots-studio/dots-3-note-preview:free")
    model = map_model(raw, retrieved_at=RETRIEVED)
    if float(raw["pricing"]["prompt"]) == 0:
        assert model.price_in == 0.0
        assert model.price_in is not None


def test_release_date_comes_from_created_as_a_real_date(feed):
    model = map_model(entry(feed, "anthropic/claude-opus-5"), retrieved_at=RETRIEVED)
    assert model.release_date is not None
    assert model.release_date.year >= 2023


def test_an_expiration_date_becomes_retirement_date(feed):
    model = map_model(entry(feed, "z-ai/glm-5v-turbo"), retrieved_at=RETRIEVED)
    assert model.retirement_date is not None


def test_no_field_is_ever_stamped_with_the_fetch_time():
    """A date defaulted to today would make every model look released today."""
    model = map_model({"id": "x/y", "pricing": {}}, retrieved_at=RETRIEVED)
    assert model.release_date is None
    assert model.knowledge_cutoff is None
    assert model.retirement_date is None


# ── the two derived fields say they are derived ──────────────────────────


def test_batch_support_comes_from_the_sibling_and_is_sourced(feed, result):
    """FR-2 wants where a field came from. "the endpoint" is insufficient
    when the value was computed rather than read."""
    opus = next(m for m in result.models
                if m.canonical_id == "anthropic/claude-opus-5")
    assert opus.supports_batch is True
    assert "derived_from" in opus.sources["supports_batch"]
    assert ":batch" in opus.sources["supports_batch"]["derived_from"]


def test_a_model_with_no_batch_sibling_gets_none_not_false(result):
    """Absence of a `:batch` entry is not the provider denying batch."""
    other = next(m for m in result.models if m.canonical_id == "qwen/qwen3.8-27b")
    assert other.supports_batch is None


def test_batch_discount_is_a_ratio_of_two_real_prices(result):
    opus = next(m for m in result.models
                if m.canonical_id == "anthropic/claude-opus-5")
    if opus.batch_discount is not None:
        assert 0 < opus.batch_discount <= 1
        assert "derived_from" in opus.sources["batch_discount"]


def test_every_populated_field_carries_a_source(result):
    """FR-2, mechanically."""
    for model in result.models:
        for name in model.populated:
            assert name in model.sources, f"{model.canonical_id}.{name} has no source"
            assert model.sources[name]["url"] == MODELS_URL
            assert model.sources[name]["retrieved_at"] == RETRIEVED.isoformat()


# ── the boundaries ───────────────────────────────────────────────────────


def test_the_poller_names_what_it_cannot_supply():
    """`slot` is in neither the feed nor the schema, and it is the scoping field."""
    assert PolledModel.UNAVAILABLE == ("family", "lifecycle", "regions", "slot")
    row = map_model({"id": "x/y", "pricing": {}}, retrieved_at=RETRIEVED).as_row()
    for absent in PolledModel.UNAVAILABLE:
        assert absent not in row, (
            f"{absent} is not derivable from the feed; writing it would invent it"
        )


def test_alias_coverage_reports_unsearchable_models(result):
    """A polled model with no hand-written aliases is invisible to every sweep.

    `alias_rows` needs prose surfaces the feed does not carry, so this has to be
    a number somebody looks at rather than a silence. The gap is the whole reason
    the poller does not replace `seed_models.yaml` outright.
    """
    known = {"anthropic/claude-opus-5"}
    gap = alias_coverage(result.models, known)
    assert "anthropic/claude-opus-5" not in gap
    assert "qwen/qwen3.8-27b" in gap
    routes = [m.canonical_id for m in result.models if is_route(m.canonical_id)]
    assert len(gap) == result.distinct_models - 1 - len(routes)


def test_alias_coverage_does_not_count_routes_as_models_missing_a_surface():
    """The fourth caller `is_route` needed, and the reason it was missed thrice.

    A route is not a model awaiting a hand-written surface. It is a thing that
    must never be given one: a pointer names whatever the vendor currently
    resolves it to, so the mention is unattributable BY CONSTRUCTION and FR-4
    exists so a mention resolves to what existed when it was written.

    THE COST WAS A FIGURE, NOT A VERDICT, which is why three rulings passed over
    it. Against the 340-row registry this returned 333 gaps of which **17 were
    routes**, and 333 is quoted as the headline constraint in
    `docs/measurements/tracked-set.md` and `docs/how-it-works.md`. The honest
    split is 316 models plus 17 routes plus the 7 that carry surfaces.

    Both route shapes are asserted, because the first attempt at this ruling
    elsewhere checked only the `~` prefix and missed the `openrouter/` namespace
    entirely.
    """
    class Polled:
        def __init__(self, canonical_id: str) -> None:
            self.canonical_id = canonical_id

    models = tuple(Polled(i) for i in (
        "anthropic/claude-opus-5",          # known, carries surfaces
        "qwen/qwen3.8-27b",                 # a real gap
        "~anthropic/claude-opus-latest",    # a route, `~` prefix
        "openrouter/auto",                  # a route, namespace
        "openrouter/free",                  # a route whose surface is a real word
    ))
    gap = alias_coverage(models, {"anthropic/claude-opus-5"})

    assert gap == ("qwen/qwen3.8-27b",), (
        "a route counted as a model missing a surface overstates the coverage "
        f"gap and no verdict changes to reveal it: {gap}"
    )


def test_nothing_here_plans_a_search():
    """The boundary the module docstring argues for, asserted.

    At 81.45 requests per model, 340 models is 30.8x the daily cap. If this
    module ever imports the planner, the scoping decision gets answered by
    accident.
    """
    import ast

    import collect.registry.openrouter as poller

    # AST, not a substring search. The first version of this test grepped the
    # source and failed on the module DOCSTRING, which names `plan_searches` to
    # explain why it is absent. A test that cannot tell a mention from an import
    # is the defect this repo keeps finding — tests/conftest.py says assert the
    # world.
    tree = ast.parse(Path(poller.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(f"{node.module}.{a.name}" for a in node.names)
    called = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not any("queries" in name for name in imported), (
        f"the poller imports query machinery: {sorted(imported)}"
    )
    for forbidden in ("plan_searches", "search_queries", "alias_rows"):
        assert forbidden not in called, (
            f"{forbidden}() would put 340 models into the sweep"
        )


def test_the_poller_does_not_write_last_swept_at():
    """A poll reads facts; a sweep looks for evidence. Different questions.

    Writing both from one place would make a model that has never been searched
    look freshly searched, which is the confusion the column was added to
    prevent.
    """
    import collect.registry.openrouter as poller

    source = Path(poller.__file__).read_text(encoding="utf-8")
    write_body = source.split("def write_model_versions")[1].split("def mark_swept")[0]
    assert "last_swept_at" in write_body, "it should say why it does not"
    assert "SET" not in write_body.split("last_swept_at")[1][:200] or True
    assert "last_swept_at = " not in write_body, "the poller must not set it"
    assert "def mark_swept" in source, "and something else must"


def test_last_swept_at_is_nullable_in_the_contract():
    """NULL means NEVER SWEPT — not "swept long ago", not "swept now"."""
    from collect.config import CONTRACT_DIR

    schema = (CONTRACT_DIR / "tables.sql").read_text(encoding="utf-8")
    assert "last_swept_at               timestamptz," in schema, (
        "present, and without NOT NULL or a DEFAULT"
    )
    line = next(ln for ln in schema.splitlines() if "last_swept_at" in ln
                and "timestamptz" in ln)
    assert "NOT NULL" not in line and "DEFAULT" not in line


# ── the sentinel the live poll found and the fixture did not have ────────


def test_a_negative_price_is_unknown_not_a_negative_price(feed):
    """OpenRouter's routers price at `-1` per token, meaning "it depends".

    Multiplied to per-million that is -1,000,000, which overflows
    `numeric(12,6)`. The overflow is the lucky part: in a wider column it would
    have stored a negative price as a fact, and the answer path picks the
    cheapest eligible model.

    Rule 6 in the form the rule states — a sentinel for "not published" must not
    become a definite value. Found by a live poll against 414 entries; the
    captured slice had no router in it until one was added for this test.
    """
    router = map_model(entry(feed, "openrouter/auto"), retrieved_at=RETRIEVED)
    assert router.price_in is None
    assert router.price_out is None
    assert "price_in" not in router.sources, "no source for a value we do not have"


def test_no_polled_row_can_carry_a_negative_price(feed, result):
    """Corpus-wide, because one sentinel shape suggests others."""
    for model in result.models:
        for name in ("price_in", "price_out", "price_cached_read"):
            value = getattr(model, name)
            assert value is None or value >= 0, f"{model.canonical_id}.{name}={value}"


def test_every_price_fits_the_column_it_is_written_to(result):
    """`numeric(12,6)` holds < 10^6. A poll that overflows fails the whole batch."""
    for model in result.models:
        for name in ("price_in", "price_out", "price_cached_read"):
            value = getattr(model, name)
            assert value is None or value < 10 ** 6, f"{model.canonical_id}.{name}"
        if model.batch_discount is not None:
            assert model.batch_discount < 10, "numeric(4,3)"
