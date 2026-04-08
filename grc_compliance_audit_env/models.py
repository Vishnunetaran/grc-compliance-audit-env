"""
models.py — Pydantic data models for the GRC Compliance Audit OpenEnv environment.

Defines Action, Observation, and State types that inherit from the OpenEnv
base classes. All sub-models use strict typing with Python 3.10+ type hints.

Framework coverage:
  - ISO 27001:2022 (Annex A controls A.5–A.8)
  - NIST SP 800-53 Rev 5 (20 control families)
  - SOC 2 Trust Services Criteria (CC, A, PI, C, P)
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# OpenEnv base class imports
# We import from openenv.core; if not available at dev-time, we fall back to
# plain BaseModel stubs so the file can be validated standalone.
# ---------------------------------------------------------------------------
try:
    from openenv.core.env_server.types import (
        Action as _ActionBase,
        Observation as _ObservationBase,
        State as _StateBase,
    )
except ImportError:
    # Fallback stubs for local development / CI without openenv-core
    class _ActionBase(BaseModel):  # type: ignore[no-redef]
        """Stub for openenv Action base class."""
        pass

    class _ObservationBase(BaseModel):  # type: ignore[no-redef]
        """Stub for openenv Observation base class."""
        reward: float = 0.0
        done: bool = False

    class _StateBase(BaseModel):  # type: ignore[no-redef]
        """Stub for openenv State base class."""
        episode_id: str = ""
        step_count: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# Literal type aliases
# ═══════════════════════════════════════════════════════════════════════════════

Framework = Literal["iso27001", "nist_80053", "soc2"]
"""Supported compliance frameworks."""

RiskLevel = Literal["critical", "high", "medium", "low"]
"""Severity classification for compliance gaps."""

TaskId = Literal["task_easy", "task_medium", "task_hard"]
"""Identifiers for the three difficulty-tiered tasks."""


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models (reusable across Action / Observation)
# ═══════════════════════════════════════════════════════════════════════════════

class ControlMapping(BaseModel):
    """
    Maps a single policy section to framework control IDs.

    Used by the agent in every task to declare which controls a given
    policy section addresses.  Each field is optional so that the agent
    can omit frameworks not in scope (e.g., task_easy only needs
    ``iso_control_ids``).
    """

    section_id: str = Field(
        ...,
        description="Policy section identifier, e.g. 'section_1' or 'access_control'",
    )
    iso_control_ids: List[str] = Field(
        default_factory=list,
        description="ISO 27001:2022 Annex A control IDs, e.g. ['A.5.15', 'A.8.3']",
    )
    nist_control_ids: List[str] = Field(
        default_factory=list,
        description="NIST 800-53 Rev 5 control IDs, e.g. ['AC-1', 'AC-3', 'IA-2']",
    )
    soc2_criteria_ids: List[str] = Field(
        default_factory=list,
        description="SOC 2 TSC criteria IDs, e.g. ['CC6.1', 'CC6.3']",
    )


class GapItem(BaseModel):
    """
    Represents a single identified compliance gap.

    The agent produces one ``GapItem`` for every control it believes is
    *not* addressed by the policy.  The grader compares these against
    the pre-seeded ground-truth gaps.
    """

    control_id: str = Field(
        ...,
        description="Framework control ID, e.g. 'A.8.5' or 'IA-2' or 'CC6.6'",
    )
    framework: Framework = Field(
        ...,
        description="Which framework this gap belongs to",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Severity of this compliance gap",
    )
    gap_description: str = Field(
        ...,
        description="One-sentence description of what is missing in the policy",
    )
    affected_section: Optional[str] = Field(
        default=None,
        description="Which policy section should be updated to close this gap",
    )
    remediation: Optional[str] = Field(
        default=None,
        description="Suggested policy text addition or amendment to close the gap",
    )


class SharedControl(BaseModel):
    """
    A control satisfied across multiple frameworks by the same policy text.

    Used only in ``task_hard``.  Identifies the *shared-control dividend*
    where a single policy section simultaneously satisfies ISO 27001,
    NIST 800-53, and SOC 2 requirements.
    """

    policy_section_id: str = Field(
        ...,
        description="The policy section that satisfies all three framework controls",
    )
    iso_control_id: str = Field(
        ...,
        description="Equivalent ISO 27001:2022 control ID",
    )
    nist_control_id: str = Field(
        ...,
        description="Equivalent NIST 800-53 Rev 5 control ID",
    )
    soc2_criteria_id: str = Field(
        ...,
        description="Equivalent SOC 2 TSC criterion ID",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GRCAction — what the agent sends to the environment
# ═══════════════════════════════════════════════════════════════════════════════

class GRCAction(_ActionBase):
    """
    The agent's response in a GRC compliance audit episode.

    Field requirements per task:
    ┌─────────────────────┬───────────┬────────────┬───────────┐
    │ Field               │ task_easy │ task_medium │ task_hard │
    ├─────────────────────┼───────────┼────────────┼───────────┤
    │ control_mappings    │ REQUIRED  │ REQUIRED   │ REQUIRED  │
    │ gaps                │ -         │ REQUIRED   │ REQUIRED  │
    │ shared_controls     │ -         │ -          │ REQUIRED  │
    │ executive_summary   │ -         │ -          │ REQUIRED  │
    └─────────────────────┴───────────┴────────────┴───────────┘

    The ``reasoning`` field is a free-text scratchpad — not scored but
    logged for analysis and useful for chain-of-thought prompting.
    """

    task_id: TaskId = Field(
        ...,
        description="Which task this action responds to",
    )
    reasoning: str = Field(
        default="",
        description="Agent's chain-of-thought or working notes (not scored)",
    )

    # ------------------------------------------------------------------
    # Task 1 / 2 / 3 — always required
    # ------------------------------------------------------------------
    control_mappings: List[ControlMapping] = Field(
        default_factory=list,
        description="One ControlMapping per policy section, in document order",
    )

    # ------------------------------------------------------------------
    # Task 2 / 3 — required for gap analysis
    # ------------------------------------------------------------------
    gaps: List[GapItem] = Field(
        default_factory=list,
        description="Identified compliance gaps with control IDs and remediation",
    )

    # ------------------------------------------------------------------
    # Task 3 only — cross-framework analysis
    # ------------------------------------------------------------------
    shared_controls: List[SharedControl] = Field(
        default_factory=list,
        description="[task_hard] Controls satisfied across all three frameworks",
    )
    executive_summary: str = Field(
        default="",
        description="[task_hard] 2-3 sentence plain-English audit summary",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GRCObservation — what the environment returns to the agent
# ═══════════════════════════════════════════════════════════════════════════════

class GRCObservation(_ObservationBase):
    """
    What the environment returns to the agent after ``reset()`` or ``step()``.

    On ``reset()``:
        Populated with the full policy text, task description, available
        frameworks, and optional hints.

    On ``step()``:
        Updated with grader feedback, partial score, and cumulative reward.

    ``reward`` (float, 0.0–1.0) and ``done`` (bool) are inherited from
    the OpenEnv Observation base class.
    """

    task_id: TaskId = Field(
        ...,
        description="Active task identifier",
    )
    task_description: str = Field(
        ...,
        description="Human-readable instructions for the current task",
    )

    # -- Policy document ------------------------------------------------
    policy_text: str = Field(
        ...,
        description="Full text of the policy to audit, with section headers",
    )
    policy_name: str = Field(
        ...,
        description="Name of the policy document, e.g. 'Access Control Policy v1.0'",
    )
    total_sections: int = Field(
        ...,
        description="Number of numbered sections in the policy",
    )

    # -- Framework context ----------------------------------------------
    target_frameworks: List[Framework] = Field(
        ...,
        description="Which frameworks to audit against for this episode",
    )
    available_iso_controls: List[str] = Field(
        default_factory=list,
        description="[task_easy] Subset of ISO 27001 IDs relevant to this policy type",
    )
    available_nist_families: List[str] = Field(
        default_factory=list,
        description="[task_medium/hard] NIST family abbreviations in scope",
    )

    # -- Feedback after each step ---------------------------------------
    step_reward: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Reward earned in this step",
    )
    cumulative_reward: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Total reward accumulated this episode",
    )
    grader_feedback: str = Field(
        default="",
        description="Human-readable feedback explaining the step score",
    )
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Score components: mapping_f1, gap_f1, description_score, etc.",
    )

    # -- Hints ----------------------------------------------------------
    hint: str = Field(
        default="",
        description="Optional hint for task_easy only",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GRCState — episode-level metadata (accessible via state())
# ═══════════════════════════════════════════════════════════════════════════════

class GRCState(_StateBase):
    """
    Episode-level metadata accessible via the ``state()`` API.

    Not sent on every step — only available on explicit request.
    Inherits ``episode_id`` (str) and ``step_count`` (int) from the
    OpenEnv State base class.
    """

    task_id: Optional[TaskId] = Field(
        default=None,
        description="Active task identifier",
    )
    policy_id: str = Field(
        default="",
        description="Fixture file identifier, e.g. 'easy_001'",
    )
    policy_name: str = Field(
        default="",
        description="Human-readable policy name",
    )
    target_frameworks: List[str] = Field(
        default_factory=list,
        description="Frameworks in scope for this episode",
    )
    accumulated_reward: float = Field(
        default=0.0,
        description="Cumulative reward over the episode",
    )
    max_steps: int = Field(
        default=20,
        description="Maximum allowed steps for the current task",
    )
    is_complete: bool = Field(
        default=False,
        description="Whether the episode has terminated",
    )
    sections_processed: int = Field(
        default=0,
        description="Number of policy sections the agent has processed so far",
    )
    score_history: List[Dict[str, float]] = Field(
        default_factory=list,
        description="Per-step score breakdown history",
    )
