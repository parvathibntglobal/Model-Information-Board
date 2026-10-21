"""#303: the thread_context export writes real store refs, never a sentinel.

`scripts/export_thread_contexts.py` wrote `flattened_text_ref =
'flattened/inline-see-json'` into its generated `load.sql`. `parse_ref` refuses
that string, so a reader crashed with `ValueError` where MISSING should have
answered, and one such row reached the shared database. Every ref the export
emits is now a content address in the right namespace, or it refuses.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from collect.ids import content_hash
from collect.rawstore import FLATTENED, RAW, build_ref, parse_ref

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import export_thread_contexts as export  # noqa: E402

#: `<column> ... VALUES (...)` is one statement per row; the refs are read back
#: by column position rather than by a regex over the whole file.
_STATEMENT = re.compile(r"INSERT INTO (\w+) \(([^)]*)\)\nVALUES \((.*?)\)\nON CONFLICT",
                        re.S)


def _values(sql: str):
    """(table, {column: literal}) per statement. Splits on the literals the
    exporter writes - quoted strings, `'{...}'` arrays, NULL, numbers."""
    for table, cols, vals in _STATEMENT.findall(sql):
        literals = re.findall(r"'(?:[^']|'')*'|NULL|true|false|-?\d+(?:\.\d+)?", vals)
        names = [c.strip() for c in cols.split(",")]
        assert len(literals) == len(names), (table, names)
        yield table, dict(zip(names, literals, strict=True))


@pytest.fixture
def exported(tmp_path, monkeypatch):
    # No registry read (that would open DATABASE_URL), no blog payloads (cwd has
    # no raw_store/), the committed Reddit fixture only.
    monkeypatch.setattr(export, "version_aliases", lambda conn=None: ())
    monkeypatch.setattr(export, "REDDIT_PAYLOAD", ROOT / export.REDDIT_PAYLOAD)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out"
    assert export.main(out, limit=1) == 0
    return out


def test_no_ref_in_load_sql_is_a_non_store_ref(exported):
    sql = (exported / "load.sql").read_text(encoding="utf-8")
    assert "inline-see-json" not in sql
    seen = {"document": 0, "thread_context": 0}
    for table, row in _values(sql):
        column = {"document": "text_ref", "thread_context": "flattened_text_ref"}.get(table)
        if column is None:
            continue
        ref = row[column].strip("'")
        namespace, _hash = parse_ref(ref)       # raises on a sentinel
        assert namespace is (RAW if table == "document" else FLATTENED), ref
        seen[table] += 1
    assert seen["document"] and seen["thread_context"], seen


def test_the_flattened_ref_addresses_the_inline_text(exported):
    sql = (exported / "load.sql").read_text(encoding="utf-8")
    (thread,) = (exported / "threads").glob("*.json")
    text = json.loads(thread.read_text(encoding="utf-8"))["flattened_text"]
    (row,) = [r for t, r in _values(sql) if t == "thread_context"]
    assert row["flattened_text_ref"].strip("'") == build_ref(content_hash(text), FLATTENED)


def test_a_non_store_ref_is_refused_loudly():
    with pytest.raises(SystemExit, match="not a raw-store ref"):
        export._store_ref("flattened/inline-see-json", FLATTENED, "thread_context x")
    ref = build_ref("ab" * 32, RAW)
    with pytest.raises(SystemExit, match="expected flattened/"):
        export._store_ref(ref, FLATTENED, "thread_context x")
