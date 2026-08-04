"""Unit tests for PMA Core LLM HTTP client (src/core/pma_llm.py)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import httpx
import pytest

from src.core.pma_llm import chat


def test_pma_llm_chat_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "### Root Cause\nMissing velocity vector."}

    with patch("httpx.post", return_value=mock_resp):
        ans = chat([{"role": "user", "content": "hello"}], provider="ollama", model="llama3")
        assert ans == "### Root Cause\nMissing velocity vector."


def test_pma_llm_chat_401_unauthorized():
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="authentication failed"):
            chat([{"role": "user", "content": "hello"}])


def test_pma_llm_chat_connection_error():
    with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(RuntimeError, match="Could not connect to PMA Core"):
            chat([{"role": "user", "content": "hello"}])
