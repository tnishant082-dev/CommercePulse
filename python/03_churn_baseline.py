#!/usr/bin/env python3
"""Churn / repurchase baseline on customer RFM-ish features.

Learning notes:
- start with logistic regression as a baseline
- try GBM after as a quick comparison (not the "main" model yet)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    mean_absolute_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "gold"
OUT = ROOT / "python" / "outputs"
REPORTS = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    print("loading ml_customer_features…")
    feat = pd.read_csv(GOLD / "ml_customer_features.csv")
    feat = feat[feat["CustomerKey"] > 0].copy()
    print(f"customers (registered): {len(feat)}")

    # --- Churned90 = no purchase in last 90 days of the window ---
    # note: leakage risk if we include Recency — dropped
    churn_cols = ["Frequency", "Monetary", "AvgOrderValue", "AvgBasketSize", "TenureDays"]
    Xc = feat[churn_cols].fillna(0)
    yc = feat["Churned90"].astype(int)

    # simple train/test split (stratify so base rate stays similar)
    Xtr, Xte, ytr, yte = train_test_split(
        Xc, yc, test_size=0.25, random_state=42, stratify=yc
    )
    print(f"train={len(Xtr)}  test={len(Xte)}  base_rate={yc.mean():.3f}")

    # start with logistic regression as a baseline
    scaler = StandardScaler()
    Xtr_s = scaler.fit_transform(Xtr)
    Xte_s = scaler.transform(Xte)

    logit = LogisticRegression(max_iter=500, random_state=42)
    logit.fit(Xtr_s, ytr)
    proba_l = logit.predict_proba(Xte_s)[:, 1]
    pred_l = (proba_l >= 0.5).astype(int)

    lr_acc = float(accuracy_score(yte, pred_l))
    lr_auc = float(roc_auc_score(yte, proba_l))
    print(f"LogisticRegression  accuracy={lr_acc:.4f}  AUC={lr_auc:.4f}")

    # experiment: GBM (optional comparison — usually a bit better)
    print("trying GradientBoosting as a quick experiment…")
    gbc = GradientBoostingClassifier(
        random_state=42, max_depth=3, n_estimators=120, learning_rate=0.08
    )
    gbc.fit(Xtr, ytr)
    proba_g = gbc.predict_proba(Xte)[:, 1]
    pred_g = (proba_g >= 0.5).astype(int)
    gb_acc = float(accuracy_score(yte, pred_g))
    gb_auc = float(roc_auc_score(yte, proba_g))
    print(f"GradientBoosting    accuracy={gb_acc:.4f}  AUC={gb_auc:.4f}")

    churn_metrics = {
        "target": "Churned90 (no purchase in last 90 days of observation window)",
        "features": churn_cols,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "base_rate": round(float(yc.mean()), 4),
        "logistic_regression": {
            "accuracy": round(lr_acc, 4),
            "auc": round(lr_auc, 4),
        },
        "gradient_boosting": {
            "accuracy": round(gb_acc, 4),
            "auc": round(gb_auc, 4),
            "feature_importance": {
                c: round(float(v), 4) for c, v in zip(churn_cols, gbc.feature_importances_)
            },
            "note": "optional comparison — not the primary baseline",
        },
        "limitations": [
            "Label is window-end inactivity, not a true future holdout churn event.",
            "Recency intentionally excluded from features to avoid trivial leakage.",
            "Guest checkouts excluded; UK-heavy mix may not transfer to other markets.",
        ],
    }

    # --- next-order value baseline (customers with 2+ orders) ---
    print("AOV baseline (customers with Frequency >= 2)…")
    rep = feat[feat["Frequency"] >= 2].copy()
    Xr = rep[["Frequency", "TenureDays", "AvgBasketSize", "RecencyDays"]].fillna(0)
    yr = rep["AvgOrderValue"]
    Xtr2, Xte2, ytr2, yte2 = train_test_split(Xr, yr, test_size=0.25, random_state=42)
    gbr = GradientBoostingRegressor(
        random_state=42, max_depth=3, n_estimators=120, learning_rate=0.08
    )
    gbr.fit(Xtr2, ytr2)
    pred_r = gbr.predict(Xte2)
    naive = np.full_like(yte2, ytr2.mean(), dtype=float)
    aov_metrics = {
        "target": "AvgOrderValue (customers with 2+ orders)",
        "features": list(Xr.columns),
        "n_train": int(len(Xtr2)),
        "n_test": int(len(Xte2)),
        "mae": round(float(mean_absolute_error(yte2, pred_r)), 2),
        "r2": round(float(r2_score(yte2, pred_r)), 4),
        "naive_mean_mae": round(float(mean_absolute_error(yte2, naive)), 2),
        "mean_aov_test": round(float(yte2.mean()), 2),
        "limitations": [
            "AOV is historical average, not a true next-order forecast.",
            "No product-mix or seasonality features in this baseline.",
        ],
    }
    print(f"AOV MAE={aov_metrics['mae']}  (naive mean MAE={aov_metrics['naive_mean_mae']})")

    # monthly revenue seasonal-naive (lag-12)
    monthly = pd.read_csv(GOLD / "mart_monthly.csv").sort_values("YearMonth")
    monthly["RevLag1"] = monthly["Revenue"].shift(1)
    monthly["RevLag12"] = monthly["Revenue"].shift(12)
    m2 = monthly.dropna(subset=["RevLag1"]).copy()
    m2["Forecast"] = m2["RevLag12"].fillna(m2["RevLag1"])
    eval_m = m2.dropna(subset=["Forecast"])
    eval12 = monthly.dropna(subset=["RevLag12"])
    if len(eval12) >= 3:
        mae_m = float(mean_absolute_error(eval12["Revenue"], eval12["RevLag12"]))
        mape = float(
            np.mean(np.abs((eval12["Revenue"] - eval12["RevLag12"]) / eval12["Revenue"])) * 100
        )
        n_eval = len(eval12)
    else:
        mae_m = float(mean_absolute_error(eval_m["Revenue"], eval_m["Forecast"]))
        mape = float(
            np.mean(np.abs((eval_m["Revenue"] - eval_m["Forecast"]) / eval_m["Revenue"])) * 100
        )
        n_eval = len(eval_m)
    demand_metrics = {
        "model": "Seasonal naive (lag-12 months) where available; else lag-1",
        "mae_revenue": round(mae_m, 2),
        "mape_pct": round(mape, 2),
        "n_eval_months": int(n_eval),
        "limitations": [
            "Baseline only — no holiday regressors or promo calendar.",
            "Short series (~25 months) limits model complexity.",
        ],
    }
    print(f"Demand MAPE={demand_metrics['mape_pct']}%")

    out = {
        "churn": churn_metrics,
        "aov_baseline": aov_metrics,
        "demand_baseline": demand_metrics,
    }
    (REPORTS / "model_metrics.json").write_text(json.dumps(out, indent=2))
    print("wrote reports/model_metrics.json")

    # score mix chart — show LR scores (hero baseline)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.patch.set_facecolor("#1B1A19")
    ax = axes[0]
    ax.set_facecolor("#252423")
    ax.hist(proba_l[yte.values == 0], bins=20, alpha=0.65, color="#2DD4BF", label="Active", density=True)
    ax.hist(proba_l[yte.values == 1], bins=20, alpha=0.65, color="#F87171", label="Churned90", density=True)
    ax.set_title(f"LR churn scores  ·  AUC {lr_auc:.3f}", color="#F8FAFC", loc="left")
    ax.set_xlabel("Predicted P(churn)", color="#94A3B8")
    ax.tick_params(colors="#94A3B8")
    ax.legend(facecolor="#252423", labelcolor="#F8FAFC", edgecolor="#40403D")
    for sp in ax.spines.values():
        sp.set_color("#40403D")

    ax2 = axes[1]
    ax2.set_facecolor("#252423")
    # show GBM importances as the experiment side panel
    imps = churn_metrics["gradient_boosting"]["feature_importance"]
    keys = list(imps.keys())
    vals = [imps[k] for k in keys]
    ax2.barh(keys, vals, color="#F2C811")
    ax2.set_title("GBM feature importance (experiment)", color="#F8FAFC", loc="left")
    ax2.tick_params(colors="#94A3B8")
    for sp in ax2.spines.values():
        sp.set_color("#40403D")
    fig.tight_layout()
    fig.savefig(OUT / "churn_baseline.png", dpi=140, facecolor=fig.get_facecolor())
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("#1B1A19")
    ax.set_facecolor("#252423")
    ax.plot(monthly["YearMonth"], monthly["Revenue"] / 1e6, color="#F2C811", marker="o", markersize=3, label="Actual")
    ax.plot(monthly["YearMonth"], monthly["RevLag12"] / 1e6, color="#60A5FA", linestyle="--", label="Seasonal naive")
    ax.set_title("Monthly revenue vs seasonal-naive baseline", color="#F8FAFC", loc="left")
    ax.tick_params(colors="#94A3B8", axis="x", labelrotation=45, labelsize=7)
    ax.tick_params(colors="#94A3B8", axis="y")
    ax.set_ylabel("£M", color="#94A3B8")
    ax.legend(facecolor="#252423", labelcolor="#F8FAFC", edgecolor="#40403D")
    for sp in ax.spines.values():
        sp.set_color("#40403D")
    fig.tight_layout()
    fig.savefig(OUT / "demand_baseline.png", dpi=140, facecolor=fig.get_facecolor())
    plt.close()

    print("--- summary ---")
    print(f"LR  AUC={lr_auc:.3f}  Acc={lr_acc:.3f}")
    print(f"GB  AUC={gb_auc:.3f}  Acc={gb_acc:.3f}  (experiment)")
    print(f"Demand MAPE={demand_metrics['mape_pct']}%")


if __name__ == "__main__":
    main()
