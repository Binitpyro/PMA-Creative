"""Blender node extractor for Zeni."""
import bpy
from typing import Any, Dict, List

def extract_node(node: bpy.types.Node, tree_path: str) -> Dict[str, Any]:
    """Extracts a single Blender node into Zeni schema."""
    parms = {}
    for inp in node.inputs:
        if not inp.is_linked:
            try:
                parms[inp.name] = str(inp.default_value)
            except Exception:
                pass
                
    connections = []
    for out in node.outputs:
        for link in out.links:
            connections.append({
                "source_output": out.name,
                "target_node": link.to_node.name,
                "target_input": link.to_socket.name
            })
            
    return {
        "node_path": f"{tree_path}/{node.name}",
        "node_type": node.bl_idname,
        "parameters": parms,
        "connections": connections,
        "hda_doc": node.bl_description if hasattr(node, "bl_description") else "",
        "assets": [],
        "code_content": "",
        "flags": {},
        "schema_version": "1.0",
        "dcc_properties": {
            "blender_type": node.type,
            "dimensions": f"{node.dimensions.x}x{node.dimensions.y}",
            "color": str(node.color) if node.use_custom_color else None
        }
    }

def extract_scene() -> List[Dict[str, Any]]:
    chunks = []
    
    # Example: extract compositing nodes
    if bpy.context.scene.use_nodes and bpy.context.scene.node_tree:
        tree = bpy.context.scene.node_tree
        for node in tree.nodes:
            chunks.append(extract_node(node, "/scene/compositing"))
            
    # Example: extract material nodes
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                chunks.append(extract_node(node, f"/materials/{mat.name}"))
                
    return chunks
