# Denovate Hackathon — Team Requirements

> **Purpose:** This document consolidates the requirements and guidance provided in the official Denovate problem statement and content submission guide. It serves as a shared reference for the entire team.
>
> **Important:** Items marked **Required** are explicitly stated in the official documents. Items marked **Recommended** are guidance for building a stronger submission. No deadlines or additional rules have been invented.

---

## 1. Project Objective

Build an AI-powered application that uses **Hindsight** as its memory system.

The project should demonstrate that an AI agent can:

- Retain useful information from previous interactions.
- Recall relevant information when needed later.
- Use remembered information to make better decisions or take more appropriate actions.
- Improve its behaviour over repeated interactions instead of behaving like a stateless chatbot.

**Core requirement:** Hindsight memory must be clearly used in the solution and central to the value the project provides. It should not be an unrelated feature added to an otherwise ordinary chatbot.

---

## 2. Required Technology and Tools

### 2.1 Hindsight — REQUIRED

Every team must build its project using **Hindsight**.

The event allows either:

- Hindsight Cloud.
- The open-source version of Hindsight.

Official resources:

- Documentation: https://hindsight.vectorize.io/
- GitHub: https://github.com/vectorize-io/hindsight
- Hindsight Cloud: https://ui.hindsight.vectorize.io

**Cloud credits:**

The problem statement provides the promo code `MEMHACK99` for $50 in Hindsight Cloud credits.

The code must be applied in the billing section after registration.

### 2.2 Band AI Desktop — REQUIRED

Participants must download and use **Band AI Desktop**.

Website: https://www.band.ai

### 2.3 LLM — FLEXIBLE

The team may use any LLM.

The problem statement recommends Groq and lists the following models:

- `openai/gpt-oss-120b`
- `qwen/qwen3-32b`

Groq: https://groq.com/

The document specifically advises teams to make their agents resilient to function-calling errors when using the suggested models.

These models and Groq are recommendations, not mandatory choices.

### 2.4 Coding Tools — OPTIONAL

The team may code manually or use coding agents.

Examples provided in the problem statement:

- https://code.in/
- https://jules.google.com/
- https://opencode.ai/

These are optional tools, not required technologies.

---

## 3. Product and Problem Selection

The official problem statement encourages projects that solve genuine business or professional workflow problems.

### Recommended Project Characteristics

A strong project should:

1. Address a real, specific pain point.
2. Serve one clearly defined user persona.
3. Focus on one workflow and one clear value proposition.
4. Use memory as a necessary part of the solution.
5. Demonstrate meaningful improvement over repeated interactions.
6. Be technically achievable and demonstrable within the event.
7. Have a plausible path to real-world use or adoption.

### Suggested Opportunity Areas

The problem statement highlights areas such as:

- Sales and deal intelligence.
- Marketing and content workflows.
- Engineering and DevOps.
- Operations and customer support.
- Product feedback and strategy.
- Compliance and audit workflows.

These are example opportunity areas, not restrictions on the project topic.

### Scope Guidance

The official guidance favours a polished agent that performs one task well over a broad prototype that performs many tasks poorly.

Avoid choosing a project merely because it sounds impressive.

Identify a workflow where people repeatedly need an agent to remember:

- Context.
- Decisions.
- Preferences.
- History.
- Previous outcomes.

### Data Requirements

Use realistic data wherever possible.

The problem statement suggests:

- Using real datasets where suitable.
- Generating realistic synthetic data when real data is unavailable.

Synthetic examples should resemble plausible users, records, transactions, conversations, incidents, or other domain-specific information.

---

## 4. What the Project Must Demonstrate

The project must make the role of Hindsight understandable to someone evaluating it.

### 4.1 Retention

Show the agent receiving information that should be useful beyond the current interaction and retaining it through Hindsight.

### 4.2 Recall

In a later interaction, show the agent retrieving relevant information from previous interactions.

### 4.3 Application of Memory

Show how the recalled information changes the agent's:

- Response.
- Decision.
- Recommendation.
- Action.

### 4.4 Improvement Over Time

Show a progression across multiple interactions.

The official problem statement specifically recommends demonstrating a learning curve, where the agent's behaviour becomes increasingly useful and personalised after repeated interactions.

### 4.5 Before-and-After Comparison

Where possible, demonstrate:

- How the workflow behaves without relevant memory.
- How it behaves after the agent has retained and recalled useful context.

Do not merely display a memory record or explain that memory exists.

Show the practical effect of memory on the user's workflow.

---

## 5. Project Submission Requirements

The problem statement lists the following team-level deliverables.

| Deliverable | Requirement |
|---|---|
| GitHub Repository | Clean, documented project code |
| Demo Video | A video showing the agent in action |
| Live Project Demo | Demonstrate the working project to judges |
| Hindsight Explanation | Explain how Hindsight memory is used in the solution |
| Content Submissions | Complete the article, social post, and video requirements described in the official content guide |

