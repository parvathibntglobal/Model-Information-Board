"""The Benchmarks page's scraper (collect/benchmarks/) and its page reads (judge/benchmarks.py).

No test here touches a live site (doc 22.3 #19). Pages are small hand-written
copies of the real structures read on 2026-10-22 - the SWE-bench
`<script id="leaderboard-data">` block, the LiveBench name cell with its "open"
badge and setting tooltip, Scale's Next.js data - plus two test-only sources
(tests/fixtures/benchmarks/): a printed HTML board and a page of embedded JSON
tables, so each parser is checked against the shape it was built for.
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import psycopg
import pytest

from collect.benchmarks import store
from collect.benchmarks.changes import diff, direction
from collect.benchmarks.config import ConfigError, load
from collect.benchmarks.fetch import Fetched
from collect.benchmarks.host_adapter import SeedModel
from collect.benchmarks.match import Resolver, normalize_name
from collect.benchmarks.merge import dedupe_source, merge
from collect.benchmarks.parse import parse
from collect.benchmarks.runner import run
from collect.benchmarks.store import StoredCell, StoredObservation
from collect.benchmarks.values import parse_rank, parse_score
from collect.config import CONTRACT_DIR, REPO_ROOT
from tests.conftest import assert_disposable, assert_safe_target


def _test_config_dir() -> Path:
    """The shipped config plus the test-only sources and the columns only they
    fill (tests/fixtures/benchmarks/). A real run never reads them."""
    target = Path(tempfile.mkdtemp(prefix="bench-config-"))
    for name in (CONTRACT_DIR / "benchmarks").glob("*.yaml"):
        shutil.copy(name, target / name.name)
    fixtures = REPO_ROOT / "tests" / "fixtures" / "benchmarks"
    for shipped, extra, key in (
        ("sources.yaml", "fixture_sources.yaml", "sources"),
        ("benchmarks.yaml", "fixture_benchmarks.yaml", "benchmarks"),
    ):
        items = (fixtures / extra).read_text(encoding="utf-8").split(f"\n{key}:\n", 1)[1]
        path = target / shipped
        path.write_text(
            path.read_text(encoding="utf-8").rstrip() + "\n\n" + items, encoding="utf-8"
        )
    # The JSON fixture's SWE-bench values carry its harness as the test setup.
    benches = target / "benchmarks.yaml"
    benches.write_text(
        benches.read_text(encoding="utf-8").replace(
            'accept: ["mini-SWE-agent"] }', 'accept: ["mini-SWE-agent", "fixture harness"] }'
        ),
        encoding="utf-8",
    )
    return target


TEST_CONFIG_DIR = _test_config_dir()


@pytest.fixture(autouse=True)
def _page_reads_the_test_config(monkeypatch):
    from judge import benchmarks as page

    monkeypatch.setattr(page, "CONFIG_DIR", TEST_CONFIG_DIR)


SEEDS = [
    SeedModel("openai/gpt-6-astra", "GPT 6 Astra"),
    SeedModel("openai/gpt-6-luna", "GPT-6 Luna"),
    SeedModel("anthropic/claude-opus-5.5", "Claude Opus 5.5"),
    SeedModel("moonshotai/kimi-k3", "Kimi K3"),
    SeedModel("openai/gpt-6.1-sol", "GPT-6.1 Sol"),
]


@pytest.fixture(scope="module")
def config():
    return load(TEST_CONFIG_DIR)


@pytest.fixture(scope="module")
def resolver(config):
    return Resolver(config, SEEDS)


# ── values ───────────────────────────────────────────────────────────────────


class TestValues:
    @pytest.mark.parametrize(
        "text,scale,expected",
        [
            ("88.7%", "percent", 88.7),
            ("88.7", "percent", 88.7),
            ("0.887", "fraction", 88.7),
            ("88.7*", "percent", 88.7),
            ("88.7 ± 1.2", "percent", 88.7),
            ("91.51% ± 5.31%", "percent", 91.51),
            ("1.0", "fraction", 100.0),
            ("0.9577020202020202", "fraction", 95.77),
        ],
    )
    def test_scores_normalise(self, text, scale, expected):
        assert parse_score(text, scale).value == expected

    @pytest.mark.parametrize("text", ["", "—", "-", "n/a", "None", "tbd"])
    def test_empty_tokens_are_empty_not_errors(self, text):
        v = parse_score(text, "percent")
        assert v.empty and v.value is None and v.error is None

    def test_out_of_range_is_rejected_with_the_raw_text(self):
        assert "140" in parse_score("140", "percent").error
        assert parse_score("1.4", "fraction").error

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("92.1%, $0.480/task", 92.1),  # ARC Prize: the one number marked %
            ("$1.20 / 45.1%", 45.1),
            ("v2: 45.1", 45.1),  # "v2" is a name, not a number
            ("GPT-5 45.1", 45.1),
            ("100.00% ± 0.00%", 100.0),  # an uncertainty is not a second value
        ],
    )
    def test_the_score_is_the_cells_one_number(self, text, expected):
        # PR #573 review: taking the FIRST number stored 1.2 and 2.0 here.
        assert parse_score(text, "percent").value == expected

    @pytest.mark.parametrize("text", ["$1.20 / 3.4", "45.1 (52.3)", "12% / 15%"])
    def test_a_cell_with_several_unmarked_numbers_is_refused(self, text):
        v = parse_score(text, "percent")
        assert v.value is None and "more than one number" in v.error

    @pytest.mark.parametrize(
        "text,rank,high,tied",
        [
            ("#3", 3, 3, False),
            ("3rd", 3, 3, False),
            ("T-3", 3, 3, True),
            ("=3", 3, 3, True),
            ("3–5", 3, 5, False),
            ("3-5", 3, 5, False),
            ("12", 12, 12, False),
        ],
    )
    def test_ranks_parse(self, text, rank, high, tied):
        v = parse_rank(text, 50)
        assert (v.value, v.rank_high, v.tied) == (rank, high, tied)

    def test_a_rank_beyond_the_board_is_rejected(self):
        assert parse_rank("60", 50).error


# ── matching ─────────────────────────────────────────────────────────────────


class TestMatching:
    def test_separators_are_not_part_of_the_name(self):
        assert (
            normalize_name("anthropic/claude-opus-5.5")
            == normalize_name("Claude Opus 5.5")
            == normalize_name("claude-opus-5-5")
        )

    def test_the_whole_name_matches_the_base_row(self, resolver):
        m = resolver.match("GPT-6 Astra")
        assert m.row.row_id == "openai/gpt-6-astra" and m.row.setting is None

    def test_a_setting_suffix_makes_a_setting_row(self, resolver):
        m = resolver.match("gpt-6-astra_max")
        assert m.row.row_id == "openai/gpt-6-astra:max" and m.row.label == "GPT 6 Astra (max)"
        assert (
            resolver.match("Claude-Opus-5.5 (high)").row.row_id == "anthropic/claude-opus-5.5:high"
        )

    def test_a_setting_from_its_own_field(self, resolver):
        assert resolver.match("Kimi K3", "max").row.row_id == "moonshotai/kimi-k3:max"

    def test_a_lookalike_is_never_matched(self, resolver):
        # GPT-5.6 Luna is not GPT-6 Luna; GPT-6.1 Sol Pro is not GPT-6.1 Sol.
        # And no "closest model" is attached either: a similar name is a different
        # model, and showing it as near-match read as a match (2026-10-22).
        for name in (
            "GPT-5.6 Luna",
            "gpt-6.1-sol-pro",
            "Claude Opus 5",
            "Kimi K2",
            "GPT-6 Astra Mini",
        ):
            m = resolver.match(name)
            assert m.row is None and m.reason == "unmatched" and m.model_id is None, name
            assert not hasattr(m, "suggestion"), name

    @pytest.mark.parametrize(
        "name,model",
        [
            ("Opus 5.5", "anthropic/claude-opus-5.5"),  # "Claude" left out
            ("Anthropic Claude Opus 5.5", "anthropic/claude-opus-5.5"),
            ("Kimi K3 Instruct", "moonshotai/kimi-k3"),  # "Instruct" added
            ("OpenAI GPT-6 Luna", "openai/gpt-6-luna"),
        ],
    )
    def test_a_name_almost_the_same_is_listed_as_similar_never_matched(self, resolver, name, model):
        # Same numbers, only filler words differ: listed for a person to confirm
        # with "Same model as", never given a row on its own (2026-10-26).
        m = resolver.match(name)
        assert m.row is None and m.reason == "similar_to_registry", name
        assert m.similar_to == (model,), name

    @pytest.mark.parametrize(
        "name", ["Claude Opus 5", "Opus 5.6", "GPT-6 Luna Mini", "Kimi K2 Instruct", "Luna"]
    )
    def test_a_different_number_or_word_is_not_similar(self, resolver, name):
        m = resolver.match(name)
        assert m.reason == "unmatched" and not m.similar_to, name

    def test_an_unknown_setting_word_makes_no_row(self, resolver):
        m = resolver.match("gpt-6-astra_turbo")
        assert m.row is None and m.reason == "unknown_setting" and m.setting_word == "turbo"

    @pytest.mark.parametrize(
        "name,setting",
        [
            ("GPT-6 Astra (Thinking, Low)", "low"),
            ("GPT-6 Astra (Thinking, None)", "none"),
            ("GPT-6 Astra (xhigh thinking)", "xhigh"),
            ("GPT-6 Astra (thinking high)", "high"),
            ("GPT-6 Astra (Nonthinking)", "none"),
        ],
    )
    def test_thinking_with_an_effort_is_that_effort(self, resolver, name, setting):
        assert resolver.match(name).row.setting == setting

    @pytest.mark.parametrize(
        "name,setting",
        [
            ("GPT-6 Astra (Thinking, 16K)", "thinking-16k"),  # a budget is its own row
            ("GPT-6 Astra (Thinking 8K)", "thinking-8k"),
            ("gpt-6-astra_32K", "thinking-32k"),
            ("GPT-6 Astra (120K, Low)", "120k-low"),  # budget and effort
            ("GPT-6 Astra (Reasoning)", "thinking"),
            ("GPT-6 Astra (Beta Reasoning)", "reasoning-beta"),
            ("GPT-6 Astra (Refine.)", "refinement"),  # ARC's refinement systems
            ("GPT-6 Astra (Non-Reasoning)", "none"),
        ],
    )
    def test_budgets_modes_and_refinement_get_their_own_rows(self, resolver, name, setting):
        assert resolver.match(name).row.setting == setting

    def test_with_fallback_alone_is_the_models_row_marked_not_stated(self, resolver):
        m = resolver.match("GPT-6 Astra (with fallback)")
        assert m.row.row_id == "openai/gpt-6-astra" and m.setting_not_stated

    def test_a_letter_touching_a_digit_is_a_boundary(self):
        assert normalize_name("Qwen 3.8 27B") == normalize_name("qwen/qwen3.8-27b")
        assert normalize_name("Seed2.0-Lite") == normalize_name("bytedance-seed/seed-2.0-lite")
        assert normalize_name("GPT 4o") == normalize_name("gpt-4o")
        assert normalize_name("GPT-5.5") != normalize_name("GPT-55")  # the dot still separates

    def test_max_is_not_high_and_none_is_not_minimal(self, resolver):
        assert resolver.match("gpt-6-astra_max").row.setting == "max"
        assert resolver.match("gpt-6-astra_high").row.setting == "high"
        assert resolver.match("gpt-6-astra_none").row.setting == "none"

    def test_unknown_means_the_base_row_marked_not_stated(self, resolver):
        m = resolver.match("gpt-6-astra_unknown")
        assert m.row.row_id == "openai/gpt-6-astra" and m.setting_not_stated

    def test_a_registry_alias_two_models_share_is_dropped_not_guessed(self, config):
        r = Resolver(
            config,
            SEEDS,
            {
                "openai/gpt-6-astra": ["GPT 6"],
                "openai/gpt-6-luna": ["gpt-6"],
                "moonshotai/kimi-k3": ["K3 Moonshot"],
            },
        )
        assert r.match("GPT 6").row is None and r.warnings and not r.problems
        assert r.match("K3 Moonshot").row.row_id == "moonshotai/kimi-k3"

    def test_a_decoration_is_ignored(self, resolver):
        assert resolver.match("GPT-6.1 Sol (max) ⚠️").row.row_id == "openai/gpt-6.1-sol:max"

    def test_effort_with_fallback_is_that_effort(self, config):
        r = Resolver(config, [SeedModel("anthropic/claude-opus-5.5", "Claude Opus 5.5")])
        assert (
            r.match("Claude Opus 5.5 (max with fallback)").row.row_id
            == "anthropic/claude-opus-5.5:max"
        )
        assert r.match("Claude Opus 5.5 (xhigh with fallback)").row.setting == "xhigh"

    def test_gpt_5_5_and_gpt_5_5_codex_are_one_row(self, config):
        # One model; Codex is a tool it supports (Parvathi, 2026-10-26). Results
        # written either way fill the same row. GPT-5.5 Pro stays its own model.
        gpt55 = SeedModel("openai/gpt-5.5", "GPT-5.5")
        pro = SeedModel("openai/gpt-5.5-pro", "GPT-5.5 Pro")
        r = Resolver(config, [gpt55], {"openai/gpt-5.5": ["gpt-5.5", "gpt 5.5"]}, [pro])
        assert r.match("GPT-5.5").row.row_id == "openai/gpt-5.5"
        assert r.match("GPT-5.5 (xhigh)").row.row_id == "openai/gpt-5.5:xhigh"
        assert r.match("GPT-5.5 Codex").row.row_id == "openai/gpt-5.5"
        assert r.match("GPT-5.5 Codex (high)").row.row_id == "openai/gpt-5.5:high"
        assert r.match("GPT-5.5 Pro").row.row_id == "openai/gpt-5.5-pro"

    def test_a_renamed_model_keeps_no_old_label(self, conn):
        store.ensure_row(
            conn,
            row_id="m",
            host_model_id="m",
            setting=None,
            label="Old Name",
            auto_created=False,
            source_key=None,
        )
        assert not store.ensure_row(
            conn,
            row_id="m",
            host_model_id="m",
            setting=None,
            label="New Name",
            auto_created=False,
            source_key=None,
        )
        label = conn.execute("SELECT display_label FROM bench_row WHERE row_id = 'm'").fetchone()
        assert label[0] == "New Name"


# ── parsing ──────────────────────────────────────────────────────────────────

TABLE_PAGE = (
    b"""<html><body><p>"""
    + b"x" * 3000
    + b"""</p><table>
