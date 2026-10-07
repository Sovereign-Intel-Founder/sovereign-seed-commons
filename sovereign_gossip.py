#!/usr/bin/env python3
"""
Sovereign Intelligence Protocol - Hardened Bare-Metal Mesh Engine
Sub-Millisecond Non-Blocking UDP Gossip Daemon with SQLite WAL Persistence
"""

import sys
import os
import time
import socket
import select
import struct
import uuid
import hashlib
import sqlite3
import logging
from typing import Dict, Tuple, Optional

# Configure high-throughput logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Binary Fixed-Size Protocol Contract (64 Bytes Total)
# Structure:
#   - 12 Bytes: Node Hash ID
#   -  1 Byte : Message Type (1 = PING, 2 = ACK, 3 = JOIN)
#   -  2 Bytes: Node Port (Unsigned Short)
#   -  8 Bytes: High-Precision Timestamp (Double)
#   - 41 Bytes: Reserved Payload / Padding
PACKET_FORMAT = "!12sBHd41s"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)

# Message Types
MSG_PING = 1
MSG_ACK = 2
MSG_JOIN = 3

# Timeout & Failure Parameters
PING_INTERVAL_SEC = 2.0
PEER_TIMEOUT_SEC = 10.0
DB_FILE = "mesh_topology.db"


def derive_hardware_node_id() -> str:
    """Derives a deterministic, unique node identity bound to host hardware MAC and hostname."""
    mac = uuid.getnode()
    hostname = socket.gethostname()
    raw = f"{hostname}:{mac}"
    node_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]
    return f"commons-{node_hash}"


class TopologyStore:
    """Zero-overhead WAL-mode SQLite database engine for persisting mesh peer topology across daemon restarts."""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        # Enable Write-Ahead Logging (WAL) mode for fast concurrent reads/writes
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS peers (
                    node_id TEXT PRIMARY KEY,
                    ip TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    last_seen REAL NOT NULL,
                    status TEXT NOT NULL
                );
            """)
            conn.commit()

    def upsert_peer(self, node_id: str, ip: str, port: int, status: str = "ACTIVE"):
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO peers (node_id, ip, port, last_seen, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    ip=excluded.ip,
                    port=excluded.port,
                    last_seen=excluded.last_seen,
                    status=excluded.status;
            """, (node_id, ip, port, now, status))
            conn.commit()

    def get_active_peers(self, timeout_sec: float = PEER_TIMEOUT_SEC) -> Dict[str, Tuple[str, int]]:
        cutoff = time.time() - timeout_sec
        active_peers = {}
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT node_id, ip, port FROM peers WHERE last_seen >= ? AND status = 'ACTIVE'",
                (cutoff,)
            )
            for row in cursor.fetchall():
                active_peers[row[0]] = (row[1], int(row[2]))
        return active_peers

    def mark_dead_peers(self, timeout_sec: float = PEER_TIMEOUT_SEC):
        cutoff = time.time() - timeout_sec
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE peers SET status = 'DEAD' WHERE last_seen < ? AND status = 'ACTIVE'",
                (cutoff,)
            )
            conn.commit()


