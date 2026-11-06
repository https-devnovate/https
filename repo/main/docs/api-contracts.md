# api-contracts.md  (v1.0-rc — FREEZE at G1, Fri Nov 6 18:00 IST; afterwards changes only by PR approved by H1)

Base: `/api`, JSON, UTF-8, no auth. Canonical models: `backend/app/contracts.py` (Pydantic v2). This document mirrors them; OpenAPI (`/openapi.json`) is generated; the frontend generates `frontend/src/api/types.ts` with `openapi-typescript`. If this file and `contracts.py` disagree, `contracts.py` wins and this file is fixed in the same PR.

**Hindsight-facing parts (adapter interface, `error_kind`, provenance) are written from documentation and SDK source only (hindsight-integration.md tiers [D]/[S]). They are *contract-frozen* now so other workstreams can build against the fake, and are corrected after the live spike if it shows a difference (that is the only allowed post-freeze change to them, via PR).**

## Enums
`Severity`: SEV1|SEV2|SEV3|SEV4 · `IncidentStatus`: open|resolved · `RootCauseStatus`: confirmed|suspected|ruled_out|superseded (resolve accepts only confirmed|suspected) · `Outcome`: effective|partial|ineffective · `StepOutcome`: tried|effective|partial|ineffective|ruled_out · `Relevance`: strong|partial|weak|unrelated · `Label`: OBSERVED|HISTORICAL|INFERRED|TO_VERIFY · `MemoryStatus`: ok|empty|unavailable|disabled · `RetainStatus` (**derived, API-only, never stored**): pending|synced|failed|not_applicable · `OutboxStatus` (**stored, the only four**): pending|in_progress|succeeded|failed · `OutboxKind`: resolution|correction · `ReflectFreshness`: fresh|stale|none · `Provenance`: document_id|metadata|tag|source_facts|text_regex · `ErrorKind`: timeout|rate_limited|auth|insufficient_credits|server|bad_request|malformed_response|bank_mismatch|unexpected
`Category` (controlled, shared by steps and recommendations — identical to data-model §2): `increase_pool_size, increase_db_capacity, adjust_proxy_pool, restart, check_library_version, upgrade_dependency, check_connection_leak, check_slow_queries, check_db_capacity, check_recent_deploy, check_config, rollback, other`

## Error envelope (all non-2xx)
```json
{"error": {"code": "VALIDATION_ERROR", "message": "Human readable", "details": [{"field": "description", "issue": "min length 10"}]}}
```
Codes: `VALIDATION_ERROR`(422) · `NOT_FOUND`(404) · `CONFLICT`(409) · `LLM_UNAVAILABLE`(503) · `INTERNAL`(500). **Hindsight problems are never errors** on analyze/resolve/reflect (degraded 200 with explicit state, see below); retention problems surface through `retain_status`/`outbox`.

## Endpoints (13)
| # | Method & path | Purpose | Success |
|---|---|---|---|
| 1 | `GET /api/health` | liveness + dependencies | 200 `Health` |
| 2 | `GET /api/services` | dropdown | 200 `{items:[{name, description}]}` |
| 3 | `POST /api/incidents` | create | 201 `Incident` |
| 4 | `GET /api/incidents?status=&service=&limit=50&offset=0` | list, newest first | 200 `{items: Incident[], total}` |
| 5 | `GET /api/incidents/{id}` | detail | 200 `IncidentDetail` |
| 6 | `POST /api/incidents/{id}/analyze` | run agent | 200 `AnalysisReport` |
| 7 | `GET /api/analyses/{analysis_id}` | stored report | 200 `AnalysisReport` |
| 8 | `POST /api/incidents/{id}/resolve` | persist resolution + enqueue retention | 200 `IncidentDetail` |
| 9 | `POST /api/incidents/{id}/retain` | retry a failed retention | 200 `RetainRetryResult` |
| 10 | `POST /api/reflect` | generate a new reflection (manual) | 200 `ReflectResult` |
| 11 | `GET /api/reflection` | last successful reflection + freshness (never calls Hindsight) | 200 `ReflectResult` |
| 12 | `GET /api/memory/events?limit=50&incident_id=` | Memory Trace history (append-only) | 200 `{items: MemoryEvent[]}` |
| 13 | `GET /api/memory/outbox?status=&incident_id=` | Memory Trace current retention state | 200 `{items: OutboxItem[]}` |

