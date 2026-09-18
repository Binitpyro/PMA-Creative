"""Direct WebSocket client for Zeni in Houdini."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any, Optional, Dict, Callable

import keyring
import websockets

try:
    from PySide6 import QtCore
except ImportError:
    try:
        from PySide2 import QtCore  # type: ignore
    except ImportError:
        from PyQt5 import QtCore  # type: ignore

# Use Core URL (8000) since we are folding Zeni into Core /modules/ws
ZENI_WS_URL = os.environ.get(
    "ZENI_WS_URL", "ws://localhost:8000/ws"
)

class ZeniWSClient(QtCore.QThread):
    """Background QThread holding the WebSocket connection."""
    connected = QtCore.Signal()
    disconnected = QtCore.Signal(str)
    message_received = QtCore.Signal(dict)
    
    def __init__(self, url: str, token: str):
        super().__init__()
        self.url = url
        self.token = token
        self._loop = None
        self._ws = None
        self._is_running = True
        
    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_listen())
        
    async def _connect_and_listen(self):
        headers = {"x-local-access-token": self.token}
        try:
            async with websockets.connect(self.url, additional_headers=headers) as ws:
                self._ws = ws
                self.connected.emit()
                while self._is_running:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        self.message_received.emit(json.loads(msg))
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
        except Exception as e:
            self.disconnected.emit(str(e))
        finally:
            self._ws = None
            self.disconnected.emit("Connection closed")
            
    def send_message(self, payload: dict) -> None:
        if self._ws and self._loop:
            msg_str = json.dumps(payload)
            asyncio.run_coroutine_threadsafe(self._ws.send(msg_str), self._loop)
            
    def stop(self):
        self._is_running = False
        self.quit()


_CLIENT_INSTANCE = None
_PENDING_REQUESTS: Dict[str, Callable] = {}


def get_token() -> str:
    token = None
    try:
        token = keyring.get_password("ZeniCreativeModule", "ZENI_ACCESS_TOKEN")
    except Exception:
        pass
    if not token:
        token = os.environ.get("ZENI_ACCESS_TOKEN") or os.environ.get("X_LOCAL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Access token not found.")
    return token


def start_client(on_message: Callable[[dict], None], on_connected: Callable[[], None], on_disconnected: Callable[[str], None]):
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is not None:
        return
    token = get_token()
    _CLIENT_INSTANCE = ZeniWSClient(ZENI_WS_URL, token)
    
    def handle_msg(msg):
        req_id = msg.get("req_id")
        if req_id and req_id in _PENDING_REQUESTS:
            _PENDING_REQUESTS.pop(req_id)(msg)
        else:
            on_message(msg)
            
    _CLIENT_INSTANCE.message_received.connect(handle_msg)
    _CLIENT_INSTANCE.connected.connect(on_connected)
    _CLIENT_INSTANCE.disconnected.connect(on_disconnected)
    _CLIENT_INSTANCE.start()


def stop_client():
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE:
        _CLIENT_INSTANCE.stop()
        _CLIENT_INSTANCE = None


def _send_action_async(action: str, payload: dict[str, Any], callback: Callable[[dict], None]):
    if not _CLIENT_INSTANCE:
        callback({"status": "error", "message": "WebSocket client not running"})
        return
        
    req_id = str(uuid.uuid4())
    _PENDING_REQUESTS[req_id] = callback
    
    msg = {"action": action, "req_id": req_id, **payload}
    _CLIENT_INSTANCE.send_message(msg)


def ingest_scene(
    hip_file: str,
    chunks: list[dict[str, Any]],
    houdini_version: str = "",
    platform: str = "",
    metadata: Optional[dict[str, Any]] = None,
    callback: Callable[[dict], None] = lambda r: None,
):
    project_name = os.path.splitext(os.path.basename(hip_file))[0] if hip_file else "Untitled"
    _send_action_async("creative_ingest", {
        "project_name": project_name,
        "hip_file": hip_file,
        "chunks": chunks,
        "houdini_version": houdini_version,
        "platform": platform,
        "metadata": metadata or {},
    }, callback)


def ask(
    question: str,
    hip_file: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    callback: Callable[[dict], None] = lambda r: None,
):
    project_name = os.path.splitext(os.path.basename(hip_file))[0] if hip_file else None
    payload: dict[str, Any] = {"question": question, "project_name": project_name}
    if provider: payload["provider"] = provider
    if model: payload["model"] = model
    _send_action_async("creative_query", payload, callback)


def cross_search(
    question: str,
    exclude_hip: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    callback: Callable[[dict], None] = lambda r: None,
):
    payload: dict[str, Any] = {"question": question, "exclude_hip": exclude_hip}
    if provider: payload["provider"] = provider
    if model: payload["model"] = model
    _send_action_async("creative_cross_query", payload, callback)


def upsert_node(
    project_name: str,
    node_data: dict[str, Any],
    callback: Callable[[dict], None] = lambda r: None,
):
    _send_action_async("scene.upsert", {
        "project_name": project_name,
        "nodes": [node_data]
    }, callback)


def delete_node(
    project_name: str,
    node_path: str,
    callback: Callable[[dict], None] = lambda r: None,
):
    _send_action_async("scene.delete", {
        "project_name": project_name,
        "node_path": node_path
    }, callback)


def list_projects(callback: Callable[[dict], None] = lambda r: None):
    _send_action_async("creative_list_projects", {}, callback)


def list_providers(callback: Callable[[dict], None] = lambda r: None):
    _send_action_async("creative_list_providers", {}, callback)
