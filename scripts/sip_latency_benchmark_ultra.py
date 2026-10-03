import time, statistics, sqlite3

DB_PATH = "/tmp/sip_persistence_stress.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Ultra-performance pragmas
cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=OFF;")
cursor.execute("PRAGMA mmap_size=268435456;")
cursor.execute("PRAGMA temp_store=MEMORY;")
cursor.execute("CREATE TABLE IF NOT EXISTS stress_log (timestamp INTEGER, load_type TEXT, latency_ns INTEGER);")

# 1. Single-row un-synced commits
latencies_single = []
iterations = 1000

for _ in range(iterations):
    start = time.perf_counter_ns()
    cursor.execute("INSERT INTO stress_log VALUES (?, ?, ?)", (start, "SINGLE_UNSYNCED", 340))
    conn.commit()
    latencies_single.append((time.perf_counter_ns() - start) / 1000.0)

# 2. Batched transaction commits (100 events per explicit transaction block)
latencies_batch_per_event = []
batch_size = 100
batches = 50

for _ in range(batches):
    start = time.perf_counter_ns()
    cursor.execute("BEGIN TRANSACTION;")
    for _ in range(batch_size):
        cursor.execute("INSERT INTO stress_log VALUES (?, ?, ?)", (time.perf_counter_ns(), "BATCH_EVENT", 340))
    conn.commit()
    elapsed_us = (time.perf_counter_ns() - start) / 1000.0
    latencies_batch_per_event.append(elapsed_us / batch_size)

conn.close()

avg_single = statistics.mean(latencies_single)
p99_single = statistics.quantiles(latencies_single, n=100)[98]
avg_batch = statistics.mean(latencies_batch_per_event)

print("\n=== SOVEREIGN INTELLIGENCE PROTOCOL: ULTRA PERSISTENCE BENCHMARK ===")
print(f"[✓] Single-Row (sync=OFF) Avg Latency : {avg_single:.2f} µs")
print(f"[✓] Single-Row (sync=OFF) P99 Latency : {p99_single:.2f} µs")
print(f"[✓] Batched Effective Per-Event Latency: {avg_batch:.3f} µs ({avg_batch * 1000:.0f} ns)")
