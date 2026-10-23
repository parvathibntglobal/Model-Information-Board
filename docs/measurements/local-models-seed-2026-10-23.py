"""One-off: resolve a seed list of local models to GGUF repos and measured file sizes.

Input: (family, label, repo-name stem) rows. For each, look for `<stem>-GGUF` under the
quantizers in preference order and read its file list with sizes. Output JSON for review.
"""

import json
import re
import sys
import time

import httpx

UA = sys.argv[1]
OUT = sys.argv[2]
AUTHORS = ["unsloth", "ggml-org", "bartowski", "lmstudio-community"]

SEED = [
    # family, label, stem (as the original repo is named)
    ("Qwen", "Qwen3.8 27B", "Qwen3.8-27B"),
    ("Qwen", "Qwen3.8 Flash Next", "Qwen3.8-Flash-Next"),
    ("Qwen", "Qwen3.6 35B A3B", "Qwen3.6-35B-A3B"),
    ("Qwen", "Qwen3.6 27B", "Qwen3.6-27B"),
    ("Qwen", "Qwen3.5 0.8B", "Qwen3.5-0.8B"),
    ("Qwen", "Qwen3.5 2B", "Qwen3.5-2B"),
    ("Qwen", "Qwen3.5 4B", "Qwen3.5-4B"),
    ("Qwen", "Qwen3.5 9B", "Qwen3.5-9B"),
    ("Qwen", "Qwen3.5 35B A3B", "Qwen3.5-35B-A3B"),
    ("Qwen", "Qwen3 4B Instruct 2507", "Qwen3-4B-Instruct-2507"),
    ("Qwen", "Qwen3 8B", "Qwen3-8B"),
    ("Qwen", "Qwen3 14B", "Qwen3-14B"),
    ("Qwen", "Qwen3 30B A3B Instruct 2507", "Qwen3-30B-A3B-Instruct-2507"),
    ("Qwen", "Qwen3 Coder 30B A3B", "Qwen3-Coder-30B-A3B-Instruct"),
    ("Qwen", "Qwen2.5 Coder 7B", "Qwen2.5-Coder-7B-Instruct"),
    ("Qwen", "Qwen2.5 Coder 14B", "Qwen2.5-Coder-14B-Instruct"),
    ("Qwen", "Qwen2.5 7B", "Qwen2.5-7B-Instruct"),
    ("Qwen", "Qwen2.5 32B", "Qwen2.5-32B-Instruct"),
    ("Gemma", "Gemma 4 E2B", "gemma-4-E2B-it"),
    ("Gemma", "Gemma 4 E4B", "gemma-4-E4B-it"),
    ("Gemma", "Gemma 4 12B", "gemma-4-12b-it"),
    ("Gemma", "Gemma 4 26B A4B", "gemma-4-26B-A4B-it"),
    ("Gemma", "Gemma 4 31B", "gemma-4-31B-it"),
    ("Gemma", "Gemma 3 1B", "gemma-3-1b-it"),
    ("Gemma", "Gemma 3 4B", "gemma-3-4b-it"),
    ("Gemma", "Gemma 3 12B", "gemma-3-12b-it"),
    ("Gemma", "Gemma 3 27B", "gemma-3-27b-it"),
    ("Llama", "Llama 3.2 1B", "Llama-3.2-1B-Instruct"),
    ("Llama", "Llama 3.2 3B", "Llama-3.2-3B-Instruct"),
    ("Llama", "Llama 3.1 8B", "Meta-Llama-3.1-8B-Instruct"),
    ("Llama", "Llama 3.1 8B", "Llama-3.1-8B-Instruct"),
    ("Llama", "Llama 3.3 70B", "Llama-3.3-70B-Instruct"),
    ("Llama", "Llama 4 Scout 17B 16E", "Llama-4-Scout-17B-16E-Instruct"),
    ("Phi", "Phi-4 mini", "Phi-4-mini-instruct"),
    ("Phi", "Phi-4", "phi-4"),
    ("Phi", "Phi-4 reasoning plus", "Phi-4-reasoning-plus"),
    ("Mistral", "Ministral 3 3B", "Ministral-3-3B-Instruct-2512"),
    ("Mistral", "Ministral 3 14B Reasoning", "Ministral-3-14B-Reasoning-2512"),
    ("Mistral", "Devstral Small 2 24B", "Devstral-Small-2-24B-Instruct-2512"),
    ("Mistral", "Mistral Small 3.2 24B", "Mistral-Small-3.2-24B-Instruct-2506"),
    ("Mistral", "Mistral Nemo 12B", "Mistral-Nemo-Instruct-2407"),
    ("DeepSeek", "DeepSeek R1 0528 Qwen3 8B", "DeepSeek-R1-0528-Qwen3-8B"),
    ("DeepSeek", "DeepSeek R1 Distill Qwen 7B", "DeepSeek-R1-Distill-Qwen-7B"),
    ("DeepSeek", "DeepSeek R1 Distill Qwen 14B", "DeepSeek-R1-Distill-Qwen-14B"),
    ("DeepSeek", "DeepSeek R1 Distill Qwen 32B", "DeepSeek-R1-Distill-Qwen-32B"),
    ("OpenAI", "gpt-oss 20B", "gpt-oss-20b"),
    ("OpenAI", "gpt-oss 120B", "gpt-oss-120b"),
    ("Zhipu", "GLM 4.7 Flash", "GLM-4.7-Flash"),
    ("NVIDIA", "Nemotron 3 Nano 4B", "NVIDIA-Nemotron-3-Nano-4B"),
    ("NVIDIA", "Nemotron 3.5 Lightning 30B A3B", "NVIDIA-Nemotron-3.5-Lightning-30B-A3B"),
    ("Hugging Face", "SmolLM3 3B", "SmolLM3-3B"),
]

