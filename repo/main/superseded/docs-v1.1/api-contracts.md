# api-contracts.md  (v0.1 — FREEZE at end of Hour 2; changes only via PR approved by Integration Lead)

Base: `/api`, JSON, UTF-8, no auth. Canonical models: `backend/app/contracts.py` (Pydantic v2). This doc mirrors them; OpenAPI (`/openapi.json`) is generated; frontend runs `openapi-typescript` to produce `frontend/src/api/types.ts`.

## Enums
`Severity`: SEV1|SEV2|SEV3|SEV4 · `IncidentStatus`: open|resolved · `RootCauseStatus`: confirmed|suspected|ruled_out|superseded · `Outcome`: effective|partial|ineffective · `StepOutcome`: tried|effective|partial|ineffective|ruled_out · `Relevance`: strong|partial|weak|unrelated · `Label`: OBSERVED|HISTORICAL|INFERRED|TO_VERIFY · `MemoryStatus`: ok|empty|unavailable|disabled · `RetainStatus`: pending|synced|failed|not_applicable

## Error envelope (all non-2xx)
```json
{"error": {"code": "VALIDATION_ERROR", "message": "Human readable", "details": [{"field": "description", "issue": "min length 10"}]}}
```
Codes: `VALIDATION_ERROR`(422) · `NOT_FOUND`(404) · `CONFLICT`(409) · `LLM_UNAVAILABLE`(503) · `INTERNAL`(500). Hindsight problems are **not** errors on analyze/reflect (degraded 200, see below); retain problems surface as `retain_status`.

## Endpoints
| # | Method & path | Purpose | Success |
|---|---|---|---|
| 1 | `GET /api/health` | liveness + dependency status | 200 `{status, db, hindsight: ok|down|unconfigured, llm: ok|down|unconfigured, memory_backend: fake|hindsight, version}` |
| 2 | `GET /api/services` | services for dropdown | 200 `{items:[{name, description}]}` |
| 3 | `POST /api/incidents` | create incident | 201 `Incident` |
| 4 | `GET /api/incidents?status=&service=&limit=50&offset=0` | list (newest first) | 200 `{items: Incident[], total}` |
| 5 | `GET /api/incidents/{id}` | detail | 200 `IncidentDetail` |
| 6 | `POST /api/incidents/{id}/analyze` | run agent | 200 `AnalysisReport` |
| 7 | `GET /api/analyses/{analysis_id}` | fetch stored report | 200 `AnalysisReport` |
| 8 | `POST /api/incidents/{id}/resolve` | close + retain | 200 `IncidentDetail` |
| 9 | `POST /api/incidents/{id}/retain` | retry retain | 200 `{retain_status}` |
| 10 | `POST /api/reflect` | pattern synthesis | 200 `ReflectResult` |
| 11 | `GET /api/memory/events?limit=50` | memory trace | 200 `{items: MemoryEvent[]}` |
| 12 | `POST /api/demo/seed` | load synthetic history (idempotent) | 200 `{seeded, retained, failed: string[]}` |
| 13 | `POST /api/demo/reset` | wipe app DB + dev bank (only if `DEMO_MODE=true`) | 200 `{ok:true}` |

