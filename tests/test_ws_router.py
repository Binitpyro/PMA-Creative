"""Unit tests for ZeniWSRouter and WebSocket action dispatches."""
from __future__ import annotations

import json
import tempfile
import pytest

from src.core.zeni_agent import ZeniAgent
from src.server.ws_router import ZeniWSRouter


@pytest.mark.asyncio
async def test_ws_router_unauthorized():
    router = ZeniWSRouter()
    res_str = await router.handle_message(
        json.dumps({"action": "creative_list_projects"}), token="invalid_token"
    )
    res = json.loads(res_str)
    assert res["status"] == "error"
    assert "Unauthorized" in res["message"]


@pytest.mark.asyncio
async def test_ws_router_ingest_and_query(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    agent = ZeniAgent(db_path=db_path)
    router = ZeniWSRouter(agent=agent)

    # Monkeypatch verify_access_token for unit test environment
    monkeypatch.setattr("src.server.ws_router.verify_access_token", lambda t: True)

    ingest_msg = json.dumps({
        "action": "creative_ingest",
        "project_name": "test_sim",
        "hip_file": "/scenes/test_sim.hip",
        "chunks": [
            {
                "path": "/obj/geo1/attribwrangle1",
                "type": "attribwrangle",
                "comment": "Initial velocity wrangle",
                "wrangle_code": "v@v = set(0, 1, 0);",
                "errors": [],
                "non_default_params": {},
            }
        ],
        "houdini_version": "20.5.278",
        "platform": "win64",
    })

    ingest_res_str = await router.handle_message(ingest_msg, token="dev_token")
    ingest_res = json.loads(ingest_res_str)
    assert ingest_res["status"] == "success"
    assert ingest_res["chunks_ingested"] == 1

    # Test Query Action
    query_msg = json.dumps({
        "action": "creative_query",
        "question": "How is initial velocity set?",
        "project_name": "test_sim",
    })
    query_res_str = await router.handle_message(query_msg, token="dev_token")
    query_res = json.loads(query_res_str)
    assert query_res["status"] == "success"
    assert "answer" in query_res
    assert query_res["chunks_retrieved"] == 1

    # Test List Projects Action
    list_msg = json.dumps({"action": "creative_list_projects"})
    list_res_str = await router.handle_message(list_msg, token="dev_token")
    list_res = json.loads(list_res_str)
    assert list_res["status"] == "success"
    assert len(list_res["projects"]) == 1
    assert list_res["projects"][0]["project_name"] == "test_sim"