**Removed from HTTP (was #12/#13 in v0.1): `POST /api/demo/seed` and `POST /api/demo/reset`.** Seeding and resetting are guarded CLI commands (below); no HTTP endpoint can delete or wipe anything.

### Health (#1)
`{status:"ok|degraded", db:"ok|down", hindsight:"ok|down|unconfigured|bank_mismatch", llm:"ok|down|unconfigured", memory_backend:"fake|hindsight", llm_backend:"fake|groq", bank_id:"srma-demo-…"|null, bank_mode:"demo|dev|eval|null", outbox:{pending:int, in_progress:int, failed:int}, version:"git sha"}`. The health check calls `aget_version()` with a 3 s timeout and is cached 10 s.

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
  "metadata": {"region": "eu-west-1", "release": "1.14.0"},    // optional, <=20 keys, str->str; MAY be incomplete (e.g. no library version)
  "occurred_at": "2026-11-05T14:20:00Z"                        // optional ISO-8601, default now
}
```
### Incident
`{id:"INC-009", title, description, service, severity, status, error_messages[], evidence, metadata{}, occurred_at, created_at, resolved_at|null, revision:int, retain_status}`
### IncidentDetail
`Incident & {investigation_steps:[{seq, action, category, outcome, notes|null}], root_cause:{description, status, cause_key|null, revision}|null, resolution:{actions_taken, outcome, verified}|null, lessons_learned|null, latest_analysis_id|null, outbox: OutboxItem|null}` — `outbox` is the latest row (highest revision, then `created_at`) and is the sole source of `retain_status`.

### Retain status — one definition, one code path
`retain_status` is computed by a single repository function `derive_retain_status(incident_id)` used by **every** serializer, from the latest outbox row: none → `not_applicable` · `pending`/`in_progress` → `pending` · `succeeded` → `synced` · `failed` → `failed`. It is never stored and never set by hand, so API and DB cannot disagree (test: `test_retain_status_matches_outbox`). State transitions and their owners are in data-model §3 and are not repeated here.

### AnalyzeRequest (#6) / AnalysisReport (#6, #7)
Request: `{"use_memory": true}` (default true). `false` ⇒ `memory.status="disabled"`, recall step skipped, **everything else identical** (same prompts, model, temperature).
```json
{
  "analysis_id": "ana_01H...", "incident_id": "INC-009", "mode": "memory_on", "created_at": "...",
  "model": "openai/gpt-oss-120b",
  "memory": {"status": "ok", "reason": null, "queries": ["..."], "hits_count": 12, "candidates_count": 5,
             "unattributed_count": 1, "unknown_refs": [], "invalid_refs": [], "latency_ms": 940},
  "incident_summary": {"services": ["checkout-service"], "symptoms": ["..."], "error_signatures": ["..."], "conditions": ["release 1.14.0"]},
  "missing_information": ["Version of the shared DB client library (svc-commons-db)", "Postgres active connections by application"],
  "related_incidents": [{
    "incident_id": "INC-001", "title": "...", "retrieval_rank": 1, "provenance": "document_id",
    "relevance": "strong", "why_relevant": "...", "matching_features": ["..."], "differences": ["..."],
    "historical_root_cause": {"text": "...", "status": "confirmed", "cause_key": "commons-db-2.3.0-retry-leak", "source": "db"},
    "past_attempts": [{"action": "Increased pool size 10->30", "category": "increase_pool_size", "outcome": "ineffective"}],
    "past_resolution": {"text": "...", "outcome": "effective", "source": "db"},
    "superseded_memory": false,
    "evidence": [{"memory_id": "mem_x|null", "memory_type": "experience|world|observation|null", "snippet": "...", "provenance": "document_id"}]
  }],
  "findings": [{"statement": "...", "label": "OBSERVED", "evidence_refs": ["incident:INC-009"]}],
  "recommended_steps": [{
    "order": 1, "action": "...", "rationale": "...", "category": "check_library_version",
    "label": "TO_VERIFY", "evidence_refs": ["INC-001","INC-002"],
    "previously_failed_refs": [], "risk_note": "read-only check"
  }],
  "validation_actions": [{"rule": "unknown_incident_id_stripped", "detail": "INC-099"}],
  "warnings": ["Historical match is not proof of the same cause."],
  "disclaimer": "Advisory only. Engineer must verify before acting."
}
```
**Fields computed by the application, never trusted from the LLM:** `historical_root_cause.*`, `past_attempts`, `past_resolution`, `title`, `provenance`, `retrieval_rank`, `superseded_memory`, `recommended_steps[].previously_failed_refs` (= IDs of related incidents with relevance ≥ partial that have a step of the same `category` with outcome `ineffective|partial|ruled_out`), and `memory.*`. The LLM supplies only `relevance`, `why_relevant`, `matching_features`, `differences`, findings, steps, `missing_information`.

**Evidence-label rules (enforced by `agent/validators.py`; violations are repaired and listed in `validation_actions`, never silently):**
1. `OBSERVED` — only facts from the *current* incident's own submitted data; `evidence_refs ⊆ ["incident:<current id>"]`.
2. `HISTORICAL` — facts about past incidents; each ref must be a candidate ID that exists in SQLite as `resolved`; **forbidden when `memory.status != ok`**.
3. `INFERRED` — reasoning from observed + historical facts; needs ≥1 ref.
4. `TO_VERIFY` — hypotheses and every action that needs confirmation. A claim about the cause of the *open* incident can never be `OBSERVED` or `HISTORICAL`; it is forced to `INFERRED`/`TO_VERIFY`. Recommended steps are only `INFERRED` or `TO_VERIFY`.
5. Missing/invalid label → downgraded to `TO_VERIFY` (rule `label_defaulted`). Unknown/open/malformed incident ID → removed from refs (rule `unknown_incident_id_stripped`); a finding left with no refs that required one is dropped (rule `unsupported_finding_dropped`).
6. A `historical_root_cause.status` shown to users is the SQLite value; if LLM text calls a suspected cause "confirmed" the sentence is flagged (rule `suspected_rendered_as_confirmed`) and replaced with the DB status.
7. `suspected`/`confirmed` language about a historical cause appears only in `historical_root_cause`; free-text must say "recorded as suspected" for `suspected`.

**Memory states:** `ok` (≥1 attributable candidate) · `empty` (recall succeeded, nothing attributable → `related_incidents=[]`, UI "No relevant historical memory found") · `unavailable` (`reason`: `timeout|rate_limited|auth|insufficient_credits|server|bad_request|malformed_response|bank_mismatch|unexpected`; banner "analysis without historical memory") · `disabled` (use_memory=false). When `memory.status != ok`: `related_incidents` MUST be `[]` and no finding may be `HISTORICAL`.

### ResolveRequest (#8) — 409 if already resolved
```json
{
  "root_cause": {"description": "...", "status": "confirmed", "cause_key": "commons-db-2.3.0-retry-leak"},   // cause_key optional, ^[a-z0-9][a-z0-9.-]{2,80}$; used only to verify cross-incident claims
  "resolution": {"actions_taken": "...", "outcome": "effective", "verified": true},
  "investigation_steps": [{"action": "...", "category": "increase_pool_size", "outcome": "ineffective", "notes": "..."}],
  "lessons_learned": "..."
}
```
Behaviour: one SQLite transaction writes resolution, root cause, steps, sets `status=resolved`, builds the retention narrative, and inserts the outbox row `pending` (data-model §3). The transaction **cannot be rolled back by Hindsight** because Hindsight is not called inside it. After commit the handler calls `outbox.kick()` (non-blocking) and returns. **The response always has `retain_status="pending"`** (never `synced`, never waits for Hindsight); the UI polls `GET /incidents/{id}` every 2 s until `synced` or `failed`. A Hindsight outage therefore never blocks, delays or fails a resolve.

### Retain retry (#9) → `RetainRetryResult`
`{retain_status, outbox: OutboxItem|null, action: "requeued"|"noop_already_synced"}`. Rules (data-model §3): latest row `failed` → same row back to `pending`, `attempts=0` (never a second row; UNIQUE(incident_id, kind, revision)); latest row `succeeded` → 200 `noop_already_synced`; latest `pending|in_progress` → 409 `CONFLICT`; incident not resolved → 409; unknown incident → 404.

### OutboxItem (#13, embedded in IncidentDetail)
`{id, incident_id, kind, revision, status: OutboxStatus, attempts, max_attempts, next_attempt_at|null, last_error_kind: ErrorKind|null, last_error|null, created_at, completed_at|null}`

### Reflect (#10, #11) — see architecture §6 for the validation algorithm
`POST /api/reflect` body `{"question": null}` (null ⇒ fixed default question; custom question allowed but stored). **Manual only** — no automatic refresh after resolve. Single flight: a second call while one is running → 409 `CONFLICT`. If SQLite has 0 resolved incidents the app does **not** call Hindsight and returns `status="empty"`. `GET /api/reflection` returns the stored last success (or `freshness="none"`) without calling Hindsight.
```json
{
  "status": "ok|unavailable|empty",
  "freshness": "fresh|stale|none",
  "stale_reason": "new_incidents_resolved|last_attempt_failed|null",
  "generated_at": "ISO|null", "resolved_count_at_generation": 8, "current_resolved_count": 9,
  "last_attempt": {"at": "ISO", "status": "ok|error", "error_kind": "timeout|null"},
  "question": "...", "latency_ms": 31000,
  "patterns": [{
    "pattern_id": "p1", "title": "Same library defect behind connection exhaustion in 3 services",
    "interpretation": "text written by Hindsight Reflect (generated)", "label": "INFERRED",
    "grounding": "db_verified_shared_cause|db_supported|unsupported",
    "shared_cause_key": "commons-db-2.3.0-retry-leak|null",
    "supporting_incidents": [{"incident_id": "INC-001", "title": "...", "service": "...",
        "root_cause": {"text": "...", "status": "confirmed", "cause_key": "..."}, "outcome": "effective", "source": "db"}],
    "flags": ["INC-008 described as confirmed by Reflect; record says suspected"]
  }],
  "narrative_markdown": "sanitised Hindsight text (untrusted, collapsed by default)",
  "grounding_summary": {"patterns_total": 3, "patterns_shown": 2, "patterns_suppressed": 1, "invalid_refs": ["INC-12"], "unknown_refs": ["INC-099"]},
  "warnings": ["..."]
}
```
`freshness`: `none` = nothing stored; `fresh` = latest stored generation covers all currently resolved incidents *and* the last attempt succeeded; `stale` otherwise (`stale_reason` says why). A stale result is always rendered with its timestamp and a "generated from N of M resolved incidents" notice, never as a new insight. The raw Hindsight response (text, structured output, `based_on`) is stored in `reflections` for traceability and is available only via `GET /api/reflection?include_raw=true` (rendered as escaped plain text in the Memory Trace).

### MemoryEvent (#12)
`{id, ts, op: retain|recall|reflect, status: pending|ok|empty|error, latency_ms|null, incident_id|null, outbox_id|null, attempt|null, error_kind|null, summary, error|null}` — append-only history. **The current state of a retention is `OutboxItem.status` (#13), never inferred from events.** The Memory Trace shows, per retention: the outbox row's current status (pending / in_progress / succeeded / failed + attempts + next attempt time) with its attempt events beneath.

## Validation summary
Trim whitespace; reject control characters; reject empty strings; enforce limits above; `evidence` truncated server-side to 6,000 chars for prompts (full text stored); unknown fields rejected (`extra=forbid`). Reflect/Hindsight text is never interpreted as HTML.

## Python seam interfaces (frozen; Protocols in `contracts.py`/`memory/base.py`)
```python
# ---- memory seam (WS-H implements; WS-B consumes). No SDK types appear here. ----
class AdapterError(BaseModel):  kind: ErrorKind; retryable: bool; message: str  # sanitised, no secrets; http_status: int | None
class RetainRequest(BaseModel): incident_id: str; revision: int; document_id: str; content: str; timestamp: datetime
                                context: str; metadata: dict[str, str]; tags: list[str]
