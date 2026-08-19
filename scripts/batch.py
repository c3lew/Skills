#!/usr/bin/env python3
"""Repo entry point for the batch planner shipped inside skills/build-batch.

The implementation lives in the skill dir because install copies only that dir
— a planner sitting in scripts/ would be missing on every machine that
installed the skill. This file is here so the repo's own check reads like the
others: `python scripts/batch.py --self-check`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "build-batch"))
from batch import self_check  # noqa: E402

if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    print(__doc__)
