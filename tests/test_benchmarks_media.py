"""Image, video and speech benchmarks (Parvathi, 2026-11-03).

Artificial Analysis's arenas and word error rates, read from each page's own
Next.js data, with rows for the model CATALOGUE's image, video and speech
models as well as the registry's (module_settings.yaml catalog_models). No test
touches a live site: the pages are small copies of the shapes read on
2026-11-03.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from psycopg import errors

from collect.benchmarks.config import CONFIG_DIR, ConfigError, load
from collect.benchmarks.host_adapter import SeedModel, get_registry_models
from collect.benchmarks.match import Resolver
from collect.benchmarks.parse import parse
from collect.benchmarks.values import parse_rating, parse_score

MEDIA = {
    "aa_text_to_image": "image",
    "aa_image_editing": "image",
    "aa_text_to_video": "video",
    "aa_image_to_video": "video",
    "aa_text_to_speech": "speech",
    "aa_wer": "speech",
}


@pytest.fixture(scope="module")
def config():
    return load()


def _page(objects) -> bytes:
    """A page carrying its data the way Next.js does: JSON inside a JS string."""
    data = json.dumps({"data": objects}, separators=(",", ":"))
    payload = json.dumps(data)[1:-1]
    return (
        b"<html><body>"
        + b"x" * 3000
        + b'<script>self.__next_f.push([1,"'
        + payload.encode()
        + b'"])</script></body></html>'
    )


def _arena(name, elo, i):
    return {
        "id": f"id-{name}-{i}",
        "slug": name.lower(),
        "name": name,
        "elo": elo,
        "lower95ci": elo - 10,
        "upper95ci": elo + 10,
        "creator": {"name": "X"},
        "price": 1.0,
    }


# ── the contract ─────────────────────────────────────────────────────────────


def test_the_media_benchmarks_have_their_own_sections(config):
    for key, section in MEDIA.items():
        assert config.benchmarks[key].category == section
    assert [c.key for c in config.categories][-3:] == ["image", "video", "speech"]
    # Arenas are Elo ratings; the word error rate is the one lower-is-better score.
    assert all(config.benchmarks[k].metrics == ("rating",) for k in MEDIA if k != "aa_wer")
    assert config.benchmarks["aa_wer"].metrics == ("score",)
    assert config.benchmarks["aa_wer"].higher_is_better is False


def test_the_media_sources_are_read_at_their_tiers(config):
    enabled = {s.key for s in config.sources if s.enabled}
    evaluators = {"aa_image_arena", "aa_video_arena", "aa_speech_arena", "aa_speech_to_text"}
    own_boards = {"open_asr_leaderboard", "tts_arena_v2", "vbench_leaderboard"}
    assert evaluators | own_boards <= enabled
    assert all(config.source(k).tier == 2 for k in evaluators)
    assert all(config.source(k).tier == 1 for k in own_boards)


def _config_with(tmp_path: Path, catalog_models) -> Path:
    for f in CONFIG_DIR.glob("*.yaml"):
        shutil.copy(f, tmp_path / f.name)
    path = tmp_path / "module_settings.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if catalog_models is None:
        raw.pop("catalog_models")
    else:
        raw["catalog_models"] = catalog_models
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "setting",
    [None, {}, {"output_modalities": "image"}, {"output_modalities": ["image", "text"]}],
)
def test_the_catalogue_setting_is_required_and_never_takes_text_models(tmp_path, setting):
    with pytest.raises(ConfigError) as e:
        load(_config_with(tmp_path, setting))
    assert any("catalog_models" in p for p in e.value.problems)


def test_an_empty_catalogue_list_is_a_choice(tmp_path):
    assert load(_config_with(tmp_path, {"output_modalities": []}))


# ── reading the pages ────────────────────────────────────────────────────────


def test_each_image_board_is_read_from_its_own_list(config):
    page = _page(
        [
            {
                "textToImage": [
                    _arena("GPT Image 2 (high)", 1188.55, 1),
                    _arena("Muse Image", 1127.1, 2),
                ],
                "imageEditing": [_arena("Muse Image", 1129.4, 3)],
            }
        ]
    )
    parsed = parse(config.source("aa_image_arena"), page, url="u")
    assert not parsed.problems and parsed.tables_found == 2
    got = {(o.benchmark, o.raw_model_name, o.raw_text) for o in parsed.observations}
    assert got == {
        ("aa_text_to_image", "GPT Image 2 (high)", "1188.55"),
        ("aa_text_to_image", "Muse Image", "1127.1"),
        ("aa_image_editing", "Muse Image", "1129.4"),
    }
    assert all(o.metric == "rating" for o in parsed.observations)
    assert parse_rating("1188.55", config.benchmarks["aa_text_to_image"].rating_range).value == 1189


def test_each_video_board_is_read_from_its_own_list(config):
    page = _page(
        [
            {
                "textToVideo": [_arena("Veo 3.1", 1101.0, 1)],
                "imageToVideo": [_arena("Veo 3.1", 1090.0, 2), _arena("Wan 3.0", 1110.0, 3)],
            }
        ]
    )
    parsed = parse(config.source("aa_video_arena"), page, url="u")
    assert not parsed.problems
    by = {(o.benchmark, o.raw_model_name) for o in parsed.observations}
    assert by == {
        ("aa_text_to_video", "Veo 3.1"),
        ("aa_image_to_video", "Veo 3.1"),
        ("aa_image_to_video", "Wan 3.0"),
    }


def test_the_speech_arena_reads_one_record_per_model(config):
    eleven = {
        "id": "a",
        "name": "Eleven v4",
        "elo": 1333.89,
        "appearances": 2608,
        "ciLower": 1318.89,
        "ciUpper": 1348.89,
        "rank": 0,
        "creator": {"name": "ElevenLabs"},
    }
    parsed = parse(config.source("aa_speech_arena"), _page([eleven, eleven]), url="u")
    assert [(o.raw_model_name, o.raw_text) for o in parsed.observations] == [
        ("Eleven v4", "1333.89")
    ]


def _stt(name, wer, host, i, maker=None):
    return {
        "id": f"s{i}",
        "name": name,
        "aaWerIndex": wer,
        "hostApiId": f"{host}/{name}",
        "host": {"name": host},
        "model": {"creator": {"name": maker or host}},
        "defaultSelectedApi": True,
    }


def test_the_makers_own_api_is_read_when_it_serves_the_model(config):
    """Nova-3 on Deepgram (its maker) and on Telnyx: Deepgram's value is read.
    Whisper, which OpenAI does not serve there, gets one setting row per host."""
    page = _page(
        [
            _stt("Nova-3", 0.0518, "Deepgram", 1, maker="Deepgram"),
            _stt("Nova-3", 0.0482, "Telnyx", 2, maker="Deepgram"),
            _stt("Whisper Large v3", 0.0407, "fal.ai", 3, maker="OpenAI"),
            _stt("Whisper Large v3", 0.0453, "Together AI", 4, maker="OpenAI"),
        ]
    )
    parsed = parse(config.source("aa_speech_to_text"), page, url="u")
    got = sorted((o.raw_model_name, o.variant, o.raw_setting) for o in parsed.observations)
    assert got == [
        ("Nova-3", "Deepgram", None),
        ("Whisper Large v3", "Together AI", "Together AI"),
        ("Whisper Large v3", "fal.ai", "fal.ai"),
    ]
    assert any("another host left out" in n for n in parsed.notes)
    assert any("one setting row per host" in n for n in parsed.notes)
    whisper = SeedModel("openai/whisper-large-v3", "Whisper Large V3")
    resolver = Resolver(config, [], {}, [whisper])
    row = resolver.match("Whisper Large v3", "Together AI", new_settings=True).row
    assert (row.row_id, row.label) == (
        "openai/whisper-large-v3:Together AI",
        "Whisper Large V3 (Together AI)",
    )


def test_word_error_rate_records_the_host_and_drops_it_from_the_name(config):
    page = _page(
        [_stt("Chirp 3, Google", 0.0612, "Google", 1), _stt("Nova-3", 0.0518, "Deepgram", 2)]
    )
    parsed = parse(config.source("aa_speech_to_text"), page, url="u")
    assert not parsed.problems
    got = {(o.raw_model_name, o.variant, o.raw_text, o.scale) for o in parsed.observations}
    assert got == {
        ("Chirp 3", "Google", "0.0612", "fraction"),
        ("Nova-3", "Deepgram", "0.0518", "fraction"),
    }
    assert parse_score("0.0518", "fraction").value == 5.18


# ── the benchmarks' own boards on Hugging Face ───────────────────────────────


def _gradio(tables):
    return {
        "version": "6.26.0",
        "components": [
            {"id": i, "type": "dataframe", "props": {"value": {"headers": h, "data": d}}}
            for i, (h, d) in enumerate(tables)
        ],
    }


ASR_HEADERS = ["Rank", "Rank Δ", "model", "Average WER ⬇️", "RTFx ⬆️️"]


def test_open_asr_is_read_from_the_apps_own_config(config):
    """Gradio 6 serves its config beside the page; a model cell is an HTML link."""
    cfg = _gradio(
        [
            (
                ASR_HEADERS,
                [
                    [
                        "1",
                        "—",
                        '<a href="https://x" style="c">zoom/scribe_v2.1_pro</a>',
                        "4.87",
                        "None",
                    ],
                    ["42", "—", '<a href="https://y">openai/whisper-large-v3</a>', "8.18", "145.2"],
                ],
            ),
            # The multilingual tab: no RTFx column, not read.
            (["Rank", "Model", "Average WER ⬇️"], [["1", "other", "9.9"]]),
        ]
    )
    content = json.dumps(cfg).encode() + b" " * 3000
    parsed = parse(config.source("open_asr_leaderboard"), content, url="u")
    assert not parsed.problems
    got = {(o.raw_model_name, o.metric, o.raw_text) for o in parsed.observations}
    assert got == {
        ("zoom/scribe_v2.1_pro", "score", "4.87"),
        ("zoom/scribe_v2.1_pro", "rank", "1"),
        ("openai/whisper-large-v3", "score", "8.18"),
        ("openai/whisper-large-v3", "rank", "42"),
    }
    assert config.benchmarks["open_asr_wer"].higher_is_better is False


VBENCH = ["Model Name (clickable)", "Total Score", "Quality Score", "Semantic Score"]
VBENCH_I2V = ["Model Name (clickable)", "Total Score", "I2V Score", "Quality Score"]


def test_vbench_is_read_from_the_config_written_into_its_page(config):
    """Gradio 4 writes the config into the page; a name is a Markdown link, and
    of a board and its filtered copy the fuller one is read."""
    cfg = _gradio(
        [
            (VBENCH, [["[Veo 3](https://v)", "84.10%", "85%", "80%"]]),
            (
                VBENCH,
                [
                    ["[Veo 3](https://v)", "84.10%", "85%", "80%"],
                    ["[Wan2.1](https://w)", "86.22%", "86%", "84%"],
                ],
            ),
            (VBENCH_I2V, [["[Wan2.1-I2V](https://w)", "86.86%", "96%", "78%"]]),
        ]
    )
    page = b"<html><head><script>window.gradio_config = " + json.dumps(cfg).encode()
    page += b";</script></head><body>" + b"x" * 3000 + b"</body></html>"
    parsed = parse(config.source("vbench_leaderboard"), page, url="u")
    assert not parsed.problems
    got = {(o.benchmark, o.raw_model_name, o.raw_text) for o in parsed.observations}
    assert got == {
        ("vbench", "Veo 3", "84.10%"),
        ("vbench", "Wan2.1", "86.22%"),
        ("vbench_i2v", "Wan2.1-I2V", "86.86%"),
    }


def _card(place, name, rating, link=True):
    tag = f'<a href="https://m">{name}</a>' if link else f"<button>{name}</button>"
    return (
        f'<div><span class="font-mono">{place}</span>'
        f'<div class="min-w-0 flex-1"><span></span><div class="min-w-0 flex-1"><div>{tag}'
        f"<span>Preliminary</span></div><p>212 votes</p></div></div>"
        f'<div><p class="nums">{rating}<span> ±26</span></p></div></div>'
    )


def test_tts_arena_reads_its_list_of_cards(config):
    page = (
        "<html><body>"
        + "x" * 3000
        + '<p>43 models · 17.9k votes cast</p><div class="card divide-y">'
        + _card("01", "Gradium TTS 2026.10", "1586")
        + _card("02", "Aurora", "1560", link=False)
        + "</div></body></html>"
    ).encode()
    parsed = parse(config.source("tts_arena_v2"), page, url="u")
    assert not parsed.problems
    got = {(o.raw_model_name, o.metric, o.raw_text) for o in parsed.observations}
    assert got == {
        ("Gradium TTS 2026.10", "rating", "1586 ±26"),
        ("Gradium TTS 2026.10", "rank", "01"),
        ("Aurora", "rating", "1560 ±26"),
        ("Aurora", "rank", "02"),
    }
    assert parse_rating("1586 ±26", (0, 3000)).value == 1586


def test_a_board_that_lost_its_table_is_said(config):
    cfg = _gradio([(["Rank", "Model"], [["1", "x"]])])
    parsed = parse(config.source("open_asr_leaderboard"), json.dumps(cfg).encode(), url="u")
    assert parsed.blocked and parsed.problems[0][0] == "table_not_found"


# ── which models get rows ────────────────────────────────────────────────────


class _Conn:
    """Answers the registry query, then the catalogue query (or raises for it)."""

    autocommit = True

    def __init__(self, registry, catalogue=None, catalogue_error=None):
        self.answers = [registry, catalogue]
        self.catalogue_error = catalogue_error
        self.asked = []

    def execute(self, sql, params=None):
        self.asked.append((sql, params))
        if "model_catalog" in sql and self.catalogue_error:
            raise self.catalogue_error
        self.rows = self.answers[len(self.asked) - 1]
        return self

    def fetchall(self):
        return self.rows


def test_catalogue_media_models_are_added_once_each():
    conn = _Conn(
        registry=[("google/gemini-3-pro-image", "Google: Nano Banana Pro (Gemini 3 Pro Image)")],
        catalogue=[
            ("google/veo-3.1", "Google: Veo 3.1"),
            ("google/gemini-3-pro-image", "Google: Nano Banana Pro (Gemini 3 Pro Image)"),
        ],
    )
    got = get_registry_models(conn, ["image", "video", "speech", "transcription"])
    assert [(m.id, m.name) for m in got] == [
        ("google/gemini-3-pro-image", "Nano Banana Pro (Gemini 3 Pro Image)"),
        ("google/veo-3.1", "Veo 3.1"),
    ]
    sql, params = conn.asked[1]
    # Only models whose every output is one of these types: a text model never.
    assert "<@" in sql and params == (["image", "video", "speech", "transcription"],)


def test_no_catalogue_list_asks_no_catalogue():
    conn = _Conn(registry=[("a/b", "A: B")])
    assert [m.id for m in get_registry_models(conn, [])] == ["a/b"]
    assert len(conn.asked) == 1


def test_a_database_without_the_catalogue_still_gives_the_registry():
    conn = _Conn(registry=[("a/b", "A: B")], catalogue_error=errors.UndefinedTable("model_catalog"))
    assert [m.id for m in get_registry_models(conn, ["image"])] == ["a/b"]


def test_openais_tts_1_is_never_assemblyais_tts_1(config):
    """The catalogue names AssemblyAI's model "TTS 1"; Artificial Analysis's
    "TTS-1" is OpenAI's (model_extras.yaml not_names)."""
    assembly = SeedModel("assemblyai/assemblyai-tts-1", "TTS 1")
    resolver = Resolver(config, [], {}, [assembly])
    assert resolver.match("TTS-1").row is None
    assert resolver.match("AssemblyAI-TTS-1").row.host_model_id == assembly.id


