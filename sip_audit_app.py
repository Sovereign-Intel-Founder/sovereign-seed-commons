#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(
    page_title="Sovereign Intelligence — Local Audit Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛡️ Sovereign Intelligence — Benchmark & Test Audit Center")
st.markdown("*Local system telemetry, historical test results, and core execution logs.*")

# Sidebar for Navigation
st.sidebar.header("Audit Controls")
log_type = st.sidebar.selectbox(
    "Select Telemetry / Log Source",
    [
        "Live Benchmarks (JSONL)",
        "Core 128 Benchmarks (JSONL)",
        "Audit Arbitrage Logs",
        "Shared Memory Metrics",
        "Concurrency Results"
    ]
)

# Helper to load JSONL logs into a DataFrame
@st.cache_data(ttl=5)
def load_jsonl(filepath):
    path = Path(filepath)
    if not path.exists():
        return pd.DataFrame()
    data = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return pd.DataFrame(data)

# Helper to load plain log files
def load_raw_log(filepath):
    path = Path(filepath)
    if not path.exists():
        return ["File missing or inactive."]
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            return lines[-100:]
    except Exception as e:
        return [f"Error reading log: {e}"]

# Main Content Area based on selection
if log_type == "Live Benchmarks (JSONL)":
    st.subheader("📊 Live Benchmark Execution Stream")
    df = load_jsonl("logs/live_benchmark.jsonl")
    if not df.empty:
        st.metric(label="Total Recorded Events", value=len(df))
        st.dataframe(df.tail(100), use_container_width=True)
    else:
        st.warning("No data found in logs/live_benchmark.jsonl")

elif log_type == "Core 128 Benchmarks (JSONL)":
    st.subheader("⚡ Core 128 High-Concurrency Checkpoints")
    df = load_jsonl("logs/core128_benchmark.jsonl")
    if not df.empty:
        st.metric(label="Logged Checkpoints", value=len(df))
        st.dataframe(df.tail(100), use_container_width=True)
        if "seq" in df.columns and "ts" in df.columns:
            st.line_chart(df.tail(200), x="seq", y="ts")
    else:
        st.warning("No data found in logs/core128_benchmark.jsonl")

elif log_type == "Audit Arbitrage Logs":
    st.subheader("🔍 Audit Arbitrage Records")
    df = load_jsonl("logs/audit_arbitrage.jsonl")
    if not df.empty:
        st.dataframe(df.tail(100), use_container_width=True)
    else:
        st.warning("No records found in logs/audit_arbitrage.jsonl")

elif log_type == "Shared Memory Metrics":
    st.subheader("🧠 Shared Memory Ring & Telemetry Logs")
    lines = load_raw_log("telemetry/tollbridge_system/shared_memory_metrics.log")
    for line in lines:
        st.text(line)

elif log_type == "Concurrency Results":
    st.subheader("📈 Toll Bridge Concurrency Results")
    lines = load_raw_log("telemetry/tollbridge_system/concurrency_results.log")
    for line in lines:
        st.text(line)

st.sidebar.markdown("---")
st.sidebar.info("Running locally on server. Zero external egress.")
