"""
final_smoke_test.py — Complete end-to-end validation of the entire codebase.

Tests every layer: imports → models → graders → tasks → environment → app factory.
"""
import sys, json, pathlib, importlib
sys.path.insert(0, ".")

PASS = []
FAIL = []

def check(label, fn):
    try:
        fn()
        PASS.append(label)
        print(f"  ✓  {label}")
    except Exception as exc:
        FAIL.append((label, exc))
        print(f"  ✗  {label}  →  {exc}")

print("\n" + "=" * 62)
print("FINAL SMOKE TEST — GRC Compliance Audit OpenEnv Environment")
print("=" * 62)

# ── 1. Package-level imports ──────────────────────────────────────────────────
print("\n[1] Package imports")

def _import_package():
    from grc_compliance_audit_env import (
        GRCAction, GRCObservation, GRCState,
        ControlMapping, GapItem, SharedControl,
        GRCEnvironment, GRCAuditEnv,
    )
check("Top-level package __init__ exports all 8 symbols", _import_package)

def _import_graders():
    from grc_compliance_audit_env.server.graders.classification_grader import (
        section_f1, macro_f1_iso, macro_f1_nist, macro_f1_soc2,
        multi_framework_mapping_score, generate_classification_feedback,
    )
    from grc_compliance_audit_env.server.graders.gap_grader import (
        gap_detection_f1, severity_weighted_delta, description_quality_score,
        severity_accuracy, composite_gap_reward_medium, gap_score_hard,
        generate_gap_feedback,
    )
    from grc_compliance_audit_env.server.graders.cross_framework_grader import (
        cross_framework_f1, cross_framework_bonus, cross_framework_score,
        generate_cross_framework_feedback,
    )
check("All grader functions importable", _import_graders)

def _import_tasks():
    from grc_compliance_audit_env.server.tasks.easy_task   import easy_task
    from grc_compliance_audit_env.server.tasks.medium_task import medium_task
    from grc_compliance_audit_env.server.tasks.hard_task   import hard_task
    assert easy_task.task_id   == "task_easy"
    assert medium_task.task_id == "task_medium"
    assert hard_task.task_id   == "task_hard"
check("Task loaders importable and task_id correct", _import_tasks)

def _import_app():
    from grc_compliance_audit_env.server.app import app, create_app
    assert app is not None
check("FastAPI app factory importable", _import_app)

# ── 2. Taxonomy validation ────────────────────────────────────────────────────
print("\n[2] Taxonomy data integrity")

base = pathlib.Path("grc_compliance_audit_env/server/data")

def _check_iso():
    iso = json.loads((base / "taxonomies/iso27001_controls.json").read_text())
    assert len(iso["controls"]) == 93
    for c in iso["controls"]:
        assert c["id"].startswith("A."), f"Bad ID: {c['id']}"
check("ISO 27001:2022 — 93 controls, all A.x IDs", _check_iso)

def _check_nist():
    nist = json.loads((base / "taxonomies/nist_80053_families.json").read_text())
    assert len(nist["families"]) == 20
    total = sum(len(f["key_controls"]) for f in nist["families"])
    assert total == 165
check("NIST 800-53 Rev 5 — 20 families, 165 sub-controls", _check_nist)

def _check_soc2():
    soc2 = json.loads((base / "taxonomies/soc2_tsc.json").read_text())
    assert len(soc2["categories"]) == 5
    total = sum(len(c["criteria"]) for c in soc2["categories"])
    assert total == 51
    assert len(soc2["cross_framework_mapping"]["mappings"]) == 15
check("SOC 2 TSC — 5 categories, 51 criteria, 15 mappings", _check_soc2)

def _check_fixtures():
    for f in ["easy_access_control_policy", "medium_infosec_policy", "hard_complete_isms_policy"]:
        assert (base / f"fixtures/{f}.txt").exists()
        data = json.loads((base / f"fixtures/{f}.json").read_text())
        assert "policy_id" in data and "sections" in data
check("All 6 fixture files present and parseable", _check_fixtures)

def _check_easy_fixture():
    data = json.loads((base / "fixtures/easy_access_control_policy.json").read_text())
    assert len(data["sections"]) == 5
    assert data["max_steps"] == 5
check("Easy fixture — 5 sections, max_steps=5", _check_easy_fixture)

def _check_medium_fixture():
    data = json.loads((base / "fixtures/medium_infosec_policy.json").read_text())
    assert len(data["sections"]) == 3
    assert len(data["seeded_gaps"]) == 4
check("Medium fixture — 3 sections, 4 seeded gaps", _check_medium_fixture)

def _check_hard_fixture():
    data = json.loads((base / "fixtures/hard_complete_isms_policy.json").read_text())
    assert len(data["sections"]) == 10
    assert len(data["seeded_gaps"]) == 5
    assert len(data["ground_truth_shared_controls"]) == 8
    w = data["grader_config"]["weights"]
    assert abs(w["mapping_score"]+w["gap_score"]+w["cross_framework_quality"] - 1.0) < 0.001
