"""Integration test for Zeni standalone extraction, ingest, FTS5 retrieval, and LLM prompt generation."""
from __future__ import annotations

import tempfile
import pytest

from src.core.zeni_agent import ZeniAgent


class MockLLMClient:
    def __init__(self):
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return "### Root Cause\nSyntax error in velocity VEX wrangle."


def test_integration_ingest_fts_search_and_answer():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    agent = ZeniAgent(db_path=db_path)

    # Simulated extractor output from Houdini scene
    extractor_chunks = [
        {
            "node_path": "/obj/geo1/pyro_solver",
            "node_type": "pyrosolver",
            "comment": "Flame simulation solver",
            "vex_snippet": "",
            "non_default_parms": {"buoyancy": "2.5", "substeps": "4"},
            "errors": [],
        },
        {
            "node_path": "/obj/geo1/vel_wrangle",
            "node_type": "attribwrangle",
            "comment": "Applies curlnoise to velocity attribute",
            "vex_snippet": "v@vel += curlnoise(@P * 0.2) * f@strength;",
            "non_default_parms": {"snippet": "v@vel += curlnoise(@P * 0.2) * f@strength;"},
            "errors": ["Warning: Undefined variable f@strength"],
        },
    ]

    # 1. Ingest Extractor Chunks
    ingest_res = agent.ingest_scene(
        project_name="pyro_blast",
        hip_file="/projects/pyro_blast.hip",
        chunks=extractor_chunks,
        houdini_version="20.0.368",
        platform="win64",
    )
    assert ingest_res["status"] == "success"
    assert ingest_res["chunks_ingested"] == 2

    # 2. Assert VEX Token Retrieval (@P and v@vel)
    retrieved_vel = list(agent.retrieve_relevant_chunks("v@vel", project_name="pyro_blast"))
    assert len(retrieved_vel) >= 1
    assert retrieved_vel[0]["node_path"] == "/obj/geo1/vel_wrangle"

    retrieved_p = list(agent.retrieve_relevant_chunks("@P", project_name="pyro_blast"))
    assert len(retrieved_p) >= 1
    assert retrieved_p[0]["node_path"] == "/obj/geo1/vel_wrangle"

    # 3. Assert Query & Answer Generation
    mock_llm = MockLLMClient()
    answer = agent.generate_answer(
        question="How is v@vel calculated in pyro_blast?",
        chunks=retrieved_vel,
        metadata={"project_name": "pyro_blast", "hip_file": "/projects/pyro_blast.hip"},
        llm_client=mock_llm,
    )

    assert "Root Cause" in answer
    assert "v@vel += curlnoise" in mock_llm.last_prompt
    assert "pyro_blast" in mock_llm.last_prompt
