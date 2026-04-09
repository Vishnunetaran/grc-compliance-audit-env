"""
grc_environment.py — GRCEnvironment(Environment)

The core RL environment class. Implements the OpenEnv V1 spec:
    reset(options)  → GRCObservation
    step(action)    → GRCObservation
    state()         → GRCState

Reward rules (Section 7 of the context document):
    Rule 1 — Per-section partial reward (task_easy/medium):
              After each section classified → emit that section's F1 immediately.
    Rule 2 — Severity-weighted gap detection (task_medium/hard):
              Critical found: +0.25 | High: +0.15 | Medium: +0.08
              Critical missed: -0.20 | False alarm: -0.05
    Rule 3 — Efficiency bonus:
              If score ≥ 0.80 before max_steps → +0.10 on terminal step.
    Rule 4 — Anti-repetition penalty:
              Identical action as prev step → reward = -0.10, done = True.
    Rule 5 — Cross-framework bonus (task_hard):
              Each correctly identified shared control → +0.05.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def safe_score(x: float) -> float:
    x = float(x)
    if x <= 0.0:
        return 0.0001
    if x >= 1.0:
        return 0.9999
    return x

# OpenEnv base class — fall back to stub if not installed
try:
    from openenv.core.env_server.types import Environment
except ImportError:
    class Environment:  # type: ignore[no-redef]
        """Stub base class for local development without openenv-core."""
        pass

from grc_compliance_audit_env.models import (
    GRCAction,
    GRCObservation,
    GRCState,
    ControlMapping,
    GapItem,
    SharedControl,
)
from grc_compliance_audit_env.server.tasks.easy_task   import easy_task,   EasyTask
from grc_compliance_audit_env.server.tasks.medium_task import medium_task, MediumTask
from grc_compliance_audit_env.server.tasks.hard_task   import hard_task,   HardTask

from grc_compliance_audit_env.server.graders.classification_grader import (
    macro_f1_iso,
    macro_f1_nist,
    macro_f1_soc2,
    multi_framework_mapping_score,
    generate_classification_feedback,
)
from grc_compliance_audit_env.server.graders.gap_grader import (
    gap_detection_f1,
    severity_weighted_delta,
    description_quality_score,
    composite_gap_reward_medium,
    gap_score_hard,
    generate_gap_feedback,
)
from grc_compliance_audit_env.server.graders.cross_framework_grader import (
    cross_framework_score,
    cross_framework_bonus,
    generate_cross_framework_feedback,
)

# Task max_steps per task_id
_MAX_STEPS: Dict[str, int] = {
    "task_easy":   5,
    "task_medium": 10,
    "task_hard":   20,
}

# Efficiency bonus threshold and amount (Rule 3)
_EFFICIENCY_THRESHOLD: float = 0.80
_EFFICIENCY_BONUS:     float = 0.10

# Anti-repetition penalty (Rule 4)
_REPETITION_PENALTY:   float = -0.10


class GRCEnvironment(Environment):
    """
    GRC Compliance Audit RL Environment.

    Episode lifecycle:
        1. reset(options={"task_id": "task_easy"|"task_medium"|"task_hard"})
           → loads the fixture, resets state, returns initial GRCObservation.
        2. step(GRCAction) × N
           → grades the action, updates state, returns GRCObservation with reward.
        3. state() → GRCState with metadata (accessible any time).
    """

    def __init__(self) -> None:
        # Preload all task fixtures at startup
        easy_task.load()
        medium_task.load()
        hard_task.load()

        # Episode state (reset on each reset() call)
        self._episode_id:          str = ""
        self._task_id:             Optional[str] = None
        self._step_count:          int = 0
        self._accumulated_reward:  float = 0.0
        self._is_complete:         bool = False
        self._sections_processed:  int = 0
        self._score_history:       List[Dict] = []
        self._prev_action_hash:    Optional[str] = None

        # Active task reference
        self._task: Optional[Any] = None

    # ─────────────────────────────────────────────────────────────────────────
    # OpenEnv API — reset()
    # ─────────────────────────────────────────────────────────────────────────

    def reset(self, options: Optional[Dict] = None) -> GRCObservation:
        """Reset the environment and start a new episode.

        Args:
            options: Dict with optional keys:
                ``task_id`` (str): one of 'task_easy', 'task_medium', 'task_hard'.
                                   Defaults to 'task_easy'.

        Returns:
            Initial GRCObservation with full policy text and task instructions.
        """
        options = options or {}
        task_id = options.get("task_id", "task_easy")

        if task_id not in _MAX_STEPS:
            raise ValueError(
                f"Unknown task_id '{task_id}'. "
                f"Must be one of: {list(_MAX_STEPS.keys())}"
            )

        # Reset episode state
        self._episode_id         = str(uuid.uuid4())
        self._task_id            = task_id
        self._step_count         = 0
        self._accumulated_reward = 0.0
        self._is_complete        = False
        self._sections_processed = 0
        self._score_history      = []
        self._prev_action_hash   = None

        # Set active task
        if task_id == "task_easy":
            self._task = easy_task
        elif task_id == "task_medium":
            self._task = medium_task
        else:
            self._task = hard_task

        logger.info(
            "GRCEnvironment.reset(): episode=%s task=%s",
            self._episode_id, task_id,
        )

        return self._build_observation(
            step_reward=0.0,
            grader_feedback="Episode started. Read the policy and submit your analysis.",
            score_breakdown={},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # OpenEnv API — step()
    # ─────────────────────────────────────────────────────────────────────────

    def step(self, action: GRCAction) -> GRCObservation:
        """Process the agent's action and return a reward + observation.

        Args:
            action: GRCAction from the agent.

        Returns:
            GRCObservation with step_reward, cumulative_reward, grader_feedback.
        """
        # Rule 4 repetition check always runs, even on a just-completed episode
        # (we increment step_count first so it counts correctly)
        self._step_count += 1

        if self._is_complete:
            # Check repetition first before blocking
            action_hash_pre = self._hash_action(action)
            if self._prev_action_hash is not None and action_hash_pre == self._prev_action_hash:
                self._score_history.append({
                    "step": self._step_count,
                    "repetition_penalty": _REPETITION_PENALTY,
                    "step_reward": _REPETITION_PENALTY,
                })
                return self._build_observation(
                    step_reward=_REPETITION_PENALTY,
                    grader_feedback=(
                        "PENALTY: Identical action repeated after episode end. "
                        f"Reward: {_REPETITION_PENALTY:.2f}."
                    ),
                    score_breakdown={"repetition_penalty": _REPETITION_PENALTY},
                    done=True,
                )
            logger.warning("step() called after episode is already complete.")
            return self._build_observation(
                step_reward=0.0,
                grader_feedback="Episode already complete. Call reset() to start a new episode.",
                score_breakdown={},
                done=True,
            )

        # ── Rule 4: Anti-repetition check ───────────────────────────────────
        action_hash = self._hash_action(action)
        if self._prev_action_hash is not None and action_hash == self._prev_action_hash:
            logger.warning("Repeated action detected — applying penalty.")
            self._is_complete = True
            self._step_count += 0  # already incremented above
            self._score_history.append({
                "step": self._step_count,
                "repetition_penalty": _REPETITION_PENALTY,
                "step_reward": _REPETITION_PENALTY,
            })
            return self._build_observation(
                step_reward=_REPETITION_PENALTY,
                grader_feedback=(
                    "PENALTY: You submitted the exact same action as the previous step. "
                    f"Reward: {_REPETITION_PENALTY:.2f}. Episode terminated."
                ),
                score_breakdown={"repetition_penalty": _REPETITION_PENALTY},
                done=True,
            )
        self._prev_action_hash = action_hash

        # ── Route to task-specific grader ────────────────────────────────────
        if self._task_id == "task_easy":
            reward, breakdown, feedback = self._grade_easy(action)
        elif self._task_id == "task_medium":
            reward, breakdown, feedback = self._grade_medium(action)
        else:
            reward, breakdown, feedback = self._grade_hard(action)

        # ── Rule 3: Efficiency bonus ─────────────────────────────────────────
        max_steps = _MAX_STEPS[self._task_id]
        eff_bonus = 0.0
        if (
            reward >= _EFFICIENCY_THRESHOLD
            and self._step_count < max_steps
            and not self._is_complete
        ):
            eff_bonus = _EFFICIENCY_BONUS
            feedback += f"\n  ★ Efficiency bonus: +{eff_bonus:.2f} (high score before max steps)"
            breakdown["efficiency_bonus"] = eff_bonus

        step_reward = min(1.0, max(0.0, reward + eff_bonus))

        # ── Update episode state ─────────────────────────────────────────────
        self._accumulated_reward = min(
            1.0, self._accumulated_reward + step_reward * (1.0 / max_steps)
        )
        self._sections_processed = len(action.control_mappings)
        self._score_history.append({
            "step":  self._step_count,
            **{k: round(v, 4) for k, v in breakdown.items() if isinstance(v, float)},
            "step_reward": round(step_reward, 4),
        })

        # ── Terminal conditions ───────────────────────────────────────────────
        done = (
            self._is_complete
            or self._step_count >= max_steps
            or step_reward >= 0.95
        )
        self._is_complete = done

        return self._build_observation(
            step_reward=step_reward,
            grader_feedback=feedback,
            score_breakdown=breakdown,
            done=done,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # OpenEnv API — state()
    # ─────────────────────────────────────────────────────────────────────────

    def state(self) -> GRCState:
        """Return current episode-level state metadata."""
        return GRCState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            task_id=self._task_id,
            policy_id=self._task.policy_id if self._task else "",
            policy_name=self._task.policy_name if self._task else "",
            target_frameworks=self._task.target_frameworks if self._task else [],
            accumulated_reward=safe_score(round(self._accumulated_reward, 4)),
            max_steps=_MAX_STEPS.get(self._task_id, 20),
            is_complete=self._is_complete,
            sections_processed=self._sections_processed,
            score_history=self._score_history,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Task-specific graders
    # ─────────────────────────────────────────────────────────────────────────

    def _grade_easy(
        self, action: GRCAction
    ) -> tuple[float, Dict, str]:
        """Grade Task 1: ISO 27001 control classification via Macro-F1."""
        task: EasyTask = self._task
        gt_sections = task.get_ground_truth_sections()
        mappings = [m.model_dump() for m in action.control_mappings]

        macro, per_section = macro_f1_iso(mappings, gt_sections)
        feedback = generate_classification_feedback(per_section, macro, "iso27001")

        breakdown = {
            "macro_f1_iso": macro,
            **{f"{sid}_f1": v["f1"] for sid, v in per_section.items()},
        }
        return macro, breakdown, feedback

    def _grade_medium(
        self, action: GRCAction
    ) -> tuple[float, Dict, str]:
        """Grade Task 2: Dual-framework coverage + gap detection."""
        task: MediumTask = self._task
        gt_sections = task.get_ground_truth_sections()
        gt_gaps     = task.get_seeded_gaps()

        mappings   = [m.model_dump() for m in action.control_mappings]
        agent_gaps = [g.model_dump() for g in action.gaps]

        composite, breakdown = composite_gap_reward_medium(
            agent_coverage=mappings,
            gt_coverage=gt_sections,
            agent_gaps=agent_gaps,
            gt_gaps=gt_gaps,
        )
        feedback = generate_gap_feedback(breakdown, "task_medium")
        return composite, breakdown, feedback

    def _grade_hard(
        self, action: GRCAction
    ) -> tuple[float, Dict, str]:
        """Grade Task 3: Full 3-framework audit with cross-framework scoring."""
        task: HardTask = self._task
        gt_sections    = task.get_ground_truth_sections()
        gt_gaps        = task.get_seeded_gaps()
        gt_shared      = task.get_gt_shared_controls()

        mappings       = [m.model_dump() for m in action.control_mappings]
        agent_gaps     = [g.model_dump() for g in action.gaps]
        agent_shared   = [s.model_dump() for s in action.shared_controls]

        # Component 1: Mapping accuracy (35%)
        mapping_score, per_fw = multi_framework_mapping_score(
            mappings, gt_sections, ["iso27001", "nist_80053", "soc2"]
        )
        map_feedback = (
            f"Mapping — ISO:{per_fw.get('iso27001', 0):.3f}  "
            f"NIST:{per_fw.get('nist_80053', 0):.3f}  "
            f"SOC2:{per_fw.get('soc2', 0):.3f}  "
            f"Mean:{mapping_score:.3f}"
        )

        # Component 2: Gap detection (40%)
        gap_score, gap_breakdown = gap_score_hard(
            agent_gaps, gt_gaps, n_seeded=5
        )
        gap_feedback = generate_gap_feedback(gap_breakdown, "task_hard")

        # Component 3: Cross-framework quality (25%) + Rule 5 bonus
        cf_score, cf_detail = cross_framework_score(agent_shared, gt_shared)
        cf_bonus, n_correct = cross_framework_bonus(agent_shared, gt_shared)
        cf_feedback = generate_cross_framework_feedback(cf_detail)

        # Composite
        composite = round(
            0.35 * mapping_score
            + 0.40 * gap_score
            + 0.25 * cf_score
            + cf_bonus,          # Rule 5 bonus added directly
            4,
        )
        composite = min(1.0, composite)

        breakdown = {
            "mapping_score":           mapping_score,
            "gap_score":               gap_score,
            "cross_framework_score":   cf_score,
            "cross_framework_bonus":   cf_bonus,
            "composite_reward":        composite,
            **{f"mapping_{k}": v for k, v in per_fw.items()},
            **{f"gap_{k}": v for k, v in gap_breakdown.items()},
        }

        feedback = "\n".join([
            "=== Task 3 Grader ===",
            f"[1/3] {map_feedback}",
            f"[2/3] {gap_feedback}",
            f"[3/3] {cf_feedback}",
            f"─── Final composite reward: {composite:.4f}",
        ])

        return composite, breakdown, feedback

    # ─────────────────────────────────────────────────────────────────────────
    # Observation builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_observation(
        self,
        step_reward: float,
        grader_feedback: str,
        score_breakdown: Dict,
        done: bool = False,
    ) -> GRCObservation:
        """Construct a GRCObservation from current episode state.

        Note: `step_reward` on GRCObservation is constrained to [0.0, 1.0] by
        Pydantic (ge=0.0, le=1.0). Negative penalty values (Rule 4) are passed
        through the inherited `reward` field, which has no constraint.
        """
        task = self._task
        step_reward = safe_score(step_reward)

        obs = GRCObservation(
            # Inherited fields — raw value including negatives for penalty
            reward=step_reward,
            done=done,
            # Task identity
            task_id=self._task_id or "task_easy",
            task_description=task.task_description if task else "",
            # Policy
            policy_text=task.policy_text if task else "",
            policy_name=task.policy_name if task else "",
            total_sections=task.total_sections if task else 0,
            # Framework context
            target_frameworks=task.target_frameworks if task else [],
            available_iso_controls=(
                task.available_iso_controls
                if hasattr(task, "available_iso_controls") else []
            ),
            available_nist_families=(
                task.available_nist_families
                if hasattr(task, "available_nist_families") else []
            ),
            # Feedback — step_reward clamped to satisfy Pydantic ge=0.0 le=1.0
            # Agents should read obs.reward (raw) for the full signal
            step_reward=max(0.0, min(1.0, step_reward)),
            cumulative_reward=round(self._accumulated_reward, 4),
            grader_feedback=grader_feedback,
            score_breakdown={
                k: round(v, 4) for k, v in score_breakdown.items()
                if isinstance(v, float)
            },
            # Hint (easy task only)
            hint=task.hint if hasattr(task, "hint") and self._task_id == "task_easy" else "",
        )
        return obs

    # ─────────────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_action(action: GRCAction) -> str:
        """Create a stable hash of an action for repeat-detection (Rule 4).

        Only hashes the scored fields — not reasoning or episode metadata.
        """
        key_data = {
            "control_mappings": sorted(
                [
                    {
                        "section_id": m.section_id,
                        "iso": sorted(m.iso_control_ids),
                        "nist": sorted(m.nist_control_ids),
                        "soc2": sorted(m.soc2_criteria_ids),
                    }
                    for m in action.control_mappings
                ],
                key=lambda x: x["section_id"],
            ),
            "gaps": sorted(
                [g.control_id for g in action.gaps]
            ),
            "shared": sorted(
                [f"{s.iso_control_id}|{s.nist_control_id}|{s.soc2_criteria_id}"
                 for s in action.shared_controls]
            ),
        }
        return hashlib.sha256(
            json.dumps(key_data, sort_keys=True).encode()
        ).hexdigest()
