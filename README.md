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
2. **Launch Case Cockpit:**
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
