#!/usr/bin/env python3
"""
Comprehensive Unit Test Suite for Sovereign Seed Ephemeral Cell Runner
Covers all positive and negative security, verification, and execution constraints.
"""

import unittest
import subprocess
import os
import json
import hashlib
import hmac
from pathlib import Path

class TestCellRunnerComprehensive(unittest.TestCase):
    
    def setUp(self):
        self.runner = "tools/cell_runner.py"
        self.mutation_path = "experiments/mutations/test_mutation.json"
        Path("experiments/mutations").mkdir(parents=True, exist_ok=True)
        
        self.head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        
        self.valid_packet = {
            "mutation_id": "mut-comp-001",
            "parent_commit": self.head,
            "objective": "Run valid test objective",
            "allowed_paths": ["tools/"],
            "allowed_commands": ["python3", "-c", "print('OK')"],
            "timeout_seconds": 5,
            "submission_policy": "local_only"
        }
        self.sign_packet(self.valid_packet)

    def sign_packet(self, packet: dict) -> None:
        secret = b"sovereign_ephemeral_key_999"
        payload = {k: v for k, v in packet.items() if k != "signature"}
        packet["signature"] = hmac.new(
            secret, 
            json.dumps(payload, sort_keys=True).encode("utf-8"), 
            hashlib.sha256
        ).hexdigest()
        with open(self.mutation_path, "w", encoding="utf-8") as f:
            json.dump(packet, f, indent=2)

    def test_01_clean_verification(self):
        res = subprocess.run(["python3", self.runner, "verify"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Boot verification passed", res.stdout)

    def test_02_dry_run_zero_network(self):
        res = subprocess.run(["python3", self.runner, "dry-run", "--mutation", self.mutation_path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Dry run complete", res.stdout)
        self.assertIn("Zero network calls made", res.stdout)

    def test_03_invalid_mutation_signature(self):
        self.valid_packet["signature"] = "forged_invalid_signature_string"
        with open(self.mutation_path, "w", encoding="utf-8") as f:
            json.dump(self.valid_packet, f)
        res = subprocess.run(["python3", self.runner, "dry-run", "--mutation", self.mutation_path], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Invalid mutation packet signature", res.stderr)

    def test_04_wrong_parent_commit(self):
        self.valid_packet["parent_commit"] = "0000000000000000000000000000000000000000"
        self.sign_packet(self.valid_packet)
        res = subprocess.run(["python3", self.runner, "dry-run", "--mutation", self.mutation_path], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Parent commit mismatch", res.stderr)

    def test_05_forbidden_path_rejection(self):
        self.valid_packet["allowed_paths"] = ["etc/passwd"]
        self.sign_packet(self.valid_packet)
        res = subprocess.run(["python3", self.runner, "dry-run", "--mutation", self.mutation_path], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Forbidden path requested", res.stderr)

    def test_06_forbidden_command_rejection(self):
        self.valid_packet["allowed_commands"] = ["rm", "-rf", "/"]
        self.sign_packet(self.valid_packet)
        res = subprocess.run(["python3", self.runner, "dry-run", "--mutation", self.mutation_path], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Forbidden dangerous command keyword detected", res.stderr)

    def test_07_timeout_enforcement(self):
        self.valid_packet["allowed_commands"] = ["sleep", "10"]
        self.valid_packet["timeout_seconds"] = 1
        self.sign_packet(self.valid_packet)
        res = subprocess.run(["python3", self.runner, "run", "--mutation", self.mutation_path], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)

    def test_08_package_and_missing_credentials(self):
        env = os.environ.copy()
        if "GITHUB_TOKEN" in env:
            del env["GITHUB_TOKEN"]
        res = subprocess.run(["python3", self.runner, "submit"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Local safe package created", res.stdout)
        self.assertTrue(Path("genesis/resurrection_bundle.tar.gz").exists())

    def test_09_single_shot_exit_and_no_daemon(self):
        res = subprocess.run(["python3", self.runner, "verify"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        # Ensure no legacy Unix socket or daemon artifacts exist or are required
        self.assertFalse(Path("/tmp/sovereign_comm.sock").exists())

if __name__ == "__main__":
    unittest.main()