<thead><tr><th></th><th>Model</th><th>Percent correct</th><th>Cost</th></tr></thead>
<tbody>
<tr><td>+</td><td>gpt-6-astra (max)</td><td>91.0%</td><td>$1</td></tr>
<tr class="details-row"><td colspan="4">details</td></tr>
<tr><td>+</td><td>Some Other Model</td><td>88.0%</td><td>$1</td></tr>
<tr><td>+</td><td>Kimi K3</td><td>88.0%</td><td>$1</td></tr>
<tr><td>+</td><td>Claude Opus 5.5</td><td>80.5%</td><td>$1</td></tr>
</tbody></table></body></html>"""
)

LIVEBENCH = (
    b"""<html><body><p>"""
    + b"x" * 3000
    + b"""</p><table>
<thead><tr><th></th><th>Model</th><th>Overall \xe2\x96\xbc</th><th>Agentic</th></tr></thead>
<tbody>
<tr><td>></td><td class="mdl-col"><div>
<span class="nm" data-tip="GPT-6 Astra \xc2\xb7 reasoning effort: max">GPT-6 Astra</span>
</div></td><td>86.1</td><td>82.4</td></tr>
<tr><td>></td><td class="mdl-col"><div>
<span class="nm" data-tip="Kimi K3 \xc2\xb7 reasoning effort: max">Kimi K3</span>
<span class="opn">open</span></div></td><td>70.2</td><td>60.0</td></tr>
</tbody></table></body></html>"""
)


def _swebench(entries):
    data = [{"name": "Lite", "results": []}, {"name": "Verified", "results": entries}]
    return (
        b"<html><body>"
        + b"x" * 3000
        + b'<script type="application/json" id="leaderboard-data">'
        + json.dumps(data).encode()
        + b"</script></body></html>"
    )


def _json_page(tables):
    """A page that ships its tables as <script type="application/json" id=...>."""
    blocks = b"".join(
        b'<script type="application/json" id="'
        + key.encode()
        + b'">'
        + json.dumps(rows).encode()
        + b"</script>"
        for key, rows in tables.items()
    )
    return b"<html><body>" + b"x" * 3000 + blocks + b"</body></html>"


JSON_TABLES = {
    "gpqa_diamond": [
        {
            "Model version": "gpt-6-astra_max",
            "mean_score": "0.9577",
            "Started at": "2026-08-30T14:57:43.000Z",
        },
        {
            "Model version": "gpt-6-astra_turbo",
            "mean_score": "0.90",
            "Started at": "2026-08-30T14:57:43.000Z",
        },
        {
            "Model version": "gpt-5.6-luna_max",
            "mean_score": "0.80",
            "Started at": "2026-08-30T14:57:43.000Z",
        },
    ],
    "fx_math_a": [
        {
            "Model version": "gpt-6-astra_max",
            "mean_score": "1.0",
            "Started at": "2026-08-30T14:57:43.000Z",
        },
    ],
    "fx_math_b": [
        {
            "Model version": "claude-opus-5-5_max",
            "mean_score": "0.9123",
            "Started at": "2026-09-01T00:00:00.000Z",
        },
    ],
    "fx_math_c": [
        {
            "Model version": "old-model",
            "mean_score": "0.5",
            "Started at": "2025-01-01T00:00:00.000Z",
        },
    ],
    "swe_bench_verified": [
        {
            "Model version": "claude-opus-5-5",
            "mean_score": "0.75",
            "Started at": "2026-02-10T00:00:00.000Z",
        },
        {
            "Model version": "claude-opus-5-5",
            "mean_score": "0.78",
            "Started at": "2026-02-18T00:00:00.000Z",
        },
    ],
    "hle_external": [
        {"Model version": "gpt-6-astra_unknown", "Accuracy": "0.548"},
    ],
}


def _next_flight_page(objects):
    """A page carrying its data the way Next.js does: JSON inside a JS string."""
    data = json.dumps({"data": objects}, separators=(",", ":"))  # compact, as pages ship it
    payload = json.dumps(data)[1:-1]  # escaped as the inside of a JS string
    return (
        b"<html><body>"
        + b"x" * 3000
        + b'<script>self.__next_f.push([1,"'
        + payload.encode()
        + b'"])</script></body></html>'
    )


MMLU_PRO = (
    b"<html><body>"
    + b"x" * 3000
    + b"""
