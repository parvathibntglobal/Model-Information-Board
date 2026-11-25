"""Which OpenRouter hosts serve the extractor on the nightly runs (2026-11-25).

From 14 Nov DeepInfra's deepseek-v4-flash answered "no claim" to nearly every thread
(14-24 Nov: 1,518 threads read by DeepInfra alone, 125 verified quotes; the other
hosts, 2,351 threads, 5,453). With no preference sent, OpenRouter routed part of every
night there, and the last models of the 24 Nov run got no quotes at all. These pin:
  * both workflows that extract send the same preference, with DeepInfra and
    OpenInference ruled out;
  * the client turns those two lines into OpenRouter's `provider` object, and an
    unknown sort is refused rather than dropped (rule 12).
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from judge.extract import client

ROOT = pathlib.Path(__file__).resolve().parents[1]
#: Every workflow that calls deepseek-v4-flash through OpenRouter: the two fetches
#: (the extractor) and the evidence feed (its paraphrases and summaries, 2026-11-25).
EXTRACTING_WORKFLOWS = ("scheduled-fetches.yml", "agent-fetches.yml", "evidence-feed.yml")


def _env(file: str) -> dict:
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / file).read_text(encoding="utf-8"))
    (job,) = [j for name, j in wf["jobs"].items() if name != "guard"]
    return job["env"]


@pytest.mark.parametrize("file", EXTRACTING_WORKFLOWS)
def test_the_nightly_workflows_rule_out_deepinfra_and_openinference(file):
    env = _env(file)
    assert env["EXTRACTOR_PROVIDER_SORT"] == "throughput", file
    ignored = {h.strip() for h in env["EXTRACTOR_PROVIDER_IGNORE"].split(",")}
    assert {"DeepInfra", "OpenInference"} <= ignored, file


def test_every_workflow_sends_the_same_preference():
    first, *rest = (_env(f) for f in EXTRACTING_WORKFLOWS)
    for other in rest:
        for key in ("EXTRACTOR_PROVIDER_SORT", "EXTRACTOR_PROVIDER_IGNORE"):
            assert first[key] == other[key], key


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
    kw = dict(model="deepseek/deepseek-v4-flash", system="s", user="u", tool=paraphrase.TOOL,
              run_id="r", max_tokens=10, reasoning_effort="none")

    env = _env("evidence-feed.yml")
    monkeypatch.setenv("EXTRACTOR_PROVIDER_SORT", env["EXTRACTOR_PROVIDER_SORT"])
    monkeypatch.setenv("EXTRACTOR_PROVIDER_IGNORE", env["EXTRACTOR_PROVIDER_IGNORE"])
    llm.call_tool(**kw)
    assert sent[-1]["provider"] == {"sort": "throughput", "ignore": ["DeepInfra", "OpenInference"]}

    # Unset, nothing is sent and OpenRouter chooses, as before.
    monkeypatch.delenv("EXTRACTOR_PROVIDER_SORT")
    monkeypatch.delenv("EXTRACTOR_PROVIDER_IGNORE")
    llm.call_tool(**kw)
    assert "provider" not in sent[-1]


def test_the_two_lines_become_openrouters_provider_object(monkeypatch):
    env = _env("scheduled-fetches.yml")
    monkeypatch.setenv("EXTRACTOR_PROVIDER_SORT", env["EXTRACTOR_PROVIDER_SORT"])
    monkeypatch.setenv("EXTRACTOR_PROVIDER_IGNORE", env["EXTRACTOR_PROVIDER_IGNORE"])
    assert client.extractor_provider() == {
        "sort": "throughput", "ignore": ["DeepInfra", "OpenInference"]}


def test_an_unknown_sort_is_refused_not_dropped(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_PROVIDER_SORT", "fastest")
    monkeypatch.setenv("EXTRACTOR_PROVIDER_IGNORE", "DeepInfra")
    with pytest.raises(RuntimeError, match="EXTRACTOR_PROVIDER_SORT"):
        client.extractor_provider()
