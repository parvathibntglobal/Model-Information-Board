"""Round 3, split three ways. A single accuracy figure over 36 rows conflates
three populations that argue different things, so it is not reported alone.
"""
import json, pathlib, collections

G = pathlib.Path("fixtures/golden")
def rows(p):
    ls = [json.loads(l) for l in (G/p).read_text(encoding="utf-8").splitlines() if l.strip()]
    return ls[0].get("_meta"), [r for r in ls if "_meta" not in r]

_, lab = rows("capability-choice-round3--labelled-by-anooj.jsonl")
_, side = rows("capability-choice-round3--extractor-chose.jsonl")
gold = {r["row_index"]: r["answers"]["capability"] for r in lab}
ext  = {r["row_index"]: r["extractor_chose"] for r in side}
quote = {r["row_index"]: " ".join(r["quote"].split()) for r in lab}

RATIFIED = {k for k in set(ext.values()) if "." in k or k == "over_refusal"}
IMPOSSIBLE = {"no-key-fits", "not-a-capability-claim"}

A = sorted(i for i, g in gold.items() if g not in IMPOSSIBLE and g != "cannot-tell")
B = sorted(i for i, g in gold.items() if g in IMPOSSIBLE)
C = sorted(i for i, g in gold.items() if g == "cannot-tell")
assert len(A) + len(B) + len(C) == 36

agree = [i for i in A if gold[i] == ext[i]]
disagree = [i for i in A if gold[i] != ext[i]]

print("=" * 72)
print("ROUND 3 — 36 claims, 15 documents, one site, one author, one extractor,")
print("one draw. NOT a pipeline misfiling rate.")
print("=" * 72)
print()
print(f"THE CEILING. The extractor's tool-schema enum offers the twelve ratified")
print(f"keys and nothing else, so `no-key-fits` and `not-a-capability-claim` are")
print(f"answers it CANNOT give. {len(B)} of 36 rows are one of those two.")
print(f"  maximum possible agreement = {len(A)} of 36 = {len(A)/36*100:.0f}%,")
print(f"  before extractor quality enters at all.")
print()
print(f"A. GOLD PICKED A RATIFIED KEY — the only rows where agreement is possible")
print(f"   n = {len(A)}   agreed {len(agree)}  disagreed {len(disagree)}"
      f"   = {len(agree)}/{len(A)} = {len(agree)/len(A)*100:.0f}%")
for i in A:
    mark = "OK " if gold[i] == ext[i] else "XX "
    print(f"     {mark} row {i:>2}  gold={gold[i]:<36} extractor={ext[i]}")
print()
print(f"B. GOLD SAYS THE EXTRACTOR SHOULD NOT HAVE ANSWERED — structurally impossible")
print(f"   n = {len(B)} of 36 = {len(B)/36*100:.0f}%")
for label in ("not-a-capability-claim", "no-key-fits"):
    ids = [i for i in B if gold[i] == label]
    print(f"     {label:<24} {len(ids):>2}  rows {ids}")
    for i in ids:
        print(f"        row {i:>2}  extractor said {ext[i]:<36} {quote[i][:52]}")
print()
print(f"C. CANNOT-TELL — about the POOL, not the extractor. Excluded from accuracy.")
print(f"   n = {len(C)}  rows {C}")
print()
print("-" * 72)
print("DENOMINATORS, kept apart:")
print(f"  {len(agree)}/36 = {len(agree)/36*100:.0f}%   what the repo scorer prints. Conflates all three.")
print(f"  {len(agree)}/{len(A)+len(B)} = {len(agree)/(len(A)+len(B))*100:.0f}%   over the 31 usable rows (cannot-tell excluded).")
print(f"  {len(agree)}/{len(A)} = {len(agree)/len(A)*100:.0f}%   over rows where agreement was POSSIBLE.")
print()
print("FILLER. Gold calls", len(B), "of the extractor's 36 choices answers it should")
print("not have given;", len([i for i in B if gold[i]=='not-a-capability-claim']),
      "of them are not-a-capability-claim (a price, an incident,")
print("a company) — the extractor emitted a ratified key for every one.")
print()
print("what the extractor said on the not-a-capability-claim rows:")
for k, n in collections.Counter(ext[i] for i in B if gold[i]=="not-a-capability-claim").most_common():
    print(f"   {n:>2}  {k}")