class RetainResult(BaseModel):  status: Literal["ok", "error"]; items_count: int | None; usage_tokens: int | None
                                latency_ms: int; operation_id: str | None; error: AdapterError | None
class MemoryHit(BaseModel):     hit_id: str | None; text: str; memory_type: Literal["world","experience","observation"] | None
                                document_id: str | None; source_incident_ids: list[str]   # [] = unattributed; >1 = cross-incident
                                provenance: Provenance | None; record_revision: int | None; rank: int
                                scores: dict[str, float | None]   # display only: final/reranker/semantic/keyword, query-relative
class Candidate(BaseModel):     incident_id: str; best_rank: int; hit_count: int; snippets: list[MemoryHit]  # <=3, distinct
                                provenance: Provenance; multi: bool
class RecallResult(BaseModel):  status: Literal["ok", "empty", "unavailable"]; queries: list[str]; hits: list[MemoryHit]
                                candidates: list[Candidate]; unattributed_count: int; invalid_refs: list[str]; unknown_refs: list[str]
                                latency_ms: int; error: AdapterError | None   # unknown_refs filled by services/ after the DB check
class ReflectRaw(BaseModel):    status: Literal["ok", "error"]; text: str | None; structured: dict | None; structured_error: str | None
                                based_on: list[dict] | None; usage_tokens: int | None; latency_ms: int; error: AdapterError | None
