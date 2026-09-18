"""PMA Creative Module schemas and models."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class IngestChunk(BaseModel):
    node_path: str = Field(alias="path", default="")
    node_type: str = Field(alias="type", default="")
    comment: str = ""
    # Legacy fields
    vex_snippet: str = ""
    non_default_parms: dict[str, Any] = Field(default_factory=dict)
    # New DCC agnostic fields
    dcc_properties: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    connections: list[dict[str, Any]] = Field(default_factory=list)
    hda_doc: str = ""
    assets: list[str] = Field(default_factory=list)
    scene: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class CreativeIngestRequest(BaseModel):
    action: str = "creative_ingest"
    project_name: str
    hip_file: str = ""
    chunks: list[IngestChunk] = Field(default_factory=list)
    houdini_version: str = ""
    platform: str = ""
    schema_version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreativeUpsertNodesRequest(BaseModel):
    action: str = "scene.upsert"
    project_name: str
    nodes: list[IngestChunk] = Field(default_factory=list)


class CreativeDeleteNodeRequest(BaseModel):
    action: str = "scene.delete"
    project_name: str
    node_path: str


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

