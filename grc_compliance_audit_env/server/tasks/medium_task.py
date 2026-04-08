"""
medium_task.py — Task 2: Dual-Framework Gap Analysis

Loads the medium fixture (3-section Information Security Policy with 4 pre-seeded
gaps across ISO 27001 and NIST 800-53) and exposes the task payload.

Task spec:
    Frameworks : ISO 27001:2022 + NIST 800-53 Rev 5
    Max steps  : 10
    Grader     : Coverage F1 (40%) + Gap F1 (40%) + Description quality (20%)
    Reward     : Per-section classification F1 emitted immediately; final gap
                 analysis scored at the end of the episode (or step 10).

Pre-seeded gaps (hidden from agent, known to grader):
    A.8.5  / IA-2  — No MFA requirement  [critical]
    A.8.8  / RA-5  — No vulnerability scanning  [high]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data"
_FIXTURE_TXT  = _DATA_DIR / "fixtures" / "medium_infosec_policy.txt"
_FIXTURE_JSON = _DATA_DIR / "fixtures" / "medium_infosec_policy.json"

_TASK_DESCRIPTION = (
    "You are a GRC analyst auditing a partial Information Security Policy "
    "against ISO 27001:2022 AND NIST SP 800-53 Rev 5 simultaneously. "
    "The policy has 3 sections. For each section:\n"
    "  1. List all ISO 27001:2022 Annex A control IDs it covers (iso_control_ids).\n"
    "  2. List all NIST 800-53 Rev 5 control IDs it covers (nist_control_ids).\n"
    "Then identify compliance GAPS — controls that the frameworks require but that "
    "NO section currently addresses. For each gap, provide:\n"
    "  - control_id, framework, risk_level, gap_description, affected_section, remediation.\n"
    "Use exact IDs: 'A.5.15' for ISO, 'AC-2' for NIST. "
    "Hint: this policy has gaps around authentication and vulnerability management."
)


class MediumTask:
    """Manages the medium task fixture data for an episode."""

    task_id: str = "task_medium"
    max_steps: int = 10
    target_frameworks: List[str] = ["iso27001", "nist_80053"]

    def __init__(self) -> None:
        self._policy_text: str = ""
        self._annotation: Dict[str, Any] = {}
        self._loaded: bool = False

    def load(self) -> None:
        if self._loaded:
            return
        try:
            self._policy_text = _FIXTURE_TXT.read_text(encoding="utf-8")
            self._annotation  = json.loads(_FIXTURE_JSON.read_text(encoding="utf-8"))
            self._loaded = True
            logger.info("MediumTask: fixture loaded — %s", self._annotation.get("policy_name"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"MediumTask fixture not found: {exc}."
            ) from exc

    # ── Public accessors ─────────────────────────────────────────────────────

    @property
    def policy_text(self) -> str:
        self._ensure_loaded()
        return self._policy_text

    @property
    def policy_name(self) -> str:
        self._ensure_loaded()
        return self._annotation.get("policy_name", "Information Security Policy v2.0")

    @property
    def policy_id(self) -> str:
        self._ensure_loaded()
        return self._annotation.get("policy_id", "medium_001")

    @property
    def total_sections(self) -> int:
        self._ensure_loaded()
        return len(self._annotation.get("sections", []))

    @property
    def sections(self) -> List[Dict]:
        self._ensure_loaded()
        return self._annotation.get("sections", [])

    @property
    def seeded_gaps(self) -> List[Dict]:
        """Return the hidden ground-truth gaps (for grader use only)."""
        self._ensure_loaded()
        return self._annotation.get("seeded_gaps", [])

    @property
    def available_nist_families(self) -> List[str]:
        """NIST family abbreviations relevant to this policy."""
        return ["AC", "IA", "AU", "IR", "MP", "RA", "SC", "SI"]

    @property
    def task_description(self) -> str:
        return _TASK_DESCRIPTION

    # ── Grading interface ────────────────────────────────────────────────────

    def get_ground_truth_sections(self) -> List[Dict]:
        self._ensure_loaded()
        return self.sections

    def get_seeded_gaps(self) -> List[Dict]:
        """Alias for seeded_gaps — used by the grader."""
        return self.seeded_gaps

    def get_section_by_id(self, section_id: str) -> Optional[Dict]:
        self._ensure_loaded()
        for s in self.sections:
            if s["section_id"] == section_id:
                return s
        return None

    @property
    def grader_config(self) -> Dict:
        self._ensure_loaded()
        return self._annotation.get("grader_config", {
            "weights": {"coverage_f1": 0.40, "gap_f1": 0.40, "description_score": 0.20}
        })

    # ── Internal ─────────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


medium_task = MediumTask()
