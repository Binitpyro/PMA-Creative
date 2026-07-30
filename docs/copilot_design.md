# Houdini Copilot RAG & Prompt System Design

## 1. Executive Summary

This document defines the architecture, system prompt design, and data flow for the **Houdini Copilot RAG Assistant** in `PMA-CreativeXprize`. The copilot allows VFX artists and Technical Directors in SideFX Houdini to query scene graph context, debug breaking nodes, and fix VEX wrangles directly from inside Houdini.

---

## 2. Understanding Summary

* **What is being built**: An in-Houdini Copilot RAG assistant and Senior Houdini TD system prompt engine that indexes `.hip` scene nodes (VEX wrangles, node comments, non-default parameters, errors/warnings) and provides interactive Q&A.
* **Why it exists**: Enables VFX artists and TDs to debug breaking nodes and complex VEX scripts inside Houdini without context-switching.
* **Target Audience**: Freelance VFX artists and small studio TDs (XPRIZE Small Business Services category).
* **Key Constraints**:
  * **Python 3.12 strictly** across the entire codebase for PMA Core compatibility.
  * Local-first, **<60MB RAM footprint**, **O(1) memory streaming** to respect local machine CPU/GPU resources.
  * Connects over WebSocket (`ws://localhost:8000/api/modules/ws`) with `X_LOCAL_ACCESS_TOKEN` stored in OS `keyring`.

---

## 3. System Prompt Design & Output Schema

The system prompt configures Gemini as a Senior Houdini Technical Director and enforces a **Structured Debugger** response layout:

```markdown
### Root Cause
[Concise technical explanation of why the node graph or VEX wrangle breaks]

### VEX / Node Fix
[Direct copy-pasteable VEX snippet or exact parameter values to set]

### Step-by-Step Instructions
[Numbered sequence of actions to perform in the Houdini Network Editor]
```

---

## 4. Architecture & Component Diagram

```
[ Houdini Plugin ] (Thin Client)
  │  extractor.py  : Node graph chunking (VEX, comments, errors, params)
  │  ui.py         : PySide Q&A UI panel (Token Streaming display)
  │  client.py     : WebSocket client (keyring auth)
  │
  └─► WebSocket (ws://localhost:8000/api/modules/ws)
        │
[ PMA Core / Backend ] (Python 3.12, <60MB RAM)
  │  src/models/schemas.py      : Pydantic message envelopes
  │  src/core/copilot_prompt.py : System prompt template & context formatters
  │  src/core/copilot_agent.py  : SQLite FTS5 retriever & Gemini LLM coordinator
  │
  └─► Gemini API (AI Studio Key / Vertex AI)
```

---

## 5. Memory & O(1) Streaming Pipeline

1. **O(1) Batch Ingestion**: Nodes extracted from Houdini are stored in local SQLite FTS5 using fixed-size batching (50 nodes per batch).
2. **Generator-Based RAG Retrieval**: FTS5 keyword queries iterate via DB cursors rather than loading full result sets into RAM.
3. **Token Streaming**: Gemini LLM responses stream token-by-token over WebSocket directly to the Houdini PySide UI for immediate feedback.

---

## 6. Decision Log

| Decision Area | Selected Option | Alternatives Considered | Rationale |
| :--- | :--- | :--- | :--- |
| **Scope Focus** | Product Copilot RAG | Trial Triage Agent | Prioritize core value product for artists. |
| **Output Style** | Structured Debugger | Action-First / Tutor | Provides predictable, high-legibility layout for PySide UI. |
| **Architecture** | Server-Side Agent (`src/core/`) | Client-side plugin prompt building | Thin Houdini plugin; prompt updates require no plugin reinstall. |
| **Python Version**| **Python 3.12 strictly** | Python 3.9–3.11 compatibility hacks | 100% compatibility with PMA Core. |
| **Memory Policy**| **O(1) Streaming (<60MB RAM)** | Bulk `fetchall()` / buffered strings | Respects local workstation CPU/GPU resources for Houdini. |

---

## 7. Next Steps & Implementation Plan

1. Create `src/core/copilot_prompt.py` with system prompt templates and context formatters.
2. Implement `src/core/copilot_agent.py` to handle RAG queries with FTS5 search and Gemini streaming.
3. Add Pydantic schemas in `src/models/schemas.py` for WebSocket envelopes.
4. Write unit tests in `tests/test_copilot_prompt.py` and `tests/test_copilot_agent.py` under Python 3.12.
