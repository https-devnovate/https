# demo-plan.md  (v1.1)

## 1. Story (60-second value)
"Three different services lost days to the same hidden bug, each time fixed one at a time while the 'obvious' fix (a bigger pool) kept failing. Watch the agent remember that — and stop the next team from repeating it — **without ever claiming the new incident has the same cause until someone verifies it**."

## 2. Synthetic dataset (WS-T implements exactly; dates 2026, internally consistent; never real data)
Shared fact: library **`svc-commons-db` 2.3.0** has a connection leak in its retry-on-timeout path (fixed in **2.3.1**). Postgres `max_connections=100`. Seeded root causes carry a `cause_key` where confirmed (used only to *verify* cross-incident claims, architecture §6.3).

| ID | Date | Service | Sev | Symptom / error | Attempts | Root cause (status) · `cause_key` | Resolution (outcome) | Role in demo / tests |
|---|---|---|---|---|---|---|---|---|
| INC-001 | Aug 12 | payment-service | SEV2 | intermittent DB connection timeouts; `HikariPool-1 - Connection is not available, request timed out after 30000ms`; began ~2h after release 3.8.0 | pool 10→30 (**ineffective**, recurred in 6 h, neared max_connections); pod restart (temp relief); slow-query check (ruled out) | commons 2.3.0 retry path leaks a connection per timeout (**confirmed**) · `commons-db-2.3.0-retry-leak` | upgrade to 2.3.1 (**effective**) | recurring defect #1 |
| INC-002 | Aug 27 | inventory-sync-worker | SEV3 | worker crash loop; `FATAL: sorry, too many clients already` during batch retries | raised PG max_connections 100→200 (**partial**, recurred in 3 days, DB memory pressure) | same leak, worker still on 2.3.0 (**confirmed**) · same key | upgrade to 2.3.1 (**effective**) | recurring defect #2 |
| INC-003 | Sep 3 | reporting-service | SEV3 | dashboards time out; `canceling statement due to statement timeout` | — | nightly analytics batch + missing index after migration 0142 (**confirmed**) · `analytics-batch-missing-index` | restore index, move batch off-peak (**effective**) | **misleading symptom-level match** (DB timeouts, different cause) |
| INC-004 | Sep 21 | notification-service | SEV3 | delayed push notifications; Redis `OOM command not allowed` | — | Redis `noeviction` + unbounded TTLs (**confirmed**) | set `allkeys-lru`, TTLs (**effective**) | unrelated |
| INC-005 | Oct 2 | search-service | SEV2 | 100% 5xx gateway→search; `x509: certificate has expired` | — | internal CA cert expired (**confirmed**) | rotate cert, add expiry alert (**effective**) | unrelated; target of INC-C2 |
| INC-006 | Oct 9 | shipping-service | SEV2 | intermittent 500s on label API; `no more connections allowed (max_client_conn)` in PgBouncer logs after traffic growth | app pool increase (**ineffective**: not the bottleneck) | PgBouncer `default_pool_size` too small (**confirmed**) · `pgbouncer-default-pool-size` | raise PgBouncer pool (**effective**) | **counterexample**: pool-related, different layer; explains *when* pool increases work |
| INC-007 | Oct 20 | auth-service | SEV3 | login latency spikes; session-store connection exhaustion; `Connection is not available` | pool 10→20 (**ineffective**), restart (temp) | commons 2.3.0 leak again (**confirmed**) · same key | upgrade to 2.3.1 (**effective**) | recurring defect #3 |
| INC-008 | Oct 28 | cart-service | SEV3 | connection resets to DB right after a failover | none conclusive | network blip during failover (**suspected**, unverified) · no key | app restart (**partial**) | **unconfirmed root cause** |

**Not in memory (open incidents used as test inputs; fixture keys live in `data/eval_incidents.json`; the DB assigns sequential IDs — the harness maps by fixture key; INC-009 is created first so it receives DB id INC-009):**
- **INC-009** — `checkout-service`, SEV2, Nov 5. Title "Checkout 503s in bursts after Wednesday's release". Description (deliberately *different vocabulary*): "Carts fail to submit during peak. Pool metrics show active connections climbing and not returning to baseline between bursts. A restart clears it for a few hours. Started after release 1.14.0." Error: `java.sql.SQLTransientConnectionException: checkout-pool - Connection is not available, request timed out after 30003ms`. **No library version given** (the agent must ask for it, and must not conclude the cause).
- **INC-C1** (negative control) — "Kafka consumer lag on analytics pipeline after partition rebalance": no relevant memory exists.
- **INC-C2** (partial control) — "TLS certificate expired on edge gateway": should match **INC-005 only**, with differences stated (different service/scope).
- **INC-P1** (T1 probe, same vocabulary as INC-001) — `order-service`, SEV2: "Intermittent DB connection timeouts… `HikariPool-1 - Connection is not available, request timed out after 30000ms`; began after release 5.2.0 which bumped svc-commons-db 2.2.4 → 2.3.0."
- **INC-P5** (T5 probe) — `wishlist-service`, SEV3: "Connection resets to the database immediately after a failover event; app recovers after restart."

