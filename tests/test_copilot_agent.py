"""Unit tests for copilot_agent RAG retriever and LLM coordinator."""
from __future__ import annotations

import sqlite3
import tempfile

from src.core.copilot_agent import CopilotAgent


class MockLLMClient:
    def __init__(self, response_text: str = "Mocked LLM Response"):
        self.response_text = response_text
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response_text


def test_copilot_agent_build_prompt():
    agent = CopilotAgent()
    chunks = [
        {
            "node_path": "/obj/geo1/wrangle",
            "node_type": "attribwrangle",
            "wrangle_code": "@P.y += 1.0;",
        }
    ]
    metadata = {"project_name": "test_proj"}
    prompt = agent.build_prompt("Why is geometry floating?", chunks, metadata)

    assert "Senior Houdini Technical Director" in prompt
    assert "Why is geometry floating?" in prompt
    assert "test_proj" in prompt
    assert "@P.y += 1.0;" in prompt


def test_copilot_agent_generate_answer_with_mock():
    agent = CopilotAgent()
    mock_client = MockLLMClient("### Root Cause\nGeometry moved upward.")
    answer = agent.generate_answer(
        question="Why offset?",
        chunks=[],
        metadata={"project_name": "demo"},
        llm_client=mock_client,
    )

    assert answer == "### Root Cause\nGeometry moved upward."
    assert "Why offset?" in mock_client.last_prompt


def test_copilot_agent_fts_retrieval():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE scene_chunks (
            id INTEGER PRIMARY KEY,
            project_name TEXT,
            node_path TEXT,
            node_type TEXT,
            comment TEXT,
            wrangle_code TEXT,
            non_default_params TEXT,
            errors TEXT
        )
    """)
    cursor.execute("""
        CREATE VIRTUAL TABLE scene_chunks_fts USING fts5(
            node_path, comment, wrangle_code, errors
        )
    """)

    cursor.execute("""
        INSERT INTO scene_chunks (project_name, node_path, node_type, wrangle_code)
        VALUES ('vfx_fire', '/obj/geo1/popwrangle', 'popwrangle', 'v@vel += @N * 10;')
    """)
    rowid = cursor.lastrowid
    cursor.execute("""
        INSERT INTO scene_chunks_fts (rowid, node_path, comment, wrangle_code, errors)
        VALUES (?, '/obj/geo1/popwrangle', '', 'v@vel += @N * 10;', '')
    """, (rowid,))
    conn.commit()
    conn.close()

    agent = CopilotAgent(db_path=db_path)
    retrieved = list(agent.retrieve_relevant_chunks("popwrangle", project_name="vfx_fire"))

    assert len(retrieved) == 1
    assert retrieved[0]["node_path"] == "/obj/geo1/popwrangle"
    assert "v@vel += @N * 10;" in retrieved[0]["wrangle_code"]
