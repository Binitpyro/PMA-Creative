"""Backwards-compatibility wrapper for ZeniAgent."""
from __future__ import annotations

from src.core.zeni_agent import ZeniAgent as CopilotAgent, ZeniAgent

__all__ = ["CopilotAgent", "ZeniAgent"]