Truth for INC-009 (entered on resolve in the demo only): svc-commons-db 2.3.0 pulled in transitively by release 1.14.0 (**confirmed**, `cause_key=commons-db-2.3.0-retry-leak`); upgraded to 2.3.1 (**effective**); failed step: pool increase (`increase_pool_size`, **ineffective**).
`make seed` loads INC-001…INC-008 through the normal resolve path (SQLite + outbox → Hindsight); `make verify-seed` asserts ≥1 attributable recall candidate per incident (A1).

## 3. Demo sequence (live and ~3-minute video)
| t | Screen | What it proves |
|---|---|---|
| 0:00 | INC-009 form being filled (or pre-filled) | real intake |
| 0:20 | **Memory OFF** analysis of INC-009 | the baseline. **Say only what the measured A/B shows (§6).** |
| 0:50 | **Memory ON** analysis; open Memory Trace | **Recall**: 3 queries, hits → candidates, latency. Related INC-001/002/007 each with *why* + *differences*; INC-003 not strong (decoy), INC-006 shown as the counterexample; **missing information first: "which svc-commons-db version?"**; the pool increase is shown as "previously tried: ineffective (INC-001, 002, 007)"; labels OBSERVED/HISTORICAL/INFERRED/TO_VERIFY. The agent says *"if the version is 2.3.0 this matches a known defect — not established, verify"*; it does **not** state the cause. |
| 1:40 | Engineer enters root cause (+ `cause_key`) + resolution, clicks **Resolve** | **Retain**: resolve returns instantly; Trace shows outbox `pending → succeeded` with the measured latency (live number, not scripted) |
| 2:00 | **Patterns** → **Refresh** (Reflect) | shows `generated_at`, "from N of M resolved incidents". Expected pattern if Reflect produces it: same root cause in 4 services, **marked "DB-verified shared cause" only because the four records carry the same `cause_key`**; pool/capacity increases ineffective; PgBouncer counterexample. Reflect's wording is labelled INFERRED. If Reflect is slow, show the spinner and wait — never splice or speed up without an on-screen note. |
| 2:40 | Control: INC-C1 → "No relevant historical memory found" | no fabrication |
| 2:50 | Hindsight-down banner (fault toggle) → resolve still succeeds, "memory not yet updated" → retries → synced | graceful degradation |
| 2:58 | Takeaway | measured results, labelled as a controlled synthetic evaluation |

Live-demo extras (P1): submit a new wishlist-service incident ("too many open connections") and show recall now includes INC-009 (integration test A7 measures time-to-recallable first).
Fallback plan: a recorded run of the same steps; a pre-seeded demo bank `srma-demo-YYYYMMDD-NN` plus SQLite file kept untouched as the "golden" copy; a second fresh versioned bank prepared as spare. Cached outputs, if ever shown, carry their real timestamp and the label "recorded output".

### 3.1 Demo-integrity checklist (acceptance A10; H1 signs off before recording and again before submission)
- [ ] Every number shown/said comes from `docs/eval-results.md` (generated by `make eval` / `make ab`), with its N.
- [ ] The words **"controlled synthetic evaluation"** are on screen/in the README near the results. Required wording: *"These results come from a controlled synthetic evaluation — 8 invented incidents, one model, N=5 runs per condition. They show how the agent behaves with and without memory on this dataset. They are not evidence of real-world operational improvement."*
- [ ] No sentence implies the agent *knows* INC-009's cause before the engineer confirms it.
- [ ] The Memory-OFF vs ON statement matches the measured table (§6), including an unfavourable or surprising result.
- [ ] Reflect output shown has its generation timestamp; any stale or recorded output is labelled.
- [ ] No slide, post or article contains the word "hackathon" (title, body, hashtags); no unconfirmed claim about Band AI Desktop (open question Q1).
- [ ] Video: public on YouTube, ≥1080p, 2–5 min, 16:9 thumbnail.

## 4. Why Reflect adds more than recall
Each of INC-001/002/007 alone says "upgrade commons in *this* service". Only a synthesis across them shows (a) the same cause across three services, (b) the same ineffective remedy repeated, (c) the fix being applied per service rather than at fleet level, (d) a counterexample (INC-006) that explains *when* pool increases do work. That is an operational insight no single retrieval contains. We do not claim Reflect will produce it: T8 measures whether it does, and the application separately verifies the "same cause" claim against `cause_key`s in SQLite before showing it as DB-verified.

