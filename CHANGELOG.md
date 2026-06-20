# Changelog

## 2026-06-20 - WorkLens Governance and Inheritance Audit

### Added
- Product north star for AIOS WorkLens.
- Master roadmap with 10 phase gates.
- Migration policy and inheritance map for 4 repositories.
- Monday pilot checklist and Case Cockpit acceptance criteria.
- Read-only inheritance audit reports for ABW_NVIDIA_FUSION_CONTROL, skill-Anti-brain-wiki_note, and Nvidia.

### Changed
- Project handover reframed AIOS_habbit as central WorkLens / Case Cockpit product repo.

### Security
- Reaffirmed local-first public safety and no blind code/data copying.

## 2026-06-20 - AIOS Habit Studio Local UI

### Added
- Streamlit-based Web UI (`aios-habit-studio`) to provide a graphical interface over the CLI tools.
- Launcher scripts `RUN_AIOS_HABIT_STUDIO.bat` and `scripts/run_studio.ps1`.
- UI tabs for Dashboard, Projects, Evidence, Memory, Review Queue, Profiles, Export, Audit, Handover, and Settings.
- Documentation for the Studio UI (`docs/STUDIO_UI.md`).

## 2026-06-20 - AIOS Habit Local Platform Completed

### Added
- Python package under `src/aios_habit`.
- CLI `aios-habit` with status, discover, evidence, memory, extract, workflow, decision, profile, export, audit, phase, and handover commands.
- Pytest suite under `tests/`.
- Documentation under `docs/`.
- Phase reports and final audit/handover generators.
- AI export packs for generic, GPT, Gemini, Claude and Grok.

### Changed
- Roadmap updated to Phase 0-9 execution model.
- Phase 0 checklist closed as PASS after validation.

### Security
- Export excludes source conversation archives by default.
- Audit detects common secret patterns and verified memory without evidence.

### Validation
- `py -3 -m pytest`: PASS.
- CLI smoke commands: PASS.
- `aios-habit audit`: PASS after implementation validation.

### Handover
- `PROJECT_HANDOVER.md` and `09_handover/final_handover.md` generated.

## 2026-06-20 - Public-safe MVP hardening

### Added
- Modular CLI implementation, real phase gates, CI workflow, and expanded tests.

### Security
- Hardened gitignore for private runtime data and export packs.

### Validation
- py -3 -m pytest: 16 passed.
