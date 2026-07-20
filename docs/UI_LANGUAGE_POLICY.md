# UI Language Policy

## Purpose

Normal owner-facing UI is Vietnamese-first. Developer identifiers, command names
and file paths remain verbatim so they are runnable and searchable.

## Rules

1. Use Vietnamese for labels, actions, warnings, empty states and user-facing
   errors.
2. Explain necessary technical terms beside the UI copy; do not make users learn
   RAG, provider, bridge, hash or gate concepts for daily work.
3. Never expose raw traceback, filesystem paths, secrets or unredacted local
   content through a normal UI error.
4. Keep runnable technical examples literal, for example `pytest`, `compileall`,
   `RUN_AIOS_WORKSPACE_CHAT.bat` and `src/aios_habit/workspace_chat_app.py`.
5. Regression checks may inspect source code, but do not treat a historical
   legacy UI as a supported user interface.
