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


def _tensor(name: str, dims: list[int]) -> bytes:
    """One tensor description: name, dimensions, type, offset - never data."""
    shape = struct.pack("<I", len(dims)) + struct.pack(f"<{len(dims)}Q", *dims)
    return _s(name) + shape + struct.pack("<IQ", 12, 0)


def gguf_bytes(arch="llama", layers=32, kv_heads=8, extra=b"", extra_pairs=0,
               tensors=(), tail=1 << 16) -> bytes:
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
    head = b"GGUF" + struct.pack("<IQQ", 3, len(tensors), len(pairs) + extra_pairs)
    listing = b"".join(_tensor(n, d) for n, d in tensors)
    return head + b"".join(pairs) + extra + listing + b"\x00" * tail  # tail: the tensor data


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

    def test_the_first_key_projection_is_kept_from_the_tensor_list(self):
        """Names and shapes only - the shape is what checks the head size."""
        listing = (("token_embd.weight", [4096, 128256]), ("blk.0.attn_q.weight", [4096, 4096]),
                   ("blk.0.attn_k.weight", [4096, 1024]), ("blk.1.attn_k.weight", [4096, 1024]))
        fields, end = gguf.parse_header(gguf_bytes(tensors=listing))
        assert fields["tensor.attn_k"] == {"layer": 0, "shape": [4096, 1024]}
        assert "tensor.attn_qkv" not in fields
        assert end == len(gguf_bytes(tensors=listing)) - (1 << 16)

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


def test_the_hardware_list_loads_grouped_and_every_mac_has_its_share():
    devices = view.hardware()
    assert devices and all(d["memory_gib"] > 0 and d["group"] and d["source"] for d in devices)
    assert {d["kind"] for d in devices} == {"discrete", "unified"}
    macs = {d["memory_gib"]: d["gpu_share"] for d in devices if d["kind"] == "unified"}
    table = view.inference_settings()["apple_gpu_share"]
    assert macs and all(s == view.gpu_share(gib, table) for gib, s in macs.items())


def test_an_unchecked_device_says_so_and_none_is_defaulted(monkeypatch):
    """#559 review: the six AMD cards' pages would not load, and the page has to
    show that, not only the contract. A device with no flag is refused."""
    devices = view.hardware()
    assert sorted(d["id"] for d in devices if d["checked"] is False) == [
        "rx-7600", "rx-7700-xt", "rx-7800-xt", "rx-7900-xt", "rx-7900-xtx", "rx-9070-xt"]
    settings = view.inference_settings()
    raw = view._read("local_hardware.yaml")
    unflagged = {**raw, "devices": [{k: v for k, v in d.items() if k != "checked"}
                                    for d in raw["devices"]]}
    monkeypatch.setattr(view, "_read", lambda name: unflagged)
    with pytest.raises(view.LocalModelsContractError):
        view.hardware(settings)


def test_a_mac_takes_the_largest_row_at_or_below_its_memory():
    table = [{"from_gib": 0, "share": 0.66}, {"from_gib": 64, "share": 0.75}]
    assert [view.gpu_share(g, table) for g in (8, 48, 63.9, 64, 512)] == [
        0.66, 0.66, 0.66, 0.75, 0.75]


def test_the_mac_table_must_start_at_zero(monkeypatch):
    raw = view._read("local_inference.yaml")
    raw = {**raw, "apple_gpu_share": [{"from_gib": 16, "share": 0.66, "evidence": "x"}]}
    monkeypatch.setattr(view, "_read", lambda name: raw)
    with pytest.raises(view.LocalModelsContractError, match="from 0 GiB"):
        view.inference_settings()


# ── the cache, from the real headers measured 2026-10-23 ─────────────────────


def _header(model_id: str) -> dict:
    fields = dict(HEADERS[model_id]["fields"])
    fields["architecture"] = fields.pop("general.architecture")
    return fields


SETTINGS = view.inference_settings()


def _shape(header):
    return view.cache_shape(header, SETTINGS)


