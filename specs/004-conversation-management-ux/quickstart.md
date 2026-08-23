# Quickstart: Validate Conversation Management UX

## Manual validation

1. Open a notebook with at least two conversations, select one, and verify its selected state and management heading identify the same title.
2. Rename it and verify the list and management heading update together.
3. Request deletion and verify the confirmation names the target; cancel and verify nothing changes.
4. Delete the active conversation while another remains; verify a remaining conversation opens immediately and the page URL references it.
5. Delete the final conversation; verify the clear empty state includes a create-conversation action.
6. Refresh an old link to a deleted conversation; verify the app recovers without a blank content pane.

## Automated validation

```powershell
py -3 -m pytest -q tests/test_workspace_chat_store.py tests/test_workspace_chat_owner_flow.py tests/test_workspace_chat_source_selection_owner_flow.py
py -3 -m compileall src tests
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
```
