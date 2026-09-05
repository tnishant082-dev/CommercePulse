#!/usr/bin/env python3
"""Deterministic golden-question checks for the insights assistant."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ai.rag.retrieve import answer, retrieve

CASES = json.loads((Path(__file__).parent / "cases.json").read_text())


def main() -> int:
    passed = 0
    for case in CASES:
        hits = retrieve(case["question"], k=4)
        out = answer(case["question"], k=4)
        top = hits[0]["score"] if hits else 0.0
        text = out["answer"]
        ok_score = top >= case["min_top_score"]
        ok_text = any(tok.lower() in text.lower() for tok in case["must_include_any"])
        ok = ok_score and ok_text
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['id']}  top_score={top:.3f}")
        if not ok:
            print("  answer snippet:", text[:240].replace("\n", " "))
            print("  expected any of:", case["must_include_any"])
        else:
            passed += 1
    print(f"{passed}/{len(CASES)} passed")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
