#!/usr/bin/env python3
import csv, os, sys

def print_hardware():
    print("=== HARDWARE MANIFEST ===")
    print("Test Host: 128 cores, 728 GB RAM")
    print("Architecture: AMD EPYC Bare-Metal Server")
    print("Location: Ashburn, Virginia")
    print("Environment: Debian/Linux")
    print("=========================")

def load_exp01():
    p = "evidence/bare_metal_2026/benchmark_summary.csv"
    print("\n=== EXP-01: SINGLE-THREAD PUSH MICROBENCHMARK ===")
    if not os.path.exists(p): sys.exit(1)
    with open(p, mode="r") as f:
        for r in csv.DictReader(f):
            if r.get("experiment_id") == "EXP-01":
                print(f"Capacity: {r.get('capacity', 'NOT_REPORTED')}")
                print(f"Workload: {r.get('workload_size', 'NOT_REPORTED')}")
                print(f"Duration (us): {r.get('duration_us', 'NOT_REPORTED')}")
                print(f"ns/op: {r.get('ns_per_operation', 'NOT_REPORTED')}")
                print(f"Run Status: {r.get('run_status', 'NOT_REPORTED')}")

def load_exp02():
    p = "evidence/bare_metal_2026/experiments/exp02_concurrent_handoff/benchmark_summary.csv"
    print("\n=== EXP-02: CONCURRENT PRODUCER/CONSUMER HANDOFF ===")
    if not os.path.exists(p): sys.exit(1)
    with open(p, mode="r") as f:
        for r in csv.DictReader(f):
            print(f"ID:{r.get('experiment_id','NOT_REPORTED')} | Cap:{r.get('capacity','NOT_REPORTED')} | Workload:{r.get('workload_size','NOT_REPORTED')} | Duration(us):{r.get('duration_us','NOT_REPORTED')} | ns/op:{r.get('ns_per_operation','NOT_REPORTED')} | Submitted:{r.get('submitted','NOT_REPORTED')} | Accepted:{r.get('accepted','NOT_REPORTED')} | Rejected:{r.get('rejected','NOT_REPORTED')} | Completed:{r.get('completed','NOT_REPORTED')} | Failed:{r.get('failed','NOT_REPORTED')} | Gaps:{r.get('sequence_gaps','NOT_REPORTED')} | Corruptions:{r.get('sequence_corruptions','NOT_REPORTED')} | Status:{r.get('run_status','NOT_REPORTED')}")

if __name__ == "__main__":
    print("Sovereign Seed Commons — offline-first, Git-native utility mesh for reproducible ephemeral cells.")
    print_hardware()
    load_exp01()
    load_exp02()
    print("\nSTATUS: OFFLINE SYNTHETIC DEMONSTRATION COMPLETE")
    print("SCOPE: utility validation; not live-data or production validation.")