def test_every_reader_has_a_name_on_the_sources_tab():
    from collect.benchmarks.config import LOCATE_TYPES
    from judge import benchmarks as page

    assert set(LOCATE_TYPES) <= set(page.READERS)


def test_a_new_bracket_word_is_a_setting_row_only_where_the_table_says(config):
    """Open ASR's "(fast-gpu-asr)" is how the model was run: on a media table it
    becomes its own row; on a text board the same word still waits in Review."""
    parakeet = SeedModel("nvidia/parakeet-tdt-0.6b-v3", "Parakeet TDT 0.6B v3")
    resolver = Resolver(config, [], {}, [parakeet])
    name = "nvidia/parakeet-tdt-0.6b-v3 (fast-gpu-asr)"
    strict = resolver.match(name)
    assert strict.row is None and strict.reason == "unknown_setting"
    row = resolver.match(name, new_settings=True).row
    assert (row.row_id, row.setting, row.label) == (
        "nvidia/parakeet-tdt-0.6b-v3:fast-gpu-asr",
        "fast-gpu-asr",
        "Parakeet TDT 0.6B v3 (fast-gpu-asr)",
    )
    # A word the vocabulary knows is still read as its standard setting.
    assert resolver.match("Parakeet TDT 0.6B v3 (High)", new_settings=True).row.setting == "high"