The content guide clarifies that:

- Each team member submits an individual article.
- Each team member submits an individual social media post.
- The team submits one video.

See Section 6.

---

## 6. Content Submission Requirements

The official content guide describes a team content contest.

To be eligible, the team must have submissions from every member as well as one team video.

All content must be in **English**.

### 6.1 Article — ONE PER TEAM MEMBER

Each team member must publish their own technical article.

#### Publication Requirements

- Publish on a public, linkable platform.
- Suggested platforms include:
  - Medium.
  - Dev.to.
  - Hashnode.
  - Substack.
  - LinkedIn Articles.
- The article must be publicly accessible through a URL.
- Each member may cover a different technical aspect or describe their own contribution to the same project.

#### Content Requirements and Guidance

The article should:

- Explain a specific engineering story about the project.
- Describe the problem and what the system does.
- Explain how the system is structured and how Hindsight is integrated.
- Include at least one real code snippet from the project.
- Include at least one concrete before-and-after example.
- Include honest lessons, limitations, or dead ends.
- Include screenshots or images.
- Link to relevant Hindsight resources, including its GitHub repository and documentation.

#### IMPORTANT RESTRICTION

**Do not mention the hackathon in the article title or body.**

The guide says articles that mention the hackathon, including in the title or body, will be disqualified.

#### Word Count Inconsistency

The supplied content guide contains two different word-count instructions:

- Overview: **800–1,500 words**.
- Detailed article-generation prompt: **1,200–2,000 words**.

The guide is internally inconsistent on this point.

Confirm the expected word count with the organisers.

Until clarified, do not treat either range as a definitively reconciled rule.

#### Additional Distribution Step

The guide asks authors to submit their published article as a link post to one of these communities:

- r/llmdevs
- r/sideproject
- r/aiagents
- r/aimemory

Follow each community's rules before posting.

### 6.2 Social Media Post — ONE PER TEAM MEMBER

Each team member must publish an individual LinkedIn post promoting the project/article.

#### Requirements

- Keep the post under **800 characters**.
- Do not mention the hackathon anywhere in the post, including hashtags.
- Do not use hackathon-related or student-related hashtags.
- Include the project GitHub repository link in the main post.
- Use **3–5 relevant hashtags** on the last line.
- Add the article URL as the first comment.
- Add the Hindsight GitHub repository link in a separate comment.

#### Content Guidance

The guide recommends a technically credible post focused on concrete behaviour and outcomes.

It should explain:

- What the project does.
- What problem it solves.
- How memory changes the agent's behaviour.

Avoid generic promotional claims.

### 6.3 Video — ONE PER TEAM

The team must produce one project demo/walkthrough video.

#### Format Requirements

| Requirement | Specification |
|---|---|
| Length | 2–5 minutes |
| Resolution | 1080p minimum |
| Format | Screen recording with voiceover |
| Talking Head | Preferred, but not mandatory |
| Platform | Public YouTube video |

Record the screen directly. Do not record a monitor using a phone camera.

#### Suggested Video Structure

| Segment | Approximate Duration | What to Show |
|---|---:|---|
| Introduction | 30 seconds | Who you are, what you built, and why |
| Problem | 30 seconds | The problem or how the workflow struggles without memory |
| Demonstration | 2–3 minutes | A realistic interaction showing retention and recall |
| Wrap-up | 30 seconds | One key takeaway or lesson |

The guide recommends showing retention and recall happening during the demonstration.

---

## 7. Judging Criteria

The official problem statement gives the following evaluation weights:

| Criterion | Weight | What Judges Are Looking For |
|---|---:|---|
| Innovation | 30% | A fresh approach to a real problem; more than an obvious chatbot |
| Use of Hindsight Memory | 25% | Memory is central to the value proposition and the agent improves over time |
| Technical Implementation | 20% | Clean architecture, functional code, and handling of edge cases |
| User Experience | 15% | Intuitive interaction and a compelling demonstration |
| Real-world Impact | 10% | A genuine problem and a plausible path to adoption |

### What This Means for the Team

- Do not optimise only for the number of features.
- Make the memory behaviour observable and consequential.
- Build a reliable end-to-end workflow.
- Use a realistic scenario in the demo.
- Explain the practical value to the intended user.

These are practical interpretations of the official judging criteria.

---

## 8. Recommended Team Workflow

The following is a suggested way to organise the work.

This is a recommendation, not an official event-mandated sequence.

### Phase 1 — Understand and Select the Problem

- [ ] Read the official problem statement and this requirements document.
- [ ] Identify real workflow problems where persistent memory is valuable.
- [ ] Define the target user, problem, and expected outcome.
- [ ] Compare candidate ideas for usefulness, memory centrality, feasibility, and demo clarity.
- [ ] Select one project direction.

### Phase 2 — Define the Product

