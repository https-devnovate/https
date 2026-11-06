# demo-plan.md

## 1. Story (60-second value)
"Three different services lost days to the same hidden bug, each time fixed one at a time while the 'obvious' fix (bigger pool) kept failing. Watch the agent remember that — and stop the fourth team from wasting time."

## 2. Synthetic dataset (WS-T implements exactly; dates 2026, internally consistent)
Shared fact: library **`svc-commons-db` 2.3.0** has a connection leak in its retry-on-timeout path (fixed in **2.3.1**). Postgres `max_connections=100`.

| ID | Date | Service | Sev | Symptom / error | Attempts | Root cause (status) | Resolution (outcome) | Role in demo |
|---|---|---|---|---|---|---|---|---|
| INC-001 | Aug 12 | payment-service | SEV2 | intermittent DB connection timeouts; `HikariPool-1 - Connection is not available, request timed out after 30000ms`; began ~2h after release 3.8.0 | pool 10→30 (**ineffective**, recurred in 6 h, neared max_connections); pod restart (temp relief); DB slow-query check (ruled out) | commons 2.3.0 retry path leaks a connection per timeout (**confirmed**) | upgrade to 2.3.1 (**effective**) | relevant #1 |
| INC-002 | Aug 27 | inventory-sync-worker | SEV3 | worker crash loop; `FATAL: sorry, too many clients already` during batch retries | raised PG max_connections 100→200 (**partial**, recurred in 3 days, DB memory pressure) | same leak, worker still on 2.3.0 (**confirmed**) | upgrade to 2.3.1 (**effective**) | relevant #2 |
| INC-003 | Sep 3 | reporting-service | SEV3 | dashboards time out; `canceling statement due to statement timeout` | — | nightly analytics batch + missing index after migration 0142 caused seq scans (**confirmed**) | restore index, move batch off-peak (**effective**) | **decoy**: DB timeouts, different cause |
| INC-004 | Sep 21 | notification-service | SEV3 | delayed push notifications; Redis `OOM command not allowed` | — | Redis eviction policy `noeviction` + unbounded TTLs (**confirmed**) | set `allkeys-lru`, TTLs (**effective**) | unrelated |
| INC-005 | Oct 2 | search-service | SEV2 | 100% 5xx from gateway→search; `x509: certificate has expired` | — | internal CA cert expired (**confirmed**) | rotate cert, add expiry alert (**effective**) | unrelated; control |
| INC-006 | Oct 9 | shipping-service | SEV2 | intermittent 500s on label API; `no more connections allowed (max_client_conn)` in PgBouncer logs after traffic growth | app pool increase (**ineffective**: not the bottleneck) | PgBouncer `default_pool_size` too small for traffic (**confirmed**) | raise PgBouncer pool (**effective**) | partial: pool-related but different layer |
| INC-007 | Oct 20 | auth-service | SEV3 | login latency spikes; session store connection exhaustion; `Connection is not available` | pool 10→20 (**ineffective**), restart (temp) | commons 2.3.0 leak again (**confirmed**) | upgrade to 2.3.1 (**effective**) | relevant #3 |
| INC-008 | Oct 28 | cart-service | SEV3 | connection resets to DB right after a failover | none conclusive | network blip during failover (**suspected**, unverified) | app restart (**partial**) | tests "suspected" handling |

**New incident INC-009 (not in memory):** `checkout-service`, SEV2, Nov 5. Title: "Checkout 503s in bursts after Wednesday's release". Description (deliberately different vocabulary): "Carts fail to submit during peak. Pool metrics show active connections climbing and not returning to baseline between bursts. A restart clears it for a few hours. Started after release 1.14.0." Error: `java.sql.SQLTransientConnectionException: checkout-pool - Connection is not available, request timed out after 30003ms`. **No library version given** (agent must ask for it).

Controls: **INC-C1** "Kafka consumer lag on analytics pipeline after partition rebalance" (no relevant memory) and **INC-C2** "TLS certificate expired on edge gateway" (should match INC-005 only).
Truth for INC-009 (used on resolve in demo): commons 2.3.0 pulled in transitively by release 1.14.0 (**confirmed**); upgraded to 2.3.1 (**effective**); failed step: pool increase.

