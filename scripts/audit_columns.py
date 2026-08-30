"""Audit: which schema columns are written, read, both, or neither.

Four states, and a fifth the four cannot see - see
`docs/measurements/column-audit-306-columns.md`.

    written + read      a writer and a SELECT both exist
    written, UNREAD     written and nothing selects it
    UNWRITTEN, read     a reader exists and no writer does. The DIAGNOSTIC one:
                        somebody already decided the value matters
    neither             no writer, no reader

WHAT THIS CAN AND CANNOT SEE

Evidence is static analysis of non-test source: SQL found in string literals,
plus dict keys in modules that insert. It CANNOT see a column reached only
through `SELECT *`, a dynamically-assembled statement, or a reader that routes
through YAML rather than a query - `source.terms_ruling` is read by
`assert_terms_reviewed` through `contract/sources.yaml`, and this reports it
unread. **The direction of that error is knowable: it under-counts reads.**
`contract/column_states.yaml` carries `read_not_by_query` for exactly that case,
so the exceptions are a declared state rather than a growing list.

It also says nothing about whether a column is POPULATED. `harvest_run.truncated_by`
is 41.3% populated and `pages_fetched` is 0.0%, and both classify identically
here. That half needs row counts and belongs in a nightly report rather than a
test - as a test it passes on an empty CI database and green-lights the
`pages_fetched` defect exactly where it matters least.

    python scripts/audit_columns.py <out_dir>
"""

from __future__ import annotations

import ast
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIRS = ("collect", "judge", "scripts")
WEB_DIRS = ("web/src",)
SKIP = re.compile(r"(^|[\\/])(tests|\.venv|__pycache__|node_modules)([\\/]|$)")

SQL_VERB = re.compile(r"\b(INSERT\s+INTO|UPDATE|SELECT|DELETE\s+FROM)\b", re.I)
STAR = re.compile(r"SELECT\s+\*", re.I)
WRITE_VERB = re.compile(r"\b(INSERT\s+INTO|UPDATE)\b", re.I)
TABLE_REF = re.compile(r"(?:INSERT\s+INTO|UPDATE|FROM|JOIN)\s+([a-z_]+)", re.I)

#: `FROM claim c`, `JOIN claim_weight AS w` -> the alias and the table it names.
#: Used to attribute a QUALIFIED column reference to one table instead of to
#: every table in the statement — the SQL twin of the web check's "the name must
#: belong to exactly one table" correction below, and found the same way: by a
#: false positive. `claim` and `claim_weight` both have `pipeline_version`, and
#: `judge/store/cells.py` joins them and filters on `c.pipeline_version`. Without
#: aliases that one WHERE clause credited `claim_weight.pipeline_version` with a
#: read it does not have, and the column's declared `write_only` — which is
#: correct — read as a mismatch.
#:
#: The trailing keyword guard matters: `JOIN document d ON ...` must yield
#: `d`, and `FROM claim WHERE ...` must yield no alias at all rather than the
#: alias `where`.
TABLE_ALIAS = re.compile(
    r"(?:FROM|JOIN)\s+([a-z_]+)(?:\s+AS)?\s+([a-z][a-z0-9_]*)"
    r"(?=\s|,|$)",
    re.I,
)
_ALIAS_STOPWORDS = frozenset(
    {"on", "where", "group", "order", "limit", "join", "left", "right", "inner",
     "outer", "full", "cross", "using", "set", "values", "returning", "as",
     "and", "or", "union", "having", "offset", "for", "natural"}
)
INSERT_TABLE = re.compile(r"INSERT\s+INTO\s+([a-z_]+)", re.I)

