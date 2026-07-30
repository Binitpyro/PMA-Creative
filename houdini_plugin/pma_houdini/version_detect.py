"""Houdini version detection for PMA Creative Module.
Target: Houdini 20.0.368"""
from __future__ import annotations

from typing import Any

TARGET_VERSION = (20, 0, 368)


def detect_houdini_version() -> dict[str, Any]:
    """Must be called inside Houdini environment."""
    import sys
    import hou

    v = hou.applicationVersion()
    info = {
        "major": v[0],
        "minor": v[1],
        "build": v[2],
        "full_version": hou.applicationVersionString(),
        "platform": hou.applicationPlatformInfo(),
        "is_apprentice": hou.isApprentice(),
        "python_version": sys.version.split()[0],
    }
    try:
        hip = hou.hipFile.path()
        if hip and hip != "untitled.hip":
            info["hip_file_version"] = hou.hipFile.savedVersion()
    except Exception:
        pass
    return info


def is_compatible() -> bool:
    import hou

    return hou.applicationVersion() >= TARGET_VERSION


def get_version_summary() -> str:
    info = detect_houdini_version()
    parts = [f"Houdini {info['full_version']}"]
    if info["is_apprentice"]:
        parts.append("(Apprentice)")
    parts.append(f"on {info['platform']}")
    parts.append(f"Python {info['python_version']}")
    return " | ".join(parts)
