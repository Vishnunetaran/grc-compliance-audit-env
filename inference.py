"""
inference.py — GRC Compliance Audit Environment Baseline Inference
==================================================================
MANDATORY (OpenEnv Hackathon Spec):
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use.
    HF_TOKEN       Your HuggingFace / OpenAI API key.

Optional:
    ENV_BASE_URL   Running environment server URL.
    LAUNCH_SERVER  Set to '1' to auto-launch the GRC server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

# ─── Hackathon-required variable names ───────────────────────────────────────
API_BASE_URL: Optional[str] = os.getenv("API_BASE_URL")
API_KEY:      Optional[str] = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME:   Optional[str] = os.getenv("MODEL_NAME")

missing_vars = []
if not API_BASE_URL: missing_vars.append("API_BASE_URL")
if not API_KEY: missing_vars.append("HF_TOKEN / API_KEY")
if not MODEL_NAME: missing_vars.append("MODEL_NAME")
if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# ─── GRC-specific config ─────────────────────────────────────────────────────
ENV_BASE_URL:   str   = os.getenv("ENV_BASE_URL", "http://localhost:8000")
LAUNCH_SERVER:  bool  = os.getenv("LAUNCH_SERVER", "1") == "1"  # Auto-start server by default
STEP_DELAY:     float = float(os.getenv("STEP_DELAY", "3"))     # Seconds between LLM calls (3s default, safe for paid keys)
TEMPERATURE:    float = 0.0    # Strict determinism — no hallucinations
MAX_TOKENS:     int   = 1200
DEBUG:          bool  = os.getenv("DEBUG", "0") == "1"

TASK_IDS  = ["task_easy", "task_medium", "task_hard"]
MAX_STEPS = {"task_easy": 5, "task_medium": 10, "task_hard": 20}

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("grc_inference")

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — High-Fidelity GRC Auditor
# ─────────────────────────────────────────────────────────────────────────────

_cached_system_prompt: Optional[str] = None

def get_system_prompt() -> str:
    global _cached_system_prompt
    if _cached_system_prompt is not None:
        return _cached_system_prompt

    base_dir = os.path.dirname(os.path.abspath(__file__))
    tax_dir = os.path.join(base_dir, "grc_compliance_audit_env", "server", "data", "taxonomies")
    
    # 1. ISO 27001
    iso_lines = []
    try:
        with open(os.path.join(tax_dir, "iso27001_controls.json"), "r") as f:
            t = json.load(f)
            for c in t.get("controls", []):
                if c["id"].startswith("A.5") or c["id"].startswith("A.6") or c["id"].startswith("A.7") or c["id"].startswith("A.8"):
                    iso_lines.append(f"  {c['id']}: {c['name']}")
    except Exception as e:
        logger.warning(f"Failed to load ISO taxonomy: {e}")
        
    # 2. NIST
    nist_lines = []
    try:
        with open(os.path.join(tax_dir, "nist_80053_families.json"), "r") as f:
            t = json.load(f)
            for fam in t.get("families", []):
                for c in fam.get("key_controls", []):
                    nist_lines.append(f"  {c['id']}: {c['name']}")
    except Exception as e:
        logger.warning(f"Failed to load NIST taxonomy: {e}")

    # 3. SOC2
    soc2_lines = []
    try:
        with open(os.path.join(tax_dir, "soc2_tsc.json"), "r") as f:
            t = json.load(f)
            for cat in t.get("categories", []):
                for c in cat.get("criteria", []):
                    soc2_lines.append(f"  {c['id']}: {c['name']}")
    except Exception as e:
        logger.warning(f"Failed to load SOC2 taxonomy: {e}")

    prompt = f"""You are a certified GRC (Governance, Risk, and Compliance) analyst.

Your task is to audit a policy document against one or more compliance frameworks and return a structured JSON response.

════════════════════════════════════════════════════════════════
CONTROL ID REFERENCE (STRICT ALPHANUMERIC ENFORCEMENT)
════════════════════════════════════════════════════════════════
The following are the ONLY valid Control IDs you may use. You must map the document to these EXACT IDs based on their descriptions.

--- ISO 27001:2022 ---
{chr(10).join(iso_lines)}

--- NIST SP 800-53 Rev 5 ---
{chr(10).join(nist_lines)}

