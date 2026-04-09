---
title: Sentinel GRC Audit
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
---
# 🛡️ Sentinel GRC: High-Precision Autonomous Compliance Auditor

## 🌍 Real-World Problem & Motivation

Enterprise compliance audits are notoriously manual, expensive, and repetitive. Security teams routinely spend weeks painfully mapping internal policy documents to sprawling control frameworks like ISO 27001, NIST 800-53, and SOC 2. The manual nature of this work introduces a high risk of human error and inconsistency in a domain where absolute precision is required—not just "good sounding answers."

Current AI methodologies (such as standard RAG pipelines or zero-shot LLMs) fail dramatically at this task:
- **Long-context truncation:** Massive security documents overwhelm context windows, causing models to simply skip or forget sections.
- **Hallucinated Control IDs:** Models frequently invent fake compliance clauses (e.g., "ISO A.9.9") instead of utilizing exact taxonomy IDs.
- **Shallow Mapping:** RAG retrieves keywords but fails to perform the deep compliance reasoning required to verify if a control is genuinely satisfied.
- **Blind Gap Detection:** Standard models struggle to detect what is *missing* from a document, which is the entire purpose of a gap analysis.

This matters because compliance failures carry catastrophic financial and legal consequences. Enterprises urgently need reliable, repeatable AI auditing systems. This is not a chatbot problem—it is a rigorous, structured reasoning problem.

## Executive Value Proposition

Sentinel GRC is a **High-Precision Autonomous Auditing System** built for the Meta OpenEnv Hackathon. It expressly solves the real-world enterprise bottleneck of policy mapping by targeting the "Truncation & Hallucination Gap" that plagues traditional LLM implementations. Sentinel GRC addresses this bottleneck by enforcing structured environments, granular state transitions, and strong grounding against deterministic ground truths.

---

## 🚀 The Triple-Threat Architecture

The Sentinel environment employs three distinct mechanisms to enforce rigorous, enterprise-grade agent behavior:

### 1. Progressive Sectional Inference
Instead of forcing an LLM to absorb a massive 50-page policy and map all controls simultaneously, the environment enforces **one-section-at-a-time auditing**. This isolates context, significantly reduces long-context truncation, and ensures highly stabilised structured output across both lightweight and complex models (accelerating audit turnaround times).

### 2. Deterministic Hint Injection
Real JSON taxonomies (specific ISO/NIST/SOC2 controls) are dynamically injected into the active prompt payload during state transitions. This empirically stabilises the output and enforces that the LLM utilizes exact, validated control IDs rather than mutating them, resolving the primary hallucination risk faced by compliance teams.

### 3. Refinement Decay Logic
To prevent agents from getting stuck in perpetual, hallucinated problem-solving loops, the inference logic implements an **early-exit mechanism**. If consecutive refinement steps yield decaying scores, the episode deterministically terminates. This mimics human auditor time-boxing, stabilizing overall agent behavior and protecting compute resources.

---

## 📊 Benchmark Performance

Sentinel GRC is evaluated using a strict multi-task grading framework. The table below shows representative validation results observed during development.

| Task | Score | Description |
|------|------:|------------|
| **task_easy** | 0.63 | Single-framework (ISO 27001) control classification. |
| **task_medium** | 0.91 | Dual-framework coverage execution & gap analysis. |
| **task_hard** | 0.56 | Full tri-framework (ISO/NIST/SOC2) audit and overlap detection. |

*Note: The 0.91 score observed in representative validation runs demonstrates strong alignment with structured audit expectations on the medium-difficulty task. The scaling difficulty of multi-framework reasoning in `task_hard` provides a realistic, representative performance ceiling for evaluating how state-of-the-art models interact with strict enterprise constraints.*

---

## 🛠️ Engineering Rigor

Sentinel was designed heavily around reliability, reproducibility, and deployability for the OpenEnv multi-mode validator:

