# Validation Guide: Modern Chat Composer

## Prerequisites

- Project dependencies are installed in `.venv`.
- Start the Workspace Chat with `RUN_AIOS_WORKSPACE_CHAT.bat`.

## Manual checks

1. Open an existing conversation and confirm the composer shows an input, attachment action and send action in one compact region.
2. Enter a multi-line question and send with both the send button and Ctrl+Enter. Confirm one answer attempt per action.
3. Open the attachment action, choose a PNG or JPG, and submit an image-only question. Confirm the existing image handling path runs.
4. Submit an empty composer without an image and confirm the existing guidance appears.
5. Resize the browser to 360 px wide and confirm controls remain accessible.

## Automated checks

```powershell
.venv\Scripts\python.exe -m pytest tests/test_workspace_chat_composer_ui.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_multi_file_uploader.py tests/test_workspace_chat_ui_i18n.py -q
.venv\Scripts\python.exe -m compileall src tests
$env:PYTHONPATH="src"; .venv\Scripts\python.exe -c "import aios_habit.workspace_chat_app"
```

Expected result: all focused tests pass, compilation succeeds, and the Workspace Chat module imports without error.
