"""Stage 3: raw model name -> table row (doc 6, 6.1).

Only EXACT aliases match, after normalisation. A tracked model names one exact
model and version; an alias is the same name written differently (spacing,
hyphens, dots, an org prefix). A similar-looking name is a DIFFERENT model and
is never matched, nor offered as a "closest" suggestion (Parvathi, 2026-10-22):
`gpt-6.1-sol-pro` is not `gpt-6.1-sol`, `gpt-5.6-luna` is not `gpt-6-luna`, and
`claude-sonnet-5` is not `claude-sonnet-5.5`.

Two steps, so a name with a setting finds its seed model and gets its own row:

    1. the whole name is an alias              -> the base row
    2. a settings pattern splits it            "gpt-6-astra_max" -> "gpt-6-astra", "max"
       the rest is an alias of a seed model    -> the setting row "GPT 6 Astra (max)"
       a word the vocabulary does not know     -> review item `unknown_setting`, no row
       a "not stated" word ("unknown")         -> the base row, marked "setting not stated"

The alias set per seed: its registry id, the id without its org prefix, its
display name, and `model_extras.yaml` aliases.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from collect.benchmarks.config import Config, normalise_word
from collect.benchmarks.host_adapter import SeedModel

_SEPARATORS = re.compile(r"[^a-z0-9]+")
_LETTER_DIGIT = re.compile(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])")

#: Words two names may differ by and still be "very similar" (2026-10-26): a
#: maker or brand word, and labels that name no different model. Never a size,
#: tier or release word - "mini", "pro", "flash", "preview", "max" make a
#: different model, so "o3" and "o3-mini" are never similar.
FILLER_WORDS = frozenset(
    {
        "claude",
        "anthropic",
        "openai",
        "google",
        "meta",
        "xai",
        "x",
        "ai",
        "mistralai",
        "deepseek",
        "alibaba",
        "zai",
        "z",
        "moonshotai",
        "moonshot",
        "bytedance",
        "chat",
        "instruct",
        "latest",
        "model",
    }
)


def similarity_key(name: str) -> tuple[frozenset[str], tuple[str, ...]] | None:
    """(the words that name the model, the numbers in order) - two names with
    the same key differ only by filler words. None when there is no number:
    a name with no version is too loose to call similar to anything."""
    tokens = normalize_name(name).split("-")
    numbers = tuple(t for t in tokens if t.isdigit())
    words = frozenset(t for t in tokens if t and not t.isdigit()) - FILLER_WORDS
    if not numbers or not words:
        return None
    return words, numbers


_ORG_PREFIX = re.compile(r"^[a-z0-9][a-z0-9._-]*/(?=\S)")


def normalize_name(name: str) -> str:
    """lowercase -> drop an "org/" prefix -> every run of non [a-z0-9] becomes "-".

    "anthropic/claude-opus-5.5", "Claude Opus 5.5" and "claude-opus-5-5" are
    one name (rule 10: a separator is not part of an identifier). The prefix is
    ONE word before the first "/" ("openai/gpt-5"); any other "/" is a
    separator - "Zonos2 8B / Kokoro 82M" is not "kokoro-82m" (PR #573 review).
    """
    s = _ORG_PREFIX.sub("", strip_symbols(name).lower().strip(), count=1)
    # A letter touching a digit is a boundary too: "Qwen3.8 27B" and "Qwen 3.8
    # 27B", "Seed2.0-Lite" and "seed-2.0-lite" are one name (2026-10-26).
    s = _LETTER_DIGIT.sub("-", s)
    return _SEPARATORS.sub("-", s).strip("-")


def strip_symbols(name: str) -> str:
    """Drop emoji and other symbols a board decorates names with ("⚠️")."""
    kept = "".join(
        ch
        for ch in str(name)
        if unicodedata.category(ch) not in ("So", "Sk", "Cf", "Mn") or ch in "()[]"
    )
    return " ".join(kept.split())


@dataclass(frozen=True)
class Row:
    row_id: str  # "<model id>", "<model id>:<setting>", "<model id>@<date>[:<setting>]"
    host_model_id: str
    setting: str | None
    label: str
    dated: str | None = None  # a dated release, the date as the source wrote it


@dataclass
class Match:
    row: Row | None
    reason: str = ""  # "" | unmatched | unknown_setting | setting_not_allowed
    setting_not_stated: bool = False
    #: The tracked model an unknown or refused SETTING belongs to (its base name
    #: matched exactly). Never set for an unmatched name.
    model_id: str | None = None
    setting_word: str | None = None
    #: The name with any setting or date removed from its end - what a person's
    #: decision about an unmatched name is keyed on (bench_name_decision).
    base_name: str | None = None
    #: Registry/tracked models this unmatched name is VERY close to (see
    #: `Resolver.similar`): shown for a person to confirm, never matched.
    similar_to: tuple[str, ...] = ()


def base_row(seed: SeedModel) -> Row:
    return Row(row_id=seed.id, host_model_id=seed.id, setting=None, label=seed.name)


def setting_row(seed: SeedModel, setting: str, dated: str | None = None) -> Row:
    if dated:
        return Row(
            row_id=f"{seed.id}@{_date_slug(dated)}:{setting}",
            host_model_id=seed.id,
            setting=setting,
            label=f"{seed.name} {dated} ({setting})",
            dated=dated,
        )
    return Row(
        row_id=f"{seed.id}:{setting}",
        host_model_id=seed.id,
        setting=setting,
        label=f"{seed.name} ({setting})",
    )


def _date_slug(dated: str) -> str:
    """ "(12/25)" -> "12-25". Not normalize_name: that reads "12/" as an org prefix."""
    return _SEPARATORS.sub("-", dated.lower()).strip("-")


def dated_row(seed: SeedModel, dated: str) -> Row:
    """A dated release: "Gemini 3 Flash (12/25)" under Gemini 3 Flash (2026-10-23)."""
    return Row(
        row_id=f"{seed.id}@{_date_slug(dated)}",
        host_model_id=seed.id,
        setting=None,
        label=f"{seed.name} {dated}",
        dated=dated,
    )


def _plausible_date(text: str) -> bool:
    """A date, not a model number: the month must be 1-12 (and a day 1-31)."""
    if "/" in text:  # month/year
        return 1 <= int(text.split("/")[0]) <= 12
    if re.fullmatch(r"[A-Za-z]+ \d{4}", text):  # "November 2024": the pattern lists the months
        return True
    digits = re.sub(r"\D", "", text)
    if len(digits) == 4:  # MMDD
        return 1 <= int(digits[:2]) <= 12 and 1 <= int(digits[2:]) <= 31
    if len(digits) == 8:  # YYYYMMDD (also YYYY-MM-DD)
        return 1 <= int(digits[4:6]) <= 12 and 1 <= int(digits[6:]) <= 31
    return False


class Resolver:
    def __init__(
        self,
        config: Config,
        seeds: list[SeedModel],
        registry_aliases: dict[str, list[str]] | None = None,
        registry_models: list[SeedModel] | None = None,
    ):
        """`registry_aliases`: the aliases the board's registry already holds for
        each seed (host_adapter.get_registry_aliases), used as exact names too.

        A collision among the config's own names stops the run (`problems`). A
        registry alias that would name two seeds is DROPPED for both and listed
        in `warnings`: an exact match on an ambiguous name is not exact.
        """
        self.config = config
        self.seeds = {s.id: s for s in seeds}
        self.index: dict[str, str] = {}
        self.problems: list[str] = []
        self.warnings: list[str] = []
        self.registry_alias_count = 0
        # `not_names`: spellings that are a DIFFERENT model, though the seed's own
        # registry id or the registry's aliases would match them (the registry
        # lists "Gemini 3 Flash" as an alias of Gemini 3 Flash PREVIEW).
        self.blocked = {
            normalize_name(n): seed.id
            for seed in seeds
            for n in (config.extras.get(seed.id).not_names if config.extras.get(seed.id) else ())
        }
        for seed in seeds:
            extras = config.extras.get(seed.id)
            names = [seed.id, seed.name, *(extras.aliases if extras else ())]
            for name in names:
                key = normalize_name(name)
                if self.blocked.get(key) == seed.id:
                    continue
                owner = self.index.get(key)
                if owner and owner != seed.id:
                    self.problems.append(
                        f"alias {name!r} normalises to {key!r}, which is already {owner!r}"
                    )
                self.index[key] = seed.id
        claimed: dict[str, set[str]] = {}
        for model_id, names in (registry_aliases or {}).items():
            if model_id not in self.seeds:
                continue
            for name in names:
                claimed.setdefault(normalize_name(name), set()).add(model_id)
        for key, owners in sorted(claimed.items()):
            if not key:
                continue
            if len(owners) > 1 or (key in self.index and self.index[key] not in owners):
                named = sorted(owners | {self.index.get(key)} - {None})
                self.warnings.append(f"registry alias {key!r} names {named} - not used")
                continue
            owner = next(iter(owners))
            if self.blocked.get(key) == owner:
                continue
            if key not in self.index:
                self.index[key] = owner
                self.registry_alias_count += 1
        self._add_registry_models(registry_models or [], registry_aliases or {})

    def _add_registry_models(self, models: list[SeedModel], aliases: dict[str, list[str]]) -> None:
        """Untracked registry models, matched as exactly as the tracked ones.

        A TRACKED model always owns its names. A registry model with any name a
        tracked model already has is left out whole - it is most likely a second
        registry entry for the same model (anthropic/claude-fable-5.1 beside the
        tracked anthropic/claude-fable-5-1, 2026-10-22) - and named in `warnings`.
        A name two registry models share is dropped for both.
        """
        self.registry_ids: set[str] = set()
        names_of: dict[str, set[str]] = {}
        for model in models:
            extras = self.config.extras.get(model.id)
            keys = {
                normalize_name(n)
                for n in [
                    model.id,
                    model.name,
                    *aliases.get(model.id, []),
                    *(extras.aliases if extras else ()),
                ]
            }
            # `not_names` holds for registry models too: the registry lists
            # "Gemini 3 Flash" as an alias of Gemini 3 Flash PREVIEW, and the two
            # are kept apart (Parvathi, 2026-10-23).
            keys -= {normalize_name(n) for n in (extras.not_names if extras else ())}
            keys.discard("")
            clash = sorted({self.index[k] for k in keys if k in self.index})
            same = [c for c in clash if normalize_name(c) == normalize_name(model.id)]
            if same:
                # The SAME model under another spelling of the tracked id: the
                # registry's anthropic/claude-fable-5.1 is the tracked
                # anthropic/claude-fable-5-1 (a dot for a hyphen; Parvathi,
                # 2026-10-26). Its names are aliases of the tracked row - no
                # second row, no warning.
                for key in keys:
                    if key not in self.index and self.blocked.get(key) != same[0]:
                        self.index[key] = same[0]
                        self.registry_alias_count += 1
                continue
            if clash:
                self.warnings.append(
                    f"registry model {model.id} shares a name with tracked {clash[0]} - "
                    "left out (a duplicate registry entry?)"
                )
                continue
            names_of[model.id] = keys
        claimed: dict[str, set[str]] = {}
        for model_id, keys in names_of.items():
            for key in keys:
                claimed.setdefault(key, set()).add(model_id)
        for model in models:
            if model.id not in names_of:
                continue
            self.seeds[model.id] = model
            self.registry_ids.add(model.id)
            for key in names_of[model.id]:
                if len(claimed[key]) > 1:
                    continue
                self.index[key] = model.id
        shared = sorted(k for k, owners in claimed.items() if len(owners) > 1)
        if shared:
            self.warnings.append(
                f"registry names shared by two registry models, not used: {shared}"
            )

    def similar(self, name: str) -> tuple[str, ...]:
        """Registry/tracked models whose name is VERY close to `name`.

        Close means: the same numbers in the same order, and the words differ
        only by FILLER_WORDS ("Opus 4.5" ~ "Claude Opus 4.5"). Built from the
        names matching actually uses. A name close to one of a model's not_names
        is not offered as that model either: the registry's "gemini-flash-3" alias
        of the PREVIEW must not make "Gemini 3 Flash" look like it (2026-10-26).
        A suggestion for a person, never a match.
        """
        if getattr(self, "_similar_index", None) is None:
            self._similar_index: dict[tuple, set[str]] = {}
            for key, model_id in self.index.items():
                sk = similarity_key(key)
                if sk:
                    self._similar_index.setdefault(sk, set()).add(model_id)
            for model_id, extras in self.config.extras.items():
                for not_name in extras.not_names:
                    sk = similarity_key(not_name)
                    if sk:
                        self._similar_index.get(sk, set()).discard(model_id)
        sk = similarity_key(name)
        return tuple(sorted(self._similar_index.get(sk, ()))) if sk else ()

    def _split_date(self, name: str) -> tuple[str, str] | None:
        """("DeepSeek V4 Pro", "0813") when the name ends in a date, else None."""
        for pattern in self.config.vocabulary.date_patterns:
            found = pattern.search(name)
            if found and _plausible_date(found.group(1)):
                return name[: found.start()].strip(" -_"), found.group(0).strip(" -_")
        return None

    def _known(self, name: str) -> tuple[SeedModel, str | None] | None:
        """The model a name is, exactly - or a known model plus a release date."""
        model_id = self.index.get(normalize_name(name))
        if model_id:
            return self.seeds[model_id], None
        split = self._split_date(name)
        if split:
            model_id = self.index.get(normalize_name(split[0]))
            if model_id:
                return self.seeds[model_id], split[1]
        return None

    def base_name(self, name: str) -> str:
        """The name with a setting, and then a date, removed from its end."""
        name = strip_symbols(name)
        for pattern in self.config.vocabulary.patterns:
            found = pattern.search(name)
            if found:
                name = name[: found.start()].strip()
                break
        split = self._split_date(name)
        return split[0] if split else name

    def match(self, raw_name: str, raw_setting: str | None = None) -> Match:
        name = strip_symbols(raw_name)
        known = self._known(name)
        if known and not raw_setting:
            seed, dated = known
            return Match(row=dated_row(seed, dated) if dated else base_row(seed))

        # A source that gives the setting in its own field ("reasoning_effort").
        if known and raw_setting:
            return self._with_setting(known[0], raw_setting, raw_name, known[1])

        for pattern in self.config.vocabulary.patterns:
            found = pattern.search(name)
            if not found:
                continue
            base = self._known(name[: found.start()].strip())
            if base is None:
                continue
            return self._with_setting(base[0], found.group(1), raw_name, base[1])

        base = self.base_name(name)
        similar = self.similar(base)
        if similar:
            return Match(row=None, reason="similar_to_registry", base_name=base, similar_to=similar)
        return Match(row=None, reason="unmatched", base_name=base)

    def _with_setting(
        self, seed: SeedModel, word: str, raw_name: str, dated: str | None = None
    ) -> Match:
        norm = normalise_word(word)
        base = self.base_name(raw_name)
        if norm in self.config.vocabulary.not_stated:
            row = dated_row(seed, dated) if dated else base_row(seed)
            return Match(row=row, setting_not_stated=True, setting_word=word)
        setting = self.config.vocabulary.words.get(norm)
        if setting is None:
            return Match(
                row=None,
                reason="unknown_setting",
                setting_word=word,
                model_id=seed.id,
                base_name=base,
            )
        extras = self.config.extras.get(seed.id)
        auto_add = (
            extras.auto_add_settings if extras else bool(self.config.settings["auto_add_settings"])
        )
        if not auto_add or (
            extras and extras.allowed_settings and setting not in extras.allowed_settings
        ):
            return Match(
                row=None,
                reason="setting_not_allowed",
                setting_word=word,
                model_id=seed.id,
                base_name=base,
            )
        return Match(row=setting_row(seed, setting, dated), setting_word=word)

    # ── a person's decisions from the Unmatched list ─────────────────────

    def add_decided_alias(self, name: str, model_id: str) -> str | None:
        """A name a person said is `model_id` written differently. Returns a
        warning instead when the name already belongs to another model."""
        key = normalize_name(name)
        if model_id not in self.seeds:
            return f"decision: {name!r} -> {model_id} skipped, {model_id} is not a known model"
        owner = self.index.get(key)
        if owner and owner != model_id:
            return f"decision: {name!r} -> {model_id} skipped, the name already is {owner}"
        self.index[key] = model_id
        return None
