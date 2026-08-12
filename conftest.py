"""Make the repo importable without an install step.

pytest inserts this file's directory at the front of sys.path, so `collect`
and `judge` import from the working tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