def test_every_media_table_makes_new_setting_rows_and_no_text_board_does(config):
    media = {"image", "video", "speech"}
    for s in config.sources:
        for t in s.tables:
            sections = {
                config.benchmarks[v["benchmark"]].category for v in t.benchmark_map.values()
            }
            assert t.new_settings == bool(sections & media), s.key


def _vals_page(rows, records):
    """Vals AI's shape: a table whose names link to /models/<org>_<id>, and the
    page's data (HTML-escaped, every value as [0, value]) keyed by model id."""
    body = "".join(
        f'<tr><td>{i + 1}</td><th scope="row"><a href="/models/{link}">{name}</a></th>'
        f"<td>Mini-SWE-agent</td><td>{score}</td></tr>"
        for i, (name, link, score) in enumerate(rows)
    )
    data = ",".join(
        f'"{mid}":[0,{{"accuracy":[0,{acc}],"reasoning_effort":[0,{json.dumps(effort)}]}}]'
        for mid, acc, effort in records
    )
    escaped = ("{" + data + "}").replace('"', "&quot;")
    return (
        f'<html><body>{"x" * 3000}<astro-island props="{escaped}"></astro-island>'
        "<table><tr><th>Rank</th><th>Model</th><th>Harness</th><th>Score</th></tr>"
        f"{body}</table></body></html>"
    ).encode()


