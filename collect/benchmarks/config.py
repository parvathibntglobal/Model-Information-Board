"""Load `contract/benchmarks/*.yaml` and check it before anything runs (L1).

A bad config stops the run at SETUP with every problem listed, rather than
failing halfway through a source. Read strictly: a missing key is an error,
never a default in code (rule 12).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from collect.config import CONTRACT_DIR, REPO_ROOT

CONFIG_DIR = CONTRACT_DIR / "benchmarks"
FILES = (
    "benchmarks.yaml",
    "sources.yaml",
    "model_extras.yaml",
    "settings_vocabulary.yaml",
    "validation.yaml",
    "module_settings.yaml",
)

METRICS = {"score", "rank", "rating"}
METHODS = {"static", "browser"}
LOCATE_TYPES = {"html_table", "embedded_json", "next_flight"}
SCALES = {"percent", "fraction"}
DUPLICATES = {"match_variant", "latest", "identical"}


class ConfigError(ValueError):
    """L1 failed. `problems` lists every one, not just the first."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class Benchmark:
    key: str
    label: str
    category: str
    order: int
    metrics: tuple[str, ...]
    higher_is_better: bool
    volatility: str
    accept: tuple[str | None, ...]
    duplicates: str
    score_unit: str | None = None
    rating_range: tuple[int, int] | None = None
    benchmark_version: str | None = None


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    order: int


@dataclass(frozen=True)
class Table:
    """One extraction from one fetched document."""

    locate: dict[str, Any]
    benchmark_map: dict[str, dict[str, Any]]
    model_column: str | None = None
    model_selector: str | None = None  # CSS selector for the name inside the model cell
    #: Regex over the model name with named groups `model`, and optionally
    #: `variant` (the test setup, e.g. an agent) and `setting`. Scale writes
    #: "Opus 5 (Claude Code) xhigh": model, agent in brackets, then the setting.
    name_pattern: str | None = None
    setting_attr: str | None = None  # attribute of that element that states the setting
    setting_pattern: str | None = None  # regex; group 1 is the setting word
    model_field: str | None = None
    setting_field: str | None = None
    variant_field: str | None = None
    date_field: str | None = None
    date_column: str | None = None
    #: CSS selector for the page's release date (LiveBench: ".lb-tl-head .date").
    #: It becomes each value's source date, and a new release is recognised as
    #: one: its changed values are not flagged as jumps (2026-10-26).
    release_selector: str | None = None
    #: Setting words this table writes bare at the end of a name, after "-" or a
    #: space ("gpt-5.1-thinking", Scale HLE). Nowhere else is a bare trailing
    #: word read as a setting: it can be part of a model's name ("Qwen3 Max").
    bare_setting_words: tuple[str, ...] = ()
    variant: str | None = None
    rank: dict[str, Any] | None = None
    rank_board: str | None = None
    priority: int | None = None
    duplicates: str | None = None


@dataclass(frozen=True)
class Source:
    key: str
    label: str
    kind: str
    priority: int
    enabled: bool
    method: str
    url: str
    license: str
    attribution: str
    tables: tuple[Table, ...]
    page_url: str | None = None
    why_disabled: str | None = None


@dataclass(frozen=True)
class Vocabulary:
    words: dict[str, str]  # normalised word -> standard setting
    not_stated: frozenset[str]
    patterns: tuple[re.Pattern[str], ...]
    date_patterns: tuple[re.Pattern[str], ...] = ()


@dataclass(frozen=True)
class Extras:
    aliases: tuple[str, ...] = ()
    auto_add_settings: bool = True
    allowed_settings: tuple[str, ...] = ()
    not_names: tuple[str, ...] = ()  # names that are NOT this model, whatever else says so


@dataclass(frozen=True)
class Config:
    categories: tuple[Category, ...]
    benchmarks: dict[str, Benchmark]
    sources: tuple[Source, ...]
    extras: dict[str, Extras]
    vocabulary: Vocabulary
    validation: dict[str, Any]
    settings: dict[str, Any]
    files: tuple[str, ...] = field(default=FILES)

    def source(self, key: str) -> Source:
        for s in self.sources:
            if s.key == key:
                return s
        raise KeyError(key)

    @property
    def log_dir(self) -> Path:
        return REPO_ROOT / self.settings["log_dir"]


def _read(directory: Path, name: str) -> Any:
    path = directory / name
    if not path.exists():
        raise ConfigError([f"{name}: missing from {directory}"])
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigError([f"{name}: not valid YAML: {error}"]) from error


