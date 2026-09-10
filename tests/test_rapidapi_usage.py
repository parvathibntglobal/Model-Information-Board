"""RapidAPI (Reddit) quota on the admin page — the reading in, the figure out.

RapidAPI bills the Reddit path as a request quota, so "spent" is requests USED
(limit − remaining). The reading is RapidAPI's own header, persisted by a Reddit
fetch and shown AS OF its timestamp — never live, never recomputed, and never a
fabricated dollar figure. These pin those properties on both sides: the writer
(scripts/fetch_model.py) and the admin reader (judge/app.py).
"""

from __future__ import annotations

import json

import judge.app as app_module
import scripts.fetch_model as fm
from judge.app import _rapidapi_quota


def _write_store(tmp_path, rec):
    """Write the LEGACY single-record shape - deliberately still exercised.

    Files in this shape exist on disk, so the reader must keep handling them.
    `_write_meters` below writes the per-arm shape used since 2026-09-10.
    """
    var = tmp_path / "var"
    var.mkdir(exist_ok=True)
    (var / "rapidapi-quota.json").write_text(json.dumps(rec), encoding="utf-8")


def _write_meters(tmp_path, meters):
    """The per-arm shape: one record per meter, keyed by `read_on`."""
    var = tmp_path / "var"
    var.mkdir(exist_ok=True)
    (var / "rapidapi-quota.json").write_text(
        json.dumps({"meters": meters}), encoding="utf-8")


