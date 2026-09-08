"""What `contract/bots.yaml` DECLARES. The list, not the loader.

`tests/test_bot_list.py` tests the loader - its refusals, its three answers, its
fingerprint - against files a test writes. This file tests the REAL contract
file's contents, which is a different question with a different reviewer:
`contract/` is the agreement between two people and gets two eyes, and this list
DROPS DOCUMENTS.

Split out 2026-09-08 when the list shipped, so the loader and the list can be
reviewed apart - the loader is code and the list is a curation decision. It also
keeps the branches honest: the loader landed without a list and reported
UNAVAILABLE for every document, which was the correct state and is what these
tests would have failed on.

THE SPLIT UNDER TEST HERE IS RULE 8's. 26 accounts are gated because GitHub
declares `user.type == "Bot"`; 7 are counted because we inferred it from the
login on a population we chose ourselves. Measured effect of the gate: 154
documents dropped, survival 57.1% -> 54.2%. Measured effect if the 7 were
promoted: 3 more documents. See `docs/the-three-dead-gates-2026-09-08.md`.
"""

from __future__ import annotations

from collect.triage.bots import load_bot_list


class TestWhatTheContractDeclares:
    def test_the_real_contract_declares_github_and_only_github(self):
        """SHIPPED 2026-09-08. This test asserted `is None` until then.

        It was written to fail the day the file landed, and the failure was the
        notification - "the gate has stopped reporting UNAVAILABLE for the
        sources it declares, update the survival caveats, then change this test
        to assert what the list contains". This is that change.

        ONLY GITHUB IS DECLARED, AND THE OTHER FOUR ARE ABSENT RATHER THAN
        EMPTY. `accounts: []` for reddit would claim somebody looked; nobody
        has. So reddit stays UNAVAILABLE and the count shrinks platform by
        platform, which is the property the per-source design exists for.
        """
        bots = load_bot_list()
        assert bots is not None
        assert set(bots.by_source) == {"github"}
        assert bots.declares("github")
        assert not bots.declares("reddit")

    def test_the_two_lists_are_the_measured_split(self):
        """26 gated, 7 counted, and the split is rule 8 rather than caution.

        The 26 are `user.type == "Bot"` - GitHub declaring it, so no population
        of ours can hide an error rate. The 7 carry `bot` in the login with
        `user.type == "User"`, found by grepping an export we gathered, which is
        exactly the population-choosing trap rule 8 names.
        """
        gh = load_bot_list().by_source["github"]
        assert len(gh.account_ids) == 26
        assert len(gh.counted_ids) == 7
        assert gh.id_space == "github_user_id"

    def test_the_gated_and_counted_lists_are_disjoint(self):
        """An id in both would be dropped AND counted, so the counted figure
        would describe a population it was not measured against."""
        gh = load_bot_list().by_source["github"]
        assert not (gh.account_ids & gh.counted_ids)

    def test_a_counted_account_is_not_gated_and_a_gated_one_is_not_counted(self):
        """The two answers have opposite consequences, so they are two methods.

        `tenstorrent-github-bot` is the account the judgement is really about -
        33 comments, joint-top voice - and it must NOT drop a document today.
        `github-actions[bot]` must.
        """
        bots = load_bot_list()
        assert bots.counts("github", "123498312")           # tenstorrent, judged
        assert not bots.contains("github", "123498312")
        assert bots.contains("github", "41898282")          # github-actions, attested
        assert not bots.counts("github", "41898282")
