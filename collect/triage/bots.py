"""E4 — the bot list, loaded from `contract/`. The detector, not the list.

WHAT THIS IS AND IS NOT
-----------------------
`collect/triage/gates.py:known_bot` has reported UNAVAILABLE for the entire
corpus since it was written, for one reason: rule 5 puts a filter rule in
`contract/` and there was no bot list there. This module is the loader that
makes the gate runnable **the day the list lands** - and it reports UNAVAILABLE
until then, per source, rather than pretending.

The list itself is `contract/bots.yaml`, which does not exist yet and is
**proposed rather than written**: `contract/` is the agreement between two
people and gets two eyes. The curated accounts and the evidence for each are in
`docs/proposals/for-engineer-2-the-bot-list.md`.

So: absent file, absent source, and declared-and-empty are three different
answers, and the whole design is keeping them apart.

    no file at all              every source UNAVAILABLE. Nothing is curated.
    file, source not declared   THAT SOURCE is UNAVAILABLE. A curation gap,
                                fixable once, and the count SHRINKS as each
                                platform is read - which is what makes it
                                `UNAVAILABLE` and not `NOT_APPLICABLE`.
    file, `accounts: []`        False. Somebody looked and found none. A real
                                measurement, and not the same statement as the
                                line above.

KEYED ON THE PLATFORM'S STABLE ACCOUNT ID, NOT ON THE LOGIN
------------------------------------------------------------
A login is mutable on every platform that has renames, so a list keyed on one
**silently stops matching** the day an account is renamed - and silence is the
failure mode this gate exists to prevent. `author.external_id` is what
`document.author_id` resolves through, so the list is keyed on the same thing
the voice count is.

⚠  THE ID SPACE IS PER PLATFORM AND ONE OF THEM IS A USERNAME. Each source
   block declares its `id_space`, and the loader refuses a block that does not,
   because getting this wrong is not visible from a row:

       github        `user.id`, numeric        41898282
       reddit        `t2_` fullname            t2_2ii4xgakc7
       huggingface   `author._id`              63142785289cf15634cccc72
       hackernews    THE USERNAME              github-actions
                     - Hacker News has no rename feature, so the username IS
                       the permanent identifier and there is nothing more
                       stable to prefer. Recorded as a declared id_space rather
                       than left to look like a mistake somebody should fix.
       x             `rest_id`, numeric        171962385

CURATED ACCOUNTS, NEVER A REGEX OVER LOGINS
--------------------------------------------
Measured over the 2,016-comment GitHub export: **7 accounts carry `bot` in the
login with no `[bot]` suffix**, and one of them is
`FacultativeObligatoryBotContract` - almost certainly a person with a joke
name. A regex would filter them, and would filter `releasebot` the helpful
maintainer. `github.py:is_bot` already refuses the string heuristic for this
reason, and records that the `[bot]`-suffix agreement it was measured against
had a denominator of **two accounts**.

So the loader takes ids and nothing else. There is no pattern field, on
purpose, and adding one would need the argument above answered rather than
repeated.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

log = logging.getLogger(__name__)

#: `contract/bots.yaml`. Absent today - see the module docstring.
BOTS_FILENAME = "bots.yaml"

#: Every id space a source block may declare. Closed on purpose: a typo in an
#: id space is a list that matches nothing, and a list that matches nothing is
#: indistinguishable from a platform with no bots.
ID_SPACES: tuple[str, ...] = (
    "github_user_id",
    "reddit_fullname",
    "huggingface_author_id",
    "hackernews_username",
    "x_rest_id",
)


class BotListError(RuntimeError):
    """The bot list is present and cannot be read as one. Never a silent skip."""


@dataclass(frozen=True)
class BotSource:
    """One platform's curated accounts, and who read them."""

    source: str
    id_space: str
    #: GATED. A document authored by one of these is DROPPED.
    account_ids: frozenset[str]
    #: COUNTED AND NEVER DROPPED. Rule 8's "weight, flag or recorded field":
    #: an account whose bot-ness is OUR judgement rather than the platform's
    #: goes here, so its effect is visible before it is acted on.
    #:
    #: THE TWO LISTS ARE DISJOINT AND `_source_of` REFUSES AN OVERLAP. An id in
    #: both would gate and be counted, and the count would then describe
    #: something other than the population it is reported against.
    counted_ids: frozenset[str] = frozenset()
    reviewed_on: date | None = None
    reviewed_by: str | None = None
    #: id -> the login it had when it was reviewed. FOR A HUMAN READING THE
    #: FILE, and never matched on: the whole point of keying on the id is that
    #: the login can change. Kept because a list of bare numbers is a list
    #: nobody can review, and re-reviewing it needs to be possible.
    logins: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BotList:
    """Every platform's list, and the identity of the set as a whole.

    `fingerprint` is here for the reason `SurfacePopulation.fingerprint` is:
    **a verdict is only re-runnable beside the population that produced it.**
    This population changes when somebody edits a YAML file, and a document
    that was `dropped` last week and `kept` today with no code change is
    otherwise unexplainable.
    """

    by_source: Mapping[str, BotSource]

    @property
    def fingerprint(self) -> str:
        """Stable digest of every (kind, source, id) triple. Sorted, so order
        cannot change it.

        BOTH LISTS, AND THE KIND IS IN THE DIGEST. A counted account does not
        change a verdict, but it does change the RESULT - `TriageResult.flags`
        carries it - so a run whose counted list moved is not re-runnable
        against one whose did not. Including the kind means PROMOTING an id
        from counted to gated changes the digest, which is precisely the change
        somebody has to be able to see.
        """
        joined = "\n".join(
            f"{kind}:{source}:{account}"
            for source, block in sorted(self.by_source.items())
            for kind, ids in (("gate", block.account_ids), ("count", block.counted_ids))
            for account in sorted(ids)
        )
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]

    @property
    def account_count(self) -> int:
        """GATED accounts only. The number that changes a verdict."""
        return sum(len(block.account_ids) for block in self.by_source.values())

    @property
    def counted_count(self) -> int:
        """COUNTED accounts. Reported apart from `account_count` on purpose:
        one number is what the gate drops and the other is what it would drop
        if the judgement were promoted, and a single total answers neither."""
        return sum(len(block.counted_ids) for block in self.by_source.values())

    def declares(self, source: str) -> bool:
        """Has anybody curated a list for this platform?

        The question `known_bot` asks before it answers. A source nobody has
        read is UNAVAILABLE; a source somebody read and found nothing on is
        `False`. Collapsing those is rule 6 on our own filter.
        """
        return source in self.by_source

    def counts(self, source: str, account_id: str) -> bool:
        """Is this account on the COUNTED list - observed, never dropped?

        Separate method from `contains` rather than a flag on it, because the
        two answers have opposite consequences and a caller that confused them
        would either drop a document on our own judgement or stop counting the
        judgement's effect. Neither is recoverable from the row.
        """
        block = self.by_source.get(source)
        return block is not None and account_id in block.counted_ids

    def contains(self, source: str, account_id: str) -> bool:
        block = self.by_source.get(source)
        if block is None:
            # Callers must ask `declares` first. Returning False here would be
            # the collapse this class exists to prevent, so it is logged loudly
            # rather than answered quietly.
            log.error(
                "bot list: contains(%r, ...) on a source the list does not "
                "declare. That is UNAVAILABLE, not False - ask declares() "
                "first.", source,
            )
            return False
        return account_id in block.account_ids

    def basis(self) -> str:
        """One line stating what this list is, for a log or a report."""
        if not self.by_source:
            return "bot list: declared for no source; every known-bot verdict is UNAVAILABLE"
        parts = ", ".join(
            f"{name} {len(block.account_ids)} gated + {len(block.counted_ids)} counted"
            for name, block in sorted(self.by_source.items())
        )
        return (
            f"bot list: {self.account_count} gated and {self.counted_count} "
            f"counted account(s) over {len(self.by_source)} source(s) "
            f"({parts}), fingerprint {self.fingerprint}"
        )


