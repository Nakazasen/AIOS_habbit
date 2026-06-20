# AIOS WorkLens Development & Agent Rules

This document specifies the locked rules that all future AI models, development agents, and code editors **MUST** follow without exception when working on the `AIOS_habbit` repository.

---

## 1. Locked Model Roles

To prevent regression, incomplete executions, or "fake PASS" verifications, development tasks are strictly partitioned by model/agent specialties:

### A. Audit Specialist
- **Primary Role:** Code quality audit, security review, anti-fake PASS checks, and architectural reasoning.
- **Constraints:**
  - Must inspect all modified files and run independent checks.
  - Must highlight potential prompt leaks, UX overload, and missing validation evidence.
  - Does not commit or write feature code unless requested for minor edits.
- **Current Recommended Model:** Codex GPT-5.5 or equivalent.

### B. Execution Specialist
- **Primary Role:** Implementing features, fixing bugs, refactoring, and writing unit tests.
- **Constraints:**
  - Must strictly adhere to the implementation plans approved by the user.
  - Must not skip writing unit tests or validating commands.
- **Current Recommended Models:** Gemini Flash 3.5 High / Gemini Pro 3.1 or equivalent.

---

## 2. Mandatory Verification & Validation Rules

No pull request or code change is allowed to be merged or pushed without satisfying the following:

1. **Compilation Check:** Code must compile cleanly using `py -3 -m compileall src tests`.
2. **Pytest Coverage:** All existing unit tests and any newly added tests must pass with `py -3 -m pytest -q`.
3. **Local CLI Audit Check:** Running `$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit` must return `"status": "PASS"` with no errors.
4. **Package Import Check:** Running `$env:PYTHONPATH="src"; py -3 -c "import aios_habit.case_cockpit"` must run without errors.

---

## 3. Core Privacy & Security Rules (Non-Negotiable)
- **No Leaks to Cloud:** `local_only` evidence items, raw text extracted from local logs/spreadsheets, and unconfirmed/draft learning cards must **never** be included in external cloud target prompts (`gemini`, `gpt`, `copilot`, `notebooklm_safe`) or cloud_safe handovers.
- **Local AI Target Only:** Such data can only be included in `local_ai` prompts if `include_local_only=True` is explicitly specified by the user.
- **Git-Ignore Rule:** Under no circumstances should local case data (`local_cases/`), actual pilot screenshots, real database files, or private `.env` files be added to Git tracking.

---

## 4. UI Language & Localization Policy
- **Vietnamese First:** The user interface must remain 100% localized in Vietnamese.
- **Explain Technical Terms:** Essential English technical constants (like `local_only`, `redacted_export`, `cloud_allowed`) must have inline Vietnamese explanations immediately adjacent to them.
- **No Code Warnings Leaked:** Raw traceback messages or unhandled Python errors must be captured and presented to the user in a clean, localized warning block.
