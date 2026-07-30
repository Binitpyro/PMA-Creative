# Zeni Architecture & Technical Specification

## 1. System Overview

**Zeni** is a local-first, low-overhead in-Houdini AI assistant and RAG retrieval engine built for SideFX Houdini. It allows VFX artists and Technical Directors (TDs) to query scene graph context, debug breaking nodes, optimize VEX wrangle code, and fix parameter errors without context-switching.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Houdini GUI / Session                           │
│                                                                        │
│   [ Shelf Tools ] ──►  extractor.py  ──►  PySide UI (ui.py)             │
│                             │                  ▲                       │
└─────────────────────────────┼──────────────────┼───────────────────────┘
                              │ Node Chunks      │ Token Stream
                              ▼                  │
┌────────────────────────────────────────────────────────────────────────┐
│                     Zeni Server (Python 3.12)                          │
│                                                                        │
│   [ ws_router.py ] ◄── (WebSocket: ws://localhost:8000/api/modules/ws) │
│          │                                                             │
│          ▼                                                             │
│   [ ZeniAgent (zeni_agent.py) ] ───► SQLite FTS5 (Local DB)            │
│          │                                                             │
│          ▼                                                             │
│   [ PromptLibrary (prompt_library.py) ] ───► Gemini API                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Principles

1. **Local-First & Private**:
   All scene graph indexing is stored locally in SQLite FTS5. Node wrangles and parameters are only sent to the user's configured Gemini API endpoint (AI Studio key or Vertex AI).

2. **Ultra-Low Memory Footprint (<60MB RAM)**:
   Designed to respect local workstation resources so Houdini's viewport, simulation solvers, and rendering threads are never starved of system CPU/GPU memory.

3. **O(1) Streaming Pipeline**:
   - Ingestion inserts node graph chunks using $O(1)$ batch processing.
   - RAG retrieval iterates over SQLite DB cursors without loading full result sets into RAM (`fetchall()`).
   - Gemini LLM answers stream token-by-token over WebSocket to the PySide UI for immediate feedback.

4. **Python 3.12 Strict Standard**:
   All server components (`src/`) adhere strictly to Python 3.12 for 100% compatibility with PMA Core.

---

## 3. Component Architecture

### 3.1 Server Router (`src/server/ws_router.py`)
- Async WebSocket message router handling incoming JSON envelopes.
- Authenticates requests using `x-local-access-token` header verified against OS `keyring` (`PersonalMemoryAssistant` service).
- Dispatches actions:
  - `creative_ingest`: Ingests node chunks into SQLite FTS5.
  - `creative_query`: Executes RAG search and streams Zeni's LLM response.
  - `creative_cross_query`: Searches solutions across multiple `.hip` projects.
  - `creative_list_projects`: Scans distinct indexed projects.

### 3.2 Zeni Core Agent (`src/core/zeni_agent.py`)
- Coordinates local SQLite FTS5 storage and retrieval.
- Formats prompt payloads using `format_cacheable_prompt` for optimal LLM prompt-caching.
- Interfaces with Gemini API (`google-generativeai` or Vertex AI).

### 3.3 Prompt Library (`src/core/prompt_library.py`)
- Centralized registry managing version-controlled system prompts with Prompt Caching prefix structure.
- Includes 5 specialized Houdini pain-point prompts (`vex_expert`, `sim_debugger`, `usd_solaris`, `kinefx_rigging`, `tops_pdg`).

### 3.4 In-Houdini Plugin (`houdini_plugin/pma_houdini/`)
- `extractor.py`: Traverses the active `.hip` node tree and extracts comments, VEX wrangle code, non-default parameters, and errors/warnings.
- `ui.py`: PySide2 / PySide6 Qt dialogs providing interactive Q&A panels inside Houdini.
- `client.py`: WebSocket client connecting to Zeni server.

---

## 4. WebSocket Communication Protocol

### Ingest Request Envelopes (`creative_ingest`)
```json
{
  "action": "creative_ingest",
  "project_name": "vfx_explosion",
  "hip_file": "/scenes/vfx_explosion.hip",
  "chunks": [
    {
      "path": "/obj/geo1/attribwrangle1",
      "type": "attribwrangle",
      "comment": "Calculates velocity noise",
      "wrangle_code": "v@v += curlnoise(@P * 0.5);",
      "errors": ["Warning: Undefined variable @vel"],
      "non_default_params": {"snippet": "v@v += curlnoise(@P * 0.5);"}
    }
  ],
  "houdini_version": "20.5.278",
  "platform": "win64"
}
```

### Query Request Envelopes (`creative_query`)
```json
{
  "action": "creative_query",
  "question": "Why is my velocity wrangle giving an undefined variable warning?",
  "project_name": "vfx_explosion"
}
```

### Server Response
```json
{
  "status": "success",
  "action": "creative_query",
  "answer": "### Root Cause\nThe variable `vel` is used without a VEX vector qualifier (`v@vel`)...\n\n### VEX / Node Fix\n```c\nv@vel += set(0, 1, 0);\n```\n\n### Step-by-Step Instructions\n1. Select `attribwrangle1`...\n",
  "chunks_retrieved": 1
}
```
