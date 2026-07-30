"""Autonomous Decision Log Store for Zeni Business Operations."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger("zeni.business.store")

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
DECISION_LOG_PATH = os.path.join(LOGS_DIR, "agent_decisions.jsonl")


def log_agent_decision(
    kind: str,
    input_summary: str,
    decision: dict[str, Any] | str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    latency_ms: float = 0.0,
) -> dict[str, Any]:
    """Append one JSON record to logs/agent_decisions.jsonl with fsync."""
    os.makedirs(LOGS_DIR, exist_ok=True)

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": kind,
        "input_summary": input_summary,
        "decision": decision,
        "provider": provider or "pma_core",
        "model": model or "default",
        "latency_ms": round(latency_ms, 2),
    }

    line = json.dumps(record) + "\n"
    with open(DECISION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())

    logger.info(f"Logged decision '{kind}' to {DECISION_LOG_PATH}")
    return record
