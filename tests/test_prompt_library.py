"""Unit tests for prompt_library and active Houdini prompts."""
from __future__ import annotations

from src.core.prompt_library import (
    PromptLibrary,
    format_cacheable_prompt,
    HOUDINI_SENIOR_TD_SYSTEM_PROMPT,
)


def test_prompt_library_all_prompts():
    keys = [
        "copilot_td",
        "vex_expert",
        "sim_debugger",
        "cross_search",
        "trial_triage",
    ]
    for k in keys:
        prompt = PromptLibrary.get_prompt(k)
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    assert "VEX Language & Mathematics Specialist" in PromptLibrary.get_prompt("vex_expert")
    assert "DOPs & Dynamics Simulation Specialist" in PromptLibrary.get_prompt("sim_debugger")
    assert "Lead VFX Pipeline Architect" in PromptLibrary.get_prompt("cross_search")


def test_format_cacheable_prompt_with_specialized_prompt():
    formatted = format_cacheable_prompt(
        prompt_name="sim_debugger",
        context_data="## Scene Context\nNode: /obj/dopnet1/pyrosolver1",
        user_query="Why is my flame simulation exploding?",
    )

    assert formatted.startswith(PromptLibrary.get_prompt("sim_debugger"))
    assert "/obj/dopnet1/pyrosolver1" in formatted
    assert "Why is my flame simulation exploding?" in formatted