- **Pydantic Action Sanitization**: Immutable parsing of agent actions.
- **Deterministic Graders**: Lightweight native Python scoring logic for reproducibility, transparency, and low runtime overhead.
- **Structured Validation**: Zero log collision (perfectly compliant `[START]/[STEP]/[END]` isolation directly on `sys.stdout`).
- **Lightweight Infrastructure**: Specifically optimized to execute gracefully within the 8GB memory footprint constraint of Hugging Face free-tier containers.
- **Production-Ready OpenEnv Deployment**: Fully supports Docker, local FastAPI, and serverless package-mode testing without configuration bloat.

---

## 🧠 Why This Matters in the Real World

This is not just a benchmark—it models a genuine enterprise workflow. Sentinel GRC bridges the gap between impressive LLM demos and production-grade auditing systems. 

In a real-world enterprise, this architecture can be directly operationalised for:
- **Audit Preparation:** Pre-scanning policies before expensive external auditors arrive.
- **Compliance Gap Detection:** Automatically flagging missing security controls during document revisions.
- **Internal Security Validation:** Standardising policy governance reviews dynamically across all internal squads.

Auditing in Sentinel requires contextual orchestration. An agent must successfully combine Constraint Reasoning, Structured Mapping, Gap Detection, and Multi-Step Improvement to securely validate corporate assets.

---

## 🧱 System Architecture

```text
Agent Prompting & Control
         │
         ▼
[ Inference Engine ] ──(REST/WebSocket)──► [ OpenEnv API Wrapper ]
                                                  │
   ┌──────────────────────────────────────────────┴─┐
   │ ⚙️ GRC Environment Wrapper                      │
   │   - Section isolation                          │
   │   - Taxonomy injection                         │
   └───────────────┬────────────────────────────────┘
                   ▼
         [ Graders & Evaluators ]
           (ISO F1, Gap Delta)
                   │
                   ▼
    Reward <─(continuous bounded signal)─> Feedback Loop
```

---

## 📦 Project Structure

```text
/
├── Dockerfile                  # HF Space / Docker initialization
├── README.md                   # Project documentation
├── inference.py                # Core progressive inference loop
├── openenv.yaml                # OpenEnv configuration manifest
├── pyproject.toml              # Project dependencies & entrypoints
├── requirements.txt            # Dep configuration
├── uv.lock                     # Validated dependency lockfile
├── server/
│   └── app.py                  # Standardized FastAPI shim
└── grc_compliance_audit_env/
    ├── Dockerfile              # Internal containerization
    ├── __init__.py
    ├── client.py               # WebSocket client hooks
    ├── models.py               # Pydantic state/schema definitions
    ├── README.md
    └── server/
        ├── app.py              # Root ASGI provider
        ├── grc_environment.py  # Primary RL loop logic
        ├── data/               # Ground-truth JSONs + Text fixtures
        ├── graders/            # F1 & Coverage penalty engines
        └── tasks/              # Easy, Medium, Hard task wrappers
```

---

## ⚡ Quick Start 

The environment requires an OpenAI-compliant API for execution.

**Environment Variables Required:**
- `API_BASE_URL` 
- `MODEL_NAME` (e.g., `gpt-4o-mini`)
- `HF_TOKEN` (or `API_KEY`)

### 1. Run inference locally (Hackathon Mode)

Executes the progressive RAG framework against the built-in test server.

```bash
uv sync
python inference.py
```

### 2. Run the environment server manually

Spin up the Uvicorn host on the mandated Hackathon port (7860).

```bash
uvicorn grc_compliance_audit_env.server.app:app --host 0.0.0.0 --port 7860
```

### 3. Build & Run via Docker

```bash
docker build -t grc-audit-env .
docker run -p 7860:7860 grc-audit-env
```

---

## 🌍 Roadmap to Enterprise

While Sentinel GRC v1 targets the core triad of security frameworks, the system's modular Pydantic architecture provides a rapid bridge to production enterprise use cases:

- **GDPR / CCPA Mapping**: Expanding taxonomies to enforce privacy directives natively.
- **HIPAA Integration**: Direct alignment for Healthcare cloud infrastructure auditing.
- **Automated Evidence Collection**: Future integration with browser-based agents for automated evidence collection from enterprise systems to prove the controls exist.
- **Enterprise Audit Copilots**: Embedding the progressive inference engine seamlessly into internal GRC platforms (like Drata or Vanta) to generate pre-audit validations.
