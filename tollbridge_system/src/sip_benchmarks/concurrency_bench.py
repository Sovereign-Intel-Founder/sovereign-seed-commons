import sqlite3
import threading
import time
import os
import tempfile
from typing import Final

class SIPHighThroughputBenchmark:
    """
    Enterprise-grade concurrent SQLite WAL performance harness.
    Features busy-timeout tuning, WAL journaling, synchronous NORMAL optimization,
    and batched multi-lane transaction execution.
    """

    __slots__ = ("num_lanes", "ops_per_lane", "db_path")

    def __init__(self, num_lanes: int = 32, ops_per_lane: int = 500):
        self.num_lanes: Final[int] = num_lanes
        self.ops_per_lane: Final[int] = ops_per_lane
        self.db_path: Final[str] = os.path.join(tempfile.gettempdir(), "sip_high_throughput.db")

    def _init_database(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS high_throughput_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane_id INTEGER NOT NULL,
                payload_signature TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def _lane_worker(self, lane_id: int, latencies: list) -> None:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA busy_timeout=5000;")
        
        try:
            for i in range(self.ops_per_lane):
                start_op = time.perf_counter()
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    "INSERT INTO high_throughput_events (lane_id, payload_signature, created_at) VALUES (?, ?, ?)",
                    (lane_id, f"sig_lane_{lane_id}_op_{i}", time.time())
                )
                conn.commit()
                latencies.append(time.perf_counter() - start_op)
        finally:
            conn.close()

    def execute(self) -> float:
        print(f"[*] Initializing High-Throughput SQLite WAL Harness ({self.num_lanes} Lanes, {self.ops_per_lane} Ops/Lane)...")
        self._init_database()

        threads = []
        all_latencies = []
        lock = threading.Lock()

        def worker_wrapper(lane_id: int):
            lane_latencies = []
            self._lane_worker(lane_id, lane_latencies)
            with lock:
                all_latencies.extend(lane_latencies)

        global_start = time.perf_counter()
        for lane in range(self.num_lanes):
            t = threading.Thread(target=worker_wrapper, args=(lane,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        global_duration = time.perf_counter() - global_start
        total_ops = self.num_lanes * self.ops_per_lane
        throughput = total_ops / global_duration
        avg_latency_ms = (sum(all_latencies) / len(all_latencies)) * 1000.0 if all_latencies else 0.0

        print(f"\n[+] --- HIGH-THROUGHPUT BENCHMARK RESULTS ---")
        print(f"    - Total Operations : {total_ops}")
        print(f"    - Active Lanes     : {self.num_lanes}")
        print(f"    - Total Duration   : {global_duration:.4f} seconds")
        print(f"    - Throughput       : {throughput:.2f} ops/sec")
        print(f"    - Mean Latency     : {avg_latency_ms:.3f} ms/op")

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        return throughput

if __name__ == "__main__":
    harness = SIPHighThroughputBenchmark(num_lanes=16, ops_per_lane=250)
    harness.execute()
