#!/usr/bin/env python3
"""CommercePulse medallion pipeline — Online Retail II → bronze/silver/gold."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SRC = Path("/workspace/RetailExecutiveDashboard-push/data/online_retail_II.xlsx")
FEE_CODES = {"POST", "DOT", "M", "D", "AMAZONFEE", "BANK CHARGES", "CRUK", "PADS", "B"}

RAW = DATA / "raw"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
GOLD = DATA / "gold"
REPORTS = ROOT / "reports"


def log(msg: str) -> None:
    print(msg, flush=True)


def load_raw() -> pd.DataFrame:
    RAW.mkdir(parents=True, exist_ok=True)
    note = RAW / "SOURCE.txt"
    note.write_text(
        "Online Retail II (UCI Machine Learning Repository)\n"
        "Chen, D. (2012). Online Retail II.\n"
        "https://archive.ics.uci.edu/dataset/502/online+retail+ii\n"
        "Period: Dec 2009 – Dec 2011 · UK-based online gift retailer\n"
        "Local copy: online_retail_II.xlsx (both year sheets)\n"
        "Full workbook retained under data/raw/ for reproducibility.\n"
    )
    if not (RAW / "online_retail_II.xlsx").exists():
        log("Copying source workbook into data/raw/ …")
        shutil.copy2(SRC, RAW / "online_retail_II.xlsx")
    log("Reading Year 2009-2010 …")
    y1 = pd.read_excel(RAW / "online_retail_II.xlsx", sheet_name="Year 2009-2010")
    log("Reading Year 2010-2011 …")
    y2 = pd.read_excel(RAW / "online_retail_II.xlsx", sheet_name="Year 2010-2011")
    y1["SourceSheet"] = "2009-2010"
    y2["SourceSheet"] = "2010-2011"
    df = pd.concat([y1, y2], ignore_index=True)
    log(f"Raw rows combined: {len(df):,}")
    return df


def to_bronze(df: pd.DataFrame) -> pd.DataFrame:
    BRONZE.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    # normalize column names once
    out.columns = [c.strip().replace(" ", "") for c in out.columns]
    if "CustomerID" not in out.columns and "CustomerID" not in out.columns:
        # original has "Customer ID"
        pass
    rename = {}
    for c in list(out.columns):
        cl = c.lower()
        if cl in ("customerid", "customer_id"):
            rename[c] = "CustomerID"
        elif cl == "invoicedate":
            rename[c] = "InvoiceDate"
        elif cl == "stockcode":
            rename[c] = "StockCode"
        elif cl == "invoice":
            rename[c] = "Invoice"
        elif cl == "description":
            rename[c] = "Description"
        elif cl == "quantity":
            rename[c] = "Quantity"
        elif cl in ("price", "unitprice"):
            rename[c] = "Price"
        elif cl == "country":
            rename[c] = "Country"
        elif cl == "sourcesheet":
            rename[c] = "SourceSheet"
    out = out.rename(columns=rename)
    # handle Customer ID with space from excel
    if "CustomerID" not in out.columns:
        for c in df.columns:
            if "customer" in c.lower():
                out["CustomerID"] = df[c]
                break
    out["Invoice"] = out["Invoice"].astype(str).str.strip()
    out["StockCode"] = out["StockCode"].astype(str).str.strip()
    out["Description"] = out["Description"].astype(str).str.strip()
    out["Country"] = out["Country"].astype(str).str.strip()
    out["InvoiceDate"] = pd.to_datetime(out["InvoiceDate"], errors="coerce")
    out["Quantity"] = pd.to_numeric(out["Quantity"], errors="coerce")
    out["Price"] = pd.to_numeric(out["Price"], errors="coerce")
    out["CustomerID"] = pd.to_numeric(out["CustomerID"], errors="coerce")
    out["IsCancel"] = out["Invoice"].str.upper().str.startswith("C").astype(int)
    out["IsFeeCode"] = out["StockCode"].isin(FEE_CODES).astype(int)
    out["LineAmount"] = out["Quantity"] * out["Price"]
    n_before = len(out)
    out = out.drop_duplicates()
    log(f"Bronze: dropped {n_before - len(out):,} exact dupes → {len(out):,} rows")
    out.to_parquet(BRONZE / "transactions.parquet", index=False)
    # also a manageable csv sample for quick peeks
    out.head(5000).to_csv(BRONZE / "transactions_sample.csv", index=False)
    return out


def to_silver(bronze: pd.DataFrame) -> dict[str, pd.DataFrame]:
    SILVER.mkdir(parents=True, exist_ok=True)
    # sales lines = positive qty/price, not cancel, not fee, has description
    sales = bronze[
        (bronze["IsCancel"] == 0)
        & (bronze["Quantity"] > 0)
        & (bronze["Price"] > 0)
        & (bronze["Description"].notna())
        & (bronze["Description"].str.len() > 0)
        & (bronze["Description"] != "nan")
        & (bronze["IsFeeCode"] == 0)
        & (bronze["InvoiceDate"].notna())
    ].copy()
    sales["IsGuest"] = sales["CustomerID"].isna().astype(int)

    returns = bronze[
        ((bronze["IsCancel"] == 1) | (bronze["Quantity"] < 0))
        & (bronze["InvoiceDate"].notna())
        & (bronze["IsFeeCode"] == 0)
    ].copy()
    returns["ReturnQty"] = returns["Quantity"].abs()
    returns["ReturnAmount"] = (returns["Quantity"].abs() * returns["Price"].abs())

    customers = (
        sales[sales["CustomerID"].notna()]
        .groupby("CustomerID", as_index=False)
        .agg(
            FirstPurchase=("InvoiceDate", "min"),
            LastPurchase=("InvoiceDate", "max"),
            Orders=("Invoice", "nunique"),
            Revenue=("LineAmount", "sum"),
            Lines=("Invoice", "count"),
            Country=("Country", lambda s: s.mode().iloc[0] if len(s.mode()) else s.iloc[0]),
        )
    )
    customers["CustomerID"] = customers["CustomerID"].astype(int)

    products = (
        sales.groupby("StockCode", as_index=False)
        .agg(
            Description=("Description", lambda s: s.mode().iloc[0] if len(s.mode()) else s.iloc[0]),
            Orders=("Invoice", "nunique"),
            Units=("Quantity", "sum"),
            Revenue=("LineAmount", "sum"),
            AvgPrice=("Price", "mean"),
        )
    )

    invoices = (
        sales.groupby("Invoice", as_index=False)
        .agg(
            InvoiceDate=("InvoiceDate", "min"),
            CustomerID=("CustomerID", "first"),
            Country=("Country", "first"),
            Lines=("StockCode", "count"),
            Units=("Quantity", "sum"),
            Revenue=("LineAmount", "sum"),
            IsGuest=("IsGuest", "max"),
        )
    )

    sales.to_parquet(SILVER / "sales_lines.parquet", index=False)
    returns.to_parquet(SILVER / "returns_lines.parquet", index=False)
    customers.to_parquet(SILVER / "customers.parquet", index=False)
    products.to_parquet(SILVER / "products.parquet", index=False)
    invoices.to_parquet(SILVER / "invoices.parquet", index=False)
    # csv mirrors for BI tooling that prefers csv
    customers.to_csv(SILVER / "customers.csv", index=False)
    products.to_csv(SILVER / "products.csv", index=False)
    invoices.to_csv(SILVER / "invoices.csv", index=False)
    log(f"Silver sales lines: {len(sales):,} | returns: {len(returns):,} | customers: {len(customers):,} | products: {len(products):,}")
    return {
        "sales": sales,
        "returns": returns,
        "customers": customers,
        "products": products,
        "invoices": invoices,
    }


def to_gold(silver: dict[str, pd.DataFrame]) -> dict:
    GOLD.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    sales = silver["sales"]
    returns = silver["returns"]
    customers = silver["customers"]
    products = silver["products"]

    # DimDate
    dates = pd.date_range(sales["InvoiceDate"].min().normalize(), sales["InvoiceDate"].max().normalize(), freq="D")
    dim_date = pd.DataFrame({"Date": dates})
    dim_date["DateKey"] = dim_date["Date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["Year"] = dim_date["Date"].dt.year
    dim_date["Month"] = dim_date["Date"].dt.month
    dim_date["MonthName"] = dim_date["Date"].dt.strftime("%b")
    dim_date["YearMonth"] = dim_date["Date"].dt.strftime("%Y-%m")
    dim_date["Quarter"] = "Q" + dim_date["Date"].dt.quarter.astype(str)
    dim_date["DayOfWeek"] = dim_date["Date"].dt.day_name()
    dim_date["IsWeekend"] = dim_date["Date"].dt.dayofweek.isin([5, 6]).astype(int)

    # DimCustomer
    dim_customer = customers.copy()
    dim_customer["CustomerKey"] = np.arange(1, len(dim_customer) + 1)
    # guest pseudo key
    guest_row = pd.DataFrame([{
        "CustomerID": -1,
        "FirstPurchase": pd.NaT,
        "LastPurchase": pd.NaT,
        "Orders": 0,
        "Revenue": 0.0,
        "Lines": 0,
        "Country": "Guest",
        "CustomerKey": 0,
    }])
    dim_customer = pd.concat([guest_row, dim_customer], ignore_index=True)

    # DimProduct
    dim_product = products.copy()
    dim_product["ProductKey"] = np.arange(1, len(dim_product) + 1)

    # DimCountry
    countries = sorted(sales["Country"].dropna().unique())
    dim_country = pd.DataFrame({"Country": countries})
    dim_country["CountryKey"] = np.arange(1, len(dim_country) + 1)

    # FactSales (invoice-line grain, with keys)
    cust_map = dim_customer.set_index("CustomerID")["CustomerKey"].to_dict()
    prod_map = dim_product.set_index("StockCode")["ProductKey"].to_dict()
    ctry_map = dim_country.set_index("Country")["CountryKey"].to_dict()

    fact = sales.copy()
    fact["DateKey"] = fact["InvoiceDate"].dt.strftime("%Y%m%d").astype(int)
    fact["CustomerKey"] = fact["CustomerID"].map(cust_map).fillna(0).astype(int)
    fact["ProductKey"] = fact["StockCode"].map(prod_map).astype(int)
    fact["CountryKey"] = fact["Country"].map(ctry_map).astype(int)
    fact["SalesKey"] = np.arange(1, len(fact) + 1)
    fact_sales = fact[[
        "SalesKey", "DateKey", "CustomerKey", "ProductKey", "CountryKey",
        "Invoice", "StockCode", "Quantity", "Price", "LineAmount", "IsGuest", "InvoiceDate",
    ]].copy()

    # FactReturns
    fact_ret = returns.copy()
    fact_ret["DateKey"] = fact_ret["InvoiceDate"].dt.strftime("%Y%m%d").astype(int)
    fact_ret["CustomerKey"] = fact_ret["CustomerID"].map(cust_map).fillna(0).astype(int)
    fact_ret["ProductKey"] = fact_ret["StockCode"].map(prod_map)
    fact_ret = fact_ret[fact_ret["ProductKey"].notna()].copy()
    fact_ret["ProductKey"] = fact_ret["ProductKey"].astype(int)
    fact_ret["CountryKey"] = fact_ret["Country"].map(ctry_map).fillna(0).astype(int)
    fact_ret["ReturnKey"] = np.arange(1, len(fact_ret) + 1)
    fact_returns = fact_ret[[
        "ReturnKey", "DateKey", "CustomerKey", "ProductKey", "CountryKey",
        "Invoice", "StockCode", "ReturnQty", "ReturnAmount", "InvoiceDate",
    ]].copy()

    # Monthly mart for charts
    monthly = (
        fact_sales.assign(YearMonth=fact_sales["InvoiceDate"].dt.strftime("%Y-%m"))
        .groupby("YearMonth", as_index=False)
        .agg(
            Revenue=("LineAmount", "sum"),
            Orders=("Invoice", "nunique"),
            Customers=("CustomerKey", lambda s: s[s > 0].nunique()),
            Units=("Quantity", "sum"),
            Lines=("SalesKey", "count"),
        )
    )
    monthly["AOV"] = monthly["Revenue"] / monthly["Orders"]

    country_mart = (
        fact_sales.groupby("CountryKey", as_index=False)
        .agg(Revenue=("LineAmount", "sum"), Orders=("Invoice", "nunique"), Units=("Quantity", "sum"))
        .merge(dim_country, on="CountryKey")
        .sort_values("Revenue", ascending=False)
    )

    product_mart = (
        fact_sales.groupby("ProductKey", as_index=False)
        .agg(Revenue=("LineAmount", "sum"), Orders=("Invoice", "nunique"), Units=("Quantity", "sum"))
        .merge(dim_product[["ProductKey", "StockCode", "Description"]], on="ProductKey")
        .sort_values("Revenue", ascending=False)
    )

    # ML feature table — customer level RFM + repurchase label
    snapshot = fact_sales["InvoiceDate"].max()
    cust_feat = fact_sales[fact_sales["CustomerKey"] > 0].copy()
    rfm = cust_feat.groupby("CustomerKey").agg(
        RecencyDays=("InvoiceDate", lambda s: (snapshot - s.max()).days),
        Frequency=("Invoice", "nunique"),
        Monetary=("LineAmount", "sum"),
        AvgOrderValue=("LineAmount", "sum"),
        AvgBasketSize=("Quantity", "mean"),
        TenureDays=("InvoiceDate", lambda s: (s.max() - s.min()).days),
        LastPurchase=("InvoiceDate", "max"),
        FirstPurchase=("InvoiceDate", "min"),
    ).reset_index()
    rfm["AvgOrderValue"] = rfm["Monetary"] / rfm["Frequency"]
    # repurchase within 90d of first purchase as simple propensity target
    # actually: churn = no purchase in last 90 days of observation window
    rfm["Churned90"] = (rfm["RecencyDays"] > 90).astype(int)
    # next-period repurchase: customers with >=2 orders
    rfm["IsRepeat"] = (rfm["Frequency"] >= 2).astype(int)
    rfm = rfm.merge(dim_customer[["CustomerKey", "CustomerID", "Country"]], on="CustomerKey", how="left")

    # write gold
    dim_date.to_csv(GOLD / "dim_date.csv", index=False)
    dim_customer.to_csv(GOLD / "dim_customer.csv", index=False)
    dim_product.to_csv(GOLD / "dim_product.csv", index=False)
    dim_country.to_csv(GOLD / "dim_country.csv", index=False)
    # fact can be large — write parquet + a csv sample for PBIP; full csv for smaller fact if needed
    fact_sales.to_parquet(GOLD / "fact_sales.parquet", index=False)
    # PBIP likes csv — write full fact as csv (may be ~40MB); also sample
    fact_sales.drop(columns=["InvoiceDate"]).to_csv(GOLD / "fact_sales.csv", index=False)
    fact_returns.drop(columns=["InvoiceDate"]).to_csv(GOLD / "fact_returns.csv", index=False)
    monthly.to_csv(GOLD / "mart_monthly.csv", index=False)
    country_mart.to_csv(GOLD / "mart_country.csv", index=False)
    product_mart.head(500).to_csv(GOLD / "mart_top_products.csv", index=False)
    rfm.to_csv(GOLD / "ml_customer_features.csv", index=False)
    rfm.to_parquet(GOLD / "ml_customer_features.parquet", index=False)

    # KPI summary — evidence based
    total_rev = float(fact_sales["LineAmount"].sum())
    total_orders = int(fact_sales["Invoice"].nunique())
    total_cust = int(fact_sales.loc[fact_sales["CustomerKey"] > 0, "CustomerKey"].nunique())
    aov = total_rev / total_orders
    guest_share = float(fact_sales["IsGuest"].mean())
    ret_amt = float(fact_returns["ReturnAmount"].sum()) if len(fact_returns) else 0.0
    ret_rate = ret_amt / total_rev if total_rev else 0.0

    # YoY: compare 2010 calendar vs 2011 calendar on overlapping months if possible
    fs = fact_sales.copy()
    fs["Year"] = fs["InvoiceDate"].dt.year
    fs["Month"] = fs["InvoiceDate"].dt.month
    y2010 = fs[fs["Year"] == 2010]
    y2011 = fs[fs["Year"] == 2011]
    # overlapping months present in both
    months_2010 = set(y2010["Month"].unique())
    months_2011 = set(y2011["Month"].unique())
    overlap = sorted(months_2010 & months_2011)
    rev_2010 = float(y2010[y2010["Month"].isin(overlap)]["LineAmount"].sum())
    rev_2011 = float(y2011[y2011["Month"].isin(overlap)]["LineAmount"].sum())
    ord_2010 = int(y2010[y2010["Month"].isin(overlap)]["Invoice"].nunique())
    ord_2011 = int(y2011[y2011["Month"].isin(overlap)]["Invoice"].nunique())
    cust_2010 = int(y2010[(y2010["Month"].isin(overlap)) & (y2010["CustomerKey"] > 0)]["CustomerKey"].nunique())
    cust_2011 = int(y2011[(y2011["Month"].isin(overlap)) & (y2011["CustomerKey"] > 0)]["CustomerKey"].nunique())

    def yoy(a, b):
        return (b - a) / a if a else None

    uk_rev = float(country_mart.loc[country_mart["Country"] == "United Kingdom", "Revenue"].sum())
    top5_share = float(product_mart.head(5)["Revenue"].sum() / total_rev)

    metrics = {
        "period_start": str(fact_sales["InvoiceDate"].min().date()),
        "period_end": str(fact_sales["InvoiceDate"].max().date()),
        "revenue": round(total_rev, 2),
        "orders": total_orders,
        "customers": total_cust,
        "aov": round(aov, 2),
        "units": int(fact_sales["Quantity"].sum()),
        "lines": int(len(fact_sales)),
        "products": int(dim_product["ProductKey"].nunique()),
        "countries": int(dim_country["CountryKey"].nunique()),
        "guest_line_share": round(guest_share, 4),
        "return_amount": round(ret_amt, 2),
        "return_rate": round(ret_rate, 4),
        "uk_revenue": round(uk_rev, 2),
        "uk_revenue_share": round(uk_rev / total_rev, 4),
        "top5_product_revenue_share": round(top5_share, 4),
        "yoy_overlap_months": overlap,
        "revenue_2010_overlap": round(rev_2010, 2),
        "revenue_2011_overlap": round(rev_2011, 2),
        "revenue_yoy": round(yoy(rev_2010, rev_2011), 4) if rev_2010 else None,
        "orders_2010_overlap": ord_2010,
        "orders_2011_overlap": ord_2011,
        "orders_yoy": round(yoy(ord_2010, ord_2011), 4) if ord_2010 else None,
        "customers_2010_overlap": cust_2010,
        "customers_2011_overlap": cust_2011,
        "customers_yoy": round(yoy(cust_2010, cust_2011), 4) if cust_2010 else None,
        "aov_2010": round(rev_2010 / ord_2010, 2) if ord_2010 else None,
        "aov_2011": round(rev_2011 / ord_2011, 2) if ord_2011 else None,
        "repeat_customer_rate": round(float(rfm["IsRepeat"].mean()), 4),
        "churned_90_rate": round(float(rfm["Churned90"].mean()), 4),
        "bronze_rows": int(len(pd.read_parquet(BRONZE / "transactions.parquet"))) if False else None,
    }
    # monthly list for charts
    metrics["monthly"] = monthly.to_dict(orient="records")
    metrics["top_countries"] = country_mart.head(12)[["Country", "Revenue", "Orders", "Units"]].to_dict(orient="records")
    metrics["top_products"] = product_mart.head(15)[["StockCode", "Description", "Revenue", "Orders", "Units"]].to_dict(orient="records")

    (GOLD / "metrics_summary.json").write_text(json.dumps(metrics, indent=2, default=str))
    (REPORTS / "kpi_summary.json").write_text(json.dumps({k: metrics[k] for k in metrics if k not in ("monthly", "top_countries", "top_products")}, indent=2, default=str))

    log(f"Gold revenue £{total_rev:,.2f} | orders {total_orders:,} | customers {total_cust:,} | AOV £{aov:,.2f}")
    log(f"YoY revenue (overlap months {overlap}): {metrics['revenue_yoy']}")
    return metrics


def main():
    raw = load_raw()
    bronze = to_bronze(raw)
    silver = to_silver(bronze)
    metrics = to_gold(silver)
    print(json.dumps({k: metrics[k] for k in ("revenue", "orders", "customers", "aov", "revenue_yoy", "return_rate")}, indent=2))


if __name__ == "__main__":
    main()
