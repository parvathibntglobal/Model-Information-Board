"""Every platform a blog post may quote has a public name (2026-10-27).

`platform_name` refuses a source it cannot name (rule 12), which is right - but
nothing checked the names against the contract, so #568 seated the Google AI
Developers Forum (`forum`) and the first board pack that drew on a forum thread
stopped with "no public name for source 'forum'". A new source is now caught
here, in the PR that seats it.

Embed-only sources are left out: they are never quoted, and one with no post
address to embed is dropped before it is named (generate_sample_blogs.py,
"A THREAD THAT CANNOT BE EMBEDDED IS NOT CHOSEN").
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import generate_sample_blogs as g  # noqa: E402


def _yaml(name: str) -> dict:
    return yaml.safe_load((ROOT / "contract" / name).read_text(encoding="utf-8"))


def test_every_quotable_platform_in_the_contract_has_a_public_name():
    sources = _yaml("sources.yaml")
    platforms = {s["platform"] for s in sources["sources"]} | {
        f["platform"] for f in sources["feeds"]
    }
    embed_only = set(_yaml("publication.yaml")["derived_posts"]["embed_only"])
    unnamed = sorted(p for p in platforms - embed_only if p not in g.PLATFORM)
    assert not unnamed, f"add these to generate_sample_blogs.PLATFORM: {unnamed}"


def test_the_forum_is_named_without_a_username():
    assert g.platform_name("forum") == "a developer forum"
