"""Pixel-compare a re-rendered carousel with the approved one.
Usage: python compare_pages.py <approved_dir> <new_dir> <prefix> <pages>"""
import sys
from pathlib import Path

from PIL import Image, ImageChops

a_dir, b_dir, prefix, pages = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
same = True
for i in range(1, pages + 1):
    a = Image.open(a_dir / f"{prefix}-p{i}.png").convert("RGB")
    b = Image.open(b_dir / f"{prefix}-p{i}.png").convert("RGB")
    if a.size != b.size:
        print(f"p{i}: size differs {a.size} vs {b.size}")
        same = False
        continue
    box = ImageChops.difference(a, b).getbbox()
    print(f"p{i}: {'identical' if box is None else f'differs in {box}'}")
    same = same and box is None
sys.exit(0 if same else 1)