class SovereignMeshEngine:
    """Hardened, Non-blocking UDP Gossip Engine with Binary Struct Packing."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.node_id = derive_hardware_node_id()
        self.node_id_bytes = self.node_id.encode('utf-8')[:12].ljust(12, b'\x00')
        self.store = TopologyStore()
        self.sock: Optional[socket.socket] = None
        self._setup_socket()

    def _setup_socket(self):
        """Initializes non-blocking UDP socket with kernel buffer optimizations."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Expand kernel receive/send buffer sizes for high packet density
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
        self.sock.setblocking(False)
        self.sock.bind((self.host, self.port))
        logging.info(f"SIP Mesh Engine bound to {self.host}:{self.port} | Node ID: {self.node_id}")

    def pack_payload(self, msg_type: int) -> bytes:
        """Packs metadata into fixed 64-byte binary payload."""
        return struct.pack(
            PACKET_FORMAT,
            self.node_id_bytes,
            msg_type,
            self.port,
            time.time(),
            b'\x00' * 41
        )

    def unpack_payload(self, data: bytes) -> Optional[Tuple[str, int, int, float]]:
        """Unpacks and validates binary payload format."""
        if len(data) != PACKET_SIZE:
            return None
        try:
            raw_id, msg_type, port, ts, _ = struct.unpack(PACKET_FORMAT, data)
            remote_node_id = raw_id.decode('utf-8').rstrip('\x00')
            return remote_node_id, msg_type, port, ts
        except Exception:
            return None

    def send_packet(self, ip: str, port: int, msg_type: int):
        payload = self.pack_payload(msg_type)
        try:
            self.sock.sendto(payload, (ip, port))
        except OSError as e:
            logging.warning(f"Socket transmission error to {ip}:{port} -> {e}")

    def seed_initial_peer(self, peer_ip: str, peer_port: int):
        """Dispatches an immediate JOIN payload to seed a new mesh node."""
        logging.info(f"Seeding initial mesh connection to {peer_ip}:{peer_port}")
        self.send_packet(peer_ip, peer_port, MSG_JOIN)

    def process_incoming_packets(self):
        """Reads non-blocking incoming UDP datagrams without kernel stalling."""
        while True:
            try:
                data, addr = self.sock.recvfrom(2048)
                unpacked = self.unpack_payload(data)
                if not unpacked:
                    continue

                remote_node_id, msg_type, remote_port, ts = unpacked

                # Ignore self-loopbacks
                if remote_node_id == self.node_id:
                    continue

                sender_ip = addr[0]

                # Update WAL SQLite store
                self.store.upsert_peer(remote_node_id, sender_ip, remote_port, status="ACTIVE")

                # Handle message protocol states
                if msg_type in (MSG_PING, MSG_JOIN):
                    # Immediately ACK incoming PING or JOIN request
                    self.send_packet(sender_ip, remote_port, MSG_ACK)
                    logging.debug(f"[GOSSIP_RECV] Received PING/JOIN from {remote_node_id} @ {sender_ip}:{remote_port}")

                elif msg_type == MSG_ACK:
                    logging.debug(f"[HEARTBEAT_ACK] Received ACK from {remote_node_id}")

            except (BlockingIOError, InterruptedError):
                break  # Buffer emptied
            except Exception as e:
                logging.error(f"Error processing packet: {e}")
                break

    def run_gossip_cycle(self):
        """Dispatches binary ping frames to all known active peers in SQLite mesh table."""
        active_peers = self.store.get_active_peers()
        for peer_id, (ip, port) in active_peers.items():
            if peer_id != self.node_id:
                self.send_packet(ip, port, MSG_PING)
                logging.debug(f"[HEARTBEAT_SENT] PING -> {peer_id} @ {ip}:{port}")

        # Evict dead peers exceeding timeout threshold
        self.store.mark_dead_peers()

    def start(self, seed_peer: Optional[Tuple[str, int]] = None):
        if seed_peer:
            self.seed_initial_peer(seed_peer[0], seed_peer[1])

        last_ping_time = 0.0
        logging.info("Mesh Execution Engine active. Entering high-performance non-blocking event loop...")

        try:
            while True:
                now = time.time()

                # Process all buffered incoming UDP sockets using select I/O multiplexing
                r, _, _ = select.select([self.sock], [], [], 0.1)
                if r:
                    self.process_incoming_packets()

                # Execute binary gossip round at defined interval
                if now - last_ping_time >= PING_INTERVAL_SEC:
                    self.run_gossip_cycle()
                    last_ping_time = now

                    # Print active cluster health status
                    peers = self.store.get_active_peers()
                    logging.info(f"[CLUSTER_STATE] Node: {self.node_id} | Active Mesh Nodes: {len(peers)}")

        except KeyboardInterrupt:
            logging.info("Shutting down SIP Mesh Engine cleanly...")
        finally:
            if self.sock:
                self.sock.close()


if __name__ == "__main__":
    bind_port = 9999
    seed_target = None

    if len(sys.argv) > 1:
        bind_port = int(sys.argv[1])

    if len(sys.argv) > 2:
        parts = sys.argv[2].split(":")
        seed_target = (parts[0], int(parts[1]))

    engine = SovereignMeshEngine(port=bind_port)
    engine.start(seed_peer=seed_target)
