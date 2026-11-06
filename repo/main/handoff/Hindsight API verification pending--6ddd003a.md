# Hindsight API verification pending

## Human



[attachment: Denovate_guide.pdf]

[attachment: Denovate_PS.pdf]

## Assistant

_[Claude used memory_write]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

**Claude shared: requirements.md, architecture.md, data-model.md, api-contracts.md, hindsight-integration.md, implementation-plan.md, demo-plan.md**

_[Artifact: requirements, architecture, data-model, api-contracts, hindsight-integration, implementation-plan, demo-plan]_

I've drafted all seven documents, but **Task 2 (verify the Hindsight API against the official docs) is not done.** I have no web access in this chat, so every Hindsight method name, parameter and response shape in `hindsight-integration.md` comes from my recollection. The file says so at the top. It contains a 10-question Day-0 spike (S1–S10) for the Hindsight owner to answer by reading the docs and running about 30 lines of real code. Nothing should depend on those calls until it's done. I put all Hindsight calls behind one adapter module so wrong assumptions cost hours, not days.

## 1. Understanding
We are building an incident-memory agent, not a chatbot. It remembers engineer-confirmed incidents (including failed fixes), recalls them with an explanation of why they're relevant and how they differ, and uses Reflect to surface patterns across incidents. Every claim is labelled OBSERVED, HISTORICAL, INFERRED or TO_VERIFY, and everything is advisory.

## 2. Hard constraints
- **Deadline:** Nov 7, 11:59 PM, one submission, all six members agree.
- **Required tools:** Hindsight and Band AI Desktop. What "use Band AI Desktop" means is unclear, so ask the organisers.
- **Content rules:** the word "hackathon" must not appear anywhere in any article or post, including hashtags. The video must be public on YouTube.
- **Article length conflict:** the guide says 800–1,500 words in one place and 1,200–2,000 in another. Aim for 1,200–1,500 to satisfy both.
- **Scope:** synthetic data only, no real integrations, no auth, no multi-agent, no Kubernetes.

## 3. Architecture
A FastAPI modular monolith with SQLite, a React SPA, Hindsight, and Groq. The core principle is that **Hindsight finds candidates and the app DB verifies them.** The DB holds incident status, confirmed vs suspected root cause, and outcomes. The agent may only cite incident IDs that exist in the DB. Diagrams are in `architecture.md`.

## 4. Stack
| Layer | Choice |
|---|---|
| Backend | Python and FastAPI |
| App DB | SQLite |
| Frontend | React, Vite, TypeScript |
| LLM | `openai/gpt-oss-120b` on Groq, `qwen/qwen3-32b` as fallback, with no tool calling |
| Memory | Hindsight Cloud, with local Docker as fallback |
| Agent framework | None |

I rejected Next.js, Postgres and LangChain because they add setup or integration time for no demo value.

## 5. Hindsight strategy
- **Retain:** only when an engineer resolves an incident, one narrative per incident. We never retain open-incident hypotheses or agent output.
- **Recall:** three queries per analysis (symptom narrative, error signature, failed fixes), then enrich each hit from the DB.
- **Reflect:** one fixed pattern question, auto-refreshed after each resolve.
- **Memory-off comparison:** it is the same pipeline with recall skipped, so the memory-on vs memory-off comparison is controlled.

## 6. MVP scope
- **P0:** intake, analysis, recall, related-incident comparison, evidence labels, resolve-and-retain, Reflect, memory on/off side-by-side, dashboard with a Memory Trace panel, seed data, graceful degradation, and 10 scripted evals.
- **P1:** correction flow, feedback retention, a live-learning incident, single-container deploy.
- **P2:** UI extras like dark mode and report export.

## 7. Workstreams
There are six workstreams and five Claude resources. A human owns Architecture/Integration with me. The five Claudes take Backend, Hindsight, Agent, Frontend and Testing/Data/Deploy. The file-ownership map is in `implementation-plan.md`. Fakes (`MEMORY_BACKEND=fake`, `LLM_BACKEND=fake`) let everyone build in parallel from about hour 3.

## 8. Highest risks
1. The unverified Hindsight API.
2. Retain latency and how soon a retained memory becomes recallable. This matters for any live retain in the demo.
3. Reflect output being generic. I designed the dataset to contain a real cross-incident insight to counter this.
4. Recall hits possibly lacking source incident IDs. Mitigation: every narrative starts with its ID.
5. Groq rate limits and invalid JSON.
6. The Band AI ambiguity.
7. Merge chaos.

## 9. Immediate sequence
1. Run the Hindsight spike and install Band AI.
2. Create the repo skeleton with fakes and freeze the contracts by about hour 2.
3. Build in parallel against fakes.
4. Integrate real Hindsight and Groq by about hour 12.
5. Seed the data and tune against the evals.
6. Freeze features, then code freeze on Nov 7 around 16:00.
7. Record the video, then write articles and posts in parallel.
8. Submit by about 22:30, which leaves buffer before the 23:59 deadline.

