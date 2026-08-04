# Zeni - PMA Creative Module

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/pytest-24%20passed-brightgreen.svg)]()

**Zeni** is a local-first, low-overhead in-Houdini AI assistant and RAG retrieval engine built for SideFX Houdini. It allows VFX artists and Technical Directors (TDs) to query scene graph context, debug breaking nodes, optimize VEX wrangle code, and fix parameter errors without context-switching.

---

## 📚 Documentation Library ([`docs/`](docs/))

- 🏗️ [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architecture, standalone server on port 8765, and WebSocket specifications.
- 🎨 [`docs/PROMPT_ENGINEERING.md`](docs/PROMPT_ENGINEERING.md) — PromptLibrary registry and specialized Houdini pain-point prompts.
- 📖 [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — Installation, setup, and usage guide for SideFX Houdini.
- 📐 [`docs/SPEC.md`](docs/SPEC.md) — WebSocket and core provider layer connection specifications.
- 🚀 [`docs/PLAN.md`](docs/PLAN.md) — XPRIZE submission plan and locked scope.
- 📋 [`docs/EVIDENCE_CHECKLIST.md`](docs/EVIDENCE_CHECKLIST.md) — Devpost submission evidence checklist.
- 🎨 [`docs/copilot_design.md`](docs/copilot_design.md) — Zeni RAG & Prompt System Design.
- ⚡ [`docs/zeni_ws_design.md`](docs/zeni_ws_design.md) — Zeni WebSocket Server Router Design.

---

## 🚀 Key Features

* **In-Houdini Q&A**: Index `.hip` scene node comments, VEX wrangles, non-default parameters, and node errors/warnings. Ask Zeni questions directly inside Houdini.
* **Structured Debugger Output**: Every answer is structured into:
  - `### Root Cause`
  - `### VEX / Node Fix`
  - `### Step-by-Step Instructions`
* **Specialized Copilot Prompts**: Targeted expert personas addressing:
  1. `copilot_td`: General Senior Houdini TD assistant and node network debugger.
  2. `vex_expert`: VEX syntax, attribute qualifiers (`v@`, `i@`), vector/matrix math.
  3. `sim_debugger`: Exploding FLIP/Pyro/Vellum/RBD sims, SDF voxel collisions, substeps.
  4. `cross_search`: Multi-project solution recall across indexed `.hip` scenes.
  5. `trial_triage`: Autonomous trial signup triage and subscription tier placement.
* **Core Provider Layer Integration**: Delegates LLM chat requests to Core (`POST /api/llm/chat`) with explicit provider/model selection, ensuring zero cloud egress when configured with local models (Ollama / LM Studio).
* **Autonomous Business Operations**: Logs trial signup evaluations and Stripe payment webhooks to atomic decision logs (`agent_decisions.jsonl`) with `fsync`.

---

## 🛠️ Repository Structure

```
docs/                # Dedicated documentation folder
  ARCHITECTURE.md    # System architecture & WebSocket specs
  PROMPT_ENGINEERING.md # PromptLibrary & pain-point prompts
  USER_GUIDE.md      # Houdini installation & usage guide
  SPEC.md            # Connection specs
  PLAN.md            # XPRIZE submission plan
  EVIDENCE_CHECKLIST.md # Devpost submission evidence

main.py              # Standalone FastAPI + Uvicorn server (Port 8765)

src/                 # Server & Zeni Engine
  business/          # Autonomous Business Module
    store.py         # Decision logger with atomic fsync
    triage.py        # Autonomous trial signup triage agent
    payment.py       # Stripe Checkout & Webhook verification
  core/
    pma_llm.py       # Core LLM provider HTTP client
    zeni_agent.py    # ZeniAgent FTS5 retriever & answer coordinator
    zeni_prompt.py   # Zeni System Prompts & Context Formatters
    prompt_library.py # Central Prompt Registry
  server/
    ws_router.py     # Async WebSocket message router for Zeni actions
  models/
    schemas.py       # Pydantic v2 schemas for WS envelopes

houdini_plugin/      # Runs INSIDE Houdini (imports hou)
  pma_houdini/
    client.py        # Direct WebSocket client to Zeni server
    extractor.py     # Walks node graph, extracts VEX wrangles & errors
    ui.py            # Non-blocking PySide Q&A UI dialogs with Settings
    version_detect.py # Houdini version detection
  shelf/
    pma_tools.shelf  # Houdini shelf tool XML

tests/               # Comprehensive pytest suite (100% passing)
```

---

## 🧪 Testing

Execute the test suite:
```bash
uv run pytest
```
