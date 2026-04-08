"""
easy_task.py — Task 1: Single-Framework Control Classification

Loads the easy fixture (Access Control Policy, 5 sections) and exposes
the task payload for the GRCEnvironment to package into a GRCObservation.

Task spec:
    Framework  : ISO 27001:2022 only
    Max steps  : 5
    Grader     : Macro-F1 on ISO control IDs per section
    Reward     : Per-section F1 emitted immediately after each step
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data"
_FIXTURE_TXT  = _DATA_DIR / "fixtures" / "easy_access_control_policy.txt"
_FIXTURE_JSON = _DATA_DIR / "fixtures" / "easy_access_control_policy.json"

_TASK_DESCRIPTION = (
    "You are a GRC analyst conducting an ISO 27001:2022 audit. "
    "Read the Access Control Policy document below and classify each numbered "
    "section by listing all ISO 27001:2022 Annex A control IDs it addresses. "
    "Use exact control IDs (e.g. 'A.5.15', 'A.8.2'). "
    "Populate control_mappings with one entry per section. "
    "You have 5 steps — one per section is the optimal strategy."
)


# ─── Loader ──────────────────────────────────────────────────────────────────

class EasyTask:
    """Manages the easy task fixture data for an episode."""

    task_id: str = "task_easy"
    max_steps: int = 5
    target_frameworks: List[str] = ["iso27001"]

    def __init__(self) -> None:
        self._policy_text: str = ""
        self._annotation: Dict[str, Any] = {}
        self._loaded: bool = False

    def load(self) -> None:
        """Load fixture files from disk. Called once per environment init."""
        if self._loaded:
            return
        try:
            self._policy_text = _FIXTURE_TXT.read_text(encoding="utf-8")
            self._annotation  = json.loads(_FIXTURE_JSON.read_text(encoding="utf-8"))
            self._loaded = True
            logger.info("EasyTask: fixture loaded — %s", self._annotation.get("policy_name"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"EasyTask fixture not found: {exc}. "
                "Ensure server/data/fixtures/ exists with the correct files."
            ) from exc

    # ── Public accessors ─────────────────────────────────────────────────────

    @property
    def policy_text(self) -> str:
        self._ensure_loaded()
        return self._policy_text

    @property
    def policy_name(self) -> str:
        self._ensure_loaded()
        return self._annotation.get("policy_name", "Access Control Policy v1.0")

    @property
    def policy_id(self) -> str:
        self._ensure_loaded()
        return self._annotation.get("policy_id", "easy_001")

    @property
    def total_sections(self) -> int:
        self._ensure_loaded()
        return len(self._annotation.get("sections", []))

    @property
    def sections(self) -> List[Dict]:
        self._ensure_loaded()
        return self._annotation.get("sections", [])

    @property
    def available_iso_controls(self) -> List[str]:
        self._ensure_loaded()
        return self._annotation.get("available_iso_controls_hint", [])

    @property
    def hint(self) -> str:
        self._ensure_loaded()
        return self._annotation.get("hint", "")

    @property
    def task_description(self) -> str:
        return _TASK_DESCRIPTION

    # ── Grading interface ────────────────────────────────────────────────────

    def get_ground_truth_sections(self) -> List[Dict]:
        """Return sections with gt_iso_controls for the grader."""
        self._ensure_loaded()
        return self.sections

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


# Singleton instance — one per server process
easy_task = EasyTask()
