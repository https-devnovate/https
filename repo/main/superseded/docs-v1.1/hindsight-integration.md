# hindsight-integration.md

> ## ⚠️ VERIFICATION STATUS: NOT YET VERIFIED
> This was drafted **without live access to the Hindsight docs/repo**. Everything below about Hindsight's API is from the architect's recollection of the project and **must be confirmed by the Day-0 spike (§1) before any code depends on it.** Items marked 🔶 are assumptions. Do not copy method names/params from this file into code until the spike sheet at the bottom is filled in with checked results. All Hindsight calls live behind `app/memory/` so surprises cost hours, not days.

## 1. Day-0 spike (Hindsight WS owner, target ≤ 2 h, blocks contract freeze for `memory/` only)
Read: https://hindsight.vectorize.io/ (quickstart, retain, recall, reflect, banks), https://github.com/vectorize-io/hindsight (README, python client examples, `/examples`), Cloud dashboard https://ui.hindsight.vectorize.io. Then run a 30-line script and fill in:

| # | Question to answer from docs + real calls | Result (fill in) |
|---|---|---|
| S1 | Cloud base URL, auth scheme, SDK package + version (`pip show`) | |
| S2 | How to create a bank; is there a mission/background/disposition setting; set it for incident-memory | |
| S3 | Exact `retain` signature: content, context, timestamp, document_id, metadata, tags; sync vs async; time until recallable | |
| S4 | Does re-retaining the same `document_id` replace or duplicate? | |
| S5 | Exact `recall` signature & result shape: fields per hit (text, type, id, document/source id, score, dates?), budget/max_tokens params, filter by type/tags | |
| S6 | Exact `reflect` signature & result shape; does it cite supporting memories; latency; determinism | |
| S7 | How to delete/reset a bank (for `demo/reset`) | |
| S8 | Rate limits / credit cost per retain (LLM extraction) and reflect; promo `MEMHACK99` applied after signup in Billing | |
| S9 | Which LLM Hindsight uses for extraction/reflect on Cloud vs local (`HINDSIGHT_API_LLM_*` env on self-host 🔶) | |
| S10 | Local fallback: Docker image/command, ports, required env, embedded DB needs | |

Deliverable: `docs/hindsight-spike-results.md` (verified snippets) → then this file is updated and the 🔶 marks removed.

## 2. Selected deployment [DECISION, pending S1/S8]
**Hindsight Cloud** as primary (one shared bank for six people + CI, no Docker/DB ops, promo credits). **Local Docker as fallback** if Cloud is flaky or credits fail. Bank IDs: `srma-demo` (seeded, used for judging), `srma-dev` (shared scratch), per-developer `srma-dev-<name>`. Bank id comes from env `HINDSIGHT_BANK_ID`.

Env vars (backend only): `HINDSIGHT_BASE_URL`, `HINDSIGHT_API_KEY`, `HINDSIGHT_BANK_ID`, `GROQ_API_KEY`, `LLM_MODEL=openai/gpt-oss-120b`, `LLM_FALLBACK_MODEL=qwen/qwen3-32b`, `MEMORY_BACKEND`, `LLM_BACKEND`, `DEMO_MODE`.

## 3. Adapter (the only code that imports the SDK)
`backend/app/memory/hindsight_adapter.py` implements `MemoryService` (see api-contracts). Responsibilities: build memory text (§4), call SDK with timeout (8 s recall, 30 s retain, 45 s reflect 🔶), retry 2× with backoff on 5xx/timeouts, normalise hits to `MemoryHit`, extract `INC-\d+` from hit text when no source id is returned (regex fallback — the reason every narrative begins with the ID), log every call to `memory_events`.

## 4. Retain workflow
Trigger: `POST /incidents/{id}/resolve` only. Content = one plain-text narrative per incident (LLM-extractor friendly, human-readable; *not* JSON):
```
INCIDENT INC-001 — Intermittent DB connection timeouts in payment-service
Date: 2026-08-12 | Service: payment-service | Severity: SEV2 | Status: resolved
Symptoms: ...
Error messages: HikariPool-1 - Connection is not available, request timed out after 30000ms
Conditions: began ~2h after release 3.8.0 which bumped svc-commons-db 2.2.4 -> 2.3.0
Investigation steps: (1) checked DB CPU/slow queries: ruled out. (2) increased pool 10->30: INEFFECTIVE, recurred in 6h and approached Postgres max_connections. (3) restarted pods: temporary relief only.
Root cause (CONFIRMED): ...
Resolution (EFFECTIVE, verified): ...
Lessons learned: ...
```
Call (🔶 verify): `retain(bank_id, content=<narrative>, context="resolved production incident postmortem", timestamp=<resolved_at>, document_id="INC-001")`. Rules: raw logs truncated to key lines; only engineer-confirmed content; suspected causes are written as "Root cause (SUSPECTED, unverified)"; never retain agent output.

## 5. Recall workflow
Three queries per analysis, merged and de-duplicated by memory id/text (all 🔶 on params):
1. **Narrative**: extracted symptoms + service + conditions, in natural language ("services failing to obtain DB connections intermittently after a release; connection count not returning to baseline").
2. **Error signature**: normalised error strings (strip numbers/ids).
3. **Experience/failure**: "what fixes were tried and failed for <symptom class>".
Use semantic recall (not exact match); cap results ~15; ask for a medium budget. Time context: the narrative carries dates; the analysis prompt receives `occurred_at` and hit dates so "recent deploys" reasoning is possible. Hits → enrich with DB incident record by source id (§3) → agent.

## 6. Reflect workflow
Called via `POST /api/reflect` and auto-refreshed after each successful resolve. Default question (fixed so demo is repeatable):
> "Across all resolved incidents: what failure patterns recur across different services? For each pattern list the incident IDs, which fixes were repeatedly ineffective, which were effective, and what should engineers check first on a new incident of this kind. Distinguish confirmed root causes from suspected ones."
Output is rendered as markdown; `INC-###` tokens linkified; IDs not in DB stripped. Cache last good result (for fallback and for demo determinism). Bank mission/disposition set per spike S2 (e.g. skeptical, literal — prefer evidence over speculation) 🔶.
**Why Reflect ≠ summarisation:** it reasons over the bank's accumulated memories (including cross-incident observations) rather than one document; see demo-plan §4 for the concrete insight no single recall gives.

## 7. Memory structure
One bank; no per-service banks (cross-service patterns are the point). Metadata/tags 🔶: `service`, `severity`, `incident_id`, `root_cause_status` if S3/S5 confirm support; otherwise all structure lives in the narrative text.

## 8. Error handling
See architecture §7. Adapter returns typed results (`status`) instead of raising; services decide degradation. Unit-test with a stub that raises timeouts, 401, 429, malformed payloads.

## 9. Verified example requests/responses
*Intentionally empty until the spike is complete — to be pasted from real calls into `hindsight-spike-results.md`.*
