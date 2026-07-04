# AIOS WorkLens & Case Cockpit

AIOS WorkLens is a Personal Senior Work Intelligence System (Hệ thống trí tuệ công việc cá nhân). The **AIOS Case Cockpit** is its local workspace module designed for handling daily incidents, organizing evidence, generating Reasoning Maps, constructing safe AI Prompt Packs, and drafting secure handovers.

---

## 📖 Key Reference Documents
- **Roadmap Index:** [ROADMAP.md](ROADMAP.md) - High-level development roadmap index and gate status.
- **Product North Star & Doctrine:** [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md) - The core loops, layers, values, and definitions of AIOS WorkLens.
- **Development & Agent Rules:** [AGENT_RULES.md](AGENT_RULES.md) - Mandatory guidelines and model roles for AI developers.
- **WorkLens Architecture:** [WORKLENS_ARCHITECTURE.md](WORKLENS_ARCHITECTURE.md) - Module boundaries and product layers.

---

## ⚡ Quick Start
1. **Install Dependencies:**
   Ensure Python 3.x is installed, then install the package in editable mode:
   ```bash
   py -3 -m pip install -e .
   ```
2. **Launch Workspace Chat (UI Chính):**
   Double-click [RUN_AIOS_HABIT_STUDIO.bat](RUN_AIOS_HABIT_STUDIO.bat) on Windows, or run:
   ```bash
   py -3 -m streamlit run src\aios_habit\workspace_chat_app.py
   ```
3. **Launch Case Cockpit (Legacy / Reference Only):**
   Double-click [RUN_AIOS_CASE_COCKPIT.bat](RUN_AIOS_CASE_COCKPIT.bat) on Windows, or run:
   ```bash
   py -3 -m streamlit run src\aios_habit\case_cockpit.py
   ```

---

## 🧪 Running Tests & Audits
- **Run Unit Tests:**
  ```bash
  py -3 -m pytest
  ```
- **Run Security & Integrity Audit:**
  ```bash
  $env:PYTHONPATH="src"
  py -3 -m aios_habit.cli audit
  ```
- **Check Ignored Runtime Assets:**
  Make sure local database and assets remain ignored:
  ```bash
  git status --short --ignored
  ```

## Using full-bundle IDE handoff

AIOS can create a local full-bundle request for Antigravity/IDE AI without calling a cloud provider.

1. In Workspace Chat (hoặc Case Cockpit legacy), create `Trả lời bằng AI IDE từ full bundle`.
2. Ask the IDE AI to read the complete `local_runs/ide_handoff/outbox/REQ-...` folder and write response JSON to `local_runs/ide_handoff/inbox/`.
3. Import that response JSON in AIOS. AIOS validates request ID, privacy acknowledgement, full-bundle use, and evidence IDs before saving.

Do not commit `local_runs/` bundles or raw local documents.
