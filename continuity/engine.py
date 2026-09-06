from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient
from sibyl_memory_client.exceptions import NotFoundError


MEMORY_CATEGORY = "continuity_case"


@dataclass(frozen=True)
class Decision:
    case_id: str
    action: str
    verdict: str
    reason: str
    recalled_policy: bool
    missing_evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_evidence"] = list(self.missing_evidence)
        return payload


class ContinuityEngine:
    """A fail-closed action gate whose policy exists only in Sibyl Memory."""

    def __init__(self, database: str | Path, *, tenant: str = "gobra") -> None:
        self.database = Path(database)
        self.memory = MemoryClient.local(self.database, tenant_id=tenant)

    def seed_case(
        self,
        case_id: str,
        *,
        mission: str,
        human_gates: list[str],
        required_evidence: dict[str, list[str]],
        evidence: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = {
            "mission": mission,
            "human_gates": sorted(set(human_gates)),
            "required_evidence": required_evidence,
            "evidence": evidence or {},
            "safety_mode": "FAIL_CLOSED",
        }
        entity = self.memory.set_entity(MEMORY_CATEGORY, case_id, body, status="active")
        self.memory.set_state(
            f"case:{case_id}:runtime",
            {"session": 1, "last_decision": None, "pending": []},
        )
        self.memory.write_event(
            acted=[f"seeded continuity case {case_id}"],
            forward=["open a fresh session and evaluate the next action"],
            extra={"case_id": case_id, "source": "SIBYL_MEMORY"},
        )
        return entity["body"]

    def remember_evidence(self, case_id: str, key: str, value: str) -> dict[str, Any]:
        policy = self._policy(case_id)
        policy["evidence"][key] = value
        self.memory.set_entity(MEMORY_CATEGORY, case_id, policy, status="active")
        self.memory.write_event(
            evaluated=[f"evidence {key} received"],
            acted=[f"updated case {case_id}"],
            extra={"case_id": case_id, "evidence_key": key},
        )
        return policy

    def evaluate(self, case_id: str, action: str) -> Decision:
        action_key = action.strip().lower()
        try:
            policy = self._policy(case_id)
        except NotFoundError:
            return Decision(
                case_id=case_id,
                action=action_key,
                verdict="MEMORY_REQUIRED",
                reason="No Sibyl Memory record was recalled, so the agent cannot act safely.",
                recalled_policy=False,
            )

        required = policy["required_evidence"].get(action_key, [])
        missing = tuple(key for key in required if not policy["evidence"].get(key))
        if action_key in policy["human_gates"]:
            verdict = "HOLD_HUMAN"
            reason = "The recalled policy marks this action as requiring explicit human approval."
        elif action_key not in policy["required_evidence"]:
            verdict = "UNKNOWN_ACTION"
            reason = "The recalled policy does not authorize this action. Add an explicit policy rule before proceeding."
        elif missing:
            verdict = "NEED_EVIDENCE"
            reason = "The recalled policy requires evidence that is not yet present."
        else:
            verdict = "ALLOW_LOCAL"
            reason = "The recalled policy permits this local action and its evidence gates are satisfied."

        decision = Decision(
            case_id=case_id,
            action=action_key,
            verdict=verdict,
            reason=reason,
            recalled_policy=True,
            missing_evidence=missing,
        )
        self.memory.set_state(
            f"case:{case_id}:runtime",
            {"last_decision": decision.to_dict(), "pending": list(missing)},
        )
        self.memory.write_event(
            evaluated=[decision.to_dict()],
            acted=[] if verdict != "ALLOW_LOCAL" else [f"authorized local action: {action_key}"],
            forward=[reason],
            extra={"case_id": case_id, "memory_is_load_bearing": True},
        )
        return decision

    def status(self, case_id: str) -> dict[str, Any]:
        policy = self._policy(case_id)
        runtime = self.memory.get_state(f"case:{case_id}:runtime")
        return {
            "case_id": case_id,
            "mission": policy["mission"],
            "safety_mode": policy["safety_mode"],
            "human_gates": policy["human_gates"],
            "evidence": policy["evidence"],
            "runtime": runtime["body"] if runtime else None,
            "memory_backend": "Sibyl Memory / SQLite + FTS5",
        }

    def deletion_test(self, case_id: str) -> dict[str, Any]:
        policy = self._policy(case_id)
        deleted = self.memory.delete_entity(MEMORY_CATEGORY, case_id)
        after = self.evaluate(case_id, "prepare_local_draft")
        self.memory.set_entity(MEMORY_CATEGORY, case_id, policy, status="active")
        self.memory.write_event(
            evaluated=["deletion test"],
            acted=["restored policy after isolated test"],
            extra={"case_id": case_id, "deleted": deleted, "verdict_without_memory": after.verdict},
        )
        return {
            "deleted": deleted,
            "verdict_without_memory": after.verdict,
            "core_function_broke_safely": after.verdict == "MEMORY_REQUIRED",
            "restored": True,
        }

    def close(self) -> None:
        """Release Sibyl's thread-local SQLite handle."""
        self.memory.storage.close()

    def _policy(self, case_id: str) -> dict[str, Any]:
        return self.memory.get_entity(MEMORY_CATEGORY, case_id)["body"]
