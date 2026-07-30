"""PMA Creative Module schemas and models."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class IngestChunk(BaseModel):
    path: str
    type: str
    comment: str = ""
    wrangle_code: str = ""
    errors: list[str] = Field(default_factory=list)
    non_default_params: dict[str, Any] = Field(default_factory=dict)


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


class CreativeResponse(BaseModel):
    status: str = "success"
    action: str
    answer: str = ""
    chunks_retrieved: int = 0
    message: Optional[str] = None