class TestTheAdminReader:
    def test_no_reading_yet_is_not_instrumented_and_shows_no_number(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        q = _rapidapi_quota("reddit")
        assert q["instrumented"] is False
        assert q["unit"] == "requests"
        assert q["headline"] and q["source_of_record"]

    def test_a_reading_reports_requests_used_as_the_spend(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_meters(tmp_path, {"reddit": {
            "quota_remaining": 950, "quota_limit": 1000,
            "at": "2026-08-28T12:00:00Z", "source_run_id": "mv_x-abc",
            "read_on": "reddit",
        }})
        q = _rapidapi_quota("reddit")
        assert q["instrumented"] is True
        assert q["quota_limit"] == 1000 and q["quota_remaining"] == 950
        assert q["requests_used"] == 50           # limit − remaining is the spend
        assert q["as_of"] == "2026-08-28T12:00:00Z"

    def test_missing_numbers_never_fabricate_a_used_figure(self, monkeypatch, tmp_path):
        # rule 6: an absent reading must not become a definite 0.
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_meters(tmp_path, {"reddit": {
            "quota_remaining": None, "quota_limit": None, "at": "x",
            "read_on": "reddit",
        }})
        q = _rapidapi_quota("reddit")
        assert q["instrumented"] is True
        assert q["requests_used"] is None

    def test_each_arm_reports_its_own_meter_and_never_the_others(
        self, monkeypatch, tmp_path
    ):
        """TWO KEYS, TWO METERS - measured 2026-09-10, and it overturned this test.

        This asserted that "the gateway meters the key and will never split it
        by endpoint, so the panel cannot show an X-only figure". The premise
        was that one key served both arms. It does not: the two keys are
        separate subscriptions with limits of 1,000,000 and 100,000, each
        returning 403 on the other provider.

        So the panel CAN show an X-only figure, and must - the shared-slot
        version displayed whichever arm read last under BOTH headings.
        """
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_meters(tmp_path, {
            "reddit": {"quota_remaining": 996207, "quota_limit": 1000000,
                       "at": "2026-09-10T05:21:38Z", "read_on": "reddit"},
            "x": {"quota_remaining": 99868, "quota_limit": 100000,
                  "at": "2026-09-10T05:22:10Z", "read_on": "x"},
        })
        reddit, x = _rapidapi_quota("reddit"), _rapidapi_quota("x")
        assert reddit["read_on"] == "reddit" and reddit["quota_limit"] == 1000000
        assert x["read_on"] == "x" and x["quota_limit"] == 100000
        # Each arm's own spend, not one number rendered twice.
        assert reddit["requests_used"] == 3793
        assert x["requests_used"] == 132

    def test_an_arm_with_no_reading_says_so_instead_of_borrowing_the_other(
        self, monkeypatch, tmp_path
    ):
        # Rule 4 at the panel. Reddit has a reading, X has none. Showing
        # Reddit's under the X heading is what the single-slot store did.
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_meters(tmp_path, {"reddit": {
            "quota_remaining": 996207, "quota_limit": 1000000,
            "at": "2026-09-10T05:21:38Z", "read_on": "reddit",
        }})
        assert _rapidapi_quota("reddit")["instrumented"] is True
        x = _rapidapi_quota("x")
        assert x["instrumented"] is False
        assert "quota_remaining" not in x, "an unread arm must publish no figure"

    def test_a_record_written_before_the_field_reports_unrecorded_not_reddit(
        self, monkeypatch, tmp_path
    ):
        # rule 6: a missing value stays missing. Defaulting to "reddit" would
        # assert a path nobody recorded, which is the exact bug being fixed.
        #
        # AND IT MUST NOT VANISH EITHER. The store is keyed by arm now, so a
        # record with no `read_on` belongs to no arm - but it is still a real
        # header reading, and reporting the arm as merely "not read" would
        # turn evidence we hold into an absence. Both facts are published.
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_store(tmp_path, {
            "quota_remaining": 950, "quota_limit": 1000, "at": "2026-08-28T12:00:00Z",
        })
        for arm in ("reddit", "x"):
            q = _rapidapi_quota(arm)
            assert q["instrumented"] is False, arm
            orphan = q["unattributed_reading"]
            assert orphan["quota_remaining"] == 950
            assert orphan["as_of"] == "2026-08-28T12:00:00Z"
            assert orphan["why_not_shown"]

    def test_a_legacy_record_naming_its_arm_is_filed_under_that_arm(
        self, monkeypatch, tmp_path
    ):
        # The old shape carrying `read_on` IS attributable, so it is shown -
        # on its own arm, and on no other.
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_store(tmp_path, {
            "quota_remaining": 99870, "quota_limit": None,
            "at": "2026-09-09T00:00:00Z", "read_on": "x",
        })
        assert _rapidapi_quota("x")["quota_remaining"] == 99870
        assert _rapidapi_quota("reddit")["instrumented"] is False

    def test_a_corrupt_store_reads_as_not_instrumented_not_a_crash(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        (tmp_path / "var").mkdir(exist_ok=True)
        (tmp_path / "var" / "rapidapi-quota.json").write_text("{not json", encoding="utf-8")
        assert _rapidapi_quota("reddit")["instrumented"] is False


class TestTheFetchWriter:
    """`_write_rapidapi_quota` now DELEGATES to `collect.usage`.

    So the seam moved: patching `fm.ROOT` no longer redirects the write,
    because the path comes from `collect.usage.QUOTA_PATH`. That is the point
    of the change — the adapters record every metered response through the
    same function, and a second path constant in the script would be a second
    place for the file to live.
    """

    @staticmethod
    def _redirect(monkeypatch, tmp_path):
        import collect.usage as usage

        target = tmp_path / "var" / "rapidapi-quota.json"
        monkeypatch.setattr(usage, "QUOTA_PATH", target)
        return target

    def test_it_persists_the_raw_reading(self, monkeypatch, tmp_path):
        self._redirect(monkeypatch, tmp_path)
        fm._write_rapidapi_quota(950, 1000, "mv_x-abc", read_on="reddit")
        store = json.loads(
            (tmp_path / "var" / "rapidapi-quota.json").read_text(encoding="utf-8"))
        rec = store["meters"]["reddit"]
        assert rec["quota_remaining"] == 950 and rec["quota_limit"] == 1000
        assert rec["source_run_id"] == "mv_x-abc" and rec["at"]
        assert rec["read_on"] == "reddit"

    def test_the_x_arm_records_itself_not_reddit(self, monkeypatch, tmp_path):
        # The X harvest spends the same quota, and until 2026-09-09 it wrote no
        # reading at all - so an X-only fetch left the panel showing an older
        # Reddit number as though nothing had been spent.
        self._redirect(monkeypatch, tmp_path)
        fm._write_rapidapi_quota(900, 1000, "mv_x-def", read_on="x")
        store = json.loads(
            (tmp_path / "var" / "rapidapi-quota.json").read_text(encoding="utf-8"))
        rec = store["meters"]["x"]
        assert rec["read_on"] == "x" and rec["quota_remaining"] == 900
        # And it landed on the X arm ONLY. It is not Reddit's meter.
        assert "reddit" not in store["meters"]

    def test_a_blank_reading_does_not_clobber_a_good_one(self, monkeypatch, tmp_path):
        # Nothing read this fetch: leave the last good reading in place.
        self._redirect(monkeypatch, tmp_path)
        fm._write_rapidapi_quota(None, None, "mv_x", read_on="reddit")
        assert not (tmp_path / "var" / "rapidapi-quota.json").exists()
