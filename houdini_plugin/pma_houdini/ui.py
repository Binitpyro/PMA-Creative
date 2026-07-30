"""PySide Qt Assistant Panel for Houdini.
Provides a non-blocking floating window inside Houdini's Qt window hierarchy.
"""
from __future__ import annotations

import html
import logging
import sys
from typing import Any

# Flexible Qt imports (PySide6, PySide2, PyQt5)
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except ImportError:
        from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore

logger = logging.getLogger(__name__)

# Global singleton panel instance
_PMA_PANEL_INSTANCE: PMAPanel | None = None


DARK_STYLESHEET = """
QWidget {
    background-color: #242424;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #383838;
    background-color: #242424;
}
QTabBar::tab {
    background-color: #1e1e1e;
    color: #a0a0a0;
    padding: 8px 16px;
    border: 1px solid #333333;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #242424;
    color: #ffffff;
    border-top: 2px solid #007acc;
}
QLineEdit, QComboBox, QTextEdit, QTextBrowser {
    background-color: #1a1a1a;
    color: #f0f0f0;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 6px;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #007acc;
}
QPushButton {
    background-color: #007acc;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #0098ff;
}
QPushButton:pressed {
    background-color: #005c99;
}
QPushButton#secondaryBtn {
    background-color: #383838;
    color: #d0d0d0;
}
QPushButton#secondaryBtn:hover {
    background-color: #4a4a4a;
}
QTableWidget {
    background-color: #1a1a1a;
    gridline-color: #333333;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}
QHeaderView::section {
    background-color: #2d2d2d;
    color: #cccccc;
    padding: 4px;
    border: 1px solid #383838;
}
"""