def load(directory: Path = CONFIG_DIR) -> Config:
    """Every file, checked together. Raises ConfigError listing all problems."""
    problems: list[str] = []
    raw = {name: _read(directory, name) for name in FILES}

    categories = tuple(
        Category(key=c["key"], label=c["label"], order=int(c["order"]))
        for c in raw["benchmarks.yaml"]["categories"]
    )
    category_keys = {c.key for c in categories}

    benchmarks: dict[str, Benchmark] = {}
    for b in raw["benchmarks.yaml"]["benchmarks"]:
        key = b["key"]
        if key in benchmarks:
            problems.append(f"benchmarks.yaml: benchmark {key!r} is listed twice")
        if b["category"] not in category_keys:
            problems.append(
                f"benchmarks.yaml: {key} names category {b['category']!r}, which is not defined"
            )
        metrics = tuple(b["metrics"])
        for m in metrics:
            if m not in METRICS:
                problems.append(f"benchmarks.yaml: {key} has unknown metric {m!r}")
        if "rating" in metrics and not b.get("rating_range"):
            problems.append(f"benchmarks.yaml: {key} has a rating and no rating_range")
        if "score" in metrics and b.get("score_unit") != "percent":
            problems.append(
                f"benchmarks.yaml: {key} score_unit must be 'percent' (the only unit built)"
            )
        duplicates = b.get("duplicates", "match_variant")
        if duplicates not in DUPLICATES:
            problems.append(
                f"benchmarks.yaml: {key} duplicates {duplicates!r} "
                f"is not one of {sorted(DUPLICATES)}"
            )
        benchmarks[key] = Benchmark(
            key=key,
            label=b["label"],
            category=b["category"],
            order=int(b["order"]),
            metrics=metrics,
            higher_is_better=bool(b["higher_is_better"]),
            volatility=b["volatility"],
            accept=tuple(b["variant_rule"]["accept"]),
            duplicates=duplicates,
            score_unit=b.get("score_unit"),
            rating_range=tuple(b["rating_range"]) if b.get("rating_range") else None,
            benchmark_version=b.get("benchmark_version"),
        )

    sources: list[Source] = []
    seen_sources: set[str] = set()
    for s in raw["sources.yaml"]["sources"]:
        key = s["key"]
        if key in seen_sources:
            problems.append(f"sources.yaml: source {key!r} is listed twice")
        seen_sources.add(key)
        if s["method"] not in METHODS:
            problems.append(
                f"sources.yaml: {key} method {s['method']!r} is not one of {sorted(METHODS)}"
            )
        if not isinstance(s["priority"], int):
            problems.append(f"sources.yaml: {key} priority must be an integer")
        if not str(s["url"]).startswith("https://"):
            problems.append(f"sources.yaml: {key} url must be https://")
        for required in ("license", "attribution"):
            if not s.get(required):
                problems.append(f"sources.yaml: {key} has no {required} (doc 22.3 #24)")
        if not s["enabled"] and not s.get("why_disabled"):
            problems.append(f"sources.yaml: {key} is disabled and does not say why")
        tables = []
        for i, t in enumerate(s.get("tables") or []):
            where = f"sources.yaml: {key} table {i + 1}"
            locate = t["locate"]
            if locate.get("type") not in LOCATE_TYPES:
                problems.append(
                    f"{where}: locate.type {locate.get('type')!r} "
                    f"is not one of {sorted(LOCATE_TYPES)}"
                )
            rank = t.get("rank") or {}
            if rank.get("from") == "row_order" and not any(
                m.get("benchmark") == rank.get("benchmark") and m.get("metric") == "score"
                for m in t["benchmark_map"].values()
            ):
                problems.append(
                    f"{where}: a row_order rank needs the same benchmark's score in the "
                    "table, to check the rows really are in score order"
                )
            if not (t.get("model_column") or t.get("model_field")):
                problems.append(f"{where}: names no model_column or model_field")
            for header, target in t["benchmark_map"].items():
                bench = benchmarks.get(target.get("benchmark"))
                if bench is None:
                    problems.append(
                        f"{where}: {header!r} maps to unknown benchmark {target.get('benchmark')!r}"
                    )
                    continue
                metric = target.get("metric")
                if metric not in METRICS:
                    problems.append(
                        f"{where}: {header!r} has no explicit metric (score|rank|rating)"
                    )
                elif metric not in bench.metrics:
                    problems.append(
                        f"{where}: {header!r} maps to {bench.key}_{metric}, "
                        "which is not an enabled metric"
                    )
                if metric == "score" and target.get("scale") not in SCALES:
                    problems.append(f"{where}: {header!r} needs scale: percent|fraction (doc 8.1)")
            rank = t.get("rank")
            if rank:
                bench = benchmarks.get(rank.get("benchmark"))
                if bench is None or "rank" not in bench.metrics:
                    problems.append(
                        f"{where}: rank maps to {rank.get('benchmark')!r}, which has no rank column"
                    )
                if rank.get("from") not in ("row_order", "order_by"):
                    problems.append(f"{where}: rank.from must be row_order or order_by")
            if t.get("duplicates") and t["duplicates"] not in DUPLICATES:
                problems.append(
                    f"{where}: duplicates {t['duplicates']!r} is not one of {sorted(DUPLICATES)}"
                )
            tables.append(
                Table(
                    locate=dict(locate),
                    benchmark_map={h: dict(v) for h, v in t["benchmark_map"].items()},
                    model_column=t.get("model_column"),
                    model_selector=t.get("model_selector"),
                    name_pattern=t.get("name_pattern"),
                    setting_attr=t.get("setting_attr"),
                    setting_pattern=t.get("setting_pattern"),
                    model_field=t.get("model_field"),
                    setting_field=t.get("setting_field"),
                    variant_field=t.get("variant_field"),
                    date_field=t.get("date_field"),
                    date_column=t.get("date_column"),
                    release_selector=t.get("release_selector"),
                    bare_setting_words=tuple(t.get("bare_setting_words") or ()),
                    variant=t.get("variant"),
                    rank=dict(rank) if rank else None,
                    rank_board=t.get("rank_board"),
                    priority=t.get("priority"),
                    duplicates=t.get("duplicates"),
                )
            )
        if s["enabled"] and not tables:
            problems.append(f"sources.yaml: {key} is enabled and has no tables")
        sources.append(
            Source(
                key=key,
                label=s["label"],
                kind=s["kind"],
                priority=s["priority"],
                enabled=bool(s["enabled"]),
                method=s["method"],
                url=s["url"],
                license=s.get("license") or "",
                attribution=s.get("attribution") or "",
                tables=tuple(tables),
                page_url=s.get("page_url"),
                why_disabled=s.get("why_disabled"),
            )
        )

    vocab_raw = raw["settings_vocabulary.yaml"]
    words: dict[str, str] = {}
    for setting, spellings in vocab_raw["settings"].items():
        for word in spellings:
            norm = normalise_word(word)
            if norm in words and words[norm] != setting:
                problems.append(
                    f"settings_vocabulary.yaml: {word!r} maps to both "
                    f"{words[norm]!r} and {setting!r}"
                )
            words[norm] = setting
    vocabulary = Vocabulary(
        words=words,
        not_stated=frozenset(normalise_word(w) for w in vocab_raw.get("not_stated") or []),
        patterns=tuple(re.compile(p) for p in vocab_raw["patterns"]),
        date_patterns=tuple(re.compile(p) for p in vocab_raw.get("date_patterns") or ()),
    )

    extras: dict[str, Extras] = {}
    for model_id, entry in (raw["model_extras.yaml"] or {}).items():
        entry = entry or {}
        allowed = tuple(entry.get("allowed_settings") or ())
        for setting in allowed:
            if setting not in vocab_raw["settings"]:
                problems.append(f"model_extras.yaml: {model_id} allows unknown setting {setting!r}")
        extras[model_id] = Extras(
            aliases=tuple(entry.get("aliases") or ()),
            auto_add_settings=bool(entry.get("auto_add_settings", True)),
            allowed_settings=allowed,
            not_names=tuple(entry.get("not_names") or ()),
        )
        if entry.get("not_in_registry"):
            problems.append(
                f"model_extras.yaml: {model_id} is not_in_registry - only registry models get rows"
            )

    settings_raw = raw["module_settings.yaml"]
    for required in (
        "timeouts",
        "retries",
        "log_dir",
        "verbosity",
    ):
        if required not in settings_raw:
            problems.append(f"module_settings.yaml: missing {required}")

    if problems:
        raise ConfigError(problems)
    return Config(
        categories=tuple(sorted(categories, key=lambda c: c.order)),
        benchmarks=benchmarks,
        sources=tuple(sources),
        extras=extras,
        vocabulary=vocabulary,
        validation=raw["validation.yaml"],
        settings=settings_raw,
    )


def normalise_word(word: str) -> str:
    """A setting word as compared: lowercase, single spaces."""
    return " ".join(str(word).lower().replace("_", " ").split())