check("Hard fixture — 10 sections, 5 gaps, 8 shared controls, weights=1.0", _check_hard_fixture)

# ── 3. Grader unit tests ──────────────────────────────────────────────────────
print("\n[3] Grader logic")

from grc_compliance_audit_env.server.graders.classification_grader import section_f1, macro_f1_iso
from grc_compliance_audit_env.server.graders.gap_grader import (
    gap_detection_f1, composite_gap_reward_medium, gap_score_hard,
)
from grc_compliance_audit_env.server.graders.cross_framework_grader import (
    cross_framework_f1, cross_framework_bonus,
)

def _f1_perfect():
    _, _, f1 = section_f1(["A.5.1","A.5.2"], ["A.5.1","A.5.2"])
    assert f1 == 1.0
check("section_f1 — perfect prediction = 1.0", _f1_perfect)

def _f1_empty():
    _, _, f1 = section_f1([], ["A.5.1"])
    assert f1 == 0.0
check("section_f1 — empty prediction = 0.0", _f1_empty)

def _f1_over():
    p, r, f1 = section_f1(["A.5.1","A.5.2","A.5.3"], ["A.5.1","A.5.2"])
    assert r == 1.0 and p < 1.0 and 0 < f1 < 1.0
check("section_f1 — over-prediction: R=1, P<1", _f1_over)

def _macro():
    maps = [{"section_id":"s1","iso_control_ids":["A.5.1","A.5.2"]},
            {"section_id":"s2","iso_control_ids":["A.5.15"]}]
    gt   = [{"section_id":"s1","gt_iso_controls":["A.5.1","A.5.2"]},
            {"section_id":"s2","gt_iso_controls":["A.5.15","A.8.3"]}]
    score, _ = macro_f1_iso(maps, gt)
    assert 0.0 < score < 1.0
check("macro_f1_iso — partial coverage in (0,1)", _macro)

def _gap_f1_perfect():
    gt  = [{"control_id":"A.8.5","risk_level":"critical"},
           {"control_id":"A.8.8","risk_level":"high"}]
    ag  = [{"control_id":"A.8.5","risk_level":"critical"},
           {"control_id":"A.8.8","risk_level":"high"}]
    _,_,f1,_ = gap_detection_f1(ag, gt)
    assert f1 == 1.0
check("gap_detection_f1 — perfect = 1.0", _gap_f1_perfect)

def _gap_f1_miss():
    gt = [{"control_id":"A.8.5","risk_level":"critical"},
          {"control_id":"A.8.8","risk_level":"high"}]
    ag = [{"control_id":"A.8.5","risk_level":"critical"}]  # miss A.8.8
    _,_,f1,_ = gap_detection_f1(ag, gt)
    assert 0.0 < f1 < 1.0
check("gap_detection_f1 — partial miss in (0,1)", _gap_f1_miss)

def _cf_bonus():
    gt = [{"policy_section_id":"s3","iso_control_id":"A.5.15",
           "nist_control_id":"AC-1","soc2_criteria_id":"CC6.1"}]
    ag = [{"policy_section_id":"s3","iso_control_id":"A.5.15",
           "nist_control_id":"AC-1","soc2_criteria_id":"CC6.1"}]
    bonus, n = cross_framework_bonus(ag, gt)
    assert n == 1 and abs(bonus - 0.05) < 0.001
check("cross_framework_bonus — 1 correct = +0.05", _cf_bonus)

# ── 4. Environment full episode ───────────────────────────────────────────────
print("\n[4] GRCEnvironment episode loops")

from grc_compliance_audit_env.server.grc_environment import GRCEnvironment
from grc_compliance_audit_env.models import (
    GRCAction, ControlMapping, GapItem, SharedControl,
)

env = GRCEnvironment()

def _reset_easy():
    obs = env.reset(options={"task_id": "task_easy"})
    assert obs.task_id == "task_easy"
    assert obs.total_sections == 5
    assert len(obs.policy_text) > 500
    assert "iso27001" in obs.target_frameworks
    assert len(obs.available_iso_controls) >= 10
check("reset(task_easy) — correct task metadata", _reset_easy)

def _step_easy_perfect():
    env.reset(options={"task_id": "task_easy"})
    action = GRCAction(task_id="task_easy", control_mappings=[
        ControlMapping(section_id="section_1", iso_control_ids=["A.5.1","A.5.2"]),
        ControlMapping(section_id="section_2", iso_control_ids=["A.5.15","A.8.3"]),
        ControlMapping(section_id="section_3", iso_control_ids=["A.8.2"]),
        ControlMapping(section_id="section_4", iso_control_ids=["A.8.5","A.8.20"]),
        ControlMapping(section_id="section_5", iso_control_ids=["A.5.15","A.6.5"]),
    ])
    obs = env.step(action)
    assert obs.step_reward >= 0.9
    assert obs.done
check("step(task_easy) — perfect action ≥0.9 reward, done=True", _step_easy_perfect)

