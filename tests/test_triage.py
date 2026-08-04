"""Unit tests for trial triage agent (src/business/triage.py)."""
from __future__ import annotations

import json
from unittest.mock import patch

from src.business.triage import _strip_markdown_fences, triage_trial_signup


def test_strip_markdown_fences():
    fenced = "```json\n{\"recommended_tier\": \"Studio Tier\"}\n```"
    stripped = _strip_markdown_fences(fenced)
    assert stripped == '{"recommended_tier": "Studio Tier"}'


def test_triage_trial_signup_success():
    mock_llm_resp = '```json\n{"recommended_tier": "Studio Tier", "reasoning": "Large VFX studio", "personalized_onboarding_note": "Welcome!"}\n```'

    signup_data = {
        "name": "Jane Doe",
        "email": "jane@vfxstudio.com",
        "organization": "Mega VFX",
        "use_case": "Crowd simulation pipeline",
    }

    with patch("src.business.triage.pma_llm_chat", return_value=mock_llm_resp), \
         patch("src.business.triage.log_agent_decision") as mock_log:

        res = triage_trial_signup(signup_data, provider="openai", model="gpt-4o")

        assert res["status"] == "success"
        assert res["recommended_tier"] == "Studio Tier"
        assert res["stripe_checkout_url"] is not None
        assert mock_log.called


def test_triage_trial_signup_malformed_json_fallback():
    mock_llm_resp = "Plain text response without JSON structure"

    signup_data = {
        "name": "Bob Smith",
        "email": "bob@indie.com",
        "organization": "Solo Artist",
        "use_case": "Pyro wrangles",
    }

    with patch("src.business.triage.pma_llm_chat", return_value=mock_llm_resp), \
         patch("src.business.triage.log_agent_decision") as mock_log:

        res = triage_trial_signup(signup_data)

        assert res["status"] == "success"
        assert res["recommended_tier"] == "Freelancer Tier"
        assert mock_log.called
