# Operator Runbook

## Human Operator Workflow
1. Launch AIOS Habit Studio (`RUN_AIOS_HABIT_STUDIO.bat`).
2. Run discovery from the **Projects** tab.
3. Manage evidence and memories in the **Evidence** and **Memory** tabs.
4. Keep unsupported claims as UNKNOWN or `needs_evidence`.
5. Build profiles only from verified/export-allowed memory via the **Profiles** tab.
6. Run the full audit via the **Audit** tab before any exports.

## AI Executor Workflow
1. Use the CLI interface (`aios-habit`).
2. Run tests and `aios-habit audit`.
3. Use `--dry-run` to preview changes before writing JSONL files.
4. Run `aios-habit phase validate` to ensure phase gate compliance.
