"""Measure the column audit's web scan: collisions, derivability, and fix cost.

The measurement behind `docs/measurements/column-audit-web-scan-collisions.md`
and the #203 proposal. Committed rather than run once and quoted, because the
figures decide which fix lands and a number that decided something has to be
re-runnable by whoever doubts it.

    node   scripts/enum_js_builtins.js > builtins.json
    python scripts/measure_web_scan.py [builtins.json]

Needs no database. The schema comes from `contract/column_states.yaml`, which
`tests/test_column_states.py` asserts equals the live schema.

  A  how many single-owner column names collide with a JS builtin accessor
  B  whether "files that consume this table's endpoint" is derivable
  C  what each candidate fix removes -- phantoms, real reads, CI mismatches
"""
from __future__ import annotations

import ast
import collections
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import audit_columns as AC  # noqa: E402
import yaml  # noqa: E402

SQL_VERB = re.compile(r"\b(INSERT\s+INTO|UPDATE|SELECT|DELETE\s+FROM)\b", re.I)
TABLE_REF = re.compile(r"(?:INSERT\s+INTO|UPDATE|FROM|JOIN)\s+([a-z_]+)", re.I)

#: Hand classification of every column whose ONLY read evidence is a web match.
#: A judgement, not a measurement -- each entry names why, so it can be argued
#: with rather than taken. Kept next to the measurement it qualifies.
PHANTOM = {
    ("watermark", "cursor"): "CSS property in a style object",
    ("golden_label", "label"): "UI config literal {label: 'Trivial'}",
    ("audit", "verdict"): "JSX prose, 'is not a verdict:'",
    ("author_identity_cluster", "evidence"): "UI config object key",
    ("role", "name"): "this.name = 'ApiError' -- Error.name",
    ("source", "platform"): "a URL search-param key",
    ("coverage_gap", "subject"): "p.subject on a static in-repo article record",
    ("model_alias", "surface"): "the word 'surface' in a docblock",
    ("label", "state"): "m.state in Board.jsx is a cell state, not label.state",
}


# ---------------------------------------------------------------- schema
def schema_from_contract() -> dict[str, list[str]]:
    doc = yaml.safe_load((ROOT / "contract" / "column_states.yaml").read_text("utf-8"))
    return {t: sorted(cols) for t, cols in doc["columns"].items()}


def declared() -> dict:
    return yaml.safe_load(
        (ROOT / "contract" / "column_states.yaml").read_text("utf-8"))["columns"]


def single_owner(schema) -> dict[str, str]:
    owners = collections.defaultdict(set)
    for t, cols in schema.items():
        for c in cols:
            owners[c].add(t)
    return {c: next(iter(ts)) for c, ts in owners.items() if len(ts) == 1}


# ---------------------------------------------------------------- A
def measure_a(schema, owners, builtins):
    proto = set(builtins["proto"])
    return {
        "schema_columns": sum(len(v) for v in schema.values()),
        "single_owner": len(owners),
        "builtin_proto_names": len(proto),
        "node": builtins["node"],
        "collisions": sorted((owners[c], c) for c in owners if c in proto),
    }


# ---------------------------------------------------------------- B
def _literals(path):
    try:
        tree = ast.parse(path.read_text("utf-8", errors="replace"))
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            out.append(" ".join(v.value for v in node.values
                                if isinstance(v, ast.Constant)
                                and isinstance(v.value, str)))
    return out


def _tables_of(path, schema):
    found = set()
    for s in _literals(path):
        if SQL_VERB.search(s):
            found |= {m.group(1).lower() for m in TABLE_REF.finditer(s)} & set(schema)
    return found


