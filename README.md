# GoBRA Continuity Gate

An action gate for long-running AI work. A fresh agent session recalls the mission, evidence, human approvals, and forbidden actions from **Sibyl Memory** before deciding what it may do next.

[Watch the continuous 3-minute demonstration](https://acg0606.github.io/gobra-continuity-gate/demo.html). The recording shows real local SDK execution across separate Python processes with a synthetic case. [Capture provenance](docs/video-receipt.json) records timestamps, the file hash and the observed outcomes.

## Why memory is load-bearing

The product's core function is safe continuity across sessions. The policy is not bundled into the evaluator and there is no permissive fallback:

1. `seed_case` writes the operating policy and evidence to the Sibyl WARM tier.
2. A new Python process creates `ContinuityEngine` and recalls that policy before every decision. The response includes the real process ID and UTC timestamp.
3. Recalled evidence can materially change `NEED_EVIDENCE` into `ALLOW_LOCAL`.
4. If the memory entity is deleted, the same action becomes `MEMORY_REQUIRED` and execution stops.

The write/read calls are in `continuity/engine.py`. `deletion_test` demonstrates that removing Sibyl Memory breaks the decision function safely.

## Local verified run

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py demo
python app.py serve --host 127.0.0.1 --port 4346
```

For the private visual demo:

```powershell
.\start-preview.ps1
# open http://127.0.0.1:4346
```

The demo writes a case in one process, exits it, and starts separate Python processes for recall and evaluation. The new process recalls the mission, blocks a human-only submission, detects missing evidence, then changes its decision after another process writes that evidence. It also blocks unlisted actions and executes the deletion test. Every HTTP operation uses the same process-isolated path.

The case is synthetic. An `ALLOW_LOCAL` verdict is a policy decision, not proof that an external action occurred. This prototype executes no trades, account changes, posts or submissions. There is no LLM or claim of model intelligence: the useful function is persistent, inspectable authorization continuity for an agent workflow.

## Evidence labels

- `LOCAL_VERIFIED`: real local Sibyl SDK calls and SQLite persistence were exercised.
- `DEMO`: the included case is synthetic and does not represent an external submission.
- `HOLD_HUMAN`: the recalled demonstration policy requires a person for the action.
- `UNKNOWN_ACTION`: the policy does not explicitly allow the requested action.

No external action, public post, account change, wallet action, or submission is performed by this package.

## Architecture

```text
new session -> recall continuity_case from Sibyl Memory
                         |
                         +-> missing memory -> MEMORY_REQUIRED (fail closed)
                         +-> human gate     -> HOLD_HUMAN
                         +-> missing proof  -> NEED_EVIDENCE
                         +-> safe + proven  -> ALLOW_LOCAL
```

## Prior Work

The HACKOPS operating model and its FACT/INFERENCE/UNKNOWN and human-gate conventions existed before the September 1, 2026 build window. This project is a new competition-window implementation that turns that prior operational insight into a standalone Sibyl-backed decision product. No pre-existing competitive code is claimed as new.

## Submission gates

The source is MIT licensed. Public submission status and final video/post links are recorded in the submission package only after publication receipts exist.

## Find the critical path in under two minutes

- **Write:** `continuity/engine.py`, `seed_case` → `MemoryClient.set_entity`, `set_state`, `write_event`.
- **Read:** `_policy` → `MemoryClient.get_entity`; `evaluate` cannot authorize an action without it.
- **Evidence update:** `remember_evidence` reads the current entity, writes the new evidence, then journals the change.
- **Cold start:** `app.py`, `run_fresh_command` starts `sys.executable app.py` per operation. `continuity/server.py` uses it for each browser request.
- **Deletion:** `deletion_test` removes the entity, verifies `MEMORY_REQUIRED`, then restores the synthetic fixture. `tests/test_process.py` independently verifies persistence across real process boundaries.

## How memory made this possible

The evaluator receives only a case ID and an action. It has no embedded fallback policy. The mission, allowed actions, human boundaries, required evidence and supplied evidence are recalled from Sibyl. Evidence written in one process changes a later process's decision; deleting that entity prevents the evaluator from acting.

## Partner stacks and product evidence

No Base or Virtuals integration is claimed. Partner multiplier: **1.0**. PMF bonus: **0**; no users, pilots, revenue, waitlist or design partners are claimed. The target audience is people coordinating long-running agent work, and the included workflow is a synthetic illustration of that problem.

## Deployment boundary

Run this as a loopback development demo. The HTTP server is not an authenticated multi-user service and should not be exposed publicly. Judges can reproduce it locally from this repository. SQLite storage is local; no Sibyl cloud session, API key, external account or on-chain action is claimed.
