# hindsight-integration.md  (v2.0 — documentation- and SDK-checked; live verification NOT RUN)

> ## STATUS: Task 2 is **NOT complete**
> Everything below is tagged with its evidence tier. **No live Hindsight Cloud call has been executed by the architect** (no key or network in the authoring environment). The live smoke test (`spike/hindsight_smoke.py`) has **not been run**; §10 and §11 are intentionally empty until the Hindsight owner (H2) pastes real output. Nothing in this file may be marked "verified" before that.
>
> | Tier | Tag | Meaning | Status |
> |---|---|---|---|
> | Documented | **[D]** | Stated on the official docs, read 2026-11-06 (links in §12) | filled in below |
> | SDK-inspected | **[S]** | Read in `hindsight-client` source at GitHub tag `v1.2.0` (via page fetch; the file was too long to read completely). **Not yet confirmed against the installed package** — run `python spike/inspect_sdk.py` first | filled in below |
> | Live-verified | **[L]** | Observed by running the smoke script against Cloud | **NONE — NOT RUN** |
> | Assumption | **[A]** | Our design decision or guess; must be confirmed by [D]/[S]/[L] or an organiser | listed in §10/§13 |
>
> Rule for all code and docs: only the tag [L] may be described as "verified". [D] and [S] are "documented" / "per SDK source".

## 1. Selected SDK and deployment
| Item | Value | Tier |
|---|---|---|
| Package / import | `pip install hindsight-client` → `from hindsight_client import Hindsight` | [D] |
| **Selected version** | **`hindsight-client==1.2.0`** (latest on PyPI, released 2026-11-03; `requires-python >=3.10`; deps include `pydantic>=2`, `aiohttp>=3.8.4`, `urllib3<3`) | [D] PyPI + [S] `pyproject.toml` at tag v1.2.0. **Installed version to be recorded from `pip show` by H2; freeze it in the lockfile and do not upgrade after the smoke test passes.** The release is 3 days old; the docs we read are for the `main`/latest site and may describe newer behaviour — hence `inspect_sdk.py`. |
| Cloud base URL | `https://api.hindsight.vectorize.io` | [D] |
| Auth | `Authorization: Bearer <api key>`; SDK `Hindsight(base_url=..., api_key=...)` | [D] |
| Constructor | `Hindsight(base_url, api_key=None, timeout=300.0, user_agent=None, max_attempts=3)`; `max_attempts` applies **only to idempotent calls (recall, reflect)**; retries only on HTTP 429/503 with `Retry-After`/jittered backoff; **retain is never retried by the SDK** | [S] |
| Python | 3.11 (satisfies `>=3.10`) | [A] choice, constraint [D] |
| Cloud vs local | Cloud primary; local Docker (`hindsight-all`/server image) fallback — local requires its own LLM key (§3) | [D] |
| Billing | prepaid credits, 1 credit = $1; retain $10/M input tokens, recall $0.75/M output tokens, reflect $0.05/call (rates effective 2026-07-06); HTTP **402** when balance is exhausted. The promo `MEMHACK99` ($50, from the organiser PDF) is **not mentioned in the billing docs** — H2 confirms in the dashboard | [D]; promo = organiser info, unconfirmed |

## 2. Which model does Hindsight use? (correction of the earlier diagram)
- **Hindsight Cloud: the LLM, embedding and reranking models are "included"/managed by the service. The docs we read do not describe any way to choose the Cloud model or to bring our own LLM key.** [D]
- **Self-hosted Hindsight** is configured by server env vars `HINDSIGHT_API_LLM_PROVIDER` (default `openai`; `groq` is a supported value), `HINDSIGHT_API_LLM_MODEL` (default `gpt-5-mini`), `HINDSIGHT_API_LLM_API_KEY`, `HINDSIGHT_API_LLM_BASE_URL`. [D] These do not apply to Cloud.
- **Therefore: our application's Groq key (`GROQ_API_KEY`) configures only the application's own analysis LLM. It does not configure, and is never used by, Hindsight's extraction/consolidation/reflect model.** The architecture diagram no longer draws a Hindsight→Groq edge.
- Consequence we accept: Hindsight's extraction quality and Reflect style are outside our control on Cloud. Mitigation: `retain_mission` / `reflect_mission` + disposition (§5, §7), L14 extraction-fidelity check, and deterministic app-side validation of Reflect output (architecture §6).
- Open item [A→docs]: ask Vectorize (or read the Cloud docs) whether a Cloud model can be configured. Not blocking.

