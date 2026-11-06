# implementation-plan.md  (v1.1 — re-planned for the real remaining time; all clock times IST)

**Time reality (as of Fri Nov 6, ~16:00 IST): ≈ 32 hours to the 11:59 PM deadline on Sat Nov 7 — not a fresh 36.** Timings below assume the working windows in §6 (marked **[A: needs H-team approval]**); if the team is less available, cut by the order in §9, never by dropping the Retain/Recall/Reflect/A-B core or the submission buffer.

## 1. Stack and version freeze (decision record)
| Layer | Choice | Version status (nothing invented) |
|---|---|---|
| Backend | Python **3.11** + FastAPI + **Pydantic v2** | Python minor recorded in `.python-version`. FastAPI/Pydantic/uvicorn: **pending — H1 freezes the exact resolved versions from the lockfile at G1**. Constraint already known: `hindsight-client` requires `pydantic>=2` and `python>=3.10` [D]. |
| App DB | SQLite (WAL, `foreign_keys=ON`) + **SQLAlchemy 2.x**, sync engine; DB calls from async code via `asyncio.to_thread` [A: H1 confirm] | SQLAlchemy exact version pending (G1). |
| Frontend | React **18** + Vite + TypeScript + Tailwind + `react-markdown` (no `rehype-raw`) | exact versions pending (G1, `package-lock.json`). |
| LLM (application) | Groq via the OpenAI-compatible Python client, base `https://api.groq.com/openai/v1` [D]; primary `openai/gpt-oss-120b` (Production on Groq's models page 2026-11-06 [D]; strict JSON-schema supported [D]); JSON output + Pydantic validation + 1 repair retry; no tool calling | client package/version pending (G1). **Fallback model unresolved:** the organiser guide names `qwen/qwen3-32b`, which is **not listed** on Groq's current models page and has no documented json_schema support; candidate `openai/gpt-oss-20b`. Decide after `spike/groq_smoke.py` (decision D6). |
| Memory | Hindsight Cloud (fallback: local Docker — self-hosted Hindsight takes its own `HINDSIGHT_API_LLM_PROVIDER=groq` + key [D]); SDK **`hindsight-client==1.2.0`** pinned exactly | version selected [D]; **installed version to be confirmed by `pip show` / `spike/inspect_sdk.py` (Task 2)**. Not upgraded after the smoke test passes. |
| Tests | pytest, pytest-asyncio; adapter tests inject a fake SDK client object; Playwright smoke (P1) | pending (G1) |
| Agent framework | none | — |
**Freeze rule:** at G1 H1 commits lockfiles (`uv.lock`/`requirements.lock`, `package-lock.json`) and a `docs/versions.md` listing the exact resolved versions; the architecture, this table and `.env.example` must agree with it. After G4 only security-critical upgrades. Rejected: Next.js (SSR overhead), Postgres (setup, no benefit), LangChain (no demo value), a message broker (SQLite outbox suffices), Kubernetes.
Environment variables: single table in api-contracts.md "Configuration".

## 2. Repository, branches, ownership
One canonical GitHub repo `srma`. CODEOWNERS enforces the map; branch protection on `main`.
```
/docs, /README.md, pyproject.toml + lockfiles, .env.example      H1 (WS-A)   [others request changes via PR comment]
/backend/app/contracts.py                                         H1 (WS-A)   frozen at G1; PR-only afterwards
/backend/app/main.py, api/, services/ (incl. outbox.py, reflect_service.py,
    incident_service.py, analysis_service.py), db/, config.py, srma/cli.py   WS-B
/backend/app/memory/ (base.py, hindsight_adapter.py, fake_memory.py, templates.py), /spike/      WS-H
/backend/app/agent/ (pipeline.py, prompts.py, llm.py, fake_llm.py, validators.py)               WS-I
/frontend/                                                        WS-F
/data/ (seed_incidents.json, eval_incidents.json, fixtures/), /eval/, /tests/, Makefile, Dockerfile, docker-compose.yml, .github/   WS-T
```
Rules (to prevent uncontrolled overlap):
1. Each Claude resource works in its **own git worktree/branch** (`ws/backend`, `ws/hindsight`, `ws/agent`, `ws/frontend`, `ws/testdata`) cut from `main` after G1; no two resources share a working tree.
2. Small PRs into `main`; **no direct pushes**; every PR reviewed by H1 and the owner of any touched module; CI must pass.
3. No edits outside owned paths — request via the owner. Shared files (`pyproject.toml`, lockfiles, `.env.example`, `Makefile`) are changed only by their single owner.
4. Contract change = one PR touching `contracts.py` **and** `api-contracts.md`, announced in the team chat, approved by H1.
5. Rebase on `main` at least every 3 hours; merge queue handled by H1 at the sync points in §6 (at least 20:30, 23:00, 08:30, 11:30, 13:30, 16:00).
6. `main` must always boot and pass `make test` with `MEMORY_BACKEND=fake LLM_BACKEND=fake` (both flags stay supported to the end). **No workstream waits for the Hindsight spike except the final form of `memory/hindsight_adapter.py`.**
7. CI greps: no Hindsight SDK import outside `memory/`; no `delete|clear|reset_bank` outside `spike/`; no `hackathon` in `README.md`/`docs/content/`.

## 3. Scope classification (nothing silently moved)
| Pri | Items |
|---|---|
| **P0** | F1–F11 (intake, analysis, recall, related-incident comparison, evidence labels, resolve + retain **via SQLite outbox**, Reflect with grounding validation, memory-ON/OFF A/B, dashboard, seed by CLI, graceful degradation); Memory Trace panel; **F14 evaluation infrastructure and all ten scripted evaluations T1–T10 (demo-plan §5)**; README; demo video; content deliverables |
| **P1** | F12 correction UI (schema + outbox kind are P0); F13 feedback retention; live-learning incident (demo-plan §3 extras); single-container deployment; Playwright smoke; eval table polish |
| **P2** | per-service pattern filter; export report; dark mode; confidence charts |
| **Out** | requirements §5 |
**Changes vs v1.0 of this plan (all deliberate, none a silent demotion):** eval harness and full T1–T10 **P1 → P0** (and "6 scripted evals" removed); outbox + derived retain status added to P0 (integrity); Reflect **auto-refresh after resolve → manual refresh** with stored last success + staleness (the Reflect *capability* stays P0); seed/reset moved **from HTTP to guarded CLI** (still P0); `cached fallback outputs` P1 → only a golden demo DB + recorded run (labelled).

## 4. Work packages, owners and acceptance criteria
### WS-A Architecture / Integration — H1 (+ architect chat)
Objective: one architecture, frozen contracts, reviewed integration. Owns docs, `contracts.py`, skeleton, CODEOWNERS, CI skeleton, version freeze.
**Acceptance:** `main` boots with both fakes (`make dev`); OpenAPI exports; TS types generate; `contracts.py` ≡ api-contracts.md (diff review); `docs/versions.md` committed; every PR reviewed < 1 h in working windows; organiser questions Q1–Q3 sent by 17:00 Fri; consistency checklist (§10) re-run before code freeze.
### WS-B Backend — Claude-B, driver H3
Objective: API, persistence, orchestration, outbox, CLI.
**Deliver:** all 13 endpoints on fakes; SQLite models incl. `retain_outbox`, `reflections`, `app_meta`; `resolve()` single-transaction + outbox insert; `services/outbox.py` (claim CAS, backoff, lease, requeue, worker at boot + 10 s tick, `kick()`); derived `retain_status`; `reflect_service` implementing architecture §6.3; recall enrichment/ID validation; CLI (`seed`, `drain-outbox`, `verify-seed`, `bank-info`, `demo-new`, `dev-new`, `archive-db`) with bank/mode guards; error envelope; CORS; static SPA serving.
**Acceptance:** contract tests for every endpoint incl. 422/404/409; outbox state-machine tests (transitions per data-model §3 incl. crash windows, duplicate prevention, UNIQUE, lease expiry); `resolve` succeeds with `MEMORY_FAULT=down` and `retain_status="pending"`; `test_retain_status_matches_outbox`; analyze works with recall unavailable/empty; unknown/open/malformed IDs dropped; Reflect grounding unit tests (no IDs, invalid IDs, contradiction, <2 incidents, structured-output failure); no HTTP route deletes anything; CLI refuses illegal bank/mode pairs.
### WS-H Hindsight — Claude-H, driver/owner H2
Objective: documented-and-then-verified Retain/Recall/Reflect behind `MemoryService`; Task 2 closure.
**Deliver:** (Fri 16:30–19:00) H2 runs `inspect_sdk.py` + `hindsight_smoke.py` → `docs/hindsight-spike-results.md`; `FakeMemoryService` with fault injection and keyword-overlap over fixtures (Fri 18:30); real adapter (Fri 19:00–23:00) per hindsight-integration §3–§7: async-only, never raises, error classification, provenance resolution, dedup + consolidation, bank guard, call logging; `ensure_bank`; seed run into a `srma-dev-*` bank.
**Acceptance:** adapter unit tests with an injected fake SDK client (timeout, 401, 402, 429, 5xx, empty, malformed, missing `document_id`, multi-incident hit, duplicate hits); no SDK type leaks (CI grep); with the seeded bank, recall for INC-009 returns candidates containing ≥2 of {001,002,007} (A1/T1 precondition); `hindsight-integration.md` §10/§11 filled with real output and every L-row resolved or explicitly marked failed/unsupported; contracts corrected by PR if the spike differs.
### WS-I Agent Intelligence — Claude-I, driver H4
Objective: extraction + memory-grounded analysis, labels, uncertainty.
**Deliver:** `extract`/`analyse` prompts with strict JSON-schema output, repair retry, fallback model, `fake_llm` canned drafts (incl. deliberately bad drafts for validator tests); `validators.py` implementing the label rules; Groq smoke (H4) to settle the fallback model.
**Prompt rules (must exist):** similar symptoms ≠ same cause; list differences; rate relevance; flag missing information first; never assert a historical cause for the open incident; never recommend an action previously rated ineffective without explaining the difference; prefer read-only checks; no production changes; later correction supersedes earlier note.
**Acceptance:** schema tests; validator tests for every label rule; golden-fixture tests with `fake_llm`; live T1–T7 each ≥4/5 on the final run, or reported as measured; invalid JSON recovered or clean `LLM_UNAVAILABLE`.
### WS-F Frontend — Claude-F, driver H5
Objective: clear, demo-friendly UI on the frozen contract.
**Screens (P0):** incident list + form; incident detail with Analyze toggle and **ON-vs-OFF side-by-side**; related-incident cards (relevance badge, why, matches, differences, past attempts with ineffective marked, past resolution, root-cause status chip, "memory snippet" vs DB-sourced fields, provenance/"corrected after memory" badges); recommendations with label chips + advisory banner; **Memory Trace** (events + outbox current state, attempts, next retry, raw Reflect as escaped text); **Patterns** (freshness, "generated from N of M", Refresh, pattern cards with DB-sourced supporting incidents and grounding chip, collapsed unverified synthesis); Resolve form (+ `cause_key`, step categories) with retain-status chip that polls pending→synced/failed and a Retry button; banners for unavailable/empty/disabled/stale; loading/error states.
**Acceptance:** demo script runs by mouse only; no uncaught errors; every state in api-contracts rendered (incl. `memory.status` ×4, `retain_status` ×4, `freshness` ×3); Markdown safety test (script/img/HTML in Reflect text does not execute or render); typecheck + build in CI; readable at 1080p.
### WS-T Testing / Data / Deployment — Claude-T, driver H6
Objective: dataset, evals, CI, run-anywhere packaging.
**Deliver:** (Fri 19:00) `seed_incidents.json` (INC-001…008) and `eval_incidents.json` (INC-009, C1, C2, P1, P5) exactly per demo-plan §2, internally consistent; CI; **eval harness for T1–T10 + `eval/ab_compare.py` + `eval/thresholds.yaml` (committed before the first full run)** running against fakes by G2 and against the real stack by G4; data-consistency checker; Makefile (`seed`, `verify-seed`, `dev`, `test`, `eval`, `ab`, `demo-new`); README quickstart; secret scan; Dockerfile (P1).
**Acceptance:** `make test` green in CI; `make eval` prints the T1–T10 table with N=5 and writes `docs/eval-results.md`; deterministic tests (T5-injection, T9, T10) pass 5/5 on fakes; clean checkout → running demo in < 10 min (A9, fresh-clone test by H6); no secrets in history.
### All members — Content (owned by humans; see §5 for owners)
Per member: article 1,200–1,500 words (Q2 interim; no "hackathon" anywhere; includes real code snippet, before/after, honest limitation, screenshots, the three required links; measured numbers only, with the §3.1 disclaimer from demo-plan), Reddit link post, LinkedIn post (<800 chars, repo link, 3–5 hashtags last line, article URL as first comment, Hindsight GitHub link as second comment; tag Code.in).

## 5. Task allocation — six humans, five Claude resources
| Who | Role | Drives / owns | Also named owner of |
|---|---|---|---|
| **H1** | Architect & Integration Lead | WS-A; contracts, reviews, merges, version freeze, final consistency check | organiser questions Q1–Q3; demo-integrity sign-off (demo-plan §3.1); tech accuracy review of articles |
| **H2** | Hindsight owner | Claude-H (WS-H); Cloud account, key, credits (+ promo check), bank hygiene, spike, L-register | A7 live loop test; bank IDs for demo/eval |
| **H3** | Backend & data-integrity lead | Claude-B (WS-B) | **content compliance scan** (no "hackathon", links, hashtags) before anything is published |
| **H4** | Agent & evaluation lead | Claude-I (WS-I); Groq smoke | `make ab` run and the eval-results narrative |
| **H5** | Frontend, UX & demo lead | Claude-F (WS-F) | **video owner: recording, editing, YouTube upload (public), demo operator** |
| **H6** | Test, deploy & release lead | Claude-T (WS-T); CI, packaging | **submission owner:** form entry, collects explicit "yes" from all six, thumbnail (16:9), fresh-clone test A9 |
| Claude-B / -H / -I / -F / -T | one workstream each | as above; each in its own worktree | — |
Every human also authors one article, one Reddit link post and one LinkedIn post (O9). H1/H3/H6 may be pulled back to fix integration issues until code freeze.

## 6. Timeline (IST) and gates
Assumed working windows **[A: needs team approval]**: Fri 16:30–23:30 · overnight rest 23:30–07:00 (Claude workstreams may continue unattended on their own branches only; no merges, no scope changes) · Sat 07:00–22:30.
| When | Milestone | Gate (acceptance) |
|---|---|---|
| Fri 15:45–16:30 | H1 reviews this doc set; decisions D1–D8 (§8); repo created; keys; Band AI installed; **Q1–Q3 sent** | **G0:** decisions recorded, workstreams started |
| Fri 16:30–18:30 | skeleton, `contracts.py`, config, CI, minimal fakes, TS types. **In parallel:** H2 runs `inspect_sdk.py` + `hindsight_smoke.py`; H4 runs `groq_smoke.py` | **G1 18:30 — contract freeze:** `main` boots on fakes, OpenAPI + TS types generated, versions frozen. Spike results by ~19:00 (**spike gate S** — blocks *only* the final real adapter and closing Task 2) |
| Fri 18:30–23:00 | parallel build on fakes; first frontend↔backend integration from ≈ 20:30; sync/merge at 20:30 and 23:00. Real adapter built 19:00–23:00 from spike results | **G2 23:00 — fake-backed vertical slice:** UI create → analyze (fake LLM + fake memory with candidates) → resolve → outbox → `synced` → Reflect with validation → Memory Trace; `make test` green; T5-injection/T9/T10 pass on fakes |
| Fri 23:00–Sat 07:00 | rest; optional unattended: prompt tuning vs fixtures (Claude-I), eval harness vs fakes (Claude-T) | — |
| Sat 07:00–08:30 | merge queue, rebase | — |
| Sat 08:30–10:30 | **Integration 1:** `MEMORY_BACKEND=hindsight` (LLM still fake): seed demo/eval bank, `verify-seed` | **G3 10:30 — real Hindsight gate:** A1 passes; L-register filled; `hindsight-integration.md` §10/§11 real; Task 2 closable |
| Sat 10:30–12:00 | **Integration 2:** `LLM_BACKEND=groq` | **G4 12:00:** INC-009 analysed on the real stack; resolve→`synced`; Reflect returns a validated result |
| Sat 12:00–14:00 | tuning against T1–T10; first full `make eval` at ≈ 13:00; P1 allowed *only* if G4 was on time | — |
| **Sat 14:00** | **FEATURE FREEZE** (§9) | no new features/prompts-for-new-behaviour; fixes only |
| Sat 14:00–16:30 | tuning/fixes, final `make eval` + `make ab` on frozen prompts (≈ 15:30–16:15), README, golden demo DB + spare bank prepared | **G5 16:30 — CODE FREEZE:** tag `v1.0-demo`; `docs/eval-results.md` generated; A9 fresh-clone test started |
| Sat 16:30–17:15 | demo-integrity checklist (H1); rehearse twice (H5 operator) | **G5b** |
| Sat 17:15–19:30 | record (≥1080p, 2–5 min) → edit → upload **public** → verify logged-out | **G6a 19:30:** video link works |
| Sat 12:00–20:30 | articles drafted from ≈ 12:00 (numbers inserted after G5); publish after G6a; Reddit + LinkedIn (video/repo links) | H3 compliance scan clean |
| Sat 20:30 | **content/submission freeze** | **G6** all six confirm in writing at 21:00 |
| **Sat 21:30** | **target: submit the form** (H6) | submission receipt screenshot saved |
| Sat 22:30 | internal hard stop — drop anything unfinished except the form | ≥ 90 min buffer to 23:59 |

**Earliest end-to-end integration:** frontend↔backend on fakes ≈ Fri 20:30 (first merged PRs after G1); **fake-backed full slice G2 Fri 23:00**; first *real-Hindsight* end-to-end is possible Fri ≈ 23:00 only if H2 + H1 stay for a late shift (optional) — **planned Sat 08:30–10:30 (G3)**; full real stack G4 Sat 12:00.
**What the spike blocks:** only the final real adapter (`hindsight_adapter.py`) and the closure of Task 2. It does **not** block contract freeze, WS-B, WS-I, WS-F, WS-T or fakes. Spike answers that differ from the documented behaviour trigger a contract-correction PR (hindsight-facing parts only).
**Slip rules:** G2 slips > 2 h → cut all P1. G3 slips past 12:30 → switch the demo to local-Docker Hindsight (needs its own LLM key via `HINDSIGHT_API_LLM_PROVIDER`) or keep Cloud with a recorded run — decision by H1. Never cut: Retain (outbox), Recall, Reflect (with validation), memory-ON/OFF, T1–T10 harness, the submission buffer.

## 7. Dependency-aware integration sequence
| Step | Depends on | Unblocks |
|---|---|---|
| 1 contracts + skeleton + fakes (G1) | decisions D1–D8 | everything below |
| 2 backend on fakes; agent on fake LLM; frontend on generated types; dataset | 1 | G2 |
| 3 spike results (S) | Cloud key + SDK installed (independent of 1) | 4 |
| 4 real adapter | 1 (Protocol), 3 | G3 |
| 5 seed + `verify-seed` on real bank | 4, dataset | G3 |
| 6 Groq on (`LLM_BACKEND=groq`) | 2, `groq_smoke` | G4 |
| 7 evals + A/B | 5, 6 | tuning |
| 8 tuning, freeze, rehearsal, video, content, submit | 7 | G5–G6 |

## 8. Assumption register (unresolved items, by how they are resolved)
**Official documentation verification** — DV1 Cloud model not configurable (docs silent) · DV2 Cloud permits bank deletion (docs silent; design does not depend on it) · DV3 installed `hindsight-client` signatures = §3 (run `inspect_sdk.py`; docs/`main` and tag v1.2.0 differed in what a partial read showed) · DV4 Groq fallback model availability and JSON-schema support (`groq_smoke.py`) · DV5 error-body structure for Hindsight errors (docs silent → L11).
**Live experiment (Hindsight, hindsight-integration §10)** — L1…L14, all **NOT RUN**.
**Live experiment (other)** — LX1 Groq p95 latency and rate limits for 2 calls/analysis · LX2 analysis p95 ≤ ~25 s on demo data (requirements NFR) · LX3 retain→recall time (A7) · LX4 Reflect latency and quality (T8).
**Organiser clarification** — Q1 meaning of "use Band AI Desktop" (**OPEN; make no claim about it**) · Q2 article length (interim 1,200–1,500) · Q3 live demo format · Q5 whether the `MEMHACK99` credit applies to Hindsight Cloud billing (billing docs don't mention promos; check dashboard).
**Team decisions needing human approval** — D1 add optional `cause_key` and step/recommendation `category` (deterministic verification of cross-incident claims) · D2 seed/reset as guarded CLI + fresh versioned demo bank, no HTTP delete/reset · D3 Reflect manual refresh with stored last-success + staleness (instead of auto-refresh) · D4 resolve always returns `retain_status="pending"`; outbox as the only retain path · D5 IST timeline, working windows and the owner allocation in §5 · D6 Groq fallback model (qwen/qwen3-32b not listed) · D7 add eval probe fixtures INC-P1/INC-P5 (does not alter INC-001…009/C1/C2) · D8 sync SQLAlchemy + `asyncio.to_thread`.
**Planning assumptions** — team availability windows (§6) · Hindsight Cloud credits sufficient (seed ≈ 8 narratives; evals ≈ 5×10 runs; reflect $0.05/call) · one uvicorn worker.

## 9. Features frozen to protect the deadline
**Feature freeze Sat 14:00:** no new endpoints, screens, schema changes or new agent behaviours; only bug fixes, prompt/threshold tuning *with H1 approval for any test change*, docs. P1 items not finished by then are dropped (correction UI, feedback retention, live-learning, Docker single-container, Playwright). P2 never starts before G5 and only if everything else is green.
**Code freeze Sat 16:30:** tag `v1.0-demo`; after this only fixes for demo-blocking defects, each approved by H1 and re-running the affected T-tests. **Cut order if behind (earliest first):** P2 → P1 → UI polish → A/B visual side-by-side (keep script + table) → fewer eval repeats (N=3, reported as such). Never cut: Retain via outbox, Recall, Reflect + validation, ON/OFF comparison, T1–T10 harness, the 90-minute submission buffer.

## 10. Highest-risk technical decisions
| Risk | Impact | Mitigation |
|---|---|---|
| Hindsight behaviour differs from documentation/SDK reading | High | Spike first; adapter seam; fakes; contract-correction PR path; Task 2 not closed until L-register real |
| Recall hits lack `document_id`/attribution; observations span incidents | Med | provenance ladder, dedup + consolidation, unattributed hits never reach the LLM; narratives start with the incident ID |
| Retain latency / not immediately recallable | High for live demo | measure (L3, L5, A7); outbox keeps resolve instant; pre-seed; never depend on live retain in the video without rehearsal |
| Reflect generic or slow | High (Innovation + Memory = 55%) | seed data with a real cross-incident insight; fixed question; app-side grounding; manual refresh with stored last success; T8 measured honestly |
| Groq rate limits / invalid JSON / fallback model missing | Med | strict JSON-schema on primary, repair retry, fallback chosen by smoke test, N small |
| Band AI Desktop "use" unclear | Med (compliance) | Q1 sent Fri 17:00; no claim made until answered |
| Merge chaos | High | worktrees, CODEOWNERS, contracts, fakes, sync points |
| Over-claiming improvement | Med (credibility) | only measured numbers, with N and the controlled-synthetic wording |
| Time | High | §6 gates, slip rules, §9 cut order, protected 90-min buffer |

**Fit to the official criteria (Innovation 30 · Hindsight 25 · Technical 20 · UX 15 · Impact 10):** incident-memory that remembers *failed fixes* and separates confirmed from suspected (Innovation, Impact); Retain→Recall→Reflect all visible in the Memory Trace with measured latency (Hindsight); outbox + provenance + grounding validation + fakes + T1–T10 (Technical); evidence labels, ON/OFF side-by-side and honest degraded states (UX). Features that do not serve one of these are cut first.

## 11. Consistency checklist (H1 runs before G5 and before submission)
Same ten T-IDs everywhere (demo-plan §5 only) · status vocabularies: adapter `ok|error`, outbox `pending|in_progress|succeeded|failed`, API `retain_status` `pending|synced|failed|not_applicable` · 13 endpoints, no `/demo/*` · Hindsight/Groq separation · versions = `docs/versions.md` · no "hackathon" · no claim about Band AI · every number traceable to `docs/eval-results.md`.
