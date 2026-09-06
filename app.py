from __future__ import annotations

import argparse
import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

from continuity import ContinuityEngine  # noqa: E402


DEFAULT_DB = ROOT / ".continuity" / "memory.db"
CASE_ID = "voice-challenge"


def new_engine(database: Path) -> ContinuityEngine:
    return ContinuityEngine(database)


def seed(engine: ContinuityEngine) -> dict:
    return engine.seed_case(
        CASE_ID,
        mission="Prepare an evidence-linked hackathon entry without fabricating proof or crossing human gates.",
        human_gates=["publish", "submit", "accept_terms", "send_form", "move_funds"],
        required_evidence={
            "finalize_claims": ["official_rules", "working_demo"],
            "record_demo": ["working_demo"],
            "prepare_local_draft": [],
            "run_tests": [],
        },
        evidence={"official_rules": "Verified official rules snapshot, 2026-09-02 UTC"},
    )


def run_demo(database: Path) -> dict:
    seeded = run_fresh_command(database, "seed")
    first_decision = run_fresh_command(database, "evaluate", "prepare_local_draft")
    recalled = run_fresh_command(database, "status")
    blocked = run_fresh_command(database, "evaluate", "submit")
    missing = run_fresh_command(database, "evaluate", "record_demo")
    remembered = run_fresh_command(database, "remember-evidence", "working_demo", "Synthetic demo fixture: recorded local run")
    allowed = run_fresh_command(database, "evaluate", "record_demo")
    deletion = run_fresh_command(database, "deletion-test")
    return {
        "mode": "LOCAL_VERIFIED",
        "fresh_session": True,
        "memory_backend": recalled["memory_backend"],
        "process_model": "One new Python process per command; no inherited engine or policy object",
        "seed_process": seeded["process"],
        "recall_process": recalled["process"],
        "first_decision": first_decision,
        "recalled_mission": recalled["mission"],
        "recalled_human_gate": blocked,
        "recalled_evidence_gate": missing,
        "remembered_evidence_process": remembered["process"],
        "decision_after_evidence": allowed,
        "deletion_test": deletion,
        "external_action_performed": False,
    }


def run_fresh_command(database: Path, *command: str) -> dict:
    """Exercise real process isolation while keeping the same Sibyl database."""
    completed = subprocess.run(
        [sys.executable, str(ROOT / "app.py"), "--database", str(database), *command],
        capture_output=True, text=True, check=True, timeout=25,
    )
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="GoBRA Continuity Gate")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("action")
    evidence = sub.add_parser("remember-evidence")
    evidence.add_argument("key")
    evidence.add_argument("value")
    sub.add_parser("status")
    sub.add_parser("demo")
    sub.add_parser("deletion-test")
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=4346)
    args = parser.parse_args()

    if args.command == "demo":
        result = run_demo(args.database)
    elif args.command == "serve":
        from continuity.server import serve

        serve(
            database=args.database,
            web_root=ROOT / "web",
            case_id=CASE_ID,
            host=args.host,
            port=args.port,
        )
        return 0
    else:
        engine = new_engine(args.database)
        try:
            if args.command == "seed":
                result = seed(engine)
            elif args.command == "evaluate":
                result = engine.evaluate(CASE_ID, args.action).to_dict()
            elif args.command == "remember-evidence":
                result = engine.remember_evidence(CASE_ID, args.key, args.value)
            elif args.command == "status":
                try:
                    result = engine.status(CASE_ID)
                except Exception as error:
                    from sibyl_memory_client.exceptions import NotFoundError
                    if not isinstance(error, NotFoundError):
                        raise
                    result = {"case_id": CASE_ID, "verdict": "MEMORY_REQUIRED", "seeded": False}
            else:
                result = engine.deletion_test(CASE_ID)
        finally:
            engine.close()

    result["process"] = {"pid": os.getpid(), "utc": datetime.now(timezone.utc).isoformat(), "fresh_process_per_request": True}

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
