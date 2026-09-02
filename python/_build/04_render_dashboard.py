#!/usr/bin/env python3
"""Render CommercePulse Power BI Desktop–style screenshots (dark charcoal + gold)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "gold"
SHOTS = ROOT / "screenshots"
OUT = ROOT / "python" / "outputs"
W, H = 1920, 1080

BG = (27, 26, 25)
PANEL = (37, 36, 35)
PANEL2 = (45, 44, 43)
BORDER = (64, 63, 61)
GOLD = (242, 200, 17)
GOLD_DIM = (180, 148, 20)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
GRAY = (100, 116, 139)
TEAL = (45, 212, 191)
RED = (248, 113, 113)
GREEN = (74, 222, 128)
ORANGE = (251, 146, 60)
BLUE = (96, 165, 250)
PURPLE = (167, 139, 250)

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

PAGES = [
    ("Executive Overview", "executive-overview.png"),
    ("Sales Performance", "sales-performance.png"),
    ("Customer Intelligence", "customer-intelligence.png"),
    ("Product & Country", "product-country.png"),
    ("Operations / Returns", "operations-returns.png"),
    ("Model Insights", "model-insights.png"),
]


def F(path, size):
    return ImageFont.truetype(path, size)


def fmt_n(n, decimals=0):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return "—"
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n:,.0f}" if decimals == 0 else f"{n:,.{decimals}f}"
    return f"{n:.{decimals}f}" if decimals else f"{n:,.0f}"


def fmt_gbp(n):
    if abs(n) >= 1_000_000:
        return f"£{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"£{n:,.0f}"
    return f"£{n:,.2f}"


def fmt_pct(x, signed=False):
    if x is None:
        return "—"
    s = f"{x*100:.1f}%"
    if signed and x > 0:
        s = "+" + s
    return s


def rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_chrome(draw, active_idx, title):
    draw.rectangle((0, 0, W, H), fill=BG)
    draw.rectangle((0, 0, W, 40), fill=(32, 31, 30))
    draw.rounded_rectangle((12, 10, 28, 30), radius=3, fill=GOLD)
    draw.text((14, 12), "P", font=F(FONT_B, 14), fill=(27, 26, 25))
    draw.text((36, 11), "CommercePulse — Retail Intelligence  ·  Power BI Desktop", font=F(FONT, 14), fill=WHITE)
    draw.text((W - 220, 11), "File   Home   View   Help", font=F(FONT, 12), fill=MUTED)
    for i, c in enumerate([(248, 113, 113), (251, 191, 36), (74, 222, 128)]):
        draw.ellipse((W - 70 + i * 18, 14, W - 58 + i * 18, 26), fill=c)

    draw.rectangle((0, 40, 56, H - 28), fill=(22, 21, 20))
    icons = ["⌂", "£", "◎", "▤", "↺", "✦"]
    for i, ic in enumerate(icons):
        y = 56 + i * 56
        if i == active_idx:
            draw.rounded_rectangle((6, y, 50, y + 44), radius=8, fill=(55, 48, 20))
            draw.rectangle((6, y + 8, 10, y + 36), fill=GOLD)
        draw.text((18, y + 12), ic, font=F(FONT, 16), fill=GOLD if i == active_idx else MUTED)

    draw.rectangle((56, 40, W, 88), fill=PANEL)
    draw.text((72, 50), title.upper(), font=F(FONT_B, 20), fill=WHITE)
    draw.text((72, 72), "Online Retail II  ·  Dec 2009 – Dec 2011  ·  Star schema / import mode", font=F(FONT, 11), fill=MUTED)

    draw.rectangle((56, 88, W, 132), fill=(33, 32, 31))
    sx = 72
    for label, val in [("Period", "Full range"), ("Country", "All"), ("Segment", "All"), ("Channel", "Online")]:
        draw.rounded_rectangle((sx, 98, sx + 150, 122), radius=6, fill=PANEL2, outline=BORDER, width=1)
        draw.text((sx + 10, 103), f"{label}: {val}", font=F(FONT, 11), fill=MUTED)
        sx += 162
    draw.rounded_rectangle((W - 160, 98, W - 72, 122), radius=6, fill=(55, 48, 20), outline=GOLD_DIM, width=1)
    draw.text((W - 148, 103), "⟳  Refresh model", font=F(FONT, 11), fill=GOLD)

    draw.rectangle((56, H - 28, W, H), fill=(22, 21, 20))
    tx = 72
    for i, (name, _) in enumerate(PAGES):
        tw = 12 + len(name) * 8
        if i == active_idx:
            draw.rectangle((tx - 4, H - 28, tx + tw, H), fill=PANEL)
            draw.rectangle((tx - 4, H - 28, tx + tw, H - 26), fill=GOLD)
            draw.text((tx, H - 20), name, font=F(FONT_B, 11), fill=WHITE)
        else:
            draw.text((tx, H - 20), name, font=F(FONT, 11), fill=MUTED)
        tx += tw + 20
    draw.text((W - 300, H - 20), "Import mode  ·  Medallion gold  ·  en-GB", font=F(FONT, 10), fill=GRAY)


def card(draw, x, y, w, h, title, value, subtitle=None, accent=GOLD, value_color=WHITE):
    rounded_rect(draw, (x, y, x + w, y + h), 10, fill=PANEL, outline=BORDER, width=1)
    draw.rectangle((x, y, x + 4, y + h), fill=accent)
    draw.text((x + 16, y + 12), title.upper(), font=F(FONT_B, 11), fill=MUTED)
    draw.text((x + 16, y + 36), value, font=F(FONT_B, 28), fill=value_color)
    if subtitle:
        draw.text((x + 16, y + h - 28), subtitle, font=F(FONT, 11), fill=GRAY)


def panel(draw, x, y, w, h, title=None):
    rounded_rect(draw, (x, y, x + w, y + h), 10, fill=PANEL, outline=BORDER, width=1)
    if title:
        draw.text((x + 16, y + 12), title.upper(), font=F(FONT_B, 12), fill=MUTED)
        draw.line((x + 16, y + 36, x + w - 16, y + 36), fill=BORDER, width=1)
    return (x, y, w, h)


def fig_to_img(fig, tw, th):
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    im = Image.fromarray(buf).convert("RGBA")
    plt.close(fig)
    return im.resize((tw, th), Image.Resampling.LANCZOS)


def style_ax(ax, bg=PANEL):
    ax.set_facecolor("#%02x%02x%02x" % bg)
    ax.tick_params(colors="#94A3B8", labelsize=8)
    for sp in ax.spines.values():
        sp.set_color("#40403D")
    ax.yaxis.label.set_color("#94A3B8")
    ax.xaxis.label.set_color("#94A3B8")
    ax.title.set_color("#F8FAFC")


def chart_bar_h(labels, values, tw, th, color="#F2C811", title=None):
    fig, ax = plt.subplots(figsize=(tw / 100, th / 100), dpi=100)
    fig.patch.set_facecolor("#%02x%02x%02x" % PANEL)
    style_ax(ax)
    y = np.arange(len(labels))
    ax.barh(y, values, color=color, height=0.62, edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.grid(axis="x", color="#40403D", linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=10, pad=8, color="#F8FAFC", loc="left", fontweight="bold")
    fig.tight_layout(pad=0.4)
    return fig_to_img(fig, tw, th)


def chart_bar_v(labels, values, tw, th, color="#60A5FA", title=None):
    fig, ax = plt.subplots(figsize=(tw / 100, th / 100), dpi=100)
    fig.patch.set_facecolor("#%02x%02x%02x" % PANEL)
    style_ax(ax)
    x = np.arange(len(labels))
    ax.bar(x, values, color=color, width=0.72, edgecolor="none")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.grid(axis="y", color="#40403D", linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=10, pad=8, color="#F8FAFC", loc="left", fontweight="bold")
    fig.tight_layout(pad=0.4)
    return fig_to_img(fig, tw, th)


def chart_line(xs, ys, tw, th, color="#F2C811", title=None, ys2=None, color2="#60A5FA", ylabel=None, ylabel2=None):
    fig, ax = plt.subplots(figsize=(tw / 100, th / 100), dpi=100)
    fig.patch.set_facecolor("#%02x%02x%02x" % PANEL)
    style_ax(ax)
    ax.plot(xs, ys, color=color, linewidth=2.2, marker="o", markersize=3.5)
    ax.fill_between(range(len(xs)), ys, alpha=0.12, color=color)
    ax.set_xticks(range(0, len(xs), max(1, len(xs) // 8)))
    ax.set_xticklabels([xs[i] for i in range(0, len(xs), max(1, len(xs) // 8))], rotation=45, ha="right", fontsize=7)
    ax.grid(color="#40403D", linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    if ys2 is not None:
        ax2 = ax.twinx()
        style_ax(ax2)
        ax2.plot(range(len(xs)), ys2, color=color2, linewidth=2.0, linestyle="--", marker="s", markersize=3)
        ax2.tick_params(colors="#94A3B8", labelsize=8)
        if ylabel2:
            ax2.set_ylabel(ylabel2, fontsize=8, color="#94A3B8")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8)
    if title:
        ax.set_title(title, fontsize=10, pad=8, color="#F8FAFC", loc="left", fontweight="bold")
    fig.tight_layout(pad=0.4)
    return fig_to_img(fig, tw, th)


def chart_donut(labels, values, tw, th, colors, title=None):
    fig, ax = plt.subplots(figsize=(tw / 100, th / 100), dpi=100)
    fig.patch.set_facecolor("#%02x%02x%02x" % PANEL)
    ax.set_facecolor("#%02x%02x%02x" % PANEL)
    wedges, _ = ax.pie(
        values, colors=colors, startangle=90,
        wedgeprops=dict(width=0.42, edgecolor="#252423", linewidth=2),
    )
    ax.legend(
        wedges, [f"{l}  {v/sum(values)*100:.0f}%" for l, v in zip(labels, values)],
        loc="center left", bbox_to_anchor=(1.0, 0.5),
        facecolor="#252423", edgecolor="#40403D", labelcolor="#F8FAFC", fontsize=8,
    )
    if title:
        ax.set_title(title, fontsize=10, pad=8, color="#F8FAFC", loc="left", fontweight="bold")
    fig.tight_layout(pad=0.6)
    return fig_to_img(fig, tw, th)


def paste(base, overlay, x, y):
    base.paste(overlay, (x, y), overlay if overlay.mode == "RGBA" else None)


def load():
    m = json.loads((DATA / "metrics_summary.json").read_text())
    monthly = pd.read_csv(DATA / "mart_monthly.csv")
    countries = pd.read_csv(DATA / "mart_country.csv")
    products = pd.read_csv(DATA / "mart_top_products.csv")
    segs = pd.read_csv(OUT / "segment_summary.csv")
    model = json.loads((ROOT / "reports" / "model_metrics.json").read_text())
    seg_meta = json.loads((ROOT / "reports" / "segmentation_metrics.json").read_text())
    returns = pd.read_csv(DATA / "fact_returns.csv")
    return m, monthly, countries, products, segs, model, seg_meta, returns


def page_executive(m, monthly, countries, segs):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_chrome(draw, 0, "Executive Overview")

    yoy_r = m["revenue_yoy"]
    yoy_o = m["orders_yoy"]
    yoy_c = m["customers_yoy"]
    yoy_a = (m["aov_2011"] - m["aov_2010"]) / m["aov_2010"] if m["aov_2010"] else 0

    kpis = [
        ("Revenue", fmt_gbp(m["revenue"]), f"2010→2011  {fmt_pct(yoy_r, True)}", GOLD if yoy_r >= 0 else ORANGE),
        ("Orders", fmt_n(m["orders"]), f"2010→2011  {fmt_pct(yoy_o, True)}", BLUE),
        ("Customers", fmt_n(m["customers"]), f"2010→2011  {fmt_pct(yoy_c, True)}", TEAL),
        ("Avg order value", fmt_gbp(m["aov"]), f"2010→2011  {fmt_pct(yoy_a, True)}", GREEN if yoy_a >= 0 else ORANGE),
        ("UK share", fmt_pct(m["uk_revenue_share"]), f"{fmt_gbp(m['uk_revenue'])} UK revenue", GOLD),
        ("Return rate", fmt_pct(m["return_rate"]), f"{fmt_gbp(m['return_amount'])} returned", RED),
    ]
    x0, y0, cw, ch, gap = 72, 148, 290, 100, 14
    for i, (t, v, s, a) in enumerate(kpis):
        card(draw, x0 + i * (cw + gap), y0, cw, ch, t, v, s, accent=a)

    xs = list(monthly["YearMonth"])
    line = chart_line(
        xs, list(monthly["Revenue"] / 1e6), 900, 400,
        color="#F2C811", title="Monthly revenue (£M)",
        ys2=list(monthly["Orders"]), color2="#60A5FA",
        ylabel="£M", ylabel2="Orders",
    )
    panel(draw, 72, 268, 940, 460, "Revenue & Order Trend")
    paste(img, line, 88, 310)

    top = countries.head(8)
    labels = [c if len(c) < 16 else c[:14] + "…" for c in top["Country"]]
    bar = chart_bar_h(labels, list(top["Revenue"] / 1e6), 820, 400, color="#F2C811",
                      title="Revenue by country (£M)")
    panel(draw, 1030, 268, 860, 460, "Geographic Mix")
    paste(img, bar, 1046, 310)

    panel(draw, 72, 748, 1818, 280, "Commercial Snapshot")
    insights = [
        ("Products", fmt_n(m["products"])),
        ("Countries", str(m["countries"])),
        ("Repeat customers", fmt_pct(m["repeat_customer_rate"])),
        ("Guest line share", fmt_pct(m["guest_line_share"])),
        ("Units sold", fmt_n(m["units"])),
        ("Top-5 SKU share", fmt_pct(m["top5_product_revenue_share"])),
    ]
    for i, (lab, val) in enumerate(insights):
        x = 100 + i * 300
        draw.text((x, 800), lab.upper(), font=F(FONT_B, 11), fill=MUTED)
        draw.text((x, 824), val, font=F(FONT_B, 26), fill=WHITE)

    draw.text((100, 880), "SEGMENT REVENUE (RFM k=4)", font=F(FONT_B, 11), fill=MUTED)
    headers = ["Segment", "Customers", "Med. Monetary", "Revenue", "Repeat %"]
    xs_h = [100, 360, 520, 720, 920]
    for h, x in zip(headers, xs_h):
        draw.text((x, 904), h, font=F(FONT_B, 10), fill=GOLD)
    for i, r in segs.iterrows():
        y = 926 + list(segs.index).index(i) * 20
        if y > 1000:
            break
        vals = [str(r["Segment"])[:22], fmt_n(r["Customers"]), fmt_gbp(r["Monetary"]),
                fmt_gbp(r["Revenue"]), fmt_pct(r["RepeatRate"])]
        for v, x in zip(vals, xs_h):
            draw.text((x, y), v, font=F(FONT, 11), fill=WHITE)

    draw.text((1200, 880), "READ", font=F(FONT_B, 11), fill=MUTED)
    draw.text((1200, 908), "• November peaks in both 2010 and 2011 — classic gift retail seasonality", font=F(FONT, 13), fill=WHITE)
    draw.text((1200, 934), "• UK still ~86% of revenue; international is a long tail of 42 markets", font=F(FONT, 13), fill=WHITE)
    draw.text((1200, 960), "• Orders dipped YoY while AOV rose — fewer baskets, higher value", font=F(FONT, 13), fill=WHITE)
    return img


def page_sales(m, monthly, countries):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_chrome(draw, 1, "Sales Performance")

    card(draw, 72, 148, 350, 92, "2010 Revenue", fmt_gbp(m["revenue_2010_overlap"]), "Calendar year", GOLD)
    card(draw, 438, 148, 350, 92, "2011 Revenue", fmt_gbp(m["revenue_2011_overlap"]), fmt_pct(m["revenue_yoy"], True), ORANGE)
    card(draw, 804, 148, 350, 92, "2010 Orders", fmt_n(m["orders_2010_overlap"]), "Calendar year", BLUE)
    card(draw, 1170, 148, 350, 92, "2011 Orders", fmt_n(m["orders_2011_overlap"]), fmt_pct(m["orders_yoy"], True), BLUE)
    card(draw, 1536, 148, 354, 92, "AOV lift", fmt_pct((m["aov_2011"]-m["aov_2010"])/m["aov_2010"], True),
         f"£{m['aov_2010']:.0f} → £{m['aov_2011']:.0f}", GREEN)

    xs = list(monthly["YearMonth"])
    panel(draw, 72, 260, 1818, 380, "Monthly Revenue & AOV")
    line = chart_line(
        xs, list(monthly["Revenue"] / 1e6), 1780, 320,
        color="#F2C811", ys2=list(monthly["AOV"]), color2="#2DD4BF",
        ylabel="£M", ylabel2="AOV (£)",
    )
    paste(img, line, 88, 300)

    panel(draw, 72, 660, 900, 360, "Orders by Month")
    bar = chart_bar_v([x[2:] for x in xs], list(monthly["Orders"]), 860, 300, color="#60A5FA")
    paste(img, bar, 88, 700)

    panel(draw, 990, 660, 900, 360, "Units by Month")
    bar2 = chart_bar_v([x[2:] for x in xs], list(monthly["Units"] / 1000), 860, 300, color="#F2C811",
                       title="Units (thousands)")
    paste(img, bar2, 1006, 690)
    return img


def page_customers(m, segs, model):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_chrome(draw, 2, "Customer Intelligence")

    card(draw, 72, 148, 350, 92, "Registered customers", fmt_n(m["customers"]), "Excludes guests", TEAL)
    card(draw, 438, 148, 350, 92, "Repeat rate", fmt_pct(m["repeat_customer_rate"]), "2+ orders", GREEN)
    card(draw, 804, 148, 350, 92, "Churned 90d rate", fmt_pct(m["churned_90_rate"]), "End-of-window inactivity", ORANGE)
    card(draw, 1170, 148, 350, 92, "Guest line share", fmt_pct(m["guest_line_share"]), "Null CustomerID lines", GRAY)
    card(draw, 1536, 148, 354, 92, "Churn model AUC", f"{model['churn']['gradient_boosting']['auc']:.3f}",
         "Gradient boosting holdout", GOLD)

    panel(draw, 72, 260, 900, 480, "RFM Segment Mix")
    donut = chart_donut(
        list(segs["Segment"]), list(segs["Customers"]),
        860, 420,
        colors=["#F2C811", "#60A5FA", "#2DD4BF", "#F87171"],
        title="Customers by segment",
    )
    paste(img, donut, 90, 300)

    panel(draw, 990, 260, 900, 480, "Segment Economics")
    bar = chart_bar_h(
        list(segs.sort_values("Revenue", ascending=False)["Segment"]),
        list(segs.sort_values("Revenue", ascending=False)["Revenue"] / 1e6),
        860, 400, color="#F2C811", title="Revenue by segment (£M)",
    )
    paste(img, bar, 1006, 310)

    panel(draw, 72, 760, 1818, 268, "Segment Detail")
    headers = ["Segment", "Customers", "Med Recency", "Med Frequency", "Med Monetary", "Revenue", "Repeat %", "Churn90 %"]
    xs_h = [100, 320, 480, 640, 800, 1000, 1220, 1420]
    for h, x in zip(headers, xs_h):
        draw.text((x, 800), h, font=F(FONT_B, 11), fill=GOLD)
    for i, r in segs.iterrows():
        y = 832 + list(segs.index).index(i) * 36
        vals = [
            str(r["Segment"])[:20], fmt_n(r["Customers"]), f"{r['RecencyDays']:.0f}d",
            f"{r['Frequency']:.0f}", fmt_gbp(r["Monetary"]), fmt_gbp(r["Revenue"]),
            fmt_pct(r["RepeatRate"]), fmt_pct(r["Churn90Rate"]),
        ]
        for v, x in zip(vals, xs_h):
            draw.text((x, y), v, font=F(FONT, 14), fill=WHITE)
    return img


def page_product_country(m, products, countries):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_chrome(draw, 3, "Product & Country")

    card(draw, 72, 148, 440, 92, "Active SKUs", fmt_n(m["products"]), "In cleaned sales", GOLD)
    card(draw, 528, 148, 440, 92, "Markets", str(m["countries"]), "Distinct countries", BLUE)
    card(draw, 984, 148, 440, 92, "Top-5 revenue share", fmt_pct(m["top5_product_revenue_share"]), "Concentration check", ORANGE)
    card(draw, 1440, 148, 450, 92, "UK revenue", fmt_gbp(m["uk_revenue"]), fmt_pct(m["uk_revenue_share"]) + " of total", TEAL)

    top_p = products.head(10).copy()
    top_p["Label"] = top_p["Description"].str.slice(0, 28)
    panel(draw, 72, 260, 940, 700, "Top Products by Revenue")
    bar = chart_bar_h(list(top_p["Label"]), list(top_p["Revenue"] / 1000), 900, 640,
                      color="#F2C811", title="Revenue (£ thousands)")
    paste(img, bar, 88, 300)

    top_c = countries.head(10)
    labels = [c if len(c) < 18 else c[:16] + "…" for c in top_c["Country"]]
    panel(draw, 1030, 260, 860, 700, "Top Countries by Revenue")
    bar2 = chart_bar_h(labels, list(top_c["Revenue"] / 1e6), 820, 640,
                       color="#60A5FA", title="Revenue (£M)")
    paste(img, bar2, 1046, 300)
    return img


def page_operations(m, returns, monthly):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_chrome(draw, 4, "Operations / Returns")

    card(draw, 72, 148, 350, 92, "Return value", fmt_gbp(m["return_amount"]), "Cancels + neg qty", RED)
    card(draw, 438, 148, 350, 92, "Return rate", fmt_pct(m["return_rate"]), "Value / sales value", ORANGE)
    card(draw, 804, 148, 350, 92, "Return lines", fmt_n(len(returns)), "fact_returns grain", GRAY)
    card(draw, 1170, 148, 350, 92, "Sales lines", fmt_n(m["lines"]), "fact_sales grain", BLUE)
    card(draw, 1536, 148, 354, 92, "Guest share", fmt_pct(m["guest_line_share"]), "Ops / CRM implication", TEAL)

    # returns by month if possible
    if "DateKey" in returns.columns:
        returns = returns.copy()
        returns["YearMonth"] = returns["DateKey"].astype(str).str.slice(0, 6)
        returns["YearMonth"] = returns["YearMonth"].str.slice(0, 4) + "-" + returns["YearMonth"].str.slice(4, 6)
        rmonth = returns.groupby("YearMonth", as_index=False)["ReturnAmount"].sum()
    else:
        rmonth = pd.DataFrame({"YearMonth": monthly["YearMonth"], "ReturnAmount": 0})

    panel(draw, 72, 260, 1200, 420, "Return Value by Month")
    if len(rmonth):
        line = chart_line(
            list(rmonth["YearMonth"]), list(rmonth["ReturnAmount"] / 1000), 1160, 360,
            color="#F87171", title="Return amount (£ thousands)", ylabel="£k",
        )
        paste(img, line, 88, 300)

    panel(draw, 1290, 260, 600, 420, "Quality Filters Applied")
    rules = [
        "✓ Drop C-prefix cancels from sales",
        "✓ Qty > 0 and Price > 0",
        "✓ Non-blank Description",
        "✓ Exclude fee / postage codes",
        "✓ Exact-dupe removal after sheet union",
        "✓ Guests flagged, not dropped",
        "✓ Returns isolated in fact_returns",
    ]
    y = 320
    for r in rules:
        draw.text((1320, y), r, font=F(FONT, 15), fill=WHITE)
        y += 42

    panel(draw, 72, 700, 1818, 328, "Operational Notes")
    notes = [
        "Return rate stays under 4% of sales value across the full window — manageable, but still worth watching around peak months.",
        "Guest checkouts are ~23% of sales lines. They inflate order counts and block RFM / churn work until identity resolution exists.",
        "Fee codes (POST, DOT, AMAZONFEE, …) are stripped from merchandise revenue so postage does not look like product demand.",
        "Reconcile dashboard cards to sql/04_kpi_queries.sql and reports/kpi_summary.json after every gold refresh.",
    ]
    y = 760
    for n in notes:
        draw.text((100, y), "•  " + n, font=F(FONT, 15), fill=MUTED)
        y += 48
    return img


def page_models(m, model, seg_meta, segs):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_chrome(draw, 5, "Model Insights")

    ch = model["churn"]["gradient_boosting"]
    dem = model["demand_baseline"]
    aov = model["aov_baseline"]

    card(draw, 72, 148, 350, 92, "Churn AUC", f"{ch['auc']:.3f}", f"Acc {ch['accuracy']:.3f} · holdout 25%", GOLD)
    card(draw, 438, 148, 350, 92, "Churn base rate", fmt_pct(model["churn"]["base_rate"]), "Churned90 label", ORANGE)
    card(draw, 804, 148, 350, 92, "Demand MAPE", f"{dem['mape_pct']:.1f}%", "Seasonal naive lag-12", BLUE)
    card(draw, 1170, 148, 350, 92, "AOV MAE", f"£{aov['mae']:.0f}", f"Naive £{aov['naive_mean_mae']:.0f}", TEAL)
    card(draw, 1536, 148, 354, 92, "RFM silhouette", f"{seg_meta['silhouette_full']:.3f}", f"k={seg_meta['k']}", PURPLE)

    # try paste saved charts
    panel(draw, 72, 260, 900, 480, "Churn Score Separation")
    churn_img = Image.open(OUT / "churn_baseline.png").convert("RGBA")
    churn_img = churn_img.resize((860, 420), Image.Resampling.LANCZOS)
    paste(img, churn_img, 88, 300)

    panel(draw, 990, 260, 900, 480, "Demand Baseline")
    dem_img = Image.open(OUT / "demand_baseline.png").convert("RGBA")
    dem_img = dem_img.resize((860, 420), Image.Resampling.LANCZOS)
    paste(img, dem_img, 1006, 300)

    panel(draw, 72, 760, 1818, 268, "Caveats (read before pitching these numbers)")
    caveats = [
        "Churned90 is end-of-window inactivity, not a future-month holdout event. Recency was excluded from features to avoid trivial leakage.",
        "Demand model is seasonal-naive only — no promo calendar, weather, or price features. MAPE ~17% on a short monthly series.",
        "AOV model predicts historical average order value for repeat buyers; it is not a next-basket forecaster.",
        "Segments are unsupervised RFM clusters with commercial labels — useful for targeting drafts, not contractual tiers.",
    ]
    y = 810
    for c in caveats:
        draw.text((100, y), "•  " + c, font=F(FONT, 14), fill=MUTED)
        y += 40
    return img


def save(img, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / name
    img.save(path, "PNG", optimize=True)
    print("wrote", path, img.size)
    return path


def main():
    m, monthly, countries, products, segs, model, seg_meta, returns = load()
    pages = [
        page_executive(m, monthly, countries, segs),
        page_sales(m, monthly, countries),
        page_customers(m, segs, model),
        page_product_country(m, products, countries),
        page_operations(m, returns, monthly),
        page_models(m, model, seg_meta, segs),
    ]
    paths = []
    for img, (_, fname) in zip(pages, PAGES):
        paths.append(save(img, fname))
    print("screenshots:", len(paths))


if __name__ == "__main__":
    main()
