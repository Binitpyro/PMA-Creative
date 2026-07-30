"""Zeni WebSocket Message Router and Connection Handler."""
from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
from typing import Any, Optional

import keyring
from pydantic import ValidationError

from src.core.zeni_agent import ZeniAgent
from src.models.schemas import (
    CreativeCrossQueryRequest,
    CreativeIngestRequest,
    CreativeListProvidersRequest,
    CreativeQueryRequest,
)

logger = logging.getLogger("zeni.server")


def verify_access_token(token: Optional[str]) -> bool:
    """Verify token using secrets.compare_digest against keyring or env var."""
    if not token:
        return False
    expected_token = None
    try:
        expected_token = keyring.get_password("ZeniCreativeModule", "ZENI_ACCESS_TOKEN")
    except Exception:
        pass

    if not expected_token:
        expected_token = os.environ.get("ZENI_ACCESS_TOKEN") or os.environ.get("X_LOCAL_ACCESS_TOKEN")

    if not expected_token:
        return False

    return secrets.compare_digest(token, expected_token)


class ZeniWSRouter:
    """Async WebSocket message router for Zeni actions."""

    def __init__(self, agent: Optional[ZeniAgent] = None):
        self.agent = agent or ZeniAgent()

    async def handle_message(self, raw_message: str, token: Optional[str] = None) -> str:
        """Parse raw JSON string and dispatch Zeni action."""
        if not verify_access_token(token):
            return json.dumps({
                "status": "error",
                "message": "Unauthorized: Invalid or missing access token",
            })

        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "message": "Invalid JSON format"})

        action = payload.get("action")
        if not action:
            return json.dumps({"status": "error", "message": "Missing 'action' field in message"})

        if action == "creative_ingest":
            return await self._handle_ingest(payload)
        elif action == "creative_query":
            return await self._handle_query(payload)
        elif action == "creative_cross_query":
            return await self._handle_cross_query(payload)
        elif action == "creative_list_projects":
            return await self._handle_list_projects()
        elif action == "creative_list_providers":
            return await self._handle_list_providers()
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown action '{action}'",
            })

    async def _handle_ingest(self, payload: dict[str, Any]) -> str:
        try:
            req = CreativeIngestRequest(**payload)
            chunks_dicts = [c.model_dump() for c in req.chunks]
            res = self.agent.ingest_scene(
                project_name=req.project_name,
                hip_file=req.hip_file,
                chunks=chunks_dicts,
                houdini_version=req.houdini_version,
                platform=req.platform,
                metadata=req.metadata,
            )
            return json.dumps({"status": "success", "action": "creative_ingest", **res})
        except ValidationError as e:
            return json.dumps({"status": "error", "message": f"Ingest validation error: {e}"})
        except sqlite3.Error as e:
            logger.error(f"SQLite error during ingest: {e}", exc_info=True)
            return json.dumps({"status": "error", "message": f"Database error: {e}"})

    async def _handle_query(self, payload: dict[str, Any]) -> str:
        try:
            req = CreativeQueryRequest(**payload)
            relevant_chunks = list(
                self.agent.retrieve_relevant_chunks(
                    query=req.question, project_name=req.project_name, limit=10
                )
            )
            metadata = {"project_name": req.project_name} if req.project_name else {}
            provider = payload.get("provider")
            model = payload.get("model")
            answer = self.agent.generate_answer(
                question=req.question,
                chunks=relevant_chunks,
                metadata=metadata,
                provider=provider,
                model=model,
            )
            return json.dumps({
                "status": "success",
                "action": "creative_query",
                "answer": answer,
                "chunks_retrieved": len(relevant_chunks),
                "provider": provider,
                "model": model,
            })
        except ValidationError as e:
            return json.dumps({"status": "error", "message": f"Query validation error: {e}"})
        except Exception as e:
            logger.error(f"Error handling query: {e}", exc_info=True)
            return json.dumps({"status": "error", "message": str(e)})

    async def _handle_cross_query(self, payload: dict[str, Any]) -> str:
        try:
            req = CreativeCrossQueryRequest(**payload)
            provider = payload.get("provider")
            model = payload.get("model")
            results = self.agent.cross_search(
                question=req.question,
                exclude_hip=req.exclude_hip,
                limit=5,
                provider=provider,
                model=model,
            )
            answer = results.get("answer", "") if isinstance(results, dict) else ""
            res_list = results.get("results", []) if isinstance(results, dict) else results
            return json.dumps({
                "status": "success",
                "action": "creative_cross_query",
                "answer": answer,
                "results": res_list,
                "provider": provider,
                "model": model,
            })
        except ValidationError as e:
            return json.dumps({"status": "error", "message": f"Cross query validation error: {e}"})
        except Exception as e:
            logger.error(f"Error handling cross query: {e}", exc_info=True)
            return json.dumps({"status": "error", "message": str(e)})

    async def _handle_list_projects(self) -> str:
        try:
            projects = self.agent.list_projects()
            return json.dumps({
                "status": "success",
                "action": "creative_list_projects",
                "projects": projects,
            })
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed listing projects: {e}"})

    async def _handle_list_providers(self) -> str:
        import httpx
        core_url = os.environ.get("PMA_CORE_URL", "http://localhost:8000")
        token = os.environ.get("X_LOCAL_ACCESS_TOKEN", "")
        headers = {}
        if token:
            headers["x-local-access-token"] = token
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{core_url.rstrip('/')}/api/providers", headers=headers, timeout=5.0)
                if res.status_code == 200:
                    return json.dumps({
                        "status": "success",
                        "action": "creative_list_providers",
                        "providers": res.json(),
                    })
                return json.dumps({
                    "status": "error",
                    "message": f"Core returned HTTP {res.status_code}",
                })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Could not reach Core providers at {core_url}: {e}",
            })