## 3. API surface we use [S] (parameters exactly as in the v1.2.0 source; all async-first)
All FastAPI code paths use the **`a*` coroutine methods only**. The sync wrappers run an internal event loop and are documented to fail inside a running loop [S] — **never call sync methods from a request handler**. One `Hindsight` instance per process, created in the app lifespan and closed with `await client.aclose()`.

| Purpose | Async method | Parameters we pass (others left default) | Returns |
|---|---|---|---|
| Version/health | `aget_version()` | — | `VersionResponse` (`api_version`, `features`) [D] |
| Create bank | `acreate_bank(bank_id, name=None, mission=None, retain_mission=None, reflect_mission=None, disposition_*=None, …)` | `bank_id`, `retain_mission`, `reflect_mission`, `disposition_skepticism` | `BankProfileResponse`. **Implemented with raw aiohttp: on HTTP error it raises `aiohttp.ClientResponseError`, not `ApiException`** [S] |
| Retain | `aretain(bank_id, content, timestamp=None, context=None, document_id=None, metadata=None, entities=None, resolve_entities=None, tags=None, update_mode=None, retain_async=False, operation_id=None, observation_scopes=…, strategy=…)` | `bank_id, content, timestamp(datetime), context, document_id, metadata, tags, update_mode="replace"` | `RetainResponse` (`success`, `bank_id`, `items_count`, `async`/`var_async`; `usage` for sync) [S]/[D] |
| Recall | `arecall(bank_id, query, types=None, max_tokens=4096, budget="mid", trace=False, query_timestamp=None, include_entities=False, include_chunks=False, include_source_facts=False, max_source_facts_tokens=4096, tags=None, tags_match="any", prefer_observations=False, min_scores=None, temporal_window=None, …)` | `bank_id, query, budget, max_tokens, include_source_facts=True` (to attribute observations — see §6) | `RecallResponse` |
| Reflect | `areflect(bank_id, query, budget="low", context=None, max_tokens=None, response_schema=None, tags=None, tags_match="any", include_facts=False, include_tool_calls=False, …)` | `bank_id, query, budget, response_schema, include_facts=True` | `ReflectResponse` |
| List memories (spike/verify only) | `alist_memories(bank_id, type=None, search_query=None, …, limit=100, offset=0, document_id=…, consolidation_state=…)` | for spike/`verify-seed` | `ListMemoryUnitsResponse` (`total`, …) |
| Close | `aclose()` | — | — |
| Op status (only if async retain is adopted) | `client.operations.get_operation_status(bank_id, operation_id)`; statuses `pending, processing, completed, failed, cancelled` | | [D] |

**Not used by app code (enforced by CI grep, data-model §6):** any `*delete*`, `*clear*`, `reset_*` method. `adelete_bank`/`delete_bank` exist in the SDK [S]; whether **Cloud** permits bank deletion is **not stated in the docs we read** [D: silent]. App never calls them; the answer does not affect the design.

