# Zeni - PMA Creative Module

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Tests](https://img.shields.io/badge/pytest-23%20passed-brightgreen.svg)]()
[![Memory Footprint](https://img.shields.io/badge/memory-%3C60MB%20RAM-success.svg)]()

**Zeni** is a local-first, low-overhead in-Houdini AI assistant and RAG retrieval engine built for SideFX Houdini. It allows VFX artists and Technical Directors (TDs) to query scene graph context, debug breaking nodes, optimize VEX wrangle code, and fix parameter errors without context-switching.

---

## 📚 Documentation Library ([`docs/`](file:///d:/projects/PMA-CreativeXprize/docs))

- 🏗️ [`docs/ARCHITECTURE.md`](file:///d:/projects/PMA-CreativeXprize/docs/ARCHITECTURE.md) — System architecture, O(1) streaming pipeline, and WebSocket specifications.
- 🎨 [`docs/PROMPT_ENGINEERING.md`](file:///d:/projects/PMA-CreativeXprize/docs/PROMPT_ENGINEERING.md) — PromptLibrary registry, 5 specialized Houdini pain-point prompts, and Prompt Caching optimization.
- 📖 [`docs/USER_GUIDE.md`](file:///d:/projects/PMA-CreativeXprize/docs/USER_GUIDE.md) — Installation, setup, and usage guide for SideFX Houdini.
- 📐 [`docs/SPEC.md`](file:///d:/projects/PMA-CreativeXprize/docs/SPEC.md) — Bootstrap connection spec to PMA Core.
- 🚀 [`docs/PLAN.md`](file:///d:/projects/PMA-CreativeXprize/docs/PLAN.md) — XPRIZE 24-day submission plan and locked scope.
- 📋 [`docs/EVIDENCE_CHECKLIST.md`](file:///d:/projects/PMA-CreativeXprize/docs/EVIDENCE_CHECKLIST.md) — Devpost submission evidence checklist.
- 🎨 [`docs/copilot_design.md`](file:///d:/projects/PMA-CreativeXprize/docs/copilot_design.md) — Zeni RAG & Prompt System Design.
- ⚡ [`docs/zeni_ws_design.md`](file:///d:/projects/PMA-CreativeXprize/docs/zeni_ws_design.md) — Zeni WebSocket Server Router Design.

---

## 🚀 Key Features

* **In-Houdini Q&A**: Index `.hip` scene node comments, VEX wrangles, non-default parameters, and node errors/warnings. Ask Zeni questions directly inside Houdini.
* **Structured Debugger Output**: Every answer is structured into:
  - `### Root Cause`
  - `### VEX / Node Fix`
  - `### Step-by-Step Instructions`
* **Specialized Pain-Point Prompts**: 5 targeted expert personas addressing:
  1. `vex_expert`: VEX syntax, attribute qualifiers (`v@`, `i@`), vector/matrix math.
  2. `sim_debugger`: Exploding FLIP/Pyro/Vellum/RBD sims, SDF voxel collisions, substeps.
  3. `usd_solaris`: Solaris LOP stage primitive paths, layer opinions, MaterialX shaders.
  4. `kinefx_rigging`: KineFX skeleton transform matrices, joint parentage, skinning.
  5. `tops_pdg`: TOPs work item generation failures, wedging, schedulers.
* **Prompt Caching Optimization**: Structured prompt prefix layout maximizing LLM prompt-caching hits to minimize API cost and latency.
* **O(1) Memory Footprint (<60MB RAM)**: Local SQLite FTS5 database with generator-based cursor streaming.

---

## 🛠️ Repository Structure

```
docs/               # Dedicated documentation folder
  ARCHITECTURE.md   # System architecture & WebSocket specs
  PROMPT_ENGINEERING.md # PromptLibrary, pain-point prompts & caching
  USER_GUIDE.md     # Houdini installation & usage guide
  SPEC.md           # Bootstrap connection spec to PMA Core
  PLAN.md           # XPRIZE submission plan
  EVIDENCE_CHECKLIST.md # Devpost submission evidence
  copilot_design.md # RAG & prompt design
  zeni_ws_design.md # WebSocket router design

src/                # Server & Zeni Core Engine (Python 3.12, <60MB RAM)
  core/
    zeni_agent.py   # ZeniAgent RAG retriever & LLM coordinator
    zeni_prompt.py  # Zeni System Prompts & Context Formatters
    prompt_library.py # Central Prompt Caching Registry
  server/
    ws_router.py    # Async WebSocket message router for Zeni actions
  models/
    schemas.py      # Pydantic v2 schemas for WS envelopes

houdini_plugin/     # Runs INSIDE Houdini (imports hou)
  pma_houdini/
    client.py       # Direct WebSocket client to Zeni server
    extractor.py    # Walks node graph, extracts VEX wrangles & errors
    ui.py           # PySide Q&A UI dialogs
    version_detect.py # Houdini version detection
  shelf/
    pma_tools.shelf # Houdini shelf tool XML

tests/              # pytest suite (100% passing)
```

---

## 🧪 Testing

Execute the test suite under Python 3.12:
```bash
uv run pytest
```
