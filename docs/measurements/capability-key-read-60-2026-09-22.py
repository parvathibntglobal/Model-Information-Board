import json
import os
from collections import Counter

# The committed sibling, so this runs from a checkout rather than from the
# scratchpad it was written in.
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'capability-key-read-60-2026-09-22.json')) as fh:
    s = json.load(fh)

# One reader (anooj, via Claude), one pass, 2026-09-22. Sample of 60 drawn from
# all 1,385 claims, random.seed(20260922).
#   match   the key names what the quote describes
#   near    arguable either way; counted as MATCH in the conservative total
#   filler  the quote describes NO capability at all (a price, a bare figure,
#           an advertised spec) and the required key was filled in anyway
#   mis     the quote describes a capability the key does not name
LABEL = {
 1:'mis',    2:'filler', 3:'near',   4:'filler', 5:'near',   6:'mis',
 7:'match',  8:'near',   9:'filler',10:'near',  11:'mis',   12:'filler',
13:'match', 14:'mis',   15:'match', 16:'filler',17:'mis',   18:'mis',
19:'mis',   20:'filler',21:'near',  22:'mis',   23:'filler',24:'mis',
25:'match', 26:'match', 27:'filler',28:'filler',29:'match', 30:'filler',
31:'mis',   32:'near',  33:'mis',   34:'mis',   35:'filler',36:'mis',
37:'mis',   38:'filler',39:'near',  40:'match', 41:'match', 42:'match',
43:'mis',   44:'match', 45:'mis',   46:'mis',   47:'match', 48:'mis',
49:'match', 50:'match', 51:'filler',52:'filler',53:'mis',   54:'filler',
55:'match', 56:'mis',   57:'mis',   58:'mis',   59:'near',  60:'mis',
}
assert len(LABEL) == 60
for i, r in enumerate(s, 1):
    r['label'] = LABEL[i]
# Labels are already in the file above; nothing is rewritten here.

c = Counter(r['label'] for r in s)
print('population 1,385 claims | sample 60 | seed 20260922 | one reader, 2026-09-22')
print()
for k in ('match', 'near', 'filler', 'mis'):
    print(f'  {k:7s} {c[k]:3d}   {c[k]/60*100:4.1f}%')
print()
print(f'  key does NOT name what the quote describes (filler+mis): '
      f'{c["filler"]+c["mis"]}/60 = {(c["filler"]+c["mis"])/60*100:.0f}%')
print(f'  conservative (near counted as match)                   : '
      f'same {c["filler"]+c["mis"]}/60')
print(f'  strict subset - real capability, wrong key (mis only)  : '
      f'{c["mis"]}/60 = {c["mis"]/60*100:.0f}%')
print()
print('--- cross-tab: does the row carry its own capability slug? ---')
print(f'{"":8s} {"has slug":>9s} {"no slug":>9s}')
for k in ('match', 'near', 'filler', 'mis'):
    hs = sum(1 for r in s if r['label'] == k and r['slug'])
    ns = sum(1 for r in s if r['label'] == k and not r['slug'])
    print(f'{k:8s} {hs:9d} {ns:9d}')
