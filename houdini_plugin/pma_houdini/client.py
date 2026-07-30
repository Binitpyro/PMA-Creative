"""Direct WebSocket client for Zeni in Houdini."""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

import keyring
import websockets

ZENI_WS_URL = os.environ.get(
    "ZENI_WS_URL", "ws://localhost:8765/ws"
)


def _send_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = None
    try:
        token = keyring.get_password("ZeniCreativeModule", "ZENI_ACCESS_TOKEN")
    except Exception:
        pass

    if not token:
        token = os.environ.get("ZENI_ACCESS_TOKEN") or os.environ.get("X_LOCAL_ACCESS_TOKEN")

    if not token:
        raise RuntimeError(
            "Access token not found in keyring or environment (ZENI_ACCESS_TOKEN / X_LOCAL_ACCESS_TOKEN)."
        )

    async def _async_call():
        headers = {"x-local-access-token": token}
        async with websockets.connect(ZENI_WS_URL, additional_headers=headers) as ws:
            msg = {"action": action, **payload}
            await ws.send(json.dumps(msg))
            raw = await ws.recv()
            resp = json.loads(raw)
            if resp.get("status") == "error":
                raise RuntimeError(f"Zeni server error: {resp.get('message')}")
            return resp

    try:
        return asyncio.run(_async_call())
    except (OSError, websockets.exceptions.WebSocketException) as e:
        raise RuntimeError(
            f"Could not connect to Zeni server at {ZENI_WS_URL}.\n"
            "Please check that Zeni server (main.py) is running.\n\n"
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


def ask(
    question: str,
    hip_file: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    project_name = (
        os.path.splitext(os.path.basename(hip_file))[0] if hip_file else None
    )
    payload: dict[str, Any] = {"question": question, "project_name": project_name}
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model
    return _send_action("creative_query", payload)


def cross_search(
    question: str,
    exclude_hip: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"question": question, "exclude_hip": exclude_hip}
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model
    return _send_action("creative_cross_query", payload)


def list_projects() -> list[dict[str, Any]]:
    res = _send_action("creative_list_projects", {})
    return res.get("projects", [])


def list_providers() -> list[dict[str, Any]]:
    res = _send_action("creative_list_providers", {})
    return res.get("providers", [])