QUANTS = {
    "Q4_K_M": re.compile(r"(?i)[-_.]Q4_K_M(-\d{5}-of-\d{5})?\.gguf$"),
    "Q8_0": re.compile(r"(?i)[-_.]Q8_0(-\d{5}-of-\d{5})?\.gguf$"),
}


def files(c, repo):
    r = c.get(f"https://huggingface.co/api/models/{repo}", params={"blobs": "true"})
    if r.status_code != 200:
        return None, r.status_code
    a = r.json()
    return a, 200


def pick(a, stem=None):
    out = {}
    stem = (stem or "").lower()
    for q in QUANTS:
        # EXACTLY `<stem>-<quant>.gguf` or its split parts, optionally vendor-prefixed
        # (bartowski). A looser match took a 177B model's MTP draft file for the model.
        exact = re.compile(
            rf"(?i)^([a-z0-9-]+_)?{re.escape(stem)}[-.]{q}(-\d{{5}}-of-\d{{5}})?\.gguf$"
        )
        hits = [s for s in a.get("siblings", []) if exact.match(s["rfilename"].rsplit("/", 1)[-1])]
        # one quant can exist at several paths (a folder per quant); keep the shortest path set
        if not hits:
            continue
        by_dir = {}
        for s in hits:
            by_dir.setdefault(
                s["rfilename"].rsplit("/", 1)[0] if "/" in s["rfilename"] else "", []
            ).append(s)
        group = min(by_dir.values(), key=lambda g: len(g[0]["rfilename"]))
        out[q] = {
            "files": sorted(s["rfilename"] for s in group),
            "bytes": sum(s.get("size") or 0 for s in group),
        }
    return out


rows, seen = [], set()
with httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True) as c:
    for fam, label, stem in SEED:
        if label in seen:
            continue
        found = None
        for au in AUTHORS:
            for name in (f"{stem}-GGUF", f"{stem.split('/')[-1]}-GGUF"):
                cands = [f"{au}/{name}"]
                if au == "bartowski":
                    cands.append(None)
                for repo in [x for x in cands if x]:
                    a, st = files(c, repo)
                    time.sleep(0.4)
                    if a is None:
                        continue
                    q = pick(a, stem)
                    if "Q4_K_M" in q:
                        found = {
                            "repo": repo,
                            "gated": a.get("gated"),
                            "base_model": (a.get("cardData") or {}).get("base_model"),
                            "license": (a.get("cardData") or {}).get("license"),
                            "quants": q,
                        }
                        break
                if found:
                    break
            if found:
                break
        if not found:
            # bartowski prefixes the vendor: search instead of guessing the prefix
            r = c.get(
                "https://huggingface.co/api/models",
                params={"author": "bartowski", "search": stem, "limit": 5},
            )
            time.sleep(0.4)
            for m in r.json() if r.status_code == 200 else []:
                if m["id"].lower().endswith(f"_{stem.lower()}-gguf"):
                    a, st = files(c, m["id"])
                    if a and "Q4_K_M" in pick(a, stem):
                        found = {
                            "repo": m["id"],
                            "gated": a.get("gated"),
                            "base_model": (a.get("cardData") or {}).get("base_model"),
                            "license": (a.get("cardData") or {}).get("license"),
                            "quants": pick(a, stem),
                        }
                        break
        rows.append({"family": fam, "label": label, "stem": stem, **(found or {"repo": None})})
        if found:
            seen.add(label)
        q = (found or {}).get("quants", {})
        print(
            f"{label:34} {(found or {}).get('repo') or 'NOT FOUND':52} "
            + " ".join(f"{k}={v['bytes'] / 2**30:.2f}GiB/{len(v['files'])}f" for k, v in q.items())
        )
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)