class TestTheCacheShape:
    def test_llama_8b_is_one_gib_at_8k_in_f16(self):
        """32 layers x 8 KV heads x (128 + 128) = 65,536 elements a token;
        x 2 bytes x 8,192 tokens = exactly 1 GiB, the published figure."""
        shape = _shape(_header("llama-3.1-8b"))
        assert shape["basis"] == "exact" and shape["full_elements"] == 65536
        assert shape["full_elements"] * 2 * 8192 == 2**30

    def test_an_unstated_head_size_is_llama_cpps_own_rule(self):
        """Llama 3.1 8B's header has no key_length: 4096 / 32 = 128."""
        assert "attention.key_length" not in _header("llama-3.1-8b")
        assert _shape(_header("llama-3.1-8b"))["full_elements"] == 32 * 8 * 256

    def test_a_full_attention_interval_caches_only_those_layers(self):
        """Qwen 3.6 27B: 64 layers, every 4th keeps a cache -> 16 x 4 x 512."""
        shape = _shape(_header("qwen3.6-27b"))
        assert shape["basis"] == "exact" and shape["full_elements"] == 16 * 4 * 512

    def test_zero_kv_heads_mark_a_layer_with_no_cache(self):
        shape = _shape(_header("nemotron-3-nano-4b"))
        kv = _header("nemotron-3-nano-4b")["attention.head_count_kv"]
        assert shape["basis"] == "exact" and sum(1 for h in kv if h) < len(kv)

    def test_a_state_space_layer_is_no_kv_and_no_feed_forward(self):
        """llama.cpp's own test. Nemotron-H's zero-KV layers with a feed-forward
        width are plain feed-forward layers and hold no state."""
        h = _header("nemotron-3-nano-4b")
        pairs = zip(h["attention.head_count_kv"], h["feed_forward_length"], strict=True)
        ssm = sum(1 for k, f in pairs if not k and not f)
        per_layer = 3 * (7680 + 2 * 8 * 128) + 128 * 7680
        assert _shape(h)["fixed_bytes"] == ssm * per_layer * 4

    def test_the_recurrent_state_is_counted_not_left_out(self):
        """Qwen 3.6 27B: 48 state-space layers x ((4-1) x (6144 + 2 x 16 x 128)
        + 128 x 6144) f32 = 156,893,184 bytes, the ~150 MiB the review found."""
        assert _shape(_header("qwen3.6-27b"))["fixed_bytes"] == 156_893_184

    def test_a_stated_window_pattern_is_exact_and_split(self):
        shape = _shape(_header("gemma-4-12b"))
        assert shape["basis"] == "exact"
        assert shape["windowed"] and shape["windowed"][0]["window"] == 1024

    def test_a_window_without_a_pattern_is_an_upper_bound(self):
        shape = _shape(_header("gemma-3-12b"))
        assert shape["basis"] == "upper_bound" and "pattern" in shape["why"]
        assert shape["windowed"] == []

    def test_a_window_of_zero_or_past_the_context_is_full_attention(self):
        assert _header("phi-4-mini")["attention.sliding_window"] == 262144
        assert _header("phi-4-reasoning-plus")["attention.sliding_window"] == 0
        assert _shape(_header("phi-4-mini"))["basis"] == "exact"
        assert _shape(_header("phi-4-reasoning-plus"))["basis"] == "exact"

    def test_attention_llama_cpp_sets_in_code_is_an_upper_bound(self):
        shape = _shape(_header("llama-4-scout-17b-16e"))
        assert shape["basis"] == "upper_bound" and "chunked" in shape["why"]

    def test_attention_the_arithmetic_does_not_model_is_unknown(self):
        """Qwen3.8 Flash Next's indexer keeps its own cache: not even a bound."""
        shape = _shape(_header("qwen3.8-flash-next"))
        assert shape["basis"] == "unknown" and "indexer" in shape["why"]

    def test_a_head_size_the_files_own_projection_contradicts_is_unknown(self):
        """unsloth's Mistral Nemo: no key_length, so 5120 / 32 = 160 - but its
        key projection is 1024 = 8 KV heads x 128 (measured 2026-10-23)."""
        nemo = {**_header("mistral-nemo-12b"),
                "tensor.attn_k": {"layer": 0, "shape": [5120, 1024]}}
        assert "attention.key_length" not in nemo
        shape = _shape(nemo)
        assert shape["basis"] == "unknown" and "160" in shape["why"] and "128" in shape["why"]
        fixed = {**nemo, "attention.key_length": 128, "attention.value_length": 128}
        assert _shape(fixed)["basis"] == "exact"

    def test_a_fused_projection_checks_the_head_size_too(self):
        """Phi-4 mini rotates 96 of 128 dims - which a rope check would misread.
        Its fused q/k/v is 24 x 128 + 2 x 8 x 128 = 5120 wide: consistent."""
        phi = {**_header("phi-4-mini"), "tensor.attn_qkv": {"layer": 0, "shape": [3072, 5120]}}
        assert phi["rope.dimension_count"] == 96
        assert _shape(phi)["basis"] == "exact"

    def test_latent_attention_is_an_upper_bound(self):
        shape = _shape(_header("glm-4.7-flash"))
        assert shape["basis"] == "upper_bound" and "latent" in shape["why"]

    def test_an_unread_header_is_unknown_never_zero(self):
        shape = _shape(None)
        assert shape["basis"] == "unknown" and shape["full_elements"] is None

    def test_the_measured_split_is_41_exact_8_upper_bound_1_unknown(self):
        """The count in the proposal, recomputed (rule 11) over the 50 headers
        measured 2026-10-23. Was 43 / 7 before review: Llama 4 Scout became an
        upper bound and Qwen3.8 Flash Next unknown."""
        bases = [_shape(_header(m))["basis"] for m in HEADERS]
        counts = (bases.count("exact"), bases.count("upper_bound"), bases.count("unknown"))
        assert counts == (41, 8, 1)


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


