#!/usr/bin/env python3
"""Retrieve top-k gold facts for a natural-language question."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[2]
IDX = ROOT / "ai" / "rag" / "index" / "tfidf.joblib"


def load():
    return joblib.load(IDX)


def retrieve(question: str, k: int = 4):
    blob = load()
    q = blob["vectorizer"].transform([question])
    sims = cosine_similarity(q, blob["matrix"]).ravel()
    order = sims.argsort()[::-1][:k]
    hits = []
    for i in order:
        d = dict(blob["docs"][i])
        d["score"] = float(sims[i])
        hits.append(d)
    return hits


def answer(question: str, k: int = 4) -> dict:
    hits = retrieve(question, k=k)
    # stitch a grounded reply from retrieved gold facts
    if not hits or hits[0]["score"] < 0.02:
        return {
            "question": question,
            "answer": "Not enough overlap with the indexed gold metrics. Try asking about revenue, UK mix, returns, segments, or a specific month (YYYY-MM).",
            "sources": [],
            "sql": None,
        }
    lines = [f"Based on the CommercePulse gold marts:"]
    for h in hits[:3]:
        lines.append(f"- ({h['title']}) {h['text']}")
    sql = hits[0].get("sql")
    return {
        "question": question,
        "answer": "\n".join(lines),
        "sources": [{"id": h["id"], "title": h["title"], "score": round(h["score"], 4)} for h in hits],
        "sql": sql,
    }


def main():
    ap = argparse.ArgumentParser(description="CommercePulse insights retrieval")
    ap.add_argument("question", nargs="?", default="Why did UK revenue change?")
    ap.add_argument("-k", type=int, default=4)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = answer(args.question, k=args.k)
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(out["answer"])
        print("\nSources:", ", ".join(s["id"] for s in out["sources"]))
        if out.get("sql"):
            print("SQL:", out["sql"])


if __name__ == "__main__":
    main()