**Parameter semantics [D]:**
- `retain.content` is the only required field; Hindsight **stores extracted facts, not the original text**.
- `retain.timestamp`: ISO-8601 string (REST), omitted = now, `"unset"` = none. The Python annotation is `datetime`; whether a `str` is accepted by the SDK is **unclear [S] → L3b**. We pass a `datetime`.
- `retain.metadata`: string→string; values returned with recalled memories; `null` values dropped. `tags` are *visibility* tags: a memory is returned in a tag-filtered recall only if its tags intersect the filter. `context` is injected into the extraction prompt.
- `retain.document_id` makes retain idempotent: **reusing it upserts — the old document and all its memories are deleted, then the new content is processed** (`update_mode="replace"`, the default). `"append"` concatenates onto the existing document and reprocesses it. Items without `document_id` are never folded into another document. Deleting a document also deletes the observations built from its facts [D]. *Live behaviour = L7.*
- `retain_async=True` returns immediately with an `operation_id`; same `operation_id` again creates no new work; reusing it for a different operation → HTTP 409; no `usage` is returned for async [D].
- `recall`: `types` ⊆ {`world`,`experience`,`observation`}; `budget` low/mid/high; `max_tokens` caps fact text only; queries **> 500 tokens are rejected** (keep our queries short); `query_timestamp` anchors relative dates; a query that matched something is never returned empty by the token cap [D].
- **Recall result fields [D]:** `id`, `text`, `type`, `context`, `metadata`, `tags`, `entities`, `occurred_start/end`, `mentioned_at`, **`document_id`**, `chunk_id`, **`source_fact_ids`** (observations only), **`scores{final, reranker, semantic, keyword}`**. Response-level: `results`, `source_facts` (dict keyed by fact id, when requested), `chunks`, `entities`, `trace`.
- **Score semantics [D]:** `final` is the ranking score (results sorted by it, descending); `reranker`/`semantic` are 0–1 or `null`; `keyword` is BM25 or `null`; **"scores are relative to a single query and are not comparable across queries"**. ⇒ The app uses **rank order only** — no absolute thresholds, no cross-query comparison (§6).
- **Reflect [D]:** `query` (situational context belongs inside the query text); `budget` low (default)/mid/high; `response_schema` adds `structured_output` next to `text` (`text` is always returned; `structured_output_error` appears if schema extraction failed but the call still returns 200); `include.facts` → `based_on{memories, mental_models, directives}` = sources actually retrieved in the loop ("citations are validated to prevent hallucinated references"); `usage`; optional `trace`. The SDK spells the flag `include_facts=True` [S].
- **Errors [D]:** 400, 401 (invalid/expired key), 402 (insufficient credits), 403, 404, 500. Error-body structure is not documented → L11. **SDK exceptions [S]:** `hindsight_client_api.exceptions.ApiException` (has `.status`, `.body`) for API calls; `aiohttp.ClientResponseError` from `acreate_bank`; `TimeoutError`/`RuntimeError` in export helpers; `ValueError` for bad `min_scores` keys; `warnings.warn` if `operation_id` is passed without `retain_async`. The adapter therefore catches `Exception` and classifies (§4).
- Banks: the docs state a bank is **auto-created with default settings on first use** [D]; mission/disposition are set by `create_bank`/`update_bank_config`. `reflect_mission` and disposition **affect only reflect** [D]. Whether `acreate_bank` on an existing id is idempotent, and whether `arecall` on a never-created bank errors or auto-creates → **L2/L2b/L2c**.
- Default SDK timeout is **300 s** [S]; we always wrap calls in `asyncio.wait_for` with our own limits (§4).

## 4. Adapter module — the only code that imports `hindsight_client`
`backend/app/memory/` (WS-H). Nothing else imports `hindsight_client`, `hindsight_client_api` or `aiohttp` for Hindsight (CI grep). Interfaces are in api-contracts.md "Python seam interfaces"; this section is the behavioural contract.

