"""The local VRAM tool ("Can I run it?", docs/proposals/can-i-run-it.md).

What these hold, in the order a reader would worry about them:

    THE SIZE SHOWN IS THE LISTED FILE'S, OR NOTHING. A listed file the repo no
    longer has leaves the size NULL and names the file - never a partial sum,
    never a look-alike (rules 6 and 12).

    NO WHOLE FILE IS EVER DOWNLOADED. The header is read by range, and a
    response that ignores the range is refused unread.

    THE CACHE IS EXACT WHERE THE HEADER SAYS ENOUGH, AN UPPER BOUND WHERE IT
    DOES NOT, AND UNKNOWN WHERE IT CANNOT BE WORKED OUT - checked against the
    50 real headers measured 2026-10-23.

    EVERY CONSTANT IS IN contract/, AND A MISSING ONE FAILS LOUDLY.

The database section needs Postgres; see docs/dev-database.md.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import struct
import subprocess
from datetime import UTC, datetime

import httpx
import psycopg
import pytest

from collect.local_models import gguf
from collect.local_models.poll import (
    LocalModel,
    LocalModelsContractError,
    ReadSettings,
    load_models,
    measure,
    read_header,
    write_rows,
)
from judge import local_models as view

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contract" / "tables.sql"
HEADERS = json.loads((ROOT / "docs" / "measurements" / "local-model-headers-2026-10-23.json")
                     .read_text(encoding="utf-8"))


# ── a GGUF header, built byte by byte ─────────────────────────────────────────


def _s(text: str) -> bytes:
    raw = text.encode()
    return struct.pack("<Q", len(raw)) + raw


def _kv(key: str, kind: int, payload: bytes) -> bytes:
    return _s(key) + struct.pack("<I", kind) + payload


def gguf_bytes(arch="llama", layers=32, kv_heads=8, extra=b"", extra_pairs=0,
               tail=1 << 16) -> bytes:
    pairs = [
        _kv("general.architecture", 8, _s(arch)),
        _kv("general.name", 8, _s("Test model")),
        _kv(f"{arch}.block_count", 4, struct.pack("<I", layers)),
        _kv(f"{arch}.attention.head_count_kv", 4, struct.pack("<I", kv_heads)),
        _kv(f"{arch}.embedding_length", 4, struct.pack("<I", 4096)),
        _kv(f"{arch}.attention.head_count", 4, struct.pack("<I", 32)),
        # The vocabulary: a string array, skipped and never stored.
        _kv("tokenizer.ggml.tokens", 9, struct.pack("<IQ", 8, 3) + _s("a") + _s("b") + _s("c")),
    ]
    head = b"GGUF" + struct.pack("<IQQ", 3, 2, len(pairs) + extra_pairs)
    return head + b"".join(pairs) + extra + b"\x00" * tail  # tail stands in for the tensors


class TestTheHeaderReader:
    def test_keeps_the_architecture_and_its_own_numbers(self):
        fields, end = gguf.parse_header(gguf_bytes())
        assert fields == {"architecture": "llama", "block_count": 32,
                          "attention.head_count_kv": 8, "embedding_length": 4096,
                          "attention.head_count": 32}
        assert end < len(gguf_bytes())

    def test_a_per_layer_array_is_kept(self):
        per_layer = struct.pack("<IQ", 4, 3) + struct.pack("<3I", 8, 8, 1)
        arr = _kv("gemma4.attention.head_count_kv", 9, per_layer)
        fields, _ = gguf.parse_header(gguf_bytes(arch="gemma4", extra=arr, extra_pairs=1))
        assert fields["attention.head_count_kv"] == [8, 8, 1]

    def test_a_prefix_that_ends_inside_the_header_asks_for_more(self):
        whole = gguf_bytes()
        _, end = gguf.parse_header(whole)
        with pytest.raises(gguf.Incomplete):
            gguf.parse_header(whole[: end - 1])

    def test_not_a_gguf_file_is_refused(self):
        with pytest.raises(gguf.NotGGUF):
            gguf.parse_header(b"PK\x03\x04" + b"\x00" * 64)


# ── reading by range, against a fake Hub ──────────────────────────────────────


class _NoWait:
    def wait(self, url, **kw):
        return 0.0


FILE = "https://huggingface.co/x/resolve/s/f.gguf"
READ = ReadSettings(quants=("Q4_K_M", "Q8_0"), chunk_bytes=64, max_header_bytes=4096)


def _hub(file_bytes: bytes, *, siblings, sha="abc123", honour_range=True, api_status=200):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "/api/models/" in request.url.path:
            if api_status != 200:
                return httpx.Response(api_status)
            return httpx.Response(200, json={"sha": sha, "siblings": siblings})
        rng = request.headers.get("Range")
        if not honour_range or not rng:
            return httpx.Response(200, content=file_bytes)
        start, end = (int(x) for x in rng.removeprefix("bytes=").split("-"))
        return httpx.Response(206, content=file_bytes[start:end + 1])

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


class _Store:
    def put(self, data):
        class Stored:
            ref = "raw/sha256/aa/bb/x"
        return Stored()


MODEL = LocalModel(id="test-8b", gguf_repo="someone/Test-8B-GGUF",
                   files={"Q4_K_M": ("Test-8B-Q4_K_M.gguf",), "Q8_0": ("Test-8B-Q8_0.gguf",)})


class TestReadingByRange:
    def test_reads_in_steps_and_stops_at_the_header(self):
        data = gguf_bytes()
        client, seen = _hub(data, siblings=[])
        fields, note = read_header(client, _NoWait(), FILE, READ)
        assert note is None and fields["block_count"] == 32
        ranges = [r.headers["Range"] for r in seen]
        assert ranges[0] == "bytes=0-63" and len(ranges) < len(data) // 64

    def test_a_response_that_ignores_the_range_is_refused_unread(self):
        client, _ = _hub(gguf_bytes(), siblings=[], honour_range=False)
        fields, note = read_header(client, _NoWait(), FILE, READ)
        assert fields is None and "HTTP 200 to a ranged request" in note

    def test_a_header_past_the_limit_is_recorded_unread(self):
        client, _ = _hub(gguf_bytes(), siblings=[])
        tiny = ReadSettings(quants=READ.quants, chunk_bytes=16, max_header_bytes=32)
        fields, note = read_header(client, _NoWait(), FILE, tiny)
        assert fields is None and "longer than 32 bytes" in note


class TestMeasuring:
    def test_sizes_and_header_come_from_the_same_commit(self):
        sib = [{"rfilename": "Test-8B-Q4_K_M.gguf", "size": 4_900_000_000},
               {"rfilename": "Test-8B-Q8_0.gguf", "size": 8_500_000_000}]
        client, seen = _hub(gguf_bytes(), siblings=sib, sha="feedbeef")
        rows = measure(client, _NoWait(), _Store(), MODEL, READ)
        assert [(r["quant"], r["bytes"], r["missing_files"]) for r in rows] == [
            ("Q4_K_M", 4_900_000_000, []), ("Q8_0", 8_500_000_000, [])]
        assert rows[0]["header"]["block_count"] == 32 and rows[0]["header_note"] is None
        assert any("/resolve/feedbeef/Test-8B-Q4_K_M.gguf" in str(r.url) for r in seen)

    def test_a_missing_listed_file_leaves_the_size_null_and_names_it(self):
        """Never a partial sum, never another file that looks like it."""
        sib = [{"rfilename": "Test-8B-Q4_K_M.gguf", "size": 4_900_000_000},
               {"rfilename": "Test-8B-Q8_0-renamed.gguf", "size": 8_500_000_000}]
        client, _ = _hub(gguf_bytes(), siblings=sib)
        rows = {r["quant"]: r for r in measure(client, _NoWait(), _Store(), MODEL, READ)}
        assert rows["Q8_0"]["bytes"] is None
        assert rows["Q8_0"]["missing_files"] == ["Test-8B-Q8_0.gguf"]
        assert rows["Q4_K_M"]["bytes"] == 4_900_000_000

    def test_split_files_are_summed_part_by_part(self):
        split = LocalModel(id="big", gguf_repo="x/Big-GGUF", files={
            "Q4_K_M": ("Big-Q4_K_M-00001-of-00002.gguf", "Big-Q4_K_M-00002-of-00002.gguf"),
            "Q8_0": ("Big-Q8_0.gguf",)})
        sib = [{"rfilename": "Big-Q4_K_M-00001-of-00002.gguf", "size": 10},
               {"rfilename": "Big-Q4_K_M-00002-of-00002.gguf", "size": 32},
               {"rfilename": "Big-Q8_0.gguf", "size": 70}]
        client, _ = _hub(gguf_bytes(), siblings=sib)
        rows = {r["quant"]: r for r in measure(client, _NoWait(), _Store(), split, READ)}
        assert rows["Q4_K_M"]["bytes"] == 42

    def test_an_unreadable_repo_is_recorded_not_dropped(self):
        client, _ = _hub(gguf_bytes(), siblings=[], api_status=404)
        rows = measure(client, _NoWait(), _Store(), MODEL, READ)
        assert all(r["bytes"] is None and r["header"] is None for r in rows)
        assert rows[0]["header_note"] == "HTTP 404 from the Hub API"


# ── the contract ──────────────────────────────────────────────────────────────


def test_the_listed_models_load_and_every_one_names_each_quant():
    models = load_models()
    assert len(models) == len({m.id for m in models}) > 0
    assert all(m.files["Q4_K_M"] and m.files["Q8_0"] for m in models)


def test_a_duplicate_id_is_refused(tmp_path):
    entry = ("  - {id: a, gguf_repo: r/x, files: {Q4_K_M: [a.gguf], Q8_0: [b.gguf]}}\n")
    path = tmp_path / "local_models.yaml"
    path.write_text("models:\n" + entry + entry, encoding="utf-8")
    with pytest.raises(LocalModelsContractError, match="duplicate"):
        load_models(path)


def test_every_constant_is_required(monkeypatch):
    monkeypatch.setattr(view, "_read", lambda name: {"quants": ["Q4_K_M"]})
    with pytest.raises(view.LocalModelsContractError):
        view.inference_settings()


def test_the_hardware_list_loads_grouped():
    devices = view.hardware()
    assert devices and all(d["memory_gib"] > 0 and d["group"] for d in devices)
    assert {d["kind"] for d in devices} == {"discrete", "unified"}


# ── the cache, from the real headers measured 2026-10-23 ─────────────────────


def _header(model_id: str) -> dict:
    fields = dict(HEADERS[model_id]["fields"])
    fields["architecture"] = fields.pop("general.architecture")
    return fields


class TestTheCacheShape:
    def test_llama_8b_is_one_gib_at_8k_in_f16(self):
        """32 layers x 8 KV heads x (128 + 128) = 65,536 elements a token;
        x 2 bytes x 8,192 tokens = exactly 1 GiB, the published figure."""
        shape = view.cache_shape(_header("llama-3.1-8b"))
        assert shape["basis"] == "exact" and shape["full_elements"] == 65536
        assert shape["full_elements"] * 2 * 8192 == 2**30

    def test_an_unstated_head_size_is_llama_cpps_own_rule(self):
        """Llama 3.1 8B's header has no key_length: 4096 / 32 = 128."""
        assert "attention.key_length" not in _header("llama-3.1-8b")
        assert view.cache_shape(_header("llama-3.1-8b"))["full_elements"] == 32 * 8 * 256

    def test_a_full_attention_interval_caches_only_those_layers(self):
        """Qwen 3.6 27B: 64 layers, every 4th keeps a cache -> 16 x 4 x 512."""
        shape = view.cache_shape(_header("qwen3.6-27b"))
        assert shape["basis"] == "exact" and shape["full_elements"] == 16 * 4 * 512

    def test_zero_kv_heads_mark_a_layer_with_no_cache(self):
        shape = view.cache_shape(_header("nemotron-3-nano-4b"))
        kv = _header("nemotron-3-nano-4b")["attention.head_count_kv"]
        assert shape["basis"] == "exact" and sum(1 for h in kv if h) < len(kv)

    def test_a_stated_window_pattern_is_exact_and_split(self):
        shape = view.cache_shape(_header("gemma-4-12b"))
        assert shape["basis"] == "exact"
        assert shape["windowed"] and shape["windowed"][0]["window"] == 1024

    def test_a_window_without_a_pattern_is_an_upper_bound(self):
        shape = view.cache_shape(_header("gemma-3-12b"))
        assert shape["basis"] == "upper_bound" and "pattern" in shape["why"]
        assert shape["windowed"] == []

    def test_latent_attention_is_an_upper_bound(self):
        shape = view.cache_shape(_header("glm-4.7-flash"))
        assert shape["basis"] == "upper_bound" and "latent" in shape["why"]

    def test_an_unread_header_is_unknown_never_zero(self):
        shape = view.cache_shape(None)
        assert shape["basis"] == "unknown" and shape["full_elements"] is None

    def test_the_measured_split_is_43_exact_and_7_upper_bound(self):
        """The count in the proposal, recomputed (rule 11)."""
        bases = [view.cache_shape(_header(m))["basis"] for m in HEADERS]
        assert (bases.count("exact"), bases.count("upper_bound")) == (43, 7)


