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
    var = tmp_path / "var"
    var.mkdir(exist_ok=True)
    (var / "rapidapi-quota.json").write_text(json.dumps(rec), encoding="utf-8")


class TestTheAdminReader:
    def test_no_reading_yet_is_not_instrumented_and_shows_no_number(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        q = _rapidapi_quota()
        assert q["instrumented"] is False
        assert q["unit"] == "requests"
        assert q["headline"] and q["source_of_record"]

    def test_a_reading_reports_requests_used_as_the_spend(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_store(tmp_path, {
            "quota_remaining": 950, "quota_limit": 1000,
            "at": "2026-08-28T12:00:00Z", "source_run_id": "mv_x-abc",
        })
        q = _rapidapi_quota()
        assert q["instrumented"] is True
        assert q["quota_limit"] == 1000 and q["quota_remaining"] == 950
        assert q["requests_used"] == 50           # limit − remaining is the spend
        assert q["as_of"] == "2026-08-28T12:00:00Z"

    def test_missing_numbers_never_fabricate_a_used_figure(self, monkeypatch, tmp_path):
        # rule 6: an absent reading must not become a definite 0.
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_store(tmp_path, {"quota_remaining": None, "quota_limit": None, "at": "x"})
        q = _rapidapi_quota()
        assert q["instrumented"] is True
        assert q["requests_used"] is None

    def test_it_names_the_path_that_took_the_reading(self, monkeypatch, tmp_path):
        # ONE KEY, TWO CONSUMERS. The gateway meters the key and will never
        # split it by endpoint, so the panel cannot show an X-only figure. What
        # it can say is WHOSE fetch read the shared one - without that the X tab
        # showed a Reddit reading under an X heading.
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_store(tmp_path, {
            "quota_remaining": 950, "quota_limit": 1000,
            "at": "2026-08-28T12:00:00Z", "source_run_id": "mv_x-abc",
            "read_on": "x",
        })
        assert _rapidapi_quota()["read_on"] == "x"

    def test_a_record_written_before_the_field_reports_unrecorded_not_reddit(
        self, monkeypatch, tmp_path
    ):
        # rule 6: a missing value stays missing. Defaulting to "reddit" would
        # assert a path nobody recorded, which is the exact bug being fixed.
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        _write_store(tmp_path, {
            "quota_remaining": 950, "quota_limit": 1000, "at": "2026-08-28T12:00:00Z",
        })
        assert _rapidapi_quota()["read_on"] is None

    def test_a_corrupt_store_reads_as_not_instrumented_not_a_crash(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_REPO_ROOT", tmp_path)
        (tmp_path / "var").mkdir(exist_ok=True)
        (tmp_path / "var" / "rapidapi-quota.json").write_text("{not json", encoding="utf-8")
        assert _rapidapi_quota()["instrumented"] is False


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
        rec = json.loads((tmp_path / "var" / "rapidapi-quota.json").read_text(encoding="utf-8"))
        assert rec["quota_remaining"] == 950 and rec["quota_limit"] == 1000
        assert rec["source_run_id"] == "mv_x-abc" and rec["at"]
        assert rec["read_on"] == "reddit"

    def test_the_x_arm_records_itself_not_reddit(self, monkeypatch, tmp_path):
        # The X harvest spends the same quota, and until 2026-09-09 it wrote no
        # reading at all - so an X-only fetch left the panel showing an older
        # Reddit number as though nothing had been spent.
        self._redirect(monkeypatch, tmp_path)
        fm._write_rapidapi_quota(900, 1000, "mv_x-def", read_on="x")
        rec = json.loads((tmp_path / "var" / "rapidapi-quota.json").read_text(encoding="utf-8"))
        assert rec["read_on"] == "x" and rec["quota_remaining"] == 900

    def test_a_blank_reading_does_not_clobber_a_good_one(self, monkeypatch, tmp_path):
        # Nothing read this fetch: leave the last good reading in place.
        self._redirect(monkeypatch, tmp_path)
        fm._write_rapidapi_quota(None, None, "mv_x", read_on="reddit")
        assert not (tmp_path / "var" / "rapidapi-quota.json").exists()
