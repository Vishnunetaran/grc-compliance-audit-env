# GRC Compliance Audit Environment — OpenEnv
## Complete Research & Execution Context Document for AI Agent

**Version:** 1.0 | **Prepared for:** Meta × Scaler OpenEnv Hackathon, Round 1
**Purpose:** Feed this document verbatim as context to an AI agent before writing a single line of code.
**Do not skip any section.** Every section feeds a specific implementation decision.

---

## SECTION 1 — MISSION STATEMENT FOR THE AI AGENT

You are building a complete, production-ready OpenEnv RL environment called
`grc_compliance_audit_env`. This environment simulates the task of a GRC (Governance, Risk,
and Compliance) analyst auditing an organisation's policy documents against one or more
security frameworks — specifically **ISO 27001:2022**, **NIST 800-53 Rev 5**, and **SOC 2
(AICPA Trust Services Criteria)**.

An AI agent trained on this environment must learn to:
1. Read a policy document (text) and identify which controls it addresses.
2. Map identified controls to the appropriate framework clauses/IDs.
3. Detect gaps — controls required by the framework that the policy does NOT cover.
4. Produce a structured gap analysis report with remediation suggestions.

The environment has **3 tasks of increasing difficulty**, deterministic graders, partial
rewards at every step, and a clean Docker+HuggingFace deployment. You will implement every
file from scratch following the exact OpenEnv spec documented in Section 5.

**Read this entire document before writing any code.**

---

## SECTION 2 — WHY THIS ENVIRONMENT HAS THE HIGHEST WIN PROBABILITY

### 2.1 Market Scale — The Real Business Pain

The GRC (Governance, Risk, and Compliance) software market is one of the most acutely
under-automated enterprise verticals:

- The global GRC market is projected to reach **$65.2 billion in 2026** according to Technavio.
  The compliance automation sub-segment alone was estimated at **$2.8 billion in 2025** and
  is growing faster than the overall market at 25%+ annually.

- The average annual audit preparation cost is **$210,000 per organisation** (Hyperproof).
  Compliance teams spend an average of **11 working weeks per year** on compliance-related
  tasks. These costs are driving adoption of compliance automation platforms that can reduce
  manual preparation time by 41%.

- **81% of organisations** report current or planned ISO 27001 certification in 2025.
  **78% of tech companies** include SOC 2 in their go-to-market strategy. According to
  Gartner, legal and compliance departments will increase their investment in GRC tools by
  **50% by 2026**.

- Modern GRC shifts compliance from periodic checkbox exercises to **continuous security
  posture management** with real-time drift detection — but this requires AI agents capable
  of reading policies, reasoning about control coverage, and flagging gaps automatically.

- AI is increasingly serving as the engine behind **cross-mapping controls across multiple
  frameworks**. Organisations with overlapping obligations under SOC 2, ISO 27001, GDPR,
  HIPAA, FedRAMP, and CMMC can use AI to maintain unified, continuously updated compliance
  states without duplicating efforts.

### 2.2 The Gap No OpenEnv Environment Fills

Search the OpenEnv Hub (`huggingface.co/openenv`) right now. There is no GRC, compliance,
or information-security audit environment. This domain has zero coverage. The environment
you build will be the **first and only** RL environment for training agents on compliance
workflows — immediately valuable to the global enterprise security community.

### 2.3 The Builder's Asymmetric Advantage

This environment is being built by someone who works at **CyRAACS**, an India-based
cybersecurity and GRC firm, building the **COMPASS platform** (policy management, gap
assessment, trust centre modules). The builder has:
- Production JSON files for ISO 27001, NIST 800-53, RBI IT GRC, and SOC2 control taxonomies.
- Real client deliverables (gap analysis reports, Excel risk registers).
- Ground-truth understanding of where agents fail in real GRC workflows.
- Experience mapping controls across frameworks in the COMPASS agentic CMS.

No other participant in a 70,000-person pool has this depth. Use it.

---

## SECTION 3 — FRAMEWORK KNOWLEDGE BASE (THE AGENT'S DOMAIN TAXONOMY)

The agent must deeply understand all three frameworks it will audit against.
This section is the authoritative reference for every data model, grader, and task design.

### 3.1 ISO 27001:2022 — Annex A Controls

**What it is:** International standard for Information Security Management Systems (ISMS).
Certification is achieved via third-party audit. The current version is **ISO 27001:2022**,
which replaced ISO 27001:2013.

**Structure:** ISO 27001:2022 contains **93 controls** structured into **4 themes** to simplify
ownership and classification — replacing the previous 14 domains from the 2013 version:
- **Organisational Controls** (37 controls, A.5.1–A.5.37): policies, rules, procedures
- **People Controls** (8 controls, A.6.1–A.6.8): HR security, training, awareness
- **Physical Controls** (14 controls, A.7.1–A.7.14): facility protection, equipment security
- **Technological Controls** (34 controls, A.8.1–A.8.34): encryption, monitoring, malware

**New in 2022:** 11 new controls were added, including:
- **A.5.7 Threat intelligence**: Collect and analyse data on potential threats.
- **A.5.23 Information security for cloud services**: Define and monitor cloud IS requirements.
- **A.5.30 ICT readiness for business continuity**: Create an ICT continuity plan.
- **A.8.9 Configuration management**: Manage security configurations of hardware/software.
- **A.8.10 Information deletion**: Delete data no longer needed per defined criteria.
- **A.8.11 Data masking**: Mask data in line with access control and business policies.
- **A.8.12 Data leakage prevention**: Detect and prevent unauthorised disclosure.
- **A.8.16 Monitoring activities**: Monitor networks, systems and applications.
- **A.8.23 Web filtering**: Manage which websites users can access.
- **A.8.28 Secure coding**: Establish and apply principles for secure software development.

**Key ISO 27001 Controls the agent will use as grader ground truth** (abbreviated list
for the most commonly assessed in enterprise audits):

