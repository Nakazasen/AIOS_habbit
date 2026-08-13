# Quickstart: Validate Resumable Stage A Preparation

1. Run focused adapter and staging tests:

   ```powershell
   .venv\Scripts\python.exe -m pytest tests\test_workspace_chat_rag_v2_adapter.py tests\test_battle_notebooklm_rag_v2.py -q
   ```

2. Confirm a synthetic interruption writes an identity-matching checkpoint, then resumes without sending the first committed document again.

3. Confirm a synthetic preparation timeout leaves the checkpoint failed and does not create a ready staging manifest.

4. Run real Stage A only after original sealed production evidence and immutable NotebookLM reference artifacts have been restored and verified. Use `local_only`; do not invoke Stage B.
