"""Unit tests for ZeniAgent RAG retriever and answer synthesis under Python 3.12."""
from __future__ import annotations

import tempfile

from src.core.zeni_agent import ZeniAgent


class MockLLMClient:
    def __init__(self, response_text: str = "Mocked Zeni Response"):
        self.response_text = response_text
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response_text


def test_zeni_agent_ingest_and_retrieve():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    agent = ZeniAgent(db_path=db_path)
    chunks = [
        {
            "node_path": "/obj/geo1/attribwrangle1",
            "node_type": "attribwrangle",
            "comment": "Calculates velocity noise",
            "errors": ["Warning: Undefined variable @vel"],
            "wrangle_code": "v@v += curlnoise(@P * 0.5);",
            "non_default_params": {"snippet": "v@v += curlnoise(@P * 0.5);"},
        }
    ]

    ingest_res = agent.ingest_scene(
        project_name="vfx_fire",
        hip_file="/scenes/vfx_fire.hip",
        chunks=chunks,
        houdini_version="20.5.278",
        platform="win64",
    )
    assert ingest_res["status"] == "success"
    assert ingest_res["chunks_ingested"] == 1

    retrieved = list(agent.retrieve_relevant_chunks("curlnoise", project_name="vfx_fire"))
    assert len(retrieved) == 1
    assert retrieved[0]["node_path"] == "/obj/geo1/attribwrangle1"
    assert "v@v += curlnoise" in retrieved[0]["wrangle_code"]


def test_zeni_agent_generate_answer_with_mock():
    agent = ZeniAgent()
    mock_client = MockLLMClient("### Root Cause\nMissing velocity vector qualifier.")
    answer = agent.generate_answer(
        question="Why is curlnoise failing?",
        chunks=[],
        metadata={"project_name": "vfx_fire"},
        llm_client=mock_client,
    )

    assert answer == "### Root Cause\nMissing velocity vector qualifier."
    assert "Why is curlnoise failing?" in mock_client.last_prompt


def test_zeni_agent_list_projects():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    agent = ZeniAgent(db_path=db_path)
    agent.ingest_scene(
        project_name="proj_a",
        hip_file="/scenes/a.hip",
        chunks=[{"node_path": "/obj/geo1", "node_type": "geo"}],
    )
    projects = agent.list_projects()
    assert len(projects) == 1
    assert projects[0]["project_name"] == "proj_a"
    assert projects[0]["node_count"] == 1
