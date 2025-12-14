"""Test configuration: ensure the `src` package is importable."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Provide defaults for required settings so importing the app doesn't require
# developer-specific environment configuration during tests.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

# Ensure both the project root and the src directory are importable so that
# `src.*` modules and top-level packages under `src/` can be resolved.
for path in (PROJECT_ROOT, SRC_PATH):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
