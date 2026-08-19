#!/usr/bin/env python3
"""CommercePulse insights assistant (Streamlit UI).

  streamlit run ai/app.py

CLI alternative:
  python ai/rag/retrieve.py "Why did UK revenue change?"
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from ai.rag.retrieve import answer

st.set_page_config(page_title="CommercePulse Insights", page_icon="📊", layout="wide")
st.title("CommercePulse — Insights Assistant")
st.caption("Decision-support retrieval over gold marts. Local TF-IDF index — no paid API key for the core demo.")

examples = [
    "Why did UK revenue change year over year?",
    "What was the peak revenue month?",
    "How large is the return rate?",
    "Which customer segments drive revenue?",
    "What share of lines are guest checkouts?",
]
pick = st.selectbox("Examples", ["(type your own)"] + examples)
q = st.text_input("Question", pick if pick != "(type your own)" else "Why did UK revenue change year over year?")

if st.button("Retrieve facts", type="primary") or q:
    out = answer(q)
    st.markdown(out["answer"])
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Sources")
        st.json(out["sources"])
    with c2:
        st.subheader("Suggested SQL")
        st.code(out.get("sql") or "-- n/a", language="sql")