<table><tr><th>Models</th><th>Data Source</th><th>Overall</th></tr>
<tr><td>Pinned</td><td>TIGER-Lab</td><td>0.99</td></tr></table>
<table><tr><th>Models</th><th>Data Source</th><th>Overall</th></tr>
<tr><td>Kimi K3</td><td>TIGER-Lab</td><td>0.9116</td></tr>
<tr><td>B</td><td>Self-Reported</td><td>0.9</td></tr>
<tr><td>C</td><td>TIGER-Lab</td><td>0.8</td></tr>
<tr><td>D</td><td>TIGER-Lab</td><td>0.7</td></tr>
</table></body></html>"""
)


class TestParse:
    def test_next_flight_reads_the_pages_own_model_objects_once_each(self, config):
        astra = {
            "id": "e05a4828-0536-4876-870d-a235023f992b",
            "slug": "gpt-6-astra-max",
            "shortName": "GPT-6 Astra (max)",
            "creator": {"name": "OpenAI"},
            "gpqa": 0.9606,
        }
        other = {
            "id": "11111111-0536-4876-870d-a235023f992b",
            "slug": "other",
            "shortName": "Other",
            "creator": {"name": "X"},
            "gpqa": 0.5,
        }
        page = _next_flight_page([astra, other, astra])  # the page repeats objects
        parsed = parse(config.source("aa_gpqa_diamond"), page, url="u")
        assert not parsed.problems and parsed.rows_parsed == 2
        assert {(o.raw_model_name, o.raw_text) for o in parsed.observations} == {
            ("GPT-6 Astra (max)", "0.9606"),
            ("Other", "0.5"),
        }

    def test_scale_entries_split_model_agent_and_setting_from_the_full_view(self, config):
        full = {
            "key": "full",
            "label": "Full",
            "entries": [
                {"model": "GPT-6-Astra (Codex) high", "rank": 5, "score": 96.9},
                {"model": "Kimi-K3 (mini-swe-agent) max", "rank": 4, "score": 97.7},
            ],
        }
        hard = {
            "key": "hard",
            "label": "Hard",
            "entries": [
                {"model": "GPT-6-Astra (Codex) high", "rank": 9, "score": 50.0},
            ],
        }
        parsed = parse(
            config.source("scale_swe_bench_pro"), _next_flight_page([full, hard]), url="u"
        )
        got = {
            (o.raw_model_name, o.variant, o.raw_setting, o.metric, o.raw_text)
            for o in parsed.observations
        }
        assert ("GPT-6-Astra", "Codex", "high", "score", "96.9") in got
        assert ("Kimi-K3", "mini-swe-agent", "max", "rank", "4") in got
        assert not any(
            o.raw_text == "50.0" for o in parsed.observations
        )  # the Hard view is not read

    def test_arc_cells_keep_their_raw_text_and_score_the_percent_number(self, config):
        page = (
            b"<html><body>" + b"x" * 3000 + b"<table><tr><th>AI System</th><th>Release Date</th>"
            b"<th>ARC-AGI-1</th><th>ARC-AGI-2</th></tr>"
            b"<tr><td>GPT-6.1 Sol (Max)</td><td>2026-09-29</td>"
            b"<td>96.5%, $0.095/task</td><td>94.2%, $0.254/task</td></tr></table></body></html>"
        )
        parsed = parse(config.source("arc_prize"), page, url="u")
        arc2 = next(o for o in parsed.observations if o.benchmark == "arc_agi_2")
        assert (
            arc2.raw_text == "94.2%, $0.254/task"
            and parse_score(arc2.raw_text, "percent").value == 94.2
        )

    def test_any_setup_column_accepts_a_stated_agent(self, config):
        obs = [
            _obs("scale_swe_bench_pro", 96.9, bench="swe_bench_pro", variant="Codex", priority=80)
        ]
        assert merge(config, obs, run_id=1)

    def test_a_pinned_copy_of_the_table_is_skipped_by_min_rows(self, config):
        parsed = parse(config.source("mmlu_pro_space"), MMLU_PRO, url="u")
        kimi = next(o for o in parsed.observations if o.raw_model_name == "Kimi K3")
        assert parsed.rows_parsed == 4 and kimi.raw_text == "0.9116" and kimi.variant == "TIGER-Lab"

    def test_html_table_skips_detail_rows_and_ranks_by_row_order_with_ties(self, config):
        parsed = parse(config.source("table_fixture"), TABLE_PAGE, url="https://example.test/table")
        assert parsed.rows_parsed == 4 and not parsed.problems
        ranks = {
            o.raw_model_name: (o.raw_text, o.rank_out_of)
            for o in parsed.observations
            if o.metric == "rank"
        }
        # 88.0 twice: both share rank 2, the next is 4
        # (standard competition ranking of the board's own order)
        assert ranks == {
            "gpt-6-astra (max)": ("1", 4),
            "Some Other Model": ("2", 4),
            "Kimi K3": ("2", 4),
            "Claude Opus 5.5": ("4", 4),
        }

    def test_a_missing_header_is_layout_changed_and_blocks(self, config):
        page = TABLE_PAGE.replace(b"Percent correct", b"Pass rate")
        parsed = parse(config.source("table_fixture"), page, url="u")
        assert parsed.blocked and parsed.problems[0][0] == "table_not_found"
        page = TABLE_PAGE.replace(b"<th>Model</th>", b"<th>Name</th>")
        parsed = parse(config.source("table_fixture"), page, url="u")
        assert parsed.blocked and parsed.problems[0][0] == "layout_changed"

    def test_livebench_reads_the_name_span_and_the_setting_tooltip(self, config):
        parsed = parse(
            config.source("livebench_leaderboard"), LIVEBENCH, url="https://livebench.ai/"
        )
        names = {(o.raw_model_name, o.raw_setting) for o in parsed.observations}
        assert names == {("GPT-6 Astra", "max"), ("Kimi K3", "max")}  # no "open" badge in the name

    def test_embedded_json_takes_the_verified_list_and_ranks_by_the_board_field(self, config):
        page = _swebench(
            [
                {
                    "model_display": "GPT-6 Astra",
                    "reasoning_effort": "max",
                    "agent": "mini-SWE-agent",
                    "resolved": 80.0,
                    "date": "2026-09-01",
                },
                {
                    "model_display": "Other",
                    "reasoning_effort": None,
                    "agent": "X",
                    "resolved": 85.0,
                    "date": "2026-09-01",
                },
            ]
        )
        parsed = parse(config.source("swebench_leaderboard"), page, url="https://www.swebench.com/")
        mine = [o for o in parsed.observations if o.raw_model_name == "GPT-6 Astra"]
        assert {(o.metric, o.raw_text) for o in mine} == {("score", "80.0"), ("rank", "2")}
        assert all(o.variant == "mini-SWE-agent" and o.raw_setting == "max" for o in mine)

    def test_embedded_json_reads_every_mapped_table(self, config):
        parsed = parse(config.source("json_fixture"), _json_page(JSON_TABLES), url="u")
        assert parsed.tables_found == 6 and not parsed.problems
        swe = [o for o in parsed.observations if o.benchmark == "swe_bench_verified"]
        assert {o.variant for o in swe} == {"fixture harness"} and {
            o.collected_on for o in swe
        } == {"2026-02-10", "2026-02-18"}

    def test_a_missing_data_block_blocks_the_source(self, config):
        tables = dict(JSON_TABLES)
        tables.pop("gpqa_diamond")
        parsed = parse(config.source("json_fixture"), _json_page(tables), url="u")
        assert parsed.blocked


# ── merge and changes ────────────────────────────────────────────────────────

NOW = datetime(2026, 10, 22, tzinfo=UTC)


def _obs(
    source,
    value,
    *,
    row="openai/gpt-6-astra",
    bench="gpqa_diamond",
    metric="score",
    priority=70,
    variant=None,
    date=None,
    stale=False,
    raw=None,
):
    return StoredObservation(
        source_key=source,
        row_id=row,
        benchmark_key=bench,
        metric=metric,
        value=value,
        rank_high=None,
        tied=False,
        rank_out_of=None,
        rank_board=None,
        variant=variant,
        raw_text=raw or str(value),
        raw_model_name="m",
        url="https://x",
        source_date=date,
        setting_not_stated=False,
        priority=priority,
        run_id=1,
        collected_at=NOW,
        stale=stale,
    )


class TestMerge:
    def test_a_column_no_longer_configured_publishes_nothing(self, config):
        assert "mmlu" not in config.benchmarks  # removed 2026-10-26
        assert merge(config, [_obs("vendor", 88.0, bench="mmlu", priority=90)], run_id=1) == {}

    def test_a_disagreement_names_the_raw_text_and_the_compared_number(self, config):
        obs = [
            _obs("scale_hle", 46.5, bench="hle", priority=80, raw="46.5"),
            _obs("aa_hle", 58.7, bench="hle", priority=70, raw="0.587"),
        ]
        flag = merge(config, obs, run_id=1)[("openai/gpt-6-astra", "hle", "score")].flags[0]
        assert "scale_hle says 46.5," in flag["message"]
        assert "aa_hle says 0.587 (= 58.7)" in flag["message"]

    def test_the_highest_priority_wins_and_a_disagreement_is_flagged(self, config):
        d = merge(
            config,
            [_obs("json_fixture", 90.0, priority=70), _obs("vendor", 95.0, priority=90)],
            run_id=1,
        )
        cell = d[("openai/gpt-6-astra", "gpqa_diamond", "score")]
        assert cell.cell.source_key == "vendor" and cell.rule == "rule 4 priority"
        assert cell.flags and cell.flags[0]["check"] == "disagreement"

    def test_within_tolerance_is_not_flagged(self, config):
        d = merge(config, [_obs("a", 90.0, priority=70), _obs("b", 91.0, priority=90)], run_id=1)
        assert not d[("openai/gpt-6-astra", "gpqa_diamond", "score")].flags

    def test_a_stale_value_never_competes(self, config):
        d = merge(config, [_obs("b", 95.0, priority=90, stale=True), _obs("a", 90.0)], run_id=1)
        assert d[("openai/gpt-6-astra", "gpqa_diamond", "score")].cell.source_key == "a"

    def test_a_setup_outside_the_accept_list_never_fills_the_column(self, config):
        obs = [
            _obs(
                "swebench_leaderboard",
                85.0,
                bench="swe_bench_verified",
                variant="TRAE",
                priority=80,
            )
        ]
        assert merge(config, obs, run_id=1) == {}

    def test_the_earlier_accepted_setup_beats_a_higher_priority_later_one(self, config):
        obs = [
            _obs(
                "swebench_leaderboard",
                70.0,
                bench="swe_bench_verified",
                variant="mini-SWE-agent",
                priority=60,
            ),
            _obs(
                "json_fixture",
                78.0,
                bench="swe_bench_verified",
                variant="fixture harness",
                priority=70,
            ),
        ]
        cell = merge(config, obs, run_id=1)[
            ("openai/gpt-6-astra", "swe_bench_verified", "score")
        ].cell
        assert cell.source_key == "swebench_leaderboard"

    def test_recency_then_alphabetical_decide_ties(self, config):
        d = merge(
            config,
            [_obs("b", 90.0, date="2026-09-01"), _obs("a", 90.0, date="2026-08-01")],
            run_id=1,
        )
        assert d[("openai/gpt-6-astra", "gpqa_diamond", "score")].cell.source_key == "b"
        d = merge(config, [_obs("b", 90.0), _obs("a", 90.0)], run_id=1)
        assert d[("openai/gpt-6-astra", "gpqa_diamond", "score")].rule == "rule 6 tie-break"


class TestDuplicates:
    def test_latest_takes_the_newest_rerun(self, config):
        obs = [
            _obs(
                "json_fixture",
                75.0,
                bench="swe_bench_verified",
                variant="fixture harness",
                date="2026-02-10",
            ),
            _obs(
                "json_fixture",
                78.0,
                bench="swe_bench_verified",
                variant="fixture harness",
                date="2026-02-18",
            ),
        ]
        key = ("openai/gpt-6-astra", "swe_bench_verified", "score")
        kept, reviews, _ = dedupe_source(obs, config.benchmarks, {key: "latest"})
        assert [o.value for o in kept] == [78.0] and not reviews

    def test_two_different_values_with_no_rule_to_choose_are_ambiguous_and_never_guessed(
        self, config
    ):
        obs = [_obs("s", 75.0), _obs("s", 78.0)]
        kept, reviews, counts = dedupe_source(obs, config.benchmarks, {})
        assert (
            kept == [] and reviews[0]["check"] == "ambiguous_duplicate" and counts["ambiguous"] == 1
        )

    def test_identical_values_keep_one(self, config):
        kept, reviews, _ = dedupe_source([_obs("s", 75.0), _obs("s", 75.0)], config.benchmarks, {})
        assert len(kept) == 1 and not reviews


def _cell(value, source="a", metric="score", bench="gpqa_diamond", out_of=None):
    return StoredCell(
        row_id="r",
        benchmark_key=bench,
        metric=metric,
        value=value,
        rank_high=None,
        tied=False,
        rank_out_of=out_of,
        rank_board=None,
        variant=None,
        benchmark_version=None,
        source_key=source,
        url="u",
        raw_text=str(value),
        raw_model_name="m",
        source_date=None,
        setting_not_stated=False,
        collected_at=NOW,
        needs_review=False,
        run_id=1,
    )


class TestChanges:
    def test_each_change_type(self, config):
        k = lambda b: ("r", b, "score")  # noqa: E731
        prev = {
            k("gpqa_diamond"): _cell(90.0),
            k("hle"): _cell(40.0, bench="hle"),
            k("mmlu_pro"): _cell(80.0, bench="mmlu_pro"),
            k("mmmu_pro"): _cell(70.0, bench="mmmu_pro"),
        }
        new = {
            k("gpqa_diamond"): _cell(92.0),
            k("hle"): _cell(40.0, bench="hle", source="b"),
            k("mmlu_pro"): _cell(80.0, bench="mmlu_pro"),
            k("livebench"): _cell(60.0, bench="livebench"),
        }
        types = {
            c["benchmark_key"]: c["change_type"]
            for c in diff(config, prev, new, reason="manual_run", actor="t")
        }
        assert types == {
            "gpqa_diamond": "updated",
            "hle": "source_changed",
            "mmmu_pro": "removed",
            "livebench": "added",
        }

    def test_a_lower_rank_is_better(self, config):
        assert direction(config, "livebench", "rank", 5, 3) == "better"
        assert direction(config, "livebench", "score", 80, 70) == "worse"


# ── config (L1) ──────────────────────────────────────────────────────────────


class TestConfig:
    def test_the_shipped_config_passes(self, config):
        # Scraping only (2026-10-22): there is no data-file method at all.
        from collect.benchmarks.config import METHODS

        assert {"static", "browser"} == METHODS and "allow_data_files" not in config.settings
        enabled = {s.key for s in config.sources if s.enabled}
        assert {"livebench_leaderboard", "arc_prize", "scale_swe_bench_pro", "vals_ioi"} <= enabled
        for s in config.sources:
            assert s.license and s.attribution

    def test_the_shipped_config_lists_only_sources_a_run_reads(self):
        # Disabled sources only printed a SKIP line every run (removed 2026-10-26).
        shipped = load()
        assert shipped.sources and all(s.enabled for s in shipped.sources)
        assert not {s.key for s in shipped.sources} & {"table_fixture", "json_fixture"}
        assert not {k for k in shipped.benchmarks if k.startswith("fx_")}

    def test_removed_columns_are_not_on_the_page(self):
        from judge import benchmarks as page

        sections, columns = page._columns()
        assert "mmlu_score" not in columns and "arena_rating" not in columns
        assert "human_pref" not in {s["key"] for s in sections}
        assert {"arc_agi_2_score", "aime_2026_score", "swe_bench_pro_score"} <= set(columns)

    def test_a_mapping_to_a_metric_the_column_does_not_have_stops_startup(self, tmp_path):
        for name in TEST_CONFIG_DIR.glob("*.yaml"):
            (tmp_path / name.name).write_text(name.read_text(encoding="utf-8"), encoding="utf-8")
        sources = tmp_path / "sources.yaml"
        sources.write_text(
            sources.read_text(encoding="utf-8").replace(
                '"Percent correct": { benchmark: fx_coding, metric: score',
                '"Percent correct": { benchmark: fx_coding, metric: rating',
            ),
            encoding="utf-8",
        )
        with pytest.raises(ConfigError) as caught:
            load(tmp_path)
        assert any("fx_coding_rating" in p for p in caught.value.problems)


# ── a whole run, against a disposable database ───────────────────────────────


class FakeFetcher:
    """Serves the hand-written pages; any source not listed fails like a dead site."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def fetch(self, source, *, wait_for=None):
        self.calls.append(source.key)
        content = self.pages.get(source.key)
        if content is None:
            return Fetched(
                ok=False,
                method=source.method,
                url=source.url,
                error="fetch_error",
                detail="HTTP 503",
            )
        return Fetched(
            ok=True,
            method=source.method,
            url=source.url,
            http_status=200,
            content=content,
            final_url=source.url,
        )

    def close(self):
        pass


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema

    assert_safe_target(test_dsn)
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        assert_disposable(c, test_dsn)
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        apply_schema(c)
        c.commit()
        yield c


