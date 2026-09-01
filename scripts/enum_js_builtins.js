// Enumerate JS builtin property names PROGRAMMATICALLY, not by hand.
//
// Two populations, because the audit's _ACCESS pattern has two shapes that can
// collide and they collide with different things:
//
//   proto   own property names on the PROTOTYPE (and instances) of every builtin
//           reachable from globalThis. These are the names that can legally
//           follow a dot -- `.size`, `.length`, `.name`. This is the population
//           that collides with the `\.name` alternative.
//   global  own property names on globalThis itself -- `Array`, `fetch`. These
//           can appear as bare identifiers, so they collide with nothing in
//           _ACCESS (all three alternatives need a dot, a bracket, or a colon),
//           and are reported only to keep the two apart.
//
// Reproducible: same Node, same output. Node version is stamped in the result so
// the figure carries where it came from.
const proto = new Set();
const glob = new Set();
const seen = new Set();

function harvest(target, into) {
  if (target == null || seen.has(target)) return;
  seen.add(target);
  try {
    for (const n of Object.getOwnPropertyNames(target)) into.add(n);
  } catch {}
}

for (const key of Object.getOwnPropertyNames(globalThis)) glob.add(key);

for (const key of Object.getOwnPropertyNames(globalThis)) {
  let v;
  try { v = globalThis[key]; } catch { continue; }
  if (v == null) continue;
  if (typeof v !== 'function' && typeof v !== 'object') continue;
  // A constructor's own statics (Array.from) and its prototype's members
  // (Array.prototype.map) both follow a dot in real code.
  harvest(v, proto);
  try { if (v.prototype) harvest(v.prototype, proto); } catch {}
}

// Instance-side names that live on neither the constructor nor the prototype.
const samples = [[], '', 0, {}, new Set(), new Map(), new WeakMap(), new Date(),
                 /x/, new Error('x'), function () {}, Promise.resolve(),
                 new Int8Array(1), new ArrayBuffer(1), new URL('https://x.tld'),
                 new URLSearchParams(), new AbortController(), new TextEncoder()];
for (const inst of samples) {
  try {
    harvest(inst, proto);
    harvest(Object.getPrototypeOf(inst), proto);
  } catch {}
}

const clean = (s) => [...s].filter((n) => /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(n)).sort();

console.log(JSON.stringify({
  node: process.version,
  note: 'DOM element properties are NOT in this population -- Node has no DOM. ' +
        'That makes the collision count a FLOOR, not a total.',
  proto_count: clean(proto).length,
  global_count: clean(glob).length,
  proto: clean(proto),
  global: clean(glob),
}, null, 1));