## Decisions for you
- **Hindsight Cloud over local Docker:** I recommend Cloud so all six people and the Claudes share one bank. Say if you'd rather go local.
- **Clock times:** my timeline uses "H+" hours because I don't know your exact kickoff time. Tell me and I'll convert it to clock times.
- **Eval numbers:** the memory-off baseline in the demo plan must be measured in rehearsal. If it doesn't recommend the failed fix, we report that honestly instead of staging it.

Next, I'd have the Hindsight owner start the spike now and send me the filled-in table. I'll then correct `hindsight-integration.md` and `api-contracts.md` before the freeze.

_[Claude used suggest_web_search_enable]_

## Human

I've turned on web search. Please retry now.

## Assistant

_[Claude used web_search]_

## Human



## Assistant

Before I touch any files, here is my review of the seven documents against both audit prompts.

## 1. Inconsistencies and risks found

**Contradictions between documents**
1. **Evaluation scope:** F14 says the eval harness is P1 with "6 checks". `demo-plan.md` defines T1–T10 and `implementation-plan.md` says "6 scripted evals". The T1–T10 list also misses three categories you require: missing metadata, empty memory, and a partial control. It spends tests on malformed input and fabrication, which belong in unit tests.
2. **Retain states:** the API returns `pending|synced`, the adapter returns `synced|failed`, and the DB has `retain_status`. Nothing says who owns each transition, so the API and DB can contradict each other.
3. **Hindsight and Groq:** the architecture diagram draws Hindsight using Groq. That was an assumption.
4. **Destructive reset:** `POST /api/demo/reset` wipes "the dev bank" while the plan uses shared Cloud banks. This is unsafe.
5. **Reflect refresh:** "auto-refresh after each resolve" conflicts with non-blocking resolve and unknown Reflect latency.
6. **Stack and versions:** the documents are mostly consistent, but there is no version-pinning rule and no stated Groq structured-output assumption.
7. **Timeline:** it assumes a fresh 36 hours with "H+" offsets, and no named owners for video, content or submission.

**Design gaps**
- Recall provenance assumes one hit maps to one incident. Hits can duplicate, span several incidents, or carry no ID.
- Validating that incident IDs in Reflect output exist is not enough. A valid ID can still carry a false claim.
- Reflect Markdown is untrusted input.
- Correction semantics are undefined, although the schema already has superseded root causes.

## 2. Proposed document changes (targeted, no redesign)
- **requirements.md:** make F14 P0 (all ten T-tests), rewrite A1–A10 to reference T-tests, and add the organiser-clarification register.
- **architecture.md:**
  - Fix the Hindsight/Groq diagram.
  - Add the outbox lifecycle, Reflect grounding, recall consolidation and bank-safety rules.
  - Add the version-pinning rule.
- **data-model.md:**
  - Add `retain_outbox`, `reflections`, `app_meta`.
  - Add `cause_key` on root causes, `category` on investigation steps, and `revision`.
- **api-contracts.md:**
  - Make the adapter interface match the SDK.
  - Add the outbox-derived `retain_status`, `GET /api/reflection` and the new `ReflectResult` shape.
  - Remove `/api/demo/seed` and `/api/demo/reset` from HTTP and move them to guarded CLI commands.
- **hindsight-integration.md:** replace "unverified" assumptions with three evidence tiers: documented, SDK-inspected, and live-verified. Live-verified stays **NOT RUN** until the smoke script is executed.
- **implementation-plan.md:** IST clock timeline, named owners, allocation of six humans and five Claudes, and the assumptions register.
- **demo-plan.md:** the canonical T1–T10, memory-on/off measured protocol, and a controlled-synthetic-evaluation disclaimer.

## 3. Hindsight details I need to verify
- **Verifiable now (docs and SDK source):**
  - Method signatures and return models.
  - Whether `document_id` and source IDs appear in recall hits.
  - Whether Cloud uses a managed model.
  - Bank creation and deletion capabilities.
- **Needs a live Cloud run only:**
  - Latency.
  - Immediate recallability.
  - Duplicate `document_id` and `update_mode` behaviour.
  - Score semantics.
  - Result quality.

I can't reach Hindsight Cloud from this sandbox, so I'll write the smoke script for your Hindsight owner instead.

## 4. Decisions needing human approval
1. Add optional `cause_key` and `category` fields so cross-incident claims can be checked deterministically against the DB.
2. Move seed and reset to CLI-only, with a fresh versioned demo bank instead of destructive reset.
3. Make Reflect manual-refresh with a staleness indicator instead of auto-refresh.
4. The IST timeline and named owners.

I'll start with the Hindsight research.

_[Claude used bash_tool]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

_[Claude used web_search]_

_[Claude used web_fetch]_

_[Claude used web_fetch]_

_[Claude used web_fetch]_

_[Claude used web_search]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

_[Claude used bash_tool]_

**Claude shared: hindsight_smoke.py**

_[Artifact: hindsight smoke]_
