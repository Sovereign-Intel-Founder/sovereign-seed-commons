import unittest
import os
import subprocess

class TestCellRunner(unittest.TestCase):
    def test_verify_clean(self):
        os.environ["SOVEREIGN_SECRET"] = "sovereign_ephemeral_key_999"
        res = subprocess.run(["python3", "tools/cell_runner.py", "verify"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_missing_secret(self):
        env = os.environ.copy()
        env.pop("SOVEREIGN_SECRET", None)
        res = subprocess.run(["python3", "tools/cell_runner.py", "verify"], env=env, capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)

if __name__ == "__main__":
    unittest.main()