| Control ID | Name | Theme | Gap-Risk Level |
|---|---|---|---|
| A.5.1 | Policies for information security | Org | HIGH |
| A.5.2 | Information security roles and responsibilities | Org | HIGH |
| A.5.10 | Acceptable use of information and assets | Org | MEDIUM |
| A.5.15 | Access control | Org | CRITICAL |
| A.5.23 | Cloud services security | Org | HIGH |
| A.5.30 | ICT readiness for business continuity | Org | HIGH |
| A.6.3 | Information security awareness, education, training | People | HIGH |
| A.6.5 | Responsibilities after termination | People | MEDIUM |
| A.7.1 | Physical security perimeters | Physical | MEDIUM |
| A.7.10 | Storage media | Physical | MEDIUM |
| A.8.2 | Privileged access rights | Tech | CRITICAL |
| A.8.3 | Information access restriction | Tech | CRITICAL |
| A.8.5 | Secure authentication | Tech | CRITICAL |
| A.8.7 | Protection against malware | Tech | HIGH |
| A.8.8 | Management of technical vulnerabilities | Tech | HIGH |
| A.8.12 | Data leakage prevention | Tech | HIGH |
| A.8.15 | Logging | Tech | HIGH |
| A.8.24 | Use of cryptography | Tech | HIGH |
| A.8.25 | Secure development lifecycle | Tech | HIGH |
| A.8.28 | Secure coding | Tech | HIGH |

**Statement of Applicability (SoA):** The most important document in ISO 27001 compliance.
Lists all 93 Annex A controls with: implementation status, justification for inclusion/exclusion,
and evidence references. The GRC audit environment simulates generating a SoA from policy documents.

### 3.2 NIST 800-53 Rev 5 — Control Families

**What it is:** The US government's catalogue of security and privacy controls for federal
information systems. Widely adopted by private sector as a comprehensive framework.
Mandatory for FISMA compliance. Published by the National Institute of Standards and Technology.

**Structure:** NIST SP 800-53 Rev 5 comprises **over 300 controls** across **20 control families**.
Each control breaks down into several sub-controls, totalling over 1,000 when sub-controls
are included. All are updated periodically to account for evolving threats.

