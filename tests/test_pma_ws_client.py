from unittest.mock import AsyncMock, patch
import pytest

from houdini_plugin.pma_houdini import client


@pytest.fixture
def mock_keyring():
    with patch("keyring.get_password") as mock:
        mock.return_value = "fake-token-123"
        yield mock


def test_client_no_token():
    with patch("keyring.get_password", return_value=None):
        with pytest.raises(RuntimeError, match="X_LOCAL_ACCESS_TOKEN not found"):
            client.ask("test query")


def test_client_ask_success(mock_keyring):
    with patch("websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = (
            '{"status": "success", "action": "creative_query", '
            '"answer": "Wrangle breaks due to frame.", "sources": ["/obj/geo1/wrangle"]}'
        )
        mock_connect.return_value.__aenter__.return_value = mock_ws

        res = client.ask("why does this break", hip_file="/tmp/fire.hip")

        assert res["answer"] == "Wrangle breaks due to frame."
        assert len(res["sources"]) == 1
        assert mock_ws.send.called


def test_client_ingest_scene_success(mock_keyring):
    with patch("websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = (
            '{"status": "success", "action": "creative_ingest", "indexed": 5}'
        )
        mock_connect.return_value.__aenter__.return_value = mock_ws

        chunks = [{"node_path": "/obj/pyro", "node_type": "pyrosolver"}]
        res = client.ingest_scene("/tmp/explosion.hip", chunks)

        assert res["indexed"] == 5
        assert mock_ws.send.called


def test_client_list_projects_success(mock_keyring):
    with patch("websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = (
            '{"status": "success", "action": "creative_list_projects", '
            '"projects": [{"project_name": "explosion", "node_count": 5}]}'
        )
        mock_connect.return_value.__aenter__.return_value = mock_ws

        projects = client.list_projects()

        assert len(projects) == 1
        assert projects[0]["project_name"] == "explosion"
