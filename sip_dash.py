#!/usr/bin/env python3
import os
import time
from pathlib import Path

TELEMETRY_FILES = [
    "telemetry/tollbridge_system/shared_memory_metrics.log",
    "telemetry/tollbridge_system/concurrency_results.log",
    "telemetry/tollbridge_system/submission_concurrency.log",
    "logs/live_benchmark.jsonl",
    "logs/core128_benchmark.jsonl"
]

def tail_file(filepath, lines=5):
    path = Path(filepath)
    if not path.exists():
        return ["[File not found or inactive]"]
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:] if line.strip()]
    except Exception as e:
        return [f"[Error reading file: {e}]"]

def render_dashboard():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("======================================================================")
        print(" SOVEREIGN INTELLIGENCE PROTOCOL — LIVE TERMINAL TELEMETRY DASHBOARD")
        print(f" Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')} | Refresh: 1s")
        print("======================================================================")

        for filepath in TELEMETRY_FILES:
            print(f"\n📂 [{filepath}]")
            print("-" * 70)
            for entry in tail_file(filepath, lines=3):
                print(f"  > {entry}")

        print("\n======================================================================")
        print(" Press Ctrl+C to exit dashboard.")
        print("======================================================================")
        time.sleep(1.0)

if __name__ == "__main__":
    render_dashboard()
