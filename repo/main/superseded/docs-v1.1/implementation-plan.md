# implementation-plan.md

## 1. Stack (decision record)
| Layer | Choice | Why / rejected alternative |
|---|---|---|
| Backend | Python 3.11 + FastAPI + Pydantic v2 | Hindsight's primary SDK is Python 🔶; contract = Pydantic. *Rejected:* Node backend (second SDK risk). |
| App DB | SQLite + SQLAlchemy 2 | zero ops, file seed, portable demo. *Rejected:* Postgres (setup time, no benefit at 20 rows). |
| Frontend | React 18 + Vite + TypeScript + Tailwind, `react-markdown` | fast, static build served by FastAPI. *Rejected:* Next.js (SSR/routing overhead). |
| LLM | Groq `openai/gpt-oss-120b`, fallback `qwen/qwen3-32b`, via OpenAI-compatible client, JSON output + Pydantic validation + 1 repair retry | no tool calling needed (O3). |
| Memory | Hindsight Cloud (fallback local Docker) | see hindsight-integration §2. |
| Tests | pytest, pytest-asyncio, respx/fakes; Playwright smoke (P1) | |
| Agent framework | none | |

## 2. Repository layout and ownership (CODEOWNERS enforces)
```
/docs                      WS-A
/backend/app/contracts.py  WS-A (frozen; change by PR only)
/backend/app/main.py, api/, services/, db/, config.py    WS-B
/backend/app/memory/       WS-H   (hindsight_adapter.py, fake_memory.py, templates.py)
/backend/app/agent/        WS-I   (pipeline.py, prompts.py, llm.py, fake_llm.py, validators.py)
/frontend/                 WS-F
/data/seed_incidents.json, /data/fixtures/, /eval/, /tests/, Dockerfile, docker-compose.yml, Makefile, .github/   WS-T
```
Rules: branches `ws/<name>`; small PRs into `main`; **no direct pushes to main**; every PR reviewed by Integration Lead (WS-A human) + owner of touched module; no edits outside owned paths without asking the owner; contract change = PR touching both `contracts.py` and `api-contracts.md`, announced in the team chat; rebase on main at least every 3 hours; `main` must always run with `MEMORY_BACKEND=fake LLM_BACKEND=fake`.

## 3. Scope classification
| Pri | Items |
|---|---|
| **P0** | F1–F11 (intake, analysis, recall, comparison, evidence labels, resolve+retain, reflect, A/B, dashboard, seed, degradation); memory trace panel; 6 scripted evals; README; demo video; content deliverables |
| **P1** | Correction/supersede flow (F12); feedback retain (F13); incident #10 live-learning scenario; Docker single-container deploy; Playwright smoke; eval metrics table in README; cached fallback outputs |
| **P2** | Per-service pattern filter in UI; export report to markdown; dark mode; confidence charts |
| **Out** | see requirements §5 |

## 4. Work packages
### WS-A Architecture / Integration (human lead + this chat)
- **Objective:** keep one architecture; freeze contracts; integrate.
- **Owns:** `/docs`, `contracts.py`, repo skeleton, CODEOWNERS, branch protection.
- **Inputs:** this doc set. **Outputs:** repo skeleton with fake backends running by **H+3**, contract freeze **H+2**, daily integration builds.
- **Acceptance:** `main` boots with fakes; OpenAPI exports; TS types generated; every PR reviewed < 1 h.
- **Tests:** CI job (pytest + frontend typecheck + build) green.

### WS-B Backend (Claude-1)
- **Objective:** API, services, persistence, orchestration.
- **Owns:** `main.py, api/, services/, db/, config.py`. **Depends on:** contracts, `MemoryService`/`AgentService` protocols (fakes available).
- **Deliver (H+3):** all 13 endpoints against fakes with SQLite; seed loader; error envelope; `memory_events` logging; validation; retain_status/outbox retry task; CORS; static SPA serving.
- **Acceptance:** contract tests pass for all endpoints incl. 422/404/409; resolve works when memory backend raises (retain_status=pending); analyze works when recall unavailable (banner state); hits enriched from DB; output validator strips unknown IDs.
- **Tests:** pytest API tests with fakes; failure-injection tests.

### WS-H Hindsight (Claude-2)
- **Objective:** verified, working Retain/Recall/Reflect behind `MemoryService`.
- **Owns:** `memory/`. **Depends on:** spike (first 2 h), API key + bank.
- **Deliver:** (H+2) `hindsight-spike-results.md`; (H+5) `FakeMemoryService` loading fixtures (keyword-overlap so tests are meaningful); (H+8) real adapter: retain template, 3-query recall, reflect with fixed question, timeouts/retries, normalisation, INC-ID regex fallback; (H+10) seed script retains all 8 incidents into `srma-demo` and verifies recall.
- **Acceptance:** with seeded bank, recall for INC-009 text returns ≥2 of {INC-001, 002, 007} in top results; reflect output mentions ≥3 incidents; adapter never raises to callers; each call logged with latency.
- **Tests:** adapter unit tests with mocked SDK (timeouts, 401, 429, empty, malformed); 1 live integration test marked `@live`.

### WS-I Agent Intelligence (Claude-3)
- **Objective:** extraction + memory-grounded analysis, evidence labelling, uncertainty.
- **Owns:** `agent/`. **Depends on:** contracts; fixtures of EnrichedHits (from WS-H/T) to work before Hindsight is live.
- **Deliver:** (H+4) `extract` + `analyse` prompts with JSON-schema output, repair retry, fallback model, fake LLM returning canned reports; (H+9) tuned prompts passing evals T2–T5; validators (label required, `suspected` never shown as confirmed, cited IDs ⊆ provided hits, no HISTORICAL when memory not ok).
- **Prompt rules (must exist):** similar symptoms ≠ same cause; list differences; rate relevance; flag missing info; never recommend an action previously rated ineffective without explaining the difference; prefer read-only checks; no production changes; later correction supersedes earlier note.
- **Acceptance:** evals T2–T5 in `demo-plan §5` pass ≥4/5 runs each; invalid JSON recovered or clean `LLM_UNAVAILABLE`.
- **Tests:** schema tests; golden-fixture tests with fake LLM; live eval script.

### WS-F Frontend (Claude-4)
- **Objective:** clear, demo-friendly UI.
- **Owns:** `frontend/`. **Depends on:** generated types; backend with fakes (H+3).
- **Screens (P0):** (1) Incident list + "New incident" form; (2) Incident detail: summary, **Analyze** with toggle / **Compare memory ON vs OFF** side-by-side; (3) Related incidents cards (relevance badge, why, matches, differences, past attempts with ineffective ones marked, past resolution, root-cause status chip); (4) Recommendations list with label chips and "advisory" banner; (5) **Memory Trace** drawer (retain/recall/reflect events + latency + retrieved snippets); (6) **Patterns** page (Reflect, linkified IDs, "Refresh"); (7) Resolve form (root cause + status, resolution + outcome, failed steps, lessons) with retain status chip; (8) banners for memory unavailable/empty states and loading/error states.
- **Acceptance:** whole demo script runs by mouse only; no uncaught errors; every state in api-contracts rendered (empty/unavailable/disabled); readable at 1080p recording.
- **Tests:** typecheck/build in CI; 1 Playwright smoke (P1).

### WS-T Testing / Deployment / Data (Claude-5)
- **Objective:** dataset, evals, CI, run-anywhere packaging.
- **Owns:** `data/, eval/, tests/, Dockerfile, docker-compose.yml, Makefile, .github/`.
- **Deliver:** (H+4) `seed_incidents.json` with the 8 incidents + INC-009 + control incidents exactly per demo-plan §2 (internally consistent dates/versions/errors); (H+6) CI; (H+10) `make eval` running T1–T8 with N=5 repeats and printing a metrics table; (H+14) Dockerfile single container; README quickstart; secret scan.
- **Acceptance:** clean checkout → `make seed && make dev` in <10 min; `make eval` prints table; no secrets in history.
- **Tests:** the eval harness itself; data consistency checker (IDs, dates, services referenced exist).

### All members — Content (after code freeze, owned by humans)
Each member: article (1,200–1,500 words, run guide Prompts 1–2 inside repo, no "hackathon"), Reddit link post, LinkedIn post (<800 chars, repo link, 3–5 hashtags, article as first comment, Hindsight link as second comment; tag Code.in). One owner for video + thumbnail.

## 5. Timeline (T = kickoff of build; re-anchor with real clock)
| Window | Milestone | Gate |
|---|---|---|
| H+0–2 | Repo, skeleton, Hindsight/Groq keys, Band AI installed; **Hindsight spike**; contract freeze | G1: spike table filled; contracts frozen |
| H+2–8 | Parallel build against fakes; WS-H real adapter in parallel | G2: end-to-end vertical slice on fakes (UI→API→DB→fake agent) |
| H+8–12 | **Integration 1:** real Hindsight + real LLM, seeded bank | G3: INC-009 analyzed on real stack |
| H+12–20 | Prompt tuning vs evals, Reflect, A/B view, resolve→retain loop, trace panel, error states | G4: all P0 acceptance A1–A9 |
| H+20–26 | Hardening, eval table, README, cached fallbacks, P1 if green | **Feature freeze** |
| Nov 7 by ~16:00 | **Code freeze**; tag `v1.0-demo`; rehearse live demo twice | G5 |
| Nov 7 16:00–20:00 | Record video (1080p), thumbnail, upload public YouTube; members write/publish articles & posts in parallel | |
| Nov 7 by 22:30 | **Submit form** (target); 23:59 is the hard deadline, not the plan | G6: all six agree |

If G2 slips by >2 h → cut P1 entirely. If G3 slips → run demo on local Docker Hindsight, or keep Cloud and freeze cached outputs. Never cut: Retain, Recall, Reflect, A/B.

## 6. Integration sequence
1) skeleton+fakes → 2) backend contract tests → 3) frontend on backend fakes → 4) swap `MEMORY_BACKEND=hindsight` → 5) swap `LLM_BACKEND=groq` → 6) seed → 7) evals → 8) tune.

## 7. Highest-risk technical decisions
| Risk | Impact | Mitigation |
|---|---|---|
| Hindsight API differs from assumptions (this doc was drafted unverified) | High | Spike first; adapter seam; fakes |
| Recall hits lack source incident ID | Med | ID embedded in narrative + regex; DB join |
| Retain extraction latency / not immediately recallable | High for live demo | Measure in spike; pre-seed; show retain via trace; poll-until-recallable helper; don't depend on live retain in video without rehearsal |
| Reflect quality non-deterministic/generic | High (25%+30% criteria) | Fixed engineered question; seed data designed to have a real cross-incident insight; cache last good; evaluate N=5 |
| Groq rate limits / JSON failures | Med | repair retry, fallback model, canned fallback, cache |
| Band AI Desktop "use" unclear | Med (possible compliance) | ask organisers now; make an honest documented use |
| Merge chaos | High | CODEOWNERS, contracts, fakes, rebase cadence |
| Over-claiming improvement | Med (credibility) | only report eval numbers actually measured |
