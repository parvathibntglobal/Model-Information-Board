"""New arrivals from providers already on the page are tracked by rule, not by PR.

`contract/tracked_models.yaml` `auto_track` (2026-10-06). These pin what the
rule admits and what it refuses, and that the rule itself is read strictly.
No database: the registry query is answered by a fake connection.
"""
from __future__ import annotations

from datetime import date

import pytest

import judge.config as config
from judge import tracked
from judge.config import AutoTrackConfigError, TrackedModel


class _Conn:
    def __init__(self, rows):
        self.rows, self.params = rows, None

    def execute(self, sql, params):
        self.params = params
        rows = self.rows

        class _R:
            def fetchall(self):
                return rows
        return _R()


HAND = (
    TrackedModel("GPT-6 Sol", "openai/gpt-6-sol", "text"),
    TrackedModel("Claude Opus 5.5", "anthropic/claude-opus-5.5", "text"),
    TrackedModel("Some Image Model", None, "image"),
)

RULE = config.AutoTrackRule(enabled=True, released_within_days=30, include_pro_tier=True,
                            exclude_name_terms=("image", "tts", "embed"))


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(tracked, "tracked_models", lambda: HAND)
    monkeypatch.setattr(tracked, "auto_track_rule", lambda: RULE)


def test_the_rule_reads_providers_from_the_hand_list():
    assert tracked.page_providers(HAND) == ["anthropic", "openai"]


def test_admits_new_text_models_and_marks_them(setup):
    conn = _Conn([("openai/gpt-6.1-sol", "OpenAI: GPT-6.1 Sol", date(2026, 9, 29), ["text"]),
                  ("openai/gpt-6.1-sol-pro", "OpenAI: GPT-6.1 Sol Pro",
                   date(2026, 9, 29), ["text"])])
    got = tracked.auto_tracked(conn, today=date(2026, 10, 6))
    assert [(m.registry, m.name, m.auto, m.kind) for m in got] == [
        ("openai/gpt-6.1-sol", "GPT-6.1 Sol", True, "text"),
        ("openai/gpt-6.1-sol-pro", "GPT-6.1 Sol Pro", True, "text"),
    ]
    # The hand ids go in twice, once against `canonical_id` and once against
    # row `id`: an entry may name either (tests/test_tracked_ids_match_either_shape.py).
    providers, cutoff, hand_ids, hand_row_ids = conn.params
    assert providers == ["anthropic", "openai"]
    assert cutoff == date(2026, 9, 6)
    assert "openai/gpt-6-sol" in hand_ids, "a hand-listed model must not be listed twice"
    assert hand_row_ids == hand_ids


def test_non_text_names_stay_manual(setup):
    conn = _Conn([("openai/gpt-image-2", "OpenAI: GPT Image 2", date(2026, 10, 1), ["text"]),
                  ("openai/tts-2", "OpenAI: TTS 2", date(2026, 10, 1), ["text"]),
                  ("openai/embedded-thing-1", "OpenAI: Embedded Thing 1",
                   date(2026, 10, 1), ["text"])])
    got = tracked.auto_tracked(conn, today=date(2026, 10, 6))
    assert [m.registry for m in got] == ["openai/embedded-thing-1"], (
        "whole words only: `embed` must not catch `embedded`")


def test_pro_tiers_follow_the_rule(setup, monkeypatch):
    monkeypatch.setattr(tracked, "auto_track_rule", lambda: config.AutoTrackRule(
        enabled=True, released_within_days=30, include_pro_tier=False,
        exclude_name_terms=()))
    conn = _Conn([("openai/gpt-6-sol-pro", "OpenAI: GPT-6 Sol Pro", date(2026, 9, 22), ["text"])])
    assert tracked.auto_tracked(conn, today=date(2026, 10, 6)) == ()


def test_disabled_admits_nothing(setup, monkeypatch):
    monkeypatch.setattr(tracked, "auto_track_rule", lambda: config.AutoTrackRule(
        enabled=False, released_within_days=30, include_pro_tier=True, exclude_name_terms=()))
    conn = _Conn([("openai/gpt-6.1-sol", "OpenAI: GPT-6.1 Sol", date(2026, 9, 29), ["text"])])
    assert tracked.auto_tracked(conn) == ()


