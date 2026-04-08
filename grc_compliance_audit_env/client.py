"""
client.py — GRCAuditEnv WebSocket client for the GRC Compliance Audit environment.

This is the client-side counterpart to server/app.py. It is what inference scripts
and external agents use to connect to the running environment server.

Follows the OpenEnv V1 EnvClient pattern:
    async with GRCAuditEnv(base_url="http://localhost:8000") as env:
        obs = await env.reset(options={"task_id": "task_easy"})
        obs = await env.step(action)
        state = await env.state()

The client communicates over WebSocket using the JSON message protocol defined
in server/app.py.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# OpenEnv EnvClient base — falls back to stub if not installed
try:
    from openenv.core.env_client import EnvClient as _BaseClient
except ImportError:
    class _BaseClient:  # type: ignore[no-redef]
        """Stub base class for local development without openenv-core."""
        def __init__(self, base_url: str = "http://localhost:8000"):
            self.base_url = base_url

try:
    import websockets  # type: ignore
    _HAS_WEBSOCKETS = True
except ImportError:
    _HAS_WEBSOCKETS = False

from grc_compliance_audit_env.models import GRCAction, GRCObservation, GRCState


class GRCAuditEnv(_BaseClient):
    """
    WebSocket client for the GRC Compliance Audit OpenEnv environment.

    Usage::

        async with GRCAuditEnv(base_url="http://localhost:8000") as env:
            obs = await env.reset(options={"task_id": "task_easy"})
            action = GRCAction(task_id="task_easy", control_mappings=[...])
            obs = await env.step(action)
            state = await env.state()

    Args:
        base_url: HTTP base URL of the running environment server.
                  Converted internally to ``ws://`` for the WebSocket connection.
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        super().__init__(base_url=base_url)
        self._ws_url = (
            base_url
            .replace("http://", "ws://")
            .replace("https://", "wss://")
            + "/ws"
        )
        self._ws: Optional[Any] = None

    # ── Async context manager ─────────────────────────────────────────────────

    async def __aenter__(self) -> "GRCAuditEnv":
        await self._connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._disconnect()

    async def _connect(self) -> None:
        if not _HAS_WEBSOCKETS:
            raise RuntimeError(
                "websockets package is required: pip install websockets"
            )
        import websockets as _ws
        self._ws = await _ws.connect(self._ws_url, max_size=10_000_000)
        logger.debug("GRCAuditEnv: connected to %s", self._ws_url)

    async def _disconnect(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            logger.debug("GRCAuditEnv: disconnected")

    # ── OpenEnv API ───────────────────────────────────────────────────────────

    async def reset(self, options: Optional[Dict[str, Any]] = None) -> GRCObservation:
        """Reset the environment and start a new episode.

        Args:
            options: Optional dict with ``task_id`` key.
                     Defaults to ``{"task_id": "task_easy"}``.

        Returns:
            Initial GRCObservation with policy text and task instructions.
        """
        options = options or {"task_id": "task_easy"}
        await self._send({"type": "reset", "options": options})
        msg = await self._recv()
        return GRCObservation(**msg["data"])

    async def step(self, action: GRCAction) -> GRCObservation:
        """Submit an action and receive the graded observation.

        Args:
            action: GRCAction populated according to the active task.

        Returns:
            GRCObservation with step_reward, cumulative_reward, grader_feedback.
        """
        await self._send({"type": "step", "action": action.model_dump()})
        msg = await self._recv()
        if msg.get("type") == "error":
            raise ValueError(f"Environment error: {msg.get('message')}")
        return GRCObservation(**msg["data"])

    async def state(self) -> GRCState:
        """Return the current episode-level state metadata.

        Returns:
            GRCState with episode_id, step_count, accumulated_reward, etc.
        """
        await self._send({"type": "state"})
        msg = await self._recv()
        return GRCState(**msg["data"])

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _send(self, msg: Dict[str, Any]) -> None:
        if self._ws is None:
            raise RuntimeError(
                "Not connected. Use 'async with GRCAuditEnv(...) as env:'"
            )
        await self._ws.send(json.dumps(msg))

    async def _recv(self) -> Dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("Not connected.")
        raw = await self._ws.recv()
        return json.loads(raw)
