"""Capability discovery: the extractor proposes a new key, code attributes and
stores it, an admin rules on it.

These cover the deterministic half — attribution (which document a proposal came
from) and idempotent storage. The LLM proposing is exercised through the schema;
the ruling is the admin endpoints (test_capability_candidate_admin.py).
"""

from __future__ import annotations

from judge.extract.runner import ProposedCapability, _attribute
from judge.extract.verify import OffsetMapping
from judge.store.capability_candidates import candidate_id, store_proposals

FLAT = "[root by a] the model overthinks every simple prompt and burns tokens badly"
MAP = [
    OffsetMapping(
        flat_start=0, flat_end=len(FLAT), document_id="doc1", raw_start=0, raw_end=len(FLAT)
    ),
]


class TestAttribution:
    def test_a_located_quote_resolves_to_its_document(self):
        assert _attribute("overthinks every simple prompt", FLAT, MAP) == "doc1"

    def test_an_absent_quote_resolves_to_nothing(self):
        assert _attribute("this text is nowhere in the thread", FLAT, MAP) is None

    def test_a_quote_crossing_two_documents_is_not_attributed(self):
        two = [
            OffsetMapping(flat_start=0, flat_end=20, document_id="a", raw_start=0, raw_end=20),
            OffsetMapping(
                flat_start=20, flat_end=len(FLAT), document_id="b",
                raw_start=0, raw_end=len(FLAT) - 20,
            ),
        ]
        # a quote spanning the boundary touches both -> unattributable, never guessed
        assert _attribute(FLAT[10:30], FLAT, two) is None

    def test_an_empty_quote_is_not_attributed(self):
        assert _attribute("", FLAT, MAP) is None


class _Cur:
    def __init__(self):
        self.rows = []

    def execute(self, sql, params):
        self.rows.append(params)
        self.rowcount = 1  # every insert lands (no conflict in this fake)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Conn:
    def __init__(self):
        self.cur = _Cur()

    def cursor(self):
        return self.cur


class TestStore:
    def test_only_attributed_proposals_are_stored_and_the_rest_are_counted(self):
        proposals = [
            ProposedCapability("output.verbosity", "over-writes", "burns tokens", True, "doc1"),
            ProposedCapability("reasoning.overthink", "over-reasons", "overthinks", True, "doc2"),
            ProposedCapability("x.made_up", "not in the text", "nowhere", False, None),  # skip
        ]
        conn = _Conn()
        out = store_proposals(conn, proposals, proposer_model="gemini", prompt_label="t")
        assert out == {"proposed": 3, "stored": 2, "unattributed": 1}
        assert len(conn.cur.rows) == 2  # the None-document one was not inserted

    def test_the_id_is_a_stable_content_hash_of_the_natural_key(self):
        a = candidate_id(document_id="d", proposed_key="k", prompt_label="p", pipeline_version="v")
        b = candidate_id(document_id="d", proposed_key="k", prompt_label="p", pipeline_version="v")
        c = candidate_id(document_id="d", proposed_key="k2", prompt_label="p", pipeline_version="v")
        assert a == b and a != c and a.startswith("cc_")
