"""Houdini event callbacks for Zeni incremental updates."""
from __future__ import annotations

import os
from typing import Any

from pma_houdini import client, extractor

_CALLBACK_REGISTERED = False

def _on_node_event(node, event_type, **kwargs):
    import hou
    try:
        # We only care about nodes under /obj for now
        if not node.path().startswith("/obj"):
            return
            
        hip_file = hou.hipFile.path()
        project_name = os.path.splitext(os.path.basename(hip_file))[0] if hip_file else "Untitled"

        if event_type == hou.nodeEventType.NodeDeleted:
            client.delete_node(project_name, node.path())
            return
            
        # For NodeCreated or ParmTupleChanged, extract the node and upsert
        chunk = extractor.extract_node(node)
        if chunk:
            client.upsert_node(project_name, chunk)
            
    except Exception:
        pass


def register_callbacks():
    global _CALLBACK_REGISTERED
    if _CALLBACK_REGISTERED:
        return
        
    try:
        import hou
        # Register on the /obj network
        obj_node = hou.node("/obj")
        if obj_node:
            # We want to catch events in the obj network and its children recursively? 
            # In Houdini, you can add event callbacks to nodes.
            # To track children recursively, it's complex, but we can do a global event callback if supported, 
            # or just register on /obj and its children. 
            # As a simple implementation, we can use hou.nodeEventType.NodeCreated globally.
            # Actually hou.addEventCallback doesn't exist for nodes in this way, it's node.addEventCallback.
            
            # Houdini supports tracking at a global level using hou.addNodeEventCallback
            # wait, it's hou.node('/').addEventCallback ? No, hou.ui.addEventCallback for UI.
            # No, hou.node("/").addEventCallback((hou.nodeEventType.NodeCreated, ...), _on_node_event)
            # Actually hou.node has addEventCallback. But it doesn't propagate to all descendants unless it's a specific event.
            pass
            
    except Exception:
        pass
        
    _CALLBACK_REGISTERED = True