PAGES = {
    "table_fixture": TABLE_PAGE,
    "livebench_leaderboard": LIVEBENCH,
    "json_fixture": _json_page(JSON_TABLES),
    "swebench_leaderboard": _swebench(
        [{"model_display": "Other", "agent": "X", "resolved": 85.0, "date": "2026-01-01"}]
    ),
}


#: Run logs from tests go here, never into the repo's collect/benchmarks/logs.
LOG_DIR = tempfile.mkdtemp(prefix="bench-test-logs-")


def _run(conn, pages, *, aliases=None, fetcher=None, registry=None, **kw):
    """A run over the hand-written pages, with the two test-only sources on."""
    import dataclasses

    from collect.benchmarks import runner

    config = load(TEST_CONFIG_DIR)
    fixture_sources = {"table_fixture", "json_fixture"}
    config = dataclasses.replace(
        config,
        settings={**config.settings, "log_dir": LOG_DIR},
        sources=tuple(
            dataclasses.replace(s, enabled=True) if s.key in fixture_sources else s
            for s in config.sources
        ),
    )
    out = io.StringIO()
    original = runner.load
    runner.load = lambda: config
    try:
        code = run(
            conn=conn,
            fetcher=fetcher or FakeFetcher(pages),
            seeds=SEEDS,
            stream=out,
            verbosity="normal",
            registry_aliases=aliases if aliases is not None else {},
            registry_models=registry or [],
            **kw,
        )
    finally:
        runner.load = original
    return code, out.getvalue()


