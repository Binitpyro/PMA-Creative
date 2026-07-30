"""Unit tests for PySide Qt Assistant Panel (pma_houdini.ui).
Automatically skipped in non-GUI test environments missing Qt bindings.
"""
from __future__ import annotations

import pytest

# Skip gracefully if Qt bindings are not installed in the local pytest runner
# (Qt bindings are natively provided in Houdini's Python 3.10 environment).
try:
    from PySide6 import QtWidgets
    HAS_QT = True
except ImportError:
    try:
        from PySide2 import QtWidgets  # type: ignore
        HAS_QT = True
    except ImportError:
        HAS_QT = False

pytestmark = pytest.mark.skipif(not HAS_QT, reason="Qt bindings (PySide6/PySide2) not installed in local runner")


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication instance exists for Qt widget testing."""
    if not HAS_QT:
        pytest.skip("Qt bindings unavailable")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


def test_pma_panel_instantiation(qapp):
    """Test that PMAPanel initializes widgets cleanly without errors."""
    from pma_houdini import ui

    panel = ui.PMAPanel()
    assert panel.windowTitle() == "PMA Creative Assistant — Houdini"
    assert panel.tabs.count() == 3
    assert panel.input_field is not None
    assert panel.chat_display is not None
    assert panel.table is not None
    panel.close()


def test_pma_panel_send_question(qapp, monkeypatch):
    """Test typing a question and receiving an answer in the chat display."""
    from pma_houdini import ui, client

    panel = ui.PMAPanel()

    def fake_ask(question, hip_file=None, provider=None, model=None):
        return {
            "status": "success",
            "answer": "Buoyancy controls upward force in fire simulation.",
            "sources": ["houdini://fire_explosion"],
        }

    monkeypatch.setattr(client, "ask", fake_ask)

    panel.input_field.setText("What does buoyancy do?")
    panel._on_send_question()

    if panel.workers:
        panel.workers[-1].wait()
        qapp.processEvents()

    chat_text = panel.chat_display.toHtml()
    assert "What does buoyancy do?" in chat_text
    assert "Buoyancy controls upward force" in chat_text
    panel.close()


def test_show_pma_panel_singleton(qapp):
    """Test that show_pma_panel creates and returns the singleton instance."""
    from pma_houdini import ui

    panel1 = ui.show_pma_panel()
    panel2 = ui.show_pma_panel()
    assert panel1 is panel2
    panel1.close()
