"""
hard_task.py — Task 3: Full Multi-Framework Compliance Audit

Loads the hard fixture (10-section complete ISMS Policy with 5 pre-seeded gaps
across ISO 27001, NIST 800-53, and SOC 2 TSC) and exposes the task payload.

Task spec:
    Frameworks : ISO 27001:2022 + NIST 800-53 Rev 5 + SOC 2 TSC
    Max steps  : 20
    Grader     : Mapping accuracy (35%) + Gap detection (40%) +
                 Cross-framework quality (25%)
    Pre-seeded gaps:
        1. A.8.5  / IA-2  / CC6.6  — No MFA requirement  [CRITICAL]
        2. A.8.8  / RA-5  / CC7.1  — No vulnerability scanning  [HIGH]
        3. A.5.24 / IR-4  / CC7.3  — No incident classification criteria  [HIGH]
        4. A.5.30 / CP-9  / A-1    — No backup frequency defined  [HIGH]
        5. A.5.19 / SR-3  / CC9.2  — No supplier assessment methodology  [MEDIUM]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data"
_FIXTURE_TXT  = _DATA_DIR / "fixtures" / "hard_complete_isms_policy.txt"
_FIXTURE_JSON = _DATA_DIR / "fixtures" / "hard_complete_isms_policy.json"

_TASK_DESCRIPTION = (
    "You are a senior GRC analyst conducting a FULL compliance audit of a "
    "complete ISMS policy against THREE frameworks simultaneously: "
    "ISO 27001:2022, NIST SP 800-53 Rev 5, and SOC 2 Trust Services Criteria.\n\n"
    "The policy has 10 sections. You must:\n"
    "  1. Map every section to controls in ALL three frameworks "
    "(iso_control_ids, nist_control_ids, soc2_criteria_ids).\n"
    "  2. Identify ALL compliance gaps — controls required by the frameworks "
    "but absent from the policy. There are exactly 5 seeded gaps.\n"
    "  3. For each gap, provide: control_id, framework, risk_level "
    "('critical'/'high'/'medium'), gap_description, affected_section, remediation.\n"
    "  4. Identify shared controls — where a single policy section satisfies "
    "equivalent controls across all three frameworks simultaneously "
    "(populate shared_controls).\n"
    "  5. Write a 2-3 sentence executive_summary of the overall compliance posture.\n\n"
    "Use exact IDs: 'A.5.15' for ISO, 'AC-2' for NIST, 'CC6.1' for SOC 2.\n"
    "Known gap areas: authentication, vulnerability management, incident "
    "classification, backup schedule, supplier assessment methodology."
)


class HardTask:
    """Manages the hard task fixture data for an episode."""

    task_id: str = "task_hard"
    max_steps: int = 20
    target_frameworks: List[str] = ["iso27001", "nist_80053", "soc2"]

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
            logger.info("HardTask: fixture loaded — %s", self._annotation.get("policy_name"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"HardTask fixture not found: {exc}."
            ) from exc

    # ── Public accessors ─────────────────────────────────────────────────────

    @property
    def policy_text(self) -> str:
        self._ensure_loaded()
        return self._policy_text

    @property
    def policy_name(self) -> str:
        self._ensure_loaded()
        return self._annotation.get("policy_name", "ISMS Policy v3.1")

    @property
    def policy_id(self) -> str:
        self._ensure_loaded()
        return self._annotation.get("policy_id", "hard_001")

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
    def ground_truth_shared_controls(self) -> List[Dict]:
        """Ground-truth shared-control mappings (for grader use only)."""
        self._ensure_loaded()
        return self._annotation.get("ground_truth_shared_controls", [])

    @property
    def available_nist_families(self) -> List[str]:
        return ["AC", "AT", "AU", "CA", "CM", "CP", "IA", "IR",
                "MP", "PE", "PL", "PM", "PS", "PT", "RA", "SA",
                "SC", "SI", "SR"]

    @property
    def task_description(self) -> str:
        return _TASK_DESCRIPTION

    @property
    def grader_config(self) -> Dict:
        self._ensure_loaded()
        return self._annotation.get("grader_config", {
            "weights": {"mapping_score": 0.35, "gap_score": 0.40, "cross_framework_quality": 0.25}
        })

    # ── Grading interface ────────────────────────────────────────────────────

    def get_ground_truth_sections(self) -> List[Dict]:
        self._ensure_loaded()
        return self.sections

    def get_seeded_gaps(self) -> List[Dict]:
        return self.seeded_gaps

    def get_gt_shared_controls(self) -> List[Dict]:
        return self.ground_truth_shared_controls

    def get_section_by_id(self, section_id: str) -> Optional[Dict]:
        self._ensure_loaded()
        for s in self.sections:
            if s["section_id"] == section_id:
                return s
        return None

    # ── Internal ─────────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


hard_task = HardTask()
