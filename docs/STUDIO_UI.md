# AIOS Habit Studio

AIOS Habit Studio is the primary local-first Web UI for users to interact with the AIOS Habit system without needing to memorize CLI commands. It provides a visual, user-friendly interface built on Streamlit.

## Key Features

1. **Dashboard**: Quick overview of repository status, memory/evidence counts, and quick actions.
2. **Projects**: Discover and scan local project repositories to build an inventory.
3. **Evidence Registry**: Add new evidence records through an easy form and view all existing evidence.
4. **Memory Vault**: Validate and store memory units. Enforces constraints (e.g. verified memories must have valid evidence).
5. **Review Queue**: Visually review, approve, or reject candidate memories extracted automatically from documents.
6. **Master Profiles**: Generate and preview the Identity, Behavior, Language, and Workflow profiles based exclusively on verified memory.
7. **Export Packs**: Compile verified, exportable memory into targeted packs for different AI models (GPT, Gemini, Claude, Grok, Generic). Includes pre-export audit safety check.
8. **Audit Validation**: Run full repository audits or specific phase gate validation checks and see clear PASS/FAIL results.
9. **Handover**: Generate the project handover documentation with a single click.
10. **Settings**: View the configured paths and ensure private data is securely kept in local-only directories.

## How to Launch

### Windows
Double-click `RUN_AIOS_HABIT_STUDIO.bat` in the root of the repository.

Alternatively, via PowerShell:
```powershell
.\scripts\run_studio.ps1
```

### Manual Launch
```bash
py -3 -m streamlit run src/aios_habit/studio.py
```

## Architecture

- **Local-first**: Does not rely on cloud processing or remote databases.
- **Stateless UI**: The Streamlit UI acts purely as a presentation layer on top of the robust core logic defined in `aios_habit`.
- **Data Safety**: Inherits all privacy and safety guarantees. The UI enforces the same validation rules as the CLI. Local-only evidence cannot be exported.