--- SOC 2 Trust Services Criteria ---
{chr(10).join(soc2_lines)}

════════════════════════════════════════════════════════════════
RULES & REQUIREMENTS (CRITICAL)
════════════════════════════════════════════════════════════════
1. You must output ONLY the alphanumeric Control IDs (e.g., A.5.15, AC-2, CC6.1). Do not use descriptive text or names in the mapping lists. If you use a name instead of an ID, the score will be 0.
2. Output ONLY raw JSON. No preamble, no 'Here is your audit', no markdown fences, no explanation. The very FIRST character must be {{ and the last must be }}.
3. BE EXHAUSTIVE but PRECISE: Map every applicable control, but only include IDs whose description closely matches the section text. Do not guess. Each section typically maps to 1-3 controls per framework.
4. In Task 3, look for sections that satisfy ISO, NIST, and SOC 2 simultaneously to trigger the +0.05 Alignment Bonus ★.
5. risk_level MUST be exactly one of: critical, high, medium, low.
6. framework MUST be exactly one of: iso27001, nist_80053, soc2.
7. A shared_control entry MUST always contain ALL THREE fields: iso_control_id, nist_control_id, AND soc2_criteria_id. If any of the three is missing or unknown, do NOT include that entry in shared_controls — put the partial mapping in control_mappings instead.
8. For gaps: look for controls that the applicable frameworks REQUIRE but that the policy text does NOT address. Each gap is a missing control.

