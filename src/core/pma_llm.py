"""HTTP client for delegating LLM inference to PMA Core's provider layer."""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger("zeni.llm")


def chat(
    messages: list[dict[str, str]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    core_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: float = 60.0,
) -> str:
    """Send chat request to PMA Core's /api/llm/chat endpoint.

    Raises RuntimeError on connection or provider errors.
    """
    base_url = core_url or os.environ.get("PMA_CORE_URL", "http://localhost:8000")
    access_token = token or os.environ.get("X_LOCAL_ACCESS_TOKEN", "")
    endpoint = f"{base_url.rstrip('/')}/api/llm/chat"

    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["x-local-access-token"] = access_token

    payload: dict[str, Any] = {"messages": messages}
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model

    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=timeout)
        if response.status_code == 401:
            raise RuntimeError(
                "PMA Core authentication failed (401 Unauthorized).\n"
                "Please configure a valid access token in Settings."
            )
        elif response.status_code == 404:
            raise RuntimeError(
                f"PMA Core LLM endpoint not found (404) at {endpoint}.\n"
                "Please verify PMA Core is running."
            )
        elif response.status_code != 200:
            raise RuntimeError(
                f"PMA Core returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        if "text" in data:
            return data["text"]
        elif "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0].get("message", {}).get("content", "")
        elif "answer" in data:
            return data["answer"]
        else:
            return str(data)
    except httpx.ConnectError as e:
        raise RuntimeError(
            f"Could not connect to PMA Core at {base_url}.\n"
            "Please verify PMA Core is running."
        ) from e
    except httpx.TimeoutException as e:
        raise RuntimeError(
            f"PMA Core LLM request timed out after {timeout}s."
        ) from e
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"LLM request error: {e}") from e