def load_bot_list(path=None) -> BotList | None:
    """`contract/bots.yaml` as a `BotList`, or **None where the file is absent**.

    None IS THE LOAD-BEARING RETURN VALUE. `known_bot` turns it into
    UNAVAILABLE for every document, which is the honest state today: nothing is
    curated, so the gate cannot run, and every survival figure computed while
    that is true is an upper bound.

    An empty `BotList` would be a different and false statement - *"the list
    exists and declares no bots"* - so the absent file is not normalised into
    one. Same distinction `known_bot` already draws between `bots is None` and
    `bots == frozenset()`, one layer up.

    RAISES on a file that exists and cannot be read as a list. A malformed bot
    list must not degrade to "no bots": that would turn a typo into a filter
    that silently passes every automated account, which is the shape
    `specificity._contract` refuses for the same reason.
    """
    import yaml

    from collect.config import CONTRACT_DIR

    target = path if path is not None else CONTRACT_DIR / BOTS_FILENAME
    if not target.exists():
        log.info(
            "bot list: %s does not exist, so the known-bot gate reports "
            "UNAVAILABLE for every document. Proposed in "
            "docs/proposals/for-engineer-2-the-bot-list.md.", target,
        )
        return None

    raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise BotListError(f"{target} is not a YAML mapping")
    sources = raw.get("sources")
    if not isinstance(sources, dict):
        raise BotListError(
            f"{target} has no `sources` mapping. An empty list is written as "
            "`sources: {}`, which declares nothing for any platform; a source "
            "with no bots is written as that source with `accounts: []`, which "
            "declares that somebody looked."
        )

    blocks: dict[str, BotSource] = {}
    for name, block in sources.items():
        blocks[str(name)] = _source_of(str(name), block, target)
    return BotList(by_source=blocks)


