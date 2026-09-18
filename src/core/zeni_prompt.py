"""Zeni System Prompts and Context Formatting Engine."""
from __future__ import annotations

from typing import Any, Iterable
from src.core.prompt_library import (
    HOUDINI_SENIOR_TD_SYSTEM_PROMPT,
    HOUDINI_VEX_ATTRIBUTE_EXPERT_PROMPT,
    HOUDINI_SIM_DEBUGGER_PROMPT,
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
    "HOUDINI_CROSS_SEARCH_SYSTEM_PROMPT",
    "TRIAL_TRIAGE_SYSTEM_PROMPT",
    "PromptLibrary",
    "format_cacheable_prompt",
    "format_context",
]


def format_context(
    metadata: dict[str, Any],
    scene_chunks: Iterable[dict[str, Any]],
    corpus_chunks: Iterable[dict[str, Any]],
    max_total_chars: int = 12000,
    max_vex_chars: int = 1500,
) -> str:
    """Format scene metadata, node graph chunks, and personal corpus into a bounded Markdown context string."""
    lines = []

    # 1. SCENE CONTEXT
    lines.append("## [SCENE_CONTEXT]")
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

    for chunk in scene_chunks:
        chunk_count += 1
        node_path = chunk.get("path") or chunk.get("node_path", "Unknown Node")
        node_type = chunk.get("type") or chunk.get("node_type", "Unknown Type")

        lines.append(f"#### Node: `{node_path}` ({node_type})")

        if chunk.get("comment"):
            lines.append(f"**Comment**: {chunk['comment']}")

        if chunk.get("errors"):
            errors = chunk["errors"]
            err_str = "; ".join(str(e) for e in errors) if isinstance(errors, list) else str(errors)
            lines.append(f"**Errors / Warnings**: {err_str}")

        dcc_props = chunk.get("dcc_properties", {})
        vex_code = dcc_props.get("code_snippet") or chunk.get("vex_snippet") or chunk.get("wrangle_code")
        if vex_code:
            lines.append("**Code Snippet**:")
            lines.append("```c")
            code_str = vex_code.strip()
            if len(code_str) > max_vex_chars:
                code_str = code_str[:max_vex_chars] + "\n... [truncated]"
            lines.append(code_str)
            lines.append("```")

        parms = chunk.get("non_default_parms") or chunk.get("non_default_params")
        if parms:
            lines.append(f"**Non-Default Parameters**: `{parms}`")
            
        flags = chunk.get("flags")
        if flags:
            lines.append(f"**Flags**: `{flags}`")

        lines.append("")

    if chunk_count == 0:
        lines.append("_No specific node graph chunks matched the query._\n")

    # 2. CORPUS CONTEXT
    lines.append("## [CORPUS_CONTEXT]")
    corpus_count = 0
    for chunk in corpus_chunks:
        corpus_count += 1
        title = chunk.get("title", "Untitled Document")
        lines.append(f"### Source: {title}")
        content = chunk.get("content", "")
        lines.append(content)
        lines.append("")
        
    if corpus_count == 0:
        lines.append("_No personal corpus documents matched the query or corpus is unavailable._\n")

    lines.append("## INSTRUCTIONS FOR LLM")
    lines.append("IMPORTANT: When answering, you MUST provide source attribution. If using info from [CORPUS_CONTEXT], cite the Source title (e.g., 'Source: March Lookdev Notes').")

    full_text = "\n".join(lines)
    if len(full_text) > max_total_chars:
        full_text = full_text[:max_total_chars] + "\n... [Context truncated due to length limits]\n"

    return full_text
