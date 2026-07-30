"""Direct WebSocket client for PMA Core in Houdini."""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

import keyring
import websockets

CORE_WS_URL = os.environ.get(
    "PMA_CORE_WS_URL", "ws://localhost:8000/api/modules/ws"
)


def _send_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = keyring.get_password("PersonalMemoryAssistant", "X_LOCAL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "X_LOCAL_ACCESS_TOKEN not found in keyring. Please configure PMA Core."
        )

    async def _async_call():
        headers = {"x-local-access-token": token}
        async with websockets.connect(CORE_WS_URL, extra_headers=headers) as ws:
            msg = {"action": action, **payload}
            await ws.send(json.dumps(msg))
            raw = await ws.recv()
            resp = json.loads(raw)
            if resp.get("status") == "error":
                raise RuntimeError(f"PMA Core error: {resp.get('message')}")
            return resp

    try:
        return asyncio.run(_async_call())
    except (OSError, websockets.exceptions.WebSocketException) as e:
        raise RuntimeError(
            f"Could not connect to PMA Core at {CORE_WS_URL}.\n"
            "Please check that PMA Core is running.\n\n"
            f"Details: {e}"
        ) from e


def ingest_scene(
    hip_file: str,
    chunks: list[dict[str, Any]],
    houdini_version: str = "",
    platform: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    project_name = (
        os.path.splitext(os.path.basename(hip_file))[0] if hip_file else "Untitled"
    )
    return _send_action(
        "creative_ingest",
        {
            "project_name": project_name,
            "hip_file": hip_file,
            "chunks": chunks,
            "houdini_version": houdini_version,
            "platform": platform,
            "metadata": metadata or {},
        },
    )


def ask(question: str, hip_file: Optional[str] = None) -> dict[str, Any]:
    project_name = (
        os.path.splitext(os.path.basename(hip_file))[0] if hip_file else None
    )
    return _send_action(
        "creative_query", {"question": question, "project_name": project_name}
    )


def cross_search(
    question: str, exclude_hip: Optional[str] = None
) -> dict[str, Any]:
    return _send_action(
        "creative_cross_query", {"question": question, "exclude_hip": exclude_hip}
    )


def list_projects() -> list[dict[str, Any]]:
    res = _send_action("creative_list_projects", {})
    return res.get("projects", [])
