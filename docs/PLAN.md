# PMA Creative Module — XPRIZE Submission Plan

Deadline: **Aug 17, 2026, 1:00pm PDT**. Written: Jul 25, 2026 (Updated Jul 30, 2026).

## Locked scope

- **DCC target:** Houdini only.
- **Category:** Small Business Services (freelance VFX artists / small studios).
- **The product feature:** In-Houdini copilot panel that indexes a `.hip` project's node comments, VEX wrangle code, non-default parameters, and errors/warnings, then answers technical questions inside Houdini.
- **The agent-operated business decision:** Trial-signup triage and subscription payment logging. When someone signs up, Zeni evaluates signups using `trial_triage` prompt and logs autonomous decisions to `logs/agent_decisions.jsonl` with `fsync`.
- **Inference & Privacy:** Zeni performs node-graph retrieval locally via SQLite FTS5 (`data/zeni.db`) and delegates LLM inference calls to Core's provider layer (`POST /api/llm/chat`) with explicit provider/model selection, protecting proprietary VEX/scene IP when used with local models (Ollama / LM Studio).
- **Google Cloud Requirement:** Cloud Run hosting or Cloud Storage for anonymized decision logs (`agent_decisions.jsonl`) satisfies the GCP infrastructure requirement using standard trial credits.

## Timeline & Status

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Standalone FastAPI server on port 8765, canonical schema alignment, FTS5 sync triggers, VEX query tokenizer. | **Completed & Verified** |
| Phase 2 | Core provider layer inheritance (`pma_llm.py`), deterministic prompt router, context bounding. | **Completed & Verified** |
| Phase 3 | Autonomous trial triage agent (`triage.py`), decision log store (`store.py`), Stripe Checkout & webhook signature handling (`payment.py`). | **Completed & Verified** |
| Phase 4 | Non-blocking PySide Qt Assistant Panel (`ui.py`) with Settings tab, settings persistence (`data/settings.json`), and worker thread offloading. | **Completed & Verified** |
| Phase 5 | 24 passing unit & integration tests, docs truth pass, zero-SDK security hardening. | **Completed & Verified** |

## Evidence Checklist

See `docs/EVIDENCE_CHECKLIST.md` — mapped 1:1 to the devpost submission list.