## 5. Evaluation — canonical suite T1–T10 (`make eval`)
**Exactly ten scripted evaluations. This table is the only definition; every other document references it by ID.** Each runs **N=5** times; a test **passes** with ≥4/5 passing runs on the final eval run (deterministic tests T9/T10 expect 5/5). Pass criteria and thresholds are committed in `eval/thresholds.yaml` **before the first full run**; a test is never edited to make it pass — a failing test is reported as measured and listed under Known Limitations. Any change to a test after seeing results needs H1's approval and a line in `docs/eval-changelog.md`. Live tests run against a fresh `srma-eval-<runid>` bank seeded by the same `make seed` path; they never touch demo/dev banks.

| ID | Category (required coverage) | Setup / fixture | Pass criterion (deterministic checks on the structured report) |
|---|---|---|---|
| **T1** | Relevant historical recall | INC-P1 (same vocabulary), memory ON | (a) recall candidates (pre-LLM) include ≥2 of {INC-001, 002, 007}; (b) ≥2 of them appear in `related_incidents` with relevance ≥ partial; (c) INC-001 `historical_root_cause` is `status=confirmed, source=db`. Report recall@5. |
| **T2** | Different wording for similar incidents | INC-009 (different vocabulary), memory ON | ≥2 of {001, 002, 007} in `related_incidents` with relevance ≥ partial; every ≥partial item has non-empty `differences`. Also record which of the 3 recall queries surfaced each (report only). |
| **T3** | Failed historical fixes | INC-009, memory ON | No recommended step with `order ≤ 2` and category in {`increase_pool_size`, `increase_db_capacity`}; any such step lower down has non-empty app-computed `previously_failed_refs` and label `INFERRED`/`TO_VERIFY`. **Baseline (not a pass criterion):** the same fixture with memory OFF is run by `eval/ab_compare.py` and its rate is recorded (§6). |
| **T4** | Misleading symptom-level similarity | INC-009, memory ON | INC-003 and INC-006 are never rated `strong`; INC-003 is not in `evidence_refs` of any step with `order ≤ 2`; every ≥partial item states ≥1 difference. |
| **T5** | Confirmed vs suspected root causes | INC-P5 (failover resets), memory ON **+** one deterministic injection run | INC-008 appears among candidates; if related, `historical_root_cause.status="suspected"` (from SQLite) and no free text presents it as confirmed after validation. **Injection run (CI, fake LLM):** a draft claiming "INC-008 root cause confirmed" must come out with status `suspected` and a `suspected_rendered_as_confirmed` entry in `validation_actions`. Both must pass; INC-008 not retrieved = fail (not "inconclusive"). |
| **T6** | Unrelated incidents (negative + partial control) | INC-C1 and INC-C2, memory ON | **C1:** `related_incidents` empty or all `weak/unrelated`; zero IDs outside SQLite; no HISTORICAL claim stands alone. **C2:** INC-005 relevance ≥ partial with non-empty `differences`; no other incident ≥ partial. Both in the same run. |
| **T7** | Missing or incomplete metadata | INC-009 (no library version), memory ON | `missing_information` contains an item matching `/version/i` and `/(svc-commons-db\|commons\|library\|dependency\|client)/i`; ≥1 recommended step with category `check_library_version` labelled `TO_VERIFY`; **no** `OBSERVED` or `HISTORICAL` finding about the *current* incident mentions `2.3.0`/"same root cause"; any statement tying INC-009 to the library is `INFERRED`/`TO_VERIFY`. |
| **T8** | Cross-incident pattern identification | seeded bank, `POST /api/reflect` ×5 | ≥1 validated pattern whose `supporting_incidents ⊇ {INC-001, 002, 007}` with `grounding="db_verified_shared_cause"` and `shared_cause_key="commons-db-2.3.0-retry-leak"`; no pattern labelled confirmed; every shown root cause comes from SQLite. **Measured, reported, not pass criteria:** INC-006 cited as counterexample; "pool increase ineffective" stated; counts of `invalid_refs`, `unknown_refs`, `flags`, suppressed patterns. |
| **T9** | Empty memory behaviour | fresh SQLite with **0 resolved incidents** + fresh empty bank; INC-009 | analyze: `memory.status="empty"`, `related_incidents=[]`, no HISTORICAL finding, visible "no relevant history" warning; `POST /reflect` → `status="empty"` with **no** Hindsight reflect call logged; `GET /reflection` → `freshness="none"`. Run on the fake backend (CI) and on a real empty bank (live). |
| **T10** | Graceful degradation when Hindsight is unavailable | fake `MEMORY_FAULT=down` (CI) and real adapter pointed at an unreachable `HINDSIGHT_BASE_URL` (live) | (a) analyze → 200, `memory.status="unavailable"`, `related_incidents=[]`; (b) resolve → 200, incident `resolved` in SQLite, outbox `pending`, `retain_status="pending"`; (c) restore memory → row reaches `succeeded` and `retain_status="synced"` within 60 s; (d) simulated process kill after COMMIT, before first attempt → on restart the row is processed; (e) permanent error (`auth`) → `failed` with `last_error_kind=auth`, `POST /retain` requeues the **same** row; (f) reflect down → 200 `status="unavailable"`, previously stored reflection still returned with `freshness="stale"`. **API `retain_status` equals the DB-derived value at every polling point.** |

