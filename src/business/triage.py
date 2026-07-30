"""Autonomous Trial Triage Agent for customer signups."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from src.business.store import log_agent_decision
from src.core.pma_llm import chat as pma_llm_chat
from src.core.prompt_library import PromptLibrary

logger = logging.getLogger("zeni.business.triage")


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` markdown code block wrappers."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def triage_trial_signup(
    signup_data: dict[str, Any],
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Autonomous triage of incoming trial signup requests using Core LLM provider."""
    start_time = time.time()
    user_name = signup_data.get("name", "Applicant")
    email = signup_data.get("email", "")
    organization = signup_data.get("organization", "Individual")
    use_case = signup_data.get("use_case", "General Houdini TD work")

    input_summary = f"Applicant: {user_name} ({organization}) | Email domain: {email.split('@')[-1] if '@' in email else 'unknown'} | Use-case: {use_case[:100]}"
    triage_prompt = PromptLibrary.get_prompt("trial_triage")

    user_payload = (
        f"Trial Signup Request:\n"
        f"- Name: {user_name}\n"
        f"- Organization: {organization}\n"
        f"- Primary Use-Case: {use_case}\n"
    )

    messages = [
        {"role": "system", "content": triage_prompt},
        {"role": "user", "content": user_payload},
    ]

    try:
        raw_response = pma_llm_chat(messages, provider=provider, model=model)
        clean_json_str = _strip_markdown_fences(raw_response)
        decision_data = json.loads(clean_json_str)

        recommended_tier = decision_data.get("recommended_tier", "Freelancer Tier")
        reasoning = decision_data.get("reasoning", "Standard individual artist evaluation.")
        onboarding_note = decision_data.get("personalized_onboarding_note", "Welcome to Zeni Creative Assistant!")
    except Exception as e:
        logger.warning(f"Trial triage LLM evaluation failed or returned malformed JSON: {e}")
        recommended_tier = "Freelancer Tier"
        reasoning = f"Default fallback tier assigned due to triage parsing error: {e}"
        onboarding_note = "Welcome to Zeni! Your trial has been activated."
        decision_data = {
            "recommended_tier": recommended_tier,
            "reasoning": reasoning,
            "personalized_onboarding_note": onboarding_note,
            "error": str(e),
        }

    elapsed_ms = (time.time() - start_time) * 1000.0

    # Log autonomous decision with fsync
    log_agent_decision(
        kind="trial_triage",
        input_summary=input_summary,
        decision=decision_data,
        provider=provider or "pma_core",
        model=model or "default",
        latency_ms=elapsed_ms,
    )

    stripe_link = "https://buy.stripe.com/test_zeni_creative_trial"

    return {
        "status": "success",
        "name": user_name,
        "recommended_tier": recommended_tier,
        "reasoning": reasoning,
        "onboarding_note": onboarding_note,
        "stripe_checkout_url": stripe_link,
    }
