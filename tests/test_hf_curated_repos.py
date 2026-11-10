"""A media model's curated Hugging Face repos are walked as named (#602).

No network: search and listing are replaced on the instance.
"""
from __future__ import annotations

from collect.adapters.huggingface import HuggingFaceHarvester
from judge.config import tracked_models


def _harvester(monkeypatch, asked):
    h = HuggingFaceHarvester(client=None, store=None)
    monkeypatch.setattr(h, "search_repos", lambda *a, **k: asked.append("search") or None)
    monkeypatch.setattr(h, "list_discussions",
                        lambda repo_id, run, page=0: asked.append(repo_id) or [])
    return h


def test_curated_repos_skip_the_name_search(monkeypatch):
    asked: list = []
    run = _harvester(monkeypatch, asked).harvest(
        "flux 3", repo_ids=["black-forest-labs/FLUX.1-dev"])
    assert asked == ["black-forest-labs/FLUX.1-dev"], "no search, exactly the named repo"
    assert run.repos_walked == ["black-forest-labs/FLUX.1-dev"]


def test_no_curated_repos_means_the_name_search_runs(monkeypatch):
    asked: list = []
    h = _harvester(monkeypatch, asked)

    class _Run:
        repos_matched: list = []
        repos_walked: list = []
        truncated_by = None
        finished_at = None

    monkeypatch.setattr(h, "search_repos", lambda q, run=None: asked.append("search") or _Run())
    h.harvest("flux 3")
    assert asked == ["search"]


def test_an_entry_without_hf_repos_reads_as_not_curated():
    """Absent is "not curated", never "has no repo" - every current entry."""
    assert all(isinstance(m.hf_repos, tuple) for m in tracked_models())
