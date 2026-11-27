"""Which OpenRouter hosts serve the extractor and the evidence feed (2026-11-25; one
source since 2026-11-26, #677 review).

From 14 Nov DeepInfra's deepseek-v4-flash answered "no claim" to nearly every thread
(14-24 Nov: 1,518 threads read by DeepInfra alone, 125 verified quotes; the other
hosts, 2,351 threads, 5,453). The preference lived in five places (three workflows,
Railway, .env) until Parvathi chose "contract only". These pin:
  * contract/scheduler.yaml `extractor_provider` rules out DeepInfra and OpenInference,
    and is the only thing read - no workflow sets the old variables;
  * a still-set EXTRACTOR_PROVIDER_* is IGNORED, with a warning;
  * a missing block, a missing key or an unknown sort is refused (rule 12);
  * the extractor's request and the feed's both carry it; a replay pins a host only by
    passing `provider=` explicitly.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from judge.extract import client

ROOT = pathlib.Path(__file__).resolve().parents[1]
#: Every workflow that calls deepseek-v4-flash through OpenRouter: the two fetches
#: (the extractor) and the evidence feed (its paraphrases and summaries).
EXTRACTING_WORKFLOWS = ("scheduled-fetches.yml", "agent-fetches.yml", "evidence-feed.yml")
EXPECTED = {"sort": "throughput", "ignore": ["DeepInfra", "OpenInference"]}


@pytest.fixture(autouse=True)
def _no_old_variables(monkeypatch):
    for name in client.RETIRED_PROVIDER_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(client, "_warned", set())


def _contract(monkeypatch, block):
    """Serve contract/scheduler.yaml with `extractor_provider` replaced (None = absent)."""
    from judge import config

    real = config._read

    def read(name):
        raw = real(name)
        if name != "scheduler.yaml":
            return raw
        raw = dict(raw)
        raw.pop("extractor_provider", None)
        if block is not None:
            raw["extractor_provider"] = block
        return raw

    monkeypatch.setattr(config, "_read", read)


def test_the_contract_rules_out_deepinfra_and_openinference():
    assert client.extractor_provider() == EXPECTED


@pytest.mark.parametrize("file", EXTRACTING_WORKFLOWS + ("industry-ai-harvest.yml",))
def test_no_workflow_sets_the_old_variables(file):
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / file).read_text(encoding="utf-8"))
    for job in wf["jobs"].values():
        for name in client.RETIRED_PROVIDER_VARIABLES:
            assert name not in (job.get("env") or {}), (file, name)
            for step in job.get("steps") or []:
                assert name not in (step.get("env") or {}), (file, name)


def test_env_example_does_not_set_them():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for name in client.RETIRED_PROVIDER_VARIABLES:
        assert f"\n{name}=" not in text, name


def test_a_leftover_variable_is_ignored_and_warned_once(monkeypatch, capsys):
    monkeypatch.setenv("EXTRACTOR_PROVIDER_SORT", "price")
    monkeypatch.setenv("EXTRACTOR_PROVIDER_IGNORE", "Wafer")
    assert client.extractor_provider() == EXPECTED
    assert client.extractor_provider() == EXPECTED
    err = capsys.readouterr().err
    assert err.count("EXTRACTOR_PROVIDER_SORT is set and IGNORED") == 1
    assert err.count("EXTRACTOR_PROVIDER_IGNORE is set and IGNORED") == 1


@pytest.mark.parametrize("block, says", [
    (None, "must have exactly"),
    ({"sort": "throughput"}, "must have exactly"),
    ({"sort": "fastest", "ignore": []}, "is not one of"),
    ({"sort": "throughput", "ignore": "DeepInfra"}, "must be a list"),
    ({"sort": "throughput", "ignore": ["DeepInfra", ""]}, "must be a list"),
])
def test_a_bad_contract_is_refused_not_dropped(monkeypatch, block, says):
    _contract(monkeypatch, block)
    with pytest.raises(client.ExtractorProviderError, match=says):
        client.extractor_provider()


def test_an_empty_ignore_list_rules_none_out(monkeypatch):
    _contract(monkeypatch, {"sort": "latency", "ignore": []})
    assert client.extractor_provider() == {"sort": "latency"}


def test_the_extractor_sends_it_and_a_replay_pins_a_host_explicitly():
    assert client.OpenRouterClient().provider == EXPECTED
    pinned = {"order": ["Wafer"], "allow_fallbacks": False}
    assert client.OpenRouterClient(provider=pinned).provider == pinned
    src = (ROOT / "judge" / "extract" / "client.py").read_text(encoding="utf-8")
    assert '"provider": self.provider,' in src


def test_the_feeds_calls_carry_the_preference(monkeypatch):
    """judge/feed/llm.py: the feed's paraphrases and summaries go to the same hosts.
    Replayed 2026-11-25: DeepInfra returned nothing for 2 of 4 batches of 20."""
    from judge.feed import llm, paraphrase

    sent = []

    class Resp:
        status_code = 200

        def json(self):
            return {"model": "deepseek/deepseek-v4-flash", "usage": {"cost": 0.0},
                    "choices": [{"message": {"tool_calls": [
                        {"function": {"arguments": '{"paraphrases": []}'}}]}}]}

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.test/api/v1")
    monkeypatch.setattr(llm.spend_ledger, "record", lambda **kw: None)
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: sent.append(k["json"]) or Resp())
    llm.call_tool(model="deepseek/deepseek-v4-flash", system="s", user="u", tool=paraphrase.TOOL,
                  run_id="r", max_tokens=10, reasoning_effort="none")
    assert sent[-1]["provider"] == EXPECTED
