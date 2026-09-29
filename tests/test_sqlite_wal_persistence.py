import os
import sys
import time
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = "/tmp/sip_persistence_stress.db"
TARGET_OPS = 368000
BATCH_SIZE = 1000
NUM_THREADS = 16

def initialize_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA temp_store = MEMORY;")
    cursor.execute("PRAGMA mmap_size = 30000000000;")
    cursor.execute("PRAGMA locking_mode = EXCLUSIVE;")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_wal_log (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_uuid TEXT NOT NULL,
            payload_blob TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
    """)
    conn.close()

def worker_task(worker_id, ops_per_thread):
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = NORMAL;")
    
    local_batch = []
    start_time = time.perf_counter()
    
    for i in range(ops_per_thread):
        event_payload = f"node_{worker_id}_payload_seq_{i}"
        local_batch.append((f"node-uuid-{worker_id}", event_payload, time.time()))
        
        if len(local_batch) >= BATCH_SIZE:
            cursor.executemany(
                "INSERT INTO telemetry_wal_log (node_uuid, payload_blob, timestamp) VALUES (?, ?, ?)",
                local_batch
            )
            conn.commit()
            local_batch.clear()
            
    if local_batch:
        cursor.executemany(
            "INSERT INTO telemetry_wal_log (node_uuid, payload_blob, timestamp) VALUES (?, ?, ?)",
            local_batch
        )
        conn.commit()
        
    conn.close()
    return time.perf_counter() - start_time

def main():
    print(f"[+] Initializing SQLite WAL Stress Harness (Target: {TARGET_OPS} ops)...")
    initialize_database()
    ops_per_thread = TARGET_OPS // NUM_THREADS
    
    start_global = time.perf_counter()
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = [executor.submit(worker_task, i, ops_per_thread) for i in range(NUM_THREADS)]
        for f in as_completed(futures):
            f.result()
            
    total_duration = time.perf_counter() - start_global
    actual_ops = TARGET_OPS
    throughput = actual_ops / total_duration
    
    print(f"[+] Completed {actual_ops} operations across {NUM_THREADS} threads in {total_duration:.4f} seconds.")
    print(f"[+] Achieved Ingestion Rate: {throughput:,.2f} ops/sec")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM telemetry_wal_log;")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == TARGET_OPS:
        print(f"[✓] Persistence Validation Passed: Exact row match ({count:,} records).")
        sys.exit(0)
    else:
        print(f"[-] Persistence Mismatch Error: Expected {TARGET_OPS}, found {count}")
        sys.exit(1)

if __name__ == "__main__":
    main()
