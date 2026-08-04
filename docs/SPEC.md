# Zeni Creative Module - Connection & Module Specification

This document provides the context, architecture, and project structure for the **Zeni Creative Module**.

---

> [!IMPORTANT]
> **Core Objective**
> Zeni is a standalone service that operates on port 8765. It runs its own SQLite FTS5 database (`data/zeni.db`) for in-Houdini scene graph retrieval, while delegating LLM inference requests to PMA Core's provider layer (`POST /api/llm/chat`).

## 1. Connection Architecture

Zeni runs a standalone FastAPI + Uvicorn server.

*   **Protocol:** WebSocket (`ws://` or `wss://`)
*   **Endpoint:** `/ws` on port `8765` (`ws://localhost:8765/ws`)
*   **Authentication:** Requires the `ZENI_ACCESS_TOKEN` or `X_LOCAL_ACCESS_TOKEN`.
    *   *Method 1:* Pass as an HTTP Header: `x-local-access-token: <TOKEN>`
    *   *Method 2:* Pass as a query parameter: `?token=<TOKEN>`

### 1.1 Secret & Token Handling

Zeni retrieves access tokens via OS Keyring (`ZeniCreativeModule` service) with fallback to `ZENI_ACCESS_TOKEN` or `X_LOCAL_ACCESS_TOKEN` environment variables. All token comparisons use `secrets.compare_digest` for constant-time security.

### 1.2 Action Dispatch Schema

Zeni dispatches actions over WebSocket:
- `creative_ingest`: Ingests node chunks into SQLite FTS5.
- `creative_query`: Executes RAG search and returns synthesized copilot answer.
- `creative_cross_query`: Cross-project recall across indexed `.hip` scenes.
- `creative_list_projects`: Lists distinct indexed projects.
- `creative_list_providers`: Fetches available LLM providers from Core (`GET /api/providers`).

---

## 2. Project Structure

```text
PMA-CreativeXprize/
├── requirements.txt         # websockets, pydantic, httpx, keyring, fastapi, uvicorn
├── pyproject.toml           # Hatchling build & pytest configuration
├── main.py                  # Standalone FastAPI server on port 8765
├── src/
│   ├── business/
│   │   ├── store.py         # Autonomous decision log store with fsync
│   │   ├── triage.py        # Autonomous trial signup triage agent
│   │   └── payment.py       # Stripe Checkout & Webhook handler
│   ├── core/
│   │   ├── pma_llm.py       # Core LLM provider HTTP client
│   │   ├── zeni_agent.py    # Zeni FTS5 retriever & answer coordinator
│   │   ├── zeni_prompt.py   # Context formatters and prompt routers
│   │   └── prompt_library.py # Central prompt registry
│   ├── server/
│   │   └── ws_router.py     # Async WebSocket message router
│   └── models/
│       └── schemas.py       # Pydantic v2 schemas
├── houdini_plugin/
│   └── pma_houdini/
│       ├── client.py        # Direct WebSocket client to Zeni server
│       ├── extractor.py     # Node graph walker & VEX extractor
│       ├── ui.py            # Non-blocking PySide Qt Panel with Settings
│       └── version_detect.py # Houdini version detection
└── tests/                   # Pytest suite
```