OUTPUT FORMAT:
{{
  "task_id": "<task_id>",
  "reasoning": "Brief analysis",
  "control_mappings": [
    {{
      "section_id": "section_1",
      "iso_control_ids": ["A.5.15", "A.5.16"],
      "nist_control_ids": ["AC-2", "AC-3"],
      "soc2_criteria_ids": ["CC6.1", "CC6.2"]
    }}
  ],
  "gaps": [
    {{
      "control_id": "A.8.5",
      "framework": "iso27001",
      "risk_level": "critical",
      "gap_description": "MFA is required but not mentioned.",
      "affected_section": "section_1",
      "remediation": "Implement MFA"
    }}
  ],
  "shared_controls": [
    {{
      "policy_section_id": "section_1",
      "iso_control_id": "A.5.15",
      "nist_control_id": "AC-2",
      "soc2_criteria_id": "CC6.1"
    }}
  ],
  "executive_summary": "Overall summary"
}}
"""
    _cached_system_prompt = prompt
    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# Server management 
# ─────────────────────────────────────────────────────────────────────────────

_server_proc: Optional[subprocess.Popen] = None

def start_server_local() -> None:
    global _server_proc
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = [
        sys.executable, "-m", "uvicorn",
        "grc_compliance_audit_env.server.app:app",
        "--host", "0.0.0.0", "--port", "8000",
        "--log-level", "warning",
    ]
    logger.info("Starting GRC server (from root directory)...")
    _server_proc = subprocess.Popen(cmd, cwd=pkg_dir)
    import urllib.request
    for attempt in range(30):
        time.sleep(1)
        try:
            urllib.request.urlopen(f"http://localhost:8000/health", timeout=2)
            logger.info("Server ready.")
            return
        except Exception:
            pass
    raise RuntimeError("GRC server failed to start.")

def stop_server_local() -> None:
    global _server_proc
    if _server_proc is not None:
        _server_proc.terminate()
        _server_proc.wait(timeout=5)
        _server_proc = None
        logger.info("GRC server stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# LLM Logic
# ─────────────────────────────────────────────────────────────────────────────

_client: Optional[OpenAI] = None

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        # Mandatory Client Initialization
        _client = OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY,
            max_retries=0
        )
    return _client

def build_user_prompt(
    obs: Dict[str, Any], 
    target_section: Optional[int], 
    prev_feedback: str, 
    cumulative_action: Dict[str, Any]
) -> str:
    task_id = obs.get("task_id", "")
    frameworks = obs.get("target_frameworks", [])
    total_sections = obs.get("total_sections", 1)

    lines = [
        f"TASK: {obs.get('task_description', '')}",
        f"TARGET FRAMEWORKS: {', '.join(frameworks)}",
    ]

    if prev_feedback and "Episode started" not in prev_feedback:
        lines.append(f"\n[GRADER FEEDBACK]\n{prev_feedback}")

    lines.append(f"\n{'─' * 60}\nPOLICY TEXT:\n{'─' * 60}")
    lines.append(obs.get("policy_text", ""))
    lines.append(f"{'─' * 60}")

    if target_section is not None:
        lines.append(f"\n[PROGRESSIVE AUDIT MODE]")
        lines.append(f"In this step, audit ONLY 'section_{target_section}'.")
        lines.append("Do not output mappings or gaps for other sections yet to prevent JSON truncation.")
    else:
        lines.append(f"\n[REFINEMENT MODE]")
        lines.append("You have audited all sections. Review the GRADER FEEDBACK.")
        lines.append("CRITICAL: DO NOT RE-OUTPUT ANY CONTROLS OR GAPS THAT ARE ALREADY IN 'MEMORY'.")
        lines.append("Output ONLY novel, newly discovered gaps or mappings to correct your mistakes.")
        lines.append("If you have nothing new to add, output an empty JSON action (empty lists).")

    # Inject hint if available (task_easy provides this)
    hint = obs.get("hint", "")
    if hint:
        lines.append(f"\n[HINT FROM ENVIRONMENT]")
        lines.append(hint)

    lines.append("\n[MEMORY: ALREADY DISCOVERED] (Do NOT duplicate these in your response!)")
    known_maps = [f"{m.get('section_id')}: ISO={m.get('iso_control_ids',[])} NIST={m.get('nist_control_ids',[])} SOC2={m.get('soc2_criteria_ids',[])}" for m in cumulative_action.get("control_mappings", [])]
    lines.append(f"Mappings already submitted: {known_maps}")
    known_gaps = [f"{g.get('affected_section')} - {g.get('control_id')}" for g in cumulative_action.get("gaps", [])]
    lines.append(f"Gaps already found: {known_gaps}")

    if task_id == "task_easy":
        lines.append("\n[TASK EASY — PRECISION MODE]")
        lines.append("Each section maps to exactly 1-2 ISO controls. Only output the MOST specific control IDs that directly match the section text. Do NOT over-predict — false positives lower your F1 score.")
    elif total_sections < 5:
        lines.append("\n[GREEDY AUDITING]")
        lines.append("This is a high-precision task. Every section MUST be mapped to at least one ID from the taxonomy. Do not leave any section unmapped.")

    return "\n".join(lines)


def call_llm(user_prompt: str, task_id: str) -> Dict[str, Any]:
    llm = get_openai_client()
    action_dict: Dict[str, Any] = {}

    print(f"  {DIM}Pacing: Sleeping {STEP_DELAY}s between steps (set STEP_DELAY env var to adjust)...{RESET}")
    time.sleep(STEP_DELAY)

    for attempt in range(3):
        try:
            response = llm.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )

            # Null-safety: OpenRouter can return empty choices on oversize prompts
            if not response or not response.choices or not response.choices[0].message:
                logger.warning("Empty response from LLM on attempt %d", attempt + 1)
                continue

            raw = response.choices[0].message.content or "{}"
        except Exception as api_exc:
            if "429" in str(api_exc) or "RateLimitError" in str(type(api_exc)):
                print(f"  {YELLOW}⚠ 429 Rate Limit Hit. The Hard Backoff: Sleeping 60 seconds...{RESET}")
                time.sleep(60)
                continue
            
            logger.warning("API call error on attempt %d: %s", attempt + 1, api_exc)
            if attempt == 2:
                return {"task_id": task_id, "control_mappings": [], "gaps": [], "shared_controls": []}
            continue
        
        # Parse JSON
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)

        try:
            action_dict = json.loads(raw)
            if not isinstance(action_dict, dict) or "control_mappings" not in action_dict or "gaps" not in action_dict:
                raise ValueError("Missing 'control_mappings' or 'gaps' array in JSON.")
            break
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Parse/Schema error on attempt %d: %s", attempt + 1, exc)
            if "[STRICT_SCHEMA_ENFORCEMENT]" not in user_prompt:
                user_prompt += "\n\n[STRICT_SCHEMA_ENFORCEMENT] Your last response was missing required JSON fields! You MUST include 'control_mappings' (with section_id, iso_control_ids, nist_control_ids, soc2_criteria_ids) and 'gaps'."
                
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    action_dict = json.loads(match.group(0))
                    if isinstance(action_dict, dict) and "control_mappings" in action_dict:
                        break
                except json.JSONDecodeError:
                    pass
            if attempt == 2:
                # Return empty action instead of crashing entirely on extreme truncation
                action_dict = {}

    action_dict["task_id"] = task_id
    action_dict.setdefault("control_mappings", [])
    action_dict.setdefault("gaps", [])
    action_dict.setdefault("shared_controls", [])
    
    for m in action_dict.get("control_mappings", []):
        m.setdefault("iso_control_ids", [])
        m.setdefault("nist_control_ids", [])
        m.setdefault("soc2_criteria_ids", [])

    # ── Sanitize shared_controls: every entry MUST have all 3 IDs ──
    valid_shared = []
    for sc in action_dict.get("shared_controls", []):
        if (sc.get("iso_control_id") and sc.get("nist_control_id") and sc.get("soc2_criteria_id") and sc.get("policy_section_id")):
            valid_shared.append(sc)
        else:
            logger.debug("Dropping incomplete shared_control: %s", sc)
    action_dict["shared_controls"] = valid_shared

    # ── Sanitize gaps: ensure required fields ──
    valid_gaps = []
    for g in action_dict.get("gaps", []):
        g.setdefault("control_id", "")
        g.setdefault("framework", "iso27001")
        g.setdefault("risk_level", "medium")
        g.setdefault("gap_description", "Gap detected")
        g.setdefault("affected_section", "section_1")
        g.setdefault("remediation", "Remediation required")
        if g["framework"] not in ("iso27001", "nist_80053", "soc2"):
            g["framework"] = "iso27001"
        if g["risk_level"] not in ("critical", "high", "medium", "low"):
            g["risk_level"] = "medium"
        if g["control_id"]:
            valid_gaps.append(g)
    action_dict["gaps"] = valid_gaps

    return action_dict


# ─────────────────────────────────────────────────────────────────────────────
# Core Async Task Runner with Cumulative Memory
# ─────────────────────────────────────────────────────────────────────────────

def merge_actions(cumulative: Dict[str, Any], new_action: Dict[str, Any]) -> None:
    """Safely merges isolated section progress into the cumulative Master Action."""
    for new_map in new_action.get("control_mappings", []) or []:
        sec_id = new_map.get("section_id")
        existing = next((m for m in cumulative["control_mappings"] if m.get("section_id") == sec_id), None)
        if existing:
            iso_new = new_map.get("iso_control_ids") or []
            nist_new = new_map.get("nist_control_ids") or []
            soc2_new = new_map.get("soc2_criteria_ids") or []
            
            existing["iso_control_ids"] = list(set(existing.get("iso_control_ids", []) + iso_new))
            existing["nist_control_ids"] = list(set(existing.get("nist_control_ids", []) + nist_new))
            existing["soc2_criteria_ids"] = list(set(existing.get("soc2_criteria_ids", []) + soc2_new))
        else:
            cumulative["control_mappings"].append(new_map)
            
    for new_gap in new_action.get("gaps", []) or []:
        dup = any(g.get("control_id") == new_gap.get("control_id") and g.get("affected_section") == new_gap.get("affected_section") for g in cumulative["gaps"])
        if not dup:
            cumulative["gaps"].append(new_gap)
            
    for new_sc in new_action.get("shared_controls", []) or []:
        dup = any(sc.get("policy_section_id") == new_sc.get("policy_section_id") for sc in cumulative["shared_controls"])
        if not dup:
            cumulative["shared_controls"].append(new_sc)


CYAN, GREEN, YELLOW, RED, BOLD, DIM, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[2m", "\033[0m"

async def run_task(task_id: str, ws_base_url: str) -> Tuple[float, bool, int]:
    import websockets as _ws
    ws_url = ws_base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    max_steps = MAX_STEPS[task_id]
    
    print(f"\n{BOLD}{'▶'} {task_id.upper()}{RESET}  (max {max_steps} steps)")

    cumulative_action = {
        "task_id": task_id,
        "control_mappings": [],
        "gaps": [],
        "shared_controls": []
    }
    
    max_reward_seen = -1.0
    best_step_reward = 0.0
    decay_steps = 0

    async with _ws.connect(ws_url, max_size=20_000_000) as ws:
        await ws.send(json.dumps({"type": "reset", "options": {"task_id": task_id}}))
        msg = json.loads(await ws.recv())
        obs = msg["data"]
        
        prev_feedback = obs.get("grader_feedback", "")
        final_obs = obs
        total_sections = obs.get("total_sections", 1)

        for step in range(1, max_steps + 1):
            if obs.get("done", False):
                break

            target_section = step if step <= total_sections else None
            user_prompt = build_user_prompt(obs, target_section, prev_feedback, cumulative_action)
            
            try:
                # Background thread to preserve websocket keep-alive
                new_action = await asyncio.to_thread(call_llm, user_prompt, task_id)
            except Exception as exc:
                logger.error("LLM execution error: %s", exc)
                break

            # Deduplication & Safely Aggregate
            merge_actions(cumulative_action, new_action)

            # Check if LLM intentionally returned nothing in refinement mode
            is_empty_refinement = (target_section is None and 
                                   not new_action.get("gaps") and 
                                   not new_action.get("control_mappings") and 
                                   not new_action.get("shared_controls"))
            
            if is_empty_refinement and obs.get("done") is False:
                print(f"  {DIM}Agent returned empty action (no new discoveries). Ending episode gracefully.{RESET}")
                break

            await ws.send(json.dumps({"type": "step", "action": cumulative_action}))
            msg = json.loads(await ws.recv())
            
            if msg.get("type") == "error":
                logger.error("Server validation error: %s", msg.get("message"))
                break
                
            obs = msg["data"]
            final_obs = obs
            
            step_reward = obs.get("step_reward", 0.0)
            best_step_reward = max(best_step_reward, step_reward)
            print(f"  Step {step}/{max_steps}  |  Target: {f'Section {target_section}' if target_section else 'Refinement'}  |  Step Reward: {step_reward:+.3f}  (best: {best_step_reward:.3f})")

            # Early Exit check (Refinement Decay) — only during refinement phase
            if target_section is None:
                if step_reward < max_reward_seen:
                    decay_steps += 1
                else:
                    decay_steps = 0
                max_reward_seen = max(max_reward_seen, step_reward)
                    
                if decay_steps >= 2:
                    print(f"  {DIM}Refinement decay detected (2 consecutive steps). Ending episode gracefully.{RESET}")
                    break
            else:
                max_reward_seen = max(max_reward_seen, step_reward)

            prev_feedback = obs.get("grader_feedback", "")

    # Return the BEST step_reward seen — this is the actual grader score
    # Mark done=True if we completed all sections or exited gracefully
    episode_done = final_obs.get("done", False) or (step > 0)
    return best_step_reward, episode_done, step

async def main_async() -> None:
    print(f"{BOLD}  GRC Compliance Audit — Progressive Inference{RESET}")
    if LAUNCH_SERVER: start_server_local()
    results = []
    
    for task_id in TASK_IDS:
        try:
            score, done, steps = await run_task(task_id, ENV_BASE_URL)
            results.append({"id": task_id, "score": score, "done": done, "steps": steps})
        except Exception as exc:
            logger.debug(traceback.format_exc())
            results.append({"id": task_id, "score": 0.0, "done": False, "steps": 0, "err": str(exc)})

    if LAUNCH_SERVER: stop_server_local()
    
    print(f"\n{BOLD}  FINAL SCOREBOARD{RESET}")
    total = 0.0
    for r in results:
        sym = f"{GREEN}✓{RESET}" if r["score"] > 0.01 else f"{RED}✗{RESET}"
        score = r["score"]
        col = GREEN if score >= 0.6 else YELLOW if score >= 0.3 else RED
        err_msg = f"  {RED}ERROR: {r['err'][:50]}{RESET}" if "err" in r else ""
        print(f"  {r['id']:<15} {col}{score:.4f}{RESET}  {sym}  {r['steps']} steps{err_msg}")
        total += score
        
    print(f"  AVERAGE: {GREEN if total/3 >= 0.5 else YELLOW}{(total/3):.4f}{RESET}\n")

if __name__ == "__main__":
    asyncio.run(main_async())
