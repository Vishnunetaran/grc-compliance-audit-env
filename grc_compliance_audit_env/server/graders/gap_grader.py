"""
gap_grader.py

Deterministic gap detection grader for Task 2 (medium) and Task 3 (hard).

Scoring logic (per the spec):
    gap_precision = |agent_gaps ∩ gt_gaps| / |agent_gaps|
    gap_recall    = |agent_gaps ∩ gt_gaps| / |gt_gaps|
    gap_f1        = 2 × P × R / (P + R)

Severity-weighted bonus/penalty (Rule 2 from Section 7):
    Critical gap found correctly : +0.25
    High gap found correctly     : +0.15
    Medium gap found correctly   : +0.08
    Critical gap MISSED          : -0.20
    High gap MISSED              : -0.10 (derived from spec)
    False alarm (spurious gap)   : -0.05

Description quality check (Component 3, weight=0.20 in task_medium):
    For each gap item the agent produces, check:
        (a) The control_id is present in gap_description (exact or normalised).
        (b) At least one keyword from the control's remediation_keywords list
            appears in gap_description (case-insensitive substring match).
    description_score = fraction of gap items passing both checks.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Severity reward / penalty tables (from spec Section 7, Rule 2)
_GAP_FOUND_REWARD: Dict[str, float] = {
    "critical": 0.25,
    "high":     0.15,
    "medium":   0.08,
    "low":      0.05,
}

_GAP_MISSED_PENALTY: Dict[str, float] = {
    "critical": -0.20,
    "high":     -0.10,
    "medium":   -0.05,
    "low":      -0.02,
}

_FALSE_ALARM_PENALTY: float = -0.05


# ─────────────────────────────────────────────────────────────────────────────
# Helper: normalise control IDs
# ─────────────────────────────────────────────────────────────────────────────

def _norm(cid: str) -> str:
    """Normalise a control ID for comparison."""
    cid = cid.strip().upper()
    # Fix missing dot: A5.15 → A.5.15
    if len(cid) >= 4 and cid[0].isalpha() and cid[1].isdigit() and cid[2] == ".":
        cid = cid[0] + "." + cid[1:]
    return cid


def _extract_gap_ids(gaps: List[Dict]) -> set[str]:
    """Extract normalised control_id set from a list of gap dicts."""
    return {_norm(g["control_id"]) for g in gaps if g.get("control_id")}


# ─────────────────────────────────────────────────────────────────────────────
# Core gap detection scoring
# ─────────────────────────────────────────────────────────────────────────────

def gap_detection_f1(
    agent_gaps: List[Dict],
    gt_gaps: List[Dict],
) -> Tuple[float, float, float, Dict]:
    """Compute precision, recall and F1 for gap detection.

    Args:
        agent_gaps: Agent-reported gap items with ``control_id`` field.
        gt_gaps:    Ground-truth seeded gaps with ``control_id`` field.

    Returns:
        (precision, recall, f1, details)
    """
    agent_ids = _extract_gap_ids(agent_gaps)
    gt_ids    = _extract_gap_ids(gt_gaps)

    if not gt_ids:
        return 1.0, 1.0, 1.0, {"message": "No seeded gaps to find."}

    if not agent_ids:
        return 0.0, 0.0, 0.0, {
            "true_positives": [],
            "false_positives": [],
            "false_negatives": list(gt_ids),
        }

    tp_ids = agent_ids & gt_ids
    fp_ids = agent_ids - gt_ids
    fn_ids = gt_ids   - agent_ids

    precision = round(len(tp_ids) / len(agent_ids), 4)
    recall    = round(len(tp_ids) / len(gt_ids),    4)
    f1 = (
        round(2.0 * precision * recall / (precision + recall), 4)
        if precision + recall > 0.0 else 0.0
    )

    return precision, recall, f1, {
        "true_positives":  sorted(tp_ids),
        "false_positives": sorted(fp_ids),
        "false_negatives": sorted(fn_ids),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Severity-weighted gap bonus/penalty
# ─────────────────────────────────────────────────────────────────────────────

def severity_weighted_delta(
    agent_gaps: List[Dict],
    gt_gaps: List[Dict],
) -> Tuple[float, Dict]:
    """Compute the net severity-weighted bonus/penalty.

    Correct gaps found → positive reward scaled by risk_level.
    Missed critical/high gaps → penalty.
    Spurious gaps not in GT → false-alarm penalty.

    Returns:
        (raw_delta, breakdown)  raw_delta can be positive or negative.
    """
    # Build GT lookup: control_id → gap metadata
    gt_lookup: Dict[str, Dict] = {
        _norm(g["control_id"]): g
        for g in gt_gaps
    }

    found    = 0.0
    penalties = 0.0
    breakdown: Dict = {
        "correct_gaps": [],
        "missed_gaps":  [],
        "false_alarms": [],
    }

    agent_ids_seen: set[str] = set()

    for ag in agent_gaps:
        cid = _norm(ag.get("control_id", ""))
        if not cid:
            continue
        agent_ids_seen.add(cid)

        if cid in gt_lookup:
            risk = gt_lookup[cid].get("risk_level", "medium")
            delta = _GAP_FOUND_REWARD.get(risk, 0.05)
            found += delta
            breakdown["correct_gaps"].append(
                {"control_id": cid, "risk_level": risk, "reward": delta}
            )
        else:
            penalties += _FALSE_ALARM_PENALTY
            breakdown["false_alarms"].append(
                {"control_id": cid, "penalty": _FALSE_ALARM_PENALTY}
            )

    # Penalise missed gaps
    for cid, gt_gap in gt_lookup.items():
        if cid not in agent_ids_seen:
            risk = gt_gap.get("risk_level", "medium")
            pen = _GAP_MISSED_PENALTY.get(risk, -0.02)
            penalties += pen
            breakdown["missed_gaps"].append(
                {"control_id": cid, "risk_level": risk, "penalty": pen}
            )

    raw_delta = round(found + penalties, 4)
    return raw_delta, breakdown


# ─────────────────────────────────────────────────────────────────────────────
# Severity accuracy (task_hard: gap_score sub-component)
# ─────────────────────────────────────────────────────────────────────────────

def severity_accuracy(
    agent_gaps: List[Dict],
    gt_gaps: List[Dict],
) -> float:
    """Fraction of found gaps whose risk_level matches ground truth.

    Only counts gaps that are true positives (agent found AND in GT).
    """
    gt_lookup: Dict[str, str] = {
        _norm(g["control_id"]): g.get("risk_level", "medium").lower()
        for g in gt_gaps
    }

    correct = 0
    total   = 0

    for ag in agent_gaps:
        cid = _norm(ag.get("control_id", ""))
        if cid in gt_lookup:
            total += 1
            agent_risk = ag.get("risk_level", "").lower()
            if agent_risk == gt_lookup[cid]:
                correct += 1

    return round(correct / total, 4) if total > 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Description quality scoring (keyword check)
# ─────────────────────────────────────────────────────────────────────────────

def description_quality_score(
    agent_gaps: List[Dict],
    gt_gaps: List[Dict],
) -> Tuple[float, List[Dict]]:
    """Keyword-match check for gap description quality.

    For each gap item the agent produces:
        Pass if:
            (a) control_id appears in gap_description (normalised, case-insensitive), OR
            (b) at least one keyword from the GT remediation_keywords list
                appears in gap_description (case-insensitive substring).

    Returns:
        (description_score, per_gap_results)
    """
    # Build GT lookup: control_id → remediation_keywords
    gt_lookup: Dict[str, List[str]] = {
        _norm(g["control_id"]): [k.lower() for k in g.get("remediation_keywords", [])]
        for g in gt_gaps
    }

    per_gap: List[Dict] = []
    passed = 0
    total  = 0

    for ag in agent_gaps:
        cid  = _norm(ag.get("control_id", ""))
        desc = (ag.get("gap_description", "") + " " +
                ag.get("remediation", "")).lower()

        if cid not in gt_lookup:
            # Spurious gap — skip description check (already penalised)
            continue

        total += 1
        keywords = gt_lookup[cid]

        # Check (a): control ID mentioned in description
        id_mentioned = cid.lower() in desc or ag.get("control_id", "").lower() in desc

        # Check (b): at least one keyword appears
        kw_matched: List[str] = [kw for kw in keywords if kw in desc]
        keyword_hit = len(kw_matched) > 0

        passes = id_mentioned or keyword_hit

        if passes:
            passed += 1

        per_gap.append({
            "control_id":    cid,
            "id_mentioned":  id_mentioned,
            "keywords_hit":  kw_matched[:3],
            "passes":        passes,
        })

    score = round(passed / total, 4) if total > 0 else 0.0
    return score, per_gap


# ─────────────────────────────────────────────────────────────────────────────
# Composite gap reward (task_medium)
# ─────────────────────────────────────────────────────────────────────────────

def composite_gap_reward_medium(
    agent_coverage: List[Dict],
    gt_coverage: List[Dict],
    agent_gaps: List[Dict],
    gt_gaps: List[Dict],
) -> Tuple[float, Dict]:
    """Compute the Task 2 composite reward.

    Components:
        40% — Coverage F1 (how well the agent mapped existing controls)
        40% — Gap F1 (how accurately the agent found the seeded gaps)
        20% — Description quality (keyword-match heuristic)

    Args:
        agent_coverage: agent_mappings flattened to coverage dicts
        gt_coverage:    ground-truth coverage dicts from the fixture
        agent_gaps:     agent's reported GapItem dicts
        gt_gaps:        fixture seeded_gaps list

    Returns:
        (composite_reward, detailed_breakdown)
    """
    from grc_compliance_audit_env.server.graders.classification_grader import (
        macro_f1_iso, macro_f1_nist
    )

    # Component 1: Coverage F1 (average ISO + NIST)
    iso_map, _  = macro_f1_iso(agent_coverage, gt_coverage)
    nist_map, _ = macro_f1_nist(agent_coverage, gt_coverage)
    coverage_f1 = round((iso_map + nist_map) / 2.0, 4)

    # Component 2: Gap F1
    _, _, gap_f1, gap_det_detail = gap_detection_f1(agent_gaps, gt_gaps)

    # Component 3: Description quality
    desc_score, desc_detail = description_quality_score(agent_gaps, gt_gaps)

    composite = round(
        0.40 * coverage_f1 + 0.40 * gap_f1 + 0.20 * desc_score, 4
    )

    return composite, {
        "coverage_f1":     coverage_f1,
        "gap_f1":          gap_f1,
        "description_score": desc_score,
        "composite_reward":  composite,
        "gap_detection_detail": gap_det_detail,
        "description_detail":   desc_detail,
        "iso_mapping_f1":  iso_map,
        "nist_mapping_f1": nist_map,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Gap score component (task_hard)
# ─────────────────────────────────────────────────────────────────────────────

def gap_score_hard(
    agent_gaps: List[Dict],
    gt_gaps: List[Dict],
    n_seeded: int = 5,
) -> Tuple[float, Dict]:
    """Compute the gap score component for Task 3.

    gap_score = 0.70 × gap_coverage + 0.30 × severity_accuracy
        gap_coverage    = |agent_gaps ∩ gt_gaps| / n_seeded

    Returns:
        (gap_score, breakdown)
    """
    agent_ids = _extract_gap_ids(agent_gaps)
    gt_ids    = _extract_gap_ids(gt_gaps)

    tp_count   = len(agent_ids & gt_ids)
    coverage   = round(tp_count / n_seeded, 4)
    sev_acc    = severity_accuracy(agent_gaps, gt_gaps)
    gap_score  = round(0.70 * coverage + 0.30 * sev_acc, 4)

    return gap_score, {
        "gap_coverage":       coverage,
        "severity_accuracy":  sev_acc,
        "gap_score":          gap_score,
        "true_positives_found": tp_count,
        "total_seeded":        n_seeded,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feedback generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_gap_feedback(breakdown: Dict, task: str = "task_medium") -> str:
    """Generate human-readable feedback for the gap grader."""
    lines = [f"Gap Grader — {task}"]

    if "coverage_f1" in breakdown:
        lines.append(f"  Coverage F1      : {breakdown['coverage_f1']:.3f}")
    if "gap_f1" in breakdown:
        lines.append(f"  Gap Detection F1 : {breakdown['gap_f1']:.3f}")
    if "description_score" in breakdown:
        lines.append(f"  Description Score: {breakdown['description_score']:.3f}")
    if "gap_coverage" in breakdown:
        lines.append(f"  Gap Coverage     : {breakdown['gap_coverage']:.3f}  "
                     f"({breakdown.get('true_positives_found', '?')}/{breakdown.get('total_seeded', '?')} seeded gaps found)")
    if "severity_accuracy" in breakdown:
        lines.append(f"  Severity Accuracy: {breakdown['severity_accuracy']:.3f}")

    composite = breakdown.get("composite_reward") or breakdown.get("gap_score", 0.0)
    lines.append(f"  ─── Score: {composite:.3f}")

    det = breakdown.get("gap_detection_detail", {})
    tp  = det.get("true_positives", [])
    fp  = det.get("false_positives", [])
    fn  = det.get("false_negatives", [])

    if tp:
        lines.append(f"  ✓ Correct gaps   : {', '.join(tp)}")
    if fp:
        lines.append(f"  ✗ False alarms   : {', '.join(fp)}")
    if fn:
        lines.append(f"  ✗ Missed gaps    : {', '.join(fn)}")

    return "\n".join(lines)
