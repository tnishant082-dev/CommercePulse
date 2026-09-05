#!/usr/bin/env python3
"""Build a local TF-IDF retrieval index over gold metrics + mart summaries."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "gold"
AI = ROOT / "ai"
IDX = AI / "rag" / "index"


def docs_from_gold() -> list[dict]:
    docs = []
    kpi = json.loads((GOLD / "metrics_summary.json").read_text())
    docs.append({
        "id": "kpi_overview",
        "title": "Executive KPI overview",
        "text": (
            f"Overall revenue is £{kpi['revenue']:,.2f} across {kpi['orders']:,} orders "
            f"and {kpi['customers']:,} registered customers. Average order value is £{kpi['aov']:.2f}. "
            f"Period runs {kpi['period_start']} to {kpi['period_end']}. "
            f"UK revenue share is {kpi['uk_revenue_share']*100:.1f}% (£{kpi['uk_revenue']:,.2f}). "
            f"Return rate is {kpi['return_rate']*100:.2f}% by value. "
            f"Guest checkout lines are {kpi['guest_line_share']*100:.1f}% of sales lines. "
            f"Calendar 2010→2011 revenue change is {kpi['revenue_yoy']*100:.2f}%, "
            f"orders {kpi['orders_yoy']*100:.2f}%, customers {kpi['customers_yoy']*100:.2f}%."
        ),
        "sql": "SELECT ROUND(SUM(LineAmount),2) AS Revenue, COUNT(DISTINCT Invoice) AS Orders FROM v_fact_sales;",
    })

    monthly = pd.read_csv(GOLD / "mart_monthly.csv")
    # find peak / soft months
    peak = monthly.loc[monthly["Revenue"].idxmax()]
    soft = monthly.loc[monthly["Revenue"].idxmin()]
    docs.append({
        "id": "monthly_seasonality",
        "title": "Monthly seasonality",
        "text": (
            f"Monthly revenue peaks in {peak['YearMonth']} at £{peak['Revenue']:,.0f} "
            f"({int(peak['Orders'])} orders). Softest month in the series is {soft['YearMonth']} "
            f"at £{soft['Revenue']:,.0f}. November gift-season peaks appear in both 2010 and 2011."
        ),
        "sql": "SELECT YearMonth, Revenue, Orders FROM v_mart_monthly ORDER BY Revenue DESC LIMIT 5;",
    })

    # UK specifically + YoY nuance
    docs.append({
        "id": "uk_revenue",
        "title": "United Kingdom revenue",
        "text": (
            f"United Kingdom contributes £{kpi['uk_revenue']:,.2f} "
            f"({kpi['uk_revenue_share']*100:.1f}% of total revenue). "
            f"Across calendar 2010 vs 2011, total revenue moved {kpi['revenue_yoy']*100:.2f}% "
            f"(£{kpi['revenue_2010_overlap']:,.0f} → £{kpi['revenue_2011_overlap']:,.0f}) while AOV rose "
            f"from £{kpi['aov_2010']:.2f} to £{kpi['aov_2011']:.2f}. "
            f"A UK 'drop' question should be checked against the monthly mart, not only the full-period total — "
            f"seasonality and Dec partial months matter."
        ),
        "sql": "SELECT Country, ROUND(SUM(LineAmount),2) AS Revenue FROM v_fact_sales WHERE Country='United Kingdom';",
    })

    countries = pd.read_csv(GOLD / "mart_country.csv").head(10)
    lines = []
    for _, r in countries.iterrows():
        lines.append(f"{r['Country']}: £{r['Revenue']:,.0f} revenue, {int(r['Orders']):,} orders")
    docs.append({
        "id": "top_countries",
        "title": "Top countries by revenue",
        "text": "Top markets by revenue — " + "; ".join(lines) + ".",
        "sql": "SELECT Country, SUM(LineAmount) AS Revenue FROM v_fact_sales GROUP BY Country ORDER BY Revenue DESC LIMIT 10;",
    })

    products = pd.read_csv(GOLD / "mart_top_products.csv").head(10)
    plines = [f"{r['Description'][:40]} (£{r['Revenue']:,.0f})" for _, r in products.iterrows()]
    docs.append({
        "id": "top_products",
        "title": "Top products by revenue",
        "text": "Highest revenue SKUs: " + "; ".join(plines) + f". Top-5 SKUs are {kpi['top5_product_revenue_share']*100:.1f}% of revenue.",
        "sql": "SELECT StockCode, SUM(LineAmount) AS Revenue FROM v_fact_sales GROUP BY StockCode ORDER BY Revenue DESC LIMIT 10;",
    })

    segs = pd.read_csv(ROOT / "python" / "outputs" / "segment_summary.csv")
    slines = [f"{r['Segment']}: {int(r['Customers'])} customers, £{r['Revenue']:,.0f} revenue" for _, r in segs.iterrows()]
    docs.append({
        "id": "segments",
        "title": "RFM customer segments",
        "text": (
            f"Registered customers split into {len(segs)} RFM segments. "
            + "; ".join(slines) + f". Overall repeat rate is {kpi['repeat_customer_rate']*100:.1f}% "
            f"and end-window Churned90 rate is {kpi['churned_90_rate']*100:.1f}%."
        ),
        "sql": "-- see data/gold/customer_segments.csv",
    })

    docs.append({
        "id": "returns",
        "title": "Returns and cancellations",
        "text": (
            f"Return value is £{kpi['return_amount']:,.2f}, a {kpi['return_rate']*100:.2f}% rate versus sales value. "
            "Returns include C-prefix cancels and negative quantity lines; fee codes are excluded."
        ),
        "sql": "SELECT ROUND(SUM(ReturnAmount)/(SELECT SUM(LineAmount) FROM v_fact_sales),4) AS return_rate FROM v_fact_returns;",
    })

    # month-level UK proxy using overall monthly (we don't have UK monthly in gold easily — build quick)
    # add a few monthly facts as individual docs for retrieval granularity
    for _, r in monthly.iterrows():
        docs.append({
            "id": f"month_{r['YearMonth']}",
            "title": f"Month {r['YearMonth']}",
            "text": (
                f"In {r['YearMonth']}, revenue was £{r['Revenue']:,.2f} from {int(r['Orders'])} orders "
                f"and {int(r['Customers'])} customers. AOV £{r['AOV']:.2f}, units {int(r['Units']):,}."
            ),
            "sql": f"SELECT * FROM v_mart_monthly WHERE YearMonth='{r['YearMonth']}';",
        })
    return docs


def main():
    IDX.mkdir(parents=True, exist_ok=True)
    docs = docs_from_gold()
    corpus = [d["text"] for d in docs]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
    matrix = vec.fit_transform(corpus)
    joblib.dump({"vectorizer": vec, "matrix": matrix, "docs": docs}, IDX / "tfidf.joblib")
    (IDX / "documents.json").write_text(json.dumps(docs, indent=2))
    print(f"indexed {len(docs)} docs → {IDX/'tfidf.joblib'}")


if __name__ == "__main__":
    main()