| Rule | Detail |
|---|---|
| Never raises | Every public method returns a typed result (`ok`/`error` + `AdapterError`). `asyncio.CancelledError` is re-raised; all other exceptions are caught and classified. |
| Normalisation | SDK models → our Pydantic models immediately; no SDK type, attribute name or field crosses the module boundary. Missing/`None` fields tolerated; unknown fields ignored; wrong types → `malformed_response`. |
| Timeouts | recall 8 s (all queries run concurrently with `asyncio.gather`; one query failing does not discard the others), retain 60 s [A, tune by L3], reflect 60 s [A, tune by L9]; SDK `timeout=` set to the same upper bound and `max_attempts=2`. |
| Retries | **No retries inside the adapter for retain** (the outbox owns retry; SDK doesn't retry writes). Recall/reflect: SDK handles 429/503 only; adapter adds none. |
| Fake | `FakeMemoryService` (keyword-overlap over `data/fixtures/*.json`) implements the identical Protocol with fault injection `MEMORY_FAULT=none|down|slow|malformed|empty|no_provenance|multi_incident`. `main` must always boot and pass tests with `MEMORY_BACKEND=fake`. |
| Bank guard | adapter is constructed with one `bank_id`; refuses to operate (`bank_mismatch`) when it differs from `app_meta.bank_id`. Bank id must match `^srma-(demo|dev|eval|spike)-[a-z0-9-]+$`. |
| Logging | each call → `memory_events` row (op, status, latency, error_kind). API keys and full content are never logged (content hash + length only). |

**Error classification (adapter → `error_kind`, `retryable`):**
| Condition | `error_kind` | outbox class |
|---|---|---|
| `asyncio.TimeoutError`, connection reset/DNS | `timeout` | transient |
| HTTP 429 | `rate_limited` | transient |
| HTTP 5xx | `server` | transient |
| HTTP 401/403 | `auth` | permanent |
| HTTP 402 | `insufficient_credits` | permanent (engineer retries after top-up) |
| HTTP 400/404/409/422 | `bad_request` | permanent |
| result fields missing / wrong type / not parseable | `malformed_response` | permanent |
| bank id ≠ `app_meta.bank_id` | `bank_mismatch` | permanent (worker does not claim rows) |
| anything else | `unexpected` | unexpected → `failed` |

## 5. Memory content (what is retained, and its formats)
Trigger: only an engineer-confirmed resolve (outbox row `kind=resolution`) or a correction (`kind=correction`). Never open incidents, never agent output, never analysis text.

**Narrative** (one plain-text document per incident revision; content is frozen into the outbox row at enqueue):
```
INCIDENT INC-001 - Intermittent DB connection timeouts in payment-service
Date: 2026-08-12 | Service: payment-service | Severity: SEV2 | Status: resolved
Symptoms: ...
Error messages: HikariPool-1 - Connection is not available, request timed out after 30000ms
Conditions: began ~2h after release 3.8.0 which bumped svc-commons-db 2.2.4 -> 2.3.0
Investigation steps: (1) DB CPU/slow queries: ruled out. (2) pool 10->30: INEFFECTIVE, recurred in 6h. (3) restart: temporary relief only.
Root cause (CONFIRMED, cause_key=commons-db-2.3.0-retry-leak): ...
Resolution (EFFECTIVE, verified): ...
Lessons learned: ...
Record revision: 1
```
Rules: first line starts with the incident ID so every extracted fact can carry it; suspected causes are written `Root cause (SUSPECTED, unverified)`; raw logs truncated to key lines; ≤ ~4,000 chars.

**Call:** `aretain(bank_id=BANK, content=<narrative>, context="resolved production incident record", timestamp=<resolved_at as datetime>, document_id="INC-001", metadata={"incident_id":"INC-001","service":"payment-service","root_cause_status":"confirmed","revision":"1"}, tags=["incident:INC-001","service:payment-service"], update_mode="replace")` — synchronous retain (response carries `usage`/`items_count`; "ok" means processed). `HINDSIGHT_RETAIN_MODE=sync` default. **Only if L3 shows sync latency too high** switch to `async` (`retain_async=True, operation_id=<outbox.id>`; adapter polls `operations.get_operation_status`); the outbox state machine is unchanged. Metadata values are strings only.

**Bank configuration (set once by CLI `demo-new`/`dev-new` via `ensure_bank`, [A] wording, tune after L14):**
- `retain_mission`: "Extract incident facts: service, symptoms, error messages, failed fixes, root cause (note confirmed vs suspected), resolution and outcome. Always keep the incident ID (INC-###) in every fact."
- `reflect_mission`: "You analyse resolved production incidents. Prefer evidence over speculation; distinguish confirmed from suspected causes; cite incident IDs; never state a cause as confirmed unless the incident record says CONFIRMED."
- Disposition: `skepticism=4, literalism=4, empathy=2` [A; D says it only affects reflect].
One bank per environment; no per-service banks (cross-service patterns are the point).

## 6. Recall workflow, provenance, consolidation
Three concurrent queries per analysis (each < 500 tokens): (1) **narrative** (symptoms + service + conditions in natural language), (2) **error signature** (normalised error strings, digits stripped), (3) **failed-fix** ("fixes tried and ineffective for <symptom class>"). `types=None` (all), `budget="mid"`, `max_tokens=4096`, `include_source_facts=True`.

**Provenance resolution per hit (adapter; in this order; first match wins):**
1. `hit.document_id` matching `^INC-\d{3}$` → `provenance="document_id"` [D: field exists; **L4: is it populated?**]
2. `hit.metadata["incident_id"]` matching the pattern → `"metadata"`
3. a tag `incident:INC-###` → `"tag"`
4. observation hits (no single document): look up `source_fact_ids` in `response.source_facts` and resolve each fact's `document_id` → `"source_facts"` [shape of `source_facts` items unverified → **L6**]
5. regex `\bINC-\d{3}\b` over `text`: exactly one distinct ID → `"text_regex"`; **two or more distinct IDs → `cross_incident`** (snippet attached to the *set* of IDs, flagged `multi`); none → unattributed.

**Rules for what the application does with hits:**
- **Not one-to-one.** One retained document yields many extracted facts [D: `memory_unit_count`], so several hits can belong to one incident, and one observation can mention several incidents.
- **Dedup:** drop repeats across the three queries by `hit.id`; then by normalised text.
- **Consolidate to candidates:** group by incident ID; per incident keep `best_rank` (lowest rank position in the query where it ranked best), up to 3 distinct snippets, `hit_count`, `memory_types`, `provenance` (weakest used). **`related_incidents` are built from candidates, never from hits.**
- **Malformed ID** (e.g. `INC-12`, `INC-1234`, `inc 001`): counted in `RecallResult.invalid_refs`, never auto-corrected, never a candidate.
- **Well-formed but not in SQLite, or in SQLite but `status=open`** (open incidents are never retained, so this signals corruption/bank mix-up): dropped; counted in `RecallResult.unknown_refs`; shown in Memory Trace as "memory references unknown incident INC-099 (ignored)".
- **Unattributed hits:** kept in the trace only; **never passed to the analysis LLM as incident evidence**.
- **Scores:** per-hit `rank` (1-based) is the only value used for logic; raw `scores.*` are displayed in the Memory Trace labelled "relative to this query" [D]. `RecallResult.status="empty"` when zero attributable candidates remain *and* zero hits (hits exist but none attributable → `ok` with a warning, `candidates=[]`).
- **Enrichment** (services/): candidate → SQLite incident record (status, root cause + status, steps, outcome). Root cause shown as "confirmed" only from SQLite (architecture §6).
- **Staleness:** narratives carry `Record revision: N`; adapter parses it when present; if DB revision > memory revision, the candidate is flagged `superseded_memory=true` (data-model §4).

## 7. Reflect workflow
Manual, on demand (`POST /api/reflect`); **no auto-refresh after resolve** (reasons in architecture §5: unknown latency, non-blocking resolve, avoids presenting stale text as new). The last successful result is stored with its timestamp (`reflections`).

Fixed default question (repeatable demo): "Across all resolved incidents: what failure patterns recur across different services? For each pattern give the supporting incident IDs, which fixes were repeatedly ineffective, which were effective, and what engineers should check first on a new incident of this kind. Say explicitly which root causes are confirmed and which are only suspected."

Call: `areflect(bank_id, query, budget="mid", include_facts=True, response_schema=PATTERN_SCHEMA)` with `PATTERN_SCHEMA = {patterns:[{title, statement, supporting_incident_ids:[str], confidence: low|medium|high}]}`. `budget`/timeout pending L9. Adapter returns `ReflectRaw{text, structured, structured_error, based_on, usage, latency_ms}`. Validation, grounding rules and the UI contract are in architecture §6 and api-contracts `ReflectResult`. **Reflect output is untrusted generated text** — it is never used to change SQLite, and is rendered without HTML.
Why Reflect ≠ recall: see demo-plan §4. If L9 shows the output is generic, the seed data and `reflect_mission` are tuned; we do **not** post-edit Reflect text.
Empty-bank rule: the application does **not** call Reflect when SQLite has zero resolved incidents (`status="empty"`); L10 records what Hindsight does anyway.

## 8. Outbox interplay (summary; canonical lifecycle in data-model §3)
Adapter `retain()` returns `ok|error`+`error_kind`; it never knows the words `pending/synced/failed`. The outbox worker (`services/outbox.py`) owns all state transitions. `document_id` = incident ID makes a crash-after-accept retry an idempotent upsert **[D; confirm L7]** ⇒ at-least-once delivery, no duplicate memories.

## 9. Banks and reset safety (summary; canonical rules in data-model §6)
- Bank IDs: demo `srma-demo-YYYYMMDD-NN` (versioned, never reused), dev `srma-dev-<name>[-NN]`, eval `srma-eval-<runid>`, spike `srma-spike-<stamp>`. `DEMO_MODE=true` requires a `srma-demo-*` bank; `DEMO_MODE=false` forbids it (a developer cannot touch the demo bank by accident).
- **No HTTP endpoint and no app code deletes or clears a bank, a document or memories.** "Reset" = CLI `demo-new` / `dev-new`: new SQLite file + new bank id; the old SQLite file is renamed into `data/archive/`, the old bank is left untouched (a human may delete it in the Cloud console). **Nothing is deleted from SQLite or Hindsight by any reset.**
- The spike script only touches `srma-spike-*` banks and never calls a delete method.

## 10. Live verification register (every row is **NOT RUN** until H2 pastes output)
Run order: `pip install hindsight-client==1.2.0` → `python spike/inspect_sdk.py` → `python spike/hindsight_smoke.py` (writes `spike/results/<ts>.json`). Fill the last column **only** from that JSON; copy snippets into `docs/hindsight-spike-results.md`.

| ID | Question | Script step | Blocks | Result |
|---|---|---|---|---|
| L1 | Auth works; `get_version` response; installed SDK version | `L1_version`, `meta.sdk_version` | adapter | NOT RUN |
| L2 | `acreate_bank` works with missions; error type; idempotent on existing id?; `arecall` on a never-created bank: error or auto-create? | `L2*` | `ensure_bank`, CLI | NOT RUN |
| L3 | Sync retain latency, `RetainResponse` fields, `usage`; does `timestamp` accept an ISO string (L3b)? | `L3*` | retain timeout, sync vs async | NOT RUN |
| L4 | Are `document_id`, `metadata`, `tags`, `scores.*`, `mentioned_at` populated on recall hits? Does `tags_match="any_strict"` filter as documented? | `L4*` | provenance order (§6) | NOT RUN |
| L5 | Time from retain return to first recall hit; time until observations consolidate | `L5`, `L5b` | live-retain demo, T-test timing | NOT RUN |
| L6 | Hits per document; do observation hits carry `source_fact_ids`; shape of `source_facts` items (has `document_id`?) | `L6_multi_hit` | rule 4 in §6 | NOT RUN |
| L7 | Duplicate `document_id`: counts after replace / append; **after replace with changed content, are old facts and observations gone from recall?** | `L7*` | idempotent retry, correction flow | NOT RUN |
| L8 | Async retain + same `operation_id` twice; status polling; time to `completed` | `L8*` | only if async mode adopted | NOT RUN |
| L9 | Reflect: shape, `structured_output`, `based_on` content, whether incident IDs appear, latency at budget low/mid, run-to-run variance | `L9*` | reflect timeout, validation design | NOT RUN |
| L10 | Recall/Reflect on an existing empty bank | `L10*` | empty-state rules | NOT RUN |
| L11 | Error shape for bad key (exception type/status/body); 402/429 only if encountered | `L11*` | error classification table (§4) | NOT RUN |
| L12 | Score behaviour: relevant vs unrelated vs signature queries (are scores query-relative as documented?) | `L12_scores` | confirms rank-only rule | NOT RUN |
| L13 | Credit cost per retain/recall/reflect (dashboard balance before/after); promo applied? | manual | budget | NOT RUN |
| L14 | **Extraction fidelity:** do extracted facts keep the incident ID, failed fixes, confirmed-vs-suspected, versions? (human reads `L14_extracted_facts`) | `L14` | retain narrative/mission tuning | NOT RUN |

**Task 2 is complete only when:** (a) `inspect_sdk.py` output is pasted and §3 reconciled with it; (b) every L-row above has a real result or an explicit "not supported / failed" note; (c) §11 is filled from real responses; (d) the contracts in api-contracts.md are corrected for any difference found. Until then the adapter is built against the Protocol + fake, and `MEMORY_BACKEND=fake` remains the default in CI.

## 11. Verified request/response examples
*Intentionally empty. To be pasted verbatim from `spike/results/<ts>.json`. No example may be written by hand.*

## 12. Sources read (2026-11-06)
Docs: hindsight.vectorize.io — Python SDK page; Retain, Recall, Reflect, Memory banks, Documents, Operations API pages; Hindsight Cloud page; models page; configuration page; docs.hindsight.vectorize.io — api-integration, billing. Source: `vectorize-io/hindsight` `hindsight-clients/python/hindsight_client/hindsight_client.py` and `pyproject.toml` at tag `v1.2.0` (partial read) and `main`. PyPI `hindsight-client`. **Discrepancy noted:** the `main`-branch read listed fewer `alist_memories`/`aretain` parameters than the v1.2.0 tag; this is why the *installed* package must be inspected (`inspect_sdk.py`) before the adapter is finalised.

## 13. Unverified assumptions specific to Hindsight (see implementation-plan §8 for the full register)
Installed SDK = 1.2.0 and matches §3 · `timestamp` as `datetime` is accepted · `document_id`/`metadata`/`tags` are returned on hits · observation attribution via `source_facts` works · `replace` removes stale facts *and* observations · sync retain latency acceptable (< ~30 s) · reflect latency acceptable at `budget="mid"` · Cloud bank creation/config via SDK works with our key · promo credit applied · Cloud model not configurable.