#: A view is never written. Leaving `cell_current` in put 18 columns into
#: "unwritten, read" and "neither" as artifacts of the method rather than
#: findings, so callers pass the view names and they are dropped.
#: A web-side hit only counts as a read where it looks like a FIELD ACCESS.
#: `row.reach`, `row["reach"]`, or `reach:` as an object key -- never a bare word,
#: because column names are often ordinary English and prose then reads as a
#: reader. See the web block in `discover` for the two columns that proved it.
_ACCESS = (
    r"\.\s*{name}(?![A-Za-z0-9_])"
    r"|\[\s*[\"']{name}[\"']\s*\]"
    r"|(?<![A-Za-z0-9_.]){name}\s*:"
)

WRITTEN_READ = "written+read"
WRITTEN_UNREAD = "written, UNREAD"
UNWRITTEN_READ = "UNWRITTEN, read"
NEITHER = "neither"


def columns_of(conn) -> dict[str, list[str]]:
    """`{table: [column, ...]}` for base tables, from any connection.

    Reads `information_schema` rather than parsing `tables.sql`, so migrations
    are included rather than overlaid by hand - and `table_type` drops views.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT c.table_name, c.column_name "
        "FROM information_schema.columns c "
        "JOIN information_schema.tables t "
        "  ON t.table_schema = c.table_schema AND t.table_name = c.table_name "
        "WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE' "
        "ORDER BY c.table_name, c.ordinal_position"
    )
    out: dict[str, list[str]] = collections.defaultdict(list)
    for table, column in cur.fetchall():
        out[table].append(column)
    return dict(out)


def _source_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for d in SRC_DIRS:
        files += [p for p in (ROOT / d).rglob("*.py") if not SKIP.search(str(p))]
    files += [p for p in ROOT.glob("*.py") if not SKIP.search(str(p))]
    return files


def _web_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for d in WEB_DIRS:
        base = ROOT / d
        if base.exists():
            for ext in ("*.js", "*.jsx"):
                files += [f for f in base.rglob(ext) if not SKIP.search(str(f))]
    return files


def _string_literals(path: pathlib.Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):
            parts = [
                v.value for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            ]
            if parts:
                out.append((node.lineno, " ".join(parts)))
    return out


def _dict_keys(path: pathlib.Path) -> set[str]:
    """`"col": value` keys, as write evidence in modules that insert."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
    return keys


