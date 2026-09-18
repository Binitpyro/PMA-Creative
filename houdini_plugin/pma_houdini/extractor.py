"""Walks a Houdini scene graph and emits structured chunks for indexing.

Must be run with Houdini's own Python (hython) or from inside Houdini's
Python Shell / a shelf tool — it imports `hou`, which only exists in
that environment.
"""
from __future__ import annotations

import json
from typing import Any


def _node_comment(node) -> str:
    try:
        return node.comment() or ""
    except Exception:
        return ""


def _node_errors_warnings(node) -> tuple[list[str], list[str]]:
    try:
        errors = list(node.errors())
    except Exception:
        errors = []
    try:
        warnings = list(node.warnings())
    except Exception:
        warnings = []
    return errors, warnings


def _wrangle_snippet(node) -> str:
    """VEX wrangle nodes (attribwrangle, pointwrangle, volumewrangle, etc.)
    keep their code in a 'snippet' parm. Not all node types have it."""
    parm = node.parm("snippet")
    if parm is None:
        return ""
    try:
        return parm.eval()
    except Exception:
        return ""


def _non_default_parms(node) -> dict[str, str]:
    out = {}
    try:
        for parm in node.parms():
            try:
                if not parm.isAtDefault():
                    out[parm.name()] = parm.evalAsString()
            except Exception:
                continue
    except Exception:
        pass
    return out


def _solver_parms(node) -> dict[str, str]:
    """Detect solver nodes (DOP/SOP solvers) and extract all their non-default params."""
    solver_types = {
        "pyrosolver",
        "smokesolver",
        "popsolver",
        "flipsolver",
        "pyrosolver::2.0",
        "smokesolver::2.0",
        "whitewatersolver",
        "vellumsolver",
        "rbdbulletsolver",
    }
    try:
        type_name = node.type().name().lower()
        if any(st in type_name for st in solver_types):
            return _non_default_parms(node)
    except Exception:
        pass
    return {}


def _render_parms(node) -> dict[str, str]:
    """Detect ROP/Render nodes (e.g. under /out or Karma/Mantra) and extract key render params."""
    try:
        cat_name = node.type().category().name().lower()
        if cat_name in {"driver", "rop"} or "/out" in node.path():
            return _non_default_parms(node)
    except Exception:
        pass
    return {}


def _node_connections(node) -> dict[str, list[str]]:
    """Extract input and output node paths for graph topology."""
    inputs = []
    outputs = []
    try:
        for inp in node.inputs():
            if inp is not None:
                inputs.append(inp.path())
    except Exception:
        pass
    try:
        for out in node.outputs():
            if out is not None:
                outputs.append(out.path())
    except Exception:
        pass
    return {"inputs": inputs, "outputs": outputs}


def _hda_doc(node) -> str:
    """If this node is a Houdini Digital Asset instance, pull whatever
    help/description text the definition carries."""
    try:
        node_type = node.type()
        definition = node_type.definition()
        if definition is None:
            return ""
        parts = []
        desc = node_type.description()
        if desc:
            parts.append(desc)
        try:
            sections = definition.sections()
            help_section = sections.get("Help")
            if help_section is not None:
                parts.append(help_section.contents())
        except Exception:
            pass
        return "\n".join(p for p in parts if p)
    except Exception:
        return ""


SKIP_PARM_TYPES = {"null", "merge", "output", "dot", "subnetwork", "geo"}


def extract_node(node) -> dict[str, Any] | None:
    """Build one chunk for a single node. Returns None if the node has
    nothing worth indexing."""
    node_type = ""
    try:
        node_type = node.type().name().lower()
    except Exception:
        pass

    comment = _node_comment(node)
    snippet = _wrangle_snippet(node)
    errors, warnings = _node_errors_warnings(node)
    all_errors = list(errors) + [f"Warning: {w}" for w in warnings]

    combined_parms = {}
    if node_type not in SKIP_PARM_TYPES:
        combined_parms.update(_non_default_parms(node))
    combined_parms.update(_solver_parms(node))
    combined_parms.update(_render_parms(node))

    hda_doc = _hda_doc(node)
    connections = _node_connections(node)

    # Assets extraction heuristic: find string parms that look like file paths
    assets = []
    try:
        for parm in node.parms():
            try:
                # Often file parms are string type and not default, or they have 'file' in name
                if parm.parmTemplate().type().name() == "String":
                    val = parm.evalAsString()
                    if val and ("." in val or "/" in val or "\\" in val) and not val.startswith("`"):
                        if "file" in parm.name().lower() or "tex" in parm.name().lower():
                            assets.append(val)
            except Exception:
                continue
    except Exception:
        pass

    if not any([comment, snippet, all_errors, combined_parms, hda_doc]):
        return None

    # DCC agnostic schema fields
    dcc_properties = {
        "code_snippet": snippet,
        "non_default_parms": combined_parms,
    }

    import hou
    scene_data = {
        "fps": hou.fps(),
        "frame_range": [hou.playbar.playbackRange()[0], hou.playbar.playbackRange()[1]]
    }

    return {
        "path": node.path(),
        "type": node.type().name(),
        "comment": comment,
        "dcc_properties": dcc_properties,
        "connections": [connections],
        "hda_doc": hda_doc,
        "assets": assets,
        "scene": scene_data,
        "errors": all_errors,
    }


def extract_scene(
    root_path: str = "/obj", max_nodes: int = 10000
) -> list[dict[str, Any]]:
    """Walk the whole scene under root_path and return all non-empty
    node chunks. Call this from a shelf tool or hython script."""
    import hou  # noqa: F401  (only importable inside Houdini)

    root = hou.node(root_path)
    if root is None:
        raise ValueError(f"No node at {root_path}")

    all_children = root.allSubChildren()
    if len(all_children) > max_nodes:
        raise ValueError(
            f"Scene has {len(all_children)} nodes (limit: {max_nodes}). "
            f"Try indexing a specific subnet: extract_scene('/obj/geo1')"
        )

    chunks = []
    for node in all_children:
        chunk = extract_node(node)
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def extract_scene_to_json(
    root_path: str = "/obj", max_nodes: int = 10000
) -> str:
    """Convenience wrapper: returns a JSON string ready to POST to the
    backend /ingest endpoint via client.py."""
    return json.dumps(extract_scene(root_path, max_nodes=max_nodes))
