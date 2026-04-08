"""
app.py — FastAPI application factory for the GRC Compliance Audit OpenEnv environment.

Creates the OpenEnv-spec-compliant WebSocket server using:
    create_app(GRCEnvironment, GRCAction, GRCObservation)

The app runs on port 8000 and exposes:
    GET  /health               → {"status": "ok"}
    GET  /info                 → environment metadata
    WS   /ws/{episode_id}      → reset / step / state WebSocket endpoint
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from grc_compliance_audit_env.models import (
    GRCAction,
    GRCObservation,
    GRCState,
)
from grc_compliance_audit_env.server.grc_environment import GRCEnvironment

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Application factory (OpenEnv V1 spec)
# ─────────────────────────────────────────────────────────────────────────────

def create_app(
    env_class=GRCEnvironment,
    action_class=GRCAction,
    observation_class=GRCObservation,
) -> FastAPI:
    """Create and return the FastAPI application.

    This function signature matches the OpenEnv V1 spec so that the framework
    can discover and instantiate the app automatically via the ``app`` entry
    point in ``openenv.yaml``.
    """
    application = FastAPI(
        title="GRC Compliance Audit Environment",
        description=(
            "OpenEnv RL environment for training agents to audit policy documents "
            "against ISO 27001:2022, NIST SP 800-53 Rev 5, and SOC 2 TSC."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Single shared environment instance per server process
    # In production this could be a pool, but for the hackathon scope one is fine.
    _env = env_class()

    # ── REST endpoints ────────────────────────────────────────────────────────

    @application.get("/health", tags=["Meta"])
    async def health() -> dict:
        """Health check — required by OpenEnv spec and Docker HEALTHCHECK."""
        return {"status": "ok", "environment": "grc_compliance_audit_env", "version": "0.1.0"}

    @application.get("/info", tags=["Meta"])
    async def info() -> dict:
        """Return environment metadata and available tasks."""
        return {
            "name": "grc_compliance_audit_env",
            "display_name": "GRC Compliance Audit",
            "version": "0.1.0",
            "description": (
                "An RL environment where an AI agent audits policy documents "
                "against ISO 27001:2022, NIST 800-53 Rev 5, and SOC 2 TSC."
            ),
            "tasks": [
                {
                    "id": "task_easy",
                    "name": "Single-Framework Control Classification",
                    "difficulty": "easy",
                    "max_steps": 5,
                    "frameworks": ["iso27001"],
                },
                {
                    "id": "task_medium",
                    "name": "Dual-Framework Gap Analysis",
                    "difficulty": "medium",
                    "max_steps": 10,
                    "frameworks": ["iso27001", "nist_80053"],
                },
                {
                    "id": "task_hard",
                    "name": "Full Multi-Framework Compliance Audit",
                    "difficulty": "hard",
                    "max_steps": 20,
                    "frameworks": ["iso27001", "nist_80053", "soc2"],
                },
            ],
            "reward_range": [0.0, 1.0],
            "spec_version": 1,
        }

    # ── REST endpoints for OpenEnv validator (POST /reset, POST /step, GET /state)

    from fastapi import Body, Request

    @application.post("/reset", tags=["OpenEnv"])
    async def rest_reset(request: Request) -> dict:
        """Reset the environment. Validator sends POST /reset with optional JSON body."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        options = body if isinstance(body, dict) else {}
        obs: GRCObservation = _env.reset(options=options)
        return obs.model_dump()

    @application.post("/step", tags=["OpenEnv"])
    async def rest_step(request: Request) -> dict:
        """Take a step. Validator sends POST /step with action JSON body."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        raw_action = body.get("action", body) if isinstance(body, dict) else {}
        try:
            action = action_class(**raw_action)
        except Exception:
            # If the validator sends a minimal/empty action, build a safe default
            action = action_class(task_id="task_easy")
        obs: GRCObservation = _env.step(action)
        return obs.model_dump()

    @application.get("/state", tags=["OpenEnv"])
    async def rest_state() -> dict:
        """Return current environment state."""
        state: GRCState = _env.state()
        return state.model_dump()

    # ── WebSocket endpoint ────────────────────────────────────────────────────

    @application.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """
        Primary WebSocket endpoint following OpenEnv V1 message protocol.

        Message format (JSON):
            Client → Server:
                {"type": "reset", "options": {"task_id": "task_easy"}}
                {"type": "step",  "action": {...GRCAction fields...}}
                {"type": "state"}

            Server → Client:
                {"type": "observation", "data": {...GRCObservation fields...}}
                {"type": "state",       "data": {...GRCState fields...}}
                {"type": "error",       "message": "..."}
        """
        await websocket.accept()
        logger.info("WebSocket connection established: %s", websocket.client)

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await _send_error(websocket, "Invalid JSON message.")
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "reset":
                    options = msg.get("options", {})
                    obs: GRCObservation = _env.reset(options=options)
                    await _send_observation(websocket, obs)

                elif msg_type == "step":
                    raw_action = msg.get("action", {})
                    try:
                        action = action_class(**raw_action)
                    except Exception as exc:
                        await _send_error(
                            websocket,
                            f"Invalid action format: {exc}. "
                            "Ensure all required fields are present.",
                        )
                        continue
                    obs = _env.step(action)
                    await _send_observation(websocket, obs)

                elif msg_type == "state":
                    state: GRCState = _env.state()
                    await websocket.send_text(
                        json.dumps({"type": "state", "data": state.model_dump()})
                    )

                else:
                    await _send_error(
                        websocket,
                        f"Unknown message type '{msg_type}'. "
                        "Valid types: 'reset', 'step', 'state'.",
                    )

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected.")
        except Exception as exc:
            logger.exception("Unhandled WebSocket error: %s", exc)
            try:
                await _send_error(websocket, f"Internal error: {exc}")
            except Exception:
                pass

    return application


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _send_observation(ws: WebSocket, obs: GRCObservation) -> None:
    await ws.send_text(
        json.dumps({"type": "observation", "data": obs.model_dump()})
    )


async def _send_error(ws: WebSocket, message: str) -> None:
    await ws.send_text(
        json.dumps({"type": "error", "message": message})
    )

# ─────────────────────────────────────────────────────────────────────────────
# ASGI app instance (for uvicorn and openenv.yaml `app:` directive)
# ─────────────────────────────────────────────────────────────────────────────

app = create_app()

@app.get("/")
def root():
    return {
        "name": "Sentinel GRC Audit Environment",
        "status": "running",
        "message": "OpenEnv environment is live."
    }
