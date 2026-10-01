import os
import time
import sqlite3
import asyncio
import logging
from typing import Dict, Any, Optional

from tollbridge.security import (
    verify_ed25519_envelope,
    verify_production_safety,
    verify_timestamp_freshness,
    MAX_TIMESTAMP_DRIFT_SEC,
)

logger = logging.getLogger("SIP.IngressMeteringEngine")


class BackpressureException(Exception):
    """Raised when the ingress queue exceeds capacity limits."""
    pass


class IngressMeteringEngine:
    """
    High-throughput async ingress metering engine for the Sovereign Intelligence Protocol.
    Handles non-blocking memory queueing, backpressure load shedding, sliding TTL nonce
    replay protection, multi-asset routing, and thread-offloaded SQLite WAL persistence.
    """

    def __init__(
        self,
        db_path: str = "revenue_vault.db",
        max_queue_depth: int = 10000,
        batch_size: int = 100,
        flush_interval_sec: float = 0.5,
        nonce_ttl_sec: float = MAX_TIMESTAMP_DRIFT_SEC
    ):
        self.db_path = db_path
        self.max_queue_depth = max_queue_depth
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self.nonce_ttl_sec = nonce_ttl_sec
        
        self.is_mainnet_live = verify_production_safety()
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_depth)
        
        # Sliding TTL Nonce Tracking: mapping nonce string to insertion epoch timestamp
        self.active_nonces: Dict[str, float] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._prune_task: Optional[asyncio.Task] = None
        self._running = False
        
        self._initialize_vault()

    def _get_connection(self) -> sqlite3.Connection:
        """Establishes an isolated SQLite connection optimized for WAL concurrency."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _initialize_vault(self) -> None:
        """Initializes database schema and performance indexing structures."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ingress_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_pubkey TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    payload_size_bytes INTEGER NOT NULL,
                    nonce TEXT UNIQUE,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pubkey ON ingress_telemetry(client_pubkey);")
            conn.commit()

    async def start(self) -> None:
        """Spawns background asynchronous flush workers and sliding TTL nonce pruners."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._vault_writer_loop())
            self._prune_task = asyncio.create_task(self._nonce_pruner_loop())
            logger.info("[INGRESS ENGINE] Async vault writer and nonce pruner workers active.")

    async def stop(self) -> None:
        """Gracefully drains the active queue and terminates background tasks."""
        self._running = False
        if self._worker_task:
            await self.queue.join()
            self._worker_task.cancel()
        if self._prune_task:
            self._prune_task.cancel()
        logger.info("[INGRESS ENGINE] Ingress queue drained and workers safely shut down.")

    def verify_envelope(self, client_pubkey: str, payload_bytes: bytes, signature_hex: str) -> bool:
        """Delegates cryptographic envelope verification to the security module."""
        return verify_ed25519_envelope(client_pubkey, payload_bytes, signature_hex)

    def _prune_expired_nonces(self) -> None:
        """Purges nonces exceeding the sliding TTL window to prevent unbounded memory growth."""
        now = time.time()
        cutoff = now - self.nonce_ttl_sec
        expired_keys = [k for k, ts in self.active_nonces.items() if ts < cutoff]
        for k in expired_keys:
            del self.active_nonces[k]
        if expired_keys:
            logger.debug(f"[NONCE PRUNER] Cleared {len(expired_keys)} expired nonces from active cache.")

    async def _nonce_pruner_loop(self) -> None:
        """Background maintenance loop executing nonce cleanup sweeps every 60 seconds."""
        while self._running:
            try:
                await asyncio.sleep(60.0)
                self._prune_expired_nonces()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[NONCE PRUNER ERROR] Maintenance loop exception: {e}")

    async def submit_payload(
        self,
        client_pubkey: str,
        raw_payload: bytes,
        signature_hex: str,
        nonce: str,
        asset_type: str = "SOL",
        timestamp_sec: Optional[float] = None,
        max_payload_bytes: int = 65536
    ) -> Dict[str, Any]:
        """
        Ingests a client packet through the complete validation pipeline:
        Size check -> Timestamp drift -> Ed25519 signature -> Nonce replay -> Backpressure check -> Enqueue.
        """
        # 1. Payload Size Hardening (DoS Mitigation)
        if not raw_payload or len(raw_payload) > max_payload_bytes:
            return {"status": "rejected", "code": 413, "reason": "PAYLOAD_TOO_LARGE"}

        # 2. Timestamp Freshness Check (Replay Prevention)
        if timestamp_sec is not None and not verify_timestamp_freshness(timestamp_sec):
            return {"status": "rejected", "code": 400, "reason": "TIMESTAMP_DRIFT_EXCEEDED"}

        # 3. Ed25519 Cryptographic Signature Check
        if not self.verify_envelope(client_pubkey, raw_payload, signature_hex):
            return {"status": "rejected", "code": 401, "reason": "INVALID_ED25519_SIGNATURE"}

        # 4. Nonce Replay Check (Sliding TTL Memory Cache)
        now = time.time()
        if nonce in self.active_nonces:
            if now - self.active_nonces[nonce] <= self.nonce_ttl_sec:
                return {"status": "rejected", "code": 409, "reason": "NONCE_REPLAY_DETECTED"}

        # 5. Queue Capacity & Backpressure Shedding Check
        if self.queue.full():
            logger.warning("[BACKPRESSURE] Ingress queue saturated. Shedding incoming load.")
            return {"status": "rejected", "code": 503, "reason": "BACKPRESSURE_QUEUE_FULL"}

        # 6. Enqueue Telemetry Event & Track Nonce
        event = {
            "pubkey": client_pubkey,
            "asset": asset_type,
            "size": len(raw_payload),
            "nonce": nonce,
            "timestamp": now
        }
        
        self.active_nonces[nonce] = now
        await self.queue.put(event)

        return {
            "status": "accepted",
            "code": 200,
            "bytes_metered": len(raw_payload),
            "asset": asset_type,
            "queue_depth": self.queue.qsize(),
            "live_mainnet": self.is_mainnet_live
        }

    async def _vault_writer_loop(self) -> None:
        """Background worker that pulls batched events and offloads disk I/O to worker threads."""
        while self._running or not self.queue.empty():
            batch = []
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=self.flush_interval_sec)
                batch.append(item)
                self.queue.task_done()

                while len(batch) < self.batch_size and not self.queue.empty():
                    b_item = self.queue.get_nowait()
                    batch.append(b_item)
                    self.queue.task_done()

            except asyncio.TimeoutError:
                pass

            if batch:
                # Offload blocking SQLite disk operations to thread pool to preserve event loop latency
                await asyncio.to_thread(self._persist_batch, batch)

    def _persist_batch(self, batch: list) -> None:
        """Executes a thread-safe, transactional batch insert into the SQLite WAL database."""
        try:
            conn = self._get_connection()
            with conn:
                conn.executemany(
                    "INSERT INTO ingress_telemetry (client_pubkey, asset_type, payload_size_bytes, nonce) VALUES (?, ?, ?, ?);",
                    [(item["pubkey"], item["asset"], item["size"], item["nonce"]) for item in batch]
                )
            conn.close()
        except Exception as e:
            logger.error(f"[VAULT PERSISTENCE ERROR] Failed writing batch of {len(batch)} items: {e}")