def test_a_vals_row_takes_the_effort_its_run_record_states(config):
    page = _vals_page(
        rows=[
            ("GPT 5.2", "openai_gpt-5.2-2025-12-11", "75.80%"),
            ("Inkling Small", "thinkingmachines_inkling-small", "50.00%"),
            ("Claude Opus 4.5 (Thinking)", "anthropic_claude-opus-4-5", "70.00%"),
            ("Kimi K2.6", "moonshotai_kimi-k2.6", "76.20%"),
        ],
        records=[
            # Another benchmark's run of the same model on the page: another score.
            ("openai/gpt-5.2-2025-12-11", 38.095, "medium"),
            ("openai/gpt-5.2-2025-12-11", 75.8, "xhigh"),
            ("thinkingmachines/inkling-small", 50.0, "0.99"),  # not an effort word
            ("anthropic/claude-opus-4-5", 70.0, "high"),  # its name states a setting
            ("moonshotai/kimi-k2.6", 76.2, None),
        ],
    )
    parsed = parse(config.source("vals_swebench_verified"), page, url="u")
    assert not parsed.problems
    settings = {o.raw_model_name: o.raw_setting for o in parsed.observations if o.metric == "score"}
    assert settings == {
        "GPT 5.2": "xhigh",
        "Inkling Small": None,
        "Claude Opus 4.5 (Thinking)": None,
        "Kimi K2.6": None,
    }
    assert any("1 rows take the setting" in n for n in parsed.notes)


def test_every_vals_table_reads_the_effort_and_no_other_does(config):
    for s in config.sources:
        for t in s.tables:
            assert bool(t.setting_from_page_data) == s.key.startswith("vals_"), s.key
