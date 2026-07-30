# PMA Creative Module — XPRIZE Submission Plan

Deadline: **Aug 17, 2026, 1:00pm PDT**. Written: Jul 25, 2026. 24 days out.

## Locked scope (do not re-litigate mid-build)

- **DCC target:** Houdini only. No Blender/Nuke/Maya in this submission.
- **Category:** Small Business Services (freelance VFX artists / small studios).
- **The one product feature:** an in-Houdini copilot that indexes a `.hip`
  project's node comments, VEX wrangle code, non-default parameters, and
  errors/warnings, then answers questions like "why does this break" or
  "where did I solve this before."
- **The one agent-operated business decision:** trial-signup triage. When
  someone signs up, Gemini reads what they submitted (use-case description
  and/or a summary of their `.hip` file) and decides which tier to
  recommend and what onboarding note to send. This is the piece that
  answers "AI operates the business," distinct from the product's own
  Q&A feature — keep both, but don't let one substitute for the other in
  the video/narrative.
- **Google Cloud requirement:** the naive path (Vertex AI Gemini via
  `gcloud auth application-default login`) hits a "Prepay" billing wall —
  the $300 GCP trial credit explicitly excludes Gemini-as-a-service
  usage, requiring real prepaid funds. **Workaround in place:**
  `gemini_client.py` now supports AI Studio's free API key
  (`GEMINI_API_KEY`, no card needed) as an interim mode, auto-switching
  to Vertex (`GCP_PROJECT`/`GCP_LOCATION`) once billing is sorted. The
  "Google Cloud product" submission requirement gets satisfied
  separately — e.g. hosting the backend on Cloud Run, or storing
  `agent_decisions.jsonl` in Cloud Storage — both of which ARE covered
  by the normal $300 trial credit, unlike genAI model-as-a-service.
  **Open:** actually stand up whichever GCP product is chosen for this
  before submission — not done yet.
- **Before charging real customers:** AI Studio's free tier permits
  Google to use inputs to improve their models. Fine for dev/testing,
  but a paying VFX artist's proprietary node graphs/VEX code going
  through it is real customer IP exposure — same category of issue
  already flagged for PMA's core product's Gemini free-tier default.
  Move to Vertex (or a paid AI Studio tier) before this touches a real
  paying customer's actual project files.

## What NOT to build

- No multi-DCC abstraction layer.
- No custom Qt Python Panel UI for v0 — shelf tools + `hou.ui.readInput` /
  `hou.ui.displayMessage` are enough to demonstrate the feature and far
  less likely to break across Houdini versions.
- No semantic/vector search for v0. SQLite FTS5 keyword search only. Add
  LanceDB/ONNX embeddings later if time allows — it is not required to
  clear the evidence bar.
- No speculative billing logic beyond a single Stripe Checkout link +
  webhook that logs a triage decision.

## 24-day timeline

| Days  | Focus |
|-------|-------|
| 1–3   | Confirm extractor.py works against a real `.hip` file in Houdini. Stand up backend locally. |
| 4–10  | Wire shelf tools to backend. Get end-to-end: open Houdini → index scene → ask a question → get an answer. |
| 10–14 | Put it in front of 5–10 real Houdini artists (existing network/communities). Not cold marketing. |
| 14–20 | Convert 1–3 to paid via Stripe (even $10–20/mo is real revenue). Collect 2–3 testimonials + permission to list as reference. Keep agent_decisions.jsonl running continuously. |
| 20–24 | Record 3-min video, write 500–1000 word narrative, assemble P&L (incl. marketing spend, even if $0), submit with buffer. |

## Evidence checklist

See `docs/EVIDENCE_CHECKLIST.md` — mapped 1:1 to the devpost submission list.

## Known open risks

- `houdini_plugin/pma_houdini/extractor.py` and the `.shelf` XML are
  written from Houdini API knowledge but **not run against a live Houdini
  session** (no Houdini available in the environment this was scaffolded
  in). Verify against your installed Houdini version before Day 3.
- Stripe webhook signature verification is stubbed, not wired to a real
  account/secret yet.
- `backend/` FastAPI service and SQLite FTS5 store **were run and tested**
  in-sandbox (see `backend/tests/test_smoke.py`) — that part is verified,
  not just claimed.
