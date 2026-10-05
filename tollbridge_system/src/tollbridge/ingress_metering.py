import os
import time
import hashlib
import sqlite3
import asyncio
import logging
from typing import Dict, Any, Optional

from tollbridge.security import (
    build_canonical_envelope_bytes,
    verify_timestamp_freshness,
    verify_ed25519_envelope
)

logger = logging.getLogger("SIP.IngressMetering")


class IngressMeteringEngine:
    """
    High-throughput, asynchronous ingestion engine for the Sovereign Intelligence Protocol.
    Validates cryptographic envelopes, enforces strict nonce-based idempotency to prevent 
    replays, and batches raw payloads into a durable SQLite WAL vault.
    """

    def __init__(
        self,
        db_path: str = "sip_ingress_vault.db",
        max_queue_depth: int = 10000,
        batch_size: int = 500,
        flush_interval_sec: float = 0.1
    ):
        self.db_path = db_path
        self.max_queue_depth = max_queue_depth
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec

        # Concurrency & Queue Primitives
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue_depth)
        self._db_conn: Optional[sqlite3.Connection] = None
        self._writer_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """
        Boots the engine, initializes the persistent SQLite WAL database, 
        establishes rigorous schemas, and starts the asynchronous background flush worker.
        """
        logger.info(f"[INGRESS] Booting Metering Engine. DB Path: {self.db_path}")
        
        # Open connection for the lifetime of the engine.
        # check_same_thread=False allows background thread delegation for concurrent DB I/O.
        self._db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db_conn.row_factory = sqlite3.Row
        
        cursor = self._db_conn.cursor()
        
        # Apply strict performance and durability PRAGMAs
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        
        # Schema 1: The Idempotency Vault (Strict Replay Protection)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS idempotency_vault (
                client_pubkey TEXT NOT NULL,
                nonce TEXT NOT NULL,
                timestamp_sec REAL NOT NULL,
                signature_hex TEXT NOT NULL,
                PRIMARY KEY (client_pubkey, nonce)
            )
        ''')
        
        # Schema 2: Batch Telemetry / Payload Storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingress_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_pubkey TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                subscription_topic TEXT NOT NULL,
                envelope_hash TEXT NOT NULL,
                content_type TEXT NOT NULL,
                payload_blob BLOB NOT NULL,
                ingested_at_sec REAL NOT NULL
            )
        ''')
        self._db_conn.commit()
        
        self._stop_event.clear()
        self._writer_task = asyncio.create_task(self._batch_writer_loop())
        logger.info("[INGRESS] Engine started. WAL tables verified. Worker loop running.")

    async def stop(self) -> None:
        """
        Gracefully drains the in-memory queue, flushes pending batches to disk, 
        and securely terminates database connections.
        """
        logger.info("[INGRESS] Stop signal received. Draining queues and flushing to WAL...")
        self._stop_event.set()
        
        if self._writer_task:
            await self._writer_task
        
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None
            
        logger.info("[INGRESS] Engine stopped cleanly. All data persisted.")

    async def submit_envelope_payload(
        self,
        protocol_version: str,
        client_pubkey: str,
        nonce: str,
        timestamp_sec: float,
        asset_type: str,
        subscription_topic: str,
        content_type: str,
        raw_payload: bytes,
        signature_hex: str
    ) -> Dict[str, Any]:
        """
        Primary entrypoint for incoming telemetry. Conducts complete security validation,
        synchronous idempotency checks, and asynchronous queueing.
        """
        
        # 1. Clock Drift / Stale Payload Check
        if not verify_timestamp_freshness(timestamp_sec):
            return {"status": "rejected", "reason": "TIMESTAMP_STALE"}

        # 2. SHA-256 Payload Hashing
        payload_hash = hashlib.sha256(raw_payload).hexdigest()

        # 3. Canonical Binding & Ed25519 Cryptographic Verification
        canonical_bytes = build_canonical_envelope_bytes(
            protocol_version=protocol_version,
            client_pubkey=client_pubkey,
            nonce=nonce,
            timestamp=timestamp_sec,
            asset_type=asset_type,
            payload_hash=payload_hash,
            content_type=content_type,
            subscription_topic=subscription_topic
        )

        is_valid, verify_reason = verify_ed25519_envelope(
            client_pubkey=client_pubkey,
            canonical_bytes=canonical_bytes,
            signature_hex=signature_hex
        )

        if not is_valid:
            return {"status": "rejected", "reason": verify_reason}

        # 4. Immediate Durable Idempotency Check
        # Offloaded to a native thread to prevent blocking the async event loop during spikes.
        try:
            await asyncio.to_thread(
                self._insert_idempotency_record_sync,
                client_pubkey,
                nonce,
                timestamp_sec,
                signature_hex
            )
        except sqlite3.IntegrityError:
            logger.warning(f"[INGRESS] Replay detected and blocked: Pubkey {client_pubkey[:8]}... / Nonce {nonce}")
            return {"status": "rejected", "reason": "NONCE_REPLAY_DETECTED"}
        except Exception as e:
            logger.error(f"[INGRESS] Database fault during idempotency check: {e}")
            return {"status": "rejected", "reason": "INTERNAL_DATABASE_FAULT"}

        # 5. Fast-Path Queue Submission
        item = (
            client_pubkey,
            asset_type,
            subscription_topic,
            payload_hash,
            content_type,
            raw_payload,
            time.time()
        )

        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            logger.error("[INGRESS] Backpressure threshold exceeded. Queue is full.")
            return {"status": "rejected", "reason": "BACKPRESSURE_REJECTION_QUEUE_FULL"}

        return {"status": "accepted", "reason": "OK"}

    def _insert_idempotency_record_sync(self, pubkey: str, nonce: str, ts: float, sig: str) -> None:
        """
        Synchronous database execution strictly wrapped for thread pool delegation.
        """
        cursor = self._db_conn.cursor()
        cursor.execute(
            "INSERT INTO idempotency_vault (client_pubkey, nonce, timestamp_sec, signature_hex) VALUES (?, ?, ?, ?)",
            (pubkey, nonce, ts, sig)
        )
        self._db_conn.commit()

    async def _batch_writer_loop(self) -> None:
        """
        Background autonomous worker cell. Pulls verified payloads from memory and executes 
        high-efficiency batched writes into the SQLite WAL to maximize disk throughput.
        """
        batch = []
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=self.flush_interval_sec)
                batch.append(item)
            except asyncio.TimeoutError:
                # Expected behavior. Proceed to flush whatever is currently in the batch.
                pass
            except asyncio.CancelledError:
                break

            if len(batch) >= self.batch_size or (batch and self._stop_event.is_set()):
                await self._flush_batch_to_wal(batch)
                for _ in batch:
                    self._queue.task_done()
                batch.clear()

        # Final drain guarantee upon shutdown
        if batch:
            await self._flush_batch_to_wal(batch)
            for _ in batch:
                self._queue.task_done()
            batch.clear()

    async def _flush_batch_to_wal(self, batch: list) -> None:
        """
        Offloads the heavy `executemany` disk write operation to the thread pool.
        """
        if not batch:
            return

        def execute_insert():
            cursor = self._db_conn.cursor()
            cursor.executemany('''
                INSERT INTO ingress_telemetry 
                (client_pubkey, asset_type, subscription_topic, envelope_hash, content_type, payload_blob, ingested_at_sec)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            self._db_conn.commit()

        try:
            await asyncio.to_thread(execute_insert)
            logger.debug(f"[INGRESS] Successfully flushed batch of {len(batch)} telemetry records to WAL.")
        except Exception as e:
            logger.critical(f"[INGRESS] Catastrophic failure flushing telemetry batch to WAL: {e}")
