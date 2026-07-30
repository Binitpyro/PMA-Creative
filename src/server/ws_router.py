"""Zeni WebSocket Message Router and Connection Handler."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import keyring
from pydantic import ValidationError

from src.core.zeni_agent import ZeniAgent
from src.models.schemas import (
    CreativeCrossQueryRequest,
    CreativeIngestRequest,
    CreativeQueryRequest,
)

logger = logging.getLogger("zeni.server")


def verify_access_token(token: Optional[str]) -> bool:
    """Verify x-local-access-token against OS keyring or environment fallback."""
    expected_token = keyring.get_password("PersonalMemoryAssistant", "X_LOCAL_ACCESS_TOKEN")
    if not expected_token:
        expected_token = os.environ.get("X_LOCAL_ACCESS_TOKEN", "dev_token")

    if not token or token != expected_token:
        return False
    return True


class ZeniWSRouter:
    """Async WebSocket message router for Zeni actions."""

    def __init__(self, agent: Optional[ZeniAgent] = None):
        self.agent = agent or ZeniAgent()

    async def handle_message(self, raw_message: str, token: Optional[str] = None) -> str:
        """Parse raw JSON string and dispatch Zeni action."""
        if not verify_access_token(token):
            return json.dumps({
                "status": "error",
                "message": "Unauthorized: Invalid or missing x-local-access-token",
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

    async def _handle_query(self, payload: dict[str, Any]) -> str:
        try:
            req = CreativeQueryRequest(**payload)
            relevant_chunks = list(
                self.agent.retrieve_relevant_chunks(
                    query=req.question, project_name=req.project_name, limit=10
                )
            )
            metadata = {"project_name": req.project_name} if req.project_name else {}
            answer = self.agent.generate_answer(
                question=req.question,
                chunks=relevant_chunks,
                metadata=metadata,
            )
            return json.dumps({
                "status": "success",
                "action": "creative_query",
                "answer": answer,
                "chunks_retrieved": len(relevant_chunks),
            })
        except ValidationError as e:
            return json.dumps({"status": "error", "message": f"Query validation error: {e}"})

    async def _handle_cross_query(self, payload: dict[str, Any]) -> str:
        try:
            req = CreativeCrossQueryRequest(**payload)
            results = self.agent.cross_search(
                question=req.question, exclude_hip=req.exclude_hip, limit=5
            )
            return json.dumps({
                "status": "success",
                "action": "creative_cross_query",
                "results": results,
            })
        except ValidationError as e:
            return json.dumps({"status": "error", "message": f"Cross query validation error: {e}"})

    async def _handle_list_projects(self) -> str:
        projects = self.agent.list_projects()
        return json.dumps({
            "status": "success",
            "action": "creative_list_projects",
            "projects": projects,
        })