def test_all_tracked_puts_the_hand_list_first(setup):
    conn = _Conn([("openai/gpt-6.1-sol", "OpenAI: GPT-6.1 Sol", date(2026, 9, 29), ["text"])])
    got = tracked.all_tracked(conn, today=date(2026, 10, 6))
    assert got[:3] == HAND and got[3].registry == "openai/gpt-6.1-sol"


# ── kind comes from what the model OUTPUTS (#602 item 6) ─────────────────


def test_any_non_text_output_decides_the_kind(setup):
    """Nano Banana 2.1 outputs image AND text, and was admitted as `text`."""
    conn = _Conn([("google/gemini-nano-banana-2.1", "Google: Nano Banana 2.1",
                   date(2026, 10, 6), ["image", "text"]),
                  ("openai/gpt-6.1-sol", "OpenAI: GPT-6.1 Sol", date(2026, 9, 29), ["text"])])
    got = tracked.auto_tracked(conn, today=date(2026, 10, 6))
    assert [(m.registry, m.kind) for m in got] == [
        ("google/gemini-nano-banana-2.1", "image"), ("openai/gpt-6.1-sol", "text")]


@pytest.mark.parametrize("mods", [["text", "hologram"], ["image", "video"], [],
                                  ["text", "audio"], ["embeddings"], ["rerank"]])
def test_a_modality_with_no_decided_kind_refuses(mods):
    with pytest.raises(tracked.UnknownOutputModality):
        tracked.kind_from_modalities("openai/odd-1", mods)


def test_one_odd_model_is_left_off_and_the_rest_still_list(setup, caplog):
    """`all_tracked` feeds the Models page and the scheduler: one model's
    unknown output must cost that model, never the whole list (#602 review)."""
    conn = _Conn([("openai/odd-1", "OpenAI: Odd 1", date(2026, 10, 1), ["text", "hologram"]),
                  ("openai/gpt-6.1-sol", "OpenAI: GPT-6.1 Sol", date(2026, 9, 29), ["text"])])
    got = tracked.auto_tracked(conn, today=date(2026, 10, 6))
    assert [m.registry for m in got] == ["openai/gpt-6.1-sol"]
    assert "openai/odd-1" in caplog.text and "hologram" in caplog.text


def test_transcription_is_its_own_kind_not_speech():
    """Speech-to-text and text-to-speech search different repos (#602 review)."""
    assert tracked.kind_from_modalities("openai/whisper-x", ["transcription"]) == "transcription"
    assert tracked.kind_from_modalities("acme/voice-1", ["speech"]) == "speech"


def test_every_output_has_a_decided_kind_or_is_kept_off():
    assert set(tracked.KIND_OF_OUTPUT) | tracked.KEPT_OFF_OUTPUTS == tracked.KNOWN_MODALITIES
    assert not set(tracked.KIND_OF_OUTPUT) & tracked.KEPT_OFF_OUTPUTS


def test_no_catalogue_row_leaves_the_model_off_rather_than_text(setup, caplog):
    conn = _Conn([("openai/new-1", "OpenAI: New 1", date(2026, 10, 1), None)])
    assert tracked.auto_tracked(conn, today=date(2026, 10, 6)) == ()
    assert "openai/new-1" in caplog.text


def test_every_catalogue_type_is_a_known_modality():
    from judge.catalog import TYPES
    assert set(TYPES) <= tracked.KNOWN_MODALITIES


class TestTheRuleIsReadStrictly:
    @pytest.fixture(autouse=True)
    def _clear(self):
        config.auto_track_rule.cache_clear()
        yield
        config.auto_track_rule.cache_clear()

    def test_the_contract_rule_loads(self):
        rule = config.auto_track_rule()
        assert rule.enabled and rule.include_pro_tier and rule.released_within_days == 30
        assert "image" in rule.exclude_name_terms

    @pytest.mark.parametrize("block", [
        None,
        {"enabled": "yes", "providers": "from_tracked", "released_within_days": 30,
         "include_pro_tier": True, "exclude_name_terms": []},
        {"enabled": True, "providers": ["openai"], "released_within_days": 30,
         "include_pro_tier": True, "exclude_name_terms": []},
        {"enabled": True, "providers": "from_tracked", "released_within_days": 0,
         "include_pro_tier": True, "exclude_name_terms": []},
    ])
    def test_a_missing_or_malformed_rule_raises(self, monkeypatch, block):
        monkeypatch.setattr(config, "_read", lambda name: {"auto_track": block})
        with pytest.raises(AutoTrackConfigError):
            config.auto_track_rule()