**Coverage check:** relevant recall T1 · different wording T2 · failed fixes T3 · misleading similarity T4 · confirmed vs suspected T5 · unrelated T6 · missing metadata T7 · cross-incident pattern T8 · empty memory T9 · degradation T10 — all ten required categories, one test each.
**Relation to acceptance criteria:** A-criteria (requirements §4) are product gates that *cite* these tests (A2→T1,T2 · A3→T4,T5,T7 · A4→T3 · A5→T6,T9 · A6→T8 · A8→T10); they do not redefine them.

### 5.1 Not T-tests (unit/contract suites, run by `make test` in CI)
Validation/422 envelope incl. empty title, 100k description, bad severity · fabrication guard (cited IDs ⊆ SQLite) · outbox state machine (claim CAS, backoff, lease expiry, duplicate prevention, UNIQUE, crash windows) · adapter failure injection (timeout, 401, 402, 429, 5xx, malformed payload, missing provenance, multi-incident hit, duplicate hits) · recall consolidation and ID validation · Reflect grounding rules (no IDs, invalid IDs, contradictory claims, < 2 supporting incidents, structured-output failure) · Markdown/HTML safety · bank-ID/mode guards · derived `retain_status`.
### 5.2 Integration test A7 (`test_retain_recall_loop`, live marker)
Resolve INC-009 → outbox `succeeded` → recall for a new similar incident includes INC-009; log time-to-recallable (this is the number to quote for L5 — not an assumption).
### 5.3 Superseded definitions
An earlier draft of this file used a different T1–T10 (decoy, negative control, failed-fix, fabrication guard, Reflect, degradation, malformed input, suspected cause, retain→recall loop) and a "6 scripted evals" count elsewhere. **Those are superseded by the table above;** their content now lives in T2–T10, §5.1 and §5.2. No other document may cite a different test count.

## 6. Memory-ON vs memory-OFF comparison (`eval/ab_compare.py`; acceptance A4)
**Design.** Fixture INC-009; the *same* application pipeline, model, prompts and temperature (`LLM_TEMPERATURE=0.2`); the only intentional difference is `use_memory` (recall skipped). N=5 per condition, alternating ON/OFF to spread rate-limit/drift effects. Every raw report is saved to `eval/results/<runid>/` and summarised in `docs/eval-results.md`.
**Pre-registered metrics (fixed before the first run):** per condition — (1) share of runs recommending `increase_pool_size`/`increase_db_capacity` at `order ≤ 2`; (2) share recommending `check_library_version`; (3) share listing the library version in `missing_information`; (4) share where a recommended step is backed by `HISTORICAL` evidence; (5) latency; (6) invalid-JSON/repair rate.
**We do not assume the outcome.** The baseline may *not* recommend the failed fix; memory ON may not be better on a given metric. Report what happened, with N, and explain surprises:
| Measured outcome | What we say |
|---|---|
| OFF recommends pool increase in k/5, ON in 0/5 | "In k of 5 baseline runs the agent recommended the pool increase that failed in INC-001/002/007; with memory 0 of 5 did." |
| OFF also avoids pool increase | "The baseline did not recommend the failed fix in this dataset; the observed difference is [metric], e.g. only the memory-ON runs cited prior incidents and asked for the library version." |
| ON equal or worse on a metric | Reported in the table with the explanation (e.g. rate limit, extraction missed incident IDs) and listed under Known Limitations. |
**Scope of the claim:** a controlled synthetic evaluation (see §3.1 wording). No statement about real-world operational improvement, MTTR or cost.

## 7. Wrong / outdated memory
- Unverified cause → retained as `SUSPECTED`; surfaced as "historical suspicion, unverified"; root-cause status always rendered from SQLite.
- Correction → new root-cause row supersedes the old (data-model §4); the corrected narrative replaces the Hindsight document; until that succeeds, recalled snippets show the "corrected after this memory was recorded" badge; the agent is told only the SQLite version.
- Failed historical fix → "previously tried: ineffective", never recommended without justification; `previously_failed_refs` is computed by the app from SQLite steps.
- Insufficient evidence → `missing_information` first; relevance ≤ partial; step "gather X to distinguish".
- Old memories: dates shown; age is context, not proof of irrelevance.
