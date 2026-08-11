#!/usr/bin/env python3
"""RFM + k-means customer segmentation.

Trying k=3..6 on silhouette, then pick something interpretable (often 4).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "gold"
OUT = ROOT / "python" / "outputs"
REPORTS = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)


def main():
    feat = pd.read_csv(GOLD / "ml_customer_features.csv")
    # skip guest checkouts — no CustomerID to segment on
    feat = feat[feat["CustomerKey"] > 0].copy()
    cols = ["RecencyDays", "Frequency", "Monetary"]
    X = feat[cols].copy()
    # log1p helps when Monetary/Frequency are skewed (common with RFM)
    X["Monetary_log"] = np.log1p(X["Monetary"])
    X["Frequency_log"] = np.log1p(X["Frequency"])
    use = ["RecencyDays", "Frequency_log", "Monetary_log"]
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X[use])

    # try a few k values — silhouette on a sample so it runs faster
    sample_idx = np.random.RandomState(42).choice(len(Xs), size=min(4000, len(Xs)), replace=False)
    silhouettes = {}
    for k in range(3, 7):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(Xs[sample_idx])
        silhouettes[k] = float(silhouette_score(Xs[sample_idx], labels))
    best_k = max(silhouettes, key=silhouettes.get)
    # if 4 is close to the best score, keep 4 (easier labels)
    if silhouettes.get(4, 0) >= silhouettes[best_k] - 0.02:
        best_k = 4

    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    feat["Cluster"] = km.fit_predict(Xs)
    full_sil = float(silhouette_score(Xs, feat["Cluster"]))
    print(f"fitted k={best_k}  silhouette={full_sil:.3f}  n={len(feat)}")

    # rough labels from median RFM — not perfect, but readable
    summary = feat.groupby("Cluster").agg(
        Customers=("CustomerKey", "count"),
        RecencyDays=("RecencyDays", "median"),
        Frequency=("Frequency", "median"),
        Monetary=("Monetary", "median"),
        Revenue=("Monetary", "sum"),
        RepeatRate=("IsRepeat", "mean"),
        Churn90Rate=("Churned90", "mean"),
    ).reset_index()

    def name_row(r):
        # Champions: low recency, high freq/monetary
        if r["RecencyDays"] <= summary["RecencyDays"].median() and r["Monetary"] >= summary["Monetary"].median() and r["Frequency"] >= summary["Frequency"].median():
            return "Champions"
        if r["RecencyDays"] > summary["RecencyDays"].quantile(0.6) and r["Frequency"] <= summary["Frequency"].median():
            return "At Risk"
        if r["Frequency"] <= summary["Frequency"].quantile(0.4) and r["RecencyDays"] <= summary["RecencyDays"].median():
            return "New / Promising"
        if r["Monetary"] >= summary["Monetary"].median():
            return "Loyal Spenders"
        return "Need Attention"

    summary["Segment"] = summary.apply(name_row, axis=1)
    # ensure unique names
    seen = {}
    names = []
    for s in summary["Segment"]:
        if s not in seen:
            seen[s] = 0
            names.append(s)
        else:
            seen[s] += 1
            names.append(f"{s} ({seen[s]+1})")
    summary["Segment"] = names
    seg_map = dict(zip(summary["Cluster"], summary["Segment"]))
    feat["Segment"] = feat["Cluster"].map(seg_map)

    feat.to_csv(GOLD / "customer_segments.csv", index=False)
    summary.to_csv(OUT / "segment_summary.csv", index=False)

    # chart
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.patch.set_facecolor("#1B1A19")
    colors = ["#F2C811", "#60A5FA", "#2DD4BF", "#F87171", "#A78BFA", "#FB923C"]
    ax = axes[0]
    ax.set_facecolor("#252423")
    for i, c in enumerate(sorted(feat["Cluster"].unique())):
        sub = feat[feat["Cluster"] == c]
        ax.scatter(sub["RecencyDays"], np.log1p(sub["Monetary"]), s=12, alpha=0.45, c=colors[i % len(colors)], label=seg_map[c])
    ax.set_xlabel("Recency (days)", color="#94A3B8")
    ax.set_ylabel("log(1+Monetary)", color="#94A3B8")
    ax.tick_params(colors="#94A3B8")
    ax.set_title("RFM clusters", color="#F8FAFC", loc="left")
    ax.legend(facecolor="#252423", edgecolor="#40403D", labelcolor="#F8FAFC", fontsize=8)
    for sp in ax.spines.values():
        sp.set_color("#40403D")

    ax2 = axes[1]
    ax2.set_facecolor("#252423")
    order = summary.sort_values("Revenue", ascending=True)
    ax2.barh(order["Segment"], order["Revenue"] / 1e6, color="#F2C811")
    ax2.set_xlabel("Revenue (£M)", color="#94A3B8")
    ax2.tick_params(colors="#94A3B8")
    ax2.set_title("Segment revenue contribution", color="#F8FAFC", loc="left")
    for sp in ax2.spines.values():
        sp.set_color("#40403D")
    fig.tight_layout()
    fig.savefig(OUT / "customer_segments.png", dpi=140, facecolor=fig.get_facecolor())
    plt.close()

    metrics = {
        "model": "KMeans RFM",
        "features": use,
        "k": int(best_k),
        "silhouette_k_sweep": silhouettes,
        "silhouette_full": round(full_sil, 4),
        "n_customers": int(len(feat)),
        "segments": summary.to_dict(orient="records"),
        "notes": "Segments named from median RFM profile; silhouette used to choose k (prefer 4 when close).",
    }
    (REPORTS / "segmentation_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    print(json.dumps({"k": best_k, "silhouette": round(full_sil, 4), "segments": list(summary["Segment"])}, indent=2))


if __name__ == "__main__":
    main()
