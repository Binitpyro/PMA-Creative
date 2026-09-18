"""PySide Qt Assistant Panel for Houdini.
Provides a non-blocking floating window inside Houdini's Qt window hierarchy.
"""
from __future__ import annotations

import html
import logging
import os
import re
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


def _format_markdown_to_html(text: str) -> str:
    """Format markdown text into HTML with formatted pre/code VEX blocks."""
    # First extract code blocks
    code_blocks = []

    def save_block(match):
        code_content = match.group(1)
        code_blocks.append(code_content)
        return f"___CODE_BLOCK_{len(code_blocks)-1}___"

    pattern = r"```(?:c|vex|python)?\s*([\s\S]*?)\s*```"
    text_without_code = re.sub(pattern, save_block, text)

    escaped = html.escape(text_without_code).replace("\n", "<br/>")

    for idx, code in enumerate(code_blocks):
        code_escaped = html.escape(code)
        block_html = f"<pre style='background-color: #111; color: #00ffcc; padding: 8px; border-radius: 4px; font-family: Consolas, monospace;'><code>{code_escaped}</code></pre>"
        escaped = escaped.replace(f"___CODE_BLOCK_{idx}___", block_html)

    return escaped


class PMAPanel(QtWidgets.QDialog):
    """Floating non-blocking PySide Qt Panel for PMA Creative Assistant."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PMA Creative Assistant — Houdini")
        self.resize(650, 550)
        self.setMinimumSize(480, 420)
        self.setStyleSheet(DARK_STYLESHEET)

        # PySide2 vs PySide6 safe window flags
        window_flag = getattr(QtCore.Qt, "Window", getattr(getattr(QtCore.Qt, "WindowType", None), "Window", None))
        min_max_flag = getattr(QtCore.Qt, "WindowMinMaxButtonsHint", getattr(getattr(QtCore.Qt, "WindowType", None), "WindowMinMaxButtonsHint", None))
        close_flag = getattr(QtCore.Qt, "WindowCloseButtonHint", getattr(getattr(QtCore.Qt, "WindowType", None), "WindowCloseButtonHint", None))

        flags = window_flag
        if min_max_flag:
            flags |= min_max_flag
        if close_flag:
            flags |= close_flag

        if flags:
            self.setWindowFlags(flags)

        self._init_ui()
        
        from pma_houdini import client, events
        client.start_client(self._on_ws_message, self._on_ws_connected, self._on_ws_disconnected)
        events.register_callbacks()

    def _init_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Splitter for Sidecar
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # Left side: Tabs
        self.tabs = QtWidgets.QTabWidget()
        self.splitter.addWidget(self.tabs)

        # Right side: Sidecar Insights
        self._init_sidecar()
        self.splitter.addWidget(self.sidecar_widget)
        self.splitter.setSizes([450, 200])

        # Tab 1: Chat Assistant
        self.chat_tab = QtWidgets.QWidget()
        self._init_chat_tab()
        self.tabs.addTab(self.chat_tab, "Assistant Chat")

        # Tab 2: Indexed Projects
        self.projects_tab = QtWidgets.QWidget()
        self._init_projects_tab()
        self.tabs.addTab(self.projects_tab, "Project Registry")

        # Tab 3: Settings (Provider / Model Selection)
        self.settings_tab = QtWidgets.QWidget()
        self._init_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")

        self.status_label = QtWidgets.QLabel("Connecting to Zeni Core over WebSocket...")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
        main_layout.addWidget(self.status_label)

    def _init_sidecar(self) -> None:
        self.sidecar_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.sidecar_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        lbl = QtWidgets.QLabel("Sidecar Insights")
        lbl.setStyleSheet("font-weight: bold; color: #007acc;")
        layout.addWidget(lbl)
        
        self.sidecar_list = QtWidgets.QListWidget()
        self.sidecar_list.setWordWrap(True)
        self.sidecar_list.setStyleSheet("background-color: #1a1a1a; border: 1px solid #3d3d3d;")
        layout.addWidget(self.sidecar_list)

    def _on_ws_connected(self):
        self.status_label.setText("Zeni Core Connected")

    def _on_ws_disconnected(self, err):
        self.status_label.setText(f"Disconnected: {err}")

    def _on_ws_message(self, msg):
        if msg.get("action") == "scene.upsert" and msg.get("insights"):
            for ins in msg.get("insights"):
                insight_data = ins.get("insight")
                if insight_data:
                    path = ins.get("node_path")
                    text = f"[{insight_data.get('insight_type')}] {path}: {insight_data.get('message')}"
                    item = QtWidgets.QListWidgetItem(text)
                    self.sidecar_list.insertItem(0, item)

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

    def _get_settings_file_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        settings_dir = os.path.join(base_dir, "data")
        os.makedirs(settings_dir, exist_ok=True)
        return os.path.join(settings_dir, "settings.json")

    def _load_settings(self) -> None:
        try:
            path = self._get_settings_file_path()
            if os.path.exists(path):
                import json
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "core_url" in data:
                    self.input_core_url.setText(data["core_url"])
                if "token" in data:
                    self.input_token.setText(data["token"])
                if "provider" in data:
                    idx = self.combo_provider.findText(data["provider"])
                    if idx >= 0:
                        self.combo_provider.setCurrentIndex(idx)
                    else:
                        self.combo_provider.addItem(data["provider"])
                        self.combo_provider.setCurrentText(data["provider"])
                if "model" in data:
                    self.input_model.setText(data["model"])
        except Exception as e:
            logger.warning(f"Could not load UI settings: {e}")

    def _save_settings(self) -> None:
        try:
            path = self._get_settings_file_path()
            import json
            data = {
                "core_url": self.input_core_url.text().strip(),
                "token": self.input_token.text().strip(),
                "provider": self.combo_provider.currentText().strip(),
                "model": self.input_model.text().strip(),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save UI settings: {e}")

    def _init_settings_tab(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.settings_tab)
        form_layout = QtWidgets.QFormLayout()

        self.input_core_url = QtWidgets.QLineEdit("http://localhost:8000")
        form_layout.addRow("PMA Core URL:", self.input_core_url)

        self.input_token = QtWidgets.QLineEdit()
        self.input_token.setEchoMode(QtWidgets.QLineEdit.Password)
        self.input_token.setPlaceholderText("Optional access token")
        form_layout.addRow("Access Token:", self.input_token)

        self.combo_provider = QtWidgets.QComboBox()
        self.combo_provider.addItems([
            "ollama", "lm_studio", "openai", "anthropic", "gemini",
            "groq", "openrouter", "nvidia_nim", "openai_compatible"
        ])
        form_layout.addRow("LLM Provider:", self.combo_provider)

        self.input_model = QtWidgets.QLineEdit("llama3")
        self.input_model.setPlaceholderText("e.g. llama3, gpt-4o, claude-3-5-sonnet")
        form_layout.addRow("Model Name:", self.input_model)

        layout.addLayout(form_layout)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_load_providers = QtWidgets.QPushButton("Refresh Providers from Core")
        self.btn_load_providers.setObjectName("secondaryBtn")
        self.btn_load_providers.clicked.connect(self._on_load_providers)
        btn_row.addWidget(self.btn_load_providers)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

        self.input_core_url.textChanged.connect(self._save_settings)
        self.input_token.textChanged.connect(self._save_settings)
        self.combo_provider.currentTextChanged.connect(self._save_settings)
        self.input_model.textChanged.connect(self._save_settings)

        self._load_settings()

    def _on_send_question(self) -> None:
        question = self.input_field.text().strip()
        if not question:
            return

        self.input_field.clear()
        self.status_label.setText("Querying Zeni Assistant...")
        scope = self.scope_combo.currentText()
        provider = self.combo_provider.currentText().strip()
        model = self.input_model.text().strip()

        # Render Question in Chat Log
        q_html = f"<div style='margin-bottom: 8px;'><b>You:</b> {html.escape(question)}</div>"
        self.chat_display.append(q_html)

        from pma_houdini import client

        hip_file = ""
        try:
            import hou
            hip_file = hou.hipFile.path()
        except Exception:
            pass

        def on_response(resp):
            if resp.get("status") == "error":
                err_html = f"<div style='color: #ff6b6b;'><b>Error:</b> {html.escape(resp.get('message', ''))}</div>"
                self.chat_display.append(err_html)
                self.status_label.setText("Query Error")
                return
                
            answer = resp.get("answer", "No answer returned.")
            used_prov = resp.get("provider") or provider
            used_model = resp.get("model") or model

            ans_html = (
                f"<div style='background-color: #1e2638; border-left: 3px solid #007acc; "
                f"padding: 8px; border-radius: 4px; margin-bottom: 12px;'>"
                f"<b>Zeni Assistant</b> <small style='color: #888888;'>({used_prov} / {used_model})</small>:<br/>"
                f"{_format_markdown_to_html(answer)}</div>"
            )
            self.chat_display.append(ans_html)
            self.status_label.setText("Done.")

        if scope == "Current Scene":
            client.ask(question, hip_file=hip_file, provider=provider, model=model, callback=on_response)
        else:
            client.cross_search(question, provider=provider, model=model, callback=on_response)

    def _on_index_scene(self) -> None:
        self.status_label.setText("Extracting scene nodes...")

        from pma_houdini import client, extractor, version_detect
        import hou

        try:
            hip_file = hou.hipFile.path()
            v_info = version_detect.detect_houdini_version()
            chunks = extractor.extract_scene("/obj", max_nodes=10000)

            if not chunks:
                self.status_label.setText("No nodes worth indexing found under /obj.")
                return

            def on_response(resp):
                if resp.get("status") == "error":
                    self.status_label.setText(f"Indexing Error: {resp.get('message')}")
                    return
                count = resp.get("chunks_ingested", len(chunks))
                self.status_label.setText(f"Successfully indexed {count} nodes.")
                self._on_refresh_projects()

            client.ingest_scene(
                hip_file=hip_file,
                chunks=chunks,
                houdini_version=v_info.get("full_version", ""),
                platform=v_info.get("platform", ""),
                callback=on_response
            )

        except Exception as e:
            self.status_label.setText(f"Extraction Error: {e}")

    def _on_refresh_projects(self) -> None:
        from pma_houdini import client

        def on_response(res):
            if res.get("status") == "error":
                self.status_label.setText(f"Refresh Error: {res.get('message')}")
                return
            projects = res.get("projects", [])
            self.table.setRowCount(0)
            for p in projects:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(p.get("project_name"))))
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(p.get("node_count"))))
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(p.get("hip_file"))))
                self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(p.get("last_indexed"))))

            self.status_label.setText(f"Loaded {len(projects)} projects.")

        client.list_projects(callback=on_response)

    def _on_load_providers(self) -> None:
        from pma_houdini import client

        self.status_label.setText("Fetching providers from PMA Core...")
        def on_response(res):
            if res.get("status") == "error":
                self.status_label.setText(f"Could not load providers: {res.get('message')}")
                return
            providers = res.get("providers", [])
            if providers:
                self.combo_provider.clear()
                for p in providers:
                    p_name = p.get("id") or p.get("name")
                    if p_name:
                        self.combo_provider.addItem(p_name)
                self.status_label.setText(f"Loaded {len(providers)} providers from Core.")
            else:
                self.status_label.setText("No custom providers returned from Core.")

        client.list_providers(callback=on_response)


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
