"""
cross_framework_grader.py

Grader for the cross-framework shared-control dividend (Task 3 — hard, Component 3).

Scoring logic (per spec Section 4, Task 3):
    For each claimed shared control (iso_id, nist_id, soc2_criteria_id, section_id):
        It is a TRUE POSITIVE if ALL of:
            (a) The triple (iso_id, nist_id, soc2_criteria_id) exists in the
                ground-truth shared-control mappings.
            (b) The policy_section_id matches (or the section is among the
                valid sections for that topic — we allow loose matching here
                because the agent shouldn't be penalised for citing a parent
                section that covers the control).

    shared_control_precision = |agent_shared ∩ gt_shared| / |agent_shared|
    shared_control_recall    = |agent_shared ∩ gt_shared| / |gt_shared|
    shared_f1                = 2 × P × R / (P + R)

Cross-framework per-correctly-identified shared control: +0.05 bonus (Rule 5).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _norm(cid: str) -> str:
    """Normalise a control ID for comparison."""
    cid = cid.strip().upper()
    if len(cid) >= 4 and cid[0].isalpha() and cid[1].isdigit() and cid[2] == ".":
        cid = cid[0] + "." + cid[1:]
    return cid


def _shared_control_key(iso: str, nist: str, soc2: str) -> str:
    """Create a canonical sorted tuple key for a shared control triple."""
    return f"{_norm(iso)}|{_norm(nist)}|{_norm(soc2)}"


def _build_gt_set(gt_shared_controls: List[Dict]) -> Dict[str, Dict]:
    """Build keyed lookup from ground-truth shared control list.

    Key = 'ISO_ID|NIST_ID|SOC2_ID'
    Value = full ground-truth dict (includes policy_section_id).
    """
    lookup: Dict[str, Dict] = {}
    for sc in gt_shared_controls:
        key = _shared_control_key(
            sc.get("iso_control_id", ""),
            sc.get("nist_control_id", ""),
            sc.get("soc2_criteria_id", ""),
        )
        lookup[key] = sc
    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# Core shared-control F1
# ─────────────────────────────────────────────────────────────────────────────

def cross_framework_f1(
    agent_shared: List[Dict],
    gt_shared: List[Dict],
) -> Tuple[float, float, float, Dict]:
    """Compute precision, recall, F1 for shared-control identification.

    The agent's SharedControl dicts are matched against ground-truth triples.
    Section matching is soft — we accept the correct triple regardless of
    whether the section_id exactly matches (to avoid penalising reasonable
    section re-labelling).

    Args:
        agent_shared: List of agent SharedControl dicts.
        gt_shared:    Ground-truth shared controls from the fixture.

    Returns:
        (precision, recall, f1, detail)
    """
    gt_lookup = _build_gt_set(gt_shared)

    if not gt_lookup:
        return 1.0, 1.0, 1.0, {"message": "No gt shared controls."}

    if not agent_shared:
        return 0.0, 0.0, 0.0, {
            "true_positives": [],
            "false_positives": [],
            "false_negatives": list(gt_lookup.keys()),
        }

    # De-duplicate agent submissions (same triple counted once)
    agent_keys_seen: set[str] = set()
    agent_keys: list[str] = []

    for sc in agent_shared:
        key = _shared_control_key(
            sc.get("iso_control_id", ""),
            sc.get("nist_control_id", ""),
            sc.get("soc2_criteria_id", ""),
        )
        if key and key not in agent_keys_seen:
            agent_keys_seen.add(key)
            agent_keys.append(key)

    gt_key_set = set(gt_lookup.keys())
    agent_key_set = set(agent_keys)

    tp = agent_key_set & gt_key_set
    fp = agent_key_set - gt_key_set
    fn = gt_key_set   - agent_key_set

    precision = round(len(tp) / len(agent_key_set), 4) if agent_key_set else 0.0
    recall    = round(len(tp) / len(gt_key_set),    4) if gt_key_set else 1.0
    f1 = (
        round(2.0 * precision * recall / (precision + recall), 4)
        if precision + recall > 0.0 else 0.0
    )

    return precision, recall, f1, {
        "true_positives":  sorted(tp),
        "false_positives": sorted(fp),
        "false_negatives": sorted(fn),
        "n_agent_submitted": len(agent_key_set),
        "n_gt_shared":       len(gt_key_set),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-shared-control bonus (Rule 5)
# ─────────────────────────────────────────────────────────────────────────────

def cross_framework_bonus(
    agent_shared: List[Dict],
    gt_shared: List[Dict],
    bonus_per_control: float = 0.05,
) -> Tuple[float, int]:
    """Compute the flat bonus for correctly identified shared controls.

    Each correctly identified shared control earns +0.05 bonus (Rule 5).

    Returns:
        (total_bonus, n_correct)
    """
    gt_lookup = _build_gt_set(gt_shared)
    n_correct = 0

    seen: set[str] = set()
    for sc in agent_shared:
        key = _shared_control_key(
            sc.get("iso_control_id", ""),
            sc.get("nist_control_id", ""),
            sc.get("soc2_criteria_id", ""),
        )
        if key in gt_lookup and key not in seen:
            n_correct += 1
            seen.add(key)

    return round(n_correct * bonus_per_control, 4), n_correct


# ─────────────────────────────────────────────────────────────────────────────
# Composite scoring for task_hard Component 3
# ─────────────────────────────────────────────────────────────────────────────

def cross_framework_score(
    agent_shared: List[Dict],
    gt_shared: List[Dict],
) -> Tuple[float, Dict]:
    """Compute the full cross-framework quality score (Component 3, weight=0.25).

    Uses F1 as the primary score.  Also returns the per-control bonus separately
    so the environment can add it on top of the composite.

    Returns:
        (cross_framework_f1_score, detail)
    """
    precision, recall, f1, det = cross_framework_f1(agent_shared, gt_shared)
    bonus, n_correct = cross_framework_bonus(agent_shared, gt_shared)

    detail: Dict = {
        "precision":      precision,
        "recall":         recall,
        "f1":             f1,
        "cross_fw_bonus": bonus,
        "n_correct_shared_controls": n_correct,
        **det,
    }
    return f1, detail


# ─────────────────────────────────────────────────────────────────────────────
# Feedback generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_cross_framework_feedback(detail: Dict) -> str:
    """Human-readable feedback for the cross-framework grader."""
    lines = ["Cross-Framework Grader"]
    lines.append(
        f"  Shared Control F1: {detail.get('f1', 0.0):.3f}  "
        f"(P={detail.get('precision', 0.0):.2f}  R={detail.get('recall', 0.0):.2f})"
    )
    lines.append(
        f"  Correct shared controls : {detail.get('n_correct_shared_controls', 0)}"
    )
    lines.append(
        f"  Cross-framework bonus   : +{detail.get('cross_fw_bonus', 0.0):.3f}"
    )

    tp = detail.get("true_positives", [])
    fp = detail.get("false_positives", [])
    fn = detail.get("false_negatives", [])

    if tp:
        summary = [k.split("|")[0] + "↔" + k.split("|")[1] for k in tp[:4]]
        lines.append(f"  ✓ Correct triples : {', '.join(summary)}")
    if fp:
        lines.append(f"  ✗ False triples   : {len(fp)} spurious shared controls")
    if fn:
        missed = [k.split("|")[0] + "↔" + k.split("|")[1] for k in fn[:4]]
        lines.append(f"  ✗ Missed triples  : {', '.join(missed)}")

    return "\n".join(lines)
