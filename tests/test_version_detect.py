from unittest.mock import MagicMock, patch
import pytest

from houdini_plugin.pma_houdini import version_detect


def test_detect_houdini_version_mocked():
    mock_hou = MagicMock()
    mock_hou.applicationVersion.return_value = (20, 0, 368)
    mock_hou.applicationVersionString.return_value = "20.0.368"
    mock_hou.applicationPlatformInfo.return_value = "windows-x86_64-cl19.38"
    mock_hou.isApprentice.return_value = False
    mock_hou.hipFile.path.return_value = "/projects/fire_sim.hip"
    mock_hou.hipFile.savedVersion.return_value = "20.0.368"

    with patch.dict("sys.modules", {"hou": mock_hou}):
        info = version_detect.detect_houdini_version()
        assert info["major"] == 20
        assert info["minor"] == 0
        assert info["build"] == 368
        assert info["full_version"] == "20.0.368"
        assert info["platform"] == "windows-x86_64-cl19.38"
        assert info["is_apprentice"] is False
        assert info["hip_file_version"] == "20.0.368"


def test_is_compatible_mocked():
    mock_hou = MagicMock()
    mock_hou.applicationVersion.return_value = (20, 0, 368)

    with patch.dict("sys.modules", {"hou": mock_hou}):
        assert version_detect.is_compatible() is True

    mock_hou.applicationVersion.return_value = (19, 5, 600)
    with patch.dict("sys.modules", {"hou": mock_hou}):
        assert version_detect.is_compatible() is False


def test_get_version_summary_mocked():
    mock_hou = MagicMock()
    mock_hou.applicationVersion.return_value = (20, 0, 368)
    mock_hou.applicationVersionString.return_value = "20.0.368"
    mock_hou.applicationPlatformInfo.return_value = "win64"
    mock_hou.isApprentice.return_value = True

    with patch.dict("sys.modules", {"hou": mock_hou}):
        summary = version_detect.get_version_summary()
        assert "Houdini 20.0.368" in summary
        assert "(Apprentice)" in summary
        assert "win64" in summary
