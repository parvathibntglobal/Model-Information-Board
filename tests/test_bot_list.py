"""The bot list loader, and the three answers it must keep apart.

`collect/triage/bots.py` exists so `known_bot` can stop reporting UNAVAILABLE
for the whole corpus the day `contract/bots.yaml` lands. The value of the
loader is entirely in its refusals: a malformed list that degraded to "no bots"
would be a filter that silently passes every automated account, and an absent
file normalised to an empty list would claim somebody had looked.
"""

from __future__ import annotations

from datetime import date

import pytest
import yaml

from collect.triage.bots import (
    BOTS_FILENAME,
    ID_SPACES,
    BotList,
    BotListError,
    BotSource,
    load_bot_list,
)


def _write(tmp_path, document) -> object:
    path = tmp_path / BOTS_FILENAME
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


# ── the three answers ────────────────────────────────────────────────────


class TestAbsentIsNotEmpty:
    def test_no_file_returns_none_and_not_an_empty_list(self, tmp_path):
        """None is the load-bearing return value.

        An empty `BotList` would assert *"the list exists and declares no
        bots"*, which is a claim nobody has made. `known_bot` turns None into
        UNAVAILABLE for every document, and every survival figure computed
        while that is true is an upper bound.
        """
        assert load_bot_list(tmp_path / "nothing.yaml") is None

    def test_an_id_in_both_lists_is_refused(self, tmp_path):
        """Promotion is a MOVE. Adding rather than moving is refused, loudly."""
        path = _write(tmp_path, {
            "version": "1.0",
            "sources": {"github": {
                "id_space": "github_user_id",
                "accounts": ["1", "2"],
                "counted": ["2", "3"],
            }},
        })
        with pytest.raises(BotListError, match="BOTH"):
            load_bot_list(path)

    def test_an_absent_counted_key_is_fine(self, tmp_path):
        """Omitting `counted` says nobody recorded a judgement call, and no
        verdict depends on it either way."""
        path = _write(tmp_path, {
            "version": "1.0",
            "sources": {"github": {
                "id_space": "github_user_id", "accounts": ["1"],
            }},
        })
        assert load_bot_list(path).by_source["github"].counted_ids == frozenset()

    def test_an_absent_accounts_key_is_still_refused(self, tmp_path):
        """The asymmetry with `counted` is deliberate.

        Omitting `accounts` is indistinguishable from a platform somebody read
        and found no bots on - and that is a measurement, so it has to be
        written rather than inferred from a missing key.
        """
        path = _write(tmp_path, {
            "version": "1.0",
            "sources": {"github": {
                "id_space": "github_user_id", "counted": ["1"],
            }},
        })
        with pytest.raises(BotListError, match="accounts"):
            load_bot_list(path)

    def test_promoting_an_id_changes_the_fingerprint(self, tmp_path):
        """A verdict that moved because this file moved must be traceable.

        Same two ids either way - only which list they sit in differs - so the
        digest must differ, or a run whose judgement was promoted looks
        identical to one whose was not.
        """
        def _fingerprint(accounts, counted, name):
            path = tmp_path / name
            import yaml as _yaml
            path.write_text(_yaml.safe_dump({
                "version": "1.0",
                "sources": {"github": {
                    "id_space": "github_user_id",
                    "accounts": accounts,
                    "counted": counted,
                }},
            }), encoding="utf-8")
            return load_bot_list(path).fingerprint

        before = _fingerprint(["1"], ["2"], "before.yaml")
        after = _fingerprint(["1", "2"], [], "after.yaml")
        assert before != after

    def test_a_declared_source_with_no_accounts_is_a_measurement(self, tmp_path):
        path = _write(
            tmp_path,
            {
                "version": "1.0",
                "sources": {
                    "hackernews": {
                        "id_space": "hackernews_username",
                        "accounts": [],
                    }
                },
            },
        )
        bots = load_bot_list(path)
        assert bots is not None
        assert bots.declares("hackernews") is True
        assert bots.account_count == 0
        # Somebody looked and found none. Not the same statement as an absent
        # source, which `declares` answers False for.
        assert bots.declares("github") is False


# ── the refusals ─────────────────────────────────────────────────────────


