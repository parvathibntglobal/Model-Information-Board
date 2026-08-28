"""Audit: which schema columns are written, read, both, or neither.

Column list from the LIVE schema (information_schema), so migrations are
included rather than overlaid onto tables.sql by hand.

Evidence from static analysis of non-test source. Method limits are printed
with the result: this classifies SQL found in string literals plus dict keys in
modules that insert, and it cannot see a column reached only through
`SELECT *`, a dynamically-built statement, or an ORM.
"""
from __future__ import annotations
import ast, pathlib, re, sys, json, collections
import psycopg
from collect.config import settings

ROOT = pathlib.Path(".")
SRC_DIRS = ["collect", "judge", "scripts"]
WEB_DIRS = ["web/src"]
SKIP = re.compile(r"(^|[\/])(tests|\.venv|__pycache__|node_modules)([\/]|$)")

SQL_VERB = re.compile(r"\b(INSERT\s+INTO|UPDATE|SELECT|DELETE\s+FROM)\b", re.I)
STAR = re.compile(r"SELECT\s+\*", re.I)


def live_columns():
    with psycopg.connect(settings().database_url, connect_timeout=25) as c:
        cur = c.cursor()
        cur.execute("""select table_name, column_name from information_schema.columns
                       where table_schema='public' order by table_name, ordinal_position""")
        out = collections.defaultdict(list)
        for t, col in cur.fetchall():
            out[t].append(col)
        return dict(out)


def source_files():
    files = []
    for d in SRC_DIRS:
        files += [p for p in (ROOT / d).rglob("*.py") if not SKIP.search(str(p))]
    files += [p for p in ROOT.glob("*.py") if not SKIP.search(str(p))]
    return files


def web_files():
    files = []
    for d in WEB_DIRS:
        p = ROOT / d
        if p.exists():
            for ext in ("*.js", "*.jsx"):
                files += [f for f in p.rglob(ext) if not SKIP.search(str(f))]
    return files


def string_literals(path):
    """Every string constant in a Python file, with its line."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):  # f-string: concatenate the literal parts
            parts = [v.value for v in node.values
                     if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            if parts:
                out.append((node.lineno, " ".join(parts)))
    return out


def dict_keys(path):
    """`"col": value` keys, as write evidence in modules that insert."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
    return keys


def main():
    schema = live_columns()
    written = collections.defaultdict(set)   # (table,col) -> {file:line}
    read = collections.defaultdict(set)
    star_tables = set()

    word = {}
    for t, cols in schema.items():
        for col in cols:
            word[(t, col)] = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(col) + r"(?![A-Za-z0-9_])")

    for path in source_files():
        rel = str(path).replace("\\", "/")
        lits = string_literals(path)
        inserting_tables = set()
        for _, s in lits:
            for m in re.finditer(r"INSERT\s+INTO\s+([a-z_]+)", s, re.I):
                inserting_tables.add(m.group(1).lower())
        dkeys = dict_keys(path) if inserting_tables else set()

        for lineno, s in lits:
            if not SQL_VERB.search(s):
                continue
            tables = {m.group(1).lower() for m in
                      re.finditer(r"(?:INSERT\s+INTO|UPDATE|FROM|JOIN)\s+([a-z_]+)", s, re.I)}
            tables &= set(schema)
            if not tables:
                continue
            is_write = bool(re.search(r"\b(INSERT\s+INTO|UPDATE)\b", s, re.I))
            is_read = bool(re.search(r"\bSELECT\b", s, re.I))
            if STAR.search(s):
                star_tables |= tables
            for t in tables:
                for col in schema[t]:
                    if word[(t, col)].search(s):
                        if is_write:
                            written[(t, col)].add(f"{rel}:{lineno}")
                        if is_read:
                            read[(t, col)].add(f"{rel}:{lineno}")

        for t in inserting_tables & set(schema):
            for col in schema[t]:
                if col in dkeys:
                    written[(t, col)].add(f"{rel}:dict-key")

    webtext = {}
    for path in web_files():
        webtext[str(path).replace("\\", "/")] = path.read_text(encoding="utf-8", errors="replace")
    for (t, col), pat in word.items():
        for rel, txt in webtext.items():
            if pat.search(txt):
                read[(t, col)].add(f"{rel}:web")
                break

    states = collections.Counter()
    rows = []
    for t in sorted(schema):
        for col in schema[t]:
            w, r = bool(written[(t, col)]), bool(read[(t, col)])
            state = ("written+read" if w and r else "written, UNREAD" if w
                     else "UNWRITTEN, read" if r else "neither")
            states[state] += 1
            rows.append((t, col, state, sorted(written[(t, col)])[:2], sorted(read[(t, col)])[:2]))

    total = sum(states.values())
    print(f"tables {len(schema)}  columns {total}\n")
    for s, n in sorted(states.items(), key=lambda x: -x[1]):
        print(f"  {s:<18} {n:4d}   {100*n/total:5.1f}%")
    print(f"\ntables reached by SELECT * anywhere: {len(star_tables)} -> {sorted(star_tables)}")
    out = pathlib.Path(sys.argv[1]) / "column-audit.json"
    out.write_text(json.dumps([{"table": t, "column": c, "state": s,
                                "written_at": w, "read_at": r} for t, c, s, w, r in rows],
                              indent=1), encoding="utf-8")
    print(f"\nfull result: {out}")
    for label in ("written, UNREAD", "UNWRITTEN, read", "neither"):
        sel = [(t, c) for t, c, s, _, _ in rows if s == label]
        print(f"\n--- {label} ({len(sel)}) ---")
        by = collections.defaultdict(list)
        for t, c in sel:
            by[t].append(c)
        for t in sorted(by):
            print(f"  {t:<22} {', '.join(by[t])}")


main()
