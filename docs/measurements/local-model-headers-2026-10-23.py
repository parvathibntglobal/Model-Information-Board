"""Measure: read every listed model's GGUF header in 4 MiB steps; record fields and bytes read."""

import json
import struct
import sys
import time

import httpx
import yaml

UA, MODELS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CHUNK, MAX = 4 << 20, 32 << 20
SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
FMT = {
    0: "<B",
    1: "<b",
    2: "<H",
    3: "<h",
    4: "<I",
    5: "<i",
    6: "<f",
    7: "<?",
    10: "<Q",
    11: "<q",
    12: "<d",
}


class Short(Exception):
    pass


def parse(b):
    def need(o, n):
        if o + n > len(b):
            raise Short

    def rstr(o):
        need(o, 8)
        (n,) = struct.unpack_from("<Q", b, o)
        need(o + 8, n)
        return b[o + 8 : o + 8 + n].decode("utf-8", "replace"), o + 8 + n

    def rval(t, o):
        if t == 8:
            return rstr(o)
        if t == 9:
            need(o, 12)
            it, n = struct.unpack_from("<IQ", b, o)
            o += 12
            if it == 8:
                for _ in range(n):
                    _, o = rstr(o)
                return None, o
            need(o, SIZES[it] * n)
            vals = (
                [struct.unpack_from(FMT[it], b, o + SIZES[it] * i)[0] for i in range(min(n, 256))]
                if n <= 256
                else None
            )
            return vals, o + SIZES[it] * n
        need(o, SIZES[t])
        (v,) = struct.unpack_from(FMT[t], b, o)
        return v, o + SIZES[t]

    need(0, 24)
    assert b[:4] == b"GGUF"
    _, nt, nkv = struct.unpack_from("<IQQ", b, 4)
    off, kv = 24, {}
    for _ in range(nkv):
        k, off = rstr(off)
        need(off, 4)
        (t,) = struct.unpack_from("<I", b, off)
        off += 4
        v, off = rval(t, off)
        if v is not None and not k.startswith("tokenizer."):
            kv[k] = v
    return kv, off


with open(MODELS, encoding="utf-8") as fh:
    models = yaml.safe_load(fh)["models"]
results = {}
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=60) as c:
    for m in models:
        f = m["files"]["Q4_K_M"][0]
        url = f"https://huggingface.co/{m['gguf_repo']}/resolve/main/{f}"
        buf, got = b"", None
        while len(buf) < MAX:
            r = c.get(url, headers={"Range": f"bytes={len(buf)}-{len(buf) + CHUNK - 1}"})
            if r.status_code not in (200, 206):
                got = {"error": f"HTTP {r.status_code}"}
                break
            buf += r.content
            try:
                kv, end = parse(buf)
                arch = kv.get("general.architecture")
                pick = {
                    k.split(".", 1)[1] if k.startswith(f"{arch}.") else k: v
                    for k, v in kv.items()
                    if k.startswith(f"{arch}.")
                    or k
                    in ("general.architecture", "general.size_label", "general.parameter_count")
                }
                got = {"header_end": end, "bytes_read": len(buf), "fields": pick}
                break
            except Short:
                time.sleep(0.3)
                continue
        results[m["id"]] = got or {"error": f"header longer than {MAX} bytes"}
        g = results[m["id"]]
        fl = g.get("fields", {})
        other_keys = (
            "ssm", "kv_lora", "sliding_window_pattern", "full_attention", "shared_kv", "recurrent",
        )
        other = [k for k in fl if any(x in k for x in other_keys)][:3]
        end = g.get("header_end", 0) / 2**20
        read = g.get("bytes_read", 0) / 2**20
        arch = fl.get("general.architecture", "")
        print(
            f"{m['id']:32} {g.get('error') or ''}{arch!s:14} end={end:.1f}MiB read={read:.0f}MiB "
            f"L={fl.get('block_count')} kvh={fl.get('attention.head_count_kv')} "
            f"kl={fl.get('attention.key_length')} sw={fl.get('attention.sliding_window')} "
            f"other={other}"
        )
        time.sleep(0.5)
with open(OUT, "w") as fh:
    json.dump(results, fh, indent=1, default=str)
