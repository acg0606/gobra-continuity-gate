# Verification — 2026-09-06

Eight tests passed, including an end-to-end test that launches separate Python processes for seed, recall, evidence changes, human/unknown action gates, and deletion. The CLI demo separately passed the same workflow.

The browser demo exercised the real local HTTP server and Sibyl SQLite backend. Observed seed PID 26048 and cold-start recall PID 31384 returned the same stored mission. Later evidence recording changed NEED_EVIDENCE to ALLOW_LOCAL. Submission returned HOLD_HUMAN, an unlisted action returned UNKNOWN_ACTION, and deletion returned MEMORY_REQUIRED with core_function_broke_safely=true. The synthetic fixture was restored after that isolated test.

Recording was captured with the supported CUA tab CDP screencast API, starting 2026-09-06T21:35:47.195Z and ending 2026-09-06T21:38:58.088Z. Every received browser frame was saved with the original screencast timestamp. No scene is replaced or cut. Final encoding metadata and SHA-256 are in video-receipt.json.

The browser displayed genuine app responses, a running UTC clock and actual process IDs. There is no audio track. The demonstration case is synthetic, PMF bonus is 0 and partner multiplier is 1.0. No cloud-Sibyl, LLM, on-chain, adoption, external publication or submission effect is claimed by these tests.