## Schemas
### CreateIncidentRequest (#3)
```json
{
  "title": "Checkout 503s in bursts after release",          // 5-200 chars, required
  "description": "Free text ...",                              // 10-5000, required
  "service": "checkout-service",                               // slug ^[a-z0-9-]{2,60}$, auto-creates service
  "severity": "SEV2",                                          // required
  "error_messages": ["java.sql.SQLTransientConnectionException ..."], // optional, <=20 items, each <=1000
  "evidence": "pasted logs / metrics notes",                   // optional, <=20000 chars
  "metadata": {"region": "eu-west-1", "release": "1.14.0"},    // optional, <=20 keys, str->str
  "occurred_at": "2026-11-05T14:20:00Z"                        // optional ISO-8601, default now
}
```
### Incident
`{id:"INC-009", title, description, service, severity, status, error_messages[], evidence, metadata{}, occurred_at, created_at, resolved_at|null, retain_status}`
### IncidentDetail
`Incident & {investigation_steps:[{seq, action, outcome, notes|null}], root_cause:{description,status}|null, resolution:{actions_taken,outcome,verified}|null, lessons_learned|null, latest_analysis_id|null}`
### AnalyzeRequest (#6)
`{"use_memory": true}` (default true). `use_memory=false` ⇒ `memory.status="disabled"`, same pipeline otherwise.
### AnalysisReport (#6/#7)
```json
{
  "analysis_id": "ana_01H...", "incident_id": "INC-009", "mode": "memory_on", "created_at": "...",
  "model": "openai/gpt-oss-120b",
  "memory": {"status": "ok", "queries": ["..."], "hits_count": 12, "latency_ms": 940},
  "incident_summary": {"services": ["checkout-service"], "symptoms": ["..."], "error_signatures": ["..."], "conditions": ["release 1.14.0"]},
  "missing_information": ["Version of shared DB client library", "Postgres active connections by application"],
  "related_incidents": [{
    "incident_id": "INC-001", "title": "...", "relevance": "strong",
    "why_relevant": "...", "matching_features": ["..."], "differences": ["..."],
    "historical_root_cause": {"text": "...", "status": "confirmed"},
    "past_attempts": [{"action": "Increased pool size 10->30", "outcome": "ineffective"}],
    "past_resolution": {"text": "...", "outcome": "effective"},
    "evidence": [{"memory_id": "mem_x|null", "snippet": "..."}]
  }],
  "findings": [{"statement": "...", "label": "OBSERVED", "evidence_refs": ["incident:INC-009"]}],
  "recommended_steps": [{
    "order": 1, "action": "...", "rationale": "...", "category": "check_library_version",
    "label": "TO_VERIFY", "evidence_refs": ["INC-001","INC-002"],
    "avoids_previously_failed": true, "risk_note": "read-only check"
  }],
  "warnings": ["Historical match is not proof of the same cause."],
  "disclaimer": "Advisory only. Engineer must verify before acting."
}
```
`category` is a controlled string (enables deterministic eval): `increase_pool_size|restart|check_library_version|check_connection_leak|check_slow_queries|check_db_capacity|check_recent_deploy|check_config|rollback|other`.
When `memory.status != "ok"`, `related_incidents` MUST be `[]` and no finding may carry label HISTORICAL.
### ResolveRequest (#8) — 409 if already resolved
```json
{
  "root_cause": {"description": "...", "status": "confirmed"},
  "resolution": {"actions_taken": "...", "outcome": "effective", "verified": true},
  "investigation_steps": [{"action": "...", "outcome": "ineffective", "notes": "..."}],
  "lessons_learned": "..."
}
```
Response: `IncidentDetail` with `retain_status` `synced` or `pending` (never fails because Hindsight failed).
### ReflectRequest / ReflectResult (#10)
Request: `{"question": null, "focus_service": null}` (null ⇒ default pattern question).
```json
{"status": "ok|unavailable|empty", "question": "...", "text": "markdown synthesis from Hindsight reflect",
 "incident_ids": ["INC-001","INC-002","INC-007"], "generated_at": "...", "latency_ms": 3100, "cached": false}
```
`incident_ids` = distinct `INC-\d+` tokens found in `text` that exist in DB (others stripped).
### MemoryEvent
`{id, ts, op: retain|recall|reflect, status: ok|empty|error, latency_ms, incident_id|null, summary, error|null}`

## Validation summary
Trim whitespace; reject control characters; reject empty strings; enforce limits above; `evidence` truncated server-side to 6,000 chars for prompts (full text stored); unknown fields rejected (`extra=forbid`).

## Python seam interfaces (also frozen)
```python
class MemoryService(Protocol):
    async def retain_incident(self, incident: IncidentDetail) -> RetainResult   # {status: synced|failed, ref|None, error|None}
    async def recall_for_incident(self, incident: Incident, extraction: Extraction) -> RecallResult
    async def reflect(self, question: str | None, focus_service: str | None) -> ReflectRaw  # {text, ok, error}
    async def health(self) -> Literal["ok","down","unconfigured"]
# RecallResult {status: ok|empty|unavailable, queries: list[str], hits: list[MemoryHit], latency_ms}
# MemoryHit {memory_id|None, text, memory_type|None, source_incident_id|None, score|None}
class AgentService(Protocol):
    async def extract(self, incident: Incident) -> Extraction
    async def analyse(self, incident: Incident, extraction: Extraction, hits: list[EnrichedHit]) -> AnalysisReport
# EnrichedHit {hit: MemoryHit, incident: IncidentDetail | None}
```
Env flags: `MEMORY_BACKEND=fake|hindsight`, `LLM_BACKEND=fake|groq`.
