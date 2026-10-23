"""Read GGUF metadata AND tensor descriptions (names, shapes) - never tensor data.
Report blk.0.attn_k / attn_v shapes against the header's implied head size."""
import struct
import sys
import time

import httpx

UA = sys.argv[1]
TARGETS = [
    ("unsloth/Mistral-Nemo-Instruct-2407-GGUF", "Mistral-Nemo-Instruct-2407.Q4_K_M.gguf"),
    ("bartowski/Mistral-Nemo-Instruct-2407-GGUF", "Mistral-Nemo-Instruct-2407-Q4_K_M.gguf"),
    ("unsloth/Phi-4-mini-instruct-GGUF", "Phi-4-mini-instruct-Q4_K_M.gguf"),
    ("bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"),
    ("unsloth/gemma-4-12b-it-GGUF", "gemma-4-12b-it-Q4_K_M.gguf"),
]
SZ = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
FM = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?",
      10: "<Q", 11: "<q", 12: "<d"}


class Short(Exception):
    pass


def parse(b):
    o = [24]

    def need(n):
        if o[0] + n > len(b):
            raise Short

    def u(fmt, n):
        need(n)
        v = struct.unpack_from(fmt, b, o[0])[0]
        o[0] += n
        return v

    def s():
        n = u("<Q", 8)
        need(n)
        t = b[o[0]:o[0] + n].decode("utf-8", "replace")
        o[0] += n
        return t

    def val(t):
        if t == 8:
            return s()
        if t == 9:
            it, n = u("<I", 4), u("<Q", 8)
            if it == 8:
                for _ in range(n):
                    s()
                return None
            need(SZ[it] * n)
            o[0] += SZ[it] * n
            return None
        return u(FM[t], SZ[t])

    _, nt, nkv = struct.unpack_from("<IQQ", b, 4)
    kv = {}
    for _ in range(nkv):
        k = s()
        kv[k] = val(u("<I", 4))
    meta_end = o[0]
    shapes = {}
    for _ in range(nt):
        name = s()
        nd = u("<I", 4)
        dims = [u("<Q", 8) for _ in range(nd)]
        u("<I", 4)
        u("<Q", 8)
        if name.startswith("blk.0.attn_"):
            shapes[name] = dims
    return kv, shapes, meta_end, o[0]


with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=60) as c:
    for repo, f in TARGETS:
        url = f"https://huggingface.co/{repo}/resolve/main/{f}"
        buf = b""
        while True:
            r = c.get(url, headers={"Range": f"bytes={len(buf)}-{len(buf) + (4 << 20) - 1}"})
            assert r.status_code == 206, r.status_code
            buf += r.content
            try:
                kv, shapes, meta_end, info_end = parse(buf)
                break
            except Short:
                time.sleep(0.3)
        arch = kv["general.architecture"]
        g = lambda k, kv=kv, arch=arch: kv.get(f"{arch}.{k}")  # noqa: E731
        kvh = g("attention.head_count_kv")
        print(f"== {repo}: metadata ends {meta_end / 2**20:.2f} MiB, tensor list ends "
              f"{info_end / 2**20:.2f} MiB, read {len(buf) / 2**20:.0f} MiB")
        print(f"   emb={g('embedding_length')} heads={g('attention.head_count')} kv_heads={kvh} "
              f"key_length={g('attention.key_length')} rope.dim={g('rope.dimension_count')}")
        for k, v in sorted(shapes.items()):
            if k.endswith(("attn_k.weight", "attn_v.weight", "attn_q.weight")):
                print(f"   {k} {v}")
        time.sleep(1)