def discover(schema: dict[str, list[str]]) -> dict[tuple[str, str], dict]:
    """`{(table, column): {state, written_at, read_at}}`. No database needed."""
    written: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    read: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    star: set[str] = set()

    word = {
        (t, c): re.compile(r"(?<![A-Za-z0-9_])" + re.escape(c) + r"(?![A-Za-z0-9_])")
        for t, cols in schema.items() for c in cols
    }

    for path in _source_files():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        literals = _string_literals(path)
        inserting = {m.group(1).lower() for _, s in literals for m in INSERT_TABLE.finditer(s)}
        keys = _dict_keys(path) if inserting else set()

        for lineno, s in literals:
            if not SQL_VERB.search(s):
                continue
            tables = {m.group(1).lower() for m in TABLE_REF.finditer(s)} & set(schema)
            if not tables:
                continue
            is_write = bool(WRITE_VERB.search(s))
            is_read = bool(re.search(r"\bSELECT\b", s, re.I))
            if STAR.search(s):
                star |= tables
            # alias -> table, for the qualified references below.
            aliases = {
                alias.lower(): tbl.lower()
                for tbl, alias in TABLE_ALIAS.findall(s)
                if alias.lower() not in _ALIAS_STOPWORDS and tbl.lower() in schema
            }
            for table in tables:
                for column in schema[table]:
                    if not word[(table, column)].search(s):
                        continue
                    # A reference qualified by an alias belongs to THAT alias's
                    # table. Only skip when every occurrence in the statement is
                    # qualified and none of them resolves here — an unqualified
                    # occurrence is genuinely ambiguous and keeps the old,
                    # over-counting behaviour, which is the direction this
                    # method already errs in.
                    qualified = {
                        m.group(1).lower()
                        for m in re.finditer(
                            r"(?<![A-Za-z0-9_])([a-z][a-z0-9_]*)\."
                            + re.escape(column)
                            + r"(?![A-Za-z0-9_])",
                            s,
                            re.I,
                        )
                    }
                    bare = re.search(
                        r"(?<![A-Za-z0-9_.])" + re.escape(column) + r"(?![A-Za-z0-9_])",
                        s,
                    )
                    if qualified and not bare:
                        owners = {aliases.get(q, q) for q in qualified}
                        if table not in owners:
                            continue
                    if is_write:
                        written[(table, column)].add(f"{rel}:{lineno}")
                    if is_read:
                        read[(table, column)].add(f"{rel}:{lineno}")

        for table in inserting & set(schema):
            for column in schema[table]:
                if column in keys:
                    written[(table, column)].add(f"{rel}:dict-key")

    # THE WEB CHECK NEEDS A FIELD ACCESS, NOT A WORD. Two corrections deep.
    #
    # First it was table-blind: a JSX hit on `pipeline_version` was credited to
    # every table owning a column of that name, giving `claim.pipeline_version` a
    # read that was really `job_run`'s. Fixed by requiring the name to belong to
    # exactly one table.
    #
    # That was not enough, because column names are often ordinary English.
    # `dedup_cluster.reach` is unique to its table AND appears in
    # `web/src/auth.js:47` as *"Cannot reach the API"* -- a word in an error
    # string, counted as a read of an empty table. It then classified as
    # UNWRITTEN-read, which is the DIAGNOSTIC state, so the false positive landed
    # in the one bucket somebody would act on.
    #
    # So a web hit must look like an ACCESS: `.reach`, `["reach"]`, `['reach']`,
    # or `reach:` as an object key. Prose does not match any of those. Still
    # under-counts -- a name reached through a destructure or a variable is
    # invisible -- and that is the direction this method already errs in, which
    # `read_not_by_query` exists to absorb.
    owners: dict[str, set[str]] = collections.defaultdict(set)
    for table, cols in schema.items():
        for column in cols:
            owners[column].add(table)

    web = {str(p.relative_to(ROOT)).replace("\\", "/"): p.read_text(encoding="utf-8",
           errors="replace") for p in _web_files()}
    for (table, column), _pattern in word.items():
        if len(owners[column]) != 1:
            continue
        access = re.compile(_ACCESS.format(name=re.escape(column)))
        for rel, text in web.items():
            if access.search(text):
                read[(table, column)].add(f"{rel}:web")
                break

    out = {}
    for table, cols in schema.items():
        for column in cols:
            key = (table, column)
            w, r = bool(written[key]), bool(read[key])
            state = (WRITTEN_READ if w and r else WRITTEN_UNREAD if w
                     else UNWRITTEN_READ if r else NEITHER)
            out[key] = {
                "state": state,
                "written_at": sorted(written[key])[:2],
                "read_at": sorted(read[key])[:2],
                "select_star_table": table in star,
            }
    return out


def main() -> int:
    import psycopg

    from collect.config import settings

    out_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    with psycopg.connect(settings().database_url, connect_timeout=25) as conn:
        schema = columns_of(conn)
    found = discover(schema)

    states = collections.Counter(v["state"] for v in found.values())
    total = sum(states.values())
    print(f"tables {len(schema)}  columns {total}\n")
    for state, n in sorted(states.items(), key=lambda x: -x[1]):
        print(f"  {state:<18} {n:4d}   {100 * n / total:5.1f}%")

    rows = [{"table": t, "column": c, **v} for (t, c), v in sorted(found.items())]
    target = out_dir / "column-audit.json"
    target.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\nfull result: {target}")

    for label in (WRITTEN_UNREAD, UNWRITTEN_READ, NEITHER):
        selected = collections.defaultdict(list)
        for (t, c), v in sorted(found.items()):
            if v["state"] == label:
                selected[t].append(c)
        n = sum(len(v) for v in selected.values())
        print(f"\n--- {label} ({n}) ---")
        for t in sorted(selected):
            print(f"  {t:<22} {', '.join(selected[t])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