def _ids_of(entries: list, *, name: str, key: str, target, logins: dict) -> set[str]:
    """Account ids out of one list, collecting logins for a human reader.

    Shared by `accounts` and `counted` so the two lists cannot drift in what
    they accept - a `counted` list that quietly took a login where `accounts`
    demands an id would be a judgement nobody could match on.
    """
    ids: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            # A bare id is accepted and its login is then unknown, which is
            # worse to review but not wrong to match on.
            ids.add(entry)
            continue
        if not isinstance(entry, dict) or not entry.get("external_id"):
            raise BotListError(
                f"{target}: source {name!r} has a {key} entry with no "
                f"`external_id`: {entry!r}. The list is keyed on the platform's "
                "stable account id; a login alone cannot be matched on, because "
                "a rename would silently stop it matching."
            )
        account_id = str(entry["external_id"])
        ids.add(account_id)
        if entry.get("login"):
            logins[account_id] = str(entry["login"])
    return ids


def _source_of(name: str, block: Any, target) -> BotSource:
    if not isinstance(block, dict):
        raise BotListError(f"{target}: source {name!r} is not a mapping")

    id_space = block.get("id_space")
    if id_space not in ID_SPACES:
        # REFUSED RATHER THAN DEFAULTED. An id space nobody stated is a list
        # keyed on an unknown thing, which matches nothing and looks like a
        # platform with no bots.
        raise BotListError(
            f"{target}: source {name!r} declares id_space={id_space!r}, which is "
            f"not one of {ID_SPACES}. The id space is what the account ids ARE - "
            "a numeric account id, a `t2_` fullname, or (on Hacker News, which "
            "has no rename feature) the username. It cannot be guessed from the "
            "values."
        )

    accounts = block.get("accounts")
    if accounts is None or not isinstance(accounts, list):
        raise BotListError(
            f"{target}: source {name!r} has no `accounts` list. Write "
            "`accounts: []` to declare that somebody looked and found none - "
            "that is a measurement, and omitting the key is not."
        )

    logins: dict[str, str] = {}
    ids = _ids_of(accounts, name=name, key="accounts", target=target, logins=logins)

    # ── THE COUNTED LIST ────────────────────────────────────────────────
    #
    # OPTIONAL, AND ABSENT IS NOT EMPTY-BUT-DIFFERENT HERE. Unlike `accounts`,
    # omitting `counted` is fine: it says nobody has recorded a judgement call
    # for this platform, and no verdict depends on it either way. `accounts`
    # cannot be omitted because its absence would be indistinguishable from a
    # platform somebody read and found no bots on, which is a measurement.
    counted_raw = block.get("counted")
    if counted_raw is None:
        counted: set[str] = set()
    elif isinstance(counted_raw, list):
        counted = _ids_of(
            counted_raw, name=name, key="counted", target=target, logins=logins
        )
    else:
        raise BotListError(
            f"{target}: source {name!r} has a `counted` that is not a list: "
            f"{counted_raw!r}. Omit the key entirely to declare no judgement "
            "calls; `counted: []` says the same thing and is also fine."
        )

    # DISJOINT, REFUSED RATHER THAN RESOLVED. An id in both lists would be
    # dropped AND counted, so the counted figure would stop being "what this
    # judgement would cost if promoted" and become an unknown mixture.
    both = ids & counted
    if both:
        shown = ", ".join(sorted(both)[:5])
        raise BotListError(
            f"{target}: source {name!r} lists {len(both)} account(s) under BOTH "
            f"`accounts` and `counted`: {shown}. `accounts` drops the document "
            "and `counted` only records it, so an id in both makes the counted "
            "figure describe a population it was not measured against. Pick "
            "one - promoting an account means MOVING it, not adding it."
        )

    reviewed_on = block.get("reviewed_on")
    return BotSource(
        source=name,
        id_space=str(id_space),
        account_ids=frozenset(ids),
        counted_ids=frozenset(counted),
        reviewed_on=reviewed_on if isinstance(reviewed_on, date) else None,
        reviewed_by=block.get("reviewed_by"),
        logins=logins,
    )