class TestDatedReleases:
    """A known model's name + a date is a dated release with its own row (2026-10-23)."""

    @pytest.mark.parametrize(
        "name,row_id,label",
        [
            ("GPT-6 Astra (12/25)", "openai/gpt-6-astra@12-25", "GPT 6 Astra (12/25)"),
            ("gpt-6-astra-0813", "openai/gpt-6-astra@0813", "GPT 6 Astra 0813"),
            ("gpt-6-astra-2026-09-03", "openai/gpt-6-astra@2026-09-03", "GPT 6 Astra 2026-09-03"),
            ("gpt-6-astra-20260903", "openai/gpt-6-astra@20260903", "GPT 6 Astra 20260903"),
            (
                "GPT-6 Astra (November 2024)",
                "openai/gpt-6-astra@november-2024",
                "GPT 6 Astra (November 2024)",
            ),
        ],
    )
    def test_a_dated_name_gets_its_own_row_never_the_models(self, resolver, name, row_id, label):
        m = resolver.match(name)
        assert m.row.row_id == row_id and m.row.label == label and m.row.dated
        assert m.row.row_id != "openai/gpt-6-astra"

    def test_a_dated_name_with_a_setting(self, resolver):
        m = resolver.match("GPT-6 Astra 0813 (max)")
        assert m.row.row_id == "openai/gpt-6-astra@0813:max" and m.row.dated == "0813"

    def test_a_number_that_is_not_a_date_is_not_a_release(self, resolver):
        # month 13 is no date: "GPT-6 Astra 1399" is a different model name
        assert resolver.match("GPT-6 Astra 1399").row is None

    def test_the_base_name_drops_setting_and_date(self, resolver):
        assert resolver.base_name("GPT-5.2 (xhigh)") == "GPT-5.2"
        assert resolver.base_name("gpt-5.2-2025-12-11") == "gpt-5.2"
        assert resolver.match("Mystery Model 2 (high)").base_name == "Mystery Model 2"


class TestNameDecisions:
    """Same model as / Add as new row / Ignore, from the Unmatched tab (2026-10-23)."""

    def _decide(self, conn, key, name, action, target=None):
        conn.execute(
            "INSERT INTO bench_name_decision (name_key, name, action, target_model_id, actor) "
            "VALUES (%s, %s, %s, %s, 'test')",
            (key, name, action, target),
        )
        conn.commit()

    def test_each_decision_applies_on_the_next_run(self, conn):
        page = LIVEBENCH.replace(b">Kimi K3</span>", b">Kimi Three</span>")
        pages = {**PAGES, "livebench_leaderboard": page}
        _run(conn, pages)
        listed = {r[0] for r in conn.execute("SELECT base_name FROM bench_unmatched").fetchall()}
        # Not in the registry, so not listed (2026-10-26); a decision still applies.
        assert "Kimi Three" not in listed and "Some Other Model" not in listed

        self._decide(conn, "kimi-three", "Kimi Three", "alias", "moonshotai/kimi-k3")
        # Only registry models get rows (2026-10-26): a leftover "new row" decision
        # for a model outside the registry is skipped, and the run says so.
        self._decide(conn, "some-other-model", "Some Other Model", "new_row")
        _, out = _run(conn, pages)
        cells = store.load_cells(conn)
        assert ("moonshotai/kimi-k3:max", "livebench", "score") in cells
        assert not any(k[0].startswith("added/") for k in cells)
        assert "not applied - only registry models get rows: Some Other Model" in out

    def test_a_similar_name_is_listed_and_one_click_makes_it_an_alias(self, conn, monkeypatch):
        from judge import benchmarks as page

        monkeypatch.setattr(page, "_seeds", lambda: [{"id": s.id, "name": s.name} for s in SEEDS])
        pages = {
            **PAGES,
            "livebench_leaderboard": LIVEBENCH.replace(
                b">Kimi K3</span>", b">Kimi K3 Instruct</span>"
            ),
        }
        _, out = _run(conn, pages)
        assert "looks like moonshotai/kimi-k3" in out
        group = next(g for g in page.unmatched(conn)["groups"] if g["name"] == "Kimi K3 Instruct")
        assert group["decidable"] and group["reasons"] == ["similar_to_registry"]
        assert group["similar_to"] == [{"id": "moonshotai/kimi-k3", "name": "Kimi K3"}]
        page.decide(
            conn, key=group["key"], name=group["name"], action="alias", target="moonshotai/kimi-k3"
        )
        conn.commit()
        _run(conn, pages)
        assert ("moonshotai/kimi-k3:max", "livebench", "score") in store.load_cells(conn)
        assert all(g["name"] != "Kimi K3 Instruct" for g in page.unmatched(conn)["groups"])

    def test_the_page_no_longer_offers_a_new_row(self, conn):
        from judge import benchmarks as page

        with pytest.raises(page.DecisionRefused):
            page.decide(conn, key="x", name="X", action="new_row", target=None)

    def test_only_registry_models_are_listed_and_ignore_still_hides_one(self, conn):
        _run(conn, PAGES)
        rows = conn.execute("SELECT raw_name, reason FROM bench_unmatched").fetchall()
        assert rows and all(reason != "unmatched" for _, reason in rows)
        assert ("gpt-6-astra_turbo", "unknown_setting") in rows  # a known model, unread setting
        self._decide(conn, "gpt-6-astra", "gpt-6-astra", "ignore")
        _run(conn, PAGES)
        listed = {r[0] for r in conn.execute("SELECT raw_name FROM bench_unmatched").fetchall()}
        assert "gpt-6-astra_turbo" not in listed

    def test_the_page_groups_names_and_validates_a_decision(self, conn, monkeypatch):
        from judge import benchmarks as page

        monkeypatch.setattr(page, "_seeds", lambda: [{"id": s.id, "name": s.name} for s in SEEDS])
        _run(conn, PAGES)
        data = page.unmatched(conn)
        assert all(g["name"] != "Some Other Model" for g in data["groups"])  # not in the registry
        group = next(g for g in data["groups"] if g["name"] == "gpt-6-astra")
        assert not group["decidable"] and group["sources"] == ["json_fixture"]
        with pytest.raises(page.DecisionRefused):
            page.decide(conn, key=group["key"], name=group["name"], action="alias", target="nope/x")
        page.decide(conn, key=group["key"], name=group["name"], action="ignore", target=None)
        data = page.unmatched(conn)
        assert all(g["key"] != group["key"] for g in data["groups"])
        assert data["decisions"][0]["action"] == "ignore"
        assert page.undo_decision(conn, key=group["key"])["undone"]