def _routes():
    tree = ast.parse((ROOT / "judge" / "app.py").read_text("utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        paths = []
        for dec in node.decorator_list:
            call = dec if isinstance(dec, ast.Call) else None
            fn = call.func if call else dec
            if (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)
                    and fn.value.id == "app"
                    and fn.attr in ("get", "post", "put", "delete")
                    and call and call.args
                    and isinstance(call.args[0], ast.Constant)):
                paths.append(call.args[0].value)
        if not paths:
            continue
        mods = []
        for sub in ast.walk(node):
            if not isinstance(sub, ast.ImportFrom) or not sub.module:
                continue
            if sub.module.startswith(("judge.pages.", "judge.store.")):
                mods.append(sub.module)
            elif sub.module == "judge":
                mods += ["judge." + a.name for a in sub.names
                         if a.name in ("spend_ledger", "key_usage")]
        out.append({"paths": paths, "handler": node.name, "modules": mods})
    return out


def _norm(p):
    p = re.sub(r"\$\{[^}]*\}|\{[^}]*\}", "*", p)
    return p.split("?")[0].rstrip("/") or "/"


def _api_exports():
    src = (ROOT / "web" / "src" / "api" / "index.js").read_text("utf-8")
    out = {}
    for pat in (r"export\s+const\s+([A-Za-z_$][\w$]*)\s*=\s*[^\n]*?"
                r"request\(\s*[`'\"]([^`'\"]+)[`'\"]",
                r"export\s+const\s+([A-Za-z_$][\w$]*)\s*=\s*\([^)]*\)\s*=>\s*\n\s*"
                r"request\(\s*[`'\"]([^`'\"]+)[`'\"]"):
        for m in re.finditer(pat, src):
            out.setdefault(m.group(1), m.group(2))
    return out


def _web_imports():
    out = {}
    for p in AC._web_files():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        names = set()
        for m in re.finditer(r"import\s*\{([^}]*)\}\s*from\s*['\"][^'\"]*api['\"]",
                             p.read_text("utf-8", errors="replace"), re.S):
            for part in m.group(1).split(","):
                part = part.strip().split(" as ")[0].strip()
                if part:
                    names.add(part)
        if names:
            out[rel] = names
    return out


def scope_map(schema):
    """table -> {web files whose imports resolve to an endpoint touching it}."""
    mods = (sorted((ROOT / "judge" / "pages").glob("*.py"))
            + sorted((ROOT / "judge" / "store").glob("*.py"))
            + [ROOT / "judge" / "spend_ledger.py", ROOT / "judge" / "key_usage.py"])
    mod_tables = {}
    for p in mods:
        if p.name == "__init__.py" or not p.exists():
            continue
        nm = ("judge.pages." if p.parent.name == "pages"
              else "judge.store." if p.parent.name == "store" else "judge.") + p.stem
        mod_tables[nm] = _tables_of(p, schema)
    routes = _routes()
    path_tables = collections.defaultdict(set)
    for r in routes:
        t = set()
        for m in r["modules"]:
            t |= mod_tables.get(m, set())
        for pth in r["paths"]:
            path_tables[_norm(pth)] |= t
    exports = _api_exports()
    export_tables = {n: path_tables.get(_norm(p), set()) for n, p in exports.items()}
    imports = _web_imports()
    scope = collections.defaultdict(set)
    for rel, names in imports.items():
        for n in names:
            for t in export_tables.get(n, set()):
                scope[t].add(rel)
    return scope, {"routes": len(routes), "mod_tables": mod_tables,
                   "resolved_routes": sum(1 for r in routes if r["modules"]),
                   "exports": len(exports), "importers": len(imports)}


# ---------------------------------------------------------------- C
_NO_A3 = (r"\.[ \t]*{name}(?![A-Za-z0-9_])"
          r"|\[\s*[\"']{name}[\"']\s*\]")


def _discover(schema, *, drop_a3=False, scope=None, no_lexer=False):
    saved = (AC._ACCESS, AC._web_files, AC._code_mask)
    try:
        if drop_a3:
            AC._ACCESS = _NO_A3
        if no_lexer:
            AC._ACCESS = (r"\.\s*{name}(?![A-Za-z0-9_])"
                          r"|\[\s*[\"']{name}[\"']\s*\]"
                          r"|(?<![A-Za-z0-9_.]){name}\s*:")
            AC._code_mask = lambda s: bytearray(b"\x01") * len(s)
        if scope is None:
            return AC.discover(schema)
        rels = {str(p.relative_to(ROOT)).replace("\\", "/"): p
                for p in saved[1]()}
        merged = {}
        for tbl in schema:
            allowed = scope.get(tbl, set())
            AC._web_files = (lambda a=allowed: [rels[r] for r in a if r in rels])
            f = AC.discover(schema)
            for c in schema[tbl]:
                merged[(tbl, c)] = f[(tbl, c)]
        return merged
    finally:
        AC._ACCESS, AC._web_files, AC._code_mask = saved


def mismatches(found, schema, decl, consistent_with):
    bad = []
    for t, cols in schema.items():
        for c in cols:
            e = decl.get(t, {}).get(c) or {}
            if not isinstance(e, dict):
                continue
            d = e.get("state")
            if d not in consistent_with or e.get("known_gap"):
                continue
            a = found[(t, c)]["state"]
            if a not in consistent_with[d]:
                bad.append((t, c, d, a))
    return bad


def main() -> int:
    if len(sys.argv) > 1:
        builtins = json.loads(pathlib.Path(sys.argv[1]).read_text("utf-8"))
    else:
        builtins = json.loads(subprocess.run(
            ["node", str(ROOT / "scripts" / "enum_js_builtins.js")],
            capture_output=True, text=True, check=True).stdout)

    schema = schema_from_contract()
    owners = single_owner(schema)
    decl = declared()
    from test_column_states import CONSISTENT_WITH

    a = measure_a(schema, owners, builtins)
    print("=" * 78)
    print("A — COLLISION EXPOSURE")
    print("=" * 78)
    print(f"  schema columns              {a['schema_columns']}")
    print(f"  single-owner names          {a['single_owner']}   <- all the web check sees")
    print(f"  builtin prototype names     {a['builtin_proto_names']}   (Node {a['node']},"
          f" enumerated; NO DOM, so this is a floor)")
    print(f"  COLLIDE                     {len(a['collisions'])}")
    for t, c in a["collisions"]:
        print(f"      {t}.{c}")

    scope, binfo = scope_map(schema)
    covered = {t for t in schema if scope.get(t)}
    print()
    print("=" * 78)
    print("B — IS ENDPOINT SCOPING DERIVABLE?")
    print("=" * 78)
    print(f"  routes                      {binfo['routes']}")
    print(f"  resolving to SQL modules    {binfo['resolved_routes']}")
    print(f"  api exports -> a path       {binfo['exports']}")
    print(f"  web files importing them    {binfo['importers']}")
    print(f"  tables reachable            {len(covered)} of {len(schema)}")
    for t in sorted(schema):
        fs = sorted(scope.get(t, ()))
        print(f"      {t:<24} {len(fs)}  {', '.join(f.split('/')[-1] for f in fs)}")

    print()
    print("=" * 78)
    print("C — WHAT EACH FIX REMOVES  (baseline: CI is green, 0 mismatches)")
    print("=" * 78)
    cur = _discover(schema)
    base_web = {k for k, v in cur.items() if v["read_only_from_web"]}
    variants = [
        ("before steps 1+2", dict(no_lexer=True)),
        ("steps 1+2 (landed)", dict()),
        ("+ drop A3 key:", dict(drop_a3=True)),
        ("+ scoping", dict(scope=scope)),
        ("+ drop A3 and scope", dict(drop_a3=True, scope=scope)),
    ]
    hdr = (f"  {'variant':<21} {'web-only':>8} {'phantom':>7} "
           f"{'diag phantom':>12} {'real lost':>9} {'CI mismatch':>11}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for name, kw in variants:
        f = _discover(schema, **kw)
        wo = {k for k, v in f.items() if v["read_only_from_web"]}
        ph = wo & set(PHANTOM)
        diag = {k for k in wo if f[k]["state"] == AC.UNWRITTEN_READ}
        lost = base_web - wo - set(PHANTOM)
        mm = mismatches(f, schema, decl, CONSISTENT_WITH)
        print(f"  {name:<21} {len(wo):>8} {len(ph):>7} {len(diag & set(PHANTOM)):>12} "
              f"{len(lost):>9} {len(mm):>11}")
        for t, c, d, act in mm:
            print(f"        reconcile {t}.{c}: declared {d!r} -> would discover {act!r}")
        for t, c in sorted(lost):
            print(f"        would drop a real web read: {t}.{c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
