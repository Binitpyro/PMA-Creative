"""Unit tests for decision log store (src/business/store.py)."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from src.business.store import log_agent_decision


def test_log_agent_decision_write_and_fsync():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_log_file = os.path.join(tmpdir, "agent_decisions.jsonl")

        with patch("src.business.store.DECISION_LOG_PATH", test_log_file), \
             patch("src.business.store.LOGS_DIR", tmpdir):

            record = log_agent_decision(
                kind="unit_test_decision",
                input_summary="Testing decision log write",
                decision={"status": "approved", "tier": "Freelancer Tier"},
                model="test-model",
                provider="test-provider",
                latency_ms=12.5,
            )

            assert record["kind"] == "unit_test_decision"
            assert record["provider"] == "test-provider"
            assert os.path.exists(test_log_file)

            with open(test_log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 1
            parsed = json.loads(lines[0])
            assert parsed["kind"] == "unit_test_decision"
            assert parsed["decision"]["tier"] == "Freelancer Tier"
            assert parsed["latency_ms"] == 12.5