class TestRegistryModels:
    """Untracked registry models with aliases get rows below the tracked ones,
    only once a source lists them (Parvathi, 2026-10-22)."""

    def test_a_registry_model_sharing_a_tracked_models_name_is_left_out(self, config):
        dup = SeedModel("openai/gpt-6-astra-dup", "GPT-6 Astra")  # a second entry, same model
        other = SeedModel("openai/gpt-5.4", "GPT-5.4")
        r = Resolver(config, SEEDS, {}, [dup, other])
        assert r.match("GPT-6 Astra").row.row_id == "openai/gpt-6-astra"  # tracked wins
        assert "openai/gpt-6-astra-dup" not in r.registry_ids and r.warnings
        assert r.match("gpt-5.4 (high)").row.row_id == "openai/gpt-5.4:high"

    def test_the_same_id_spelled_with_a_dot_is_an_alias_not_a_duplicate(self, config):
        # The registry's anthropic/claude-fable-5.1 is the tracked
        # anthropic/claude-fable-5-1 (2026-10-26): folded in, with no warning.
        seeds = [*SEEDS, SeedModel("anthropic/claude-fable-5-1", "Claude Fable 5.1")]
        dotted = SeedModel("anthropic/claude-fable-5.1", "Claude Fable 5.1")
        r = Resolver(
            config, seeds, {"anthropic/claude-fable-5.1": ["Fable 5.1 Thinking"]}, [dotted]
        )
        assert not r.warnings and "anthropic/claude-fable-5.1" not in r.registry_ids
        assert r.match("anthropic/claude-fable-5.1").row.row_id == "anthropic/claude-fable-5-1"
        assert r.match("Fable 5.1 Thinking").row.row_id == "anthropic/claude-fable-5-1"

    def test_gemini_3_flash_is_not_the_preview(self, config):
        # The registry lists "Gemini 3 Flash" as an alias of the PREVIEW; the two
        # are kept apart (2026-10-23). The released model is not in the registry,
        # so it gets no row and is not offered as like the preview (2026-10-26).
        preview = SeedModel("google/gemini-3-flash-preview", "Gemini 3 Flash Preview")
        r = Resolver(
            config,
            SEEDS,
            {
                "google/gemini-3-flash-preview": [
                    "Gemini 3 Flash",
                    "gemini-3-flash-preview",
                    "gemini-flash-3",  # the registry has this one too
                ]
            },
            [preview],
        )
        m = r.match("Gemini 3 Flash (high)")
        assert m.row is None and m.reason == "unmatched" and not m.similar_to
        assert r.match("gemini-3-flash-preview").row.row_id == "google/gemini-3-flash-preview"

    def test_a_declared_model_outside_the_registry_is_a_config_problem(self, tmp_path):
        for name in TEST_CONFIG_DIR.glob("*.yaml"):
            (tmp_path / name.name).write_text(name.read_text(encoding="utf-8"), encoding="utf-8")
        extras = tmp_path / "model_extras.yaml"
        extras.write_text(
            extras.read_text(encoding="utf-8")
            + '\nunregistered/x:\n  not_in_registry: true\n  name: "X"\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError) as caught:
            load(tmp_path)
        assert any("only registry models get rows" in p for p in caught.value.problems)

    def test_a_matched_registry_model_gets_a_row_in_its_own_group(self, conn, monkeypatch):
        from judge import benchmarks as page

        page_html = LIVEBENCH.replace(b">Kimi K3</span>", b">GPT-5.4</span>")
        reg = [SeedModel("openai/gpt-5.4", "GPT-5.4"), SeedModel("z-ai/glm-4.7", "GLM 4.7")]
        code, out = _run(conn, {**PAGES, "livebench_leaderboard": page_html}, registry=reg)
        assert code == 0, out
        rows = store.existing_rows(conn)
        assert {"openai/gpt-5.4", "openai/gpt-5.4:max"} <= rows
        assert "z-ai/glm-4.7" not in rows  # listed nowhere: no empty row
        monkeypatch.setattr(page, "_seeds", lambda: [{"id": s.id, "name": s.name} for s in SEEDS])
        data = page.table(conn)
        groups = [r["group"] for r in data["rows"]]
        assert groups[: len(SEEDS)] == ["tracked"] * len(SEEDS) and groups[len(SEEDS) :] == [
            "registry"
        ]
        reg_row = data["rows"][-1]
        assert reg_row["label"] == "GPT-5.4" and reg_row["children"][0]["cells"]["livebench_score"]


class TestScrapingFirst:
    def test_a_registry_alias_matches_exactly(self, conn):
        page = LIVEBENCH.replace(b">GPT-6 Astra</span>", b">Astra Six</span>")
        code, _ = _run(
            conn,
            {**PAGES, "livebench_leaderboard": page},
            aliases={"openai/gpt-6-astra": ["Astra Six"]},
        )
        assert code == 0
        assert ("openai/gpt-6-astra:max", "livebench", "score") in store.load_cells(conn)


class TestARun:
    def test_a_run_publishes_raw_values_into_setting_rows(self, conn):
        code, out = _run(conn, PAGES)
        assert code == 0, out
        cells = store.load_cells(conn)
        astra = cells[("openai/gpt-6-astra:max", "gpqa_diamond", "score")]
        assert (
            astra.value == 95.77
            and astra.raw_text == "0.9577"
            and astra.source_key == "json_fixture"
        )
        assert cells[("openai/gpt-6-astra:max", "livebench", "rank")].value == 1
        assert cells[("openai/gpt-6-astra:max", "fx_coding", "score")].value == 91.0
        # the newest re-run, in the fixture's harness
        swe = cells[("anthropic/claude-opus-5.5", "swe_bench_verified", "score")]
        assert swe.value == 78.0 and swe.variant == "fixture harness"
        # "_unknown": the model's own row, marked
        assert cells[("openai/gpt-6-astra", "hle", "score")].setting_not_stated
        rows = store.existing_rows(conn)
        assert (
            "openai/gpt-6-astra:max" in rows and "openai/gpt-6-luna" in rows
        )  # every seed has its row
        kinds = {r[0] for r in conn.execute("SELECT change_type FROM bench_change").fetchall()}
        assert kinds == {"added", "variant_added"}
        status = conn.execute("SELECT status FROM bench_run ORDER BY id DESC LIMIT 1").fetchone()[0]
        assert status == "partial"  # hle_lastexam and livecodebench are not served
        assert "NO VALUES YET" in out and "SUMMARY" in out
        reviews = {
            r[0] for r in conn.execute("SELECT check_code FROM bench_review_item").fetchall()
        }
        assert "unknown_setting" in reviews  # gpt-6-astra_turbo
        unmatched = {r[0] for r in conn.execute("SELECT raw_name FROM bench_unmatched").fetchall()}
        assert "gpt-5.6-luna_max" not in unmatched  # not in the registry: not listed

    def test_a_second_identical_run_changes_nothing(self, conn):
        _run(conn, PAGES)
        before = store.load_cells(conn)
        code, out = _run(conn, PAGES)
        assert code == 0
        assert store.load_cells(conn).keys() == before.keys()
        last = conn.execute("SELECT max(run_id) FROM bench_change").fetchone()[0]
        assert last == 1 and "content unchanged" in out

    def test_an_item_a_later_run_does_not_raise_is_resolved(self, conn):
        _run(conn, PAGES)
        open_before = conn.execute(
            "SELECT count(*) FROM bench_review_item WHERE status = 'open' "
            "AND check_code = 'unknown_setting'"
        ).fetchone()[0]
        assert open_before > 0  # gpt-6-astra_turbo: no such setting word
        conn.execute(
            "UPDATE bench_review_item SET message = 'an older message nobody raises now' "
            "WHERE check_code = 'unknown_setting'"
        )
        conn.commit()
        _, out = _run(conn, PAGES)
        resolved = conn.execute(
            "SELECT count(*) FROM bench_review_item WHERE status = 'resolved'"
        ).fetchone()[0]
        assert resolved == open_before and "resolved" in out

    def test_a_problem_seen_again_is_not_a_second_review_item(self, conn):
        _run(conn, PAGES)
        count = "SELECT count(*) FROM bench_review_item"
        first = conn.execute(count).fetchone()[0]
        _, out = _run(conn, PAGES)
        assert first > 0 and conn.execute(count).fetchone()[0] == first
        assert "0 new review items" in out

    def test_a_source_no_longer_read_stops_publishing_and_goes_stale(self, conn):
        # 2026-10-26: renaming a source left its values in the table,
        # because only sources read in a run were cleaned up.
        _run(conn, PAGES)
        assert ("openai/gpt-6-astra:max", "livebench", "score") in store.load_cells(conn)
        conn.execute(
            "UPDATE bench_observation SET source_key = 'old_renamed_source' "
            "WHERE source_key = 'livebench_leaderboard'"
        )
        conn.execute(
            "UPDATE bench_cell SET source_key = 'old_renamed_source' "
            "WHERE source_key = 'livebench_leaderboard'"
        )
        conn.commit()
        pages = dict(PAGES)
        pages.pop(
            "livebench_leaderboard"
        )  # the live source fails, so only the old key holds values
        _, out = _run(conn, pages)
        assert ("openai/gpt-6-astra:max", "livebench", "score") not in store.load_cells(conn)
        stale = conn.execute(
            "SELECT bool_and(stale) FROM bench_observation WHERE source_key = 'old_renamed_source'"
        ).fetchone()[0]
        assert stale and "old_renamed_source" in out

    def test_the_newest_of_two_same_setup_entries_wins(self, config):
        obs = [
            _obs(
                "swebench_leaderboard",
                72.8,
                bench="swe_bench_verified",
                variant="mini-SWE-agent",
                date="2026-02-17",
            ),
            _obs(
                "swebench_leaderboard",
                71.8,
                bench="swe_bench_verified",
                variant="mini-SWE-agent",
                date="2025-12-11",
            ),
        ]
        key = ("openai/gpt-6-astra", "swe_bench_verified", "score")
        policy = config.source("swebench_leaderboard").tables[0].duplicates
        kept, reviews, _ = dedupe_source(obs, config.benchmarks, {key: policy})
        assert policy == "latest" and [o.value for o in kept] == [72.8] and not reviews

    def test_a_failing_source_keeps_its_previous_values(self, conn):
        _run(conn, PAGES)
        pages = dict(PAGES)
        pages.pop("livebench_leaderboard")
        code, out = _run(conn, pages)
        assert code == 0 and "previous values kept" in out
        assert ("openai/gpt-6-astra:max", "livebench", "score") in store.load_cells(conn)

    def test_a_dry_run_publishes_nothing(self, conn):
        code, out = _run(conn, PAGES, dry_run=True)
        assert code == 0 and "NOT written" in out
        assert store.load_cells(conn) == {}
        assert conn.execute("SELECT status FROM bench_run").fetchone()[0] == "dry_run"

    def test_a_value_that_drops_off_the_board_goes_stale_and_the_cell_is_removed(self, conn):
        _run(conn, PAGES)
        page = LIVEBENCH.replace(b"Kimi K3</span>", b"Kimi K9</span>")
        pages = {**PAGES, "livebench_leaderboard": page}
        _run(conn, pages)
        assert ("moonshotai/kimi-k3:max", "livebench", "score") not in store.load_cells(conn)
        removed = conn.execute(
            "SELECT count(*) FROM bench_change WHERE change_type = 'removed'"
        ).fetchone()[0]
        assert removed >= 1

    def test_one_run_at_a_time(self, conn, test_dsn):
        with psycopg.connect(test_dsn) as other:
            assert store.try_lock(other)
            code, out = _run(conn, PAGES)
            store.unlock(other)
        assert code == 3 and "one run at a time" in out

    def test_the_page_reads_the_table_with_setting_rows_nested(self, conn, monkeypatch):
        from judge import benchmarks as page

        _run(conn, PAGES)
        monkeypatch.setattr(page, "_seeds", lambda: [{"id": s.id, "name": s.name} for s in SEEDS])
        data = page.table(conn)
        astra = next(r for r in data["rows"] if r["row_id"] == "openai/gpt-6-astra")
        child = next(c for c in astra["children"] if c["setting"] == "max")
        cell = child["cells"]["gpqa_diamond_score"]
        # RAW: exactly what the source printed - no "%" added, no conversion, no rounding
        assert cell["display"] == "0.9577" and cell["raw_text"] == "0.9577" and cell["source_label"]
        assert "value" not in cell  # the one-unit figure is for the checks only
        assert cell["sort"] == pytest.approx(95.77)  # ...and for sorting the column
        assert child["cells"]["livebench_rank"]["display"] == "1"
        assert child["cells"]["livebench_score"]["display"] == "86.1"
        in_table = {s["key"] for s in data["sources"] if s["in_table"]}
        assert in_table >= {"json_fixture", "livebench_leaderboard"} and "attribution" not in data
        assert data["counts"]["benchmarks"] < data["counts"]["columns"]
        log = page.changelog(conn)
        assert log["total"] > 0 and log["entries"][0]["type"] in ("added", "variant_added")
        added = {(e["row"], e["column"]): e["new"] for e in log["entries"] if e["type"] == "added"}
        assert added[("GPT 6 Astra (max)", "GPQA Diamond")] == "0.9577"
        runs = page.runs(conn)["runs"]
        detail = page.run_detail(conn, run_id=runs[0]["id"])
        assert detail["done"] and "BENCHMARK RUN" in detail["log"]


class TestStartingARun:
    def test_a_run_starts_on_a_connection_left_in_a_transaction(self, conn):
        # PR #573 review, the blocker: the CLI's preflight reads and leaves a
        # transaction open, and switching to autocommit then raised.
        conn.autocommit = False
        conn.execute("SELECT 1")
        code, out = _run(conn, PAGES)
        assert code == 0, out
        assert conn.autocommit

    def test_a_non_local_target_is_refused(self, monkeypatch):
        from judge import benchmarks as page

        monkeypatch.setenv("BENCHMARKS_DATABASE_URL", "postgresql://u@db.example.com:5432/x")
        with pytest.raises(page.RunRefused, match="local-only"):
            page.start_run(None, dry_run=True, use_snapshot=False)

    def test_reparse_is_refused_until_a_page_has_been_saved(self, conn, monkeypatch, test_dsn):
        # Run #1 on 2026-10-22: Re-parse pressed on an empty database ran, and
        # every source failed "no snapshot". It is refused before it starts now.
        from judge import benchmarks as page

        monkeypatch.setenv("BENCHMARKS_DATABASE_URL", test_dsn)
        with pytest.raises(page.RunRefused, match="nothing to re-parse"):
            page.start_run(conn, dry_run=False, use_snapshot=True)
        assert conn.execute("SELECT count(*) FROM bench_run").fetchone()[0] == 0

    def test_a_running_run_refuses_a_second(self, conn, monkeypatch, test_dsn):
        from judge import benchmarks as page

        monkeypatch.setenv("BENCHMARKS_DATABASE_URL", test_dsn)
        store.start_run(conn, trigger="manual_run", scope="all", dry_run=False, request_id=None)
        conn.commit()
        with pytest.raises(page.RunRefused, match="still running"):
            page.start_run(conn, dry_run=True, use_snapshot=False)

    def test_an_abandoned_run_is_closed(self, conn):
        rid = store.start_run(
            conn, trigger="manual_run", scope="all", dry_run=False, request_id=None
        )
        conn.execute(
            "UPDATE bench_run SET started_at = %s WHERE id = %s",
            (datetime.now(UTC) - timedelta(hours=3), rid),
        )
        assert store.close_abandoned_runs(conn, older_than_minutes=40) == [rid]


def _livebench(scores, release=None):
    """A LiveBench page: {name: overall} in order, with an optional release date."""
    head = (
        f'<div class="lb-tl-head"><span class="lab">Release</span>'
        f'<span class="date">{release}</span></div>'
        if release
        else ""
    )
    rows = "".join(
        f'<tr><td>></td><td><span class="nm" data-tip="{n} · reasoning effort: max">{n}</span>'
        f"</td><td>{v}</td><td>1</td></tr>"
        for n, v in scores.items()
    )
    return (
        "<html><body><p>" + "x" * 3000 + "</p>" + head + "<table><thead><tr><th></th>"
        "<th>Model</th><th>Overall ▼</th><th>Agentic</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></body></html>"
    ).encode()


LAB = [SeedModel(f"lab/m-{i}", f"Lab M{i}") for i in range(12)]


class TestListAndReleaseChanges:
    """Two false alarms seen in run #44 (2026-10-26): AA's GPQA page listing more
    models was blocked as a layout change, and LiveBench's new release raised
    eight large-jump flags."""

    def _reviews(self, conn):
        return [r[0] for r in conn.execute("SELECT check_code FROM bench_review_item").fetchall()]

    def test_a_longer_list_with_the_same_values_is_taken(self, conn):
        first = {f"Lab M{i}": 50 + i for i in range(4)}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(first)}, registry=LAB)
        longer = {**first, **{f"Lab M{i}": 40 + i for i in range(4, 12)}}  # 4 -> 12 rows
        _, out = _run(conn, {**PAGES, "livebench_leaderboard": _livebench(longer)}, registry=LAB)
        assert "the list changed: 4 of 4 values listed both times are unchanged" in out
        cells = store.load_cells(conn)
        assert ("lab/m-11:max", "livebench", "score") in cells

    def test_a_longer_list_with_different_values_is_still_blocked(self, conn):
        first = {f"Lab M{i}": 50 + i for i in range(4)}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(first)}, registry=LAB)
        other = {f"Lab M{i}": 10 + i for i in range(12)}  # every known value moved
        _, out = _run(conn, {**PAGES, "livebench_leaderboard": _livebench(other)}, registry=LAB)
        assert "suspected_layout_change" in out
        cells = store.load_cells(conn)
        assert cells[("lab/m-0:max", "livebench", "score")].raw_text == "50"  # kept
        assert ("lab/m-11:max", "livebench", "score") not in cells
        rows = {r[0] for r in conn.execute("SELECT row_id FROM bench_row").fetchall()}
        assert "lab/m-11" not in rows  # a blocked read adds no rows

    def test_a_new_release_is_not_flagged_as_jumps(self, conn):
        old = {"GPT 6 Astra": 86.1, "Kimi K3": 70.2}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(old, "2026-10-14")})
        new = {"Kimi K3": 90.0, "GPT 6 Astra": 40.0}  # big moves, and ranks swap
        _, out = _run(conn, {**PAGES, "livebench_leaderboard": _livebench(new, "2026-10-25")})
        assert "new release 2026-10-25 (last published run read 2026-10-14)" in out
        assert "large_jump" not in self._reviews(conn)
        cell = store.load_cells(conn)[("moonshotai/kimi-k3:max", "livebench", "score")]
        assert cell.raw_text == "90.0" and cell.source_date == "2026-10-25"
        notes = {r[0] for r in conn.execute("SELECT note FROM bench_change").fetchall()}
        assert "new release 2026-10-25 (was 2026-10-14)" in notes

    def test_the_same_release_with_a_big_move_is_still_flagged(self, conn):
        old = {"GPT 6 Astra": 86.1, "Kimi K3": 70.2}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(old, "2026-10-14")})
        moved = {"GPT 6 Astra": 86.1, "Kimi K3": 30.0}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(moved, "2026-10-14")})
        assert "large_jump" in self._reviews(conn)

    def test_the_release_is_read_from_the_page(self, config):
        from collect.benchmarks.parse import parse

        source = next(s for s in config.sources if s.key == "livebench_leaderboard")
        parsed = parse(source, _livebench({"Kimi K3": 1}, "2026-10-25"), url="u")
        assert parsed.release == "2026-10-25"
        assert {o.collected_on for o in parsed.observations} == {"2026-10-25"}

    def test_a_blocked_read_is_not_the_next_baseline(self, conn):
        first = {f"Lab M{i}": 50 + i for i in range(4)}
        page = {**PAGES, "livebench_leaderboard": _livebench(first)}
        _run(conn, page, registry=LAB)
        other = {f"Lab M{i}": 10 + i for i in range(12)}
        bad = {**PAGES, "livebench_leaderboard": _livebench(other)}
        _run(conn, bad, registry=LAB)
        _, out = _run(conn, bad, registry=LAB)  # the same bad read again
        assert "suspected_layout_change" in out

    def test_a_rank_move_is_never_a_review_item(self, conn):
        # Same release, so this is not the new-release case: ranks swap because
        # the scores moved a little. Ranks follow the board's list (2026-10-26).
        old = {"GPT 6 Astra": 86.1, "Kimi K3": 85.9}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(old, "2026-10-14")})
        swapped = {"Kimi K3": 86.2, "GPT 6 Astra": 86.1}
        _, out = _run(conn, {**PAGES, "livebench_leaderboard": _livebench(swapped, "2026-10-14")})
        assert "rank(s) moved - the board's list changed; not flagged" in out
        assert "large_jump" not in self._reviews(conn)
        moved = conn.execute(
            "SELECT count(*) FROM bench_change WHERE metric = 'rank' AND change_type = 'updated'"
        ).fetchone()[0]
        assert moved == 2  # both moves are in the changelog

    def test_the_changelog_filters_the_whole_log_by_kind(self, conn, monkeypatch):
        from judge import benchmarks as page

        monkeypatch.setattr(page, "_seeds", lambda: [{"id": s.id, "name": s.name} for s in SEEDS])
        old = {"GPT 6 Astra": 86.1, "Kimi K3": 85.9}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(old, "2026-10-14")})
        swapped = {"Kimi K3": 86.2, "GPT 6 Astra": 86.1}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(swapped, "2026-10-14")})
        everything = page.changelog(conn)
        assert everything["counts"]["rank"] == 2 and everything["counts"]["score"] == 1
        ranks = page.changelog(conn, kind="rank")["entries"]
        assert len(ranks) == 2 and all(
            e["metric"] == "rank" and e["type"] == "updated" for e in ranks
        )
        up = page.changelog(conn, kind="up")["entries"]
        assert up and all(e["direction"] == "better" for e in up)
        # Anything else is not a filter: the whole log comes back, never an error.
        assert len(page.changelog(conn, kind="1; DROP TABLE x")["entries"]) == len(
            everything["entries"]
        )