class PMAPanel(QtWidgets.QDialog):
    """Floating non-blocking PySide Qt Panel for PMA Creative Assistant."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PMA Creative Assistant — Houdini")
        self.resize(600, 520)
        self.setMinimumSize(450, 400)
        self.setStyleSheet(DARK_STYLESHEET)

        # Non-blocking dialog behavior
        self.setWindowFlags(
            QtCore.Qt.WindowType.Window
            | QtCore.Qt.WindowType.WindowMinMaxButtonsHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint
        )

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Chat Assistant
        self.chat_tab = QtWidgets.QWidget()
        self._init_chat_tab()
        self.tabs.addTab(self.chat_tab, "Assistant Chat")

        # Tab 2: Indexed Projects
        self.projects_tab = QtWidgets.QWidget()
        self._init_projects_tab()
        self.tabs.addTab(self.projects_tab, "Project Registry")

        # Status Bar
        self.status_label = QtWidgets.QLabel("PMA Connected over WebSocket")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
        main_layout.addWidget(self.status_label)

    def _init_chat_tab(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.chat_tab)
        layout.setSpacing(8)

        # Top Control Row
        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel("Scope:"))
        self.scope_combo = QtWidgets.QComboBox()
        self.scope_combo.addItems(["Current Scene", "Cross-Project Recall"])
        top_row.addWidget(self.scope_combo)
        top_row.addStretch()

        self.btn_index_quick = QtWidgets.QPushButton("Index Scene Now")
        self.btn_index_quick.setObjectName("secondaryBtn")
        self.btn_index_quick.clicked.connect(self._on_index_scene)
        top_row.addWidget(self.btn_index_quick)

        layout.addLayout(top_row)

        # Chat Response View
        self.chat_display = QtWidgets.QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setHtml(
            "<p style='color: #888888;'><i>Ask any question about your scene or VEX code snippets below...</i></p>"
        )
        layout.addWidget(self.chat_display)

        # Input Area
        input_row = QtWidgets.QHBoxLayout()
        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText("Type a question (e.g. how is buoyancy set in pyro solver)...")
        self.input_field.returnPressed.connect(self._on_send_question)
        input_row.addWidget(self.input_field)

        self.btn_send = QtWidgets.QPushButton("Ask")
        self.btn_send.clicked.connect(self._on_send_question)
        input_row.addWidget(self.btn_send)

        layout.addLayout(input_row)

    def _init_projects_tab(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.projects_tab)

        # Action Button Row
        btn_row = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Refresh List")
        self.btn_refresh.setObjectName("secondaryBtn")
        self.btn_refresh.clicked.connect(self._on_refresh_projects)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Table Widget
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Project Name", "Nodes", "HIP File Path", "Last Indexed"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def _on_send_question(self) -> None:
        question = self.input_field.text().strip()
        if not question:
            return

        self.input_field.clear()
        self.status_label.setText("Querying PMA Core...")
        scope = self.scope_combo.currentText()

        # Render Question in Chat Log
        q_html = f"<div style='margin-bottom: 8px;'><b>You:</b> {html.escape(question)}</div>"
        self.chat_display.append(q_html)

        try:
            from pma_houdini import client

            hip_file = ""
            try:
                import hou
                hip_file = hou.hipFile.path()
            except Exception:
                pass

            if scope == "Current Scene":
                resp = client.ask(question, hip_file=hip_file)
            else:
                resp = client.cross_search(question)

            answer = resp.get("answer", "No answer returned.")
            sources = resp.get("sources", [])

            # Format Answer HTML
            ans_html = (
                f"<div style='background-color: #1e2638; border-left: 3px solid #007acc; "
                f"padding: 8px; border-radius: 4px; margin-bottom: 12px;'>"
                f"<b>PMA Assistant:</b><br/>{html.escape(answer).replace('\n', '<br/>')}"
            )
            if sources:
                src_str = ", ".join(str(s) for s in sources)
                ans_html += f"<br/><br/><small style='color: #88bbff;'>Sources: {html.escape(src_str)}</small>"
            ans_html += "</div>"

            self.chat_display.append(ans_html)
            self.status_label.setText("Done.")
        except Exception as e:
            err_html = f"<div style='color: #ff6b6b;'><b>Error:</b> {html.escape(str(e))}</div>"
            self.chat_display.append(err_html)
            self.status_label.setText("Query Error")

    def _on_index_scene(self) -> None:
        self.status_label.setText("Extracting scene nodes...")
        QtWidgets.QApplication.processEvents()

        try:
            from pma_houdini import client, extractor, version_detect
            import hou

            hip_file = hou.hipFile.path()
            v_info = version_detect.detect_houdini_version()
            chunks = extractor.extract_scene("/obj", max_nodes=10000)

            if not chunks:
                self.status_label.setText("No nodes worth indexing found under /obj.")
                return

            resp = client.ingest_scene(
                hip_file=hip_file,
                chunks=chunks,
                houdini_version=v_info.get("full_version", ""),
                platform=v_info.get("platform", ""),
            )
            indexed_count = resp.get("indexed", len(chunks))
            self.status_label.setText(f"Successfully indexed {indexed_count} nodes.")
            self._on_refresh_projects()
        except Exception as e:
            self.status_label.setText(f"Indexing Error: {e}")

    def _on_refresh_projects(self) -> None:
        try:
            from pma_houdini import client

            projects = client.list_projects()
            self.table.setRowCount(0)

            for p in projects:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(p.get("project_name"))))
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(p.get("node_count"))))
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(p.get("hip_file"))))
                self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(p.get("last_indexed"))))

            self.status_label.setText(f"Loaded {len(projects)} projects.")
        except Exception as e:
            self.status_label.setText(f"Refresh Error: {e}")


def show_pma_panel() -> PMAPanel:
    """Launch or focus the PMA PySide Qt Panel inside Houdini."""
    global _PMA_PANEL_INSTANCE

    parent = None
    try:
        import hou
        parent = hou.qt.mainWindow()
    except Exception:
        pass

    if _PMA_PANEL_INSTANCE is None:
        _PMA_PANEL_INSTANCE = PMAPanel(parent=parent)

    _PMA_PANEL_INSTANCE.show()
    _PMA_PANEL_INSTANCE.raise_()
    _PMA_PANEL_INSTANCE.activateWindow()
    return _PMA_PANEL_INSTANCE
