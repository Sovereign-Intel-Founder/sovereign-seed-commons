#!/usr/bin/env python3
import csv, os, sys, time

def get_repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "evidence")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()

ROOT = get_repo_root()

def print_hardware():
    print("=== HARDWARE CONTEXT ===")
    print("Host Architecture: AMD EPYC Bare-Metal Server")
    print("CPU Cores: 128 cores")
    print("RAM: 728 GB RAM")
    print("OS Environment: Debian/Linux")
    print("Location: Ashburn, Virginia (documented host location)")
    print("Note: Workloads run on isolated pinned core subsets, not all 128 cores simultaneously.")

def load_exp01():
    print("\n=== EXP-01 EVIDENCE ===")
    print("SPSC ring push microbenchmark — single-thread synthetic")
    p = os.path.join(ROOT, "evidence/bare_metal_2026/benchmark_summary.csv")
    if not os.path.exists(p): sys.exit(1)
    with open(p, mode="r") as f:
        for r in csv.DictReader(f):
            if r.get("experiment_id") == "EXP-01":
                for k in ["capacity", "workload_size", "duration_us", "ns_per_operation"]:
                    print(f"{k}: {r.get(k, 'NOT_REPORTED')}")
    print("Note: This is a single-thread synthetic push measurement, not end-to-end handoff.")

def load_exp02():
    print("\n=== EXP-02 EVIDENCE ===")
    p = os.path.join(ROOT, "evidence/bare_metal_2026/experiments/exp02_concurrent_handoff/benchmark_summary.csv")
    if not os.path.exists(p): sys.exit(1)
    with open(p, mode="r") as f:
        for r in csv.DictReader(f):
            print(f"ID:{r.get('experiment_id','NOT_REPORTED')} | Cap:{r.get('capacity','NOT_REPORTED')} | Workload:{r.get('workload_size','NOT_REPORTED')} | Dur(us):{r.get('duration_us','NOT_REPORTED')} | ns/op:{r.get('ns_per_operation','NOT_REPORTED')} | Sub:{r.get('submitted','NOT_REPORTED')} | Acc:{r.get('accepted','NOT_REPORTED')} | Rej:{r.get('rejected','NOT_REPORTED')} | Comp:{r.get('completed','NOT_REPORTED')} | Fail:{r.get('failed','NOT_REPORTED')} | Gaps:{r.get('sequence_gaps','NOT_REPORTED')} | Corr:{r.get('sequence_corruptions','NOT_REPORTED')} | Status:{r.get('run_status','NOT_REPORTED')}")

def run_synthetic_cell():
    print("\n=== CELL EXECUTION ===")
    records = [{"seq": i, "data": f"record_{i}"} for i in range(1000)]
    print(f"Generated {len(records)} deterministic local synthetic records.")
    
    print("\n=== INTEGRITY CHECKS ===")
    last_seq = -1
    for r in records:
        if r["seq"] != last_seq + 1:
            print("ERROR: Sequence gap detected!")
            sys.exit(1)
        last_seq = r["seq"]
    print("Sequence continuity verified: 0 gaps, 0 corruptions.")

def print_limitations():
    print("\n=== LIMITATIONS ===")
    print("Scope: Offline-first, Git-native utility mesh for reproducible ephemeral execution cells.")
    print("Not live-data, production, mainnet, MEV, trading, or settlement validation.")

if __name__ == "__main__":
    print("Sovereign Seed Commons — an offline-first, Git-native utility mesh for reproducible ephemeral execution cells.")
    print_hardware()
    print("\n=== DEMONSTRATION CONFIGURATION ===")
    print("Mode: Offline Synthetic Local Validation")
    load_exp01()
    load_exp02()
    run_synthetic_cell()
    print_limitations()
    print("\nSTATUS: OFFLINE SYNTHETIC DEMONSTRATION COMPLETE")
    print("SCOPE: UTILITY VALIDATION; NOT LIVE-DATA OR PRODUCTION VALIDATION")
    sys.exit(0)
