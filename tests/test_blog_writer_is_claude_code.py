"""While blog_formats.yaml says `writer: claude-code` (2026-10-16), the blog
makes no OpenRouter call: Admin's Generate is refused before a run starts, the
generator refuses its model path, and Admin shows the method and the packs.
"""

from __future__ import annotations

import pytest

from judge import blog_method, blog_posts


def test_the_writer_is_read_from_the_formats_file():
    assert blog_method.writer() == "claude-code"


def test_admin_generate_is_refused_before_any_run(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setattr(blog_posts, "_proc", None)
    with pytest.raises(blog_posts.GenerationRefused) as e:
        blog_posts.start_generation(3)
    assert e.value.status == 409 and "Claude Code" in e.value.detail


def test_the_generator_refuses_its_model_path(monkeypatch, tmp_path):
    import importlib.util
    import pathlib
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("gsb", root / "generate_sample_blogs.py")
    gsb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gsb)
    monkeypatch.setattr(sys, "argv", ["generate_sample_blogs.py", "--plan", "1"])
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    with pytest.raises(gsb.BuildError, match="claude-code"):
        gsb.main()


def test_the_method_names_every_stage_and_rule_group():
    m = blog_method.method()
    assert [s["who"] for s in m["stages"]].count("person") == 1  # a person approves
    assert any(s["who"] == "writer" for s in m["stages"])
    assert {g["group"] for g in m["rules"]} >= {"Quotes and sources", "Numbers", "Shape", "Writing"}