## 3. Demo sequence (live and video; ~3 min video cut)
| t | Screen | What it proves |
|---|---|---|
| 0:00 | Problem slide-free: show INC-009 form being filled (or pre-filled) | real intake |
| 0:20 | **Memory OFF** analysis of INC-009 | generic output; recommends bigger pool / check slow queries — i.e. the fix that failed 3 times (verify this actually happens in rehearsal; if the baseline doesn't, say so — don't fake it) |
| 0:50 | **Memory ON** analysis; open Memory Trace | **Recall**: 3 queries, hits, latency; strong matches INC-001/002/007 with *why* + *differences*; INC-003 rated weak (decoy), INC-006 partial; missing info: "which svc-commons-db version?" ; pool-increase marked previously ineffective; labels OBSERVED/HISTORICAL/INFERRED/TO_VERIFY |
| 1:40 | Engineer enters root cause + resolution, clicks **Resolve** | **Retain**: trace shows retain event, status synced |
| 2:00 | **Patterns** → Reflect | **Reflect**: "same root cause in 4 services (now incl. INC-009), fixed one-at-a-time; pool/max_connections increases ineffective in 4/4 (INC-001, 002, 007, 009); PgBouncer pool increase worked only because it was the true bottleneck (INC-006); recommend auditing every service for svc-commons-db < 2.3.1" — **the cross-incident insight** |
| 2:40 | Control: INC-C1 → "No relevant historical memory found" | no fabrication |
| 2:55 | Takeaway | memory changed agent behaviour |

Live-demo extras (P1): submit INC-010 (wishlist-service, "too many open connections") and show recall now includes INC-009.
Fallback plan: pre-recorded analysis outputs cached in `data/fixtures/`; Hindsight-down banner demo available on purpose (`MEMORY_BACKEND` toggle) to show graceful degradation.

## 4. Why Reflect adds more than recall (Design Q-E)
Each of INC-001/002/007 alone says "upgrade commons in *this* service". Only the synthesis across them shows (a) the same cause across three different services, (b) the same ineffective remedy repeated, (c) the fix is being applied per service rather than at the library/fleet level, (d) a counter-example (INC-006) explaining *when* pool increases do work. That is an operational insight no single retrieval contains.

## 5. Evaluation (Design Q-D) — `make eval`, each run N=5, report actual pass rates; no claims beyond measured results
| ID | Test | Pass criterion (deterministic) |
|---|---|---|
| T1 | Recall relevance for INC-009 | ≥2 of {001,002,007} among top-5 related; report recall@5 |
| T2 | Decoy handling | INC-003 relevance ≠ strong |
| T3 | Negative control INC-C1 | `related_incidents` empty or all weak/unrelated; zero IDs outside DB |
| T4 | Failed-fix avoidance | memory-ON: no primary (order ≤2) step with category `increase_pool_size` unless `avoids_previously_failed` explained; **also record how often memory-OFF recommends it** (baseline, may be <100%) |
| T5 | Fabrication guard | all cited IDs ∈ DB; HISTORICAL labels absent when memory not ok |
| T6 | Reflect | text mentions INC-001, 002, 007 and states pool increases ineffective |
| T7 | Degradation | Hindsight forced down → 200 report with `memory.status=unavailable` |
| T8 | Malformed input | empty title / 100k description / bad severity → 422 envelope |
| T9 | Suspected-cause handling | INC-008 root cause never rendered as "confirmed" |
| T10 | Retain→recall loop | after resolving INC-009, recall for a new similar incident includes INC-009 (and time-to-recallable logged) |

## 6. Wrong / outdated memory (Design Q-F)
- Unverified cause → stored as SUSPECTED; surfaced as "historical suspicion, unverified".
- Contradiction → agent shows both with dates; later correction note wins; app DB `superseded` status.
- Failed historical fix → shown as "previously tried: ineffective", never recommended without justification.
- Insufficient evidence → `missing_information` first; relevance ≤ partial; step "gather X to distinguish".
- Old memories: dates shown; age is context, not proof of irrelevance.
