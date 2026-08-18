# Dispatch Assignment — teamwork_preview_worker_1

## 2026-08-18T23:15:28Z

You are teamwork_preview_worker_1.
Working directory: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_worker_1
Project root: d:\Sandbox\AIOS_habbit
Original request file: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md
Project specification file: d:\Sandbox\AIOS_habbit\PROJECT.md
Reference analysis: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_1\analysis.md

Task: Milestone 1 (Layers & Tour Translation)
1. Read the `layers` (8 layers), `tour` (9 steps), and `project` object from `.understand-anything/knowledge-graph.json`.
2. Translate the following text fields into natural, accurate Vietnamese:
   - For each layer in `layers`: translate `name` and `description`. Retain `id` and `nodeIds` 100% untouched.
   - For each step in `tour`: translate `title` and `description`. Retain `order` and `nodeIds` 100% untouched.
   - For `project`: translate `description`.
3. Follow the IT Terminology Glossary in `PROJECT.md` strictly: preserve terms like Agent, Local Storage, Orchestration, Framework, Dashboard, RAG, Streamlit, Pydantic, JSONL, SQLite, CLI, Brain Gateway, Claim Guard, etc. in English.
4. Output your clean translated structure to `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_worker_1\layers_tour_translated.json`.
5. Verify valid JSON syntax and completeness.
6. Write a comprehensive `handoff.md` with Observation, Logic Chain, Caveats, Conclusion, and Verification.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Send a completion message back to parent when done.
