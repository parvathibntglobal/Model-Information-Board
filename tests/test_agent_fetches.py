"""The agent fetch (#609-#611): its own list, its own run, never mixed with models.

No database: the contract is read from disk, and the runner's query is faked.
"""
from __future__ import annotations

import pathlib

import pytest
import yaml

import scripts.fetch_model as fetch_model
import scripts.run_scheduled_fetches as runner
from collect.registry.aliases import classify_specificity
from collect.registry.load import load_seed_file
from judge import config

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _fresh_contract_cache():
    for fn in (config._agents_raw, config.agent_run_rule, config.tracked_agents):
        fn.cache_clear()
    yield
    for fn in (config._agents_raw, config.agent_run_rule, config.tracked_agents):
        fn.cache_clear()


# ── the contract ─────────────────────────────────────────────────────────────

def test_the_real_lists_agree_and_never_touch_the_model_list():
    agents = config.tracked_agents()
    seed = load_seed_file(ROOT / "contract" / "agent_models.yaml")
    seeded = {m.canonical_id for m in seed.models}
    assert len(agents) == 9
    assert {a.registry for a in agents} == seeded  # every tracked agent has a registry row
    # NEVER IN tracked_models.yaml: that list feeds the model fetch, the models
    # page and auto_track (whose providers would then admit Meta's models).
    model_ids = {m.registry for m in config.tracked_models() if m.registry}
    assert not model_ids & seeded
    assert all(m.kind != "agent" for m in config.tracked_models())


def test_every_agent_alias_is_a_snapshot_never_a_family_row():
    """Test B's lesson: a digitless name is searched only as a snapshot, i.e. the
    id's local part. A family row is never searched and resolves at family level."""
    for m in load_seed_file(ROOT / "contract" / "agent_models.yaml").models:
        for surface in [m.aliases.surface, *m.aliases.variants]:
            assert classify_specificity(surface, m) == "snapshot", (m.canonical_id, surface)


def test_the_run_settings_are_read_strictly():
    rule = config.agent_run_rule()
    assert rule.enabled is True and rule.run_spend_ceiling_usd > 0


def _with_raw(monkeypatch, raw):
    monkeypatch.setattr(config, "_read", lambda name: raw if name == "tracked_agents.yaml" else {})


@pytest.mark.parametrize("broken, says", [
    ({"run": {"enabled": True}}, "run_spend_ceiling_usd"),
    ({"run": {"enabled": "yes", "run_spend_ceiling_usd": 1}}, "run.enabled"),
    ({"run": {"enabled": True, "run_spend_ceiling_usd": 0}}, "positive number"),
])
def test_a_missing_or_wrong_run_setting_is_refused(monkeypatch, broken, says):
    _with_raw(monkeypatch, broken)
    with pytest.raises(config.AgentConfigError, match=says):
        config.agent_run_rule()


@pytest.mark.parametrize("agent, says", [
    ({"name": "X", "registry": "a/x", "search_terms": []}, "subreddits"),
    ({"name": "X", "registry": "nope", "search_terms": [], "subreddits": []}, "canonical id"),
    ({"name": "X", "registry": "a/x", "search_terms": [""], "subreddits": []}, "non-empty strings"),
])
def test_a_malformed_agent_is_refused_not_defaulted(monkeypatch, agent, says):
    _with_raw(monkeypatch, {"agents": [agent]})
    with pytest.raises(config.AgentConfigError, match=says):
        config.tracked_agents()


def test_an_agent_listed_twice_is_refused(monkeypatch):
    a = {"name": "X", "registry": "a/x", "search_terms": [], "subreddits": []}
    _with_raw(monkeypatch, {"agents": [a, dict(a)]})
    with pytest.raises(config.AgentConfigError, match="listed twice"):
        config.tracked_agents()


# ── the fetch ────────────────────────────────────────────────────────────────

def test_an_agent_takes_the_name_only_path():
    assert "agent" in fetch_model.MEDIA_KINDS


def test_an_agent_is_recognised_by_either_id_and_a_model_is_not(monkeypatch):
    import judge.tracked as tracked

    monkeypatch.setattr(tracked, "all_tracked", lambda conn: ())
    assert fetch_model._tracked_kind(None, "mv_x", "meta/meta-muse") == "agent"
    assert fetch_model._tracked_kind(None, "mv_x", "openai/gpt-6-astra") is None


def test_search_terms_come_right_after_the_primary_spelling():
    v = ["meta muse", "meta-muse", "metamuse"]
    assert fetch_model._with_search_terms(v, ("muse whatsapp",)) == [
        "meta muse", "muse whatsapp", "meta-muse", "metamuse"]
    assert fetch_model._with_search_terms(v, ("meta muse",)) == v  # never duplicated
    assert fetch_model._with_search_terms([], ("muse whatsapp",)) == []  # no name, no search


def test_own_subreddits_are_lower_cased_and_shared_ones_are_absent():
    by = {a.registry: a for a in config.tracked_agents()}
    assert by["xai/grok-bot"].subreddits == {"grokbot"}
    assert by["openclaw/openclaw"].subreddits == {"openclaw"}
    assert all("askclaw" not in a.subreddits and "chatgptpro" not in a.subreddits
               for a in by.values())


# ── the runner ───────────────────────────────────────────────────────────────

class _Conn:
    def execute(self, *a, **k):
        return self

    def fetchall(self):
        return []


def test_the_agent_list_is_fetched_and_a_missing_row_is_named(monkeypatch):
    rows = runner.due_rows(_Conn(), "agents")
    assert {r["registry"] for r in rows} == {a.registry for a in config.tracked_agents()}
    assert all(r.get("registry_row_missing") for r in rows)  # named, not dropped (rule 4)


def test_an_unknown_list_is_refused():
    with pytest.raises(ValueError, match="models' or 'agents"):
        runner.due_rows(_Conn(), "everything")


def test_the_workflow_runs_agents_on_their_own_schedule_and_issue():
    workflows = ROOT / ".github" / "workflows"
    wf = yaml.safe_load((workflows / "agent-fetches.yml").read_text(encoding="utf-8"))
    job = wf["jobs"]["fetch"]
    assert wf["concurrency"]["group"] == "agent-fetches"
    assert job["env"]["SCHEDULER_ISSUE"] == "${{ vars.AGENT_SCHEDULER_ISSUE }}"
    assert any("--list agents" in (s.get("run") or "") for s in job["steps"])
    model_wf = (workflows / "scheduled-fetches.yml").read_text(encoding="utf-8")
    assert "--list agents" not in model_wf
