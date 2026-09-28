"""Audit: which fields the API emits, and which of them anything reads.

#275's DECLARATION half. It asks one question — *does this producer's field have
a consumer* — and says nothing about whether the value is right. The other half,
whether a source still describes what it points at, is a different check with a
different reporting shape and is deliberately not here.

    consumed        a web file accesses the name as a field
    no_consumer     nothing does

WHY THE DECLARATION AND NOT AGREEMENT. Ruled on #275 from the #274/#279
sequence: `board_entry.quote` and `claim.quote` both held a JSON slice for
weeks, agreeing perfectly and both wrong, and an agreement check would have
been green throughout. Agreement between a copy and its source says nothing
about whether either is right.

THE WAIVER LIST IS THE OUTPUT THAT MATTERS
-------------------------------------------
A route this cannot analyse is LISTED AND WAIVED. It never fails the build.
Ruled by @anoojntglobal-sudo on #275, 2026-09-24:

    A check that blocks on what it cannot understand gets disabled, and a
    disabled check is worse than a permissive one with a visible waiver list.

So the waived set is printed on every run rather than only on failure. It is
the set of routes nobody can vouch for, written down — which is a finding, not
an apology.

WHAT THIS CANNOT SEE, AND WHICH WAY IT IS WRONG
------------------------------------------------
Evidence is a static read of `judge/app.py` and `web/src`. It cannot see a
field reached through spread (`{...row}`), through a variable built elsewhere,
or named only in a computed access. And a generic name — `id`, `count`, `key`
— matches a field access somewhere in a large frontend whether or not it is
THIS field.

**Both errors run the same way: they over-count consumers.** So a `no_consumer`
finding is a floor and a `consumed` finding is not proof. That is the same
direction as `audit_columns.py`'s own documented bias, and it is the safe
direction for a gate: it goes quiet rather than crying wolf, and the thing it
goes quiet about is recorded in the contract rather than lost.

    python scripts/audit_api_fields.py [out_dir]
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from audit_columns import _ACCESS, _code_mask, _web_files  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "judge" / "app.py"
CONTRACT = ROOT / "contract" / "api_fields.yaml"

_ROUTE_VERBS = ("get", "post", "put", "patch", "delete")

CONSUMED = "consumed"
NO_CONSUMER = "no_consumer"


class Unanalysable(str):
    """A route whose emitted fields cannot be read from the source.

    A string subclass so it prints as the reason and compares as one, rather
    than a bare tuple a caller has to remember the order of.
    """


def _route_paths(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Every path this handler is mounted at. One handler may carry several."""
    paths = []
    for dec in node.decorator_list:
        call = dec if isinstance(dec, ast.Call) else None
        fn = call.func if call else dec
        if (
            isinstance(fn, ast.Attribute)
            and isinstance(fn.value, ast.Name)
            and fn.value.id == "app"
            and fn.attr in _ROUTE_VERBS
            and call
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            paths.append(call.args[0].value)
    return paths


def emitted() -> tuple[dict[str, set[str]], dict[str, Unanalysable]]:
    """`({route: {field, ...}}, {route: why it could not be read})`.

    ⚠ TOP-LEVEL KEYS OF RETURNED DICT LITERALS, AND NOTHING ELSE. A narrow
      definition stated out loud beats a broad one that quietly includes
      whatever the walker happened to reach: a reader of the contract has to
      know which fields are in scope to know what its silence means.

    A handler with several `return`s contributes the union, because a caller
    may receive any of them.
    """
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    fields: dict[str, set[str]] = {}
    waived: dict[str, Unanalysable] = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        paths = _route_paths(node)
        if not paths:
            continue

        keys: set[str] = set()
        reasons: set[str] = set()
        returns = [
            sub for sub in ast.walk(node)
            if isinstance(sub, ast.Return) and sub.value is not None
        ]
        for sub in returns:
            if isinstance(sub.value, ast.Dict):
                for key in sub.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        keys.add(key.value)
                    else:
                        reasons.add("a computed key in the returned dict")
            else:
                reasons.add(f"returns {type(sub.value).__name__} rather than a dict literal")

        for path in paths:
            if keys:
                fields[path] = keys
            # ⚠ A ROUTE CAN BE BOTH, AND BOTH FACTS ARE KEPT. A handler with one
            #   dict-literal return and one `return _something(...)` has fields
            #   this can check AND a shape it cannot, and recording only the
            #   first would present partial coverage as complete.
            if reasons:
                waived[path] = Unanalysable("; ".join(sorted(reasons)))
    return fields, waived


def consumers() -> dict[str, set[str]]:
    """`{field name: {web files that access it}}`.

    ⚠ COMMENTS AND STRING LITERALS ARE MASKED OUT FIRST, via the same
      `_code_mask` the column audit uses. Reusing it rather than writing a
      second one is deliberate: two implementations of "is this a real access
      or just the word" drift, and the drift is invisible because both look
      right in isolation. That scanner already carries the corrections that
      cost weeks — `dedup_cluster.reach` credited to "Cannot reach the API",
      and a comment that had to be reworded to keep CI green.
    """
    found: dict[str, set[str]] = {}
    sources = []
    for path in _web_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        mask = _code_mask(text)
        code = "".join(c if mask[i] else " " for i, c in enumerate(text))
        sources.append((path, code))

    names = {f for fs in emitted()[0].values() for f in fs}
    for name in names:
        pattern = re.compile(_ACCESS.format(name=re.escape(name)))
        hits = {
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path, code in sources if pattern.search(code)
        }
        if hits:
            found[name] = hits
    return found


def discover() -> dict:
    """The whole audit, as data. No I/O beyond reading the tree."""
    fields, waived = emitted()
    reads = consumers()

    rows = {}
    for route, names in sorted(fields.items()):
        for name in sorted(names):
            rows.setdefault(name, {"routes": [], "state": NO_CONSUMER, "read_by": []})
            rows[name]["routes"].append(route)
            if name in reads:
                rows[name]["state"] = CONSUMED
                rows[name]["read_by"] = sorted(reads[name])
    return {
        "fields": rows,
        "waived": {route: str(why) for route, why in sorted(waived.items())},
        "routes_analysed": len(fields),
        "routes_waived": len(waived),
    }


def main(argv: list[str] | None = None) -> int:
    #: TAKEN AS AN ARGUMENT, NOT READ FROM `sys.argv` INSIDE. A `main()` that
    #: can only be called through global state is one a test calls with pytest's
    #: own argv - which is how the first version of the waiver-list test tried
    #: to mkdir a directory named after a test file.
    argv = sys.argv[1:] if argv is None else argv
    result = discover()
    no_consumer = [n for n, r in result["fields"].items() if r["state"] == NO_CONSUMER]

    print(f"routes analysed   {result['routes_analysed']}")
    print(f"routes waived     {result['routes_waived']}   <- nobody can vouch for these")
    print(f"fields emitted    {len(result['fields'])}")
    print(f"  with a consumer {len(result['fields']) - len(no_consumer)}")
    print(f"  NO CONSUMER     {len(no_consumer)}")
    print()
    print("WAIVED ROUTES, printed every run rather than only on failure:")
    for route, why in result["waived"].items():
        print(f"  {route:52} {why}")

    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "api-fields.json").write_text(
            json.dumps(result, indent=1, sort_keys=True), encoding="utf-8"
        )
        print(f"\nwrote {out / 'api-fields.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
