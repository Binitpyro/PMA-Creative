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
                              │ Node Chunks      │ Action Responses
                              ▼                  │
┌────────────────────────────────────────────────────────────────────────┐
│                     Zeni Server (main.py, Port 8765)                   │
│                                                                        │
│   [ ws_router.py ] ◄── (WebSocket: ws://localhost:8765/ws)             │
│          │                                                             │
│          ▼                                                             │
│   [ ZeniAgent (zeni_agent.py) ] ───► SQLite FTS5 (Local DB data/zeni.db)│
│          │                                                             │
│          ▼                                                             │
│   [ pma_llm.py ] ───► Core Provider Layer (POST /api/llm/chat)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Principles

1. **Local-First & Private Search**:
   All scene graph indexing and FTS5 retrieval is stored locally in SQLite (`data/zeni.db`). Requests delegate to PMA Core's provider layer (`POST /api/llm/chat`) using whatever provider/model the artist configures in Settings (e.g. 100% offline Ollama / LM Studio).

2. **Low-Overhead Indexing**:
   Node wrangles and non-default parameter dictionaries are indexed using FTS5 triggers with $O(1)$ batch processing (`executemany`).

3. **Core Provider Layer Inheritance**:
   Zeni does not vendor cloud AI SDKs (`google-genai` or vendor SDKs). All inference routes through Core's 9-provider engine, keeping API secrets in Core's OS keyring (`pma_backend`).

4. **Python Version Compatibility**:
   - `src/` (Standalone Server): Runs on Python 3.10+ (tested on Python 3.11/3.14).
   - `houdini_plugin/` (In-Houdini): Compatible with Houdini 20.0's hython (Python 3.10) and PySide2 / PySide6.

---

## 3. Component Architecture

### 3.1 Standalone Server (`main.py` & `src/server/ws_router.py`)
- Async FastAPI + Uvicorn server running on port `8765` bound to `127.0.0.1` by default.
- Authenticates requests using `x-local-access-token` header verified against `ZENI_ACCESS_TOKEN` / `X_LOCAL_ACCESS_TOKEN` using `secrets.compare_digest`.
- Dispatches WS actions:
  - `creative_ingest`: Ingests node chunks into SQLite FTS5.
  - `creative_query`: Executes RAG search and synthesizes TD copilot answers.
  - `creative_cross_query`: Searches solutions across multiple `.hip` projects.
  - `creative_list_projects`: Lists distinct indexed projects.
  - `creative_list_providers`: Fetches available LLM providers from PMA Core.

### 3.2 Zeni Core Agent (`src/core/zeni_agent.py`)
- Coordinates local SQLite FTS5 storage and trigger-backed retrieval.
- Routes queries deterministically to `vex_expert`, `sim_debugger`, or `copilot_td`.
- Delegates LLM answer generation to `pma_llm.chat()`.

### 3.3 Autonomous Business Module (`src/business/`)
- `store.py`: `log_agent_decision` writes structured records to `logs/agent_decisions.jsonl` with atomic `fsync`.
- `triage.py`: Autonomous trial signup triage agent evaluating customer requirements.
- `payment.py`: Stripe Checkout session creation and webhook signature processing.

### 3.4 In-Houdini Plugin (`houdini_plugin/pma_houdini/`)
- `extractor.py`: Traverses `.hip` node graph and extracts comments, VEX snippets, non-default parms, and errors/warnings.
- `ui.py`: Non-blocking PySide Qt dialogs with QThread worker execution and Settings persistence (`data/settings.json`).
- `client.py`: Direct WebSocket client to Zeni server.

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
      "node_path": "/obj/geo1/attribwrangle1",
      "node_type": "attribwrangle",
      "comment": "Calculates velocity noise",
      "vex_snippet": "v@v += curlnoise(@P * 0.5);",
      "errors": ["Warning: Undefined variable @vel"],
      "non_default_parms": {"snippet": "v@v += curlnoise(@P * 0.5);"}
    }
  ],
  "houdini_version": "20.0.368",
  "platform": "win64"
}
```

### Query Request Envelopes (`creative_query`)
```json
{
  "action": "creative_query",
  "question": "Why is my velocity wrangle giving an undefined variable warning?",
  "project_name": "vfx_explosion",
  "provider": "ollama",
  "model": "llama3"
}
```

### Server Response
```json
{
  "status": "success",
  "action": "creative_query",
  "answer": "### Root Cause\nThe variable `vel` is used without a VEX vector qualifier (`v@vel`)...\n\n### VEX / Node Fix\n```c\nv@vel += set(0, 1, 0);\n```\n\n### Step-by-Step Instructions\n1. Select `attribwrangle1`...\n",
  "chunks_retrieved": 1,
  "provider": "ollama",
  "model": "llama3"
}
```