**The 20 NIST 800-53 Control Families** (the agent's classification taxonomy for NIST):

| Family ID | Family Name | Abbrev | Relevance |
|---|---|---|---|
| AC | Access Control | AC | CRITICAL |
| AT | Awareness and Training | AT | HIGH |
| AU | Audit and Accountability | AU | HIGH |
| CA | Assessment, Authorization, Monitoring | CA | HIGH |
| CM | Configuration Management | CM | HIGH |
| CP | Contingency Planning | CP | HIGH |
| IA | Identification and Authentication | IA | CRITICAL |
| IR | Incident Response | IR | HIGH |
| MA | Maintenance | MA | MEDIUM |
| MP | Media Protection | MP | MEDIUM |
| PE | Physical and Environmental Protection | PE | MEDIUM |
| PL | Planning | PL | HIGH |
| PM | Program Management | PM | HIGH |
| PS | Personnel Security | PS | HIGH |
| PT | PII Processing and Transparency | PT | HIGH |
| RA | Risk Assessment | RA | CRITICAL |
| SA | System and Services Acquisition | SA | HIGH |
| SC | System and Communications Protection | SC | CRITICAL |
| SI | System and Information Integrity | SI | CRITICAL |
| SR | Supply Chain Risk Management | SR | HIGH |

**Key sub-controls referenced in policy audits:**
- AC-1: Access Control Policy and Procedures
- AC-2: Account Management
- AC-3: Access Enforcement
- AC-17: Remote Access
- IA-2: Multi-Factor Authentication
- IA-5: Authenticator Management
- AU-2: Event Logging
- AU-12: Audit Record Generation
- IR-1: Incident Response Policy
- IR-4: Incident Handling
- SC-8: Transmission Confidentiality and Integrity
- SC-28: Protection of Information at Rest
- SI-3: Malicious Code Protection
- SI-10: Information Input Validation
- RA-3: Risk Assessment
- RA-5: Vulnerability Monitoring and Scanning
- CM-6: Configuration Settings
- CP-9: System Backup

**Official NIST mapping resource:**
NIST publishes a formal crosswalk between NIST 800-53 Rev 5 and ISO 27001:2022 at:
`https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final`
(Document: `sp800-53r5-to-iso-27001-mapping.docx`)
The agent must use control IDs from this crosswalk when generating cross-framework mappings.

### 3.3 SOC 2 (AICPA Trust Services Criteria)

**What it is:** Auditing standard for service organisations managing customer data. Developed
by the American Institute of CPAs (AICPA). Not a certification — it's a third-party audit
report (Type I = point-in-time, Type II = over 6–12 months). Universally required for
B2B SaaS companies seeking enterprise customers.

**Structure — 5 Trust Services Criteria (TSC):**

| TSC ID | Criterion | Typical Policy Area |
|---|---|---|
| CC | Common Criteria (Security) | 9 categories, mandatory for all SOC 2 audits |
| A | Availability | System availability SLAs and monitoring |
| PI | Processing Integrity | Data processing accuracy and completeness |
| C | Confidentiality | Data classification and handling |
| P | Privacy | Personal data collection, use, retention, disposal |

**SOC 2 Common Criteria (CC) — most commonly audited, mapped to policy docs:**

| CC ID | Name | Maps to in Policy |
|---|---|---|
| CC1.1–CC1.5 | Control Environment | Security governance, roles |
| CC2.1–CC2.3 | Communication & Information | Security communications policy |
| CC3.1–CC3.4 | Risk Assessment | Risk management policy |
| CC4.1–CC4.2 | Monitoring Activities | Audit and monitoring policy |
| CC5.1–CC5.3 | Control Activities | Access control, change management |
| CC6.1–CC6.8 | Logical and Physical Access | Access control policy (most assessed) |
| CC7.1–CC7.5 | System Operations | Incident response, change management |
| CC8.1 | Change Management | Change management policy |
| CC9.1–CC9.2 | Risk Mitigation | Vendor management, business continuity |

**Cross-framework overlap (critical for the grader's shared-control scoring):**
There is approximately **80% overlap** between SOC 2 and ISO 27001 criteria according to
the AICPA's official mapping spreadsheet. The controls in both standards overlap by as much
as **96%**, covering foundational security principles such as data security, integrity,
availability, and confidentiality.

This overlap is a KEY feature of the environment — the hard task uses multi-framework
coverage, and shared controls earn score across both frameworks simultaneously.

### 3.4 The Cross-Framework Mapping Table (Agent's Core Reference)

This is the ground truth for the grader's cross-framework coverage calculation:

| Policy Topic | ISO 27001 | NIST 800-53 | SOC 2 TSC |
|---|---|---|---|
| Access Control Policy | A.5.15, A.8.2, A.8.3 | AC-1, AC-2, AC-3 | CC6.1, CC6.2, CC6.3 |
| Authentication & MFA | A.8.5 | IA-2, IA-5 | CC6.1, CC6.6 |
| Incident Response Policy | A.5.24, A.5.25, A.5.26 | IR-1, IR-4, IR-8 | CC7.2, CC7.3, CC7.4 |
| Data Classification | A.5.12, A.5.13 | MP-3, RA-2 | C-1, C-2 |
| Encryption / Cryptography | A.8.24 | SC-8, SC-28 | CC6.1, CC6.7 |
| Vulnerability Management | A.8.8 | RA-5, SI-2 | CC7.1 |
| Change Management | A.8.32 | CM-3, CM-5 | CC8.1 |
| Business Continuity | A.5.29, A.5.30 | CP-2, CP-9 | A-1 |
| Logging & Monitoring | A.8.15, A.8.16 | AU-2, AU-12 | CC7.2 |
| Vendor Management | A.5.19, A.5.20 | SR-3, SR-5 | CC9.2 |
| Security Awareness Training | A.6.3 | AT-2, AT-3 | CC1.4 |
| Physical Security | A.7.1–A.7.4 | PE-2, PE-3 | CC6.4 |
| Secure Development | A.8.25, A.8.28 | SA-3, SA-8 | CC8.1 |
| Risk Assessment | A.5.3, A.8.2 | RA-3, RA-5 | CC3.1–CC3.4 |
| Privacy / Data Protection | A.5.34 | PT-1–PT-7 | P-1–P-8 |

---

## SECTION 4 — THE THREE TASKS: COMPLETE SPECIFICATION

### Task 1 — EASY: Single-Framework Control Classification

**Difficulty:** Easy
**Max steps:** 5
**Target framework:** ISO 27001:2022 only
**Episode type:** One policy document, one framework

**Scenario:** The agent is given a single synthetic policy document (e.g., an Access Control
Policy, ~400 words, 5–8 numbered sections). The agent must read each section and classify
it as addressing one or more ISO 27001 Annex A control IDs.

**Action the agent takes:**
```
For each policy section → output a list of ISO 27001 control IDs it satisfies
```

**Grader logic (fully deterministic):**
```
For each policy section s:
  ground_truth_controls(s)  = set of control IDs in the annotation fixture
  agent_controls(s)         = set of control IDs in the agent's action

  section_precision = |agent ∩ gt| / |agent|   (if agent is empty: 0)
  section_recall    = |agent ∩ gt| / |gt|       (if gt is empty: 1.0)
  section_f1        = 2 × P × R / (P + R)

macro_f1 = mean(section_f1 across all sections with non-empty gt)
reward   = macro_f1   # already in [0.0, 1.0]
```

**Partial reward:** After each step (each section classified), emit partial reward
equal to that section's F1. Agent learns section-by-section, not just at episode end.

**Why this is genuinely hard for frontier models:**
- ISO 27001 control IDs are not well-represented in training data.
- A.8.2 (Privileged Access Rights) vs A.5.15 (Access Control) are frequently confused.
- Some policy sections address multiple controls; agents must emit a set, not a singleton.
- Over-flagging (high recall, low precision) is penalised equally to under-flagging.

### Task 2 — MEDIUM: Gap Analysis Against Two Frameworks

**Difficulty:** Medium
**Max steps:** 10
**Target frameworks:** ISO 27001:2022 + NIST 800-53 Rev 5
**Episode type:** A 3-section policy document with deliberate gaps pre-seeded

**Scenario:** The agent is given a partial Information Security Policy (3 sections: Data
Classification, Access Control, Incident Response). The policy is intentionally missing
two required controls per framework. The agent must:
1. Map each policy section to ISO 27001 and NIST 800-53 controls it covers.
2. Identify the controls from the target framework that are NOT covered by any section.
3. Output a structured gap analysis listing missing control IDs and the policy sections that
   would need to be added/amended to close each gap.

**Action the agent takes:**
```
covered_controls:   {iso_ids: [...], nist_ids: [...]}  # what IS addressed
gap_controls:       {iso_ids: [...], nist_ids: [...]}  # what is MISSING
gap_analysis:       [{control_id, framework, gap_description, suggested_addition}]
```

**Grader logic (fully deterministic):**
```
# Component 1: Coverage accuracy (40%)
# How many of the policy's actual control coverages did the agent correctly identify?
coverage_precision = |agent_covered ∩ gt_covered| / |agent_covered|
coverage_recall    = |agent_covered ∩ gt_covered| / |gt_covered|
coverage_f1        = 2 × P × R / (P + R)

# Component 2: Gap detection accuracy (40%)
# Did the agent find the pre-seeded gaps?
gap_precision = |agent_gaps ∩ gt_gaps| / |agent_gaps|
gap_recall    = |agent_gaps ∩ gt_gaps| / |gt_gaps|
gap_f1        = 2 × P × R / (P + R)

# Component 3: Gap description quality (20%)
# Does each gap description correctly name the missing control and why?
# Keyword-match check: deterministic — checks that control_id is mentioned,
# and that gap_description contains at least one keyword from the control's
# canonical description (e.g. "authentication" for IA-2).
description_score = fraction of gap items passing keyword check

composite_reward = 0.40 × coverage_f1 + 0.40 × gap_f1 + 0.20 × description_score
```

**Partial reward:** After each step (submit coverage for one section), emit partial reward
for that section's classification accuracy before the agent moves to the next section.

**Pre-seeded gaps in the medium fixture (known to the grader, hidden from the agent):**
ISO 27001 gaps: A.8.5 (Secure Authentication), A.8.8 (Vulnerability Management)
NIST 800-53 gaps: IA-2 (Multi-Factor Authentication), RA-5 (Vulnerability Scanning)
Note: These are paired — same real-world gap surfaces in both frameworks simultaneously.
This tests whether the agent understands cross-framework equivalence.

### Task 3 — HARD: Full Multi-Framework Compliance Audit

**Difficulty:** Hard
**Max steps:** 20
**Target frameworks:** ISO 27001:2022 + NIST 800-53 Rev 5 + SOC 2 TSC
**Episode type:** A 10-section Information Security Policy with 5 pre-seeded gaps

**Scenario:** The agent receives a complete (but imperfect) Information Security Policy
covering: Security Governance, Asset Management, Access Control, Cryptography, Physical
Security, Operations Security, Incident Management, Business Continuity, Vendor Management,
Compliance & Audit. The policy has 5 deliberate gaps across the three frameworks.

The agent must produce a complete compliance audit report:
1. Map all policy sections to controls across all three frameworks.
2. Identify all 5 gaps with correct control IDs, framework names, and risk ratings.
3. Write remediation suggestions for each gap.
4. Output a cross-framework coverage summary (which controls are satisfied by multiple
   frameworks simultaneously — the "shared control dividend").

**Action the agent takes:**
```
control_mapping:    {section_id → {iso: [...], nist: [...], soc2: [...]}}
gaps:               [{control_id, framework, risk_level, gap_description, remediation}]
cross_framework:    [{iso_id, nist_id, soc2_id, policy_section_satisfying_all}]
executive_summary:  str  # brief plain-English audit summary
```

**Grader logic (three-component composite, fully deterministic + optional LLM judge):**
```
# Component 1: Control mapping accuracy (35%)
# For each section, F1 between agent's control IDs and ground truth per framework
per_framework_f1 = {
    "iso": macro_f1(agent_iso, gt_iso),
    "nist": macro_f1(agent_nist, gt_nist),
    "soc2": macro_f1(agent_soc2, gt_soc2)
}
mapping_score = mean(per_framework_f1.values())

# Component 2: Gap detection (40%)
# Did the agent find all 5 seeded gaps?
gap_coverage = |agent_gaps ∩ seeded_gaps| / 5     # 0.0 to 1.0
# Severity accuracy: did agent correctly classify risk_level?
# (seeded gaps have known risk levels: critical, high, medium)
severity_accuracy = fraction of found gaps with correct risk_level
gap_score = 0.7 × gap_coverage + 0.3 × severity_accuracy

# Component 3: Cross-framework quality (25%)
# Did agent identify shared controls? (deterministic check against cross-map table)
shared_control_precision = |agent_shared ∩ gt_shared| / |agent_shared|
shared_control_recall    = |agent_shared ∩ gt_shared| / |gt_shared|
shared_f1 = 2 × P × R / (P + R)

# Optional LLM judge for remediation quality (replaces component 3 if OPENAI_API_KEY set)
# Prompt: "Rate 0.0–1.0: does this remediation correctly address [control_id]? Output only float."
# Falls back to keyword-match heuristic if no API key.

composite_reward = 0.35 × mapping_score + 0.40 × gap_score + 0.25 × cross_framework_quality
```

**Pre-seeded gaps in hard fixture:**
1. Missing: A.8.5 / IA-2 / CC6.6 — No MFA requirement in the Access Control section (CRITICAL)
2. Missing: A.8.8 / RA-5 / CC7.1 — No vulnerability scanning procedure (HIGH)
3. Missing: A.5.24 / IR-4 / CC7.3 — Incident classification criteria absent (HIGH)
4. Missing: A.5.30 / CP-9 / A-1 — No data backup frequency specified in BCP (HIGH)
5. Missing: A.5.19 / SR-3 / CC9.2 — Third-party security assessment process missing (MEDIUM)

---

## SECTION 5 — OPENENV SPEC (EXACT IMPLEMENTATION INSTRUCTIONS)

### 5.1 Framework Overview

OpenEnv is Meta's open-source RL environment framework. It uses Gymnasium-style APIs
(`reset()`, `step()`, `state()`) served over **WebSocket** via FastAPI.

**Install:** `pip install openenv-core`
**GitHub:** `https://github.com/meta-pytorch/OpenEnv`
**Docs:** `https://meta-pytorch.org/OpenEnv/`
**HF Course:** `https://github.com/huggingface/openenv-course`

### 5.2 Required Project Structure

```
grc_compliance_audit_env/
├── __init__.py                    # exports: GRCAction, GRCObservation, GRCAuditEnv
├── client.py                      # GRCAuditEnv(EnvClient) — WebSocket client
├── models.py                      # GRCAction, GRCObservation, GRCState (Pydantic)
├── openenv.yaml                   # manifest — spec_version: 1
├── pyproject.toml                 # package deps
├── inference.py                   # MUST be in root, uses OpenAI client, env variables
├── README.md
└── server/
    ├── __init__.py
    ├── app.py                     # create_app(GRCEnvironment, GRCAction, GRCObservation)
    ├── grc_environment.py         # GRCEnvironment(Environment) — reset/step/state
    ├── tasks/
    │   ├── __init__.py
    │   ├── easy_task.py           # Task 1: single-framework classification
    │   ├── medium_task.py         # Task 2: dual-framework gap analysis
    │   └── hard_task.py           # Task 3: full multi-framework audit
    ├── graders/
    │   ├── __init__.py
    │   ├── classification_grader.py   # F1 scorer using sklearn
    │   ├── gap_grader.py              # gap detection precision/recall
    │   └── cross_framework_grader.py  # shared-control coverage grader
    ├── data/
    │   ├── fixtures/
    │   │   ├── easy_access_control_policy.txt
    │   │   ├── easy_access_control_policy.json      # ground truth annotations
    │   │   ├── medium_infosec_policy.txt
    │   │   ├── medium_infosec_policy.json
    │   │   ├── hard_complete_isms_policy.txt
    │   │   └── hard_complete_isms_policy.json
    │   └── taxonomies/
    │       ├── iso27001_controls.json                # all 93 controls with IDs + names
    │       ├── nist_80053_families.json              # 20 families + key sub-controls
    │       └── soc2_tsc.json                         # TSC categories + criteria IDs
    ├── requirements.txt
    └── Dockerfile
```

### 5.3 openenv.yaml — Exact Format

```yaml
spec_version: 1

name: grc_compliance_audit_env
display_name: "GRC Compliance Audit"
version: "0.1.0"
description: >
  An RL environment where an AI agent acts as a GRC analyst, reading policy documents
  and auditing them against ISO 27001:2022, NIST 800-53 Rev 5, and SOC 2 Trust Services
  Criteria. The agent must identify covered controls, detect compliance gaps, and produce
  structured gap analysis reports — scored against expert-annotated ground truth.
  Designed to train agents for enterprise cybersecurity compliance workflows.

type: text
author: "<your_name>"
license: "Apache-2.0"
tags:
  - grc
  - compliance
  - iso27001
  - nist
  - soc2
  - cybersecurity
  - enterprise
  - gap-analysis

runtime:
  type: docker
  image: grc-compliance-audit-env:latest

app: server.app:app
port: 8000

env_vars:
  - name: OPENAI_API_KEY
    description: "API key for optional LLM-as-judge grader (hard task)"
    required: false
  - name: MODEL_NAME
    description: "LLM model identifier for inference script"
    default: "gpt-4o-mini"
    required: false
  - name: API_BASE_URL
    description: "Base URL for OpenAI-compatible API"
    default: "https://api.openai.com/v1"
    required: false
  - name: HF_TOKEN
    description: "Hugging Face token for Space deployment"
    required: false

tasks:
  - id: "task_easy"
    name: "Single-Framework Control Classification"
    difficulty: "easy"
    description: >
      Read a single policy document (Access Control Policy, ~400 words) and classify
      each section's coverage against ISO 27001:2022 Annex A control IDs.
      Score: macro-F1 on control ID assignment vs ground-truth annotations.
    reward_range: [0.0, 1.0]
    max_steps: 5

  - id: "task_medium"
    name: "Dual-Framework Gap Analysis"
    difficulty: "medium"
    description: >
      Audit a 3-section policy against ISO 27001:2022 and NIST 800-53. Map covered
      controls and identify the 4 pre-seeded gaps. Output structured gap analysis.
      Score: coverage F1 + gap detection F1 + description quality.
    reward_range: [0.0, 1.0]
    max_steps: 10

  - id: "task_hard"
    name: "Full Multi-Framework Compliance Audit"
    difficulty: "hard"
    description: >
      Audit a complete 10-section ISMS policy against ISO 27001, NIST 800-53, and
      SOC 2 simultaneously. Find all 5 seeded gaps, produce remediation suggestions,
      and output a cross-framework shared-control analysis.
      Score: mapping accuracy + gap detection + cross-framework coverage quality.
    reward_range: [0.0, 1.0]
    max_steps: 20
```

### 5.4 models.py — Complete Pydantic Implementation

```python
# models.py
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field
from openenv.core.env_server.types import Action, Observation, State


# ─── Enumerations ────────────────────────────────────────────────────────────

Framework = Literal["iso27001", "nist_80053", "soc2"]

RiskLevel = Literal["critical", "high", "medium", "low"]

TaskId = Literal["task_easy", "task_medium", "task_hard"]


# ─── Sub-models ──────────────────────────────────────────────────────────────

class ControlMapping(BaseModel):
    """Agent's mapping of a single policy section to framework controls."""
    section_id: str = Field(..., description="e.g. 'section_2' or 'access_control'")
    iso_control_ids: List[str] = Field(
        default_factory=list,
        description="ISO 27001 Annex A control IDs, e.g. ['A.5.15', 'A.8.3']"
    )
    nist_control_ids: List[str] = Field(
        default_factory=list,
        description="NIST 800-53 control IDs, e.g. ['AC-1', 'AC-3', 'IA-2']"
    )
    soc2_criteria_ids: List[str] = Field(
        default_factory=list,
        description="SOC 2 TSC criteria IDs, e.g. ['CC6.1', 'CC6.3']"
    )


class GapItem(BaseModel):
    """A single identified compliance gap."""
    control_id: str = Field(..., description="e.g. 'A.8.5' or 'IA-2' or 'CC6.6'")
    framework: Framework = Field(..., description="Which framework this gap belongs to")
    risk_level: RiskLevel = Field(..., description="Severity of this compliance gap")
    gap_description: str = Field(...,
        description="One-sentence description of what is missing in the policy")
    affected_section: Optional[str] = Field(None,
        description="Which policy section should be updated to close this gap")
    remediation: Optional[str] = Field(None,
        description="Suggested policy text addition or amendment to close the gap")


class SharedControl(BaseModel):
    """A control that is satisfied across multiple frameworks by the same policy text."""
    policy_section_id: str = Field(...,
        description="The policy section that satisfies all three framework controls")
    iso_control_id: str = Field(..., description="Equivalent ISO 27001 control")
    nist_control_id: str = Field(..., description="Equivalent NIST 800-53 control")
    soc2_criteria_id: str = Field(..., description="Equivalent SOC 2 TSC criterion")


# ─── Action ──────────────────────────────────────────────────────────────────

class GRCAction(Action):
    """
    The agent's response in a GRC compliance audit episode.

    For task_easy: populate control_mappings only.
    For task_medium: populate control_mappings AND gaps.
    For task_hard: populate control_mappings, gaps, shared_controls, executive_summary.

    The `reasoning` field is a free-text scratchpad — not scored, but logged for analysis
    and useful for chain-of-thought prompting in inference.py.
    """
    task_id: TaskId = Field(..., description="Which task this action responds to")
    reasoning: str = Field(default="",
        description="Agent's chain-of-thought or working notes (not scored)")

    # Task 1, 2, 3 — always required
    control_mappings: List[ControlMapping] = Field(
        default_factory=list,
        description="One ControlMapping per policy section, in order"
    )

    # Task 2, 3 — required for gap analysis
    gaps: List[GapItem] = Field(
        default_factory=list,
        description="Identified compliance gaps with control IDs and remediation"
    )

    # Task 3 only — cross-framework analysis
    shared_controls: List[SharedControl] = Field(
        default_factory=list,
        description="[task_hard] Controls satisfied across all three frameworks"
    )
    executive_summary: str = Field(default="",
        description="[task_hard] 2-3 sentence plain-English audit summary"
    )


# ─── Observation ─────────────────────────────────────────────────────────────

class GRCObservation(Observation):
    """
    What the environment returns to the agent.

    On reset(): full policy text, task description, available frameworks, hints.
    On step(): grader feedback, partial score, updated cumulative reward.

    `reward` (float, 0.0–1.0) and `done` (bool) are inherited from Observation base.
    """
    task_id: TaskId = Field(..., description="Active task")
    task_description: str = Field(...,
        description="Human-readable instructions for the current task")

    # Policy document
    policy_text: str = Field(...,
        description="Full text of the policy to audit, with section headers")
    policy_name: str = Field(...,
        description="Name of the policy document, e.g. 'Access Control Policy v2.1'")
    total_sections: int = Field(...,
        description="Number of numbered sections in the policy")

    # Framework context
    target_frameworks: List[Framework] = Field(...,
        description="Which frameworks to audit against for this episode")
    available_iso_controls: List[str] = Field(default_factory=list,
        description="[task_easy] Subset of ISO 27001 IDs relevant to this policy type")
    available_nist_families: List[str] = Field(default_factory=list,
        description="[task_medium/hard] NIST family abbreviations in scope")

    # Feedback after each step
    step_reward: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Reward earned in this step")
    cumulative_reward: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Total reward accumulated this episode")
    grader_feedback: str = Field(default="",
        description="Human-readable feedback explaining the step score")
    score_breakdown: Dict[str, float] = Field(default_factory=dict,
        description="Score components: mapping_f1, gap_f1, description_score, etc.")

    # Hints (task_easy gets hint on relevant control IDs, harder tasks don't)
    hint: str = Field(default="",
        description="Optional hint for task_easy only")


# ─── State ───────────────────────────────────────────────────────────────────

class GRCState(State):
    """
    Episode-level metadata. Extends the base State class.
    Accessible via state() — not sent on every step.
    Inherited from State: episode_id (str), step_count (int)
    """
    task_id: Optional[TaskId] = Field(default=None)
    policy_id: str = Field(default="", description="Fixture file identifier")
    policy_name: str = Field(default="")
    target_frameworks: List[str] = Field(default_factory=list)
    accumulated_reward: float = Field(default=0.0)
    max_steps: int = Field(default=20)
    is_complete: bool = Field(default=False)
    sections_processed: int = Field(default=0)
    score_history: List[Dict[str, float]] = Field(default_factory=list)
```

---

## SECTION 6 — DATA FIXTURES SPECIFICATION

The environment MUST be self-contained. All policy documents and annotations are bundled
as plain text + JSON files in `server/data/fixtures/`. No external API calls during inference.

### 6.1 Easy Fixture: Access Control Policy

**File:** `easy_access_control_policy.txt`

Structure (synthetic, ~400 words, 5 sections):
```
ACCESS CONTROL POLICY v1.0

1. Purpose and Scope
This policy establishes requirements for controlling access to information systems...

2. User Access Management
Access to systems is granted on a need-to-know basis. User accounts are provisioned
through formal request and approval. Access rights are reviewed quarterly...

3. Privileged Access
Administrative privileges are strictly limited. Privileged accounts require separate
credentials from standard user accounts. All privileged access is logged...

4. Remote Access
Remote access to organisational systems requires VPN. Sessions time out after 15 minutes
of inactivity...

5. Access Review and Termination
Access rights are reviewed every 6 months. Upon termination, all access is revoked within
24 hours...
```

**Annotation file:** `easy_access_control_policy.json`
```json
{
  "policy_id": "easy_001",
  "policy_name": "Access Control Policy v1.0",
  "policy_type": "access_control",
  "target_framework": "iso27001",
  "sections": [
    {
      "section_id": "section_1",
      "heading": "Purpose and Scope",
      "gt_iso_controls": ["A.5.1", "A.5.2"],
      "risk_coverage": "low"
    },
    {
      "section_id": "section_2",
      "heading": "User Access Management",
      "gt_iso_controls": ["A.5.15", "A.8.3"],
      "risk_coverage": "high"
    },
    {
      "section_id": "section_3",
      "heading": "Privileged Access",
      "gt_iso_controls": ["A.8.2"],
      "risk_coverage": "critical"
    },
    {
      "section_id": "section_4",
      "heading": "Remote Access",
      "gt_iso_controls": ["A.8.5", "A.8.20"],
      "risk_coverage": "high"
    },
    {
      "section_id": "section_5",
      "heading": "Access Review and Termination",
      "gt_iso_controls": ["A.5.15", "A.6.5"],
      "risk_coverage": "medium"
    }
  ]
}
```

### 6.2 Medium Fixture: Information Security Policy (Partial)

**File:** `medium_infosec_policy.txt`
Three sections covering Data Classification, Access Control, Incident Response.
**Pre-seeded gaps:** A.8.5 (no MFA requirement), A.8.8 (no vulnerability scanning).

**Annotation file:** `medium_infosec_policy.json`
```json
{
  "policy_id": "medium_001",
  "policy_name": "Information Security Policy v2.0 (Partial)",
  "target_frameworks": ["iso27001", "nist_80053"],
  "sections": [...],
  "seeded_gaps": [
    {
      "control_id": "A.8.5",
      "framework": "iso27001",
      "equivalent_nist": "IA-2",
      "risk_level": "critical",
      "gap_description": "No multi-factor authentication requirement specified",
      "missing_from_section": "section_2"
    },
    {
      "control_id": "A.8.8",
      "framework": "iso27001",
      "equivalent_nist": "RA-5",
      "risk_level": "high",
      "gap_description": "No vulnerability scanning or patch management process defined",
      "missing_from_section": null
    },
    {
      "control_id": "IA-2",
      "framework": "nist_80053",
      "equivalent_iso": "A.8.5",
      "risk_level": "critical",
      "gap_description": "Multi-factor authentication not specified for privileged access",
      "missing_from_section": "section_2"
    },
    {
      "control_id": "RA-5",
      "framework": "nist_80053",
      "equivalent_iso": "A.8.8",
      "risk_level": "high",
      "gap_description": "Vulnerability monitoring and scanning procedure absent",
      "missing_from_section": null
    }
  ]
}
```

### 6.3 Hard Fixture: Complete ISMS Policy

**File:** `hard_complete_isms_policy.txt`
10 sections covering all major ISMS domains. ~2,500 words. Five deliberate gaps.

**Annotation file:** `hard_complete_isms_policy.json`
Contains full ground truth for all three frameworks, all seeded gaps, and the
ground-truth shared-control mappings for cross-framework scoring.

The 5 seeded gaps are documented in Section 4, Task 3 above.
Each gap's annotation includes: control_id, framework, risk_level, gap_description,
missing_from_section, remediation_reference (keyword list for heuristic grader).

### 6.4 Taxonomy Files

**`server/data/taxonomies/iso27001_controls.json`:**
```json
{
  "version": "ISO 27001:2022",
  "controls": [
    {"id": "A.5.1", "name": "Policies for information security",
     "theme": "organizational", "keywords": ["policy", "information security", "management"]},
    {"id": "A.5.2", "name": "Information security roles and responsibilities",
     "theme": "organizational", "keywords": ["roles", "responsibilities", "accountability"]},
    {"id": "A.5.15", "name": "Access control",
     "theme": "organizational", "keywords": ["access", "authorisation", "need-to-know"]},
    {"id": "A.8.2", "name": "Privileged access rights",
     "theme": "technological", "keywords": ["privileged", "administrative", "superuser"]},
    {"id": "A.8.5", "name": "Secure authentication",
     "theme": "technological", "keywords": ["authentication", "MFA", "multi-factor", "password"]},
    ...all 93 controls...
  ]
}
```

**`server/data/taxonomies/nist_80053_families.json`:**
```json
{
  "version": "NIST SP 800-53 Rev 5",
  "families": [
    {"id": "AC", "name": "Access Control",
     "key_controls": ["AC-1", "AC-2", "AC-3", "AC-17"],
     "keywords": ["access", "authorisation", "account management"]},
    {"id": "IA", "name": "Identification and Authentication",
     "key_controls": ["IA-2", "IA-5"],
     "keywords": ["authentication", "identity", "MFA", "credentials"]},
    ...all 20 families...
  ]
}
```

---

## SECTION 7 — REWARD FUNCTION DESIGN

### 7.1 Principles

The reward function must provide **dense signal at every step**, not just at episode end.
This is a hard judging requirement ("Meaningful reward function — provides signal over
full trajectory").

**Rule 1 — Per-section partial reward (task_easy, task_medium):**
After each section classified, emit reward = that section's F1 immediately.
Never wait until all sections are done.

**Rule 2 — Severity-weighted gap detection (task_medium, task_hard):**
- Critical gap found correctly: +0.25 reward
- High gap found correctly: +0.15 reward
- Medium gap found correctly: +0.08 reward
- Critical gap missed entirely: -0.20 penalty (false negative on critical is severe)
- False alarm (gap reported that doesn't exist): -0.05 penalty

**Rule 3 — Efficiency bonus:**
If agent achieves score ≥ 0.80 before max_steps, add +0.10 bonus on the terminal step.
Trains agents to be efficient, not just thorough.

**Rule 4 — Anti-repetition penalty:**
If agent submits identical action as previous step: reward = -0.10, done = True.
Prevents infinite loop behaviour that wastes training compute.

**Rule 5 — Cross-framework bonus (task_hard only):**
For each correctly identified shared control (same gap in ISO + NIST + SOC2): +0.05 bonus.
Trains agents to understand framework equivalence, not just single-framework lookup.

```python
# Pseudocode reward calculation
def calculate_step_reward(action, ground_truth, step_count, prev_action):
    if action == prev_action:  # Rule 4
        return -0.10, True  # done=True

    # Base classification reward
    base = compute_f1(action.control_mappings, ground_truth.control_mappings)

    # Gap detection bonus (task_medium, task_hard)
    gap_bonus = 0.0
    for gap in action.gaps:
        if gap in ground_truth.seeded_gaps:
            gap_bonus += GAP_SEVERITY_REWARD[gap.risk_level]
        else:
            gap_bonus -= 0.05  # false alarm

    # Cross-framework bonus (task_hard)
    cf_bonus = 0.05 * shared_controls_correct(action.shared_controls, ground_truth.shared_controls)

    # Efficiency bonus
    eff_bonus = 0.10 if (base + gap_bonus >= 0.80 and step_count < max_steps) else 0.0

    reward = min(1.0, max(0.0, base + gap_bonus + cf_bonus + eff_bonus))
    done = (step_count >= max_steps) or (reward >= 0.95)
    return reward, done
```

---

## SECTION 8 — inference.py SPECIFICATION

This file MUST be in the **root directory** of the project.
MUST use OpenAI client. MUST read credentials from environment variables.
Runtime MUST be under 20 minutes on 2-vCPU / 8GB RAM.

```python
# inference.py
import os
import asyncio
import json
from openai import OpenAI
from grc_compliance_audit_env import GRCAuditEnv, GRCAction, ControlMapping, GapItem

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "https://<your-hf-space>.hf.space")

client = OpenAI(base_url=API_BASE_URL, api_key=os.environ.get("OPENAI_API_KEY", ""))

TASK_IDS = ["task_easy", "task_medium", "task_hard"]

SYSTEM_PROMPT = """You are an expert GRC analyst. When given a compliance audit task,
you must read the policy document carefully and output a JSON object matching the
GRCAction schema. Be precise with control IDs — use exact format like 'A.5.15' for
ISO 27001 and 'AC-2' for NIST 800-53."""

async def run_task(task_id: str) -> dict:
    async with GRCAuditEnv(base_url=ENV_BASE_URL) as env:
        obs = await env.reset(options={"task_id": task_id})

        for step in range(obs.max_steps if hasattr(obs, 'max_steps') else 20):
            user_prompt = f"""
Task: {obs.task_description}
Policy Document: {obs.policy_name}
Target Frameworks: {', '.join(obs.target_frameworks)}

Policy Text:
{obs.policy_text}

{"Available ISO 27001 controls: " + str(obs.available_iso_controls) if obs.available_iso_controls else ""}
{"Previous feedback: " + obs.grader_feedback if obs.grader_feedback else ""}

Output a JSON object with:
- task_id: "{task_id}"
- control_mappings: [{{section_id, iso_control_ids, nist_control_ids, soc2_criteria_ids}}]
- gaps: [{{control_id, framework, risk_level, gap_description, remediation}}]
- shared_controls: [{{policy_section_id, iso_control_id, nist_control_id, soc2_criteria_id}}]
"""
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            raw = json.loads(response.choices[0].message.content)
            action = GRCAction(task_id=task_id, **raw)
            obs = await env.step(action)

            print(f"  Step {step+1}: reward={obs.step_reward:.3f} cumulative={obs.cumulative_reward:.3f}")
            if obs.done:
                break

        return {"task_id": task_id, "score": obs.cumulative_reward}

async def main():
    results = []
    for task_id in TASK_IDS:
        print(f"\nRunning {task_id}...")
        r = await run_task(task_id)
        results.append(r)
        print(f"  Final score: {r['score']:.4f}")

    print("\n=== BASELINE SCORES ===")
    for r in results: print(f"  {r['task_id']}: {r['score']:.4f}")
    avg = sum(r['score'] for r in results) / len(results)
    print(f"  average:     {avg:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## SECTION 9 — DOCKER AND DEPLOYMENT

### 9.1 Dockerfile

```dockerfile
FROM ghcr.io/meta-pytorch/openenv-base:latest

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.2 server/requirements.txt

```
openenv-core>=0.2.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
scikit-learn>=1.3.0
scipy>=1.11.0
numpy>=1.24.0
```

Note: No heavy ML libraries required. BERTScore is intentionally omitted here because
the grader uses keyword matching and F1 — both deterministic, zero-latency, no GPU needed.
This guarantees < 20-minute runtime on 2-vCPU / 8GB RAM (the hard infrastructure limit).

### 9.3 Pre-Submission Validation Checklist

Run these in order before submitting:

```bash
# 1. Validate spec compliance
openenv validate --verbose

# 2. Build and test Docker
docker build -t grc-compliance-audit-env:latest .
docker run -p 8000:8000 grc-compliance-audit-env:latest

# 3. Run validation against local container
openenv validate --url http://localhost:8000

# 4. Run baseline inference (confirm < 20 min, all 3 tasks complete without error)
OPENAI_API_KEY=<key> MODEL_NAME=gpt-4o-mini API_BASE_URL=https://api.openai.com/v1 \
  ENV_BASE_URL=http://localhost:8000 python inference.py

# 5. Deploy to HuggingFace
openenv push --repo-id <your-hf-username>/grc-compliance-audit-env
```

---

## SECTION 10 — KNOWN FAILURE MODES (DO NOT DO THESE)

1. **Do NOT use LLM calls inside the grader as the primary scoring mechanism.**
   The primary grader is F1 + keyword matching — fully deterministic. LLM judge is
   only an optional overlay for remediation quality in task_hard, gated by OPENAI_API_KEY.
   Without it, the environment produces valid 0.0–1.0 scores.

2. **Do NOT bundle external framework documents (ISO 27001 PDF, NIST PDFs) in the repo.**
   These are copyrighted. Bundle only taxonomy JSON files with control IDs and names,
   which are factual data not protected by copyright. The policy fixtures are synthetic.

3. **Do NOT use sparse terminal rewards.** The judging criteria explicitly checks for
   "reward function that provides signal over the full trajectory." Binary end-of-episode
   reward = automatic deduction on Environment Design (20%).

4. **Do NOT exceed the 20-minute inference runtime limit** for 3 tasks.
   No GPU available. No BERTScore. No external network calls inside the grader.
   Use sklearn F1 and string/keyword matching only.

5. **Do NOT confuse ISO 27001:2013 control IDs with ISO 27001:2022.**
   The 2013 version had 114 controls across 14 domains (A.6 through A.18).
   The 2022 version has 93 controls across 4 themes (A.5 through A.8).
   All fixture annotations and taxonomy files must use 2022 IDs exclusively.

6. **Do NOT forget `inference.py` in the root directory.** Submissions missing this
   file fail the automated baseline validation check — immediate disqualification.

7. **Do NOT omit the `openenv.yaml` `tasks` section.** The pre-submission validator
   enumerates tasks, runs each grader, and verifies scores are in [0.0, 1.0].
   Missing tasks = validation failure.

---

## SECTION 11 — SCORING ESTIMATE AGAINST JUDGING RUBRIC

| Criterion | Weight | Score | Justification |
|---|---|---|---|
| Real-world utility | 30% | **29/30** | $65B GRC market, $210K/org audit cost, 81% ISO adoption, immediate enterprise deployment value. No equivalent RL env exists. |
| Task & grader quality | 25% | **23/25** | 3 tasks with calibrated difficulty, deterministic F1+keyword graders, severity-weighted gap scoring, hard task genuinely challenges frontier models on multi-framework cross-mapping. |
| Environment design | 20% | **18/20** | Dense per-section partial rewards, clean episode reset, 3 fixture types, typed Pydantic models, cross-framework bonus reward signal trains alignment across ISO/NIST/SOC2 simultaneously. |
| Code quality & spec | 15% | **13/15** | Full OpenEnv spec compliance, Pydantic typed models, Dockerfile, openenv validate passes, inference.py in root, all env vars documented. |
| Creativity & novelty | 10% | **9/10** | First GRC compliance audit environment in OpenEnv ecosystem. Multi-framework simultaneous auditing is novel. Severity-weighted gap reward with cross-framework bonus is original design. |
| **Estimated total** | | **~92/100** | |

---

## SECTION 12 — IMPLEMENTATION SEQUENCE (EXECUTE IN ORDER)

1. Read this entire document.
2. `pip install openenv-core scikit-learn pydantic fastapi uvicorn`
3. `openenv init grc_compliance_audit_env` — scaffold the project.
4. Replace `models.py` with the full implementation in Section 5.4.
5. Write `server/data/taxonomies/iso27001_controls.json` — all 93 controls, IDs + keywords.
6. Write `server/data/taxonomies/nist_80053_families.json` — 20 families + key sub-controls.
7. Write `server/data/taxonomies/soc2_tsc.json` — CC1–CC9, A, PI, C, P criteria.
8. Write the 3 fixture pairs (`.txt` + `.json`) for easy/medium/hard tasks per Section 6.
9. Write `server/graders/classification_grader.py` — macro-F1 using sklearn.
10. Write `server/graders/gap_grader.py` — severity-weighted precision/recall.
11. Write `server/graders/cross_framework_grader.py` — shared-control F1.
12. Write `server/tasks/easy_task.py`, `medium_task.py`, `hard_task.py` — task loaders.
13. Write `server/grc_environment.py` — `GRCEnvironment(Environment)` with full reward logic.
14. Write `server/app.py` — `create_app(GRCEnvironment, GRCAction, GRCObservation)`.
15. Write `openenv.yaml` per Section 5.3.
16. Write `server/Dockerfile` per Section 9.1.
17. Write `inference.py` per Section 8 — in root, not in server/.
18. Run `openenv validate` — fix any errors.
19. Run `docker build && docker run` — verify container starts and `/health` returns 200.
20. Run `inference.py` — confirm all 3 tasks complete with valid scores.
21. `openenv push` to HuggingFace Spaces.

---

*Document version 1.0 | April 2026 | OpenEnv Hackathon Round 1*
*Research sources: BusinessofGRC.com (2026), Secureframe (2025), ISO 27001:2022 Annex A,
NIST SP 800-53 Rev 5, AICPA Trust Services Criteria, NIST crosswalk documents*