def _step_easy_state():
    env.reset(options={"task_id": "task_easy"})
    action = GRCAction(task_id="task_easy", control_mappings=[
        ControlMapping(section_id="section_1", iso_control_ids=["A.5.1","A.5.2"]),
    ])
    env.step(action)
    state = env.state()
    assert state.task_id == "task_easy"
    assert state.step_count == 1
    assert isinstance(state.episode_id, str) and len(state.episode_id) == 36
check("state() — correct schema after 1 step", _step_easy_state)

def _rule4_repetition():
    env.reset(options={"task_id": "task_easy"})
    partial = GRCAction(task_id="task_easy", control_mappings=[
        ControlMapping(section_id="section_1", iso_control_ids=["A.5.1"]),
    ])
    obs1 = env.step(partial)
    assert not obs1.done, "Should not be done after partial action"
    obs2 = env.step(partial)
    assert obs2.done
    assert obs2.reward < 0.0  # negative penalty on raw reward
check("Rule 4 — repeated action: done=True, reward<0", _rule4_repetition)

def _reset_medium():
    obs = env.reset(options={"task_id": "task_medium"})
    assert obs.task_id == "task_medium"
    assert obs.total_sections == 3
    assert set(obs.target_frameworks) == {"iso27001", "nist_80053"}
check("reset(task_medium) — 3 sections, dual framework", _reset_medium)

def _reset_hard():
    obs = env.reset(options={"task_id": "task_hard"})
    assert obs.task_id == "task_hard"
    assert obs.total_sections == 10
    assert set(obs.target_frameworks) == {"iso27001", "nist_80053", "soc2"}
check("reset(task_hard) — 10 sections, 3 frameworks", _reset_hard)

def _unknown_task():
    try:
        env.reset(options={"task_id": "task_invalid"})
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
check("reset(unknown_task) — raises ValueError", _unknown_task)

# ── 5. FastAPI app ────────────────────────────────────────────────────────────
print("\n[5] FastAPI app structure")

def _app_routes():
    from grc_compliance_audit_env.server.app import app
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/health" in routes
    assert "/info"   in routes
    assert "/ws"     in routes
check("FastAPI routes: /health, /info, /ws", _app_routes)

def _app_health():
    from fastapi.testclient import TestClient
    from grc_compliance_audit_env.server.app import app
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "grc_compliance_audit_env" in data["environment"]
check("/health returns 200 + status=ok", _app_health)

def _app_info():
    from fastapi.testclient import TestClient
    from grc_compliance_audit_env.server.app import app
    with TestClient(app) as c:
        r = c.get("/info")
        assert r.status_code == 200
        data = r.json()
        assert len(data["tasks"]) == 3
        task_ids = {t["id"] for t in data["tasks"]}
        assert task_ids == {"task_easy", "task_medium", "task_hard"}
check("/info returns 3 tasks with correct IDs", _app_info)

# ── 6. WebSocket protocol ─────────────────────────────────────────────────────
print("\n[6] WebSocket protocol (TestClient)")

def _ws_reset_step():
    from fastapi.testclient import TestClient
    from grc_compliance_audit_env.server.app import app
    with TestClient(app) as c:
        with c.websocket_connect("/ws") as ws:
            # reset
            ws.send_json({"type": "reset", "options": {"task_id": "task_easy"}})
            msg = ws.receive_json()
            assert msg["type"] == "observation"
            assert msg["data"]["task_id"] == "task_easy"
            assert msg["data"]["total_sections"] == 5

            # step
            action = {
                "task_id": "task_easy",
                "control_mappings": [
                    {"section_id":"section_1","iso_control_ids":["A.5.1","A.5.2"],
                     "nist_control_ids":[],"soc2_criteria_ids":[]},
                ],
                "gaps": [], "shared_controls": [],
            }
            ws.send_json({"type": "step", "action": action})
            msg = ws.receive_json()
            assert msg["type"] == "observation"
            assert msg["data"]["step_reward"] >= 0.0

            # state
            ws.send_json({"type": "state"})
            msg = ws.receive_json()
            assert msg["type"] == "state"
            assert msg["data"]["step_count"] == 1
check("WebSocket reset → step → state protocol", _ws_reset_step)

def _ws_bad_message():
    from fastapi.testclient import TestClient
    from grc_compliance_audit_env.server.app import app
    with TestClient(app) as c:
        with c.websocket_connect("/ws") as ws:
            ws.send_json({"type": "unknown_type"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
check("WebSocket unknown message type returns error", _ws_bad_message)

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
total = len(PASS) + len(FAIL)
print(f"RESULTS: {len(PASS)}/{total} tests passed")
if FAIL:
    print(f"\nFAILED ({len(FAIL)}):")
    for label, exc in FAIL:
        print(f"  ✗ {label}")
        print(f"    {type(exc).__name__}: {exc}")
    print("\n" + "=" * 62)
    sys.exit(1)
else:
    print("\n✓ ALL TESTS PASSED — Environment is production-ready")
    print("=" * 62 + "\n")