class TestTheGroups:
    """need = 4.58 file + 1 context + 1 runtime = 6.58 GiB."""

    def test_fits_tight_and_wont(self, js):
        assert js["llama8gb"]["group"] == "fits"       # 6.58 <= 85% of 8 = 6.8
        assert js["llama7_5gb"]["group"] == "tight"    # over 6.375, under 7.5
        assert js["llama6gb"]["group"] == "wont"

    def test_two_cards_pay_the_runtime_twice(self, js):
        assert js["llamaTwoSmallCards"]["group"] == "tight"  # 7.58 of 8
        assert js["budget"]["twoCards"] == 48 * GIB

    def test_a_mac_counts_only_its_gpu_share_and_one_runtime(self, js):
        assert js["llamaMac8"]["group"] == "wont"      # file + runtime 5.58 > 5.28
        assert js["llamaMac16"]["group"] == "fits"     # cards ignored on a Mac
        assert js["budget"]["mac16"] == pytest.approx(16 * 0.66 * GIB)

    def test_an_unknown_context_is_cant_tell_never_zero(self, js):
        """Rule 6: never fits on an unknown. Won't fit only when the file and
        the runtime alone are already over - certain either way."""
        assert js["unknown8gb"]["group"] == "unknown"
        assert js["unknown8gb"]["cacheKnown"] is False
        assert js["unknownTooBig"]["group"] == "wont"

    def test_a_missing_size_is_no_group(self, js):
        assert js["missing"] is None

    def test_the_context_is_capped_at_the_models_maximum(self, js):
        assert js["capped"]["context"] == {"tokens": 4096, "capped": True}

    def test_no_computed_figure_leaves_the_function(self, js):
        """Rule 3: the row gets the measured size and a group - no total."""
        assert set(js["llama8gb"]) == {"fileBytes", "group", "context", "cacheKnown",
                                       "upperBound"}

    def test_the_cache_arithmetic(self, js):
        assert js["cache"]["llama8k"] == GIB
        assert js["cache"]["llama8kQ8"] == pytest.approx(GIB * 1.0625 / 2)
        assert js["cache"]["gemma32k"] == 2 * (8192 * 32768 + 163840 * 1024)
        assert js["cache"]["hybrid8k"] == 2 * 32768 * 8192 + 156_893_184
        assert js["cache"]["unknown"] is None

    def test_sizes_are_gib_and_say_so(self, js):
        assert js["fmt"] == ["4.68 GiB", "15.3 GiB", "111 GiB", "\u2014"]


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
    assert set(out["constants"]) >= {"quants", "contexts", "kv_cache_bytes", "fits_at_most"}
    # The Mac share travels on each Mac, from the memory-size table.
    assert all("gpu_share" in d for d in out["hardware"] if d["kind"] == "unified")


def test_a_size_without_its_files_or_a_header_without_a_reason_is_refused(conn):
    bad = _row("a", "Q4_K_M", None, None)
    bad["missing_files"] = []
    with pytest.raises(psycopg.errors.CheckViolation):
        write_rows(conn, [bad])
