"""First reading against second. WHAT THE MISSING CONTEXT WAS WORTH.

NOT A TREND AND NOT TWO LABELLERS. Same 36 rows, same 15 options, one labeller,
and the second reading had `source_document_text` and the twelve key
definitions that the first did not. So a disagreement measures the information,
not the reader and not the extractor.
"""
import json
import pathlib
from collections import Counter

G = pathlib.Path("fixtures/golden")
IMPOSSIBLE = {"no-key-fits", "not-a-capability-claim"}


def rows(name):
    text = (G / name).read_text(encoding="utf-8")
    ls = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [r for r in ls if "_meta" not in r]


first = {r["row_index"]: r["answers"]["capability"]
         for r in rows("capability-choice-round3--labelled-by-anooj.jsonl")}
second = {r["row_index"]: r["answers"]["capability"]
          for r in rows("capability-choice-round3--second-reading-by-anooj.jsonl")}
ext = {r["row_index"]: r["extractor_chose"]
       for r in rows("capability-choice-round3--extractor-chose.jsonl")}
quote = {r["row_index"]: " ".join(r["quote"].split())
         for r in rows("capability-choice-round3--unlabelled.jsonl")}


def bucket(g):
    if g == "cannot-tell":
        return "cannot-tell"
    return "impossible" if g in IMPOSSIBLE else "ratified"


print("=" * 74)
print("ROUND 3 — what the missing context was worth")
print("36 rows, one labeller, two readings. NOT a trend, NOT two labellers.")
print("=" * 74)
print()

changed = sorted(i for i in first if first[i] != second[i])
print(f"CHANGED: {len(changed)} of 36")
for i in changed:
    print(f"  row {i:>2}  {first[i]:<24} -> {second[i]:<24} {quote[i][:44]}")
print()

for label, d in (("first ", first), ("second", second)):
    c = Counter(bucket(v) for v in d.values())
    print(f"{label}:  ratified {c['ratified']:>2}   impossible {c['impossible']:>2}"
          f"   cannot-tell {c['cannot-tell']:>2}")
print()

ct1 = {i for i, v in first.items() if v == "cannot-tell"}
ct2 = {i for i, v in second.items() if v == "cannot-tell"}
print(f"cannot-tell resolved: {len(ct1 - ct2)} of {len(ct1)}  -> rows {sorted(ct1 - ct2)}")
print(f"           remaining: {sorted(ct2)}")
print()

print("THE CEILING MOVED. Only rows whose gold is a ratified key can ever agree")
print("with the extractor, whose enum offers nothing else.")
for label, d in (("first ", first), ("second", second)):
    poss = [i for i in d if bucket(d[i]) == "ratified"]
    agree = [i for i in poss if d[i] == ext[i]]
    print(f"  {label}: ceiling {len(poss)}/36 = {len(poss)/36*100:.0f}%"
          f"   agreed {len(agree)}/{len(poss)} = {len(agree)/len(poss)*100:.0f}%")
print()

print("DIRECTION — where the extra information pushed the answer:")
moves = Counter((bucket(first[i]), bucket(second[i])) for i in changed)
for (a, b), n in sorted(moves.items(), key=lambda kv: -kv[1]):
    print(f"  {n:>2}  {a} -> {b}")
print()
toward_impossible = [i for i in changed if bucket(second[i]) == "impossible"
                     and bucket(first[i]) != "impossible"]
print(f"  rows that became 'the claim should not exist' WITH context: {toward_impossible}")
