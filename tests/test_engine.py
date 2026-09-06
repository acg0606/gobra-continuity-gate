from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from continuity import ContinuityEngine


class ContinuityEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "memory.db"
        self.engines: list[ContinuityEngine] = []
        self.engine = self.new_engine()
        self.engine.seed_case(
            "alpha",
            mission="Ship safely",
            human_gates=["submit", "publish"],
            required_evidence={"record_demo": ["working_demo"], "run_tests": []},
        )

    def tearDown(self) -> None:
        for engine in self.engines:
            engine.close()
        self.temp.cleanup()

    def new_engine(self) -> ContinuityEngine:
        engine = ContinuityEngine(self.db)
        self.engines.append(engine)
        return engine

    def test_fresh_session_recalls_policy_and_blocks_submission(self) -> None:
        fresh = self.new_engine()
        decision = fresh.evaluate("alpha", "submit")
        self.assertEqual("HOLD_HUMAN", decision.verdict)
        self.assertTrue(decision.recalled_policy)

    def test_missing_evidence_blocks_action(self) -> None:
        decision = self.engine.evaluate("alpha", "record_demo")
        self.assertEqual("NEED_EVIDENCE", decision.verdict)
        self.assertEqual(("working_demo",), decision.missing_evidence)

    def test_remembered_evidence_changes_next_decision(self) -> None:
        self.engine.remember_evidence("alpha", "working_demo", "verified local run #42")
        fresh = self.new_engine()
        decision = fresh.evaluate("alpha", "record_demo")
        self.assertEqual("ALLOW_LOCAL", decision.verdict)

    def test_safe_local_action_is_allowed(self) -> None:
        decision = self.engine.evaluate("alpha", "run_tests")
        self.assertEqual("ALLOW_LOCAL", decision.verdict)

    def test_unknown_case_fails_closed(self) -> None:
        decision = self.engine.evaluate("missing", "run_tests")
        self.assertEqual("MEMORY_REQUIRED", decision.verdict)
        self.assertFalse(decision.recalled_policy)

    def test_unlisted_action_fails_closed(self) -> None:
        for action in ("wire_money", "", "delete_repository"):
            with self.subTest(action=action):
                self.assertEqual("UNKNOWN_ACTION", self.engine.evaluate("alpha", action).verdict)

    def test_deletion_breaks_core_function_and_restores_fixture(self) -> None:
        result = self.engine.deletion_test("alpha")
        self.assertTrue(result["core_function_broke_safely"])
        self.assertEqual("MEMORY_REQUIRED", result["verdict_without_memory"])
        self.assertEqual("Ship safely", self.engine.status("alpha")["mission"])


if __name__ == "__main__":
    unittest.main()