class HealthResult(BaseModel):  status: Literal["ok", "down", "unconfigured", "bank_mismatch"]; detail: str | None

class MemoryService(Protocol):
    bank_id: str
    async def retain(self, req: RetainRequest) -> RetainResult                                   # never raises
    async def recall_for_incident(self, incident: Incident, extraction: Extraction) -> RecallResult   # never raises; dedup + consolidation inside
    async def reflect(self, question: str) -> ReflectRaw                                         # never raises
    async def health(self) -> HealthResult
    async def ensure_bank(self, retain_mission: str, reflect_mission: str) -> None               # CLI only; create-if-absent, never deletes
# NOTE: there is deliberately no delete/clear/reset method on this Protocol.

# ---- agent seam (WS-I) ----
class AgentService(Protocol):
    async def extract(self, incident: Incident) -> Extraction
    async def analyse(self, incident: Incident, extraction: Extraction, candidates: list[EnrichedCandidate]) -> AnalysisDraft
# EnrichedCandidate {candidate: Candidate, incident: IncidentDetail}   # services/ builds it; only DB-resolved incidents reach the agent
# AnalysisDraft = LLM-owned fields only; services/ merges app-computed fields (see AnalysisReport) and runs validators.
```
`retain_status` vocabulary (`pending|synced|failed|not_applicable`) exists **only** in the API layer; adapter vocabulary is `ok|error`; outbox vocabulary is `pending|in_progress|succeeded|failed`. No component may use another component's words.

## CLI commands (guarded; `python -m srma.cli <cmd>`, wrapped by `make`)
| Command | Does | Never does |
|---|---|---|
| `bank-info` | prints bank id/mode, `app_meta`, health | writes |
| `seed` | loads `data/seed_incidents.json` through the normal resolve path (SQLite + outbox), then `drain-outbox`; idempotent (re-seed = same `document_id` upsert, no duplicates [D; L7]). Refuses if `HINDSIGHT_BANK_ID` ≠ `app_meta.bank_id` or the bank/mode pairing is illegal | deletes anything |
| `drain-outbox [--timeout 300]` | runs the worker until no `pending/in_progress` rows remain | |
| `verify-seed` | for each seeded incident, recall its title and assert ≥1 attributable candidate (acceptance A1) | |
| `demo-new --date YYYYMMDD --nn NN` | **requires `DEMO_MODE=true`**; creates `data/demo/srma-demo-YYYYMMDD-NN.sqlite`, a **new** bank `srma-demo-YYYYMMDD-NN` via `ensure_bank`, writes `app_meta`; refuses if that bank id was used before | delete/clear any SQLite file or bank |
| `dev-new --name <n>` | same for `srma-dev-<n>-NN` with `DEMO_MODE=false` | idem |
| `archive-db` | renames the current SQLite file into `data/archive/<ts>-<name>.sqlite` | deletes |
**Exactly what any "reset" deletes: nothing** — in SQLite (old file archived by rename) and in Hindsight (old bank untouched). A human may delete old banks in the Cloud console. Rule enforced by CI grep for `delete|clear|reset_bank` outside `spike/` (data-model §6).

## Configuration (single source: `backend/app/config.py`; `.env.example` mirrors this table)
| Variable | Default | Notes |
|---|---|---|
| `MEMORY_BACKEND` | `fake` | `fake|hindsight` |
| `LLM_BACKEND` | `fake` | `fake|groq` |
| `MEMORY_FAULT`, `LLM_FAULT` | `none` | fake backends only: `down|slow|malformed|empty|no_provenance|multi_incident` / `invalid_json|timeout|rate_limit` |
| `HINDSIGHT_BASE_URL` | `https://api.hindsight.vectorize.io` | [D] |
| `HINDSIGHT_API_KEY` | — | secret, backend only |
| `HINDSIGHT_BANK_ID` | — | must match `^srma-(demo|dev|eval|spike)-[a-z0-9-]+$` |
| `HINDSIGHT_RETAIN_MODE` | `sync` | `sync|async` (async only if L3 requires) |
| `HINDSIGHT_RECALL_TIMEOUT_S` / `_RETAIN_TIMEOUT_S` / `_REFLECT_TIMEOUT_S` | `8` / `60` / `60` | [A]; tune after L3, L9 |
| `HINDSIGHT_REFLECT_BUDGET` | `mid` | `low|mid|high` [D] |
| `GROQ_API_KEY` | — | secret. **Application LLM only; does not configure Hindsight** |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible |
| `LLM_MODEL` | `openai/gpt-oss-120b` | listed Production on Groq 2026-11-06 [D] |
| `LLM_FALLBACK_MODEL` | *unset until `spike/groq_smoke.py` is run* | organiser guide names `qwen/qwen3-32b`, which is **not on Groq's current models page**; candidate `openai/gpt-oss-20b` (strict JSON-schema listed) |
| `LLM_TEMPERATURE` | `0.2` | fixed for A/B and evals |
| `DEMO_MODE` | `false` | only enables the guarded `demo-new` CLI; nothing destructive exists |
| `SRMA_DB_PATH` | `data/dev/srma-dev.sqlite` | |
| `OUTBOX_TICK_S` / `OUTBOX_LEASE_S` / `OUTBOX_MAX_ATTEMPTS` | `10` / `180` / `5` | match data-model §3 |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS |
