# requirements.md — Service Reliability Memory Agent (SRMA)  (v1.2 — consistency pass after Hindsight docs/SDK check)

Tags: **[OFFICIAL]** competition PDFs/brief · **[PRODUCT]** · **[ENG]** engineering constraint · **[DECISION]** our decision · **[REC]** recommendation. Deadline timezone is **IST** throughout.

## 1. Official requirements [OFFICIAL]
| ID | Requirement |
|---|---|
| O1 | Build with Hindsight (Cloud or OSS); memory central and visibly demonstrated. |
| O2 | Download and use Band AI Desktop. **Meaning of "use" is unclear — recorded as organiser question Q1; no interpretation is assumed.** |
| O3 | Any LLM; Groq recommended (`openai/gpt-oss-120b`, `qwen/qwen3-32b`); "be ready to handle function-calling errors". **`qwen/qwen3-32b` is not on Groq's current models page (checked 2026-11-06); fallback model chosen by `spike/groq_smoke.py` (decision D6, implementation-plan §8).** |
| O4 | Deliverables: GitHub repo (clean, documented), demo video, live demo to judges, explanation of Hindsight usage, content deliverables. |
| O5 | One submission per team; all six agree; **deadline Nov 7 2026, 11:59 PM IST**. Form: https://forms.gle/7eSw5Dz2oT2MhymX7 |
| O6 | Judging: Innovation 30 · Hindsight Memory 25 · Technical Implementation 20 · User Experience 15 · Real-world Impact 10. |
| O7 | Avoid student-centric projects; realistic data (real-sounding error logs). Promo `MEMHACK99` = $50 Cloud credit (add in Billing after registering). **Whether it applies to Hindsight Cloud billing is unconfirmed (Q5).** |
| O8 | Video: 1 per team, 2–5 min, ≥1080p, screen recording + voiceover, **public YouTube**, 16:9 thumbnail. |
| O9 | Per member: 1 article (public Medium/Dev.to/Hashnode/Substack/LinkedIn Article), Reddit **link** post (r/llmdevs, r/sideproject, r/aiagents, r/aimemory), 1 LinkedIn post. |
| O10 | Article content: engineering story, problem, Hindsight integration, real code snippet, before/after example, honest lesson/limitation, screenshots, the three required links (Hindsight GitHub, Hindsight docs, vectorize.io/what-is-agent-memory). |
| O11 | LinkedIn post: <800 chars; project GitHub link in main post; 3–5 hashtags on the last line; article URL as **first comment**; Hindsight GitHub link as a separate comment. |
| O12 | **The word "hackathon" must not appear in any article or post (title, body, hashtags).** No student-related tags. |
| O13 | Tag Code.in on LinkedIn and articles. |

### Organiser clarifications register
| # | Question | Owner | Status | Interim rule |
|---|---|---|---|---|
| Q1 | What counts as "using Band AI Desktop"? | H1 | **OPEN** | Install now; make no claim about its use in README/video/articles until answered. |
| Q2 | Article length: 800–1,500 vs 1,200–2,000 words | H1 | **OPEN** | Write 1,200–1,500 (satisfies both). |
| Q3 | Live demo format (in person / video call; needs hosted URL?) | H1 | **OPEN** | Support local laptop run + optional hosted container (P1). |
| Q4 | Guide prompt numbering/count inconsistencies (title ideas 20 vs 5; "6 prompts") | — | Ignore | No effect on deliverables. |
| Q5 | Does the `MEMHACK99` credit apply to Hindsight Cloud billing? (billing docs do not mention promos) | H2 | **OPEN** | Check the Cloud dashboard balance after applying; budget assumes credits suffice (seed ≈ 8 narratives; evals ≈ 5×10 runs; reflect $0.05/call). |

## 2. Product scope [PRODUCT]
**Value proposition:** an agent that accumulates operational knowledge from engineer-confirmed incidents and uses it to make the next investigation better-informed — while never presenting a suspected cause as confirmed. Not a chatbot, dashboard, log viewer, generic tracker, plain RAG, or LLM wrapper. **Target users:** software engineers, SREs, DevOps, engineering ops. **Core principle:** Hindsight finds candidates; SQLite verifies them.

### Functional requirements (all P0 unless stated)
| ID | Requirement |
|---|---|
| F1 | Incident intake with validation (title, description, service, severity, error messages, evidence, metadata). |
| F2 | Analysis: extract symptoms/entities/error signatures, list missing information, propose investigation steps. |
| F3 | Recall from Hindsight during analysis; retrieved memories visible (Memory Trace). |
| F4 | Related-incident comparison: relevance, why relevant, matching features, **differences**, past root cause (from DB, with status), past attempts incl. failed, past resolution. |
| F5 | Evidence labels `OBSERVED/HISTORICAL/INFERRED/TO_VERIFY` on every finding/step; suspected causes never shown as confirmed; app-computed `previously_failed_refs` on recommended steps. |
| F6 | Resolve with root cause (+status, optional `cause_key`), resolution, outcome, categorised investigation steps, lessons → persisted in SQLite **and** enqueued for retention (outbox). A Hindsight outage never blocks resolving. |
| F7 | Reflect: on-demand pattern synthesis via Hindsight Reflect with **grounding validation** (arch §6); last successful reflection preserved with timestamp and staleness; never auto-blocks resolve. |
| F8 | Memory-ON vs memory-OFF comparison using the identical pipeline (recall step is the only difference). |
| F9 | Dashboard: incident list/detail, related incidents, recommendations, patterns, Memory Trace (retain/recall/reflect events, outbox status). |
| F10 | Synthetic seed dataset loaded by CLI (idempotent). |
| F11 | Degradation: Hindsight/LLM failures, empty recall, malformed input handled visibly. |
| **F14** | **Evaluation infrastructure and all ten scripted evaluations T1–T10 (canonical definitions in demo-plan.md §5) are P0.** `make eval` runs them N=5 times each and prints measured results. |
| F12 (P1) | Correction flow UI (schema/outbox support is P0). |
| F13 (P1) | Engineer feedback on recommendations retained as experience. |

### Non-functional requirements
Advisory only (no production actions; every recommendation says verify first) · never fabricate incidents: every cited ID exists in SQLite · evidence provenance (incident ID + snippet) · secrets only in env vars, none in frontend/Git · synthetic data only · Reflect/Markdown output rendered safely (no raw HTML) · analysis target ≤ ~25 s p95 on demo data [REC, to be measured].

## 3. Engineering constraints [ENG]
No Kubernetes, microservices, multi-agent, RBAC/auth, real monitoring integrations, message broker. Modular monolith, one repo, one stack (implementation-plan §1).

## 4. Acceptance criteria — complementary to T1–T10
T-tests (demo-plan §5) measure **agent/memory behaviour**; A-criteria below are **product go/no-go gates** and cite the T-tests they depend on. A "pass" for a T-test is ≥4 of 5 runs on the final eval run; any T-test below that is reported as measured and listed under Known Limitations — never edited to pass.
| ID | Criterion | Evidence |
|---|---|---|
| A1 | Seed loads: 8 incidents in SQLite; all outbox rows `succeeded`; `make verify-seed` recalls ≥1 hit per seeded incident. | seed verify script |
| A2 | Recall quality on different wording and controls. | T1, T2 |
| A3 | Uncertainty handling: misleading similarity, suspected vs confirmed, missing metadata. | T4, T5, T7 |
| A4 | Failed-fix avoidance is measured, memory-OFF baseline recorded. | T3 + `eval/ab_compare.py` |
| A5 | Unrelated and empty-memory incidents never invent history. | T6, T9 |
| A6 | Reflect surfaces the cross-incident pattern and passes grounding validation. | T8 |
| A7 | Live loop: resolve → outbox `succeeded` → recall for a follow-up incident includes it; latency logged. | integration test `test_retain_recall_loop` (live marker) |
| A8 | Degradation + consistency: Hindsight down never blocks analyze/resolve; outbox recovers; API state = DB state. | T10 |
| A9 | Clean checkout → running demo in <10 min via README. | fresh-clone test |
| A10 | Demo integrity: video/live demo shows measured results only, labelled "controlled synthetic evaluation", not evidence of real-world operational improvement. | demo-plan §3 checklist |

Unit/contract suites (`make test`, not part of T1–T10): validation/422 envelope, malformed input, fabrication guard, outbox state machine incl. crash/lease/duplicate, adapter failure injection, Reflect grounding rules, Markdown safety.

## 5. Out of scope
Kubernetes, real log/APM ingestion, PagerDuty/Slack/Jira, auto-remediation, auth/RBAC, multi-tenant, multi-agent, fine-tuning, our own vector DB, real production data, mobile UI, i18n, message brokers, HTTP endpoints that delete banks or wipe data.
