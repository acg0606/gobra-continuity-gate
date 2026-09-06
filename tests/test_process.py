from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import run_fresh_command


class FreshProcessTests(unittest.TestCase):
    def test_memory_crosses_real_processes_and_evidence_changes_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "process.db"
            seeded = run_fresh_command(database, "seed")
            recalled = run_fresh_command(database, "status")
            self.assertNotEqual(seeded["process"]["pid"], recalled["process"]["pid"])
            self.assertEqual(seeded["mission"], recalled["mission"])
            self.assertEqual("NEED_EVIDENCE", run_fresh_command(database, "evaluate", "record_demo")["verdict"])
            run_fresh_command(database, "remember-evidence", "working_demo", "test fixture")
            self.assertEqual("ALLOW_LOCAL", run_fresh_command(database, "evaluate", "record_demo")["verdict"])
            self.assertEqual("HOLD_HUMAN", run_fresh_command(database, "evaluate", "submit")["verdict"])
            self.assertEqual("UNKNOWN_ACTION", run_fresh_command(database, "evaluate", "invented_action")["verdict"])
            deleted = run_fresh_command(database, "deletion-test")
            self.assertTrue(deleted["core_function_broke_safely"])
            self.assertEqual(seeded["mission"], run_fresh_command(database, "status")["mission"])