class TestItRefusesRatherThanDegrading:
    def test_a_missing_id_space_is_refused(self, tmp_path):
        """An id space nobody stated is a list keyed on an unknown thing.

        It would match nothing, and matching nothing is indistinguishable from
        a platform with no bots.
        """
        path = _write(
            tmp_path,
            {"sources": {"github": {"accounts": [{"external_id": "1"}]}}},
        )
        with pytest.raises(BotListError, match="id_space"):
            load_bot_list(path)

    def test_an_unknown_id_space_is_refused(self, tmp_path):
        path = _write(
            tmp_path,
            {
                "sources": {
                    "github": {"id_space": "github_login", "accounts": []}
                }
            },
        )
        with pytest.raises(BotListError, match="not one of"):
            load_bot_list(path)

    def test_a_missing_accounts_key_is_refused_rather_than_read_as_empty(
        self, tmp_path
    ):
        """Omitting the key is not a measurement; `accounts: []` is."""
        path = _write(
            tmp_path,
            {"sources": {"github": {"id_space": "github_user_id"}}},
        )
        with pytest.raises(BotListError, match="accounts"):
            load_bot_list(path)

    def test_an_entry_with_only_a_login_is_refused(self, tmp_path):
        """The whole point of the key. A login cannot be matched on."""
        path = _write(
            tmp_path,
            {
                "sources": {
                    "github": {
                        "id_space": "github_user_id",
                        "accounts": [{"login": "github-actions[bot]"}],
                    }
                }
            },
        )
        with pytest.raises(BotListError, match="external_id"):
            load_bot_list(path)

    def test_a_file_that_is_not_a_mapping_is_refused(self, tmp_path):
        path = tmp_path / BOTS_FILENAME
        path.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(BotListError):
            load_bot_list(path)

    def test_a_file_with_no_sources_key_is_refused(self, tmp_path):
        path = _write(tmp_path, {"version": "1.0"})
        with pytest.raises(BotListError, match="sources"):
            load_bot_list(path)


# ── what it loads ────────────────────────────────────────────────────────


class TestWhatItLoads:
    def _list(self, tmp_path) -> BotList:
        path = _write(
            tmp_path,
            {
                "version": "1.0",
                "sources": {
                    "github": {
                        "id_space": "github_user_id",
                        "reviewed_on": date(2026, 9, 7),
                        "reviewed_by": "anooj",
                        "accounts": [
                            {"external_id": "41898282", "login": "github-actions[bot]"},
                            {"external_id": "99", "login": "tenstorrent-github-bot"},
                        ],
                    },
                    "hackernews": {
                        "id_space": "hackernews_username",
                        "accounts": ["some-hn-bot"],
                    },
                },
            },
        )
        loaded = load_bot_list(path)
        assert loaded is not None
        return loaded

    def test_ids_match_and_logins_are_kept_for_review_only(self, tmp_path):
        bots = self._list(tmp_path)
        assert bots.contains("github", "41898282") is True
        assert bots.contains("github", "not-listed") is False
        # The login is carried so a human can review the file, and is not what
        # anything matches on.
        assert bots.by_source["github"].logins["99"] == "tenstorrent-github-bot"

    def test_a_bare_id_is_accepted_with_no_login(self, tmp_path):
        """Worse to review, not wrong to match on."""
        bots = self._list(tmp_path)
        assert bots.contains("hackernews", "some-hn-bot") is True
        assert bots.by_source["hackernews"].logins == {}

    def test_hackernews_declares_the_username_as_its_id_space(self, tmp_path):
        """The one platform where the id IS a username, because HN has no
        rename feature. Declared so it cannot look like a mistake."""
        assert self._list(tmp_path).by_source["hackernews"].id_space == (
            "hackernews_username"
        )
        assert "hackernews_username" in ID_SPACES

    def test_the_fingerprint_is_stable_and_order_independent(self, tmp_path):
        """A verdict is only re-runnable beside the population that produced it.

        This population changes when somebody edits a YAML file, so a document
        dropped last week and kept today with no code change is otherwise
        unexplainable — `SurfacePopulation.fingerprint` exists for the same
        reason.
        """
        one = BotList(
            by_source={
                "github": BotSource(
                    source="github",
                    id_space="github_user_id",
                    account_ids=frozenset({"a", "b"}),
                )
            }
        )
        other = BotList(
            by_source={
                "github": BotSource(
                    source="github",
                    id_space="github_user_id",
                    account_ids=frozenset({"b", "a"}),
                )
            }
        )
        assert one.fingerprint == other.fingerprint
        assert one.fingerprint != BotList(by_source={}).fingerprint

    def test_the_basis_line_names_the_gap_when_nothing_is_declared(self):
        assert "UNAVAILABLE" in BotList(by_source={}).basis()

    def test_contains_on_an_undeclared_source_does_not_answer_quietly(
        self, tmp_path, caplog
    ):
        """Callers must ask `declares` first, and a caller that forgot is loud.

        Returning False here is the collapse the class exists to prevent, so it
        is logged at ERROR rather than answered silently.
        """
        bots = self._list(tmp_path)
        with caplog.at_level("ERROR"):
            assert bots.contains("devto", "1") is False
        assert "UNAVAILABLE, not False" in caplog.text