# ── the page's arithmetic, run in node ────────────────────────────────────────


@pytest.fixture(scope="module")
def js() -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to run web/src/vram/estimate.js")
    run = subprocess.run([node, str(ROOT / "tests" / "js" / "vram_estimate.mjs")],
                         capture_output=True, text=True, encoding="utf-8", cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"vram_estimate.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


GIB = 2**30


class TestTheEstimate:
    def test_file_plus_cache_plus_runtime(self, js):
        e = js["llama8gb"]
        assert e["cacheBytes"] == GIB and e["overheadBytes"] == GIB
        assert e["total"] == pytest.approx(4.58 * GIB + 2 * GIB)

    def test_the_groups(self, js):
        """6.58 GiB estimated. 8 GiB: 85% is 6.8, so it fits. 7.5 GiB: over 85%
        (6.375), under 100%, so tight. 6 GiB: won't fit."""
        assert js["llama8gb"]["group"] == "fits"
        assert js["llama7_5gb"]["group"] == "tight"
        assert js["llama6gb"]["group"] == "wont"

    def test_an_8_bit_cache_is_smaller(self, js):
        assert js["llamaQ8cache"]["cacheBytes"] == pytest.approx(GIB * 1.0625 / 2)

    def test_two_cards_double_memory_and_pay_overhead_twice(self, js):
        e = js["llamaTwoCards"]
        assert e["budget"] == 8 * GIB and e["overheadBytes"] == 2 * GIB

    def test_a_mac_gets_its_gpu_share_and_one_runtime(self, js):
        assert js["llamaMac8"]["budget"] == pytest.approx(6 * GIB)
        assert js["llamaMacIgnoresCards"]["budget"] == pytest.approx(12 * GIB)
        assert js["llamaMacIgnoresCards"]["overheadBytes"] == GIB

    def test_windowed_layers_stop_growing_at_their_window(self, js):
        e = js["gemma32k"]
        assert e["cacheBytes"] == 2 * (8192 * 32768 + 163840 * 1024)

    def test_unknown_context_memory_stays_unknown(self, js):
        assert js["unknown"]["cacheBytes"] is None
        assert js["unknown"]["total"] == 3 * GIB  # file + runtime, and the page says so

    def test_a_missing_size_is_no_estimate(self, js):
        assert js["missing"] is None

    def test_the_context_is_capped_at_the_models_maximum(self, js):
        assert js["capped"]["context"] == {"tokens": 4096, "capped": True}

    def test_sizes_are_gib_and_say_so(self, js):
        assert js["fmt"] == ["4.68 GiB", "15.3 GiB", "111 GiB", "—"]


# ── the table and the view (Postgres) ─────────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
        yield c


def _row(model_id, quant, size, header):
    return {"model_id": model_id, "quant": quant, "gguf_repo": "r/x", "files": [f"{quant}.gguf"],
            "bytes": size, "missing_files": [] if size else [f"{quant}.gguf"],
            "header": header, "header_note": None if header else "not read",
            "repo_sha": "abc", "raw_ref": "raw/x",
            "measured_at": datetime(2026, 10, 23, tzinfo=UTC),
            "pipeline_version": "test"}


def test_the_view_lists_measured_models_and_names_the_rest(conn, monkeypatch):
    listed = [{"id": "a", "name": "A", "family": "F", "original": "o/a", "openrouter": "f/a",
               "gguf_repo": "r/x"},
              {"id": "b", "name": "B", "family": "F", "original": None, "openrouter": None,
               "gguf_repo": "r/y"}]
    monkeypatch.setattr(view, "listed_models", lambda: listed)
    write_rows(conn, [_row("a", "Q4_K_M", 5 * GIB, _header("llama-3.1-8b")),
                      _row("a", "Q8_0", None, _header("llama-3.1-8b"))])
    conn.execute(
        "INSERT INTO model_catalog (canonical_id, provider, name, input_modalities, "
        "output_modalities, pricing, last_seen_at, price_in, price_out) "
        "VALUES ('f/a', 'f', 'A', '{text}', '{text}', '{}', now(), 0.1, 0.3)")
    out = view.local_models_view(conn)
    assert out["not_measured"] == ["b"]
    (a,) = out["models"]
    assert a["quants"]["Q4_K_M"]["bytes"] == 5 * GIB
    assert a["quants"]["Q8_0"]["bytes"] is None and a["quants"]["Q8_0"]["missing_files"]
    assert a["cache"]["basis"] == "exact" and a["on_catalog"] and a["price_out"] == 0.3
    assert set(out["constants"]) >= {"quants", "contexts", "kv_cache_bytes", "apple_gpu_share"}


def test_a_size_without_its_files_or_a_header_without_a_reason_is_refused(conn):
    bad = _row("a", "Q4_K_M", None, None)
    bad["missing_files"] = []
    with pytest.raises(psycopg.errors.CheckViolation):
        write_rows(conn, [bad])
