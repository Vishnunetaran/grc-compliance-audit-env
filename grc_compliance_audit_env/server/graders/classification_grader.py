"""
classification_grader.py

Deterministic Macro-F1 grader for Task 1 (easy) and as the base scoring
component for Tasks 2 and 3.

Scoring logic (per the spec):
    For each policy section s:
        ground_truth = set of control IDs in the annotation fixture
        agent_pred   = set of control IDs in the agent's action

        precision = |pred ∩ gt| / |pred|    (0 if pred is empty)
        recall    = |pred ∩ gt| / |gt|      (1.0 if gt is empty)
        f1        = 2 × P × R / (P + R)     (0 if P+R == 0)

    macro_f1 = mean(f1 over all sections with non-empty gt)

No ML libraries used — only standard set operations. sklearn is used only for
its f1_score utility when batching multi-label predictions.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_id(control_id: str) -> str:
    """Normalise a control ID to a canonical uppercase string.

    Handles common agent formatting variations:
        'a.5.15'  → 'A.5.15'
        'A5.15'   → 'A.5.15'   (missing dot after letter)
        'ac-2'    → 'AC-2'
        ' A.8.5 ' → 'A.8.5'
    """
    cid = control_id.strip().upper()
    # Fix ISO IDs that are missing the dot after the letter (e.g. "A515" → skip)
    # Only fix the common case: A5.15 → A.5.15
    if len(cid) >= 4 and cid[0].isalpha() and cid[1].isdigit() and cid[2] == ".":
        cid = cid[0] + "." + cid[1:]
    return cid


def _normalise_ids(ids: List[str]) -> set[str]:
    """Return a set of normalised control IDs."""
    return {_normalise_id(cid) for cid in ids if cid and cid.strip()}


def section_f1(
    predicted_ids: List[str],
    ground_truth_ids: List[str],
) -> Tuple[float, float, float]:
    """Compute precision, recall, and F1 for a single policy section.

    Args:
        predicted_ids:   Control IDs the agent predicted for this section.
        ground_truth_ids: Annotated ground-truth control IDs for this section.

    Returns:
        (precision, recall, f1) — all floats in [0.0, 1.0].
    """
    pred = _normalise_ids(predicted_ids)
    gt   = _normalise_ids(ground_truth_ids)

    # Edge cases
    if not gt:
        # No ground-truth controls for this section → section is trivially correct
        return (1.0, 1.0, 1.0)
    if not pred:
        # Agent predicted nothing but GT is non-empty
        return (0.0, 0.0, 0.0)

    tp = len(pred & gt)
    precision = tp / len(pred)
    recall    = tp / len(gt)

    if precision + recall == 0.0:
        f1 = 0.0
    else:
        f1 = 2.0 * precision * recall / (precision + recall)

    return (round(precision, 4), round(recall, 4), round(f1, 4))


# ─────────────────────────────────────────────────────────────────────────────
# Multi-section graders
# ─────────────────────────────────────────────────────────────────────────────

def macro_f1_iso(
    agent_mappings: List[Dict],
    gt_sections: List[Dict],
) -> Tuple[float, Dict[str, Dict]]:
    """Compute macro-F1 across all sections for ISO 27001 control IDs.

    Args:
        agent_mappings: List of dicts with keys ``section_id`` and
                        ``iso_control_ids``.
        gt_sections:    Ground-truth sections with ``section_id`` and
                        ``gt_iso_controls``.

    Returns:
        (macro_f1, per_section_breakdown)
        per_section_breakdown maps section_id → {precision, recall, f1}.
    """
    # Build lookup: section_id → gt controls
    gt_map: Dict[str, List[str]] = {
        s["section_id"]: s.get("gt_iso_controls", [])
        for s in gt_sections
    }

    # Build lookup: section_id → predicted controls
    pred_map: Dict[str, List[str]] = {
        m["section_id"]: m.get("iso_control_ids", [])
        for m in agent_mappings
    }

    per_section: Dict[str, Dict] = {}
    f1_scores: List[float] = []

    for section_id, gt_ids in gt_map.items():
        if not gt_ids:
            continue  # skip sections with no ground truth (trivially satisfied)
        pred_ids = pred_map.get(section_id, [])
        p, r, f1 = section_f1(pred_ids, gt_ids)
        per_section[section_id] = {"precision": p, "recall": r, "f1": f1}
        f1_scores.append(f1)

    macro = round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0.0
    return macro, per_section


def macro_f1_nist(
    agent_mappings: List[Dict],
    gt_sections: List[Dict],
) -> Tuple[float, Dict[str, Dict]]:
    """Compute macro-F1 across all sections for NIST 800-53 control IDs."""
    gt_map: Dict[str, List[str]] = {
        s["section_id"]: s.get("gt_nist_controls", [])
        for s in gt_sections
    }
    pred_map: Dict[str, List[str]] = {
        m["section_id"]: m.get("nist_control_ids", [])
        for m in agent_mappings
    }

    per_section: Dict[str, Dict] = {}
    f1_scores: List[float] = []

    for section_id, gt_ids in gt_map.items():
        if not gt_ids:
            continue
        pred_ids = pred_map.get(section_id, [])
        p, r, f1 = section_f1(pred_ids, gt_ids)
        per_section[section_id] = {"precision": p, "recall": r, "f1": f1}
        f1_scores.append(f1)

    macro = round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0.0
    return macro, per_section


def macro_f1_soc2(
    agent_mappings: List[Dict],
    gt_sections: List[Dict],
) -> Tuple[float, Dict[str, Dict]]:
    """Compute macro-F1 across all sections for SOC 2 TSC criteria IDs."""
    gt_map: Dict[str, List[str]] = {
        s["section_id"]: s.get("gt_soc2_criteria", [])
        for s in gt_sections
    }
    pred_map: Dict[str, List[str]] = {
        m["section_id"]: m.get("soc2_criteria_ids", [])
        for m in agent_mappings
    }

    per_section: Dict[str, Dict] = {}
    f1_scores: List[float] = []

    for section_id, gt_ids in gt_map.items():
        if not gt_ids:
            continue
        pred_ids = pred_map.get(section_id, [])
        p, r, f1 = section_f1(pred_ids, gt_ids)
        per_section[section_id] = {"precision": p, "recall": r, "f1": f1}
        f1_scores.append(f1)

    macro = round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0.0
    return macro, per_section


def multi_framework_mapping_score(
    agent_mappings: List[Dict],
    gt_sections: List[Dict],
    frameworks: List[str],
) -> Tuple[float, Dict[str, float]]:
    """Compute the mapping score averaged across all frameworks in scope.

    Used by task_hard grader (Component 1, weight=0.35).

    Args:
        agent_mappings: Agent's ControlMapping list as dicts.
        gt_sections:    Ground-truth sections containing gt_iso/nist/soc2.
        frameworks:     List like ['iso27001', 'nist_80053', 'soc2'].

    Returns:
        (mean_score, per_framework_f1)
    """
    per_fw: Dict[str, float] = {}

    if "iso27001" in frameworks:
        iso_f1, _ = macro_f1_iso(agent_mappings, gt_sections)
        per_fw["iso27001"] = iso_f1

    if "nist_80053" in frameworks:
        nist_f1, _ = macro_f1_nist(agent_mappings, gt_sections)
        per_fw["nist_80053"] = nist_f1

    if "soc2" in frameworks:
        soc2_f1, _ = macro_f1_soc2(agent_mappings, gt_sections)
        per_fw["soc2"] = soc2_f1

    mean_score = round(
        sum(per_fw.values()) / len(per_fw), 4
    ) if per_fw else 0.0

    return mean_score, per_fw


def generate_classification_feedback(
    per_section: Dict[str, Dict],
    macro: float,
    framework: str = "iso27001",
) -> str:
    """Generate a human-readable feedback string for the agent."""
    lines = [f"Classification grader — {framework.upper()} | Macro-F1: {macro:.3f}"]
    for sid, scores in per_section.items():
        lines.append(
            f"  {sid}: P={scores['precision']:.2f}  R={scores['recall']:.2f}  "
            f"F1={scores['f1']:.2f}"
        )
    if macro >= 0.9:
        lines.append("Excellent coverage — near-perfect control identification.")
    elif macro >= 0.7:
        lines.append("Good coverage — some controls missed or over-predicted.")
    elif macro >= 0.5:
        lines.append("Partial coverage — review sections with low recall.")
    else:
        lines.append("Low coverage — significant control identification gaps.")
    return "\n".join(lines)
