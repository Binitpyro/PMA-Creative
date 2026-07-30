# Zeni WebSocket Server Routes & Agent Refactor Design

## 1. Executive Summary

This document defines the design and implementation for the **Zeni WebSocket Server Routes** (`src/server/ws_router.py`) and the **Zeni Core Refactor** (`src/core/zeni_agent.py`, `src/core/zeni_prompt.py`). The router connects `pma_houdini` client tools over WebSocket (`ws://localhost:8000/api/modules/ws`) to Zeni's RAG retrieval and answer engine.

---

## 2. Understanding Summary

* **What is being built**: Zeni WebSocket server message router and agent refactor handling `creative_ingest`, `creative_query`, `creative_cross_query`, and `creative_list_projects`.
* **Product Name**: **Zeni** (in-Houdini AI assistant).
* **Key Constraints**:
  * **Python 3.12 strictly**.
  * **O(1) memory streaming footprint (<60MB RAM)**.
  * Authenticates using `x-local-access-token` header verified against OS `keyring`.

---

## 3. Architecture & Data Flow

```
Houdini Client (client.py) ◄───(WS Token Stream)─── Zeni WS Router (ws_router.py)
                                                            │
                                                     ZeniAgent (zeni_agent.py)
                                                            │
                                                     SQLite FTS5 (Local DB)
```

### Action Dispatch Rules

| Action | Handler | O(1) Memory Strategy |
| :--- | :--- | :--- |
| `creative_ingest` | `ZeniAgent.ingest_scene()` | Fixed 50-node batch inserts (`executemany`) |
| `creative_query` | `ZeniAgent.stream_answer()` | SQLite FTS5 generator + token streaming |
| `creative_cross_query` | `ZeniAgent.cross_search()` | Cross-project FTS5 generator retrieval |
| `creative_list_projects` | `ZeniAgent.list_projects()` | Indexed `.hip` project name scan |

---

## 4. Decision Log

| Decision Area | Selected Option | Alternatives Considered | Rationale |
| :--- | :--- | :--- | :--- |
| **Product Brand** | **Zeni** | Copilot | Rebranded per user directive. |
| **Router Architecture**| Modular Router (`src/server/ws_router.py`) | Monolithic in `main.py` | Clean separation between WS transport and RAG logic; easy async unit testing. |
| **Streaming Protocol**| Token-by-token WS streaming | Single-shot buffered string | Maintains <60MB RAM footprint; provides instant UI feedback. |
| **Authentication** | `x-local-access-token` via Keyring | Plaintext `.env` secret | Secure secret handling using OS Keyring. |

---

## 5. Implementation Plan Steps

1. Refactor `src/core/copilot_agent.py` → `src/core/zeni_agent.py` and `copilot_prompt.py` → `zeni_prompt.py`.
2. Create `src/server/__init__.py` and `src/server/ws_router.py`.
3. Update `client.py` and test modules to reference `Zeni`.
4. Create async integration test suite in `tests/test_ws_router.py`.
