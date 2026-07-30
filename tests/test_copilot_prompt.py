"""Unit tests for copilot_prompt module under Python 3.12."""
from __future__ import annotations

from src.core.copilot_prompt import (
    HOUDINI_SENIOR_TD_SYSTEM_PROMPT,
    format_scene_context,
)


def test_system_prompt_structure():
    assert "Senior Houdini Technical Director" in HOUDINI_SENIOR_TD_SYSTEM_PROMPT
    assert "### Root Cause" in HOUDINI_SENIOR_TD_SYSTEM_PROMPT
    assert "### VEX / Node Fix" in HOUDINI_SENIOR_TD_SYSTEM_PROMPT
    assert "### Step-by-Step Instructions" in HOUDINI_SENIOR_TD_SYSTEM_PROMPT


def test_format_scene_context_empty():
    res = format_scene_context(metadata={}, chunks=[])
    assert "## Houdini Scene Context" in res
    assert "_No specific node graph chunks matched the query._" in res


def test_format_scene_context_with_chunks():
    metadata = {
        "project_name": "fire_sim",
        "hip_file": "/path/to/fire_sim.hip",
        "houdini_version": "20.5.278",
        "platform": "win64",
    }
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

    res = format_scene_context(metadata, chunks)
    assert "Project / Scene Name**: fire_sim" in res
    assert "Houdini Version**: 20.5.278" in res
    assert "#### Node: `/obj/geo1/attribwrangle1` (attribwrangle)" in res
    assert "v@v += curlnoise(@P * 0.5);" in res
    assert "Warning: Undefined variable @vel" in res
