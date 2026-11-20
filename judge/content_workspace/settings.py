"""The workspace's settings and seed, read from `config/`.

No defaults in code (rule 12): a missing key raises KeyError where it is read.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

HERE = Path(__file__).parent / "config"
SETTINGS_FILE = HERE / "workspace.yaml"
SEED = HERE / "seed_platforms.yaml"

SECTIONS = ("philosophy", "research", "rule", "recommendation")
# The seed file's plural keys for each section.
SEED_SECTION_KEYS = {"philosophy": "philosophy", "research": "research",
                     "rule": "rules", "recommendation": "recommendations"}


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """workspace.yaml, read once per process (restart the backend after editing it)."""
    return yaml.safe_load(SETTINGS_FILE.read_text(encoding="utf-8"))


def site_hosts(s: dict[str, Any], environ: dict[str, str] | None = None) -> list[str]:
    """Our site's hosts: those listed, plus the host of the URL in the
    environment variable `site.hosts_env` names, when it is set."""
    environ = os.environ if environ is None else environ
    hosts = list(s["site"]["hosts"])
    url = (environ.get(s["site"]["hosts_env"]) or "").strip()
    if url:
        host = urlsplit(url if "://" in url else f"https://{url}").hostname
        if host:
            hosts.append(host.removeprefix("www."))
    return hosts


def seed(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or SEED).read_text(encoding="utf-8"))
