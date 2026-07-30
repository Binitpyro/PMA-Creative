# Zeni Prompt Engineering & Prompt Library Guide

## 1. Overview

Zeni uses a **Prompt Library Architecture** (`src/core/prompt_library.py`) optimized with:
1. **Prompt Caching Prefix Structure**: Static instructions remain at the top of the prompt payload to maximize LLM prompt-caching hits, reducing token cost and latency.
2. **Instruction Hierarchy & CoT**: System Context → 3-Step Reasoning Steps → Structured Response Format → Few-Shot Example → Edge-Case Fallbacks.
3. **Specialized Houdini Pain-Point Prompts**: Targeted expert personas addressing the top 5 production difficulties in SideFX Houdini.

---

## 2. Specialized Prompt Registry (`PromptLibrary`)

| Prompt Key | Role Persona | Production Pain Point Addressed |
| :--- | :--- | :--- |
| `copilot_td` | **Senior Houdini Technical Director** | General `.hip` scene RAG debugging & Q&A |
| `vex_expert` | **VEX Language & Math Specialist** | Attribute qualifiers (`v@`, `i@`, `s@`), vector/matrix math, and Run-Over modes (Point vs Prim vs Detail) |
| `sim_debugger` | **DOPs & Dynamics Simulation Specialist** | Exploding FLIP/Pyro/Vellum/RBD sims, SDF voxel collisions, sub-steps, constraint breakdowns |
| `usd_solaris` | **Solaris & OpenUSD Pipeline Specialist** | LOP stage primitive paths (`/World/geo`), layer opinion conflicts (`def`/`over`), MaterialX shaders |
| `kinefx_rigging`| **KineFX Rigging & Motion Specialist** | Skeleton transform matrices (`m4@transform`), joint parentage (`i@parent`), skinning wrangles |
| `tops_pdg` | **TOPs / PDG Automation Specialist** | Work item generation failures, wedging errors, dynamic partitioners, cache invalidation |
| `cross_search` | **Lead VFX Pipeline Architect** | Solution comparison across multiple `.hip` projects |
| `trial_triage` | **Autonomous Business Operator** | Artist trial signup triage and tier recommendations |

---

## 3. Standard Response Format

All Zeni debugging prompts enforce a strict 3-section Markdown output format:

```markdown
### Root Cause
A clear, technical explanation of why the node error, VEX bug, or network bottleneck occurs.

### VEX / Node Fix
Direct, production-ready, copy-pasteable VEX wrangle code block or exact parameter values to set.

### Step-by-Step Instructions
A numbered, clear sequence of actions to perform in the Houdini Network Editor.
```

---

## 4. Prompt Caching Optimization (`format_cacheable_prompt`)

LLM providers (such as Gemini and Claude) cache prompt prefixes when static system instructions stay identical across calls. Zeni structures payloads using `format_cacheable_prompt`:

```python
def format_cacheable_prompt(prompt_name: str, context_data: str, user_query: str) -> str:
    system_prefix = PromptLibrary.get_prompt(prompt_name)
    return f"{system_prefix}\n\n{context_data}\n\n## User Input / Query\n{user_query}\n"
```

```
┌───────────────────────────────────────────────────────────┐
│ STATIC PREFIX (CACHED BY LLM PROVIDER)                    │
│   • System Role & Persona                                 │
│   • Instruction Hierarchy & CoT Steps                     │
│   • Output Section Rules                                  │
│   • Few-Shot Examples                                     │
├───────────────────────────────────────────────────────────┤
│ DYNAMIC PAYLOAD                                           │
│   • RAG Scene Chunks (Node comments, wrangles, errors)    │
│   • User Question                                         │
└───────────────────────────────────────────────────────────┘
```
