"""Zeni System Prompts and Context Formatting Engine."""
from __future__ import annotations

from typing import Any, Iterable
from src.core.prompt_library import (
    HOUDINI_SENIOR_TD_SYSTEM_PROMPT,
    HOUDINI_VEX_ATTRIBUTE_EXPERT_PROMPT,
    HOUDINI_SIM_DEBUGGER_PROMPT,
    HOUDINI_SOLARIS_USD_EXPERT_PROMPT,
    HOUDINI_KINEFX_RIGGING_PROMPT,
    HOUDINI_TOPS_PDG_EXPERT_PROMPT,
    HOUDINI_CROSS_SEARCH_SYSTEM_PROMPT,
    TRIAL_TRIAGE_SYSTEM_PROMPT,
    PromptLibrary,
    format_cacheable_prompt,
)

ZENI_SYSTEM_PROMPT = HOUDINI_SENIOR_TD_SYSTEM_PROMPT

__all__ = [
    "ZENI_SYSTEM_PROMPT",
    "HOUDINI_SENIOR_TD_SYSTEM_PROMPT",
    "HOUDINI_VEX_ATTRIBUTE_EXPERT_PROMPT",
    "HOUDINI_SIM_DEBUGGER_PROMPT",
    "HOUDINI_SOLARIS_USD_EXPERT_PROMPT",
    "HOUDINI_KINEFX_RIGGING_PROMPT",
    "HOUDINI_TOPS_PDG_EXPERT_PROMPT",
    "HOUDINI_CROSS_SEARCH_SYSTEM_PROMPT",
    "TRIAL_TRIAGE_SYSTEM_PROMPT",
    "PromptLibrary",
    "format_cacheable_prompt",
    "format_scene_context",
]


def format_scene_context(
    metadata: dict[str, Any], chunks: Iterable[dict[str, Any]]
) -> str:
    """Format scene metadata and node graph chunks into a Markdown context string using streaming iterators."""
    lines = ["## Houdini Scene Context"]

    if metadata:
        lines.append("### Scene Metadata")
        if "project_name" in metadata:
            lines.append(f"- **Project / Scene Name**: {metadata['project_name']}")
        if "hip_file" in metadata:
            lines.append(f"- **HIP File Path**: {metadata['hip_file']}")
        if "houdini_version" in metadata:
            lines.append(f"- **Houdini Version**: {metadata['houdini_version']}")
        if "platform" in metadata:
            lines.append(f"- **Platform**: {metadata['platform']}")
        lines.append("")

    lines.append("### Indexed Node Chunks")
    chunk_count = 0

    for chunk in chunks:
        chunk_count += 1
        node_path = chunk.get("path") or chunk.get("node_path", "Unknown Node")
        node_type = chunk.get("type") or chunk.get("node_type", "Unknown Type")

        lines.append(f"#### Node: `{node_path}` ({node_type})")

        if chunk.get("comment"):
            lines.append(f"**Comment**: {chunk['comment']}")

        if chunk.get("errors"):
            errors = chunk["errors"]
            if isinstance(errors, list):
                err_str = "; ".join(str(e) for e in errors)
            else:
                err_str = str(errors)
            lines.append(f"**Errors / Warnings**: {err_str}")

        if chunk.get("wrangle_code"):
            lines.append("**VEX Wrangle Code**:")
            lines.append("```c")
            lines.append(chunk["wrangle_code"].strip())
            lines.append("```")

        if chunk.get("non_default_params"):
            params = chunk["non_default_params"]
            lines.append(f"**Non-Default Parameters**: `{params}`")

        lines.append("")

    if chunk_count == 0:
        lines.append("_No specific node graph chunks matched the query._\n")

    return "\n".join(lines)
