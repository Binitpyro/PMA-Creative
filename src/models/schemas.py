"""PMA Creative Module schemas and models."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class IngestChunk(BaseModel):
    node_path: str
    node_type: str
    comment: str = ""
    vex_snippet: str = ""
    non_default_parms: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class CreativeIngestRequest(BaseModel):
    action: str = "creative_ingest"
    project_name: str
    hip_file: str = ""
    chunks: list[IngestChunk] = Field(default_factory=list)
    houdini_version: str = ""
    platform: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreativeQueryRequest(BaseModel):
    action: str = "creative_query"
    question: str
    project_name: Optional[str] = None


class CreativeCrossQueryRequest(BaseModel):
    action: str = "creative_cross_query"
    question: str
    exclude_hip: Optional[str] = None


class CreativeListProvidersRequest(BaseModel):
    action: str = "creative_list_providers"


class CreativeResponse(BaseModel):
    status: str = "success"
    action: str
    answer: str = ""
    chunks_retrieved: int = 0
    message: Optional[str] = None