class TestNewsWorthy:
    """Debut / fresh / mover tags on the changelog (Parvathi, 2026-10-26): what
    happened, not just what the board read."""

    RELEASED = {"lab/new": date(2026, 10, 1), "lab/old": date(2025, 1, 1)}
    BASELINE = {"src": 1}

    def _tag(self, **change):
        from judge import benchmarks as page

        base = {
            "run_id": 5,
            "new_source": "src",
            "row_id": "lab/old:max",
            "metric": "score",
            "type": "added",
            "old_value": None,
            "new_value": 80.0,
            "changed_at": "2026-10-26T10:00:00+00:00",
            "source_date": None,
            "note": None,
        }
        return page._news({**base, **change}, self.RELEASED, self.BASELINE)

    def test_a_recent_model_showing_up_is_a_debut(self):
        assert self._tag(row_id="lab/new:max") == "debut"
        assert self._tag(row_id="lab/new@0902") == "debut"  # a dated release of it too

    def test_an_old_model_with_a_recently_dated_value_is_fresh(self):
        assert self._tag(source_date="2026-10-20") == "fresh"
        assert self._tag(source_date="2026-08-01") is None  # dated long ago: a backfill
        assert self._tag() is None  # no date at all: a backfill

    def test_a_sources_first_read_is_never_news(self):
        assert self._tag(run_id=1, row_id="lab/new:max") is None

    def test_movers_are_real_moves_on_the_same_release(self):
        moved = {"type": "updated", "old_value": 70.0}
        assert self._tag(**moved, new_value=72.0) == "mover"
        assert self._tag(**moved, new_value=70.4) is None  # under a point: noise
        assert self._tag(type="updated", metric="rank", old_value=5, new_value=4) == "mover"
        reset = {**moved, "new_value": 60.0, "note": "new release 2026-10-25 (was 2026-10-14)"}
        assert self._tag(**reset) is None
        assert self._tag(type="source_changed", old_value=70.0, new_value=90.0) is None

    def test_the_changelog_filters_and_counts_news(self, conn, monkeypatch):
        from judge import benchmarks as page

        monkeypatch.setattr(page, "_seeds", lambda: [{"id": s.id, "name": s.name} for s in SEEDS])
        old = {"GPT 6 Astra": 86.1, "Kimi K3": 70.0}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(old, "2026-10-14")})
        moved = {"GPT 6 Astra": 86.1, "Kimi K3": 75.0}  # same release, +5 points
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(moved, "2026-10-14")})
        log = page.changelog(conn)
        assert log["counts"]["mover"] >= 1 and log["counts"]["news"] >= log["counts"]["mover"]
        movers = page.changelog(conn, kind="mover")["entries"]
        assert movers and all(e["news"] == "mover" for e in movers)
        assert any(e["row"].startswith("Kimi K3") and e["new"] == "75.0" for e in movers)