- [ ] Write a concise problem statement.
- [ ] Define the target persona and primary workflow.
- [ ] Specify what information the agent should retain.
- [ ] Specify when and how it should recall that information.
- [ ] Define what behaviour should improve because of memory.
- [ ] Define the smallest end-to-end version that proves the idea.

### Phase 3 — Design the System

- [ ] Review Hindsight documentation.
- [ ] Select Cloud or open-source deployment.
- [ ] Decide the LLM and application stack.
- [ ] Design the agent workflow and Hindsight integration.
- [ ] Define API boundaries and data flow.
- [ ] Plan error handling and persistence.
- [ ] Document the architecture before splitting implementation work.

### Phase 4 — Implement

- [ ] Build the smallest working end-to-end workflow first.
- [ ] Integrate Hindsight early.
- [ ] Implement retention, recall, and use of recalled information.
- [ ] Add the user interface and supporting backend components.
- [ ] Keep the repository organised and documented.

### Phase 5 — Test and Validate

- [ ] Test retention and recall across separate interactions.
- [ ] Test whether the correct information is recalled in the correct context.
- [ ] Test missing, ambiguous, outdated, or conflicting information.
- [ ] Test LLM and function-calling failures where applicable.
- [ ] Verify the complete workflow from the user's perspective.
- [ ] Prepare repeatable demo scenarios using realistic data.

### Phase 6 — Prepare the Submission

- [ ] Clean up and document the GitHub repository.
- [ ] Prepare the live demonstration.
- [ ] Record and publish the team video.
- [ ] Ensure every member publishes an article and social post.
- [ ] Prepare a clear explanation of Hindsight's role.
- [ ] Verify every deliverable before submission.

---

## 9. Team Coordination

The event documents do not prescribe team roles.

The following is a suggested division for a six-member team. Adjust it based on members' strengths and the selected architecture.

| Workstream | Suggested Responsibility |
|---|---|
| Architecture and Technical Coordination | System design, integration decisions, technical consistency |
| Agent and LLM Workflow | Agent logic, prompting, tool/function calling, workflow execution |
| Hindsight and Memory | Hindsight setup, retention, recall, memory evaluation |
| Backend and Data | APIs, application data, persistence, validation |
| Frontend and User Experience | User interface, interaction flow, usability |
| Testing, Integration, and Delivery | End-to-end testing, reliability, deployment, demo coordination |

These are workstreams, not isolated silos.

Every member should understand:

- The product workflow.
- The system architecture.
- How Hindsight contributes to the solution.

Pair on integration points and review one another's work.

---

## 10. Important Clarifications and Unknowns

The supplied problem statement and content guide do **not** specify:

- A confirmed event date or final submission deadline.
- An interim deadline such as a project idea, abstract, proposal, or architecture submission.
- A mandatory programming language or application framework.
- A mandatory LLM provider or model.
- A mandatory choice between Hindsight Cloud and the open-source version.
- A prescribed team-role structure.

Do not infer deadlines or additional submission rules from this document.

Check official organiser announcements for updates and clarifications.

The content guide's article word-count inconsistency is documented in Section 6.1. Ask the organisers to clarify it.

---

## 11. Official Reference Links

| Resource | Link |
|---|---|
| Hindsight Documentation | https://hindsight.vectorize.io/ |
| Hindsight GitHub | https://github.com/vectorize-io/hindsight |
| Hindsight Cloud | https://ui.hindsight.vectorize.io |
| Band AI Desktop | https://www.band.ai |
| Groq | https://groq.com/ |
| Code.in | https://code.in/ |
| Google Jules | https://jules.google.com/ |
| OpenCode | https://opencode.ai/ |

---

## 12. Team Readiness Checklist

Use this checklist to track whether the team is prepared.

This is a working checklist, not a separate official submission form.

### Project

- [ ] We have selected a real problem and a clear target user.
- [ ] We have defined one primary workflow.
- [ ] Hindsight is central to the solution.
- [ ] We can explain what the agent retains, recalls, and does differently.
- [ ] We have a realistic scenario and data for the demonstration.

### Technology

- [ ] We have downloaded and used Band AI Desktop.
- [ ] We have selected Hindsight Cloud or the open-source version.
- [ ] We have reviewed the Hindsight documentation.
- [ ] We have selected an LLM and application stack.
- [ ] We have a working end-to-end integration.

### Engineering

- [ ] The repository is organised and documented.
- [ ] Retention and recall work across separate interactions.
- [ ] We have tested failure and edge cases.
- [ ] The complete workflow is reproducible.
- [ ] We have a stable demonstration environment.

### Submission

- [ ] GitHub repository is ready.
- [ ] Hindsight usage is documented and explainable.
- [ ] Live demo is prepared.
- [ ] Team video is publicly available on YouTube and meets the format requirements.
- [ ] Every team member has published an article.
- [ ] Every team member has published a social post.
- [ ] Article and social post restrictions have been checked.
- [ ] Any unresolved requirements have been clarified with the organisers.

---

**End of Requirements Document**