class TestRowsNoSourceLists:
    """A row a run created goes once no source lists it (2026-10-26): Qwen3.8 Flash,
    Grok Build 0.1 and eleven setting rows were empty lines on the page."""

    def _rows(self, conn):
        return {r[0] for r in conn.execute("SELECT row_id FROM bench_row").fetchall()}

    def test_a_model_no_source_lists_any_more_is_removed(self, conn):
        listed = {"Lab M1": 50, "Lab M2": 40, "Lab M3": 30}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(listed)}, registry=LAB)
        assert {"lab/m-1", "lab/m-1:max"} <= self._rows(conn)
        fewer = {"Lab M2": 40, "Lab M3": 30}
        _, out = _run(conn, {**PAGES, "livebench_leaderboard": _livebench(fewer)}, registry=LAB)
        rows = self._rows(conn)
        assert "lab/m-1" not in rows and "lab/m-1:max" not in rows
        assert "lab/m-2:max" in rows and "no source lists any more removed" in out
        gone = conn.execute(
            "SELECT count(*) FROM bench_observation WHERE row_id LIKE 'lab/m-1%%'"
        ).fetchone()[0]
        assert gone == 0
        # It comes back the next time a source lists it.
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(listed)}, registry=LAB)
        assert "lab/m-1:max" in self._rows(conn)

    def test_a_failed_fetch_removes_nothing(self, conn):
        listed = {"Lab M1": 50, "Lab M2": 40}
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench(listed)}, registry=LAB)
        before = self._rows(conn)
        down = {k: v for k, v in PAGES.items() if k != "livebench_leaderboard"}
        _run(conn, down, registry=LAB)  # LiveBench answers 503
        assert self._rows(conn) == before

    def test_tracked_models_always_keep_their_row(self, conn):
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench({"Kimi K3": 70})})
        _run(conn, {**PAGES, "livebench_leaderboard": _livebench({"GPT 6 Astra": 80})})
        rows = self._rows(conn)
        assert "moonshotai/kimi-k3" in rows and "moonshotai/kimi-k3:max" not in rows
